"""Tests for payment event idempotency, replay, lease management,
and conflict detection."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from portal.models.payment_event import PaymentEvent
from portal.services.payment_event_service import (
    PLATFORM_SENTINEL,
    ActiveProcessingError,
    EventConflictError,
    TenantResolutionError,
    complete_event,
    compute_payload_digest,
    fail_event,
    reserve_event,
)


def _make_event_record(
    provider_event_id: str = "evt_123",
    provider_account_id: str = "__platform__",
    tenant_id: str = "tenant_a",
    operation: str = "payment_intent.succeeded",
    payload_digest: str = "abc123",
    status: str = "completed",
    result_reference: str = "rcpt_old",
    processing_owner: str | None = None,
    lease_expires_at: datetime | None = None,
    attempt_count: int = 0,
    version: int = 1,
) -> PaymentEvent:
    """Create a mock PaymentEvent record."""
    record = MagicMock(spec=PaymentEvent)
    record.provider = "stripe"
    record.provider_account_id = provider_account_id
    record.provider_event_id = provider_event_id
    record.tenant_id = tenant_id
    record.operation = operation
    record.payload_digest = payload_digest
    record.status = status
    record.result_reference = result_reference
    record.processing_owner = processing_owner
    record.lease_expires_at = lease_expires_at
    record.attempt_count = attempt_count
    record.version = version
    record.correlation_id = None
    return record


class TestReplayDetection:
    """Test replay behavior for previously processed events."""

    @pytest.mark.asyncio
    async def test_completed_replay_returns_cached_result(self):
        """A second webhook with same event ID returns the cached completed result."""
        digest = compute_payload_digest(b'{"id":"evt_123"}')
        existing = _make_event_record(
            status="completed",
            result_reference="rcpt_old",
            payload_digest=digest,
        )

        db = AsyncMock()
        db.flush = AsyncMock()
        db.execute = AsyncMock(
            side_effect=[
                MagicMock(),
                MagicMock(
                    scalars=MagicMock(
                        return_value=MagicMock(first=MagicMock(return_value=existing))
                    )
                ),
            ]
        )

        record = await reserve_event(
            db,
            tenant_id="tenant_a",
            provider="stripe",
            provider_account_id=PLATFORM_SENTINEL,
            provider_event_id="evt_123",
            operation="payment_intent.succeeded",
            payload_digest=digest,
            correlation_id=None,
        )
        assert record.status == "completed"
        assert record.result_reference == "rcpt_old"

    @pytest.mark.asyncio
    async def test_failed_replay_returns_failed_status(self):
        """A second webhook for a failed event returns the failed status."""
        digest = compute_payload_digest(b'{"id":"evt_fail"}')
        existing = _make_event_record(
            status="failed",
            payload_digest=digest,
        )
        db = AsyncMock()
        db.flush = AsyncMock()
        db.execute = AsyncMock(
            side_effect=[
                MagicMock(),
                MagicMock(
                    scalars=MagicMock(
                        return_value=MagicMock(first=MagicMock(return_value=existing))
                    )
                ),
            ]
        )
        record = await reserve_event(
            db,
            tenant_id="tenant_a",
            provider="stripe",
            provider_account_id=PLATFORM_SENTINEL,
            provider_event_id="evt_fail",
            operation="payment_intent.succeeded",
            payload_digest=digest,
            correlation_id=None,
        )
        assert record.status == "failed"


class TestConflictDetection:
    """Test tenant, payload, and operation mismatch detection."""

    @pytest.mark.asyncio
    async def test_tenant_mismatch_fails_closed(self):
        digest = compute_payload_digest(b'{"id":"evt_t"}')
        existing = _make_event_record(
            tenant_id="tenant_a",
            payload_digest=digest,
        )
        db = AsyncMock()
        db.flush = AsyncMock()
        db.execute = AsyncMock(
            side_effect=[
                MagicMock(),
                MagicMock(
                    scalars=MagicMock(
                        return_value=MagicMock(first=MagicMock(return_value=existing))
                    )
                ),
            ]
        )
        with pytest.raises(EventConflictError, match="tenant_mismatch"):
            await reserve_event(
                db,
                tenant_id="tenant_b",
                provider="stripe",
                provider_account_id=PLATFORM_SENTINEL,
                provider_event_id="evt_t",
                operation="payment_intent.succeeded",
                payload_digest=digest,
                correlation_id=None,
            )

    @pytest.mark.asyncio
    async def test_payload_digest_mismatch_fails_as_tampering(self):
        existing = _make_event_record(
            payload_digest="sha256_different",
            tenant_id="tenant_a",
        )
        db = AsyncMock()
        db.flush = AsyncMock()
        db.execute = AsyncMock(
            side_effect=[
                MagicMock(),
                MagicMock(
                    scalars=MagicMock(
                        return_value=MagicMock(first=MagicMock(return_value=existing))
                    )
                ),
            ]
        )
        with pytest.raises(EventConflictError, match="payload_mismatch"):
            await reserve_event(
                db,
                tenant_id="tenant_a",
                provider="stripe",
                provider_account_id=PLATFORM_SENTINEL,
                provider_event_id="evt_123",
                operation="payment_intent.succeeded",
                payload_digest="sha256_new_digest",
                correlation_id=None,
            )

    @pytest.mark.asyncio
    async def test_operation_mismatch_fails_as_tampering(self):
        digest = compute_payload_digest(b'{"id":"evt_o"}')
        existing = _make_event_record(
            operation="payment_intent.failed",
            payload_digest=digest,
        )
        db = AsyncMock()
        db.flush = AsyncMock()
        db.execute = AsyncMock(
            side_effect=[
                MagicMock(),
                MagicMock(
                    scalars=MagicMock(
                        return_value=MagicMock(first=MagicMock(return_value=existing))
                    )
                ),
            ]
        )
        with pytest.raises(EventConflictError, match="operation_mismatch"):
            await reserve_event(
                db,
                tenant_id="tenant_a",
                provider="stripe",
                provider_account_id=PLATFORM_SENTINEL,
                provider_event_id="evt_o",
                operation="payment_intent.succeeded",
                payload_digest=digest,
                correlation_id=None,
            )


class TestLeaseManagement:
    """Test processing lease acquisition and completion."""

    @pytest.mark.asyncio
    async def test_processing_owner_must_match_for_completion(self):
    """Test processing lease acquisition and completion."""
    # Create a simple object to act as the record
    class MockRecord:
        def __init__(self):
            self.processing_owner = "worker_1"
    
    record = MockRecord()
    db = AsyncMock()
    db.flush = AsyncMock()
    # Set the processing_owner to None to trigger the error
    record.processing_owner = None
    with pytest.raises(EventConflictError, match="no_owner"):
        await complete_event(db, record, result_reference="rcpt_new")

    @pytest.mark.asyncio
    async def test_concurrent_active_processing_raises(self):
        digest = compute_payload_digest(b'{"id":"evt_conc"}')
        now = datetime.now(UTC)
        existing = _make_event_record(
            status="processing",
            processing_owner="worker_a",
            lease_expires_at=now + timedelta(seconds=30),
            payload_digest=digest,
            attempt_count=1,
        )
        db = AsyncMock()
        db.flush = AsyncMock()
        db.execute = AsyncMock(
            side_effect=[
                MagicMock(),
                MagicMock(
                    scalars=MagicMock(
                        return_value=MagicMock(first=MagicMock(return_value=existing))
                    )
                ),
            ]
        )
        with pytest.raises(ActiveProcessingError):
            await reserve_event(
                db,
                tenant_id="tenant_a",
                provider="stripe",
                provider_account_id=PLATFORM_SENTINEL,
                provider_event_id="evt_conc",
                operation="payment_intent.succeeded",
                payload_digest=digest,
                correlation_id=None,
            )


class TestFailureClassification:
    """Test transient and permanent failure behavior."""

    @pytest.mark.asyncio
    async def test_transient_failure_sets_retryable(self):
        record = _make_event_record(
            status="processing",
            processing_owner="worker_1",
            attempt_count=1,
        )
        db = AsyncMock()
        db.flush = AsyncMock()
        await fail_event(db, record, error_code="downstream_timeout", permanent=False)
        assert record.status == "reserved"  # Allow retry
        assert record.last_error_code == "downstream_timeout"

    @pytest.mark.asyncio
    async def test_permanent_failure_sets_failed(self):
        record = _make_event_record(
            status="processing",
            processing_owner="worker_1",
            attempt_count=1,
        )
        db = AsyncMock()
        db.flush = AsyncMock()
        await fail_event(db, record, error_code="invalid_signature", permanent=True)
        assert record.status == "failed"

    @pytest.mark.asyncio
    async def test_max_attempts_marks_permanent(self):
        record = _make_event_record(
            status="processing",
            processing_owner="worker_1",
            attempt_count=5,
        )
        db = AsyncMock()
        db.flush = AsyncMock()
        await fail_event(db, record, error_code="downstream_timeout", permanent=False)
        assert record.status == "failed"
        assert record.completed_at is not None


class TestSink:
    """Test the no-side-effect acknowledgment sink."""

    def test_sink_returns_acknowledgment(self):
        from portal.services.payment_event_service import VerifiedPaymentEventSink
        sink = VerifiedPaymentEventSink()
        receipt = sink.acknowledge(
            provider_event_id="evt_123",
            provider="stripe",
            tenant_id="tenant_a",
            operation="payment_intent.succeeded",
            correlation_id=None,
        )
        assert receipt.status == "acknowledged"
        assert receipt.receipt_id.startswith("rcpt_")

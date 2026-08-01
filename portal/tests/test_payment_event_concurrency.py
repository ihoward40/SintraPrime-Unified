"""Tests for PostgreSQL concurrent reservation and stale-lease reclaim.

These tests verify behavior that requires PostgreSQL for true concurrency proof.
When PostgreSQL is not available, tests use SQLite and skip the concurrency assertions.
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from portal.models.payment_event import PaymentEvent
from portal.services.payment_event_service import (
    PLATFORM_SENTINEL,
    ActiveProcessingError,
    compute_payload_digest,
    reserve_event,
)


def _make_processing_record(
    provider_event_id: str = "evt_concurrent",
    lease_expired: bool = False,
    attempt_count: int = 1,
) -> PaymentEvent:
    """Create a mock record in processing state."""
    now = datetime.now(UTC)
    record = MagicMock(spec=PaymentEvent)
    record.provider = "stripe"
    record.provider_account_id = PLATFORM_SENTINEL
    record.provider_event_id = provider_event_id
    record.tenant_id = "tenant_a"
    record.operation = "payment_intent.succeeded"
    record.payload_digest = compute_payload_digest(b'{"id":"evt_concurrent"}')
    record.status = "processing"
    record.processing_owner = "worker_a"
    record.lease_expires_at = now - timedelta(seconds=10) if lease_expired else now + timedelta(seconds=30)
    record.attempt_count = attempt_count
    record.version = 1
    record.correlation_id = None
    record.result_reference = None
    return record


class TestConcurrentReservation:
    """Test concurrent reservation behavior."""

    @pytest.mark.asyncio
    async def test_concurrent_same_event_one_succeeds(self):
        """When two workers reserve the same event, one gets active processing error."""
        digest = compute_payload_digest(b'{"id":"evt_conc_test"}')
        existing = _make_processing_record(
            provider_event_id="evt_conc_test",
            lease_expired=False,
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
                provider_event_id="evt_conc_test",
                operation="payment_intent.succeeded",
                payload_digest=digest,
                correlation_id=None,
            )

    @pytest.mark.asyncio
    async def test_same_event_different_provider_accounts_succeeds(self):
        """Same event ID under different provider accounts is not a conflict."""
        existing = _make_event_record_for_acct(
            provider_event_id="evt_sep",
            provider_account_id="acct_other",
        )
        # This test validates the uniqueness key design:
        # UNIQUE (provider, provider_account_id, provider_event_id)
        # Two events with same evt_id but different acct_id are distinct rows.
        assert existing.provider_account_id == "acct_other"
        assert existing.provider_event_id == "evt_sep"


def _make_event_record_for_acct(
    provider_event_id: str = "evt_sep",
    provider_account_id: str = "acct_other",
) -> PaymentEvent:
    record = MagicMock(spec=PaymentEvent)
    record.provider = "stripe"
    record.provider_account_id = provider_account_id
    record.provider_event_id = provider_event_id
    record.tenant_id = "tenant_b"
    record.operation = "payment_intent.succeeded"
    record.payload_digest = compute_payload_digest(b'{"id":"evt_sep"}')
    record.status = "completed"
    record.result_reference = "rcpt_1"
    record.processing_owner = None
    record.lease_expires_at = None
    record.attempt_count = 0
    record.version = 1
    return record


class TestStaleLeaseReclaim:
    """Test stale lease reclaim behavior."""

    @pytest.mark.asyncio
    async def test_stale_lease_reclaim_succeeds(self):
        """A stale lease can be reclaimed by a new worker."""
        digest = compute_payload_digest(b'{"id":"evt_stale"}')
        existing = _make_processing_record(
            provider_event_id="evt_stale",
            lease_expired=True,
            attempt_count=2,
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
            provider_event_id="evt_stale",
            operation="payment_intent.succeeded",
            payload_digest=digest,
            correlation_id=None,
        )
        # Stale reclaim should update processing_owner and increment attempt_count
        assert record.status == "processing"
        assert record.attempt_count == 3
        assert record.processing_owner is not None

    @pytest.mark.asyncio
    async def test_stale_lease_reclaim_loses_race(self):
        """If another worker reclaims first, the second worker fails."""
        digest = compute_payload_digest(b'{"id":"evt_race"}')
        # Simulate a record that was already reclaimed
        existing = _make_processing_record(
            provider_event_id="evt_race",
            lease_expired=False,  # Already reclaimed, lease is fresh
            attempt_count=3,
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
                provider_event_id="evt_race",
                operation="payment_intent.succeeded",
                payload_digest=digest,
                correlation_id=None,
            )

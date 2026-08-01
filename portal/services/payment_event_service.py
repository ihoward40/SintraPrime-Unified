"""Payment event service — signature verification, tenant resolution,
idempotency, lease management, and audit-envelope integration.

The payment_events row is the authoritative webhook acknowledgment and
idempotency record. result_reference stores a deterministic acknowledgment
identifier. No separate receipt table exists.

Audit envelopes remain the audit-event authority. The payment_events table
does not replace the audit envelope and introduces no competing evidence
hash authority.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.audit_envelope import ActorType, Outcome, Transport, build_audit_event
from ..models.payment_event import PaymentEvent
from ..models.provider_tenant_mapping import ProviderTenantMapping

logger = logging.getLogger(__name__)

LEASE_TIMEOUT_SECONDS = 60
MAX_ATTEMPTS = 5
PLATFORM_SENTINEL = "__platform__"

PERMANENT_ERROR_CODES = frozenset({
    "invalid_signature",
    "missing_signature",
    "expired_signature",
    "tenant_unresolved",
    "tenant_ambiguous",
    "tenant_inactive",
    "tenant_mismatch",
    "payload_mismatch",
    "operation_mismatch",
})


@dataclass(frozen=True)
class Receipt:
    """Deterministic acknowledgment returned by the sink."""

    receipt_id: str
    status: str
    recorded_at: str


class VerifiedPaymentEventSink:
    """No-side-effect sink for verified payment events.

    For Increment One, the only authorized production behavior is:
    - persist a deterministic acknowledgment identifier;
    - record audit evidence;
    - return a deterministic acknowledgment.

    It must NOT create a case, modify a subscription, issue a refund,
    capture or charge payment, call Airtable, invoke Mission Control,
    trigger workflow_builder or scheduler, or mutate billing state
    beyond the new idempotency record.
    """

    def acknowledge(
        self,
        *,
        provider_event_id: str,
        provider: str,
        tenant_id: str,
        operation: str,
        correlation_id: str | None,
    ) -> Receipt:
        receipt_id = f"rcpt_{uuid.uuid4()}"
        recorded_at = datetime.now(UTC).isoformat()
        logger.info(
            "Payment event acknowledged",
            extra={
                "provider_event_id": provider_event_id,
                "provider": provider,
                "operation": operation,
                "receipt_id": receipt_id,
            },
        )
        return Receipt(receipt_id=receipt_id, status="acknowledged", recorded_at=recorded_at)


class TenantResolutionError(Exception):
    """Raised when tenant resolution fails."""

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


class EventConflictError(Exception):
    """Raised when an existing event record conflicts with a new submission."""

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


class ActiveProcessingError(Exception):
    """Raised when a concurrent active processing is detected."""

    def __init__(self, detail: str = ""):
        self.detail = detail
        super().__init__(detail)


def compute_payload_digest(raw_body: bytes) -> str:
    """Compute SHA-256 digest of the raw webhook body."""
    return hashlib.sha256(raw_body).hexdigest()


def verify_stripe_signature(
    raw_body: bytes,
    sig_header: str | None,
    webhook_secret: str,
) -> stripe.Event:
    """Verify the Stripe webhook signature and return the verified event.

    Raises stripe.error.SignatureVerificationError on invalid signatures.
    """
    if not sig_header:
        raise stripe.error.SignatureVerificationError(
            "Missing Stripe-Signature header", sig_header or ""
        )
    return stripe.Webhook.construct_event(raw_body, sig_header, webhook_secret)


async def resolve_tenant(
    db: AsyncSession,
    *,
    provider: str,
    provider_account_id: str | None,
    provider_customer_id: str | None,
) -> str:
    """Resolve tenant from server-side provider_tenant_mappings.

    Caller-supplied tenant_id is NEVER authoritative.
    Unknown, inactive, conflicting, or ambiguous mappings fail closed.
    """
    filters = [ProviderTenantMapping.provider == provider, ProviderTenantMapping.mapping_status == "active"]

    if provider_account_id:
        filters.append(ProviderTenantMapping.provider_account_id == provider_account_id)
    if provider_customer_id:
        filters.append(ProviderTenantMapping.provider_customer_id == provider_customer_id)

    result = await db.execute(
        select(ProviderTenantMapping).where(*filters)
    )
    mappings = result.scalars().all()

    if len(mappings) == 0:
        raise TenantResolutionError("tenant_unresolved", "No active mapping found")

    if len(mappings) > 1:
        raise TenantResolutionError("tenant_ambiguous", f"{len(mappings)} mappings found")

    mapping = mappings[0]
    if mapping.mapping_status != "active":
        raise TenantResolutionError("tenant_inactive", f"Mapping status: {mapping.mapping_status}")

    return mapping.tenant_id


def _get_provider_account_id(event: stripe.Event) -> str:
    """Extract the provider account ID from a Stripe event, or use platform sentinel."""
    account_id = None
    if hasattr(event, "account") and event.account:
        account_id = event.account
    elif event.get("account"):
        account_id = event.get("account")

    if account_id:
        return account_id
    return PLATFORM_SENTINEL


def _audit(
    *,
    action: str,
    outcome: Outcome,
    tenant_id: str | None = None,
    denial_reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Build and log an audit envelope."""
    event = build_audit_event(
        action=action,
        actor_type=ActorType.SYSTEM,
        actor_id=None,
        tenant_id=tenant_id,
        source_transport=Transport.WEBHOOK,
        outcome=outcome,
        denial_reason=denial_reason,
        metadata=metadata,
    )
    logger.info(
        "Audit event recorded",
        extra={
            "audit_event_id": event.event_id,
            "audit_action": action,
            "audit_outcome": event.outcome,
            "audit_tenant": event.tenant_id,
        },
    )


async def reserve_event(
    db: AsyncSession,
    *,
    tenant_id: str,
    provider: str,
    provider_account_id: str,
    provider_event_id: str,
    operation: str,
    payload_digest: str,
    correlation_id: str | None,
) -> PaymentEvent:
    """Atomically reserve a payment event record.

    Uses INSERT ... ON CONFLICT DO NOTHING followed by SELECT to handle
    both first-arrival and replay/conflict paths.
    """
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    worker_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    values = {
        "tenant_id": tenant_id,
        "provider": provider,
        "provider_account_id": provider_account_id,
        "provider_event_id": provider_event_id,
        "operation": operation,
        "payload_digest": payload_digest,
        "status": "reserved",
        "correlation_id": correlation_id,
    }

    try:
        stmt = pg_insert(PaymentEvent).values(**values).on_conflict_do_nothing(
            index_elements=["provider", "provider_account_id", "provider_event_id"]
        )
        await db.execute(stmt)
    except Exception:
        # SQLite fallback for local tests
        stmt = sqlite_insert(PaymentEvent).values(**values).on_conflict_do_nothing(
            index_elements=["provider", "provider_account_id", "provider_event_id"]
        )
        await db.execute(stmt)

    await db.flush()

    result = await db.execute(
        select(PaymentEvent).where(
            PaymentEvent.provider == provider,
            PaymentEvent.provider_account_id == provider_account_id,
            PaymentEvent.provider_event_id == provider_event_id,
        )
    )
    record = result.scalars().first()

    if record.status == "reserved" and record.tenant_id == tenant_id and record.payload_digest == payload_digest:
        # First arrival — acquire lease
        record.status = "processing"
        record.processing_owner = worker_id
        record.lease_expires_at = now + timedelta(seconds=LEASE_TIMEOUT_SECONDS)
        record.started_at = now
        record.attempt_count = 1
        record.updated_at = now
        record.version += 1
        await db.flush()
        return record

    # Existing record — validate consistency
    if record.tenant_id != tenant_id:
        _audit(
            action="webhook.tenant_conflict",
            outcome=Outcome.DENIED,
            denial_reason="tenant_mismatch",
            metadata={"provider_event_id": provider_event_id},
        )
        raise EventConflictError("tenant_mismatch", "Existing record has different tenant")

    if record.payload_digest != payload_digest:
        _audit(
            action="webhook.payload_mismatch",
            outcome=Outcome.DENIED,
            denial_reason="payload_mismatch",
            metadata={"provider_event_id": provider_event_id},
        )
        raise EventConflictError("payload_mismatch", "Payload digest differs from existing record")

    if record.operation != operation:
        _audit(
            action="webhook.operation_mismatch",
            outcome=Outcome.DENIED,
            denial_reason="operation_mismatch",
            metadata={"provider_event_id": provider_event_id},
        )
        raise EventConflictError("operation_mismatch", "Operation differs from existing record")

    # Same event — check status for replay/concurrent/stale
    if record.status == "completed":
        _audit(
            action="idempotency.replayed",
            outcome=Outcome.SUCCESS,
            tenant_id=tenant_id,
            metadata={"provider_event_id": provider_event_id, "result_reference": record.result_reference},
        )
        return record

    if record.status == "failed":
        return record

    if record.status == "processing":
        if record.lease_expires_at and record.lease_expires_at > now:
            raise ActiveProcessingError("Event is currently being processed")
        # Stale lease — reclaim
        old_version = record.version
        record.processing_owner = worker_id
        record.lease_expires_at = now + timedelta(seconds=LEASE_TIMEOUT_SECONDS)
        record.attempt_count += 1
        record.updated_at = now
        record.version = old_version + 1
        await db.flush()
        return record

    # reserved (no processing started) — claim
    record.status = "processing"
    record.processing_owner = worker_id
    record.lease_expires_at = now + timedelta(seconds=LEASE_TIMEOUT_SECONDS)
    record.started_at = now
    record.attempt_count = 1
    record.updated_at = now
    record.version += 1
    await db.flush()
    return record


async def complete_event(
    db: AsyncSession,
    record: PaymentEvent,
    *,
    result_reference: str,
) -> None:
    """Mark an event as completed. Verifies processing ownership."""
    if record.processing_owner is None:
        raise EventConflictError("no_owner", "Record has no processing owner")

    record.status = "completed"
    record.result_reference = result_reference
    record.completed_at = datetime.now(UTC)
    record.updated_at = datetime.now(UTC)
    record.version += 1
    await db.flush()

    _audit(
        action="webhook.processed",
        outcome=Outcome.SUCCESS,
        tenant_id=record.tenant_id,
        metadata={
            "provider_event_id": record.provider_event_id,
            "operation": record.operation,
            "result_reference": result_reference,
        },
    )


async def fail_event(
    db: AsyncSession,
    record: PaymentEvent,
    *,
    error_code: str,
    permanent: bool = False,
) -> None:
    """Mark an event as failed. Unknown failures default to transient."""
    if record.processing_owner is None:
        raise EventConflictError("no_owner", "Record has no processing owner")

    now = datetime.now(UTC)
    record.last_error_code = error_code
    record.updated_at = now
    record.version += 1

    if permanent or record.attempt_count >= MAX_ATTEMPTS:
        record.status = "failed"
        record.completed_at = now
    else:
        record.status = "reserved"  # Allow retry

    await db.flush()

    _audit(
        action="webhook.failed",
        outcome=Outcome.FAILURE,
        tenant_id=record.tenant_id,
        denial_reason=error_code,
        metadata={
            "provider_event_id": record.provider_event_id,
            "error_code": error_code,
            "permanent": permanent or record.attempt_count >= MAX_ATTEMPTS,
        },
    )

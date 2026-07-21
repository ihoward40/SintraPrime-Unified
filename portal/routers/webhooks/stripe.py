"""Stripe webhook route — signature verification, tenant resolution,
idempotency reservation, audit recording, and no-side-effect dispatch.

The payment_events row is the authoritative webhook acknowledgment and
idempotency record. result_reference stores a deterministic acknowledgment
identifier. No separate receipt table exists.

Audit envelopes remain the audit-event authority. The payment_events table
does not replace the audit envelope and introduces no competing evidence
hash authority.
"""

from __future__ import annotations

import logging
import os

import stripe
from fastapi import APIRouter, HTTPException, Request, status

from ...auth.audit_envelope import ActorType, Outcome, Transport, build_audit_event
from ...database import AsyncSessionLocal
from ...schemas.payment_event import WebhookAcknowledgment, WebhookRejection
from ...services.payment_event_service import (
    ActiveProcessingError,
    EventConflictError,
    TenantResolutionError,
    VerifiedPaymentEventSink,
    complete_event,
    compute_payload_digest,
    fail_event,
    reserve_event,
    resolve_tenant,
    verify_stripe_signature,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_sink = VerifiedPaymentEventSink()


def _get_webhook_secret() -> str:
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="STRIPE_WEBHOOK_SECRET not configured",
        )
    return secret


def _audit_pre_tenant(
    action: str,
    outcome: Outcome,
    denial_reason: str | None = None,
    metadata: dict | None = None,
) -> None:
    """Record an audit envelope before tenant resolution."""
    event = build_audit_event(
        action=action,
        actor_type=ActorType.SYSTEM,
        actor_id=None,
        tenant_id=None,
        source_transport=Transport.WEBHOOK,
        outcome=outcome,
        denial_reason=denial_reason,
        metadata=metadata,
    )
    logger.info(
        "Pre-tenant audit event",
        extra={
            "audit_event_id": event.event_id,
            "audit_action": action,
            "audit_outcome": event.outcome,
        },
    )


@router.post("/stripe", response_model=WebhookAcknowledgment)
async def handle_stripe_webhook(request: Request):
    """Handle a Stripe webhook event.

    1. Read raw body (do not deserialize/reserialize before verification).
    2. Read Stripe-Signature header.
    3. Verify using stripe.Webhook.construct_event.
    4. Reject invalid verification.
    5. Preserve verified Stripe event ID and type.
    6. Resolve tenant from server-side provider mappings.
    7. Ignore caller-supplied tenant identity.
    8. Reserve event atomically.
    9. Record audit envelopes.
    10. Call no-side-effect acknowledgment sink.
    11. Complete or fail the event record.
    12. Return deterministic response.
    """
    # Step 1: Read raw body
    raw_body = await request.body()

    # Step 2: Read signature header
    sig_header = request.headers.get("stripe-signature")

    # Step 3 + 4: Verify signature
    webhook_secret = _get_webhook_secret()
    try:
        event = verify_stripe_signature(raw_body, sig_header, webhook_secret)
    except stripe.error.SignatureVerificationError as e:
        _audit_pre_tenant(
            action="webhook.signature_rejected",
            outcome=Outcome.DENIED,
            denial_reason="invalid_signature",
            metadata={"provider": "stripe", "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=WebhookRejection(error="invalid_signature", detail=str(e)).model_dump(),
        )
    except ValueError as e:
        _audit_pre_tenant(
            action="webhook.signature_rejected",
            outcome=Outcome.DENIED,
            denial_reason="missing_signature",
            metadata={"provider": "stripe", "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=WebhookRejection(error="missing_signature", detail=str(e)).model_dump(),
        )

    # Step 5: Preserve verified event ID and type
    provider_event_id = event.get("id", "")
    operation = event.get("type", "")
    provider_account = event.get("account")
    provider_account_id = provider_account if provider_account else "__platform__"

    # Compute payload digest of raw body
    payload_digest = compute_payload_digest(raw_body)

    # Step 6: Resolve tenant
    async with AsyncSessionLocal() as db:
        try:
            # Try Connect account first, then customer from event data
            customer_id = None
            event_data = event.get("data", {}).get("object", {})
            if event_data.get("customer"):
                customer_id = event_data.get("customer")

            tenant_id = await resolve_tenant(
                db,
                provider="stripe",
                provider_account_id=provider_account if provider_account else None,
                provider_customer_id=customer_id,
            )
        except TenantResolutionError as e:
            _audit_pre_tenant(
                action="webhook.tenant_rejected",
                outcome=Outcome.DENIED,
                denial_reason=e.code,
                metadata={"provider_event_id": provider_event_id, "error": e.detail},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=WebhookRejection(error=e.code, detail=e.detail).model_dump(),
            )

        # Step 8: Reserve event atomically
        correlation_id = None
        ctx = request.state
        if hasattr(ctx, "correlation_id"):
            correlation_id = ctx.correlation_id

        try:
            record = await reserve_event(
                db,
                tenant_id=tenant_id,
                provider="stripe",
                provider_account_id=provider_account_id,
                provider_event_id=provider_event_id,
                operation=operation,
                payload_digest=payload_digest,
                correlation_id=correlation_id,
            )
        except EventConflictError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=WebhookRejection(error=e.code, detail=e.detail).model_dump(),
            )
        except ActiveProcessingError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=WebhookRejection(error="processing_in_progress", detail=str(e)).model_dump(),
            )

        # Step 9: Audit already recorded in reserve_event for first arrival

        # Check for replay
        if record.status == "completed":
            return WebhookAcknowledgment(
                status="replayed",
                event_id=provider_event_id,
                receipt_id=record.result_reference,
            )

        if record.status == "failed":
            return WebhookAcknowledgment(
                status="failed",
                event_id=provider_event_id,
                receipt_id=record.result_reference,
            )

        # Step 10: Call no-side-effect sink (NO transaction held)
        try:
            receipt = _sink.acknowledge(
                provider_event_id=provider_event_id,
                provider="stripe",
                tenant_id=tenant_id,
                operation=operation,
                correlation_id=correlation_id,
            )
        except Exception as e:
            await fail_event(
                db,
                record,
                error_code="downstream_error",
                permanent=False,
            )
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=WebhookRejection(error="processing_failed", detail=str(e)).model_dump(),
            )

        # Step 11: Complete the event record
        await complete_event(db, record, result_reference=receipt.receipt_id)
        await db.commit()

    # Step 12: Return deterministic response
    return WebhookAcknowledgment(
        status="completed",
        event_id=provider_event_id,
        receipt_id=receipt.receipt_id,
    )

"""Gate 4B durable authority envelope for one disposable E1 sandbox adapter.

No real connector is registered here. `sandbox.echo-write-v1` is the only executable
adapter and its provider effect is an isolated PostgreSQL certification object.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.external_action_sandbox import (
    ExternalActionApproval,
    ExternalActionEvidence,
    ExternalActionIntent,
    ExternalExecutionKillSwitch,
)
from ..models.governed_service_identity import GovernedServiceIdentityRecord
from .sandbox_echo_adapter import (
    ADAPTER_ID,
    ENVIRONMENT,
    OPERATION_ID,
    canonical_json_hash,
    sandbox_echo_adapter,
)

RISK_CLASS = "E1"
REQUIRED_CAPABILITY = f"external:{ADAPTER_ID}:{OPERATION_ID}"


class ExternalActionAuthorityError(RuntimeError):
    """Raised whenever Gate 4B authority fails closed."""


class ExternalActionIdempotencyConflictError(ExternalActionAuthorityError):
    def __init__(self, intent_id: str):
        self.intent_id = intent_id
        super().__init__("External-action idempotency key was reused with different content")


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _canonical_hash(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _request_hash(
    *,
    tenant_id: str,
    principal_id: str,
    service_identity_id: str,
    destination: str,
    payload_hash: str,
    idempotency_key: str,
    mission_id: str | None,
    schedule_id: str | None,
) -> str:
    return _canonical_hash(
        {
            "tenant_id": tenant_id,
            "principal_id": principal_id,
            "service_identity_id": service_identity_id,
            "adapter_id": ADAPTER_ID,
            "operation_id": OPERATION_ID,
            "environment": ENVIRONMENT,
            "destination": destination,
            "risk_class": RISK_CLASS,
            "payload_hash": payload_hash,
            "idempotency_key": idempotency_key,
            "mission_id": mission_id,
            "schedule_id": schedule_id,
        }
    )


async def _append_evidence(
    db: AsyncSession,
    *,
    intent_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> ExternalActionEvidence:
    previous = await db.scalar(
        select(ExternalActionEvidence)
        .where(ExternalActionEvidence.intent_id == intent_id)
        .order_by(ExternalActionEvidence.sequence_no.desc())
        .limit(1)
    )
    sequence_no = 1 if previous is None else previous.sequence_no + 1
    previous_hash = previous.event_hash if previous is not None else None
    created_at = _now()
    event_hash = _canonical_hash(
        {
            "intent_id": intent_id,
            "sequence_no": sequence_no,
            "event_type": event_type,
            "event_payload": payload,
            "previous_event_hash": previous_hash,
            "created_at": created_at.isoformat(),
        }
    )
    event = ExternalActionEvidence(
        id=str(uuid.uuid4()),
        intent_id=intent_id,
        sequence_no=sequence_no,
        event_type=event_type,
        event_payload=payload,
        previous_event_hash=previous_hash,
        event_hash=event_hash,
        created_at=created_at,
    )
    db.add(event)
    await db.flush()
    return event


async def create_external_intent(
    db: AsyncSession,
    *,
    tenant_id: str,
    principal_id: str,
    service_identity_id: str,
    destination: str,
    payload: dict[str, Any],
    payload_summary: str,
    idempotency_key: str,
    mission_id: str | None = None,
    schedule_id: str | None = None,
) -> dict[str, Any]:
    sandbox_echo_adapter.validate_destination(destination)
    canonical_payload, payload_hash = sandbox_echo_adapter.canonicalize_payload(payload)
    request_hash = _request_hash(
        tenant_id=tenant_id,
        principal_id=principal_id,
        service_identity_id=service_identity_id,
        destination=destination,
        payload_hash=payload_hash,
        idempotency_key=idempotency_key,
        mission_id=mission_id,
        schedule_id=schedule_id,
    )
    existing = await db.scalar(
        select(ExternalActionIntent).where(
            ExternalActionIntent.tenant_id == tenant_id,
            ExternalActionIntent.principal_id == principal_id,
            ExternalActionIntent.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.request_hash != request_hash:
            raise ExternalActionIdempotencyConflictError(existing.id)
        return await get_external_intent(db, tenant_id=tenant_id, intent_id=existing.id)

    intent = ExternalActionIntent(
        id=f"ext-{uuid.uuid4().hex[:20]}",
        tenant_id=tenant_id,
        principal_id=principal_id,
        service_identity_id=service_identity_id,
        mission_id=mission_id,
        schedule_id=schedule_id,
        adapter_id=ADAPTER_ID,
        operation_id=OPERATION_ID,
        environment=ENVIRONMENT,
        destination=destination,
        risk_class=RISK_CLASS,
        payload=canonical_payload,
        canonical_payload_hash=payload_hash,
        request_hash=request_hash,
        payload_summary=payload_summary,
        idempotency_key=idempotency_key,
        credential_ref=None,
        status="DRAFT",
    )
    db.add(intent)
    await db.flush()
    await _append_evidence(
        db,
        intent_id=intent.id,
        event_type="INTENT_CREATED",
        payload={
            "adapter_id": ADAPTER_ID,
            "operation_id": OPERATION_ID,
            "environment": ENVIRONMENT,
            "destination": destination,
            "payload_hash": payload_hash,
            "risk_class": RISK_CLASS,
            "schedule_id": schedule_id,
            "external_effect": False,
        },
    )
    return await get_external_intent(db, tenant_id=tenant_id, intent_id=intent.id)


async def preflight_external_intent(
    db: AsyncSession,
    *,
    tenant_id: str,
    intent_id: str,
) -> dict[str, Any]:
    intent = await _locked_intent(db, tenant_id=tenant_id, intent_id=intent_id)
    if intent is None:
        raise ExternalActionAuthorityError("External-action intent not found")
    if intent.status not in {"DRAFT", "APPROVAL_REQUIRED"}:
        raise ExternalActionAuthorityError(f"Intent cannot preflight from {intent.status}")
    receipt = sandbox_echo_adapter.preflight(
        destination=intent.destination,
        payload=dict(intent.payload),
    )
    if receipt["payload_hash"] != intent.canonical_payload_hash:
        raise ExternalActionAuthorityError("Preflight payload hash does not match durable intent")
    intent.preflight_receipt_hash = receipt["receipt_hash"]
    intent.status = "APPROVAL_REQUIRED"
    intent.updated_at = _now()
    await _append_evidence(
        db,
        intent_id=intent.id,
        event_type="PREFLIGHT_COMPLETED",
        payload={
            "preflight_receipt_hash": receipt["receipt_hash"],
            "destination": intent.destination,
            "payload_hash": intent.canonical_payload_hash,
            "network_access": False,
            "credential_access": False,
            "production_reachable": False,
            "external_effect": False,
        },
    )
    return await get_external_intent(db, tenant_id=tenant_id, intent_id=intent.id)


async def approve_external_intent(
    db: AsyncSession,
    *,
    tenant_id: str,
    intent_id: str,
    principal_id: str,
    approval_nonce: str,
    expires_at: datetime,
) -> dict[str, Any]:
    intent = await _locked_intent(db, tenant_id=tenant_id, intent_id=intent_id)
    if intent is None:
        raise ExternalActionAuthorityError("External-action intent not found")
    if intent.principal_id != principal_id:
        raise ExternalActionAuthorityError("Only the bound Principal may approve this intent")
    if intent.status != "APPROVAL_REQUIRED" or not intent.preflight_receipt_hash:
        raise ExternalActionAuthorityError("Intent must complete preflight before approval")
    expires_at = _aware(expires_at)
    if expires_at <= _now():
        raise ExternalActionAuthorityError("Approval expiry must be in the future")

    existing = await db.scalar(
        select(ExternalActionApproval).where(ExternalActionApproval.intent_id == intent.id)
    )
    if existing is not None:
        if (
            existing.principal_id != principal_id
            or existing.approval_nonce != approval_nonce
            or existing.canonical_payload_hash != intent.canonical_payload_hash
            or existing.destination != intent.destination
        ):
            raise ExternalActionAuthorityError("Intent already has a different approval binding")
        return await get_external_intent(db, tenant_id=tenant_id, intent_id=intent.id)

    approved_at = _now()
    approval = ExternalActionApproval(
        id=f"apv-{uuid.uuid4().hex[:20]}",
        intent_id=intent.id,
        tenant_id=tenant_id,
        principal_id=principal_id,
        adapter_id=intent.adapter_id,
        operation_id=intent.operation_id,
        destination=intent.destination,
        canonical_payload_hash=intent.canonical_payload_hash,
        approval_nonce=approval_nonce,
        status="APPROVED",
        approved_at=approved_at,
        expires_at=expires_at,
    )
    db.add(approval)
    intent.status = "APPROVED"
    intent.updated_at = approved_at
    await db.flush()
    await _append_evidence(
        db,
        intent_id=intent.id,
        event_type="PRINCIPAL_APPROVAL_BOUND",
        payload={
            "approval_id": approval.id,
            "principal_id": principal_id,
            "adapter_id": intent.adapter_id,
            "operation_id": intent.operation_id,
            "destination": intent.destination,
            "payload_hash": intent.canonical_payload_hash,
            "expires_at": expires_at.isoformat(),
            "external_effect": False,
        },
    )
    return await get_external_intent(db, tenant_id=tenant_id, intent_id=intent.id)


async def revoke_external_approval(
    db: AsyncSession,
    *,
    tenant_id: str,
    intent_id: str,
    principal_id: str,
    reason: str,
) -> None:
    intent = await _locked_intent(db, tenant_id=tenant_id, intent_id=intent_id)
    if intent is None or intent.principal_id != principal_id:
        raise ExternalActionAuthorityError("External-action intent not found for Principal")
    approval = await db.scalar(
        select(ExternalActionApproval).where(
            ExternalActionApproval.intent_id == intent_id,
            ExternalActionApproval.tenant_id == tenant_id,
        )
    )
    if approval is None:
        raise ExternalActionAuthorityError("Approval not found")
    approval.status = "REVOKED"
    approval.revoked_at = _now()
    approval.revocation_reason = reason
    intent.status = "BLOCKED"
    intent.updated_at = _now()
    await _append_evidence(
        db,
        intent_id=intent.id,
        event_type="APPROVAL_REVOKED",
        payload={"reason": reason, "external_effect": False},
    )


async def execute_external_intent(
    db: AsyncSession,
    *,
    tenant_id: str,
    intent_id: str,
    worker_id: str,
    execution_destination: str | None = None,
    execution_payload: dict[str, Any] | None = None,
    simulate_ambiguous_after_write: bool = False,
) -> dict[str, Any]:
    intent = await _locked_intent(db, tenant_id=tenant_id, intent_id=intent_id)
    if intent is None:
        raise ExternalActionAuthorityError("External-action intent not found")
    if intent.status == "SUCCEEDED":
        reconciled = await sandbox_echo_adapter.reconcile_unknown_outcome(
            db,
            tenant_id=tenant_id,
            idempotency_key=intent.idempotency_key,
        )
        if reconciled is None:
            raise ExternalActionAuthorityError("Succeeded intent is missing its sandbox provider effect")
        return {**await _intent_dict(db, intent), "provider": reconciled, "duplicate": True}
    if intent.status != "APPROVED":
        raise ExternalActionAuthorityError(f"Intent is not executable from status {intent.status}")

    destination = execution_destination if execution_destination is not None else intent.destination
    payload = execution_payload if execution_payload is not None else dict(intent.payload)
    _, execution_payload_hash = sandbox_echo_adapter.canonicalize_payload(payload)
    if destination != intent.destination:
        raise ExternalActionAuthorityError("Execution destination differs from Principal-approved destination")
    if execution_payload_hash != intent.canonical_payload_hash:
        raise ExternalActionAuthorityError("Execution payload differs from Principal-approved payload")

    approval = await _validate_authority(db, intent=intent)
    intent.status = "CLAIMED"
    intent.claimed_by = worker_id
    intent.claimed_at = _now()
    intent.updated_at = _now()
    await _append_evidence(
        db,
        intent_id=intent.id,
        event_type="EXECUTION_CLAIMED",
        payload={
            "worker_id": worker_id,
            "approval_id": approval.id,
            "payload_hash": execution_payload_hash,
            "destination": destination,
            "external_effect": False,
        },
    )

    intent.status = "EXECUTING"
    provider_request = {
        "adapter_id": ADAPTER_ID,
        "operation_id": OPERATION_ID,
        "environment": ENVIRONMENT,
        "destination": destination,
        "payload_hash": execution_payload_hash,
        "idempotency_key": intent.idempotency_key,
    }
    intent.provider_request_hash = _canonical_hash(provider_request)
    await _append_evidence(
        db,
        intent_id=intent.id,
        event_type="EXECUTION_ATTEMPTED",
        payload={
            "provider_request_hash": intent.provider_request_hash,
            "external_effect": False,
        },
    )

    provider = await sandbox_echo_adapter.execute_once(
        db,
        tenant_id=tenant_id,
        destination=destination,
        payload=payload,
        idempotency_key=intent.idempotency_key,
    )
    if simulate_ambiguous_after_write:
        intent.status = "UNKNOWN_REQUIRES_RECONCILIATION"
        intent.updated_at = _now()
        await _append_evidence(
            db,
            intent_id=intent.id,
            event_type="PROVIDER_OUTCOME_AMBIGUOUS",
            payload={
                "provider_request_hash": intent.provider_request_hash,
                "automatic_retry_allowed": False,
                "external_effect_possible": True,
            },
        )
        return {**await _intent_dict(db, intent), "provider": None, "ambiguous": True}

    await _record_success(db, intent=intent, provider=provider)
    return {**await _intent_dict(db, intent), "provider": provider, "duplicate": provider["duplicate"]}


async def reconcile_external_intent(
    db: AsyncSession,
    *,
    tenant_id: str,
    intent_id: str,
) -> dict[str, Any]:
    intent = await _locked_intent(db, tenant_id=tenant_id, intent_id=intent_id)
    if intent is None:
        raise ExternalActionAuthorityError("External-action intent not found")
    if intent.status != "UNKNOWN_REQUIRES_RECONCILIATION":
        raise ExternalActionAuthorityError("Only ambiguous outcomes may be reconciled")
    provider = await sandbox_echo_adapter.reconcile_unknown_outcome(
        db,
        tenant_id=tenant_id,
        idempotency_key=intent.idempotency_key,
    )
    if provider is None:
        intent.status = "FAILED"
        intent.updated_at = _now()
        await _append_evidence(
            db,
            intent_id=intent.id,
            event_type="RECONCILIATION_CONFIRMED_NO_EFFECT",
            payload={"external_effect": False},
        )
        return await _intent_dict(db, intent)
    await _record_success(db, intent=intent, provider=provider, reconciled=True)
    return {**await _intent_dict(db, intent), "provider": provider, "reconciled": True}


async def compensate_external_intent(
    db: AsyncSession,
    *,
    tenant_id: str,
    intent_id: str,
    principal_id: str,
    reason: str,
) -> dict[str, Any]:
    intent = await _locked_intent(db, tenant_id=tenant_id, intent_id=intent_id)
    if intent is None or intent.principal_id != principal_id:
        raise ExternalActionAuthorityError("Only the bound Principal may compensate this intent")
    if intent.status != "SUCCEEDED":
        raise ExternalActionAuthorityError("Only a succeeded sandbox effect may be compensated")
    provider = await sandbox_echo_adapter.compensate(
        db,
        tenant_id=tenant_id,
        idempotency_key=intent.idempotency_key,
    )
    if provider is None:
        raise ExternalActionAuthorityError("Sandbox effect is missing and cannot be compensated")
    intent.status = "COMPENSATED"
    intent.updated_at = _now()
    await _append_evidence(
        db,
        intent_id=intent.id,
        event_type="COMPENSATION_COMPLETED",
        payload={
            "reason": reason,
            "effect_id": provider["effect_id"],
            "confirmation_id": provider["confirmation_id"],
            "compensated": True,
            "external_effect": True,
        },
    )
    return {**await _intent_dict(db, intent), "provider": provider}


async def set_external_kill_switch(
    db: AsyncSession,
    *,
    scope_key: str,
    active: bool,
    updated_by: str,
    reason: str,
    tenant_id: str | None = None,
    adapter_id: str | None = None,
) -> None:
    record = await db.get(ExternalExecutionKillSwitch, scope_key)
    if record is None:
        record = ExternalExecutionKillSwitch(
            scope_key=scope_key,
            tenant_id=tenant_id,
            adapter_id=adapter_id,
            active=active,
            reason=reason,
            updated_by=updated_by,
            updated_at=_now(),
        )
        db.add(record)
    else:
        record.active = active
        record.reason = reason
        record.updated_by = updated_by
        record.updated_at = _now()
    await db.flush()


async def verify_external_evidence_chain(
    db: AsyncSession,
    *,
    tenant_id: str,
    intent_id: str,
) -> dict[str, Any]:
    intent = await db.scalar(
        select(ExternalActionIntent).where(
            ExternalActionIntent.id == intent_id,
            ExternalActionIntent.tenant_id == tenant_id,
        )
    )
    if intent is None:
        raise ExternalActionAuthorityError("External-action intent not found")
    events = list(
        (
            await db.scalars(
                select(ExternalActionEvidence)
                .where(ExternalActionEvidence.intent_id == intent_id)
                .order_by(ExternalActionEvidence.sequence_no)
            )
        ).all()
    )
    previous_hash: str | None = None
    for expected_sequence, event in enumerate(events, start=1):
        if event.sequence_no != expected_sequence or event.previous_event_hash != previous_hash:
            raise ExternalActionAuthorityError("External-action evidence chain linkage is invalid")
        expected_hash = _canonical_hash(
            {
                "intent_id": intent_id,
                "sequence_no": event.sequence_no,
                "event_type": event.event_type,
                "event_payload": dict(event.event_payload),
                "previous_event_hash": event.previous_event_hash,
                "created_at": _aware(event.created_at).isoformat(),
            }
        )
        if event.event_hash != expected_hash:
            raise ExternalActionAuthorityError("External-action evidence hash is invalid")
        previous_hash = event.event_hash
    return {
        "intent_id": intent_id,
        "event_count": len(events),
        "head_hash": previous_hash,
        "valid": True,
    }


async def get_external_intent(
    db: AsyncSession,
    *,
    tenant_id: str,
    intent_id: str,
) -> dict[str, Any] | None:
    intent = await db.scalar(
        select(ExternalActionIntent).where(
            ExternalActionIntent.id == intent_id,
            ExternalActionIntent.tenant_id == tenant_id,
        )
    )
    return await _intent_dict(db, intent) if intent is not None else None


async def _locked_intent(
    db: AsyncSession,
    *,
    tenant_id: str,
    intent_id: str,
) -> ExternalActionIntent | None:
    return await db.scalar(
        select(ExternalActionIntent)
        .where(
            ExternalActionIntent.id == intent_id,
            ExternalActionIntent.tenant_id == tenant_id,
        )
        .with_for_update()
    )


async def _validate_authority(
    db: AsyncSession,
    *,
    intent: ExternalActionIntent,
) -> ExternalActionApproval:
    if intent.adapter_id != ADAPTER_ID or intent.operation_id != OPERATION_ID:
        raise ExternalActionAuthorityError("Adapter or operation is not Gate 4B allowlisted")
    if intent.environment != ENVIRONMENT or intent.risk_class != RISK_CLASS:
        raise ExternalActionAuthorityError("Only E1 sandbox execution is permitted")
    await _assert_kill_switches_clear(db, intent=intent)

    identity = await db.scalar(
        select(GovernedServiceIdentityRecord).where(
            GovernedServiceIdentityRecord.id == intent.service_identity_id,
            GovernedServiceIdentityRecord.tenant_id == intent.tenant_id,
        )
    )
    if identity is None or identity.status != "ACTIVE":
        raise ExternalActionAuthorityError("Durable service identity is missing or revoked")
    if _aware(identity.expires_at) <= _now():
        raise ExternalActionAuthorityError("Durable service identity has expired")
    if REQUIRED_CAPABILITY not in list(identity.allowed_capabilities or []):
        raise ExternalActionAuthorityError("Service identity lacks the exact sandbox adapter capability")
    scoped = list(identity.scoped_folders or [])
    if scoped and intent.destination not in scoped:
        raise ExternalActionAuthorityError("Destination is outside the service identity resource scope")

    approval = await db.scalar(
        select(ExternalActionApproval).where(
            ExternalActionApproval.intent_id == intent.id,
            ExternalActionApproval.tenant_id == intent.tenant_id,
        )
    )
    if approval is None or approval.status != "APPROVED":
        raise ExternalActionAuthorityError("Principal approval is missing or revoked")
    if _aware(approval.expires_at) <= _now():
        raise ExternalActionAuthorityError("Principal approval has expired")
    if (
        approval.principal_id != intent.principal_id
        or approval.adapter_id != intent.adapter_id
        or approval.operation_id != intent.operation_id
        or approval.destination != intent.destination
        or approval.canonical_payload_hash != intent.canonical_payload_hash
    ):
        raise ExternalActionAuthorityError("Principal approval binding no longer matches the intent")
    return approval


async def _assert_kill_switches_clear(
    db: AsyncSession,
    *,
    intent: ExternalActionIntent,
) -> None:
    keys = (
        "GLOBAL",
        f"TENANT:{intent.tenant_id}",
        f"ADAPTER:{intent.adapter_id}",
    )
    switches = list(
        (
            await db.scalars(
                select(ExternalExecutionKillSwitch).where(
                    ExternalExecutionKillSwitch.scope_key.in_(keys),
                    ExternalExecutionKillSwitch.active.is_(True),
                )
            )
        ).all()
    )
    if switches:
        raise ExternalActionAuthorityError(
            "External execution is disabled by kill switch: "
            + ",".join(sorted(record.scope_key for record in switches))
        )


async def _record_success(
    db: AsyncSession,
    *,
    intent: ExternalActionIntent,
    provider: dict[str, Any],
    reconciled: bool = False,
) -> None:
    provider_response = {
        "effect_id": provider["effect_id"],
        "confirmation_id": provider["confirmation_id"],
        "payload_hash": provider["payload_hash"],
        "destination": provider["destination"],
    }
    intent.provider_response_hash = canonical_json_hash(provider_response)
    intent.provider_confirmation_id = provider["confirmation_id"]
    intent.status = "SUCCEEDED"
    intent.updated_at = _now()
    await _append_evidence(
        db,
        intent_id=intent.id,
        event_type="RECONCILIATION_CONFIRMED_EFFECT" if reconciled else "EXECUTION_SUCCEEDED",
        payload={
            "provider_response_hash": intent.provider_response_hash,
            "provider_confirmation_id": intent.provider_confirmation_id,
            "effect_id": provider["effect_id"],
            "external_effect": True,
            "reconciled": reconciled,
        },
    )


async def _intent_dict(
    db: AsyncSession,
    intent: ExternalActionIntent,
) -> dict[str, Any]:
    events = list(
        (
            await db.scalars(
                select(ExternalActionEvidence)
                .where(ExternalActionEvidence.intent_id == intent.id)
                .order_by(ExternalActionEvidence.sequence_no)
            )
        ).all()
    )
    approval = await db.scalar(
        select(ExternalActionApproval).where(ExternalActionApproval.intent_id == intent.id)
    )
    return {
        "intent_id": intent.id,
        "tenant_id": intent.tenant_id,
        "principal_id": intent.principal_id,
        "service_identity_id": intent.service_identity_id,
        "mission_id": intent.mission_id,
        "schedule_id": intent.schedule_id,
        "adapter_id": intent.adapter_id,
        "operation_id": intent.operation_id,
        "environment": intent.environment,
        "destination": intent.destination,
        "risk_class": intent.risk_class,
        "payload": dict(intent.payload),
        "canonical_payload_hash": intent.canonical_payload_hash,
        "idempotency_key": intent.idempotency_key,
        "status": intent.status,
        "preflight_receipt_hash": intent.preflight_receipt_hash,
        "provider_request_hash": intent.provider_request_hash,
        "provider_response_hash": intent.provider_response_hash,
        "provider_confirmation_id": intent.provider_confirmation_id,
        "approval": (
            {
                "approval_id": approval.id,
                "status": approval.status,
                "payload_hash": approval.canonical_payload_hash,
                "destination": approval.destination,
                "expires_at": _aware(approval.expires_at).isoformat(),
            }
            if approval is not None
            else None
        ),
        "events": [
            {
                "sequence_no": event.sequence_no,
                "event_type": event.event_type,
                "event_payload": dict(event.event_payload),
                "previous_event_hash": event.previous_event_hash,
                "event_hash": event.event_hash,
            }
            for event in events
        ],
    }

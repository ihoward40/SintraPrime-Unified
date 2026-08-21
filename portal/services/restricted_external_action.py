"""Canonical durable restricted external-action authority for Gates 4B and 4C.

This module remains the single execution authority. Protocol adapters may validate,
translate and perform provider I/O, but they cannot mint approval, widen scope,
select credentials, bypass rate limits, or own durable lifecycle state.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.external_action_sandbox import (
    ExternalActionApproval,
    ExternalActionEvidence,
    ExternalActionIntent,
    ExternalExecutionKillSwitch,
    ExternalProviderAttempt,
    ExternalProviderCredentialLease,
    ExternalProviderRateBucket,
)
from ..models.governed_service_identity import GovernedServiceIdentityRecord
from .postman_echo_provider_adapter import (
    ADAPTER_ID as POSTMAN_ADAPTER_ID,
    APPROVED_URL as POSTMAN_APPROVED_URL,
    ENVIRONMENT as POSTMAN_ENVIRONMENT,
    OPERATION_ID as POSTMAN_OPERATION_ID,
    ProviderBoundaryError,
    postman_echo_provider_adapter,
)
from .sandbox_echo_adapter import (
    ADAPTER_ID as SANDBOX_ADAPTER_ID,
    ENVIRONMENT as SANDBOX_ENVIRONMENT,
    OPERATION_ID as SANDBOX_OPERATION_ID,
    canonical_json_hash,
    sandbox_echo_adapter,
)

RISK_CLASS = "E1"


class ExternalActionAuthorityError(RuntimeError):
    """Raised whenever restricted external-action authority fails closed."""


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


def _adapter_spec(adapter_id: str) -> dict[str, Any]:
    if adapter_id == SANDBOX_ADAPTER_ID:
        return {
            "adapter": sandbox_echo_adapter,
            "adapter_id": SANDBOX_ADAPTER_ID,
            "operation_id": SANDBOX_OPERATION_ID,
            "environment": SANDBOX_ENVIRONMENT,
            "risk_class": RISK_CLASS,
            "credential_required": False,
            "capability": f"external:{SANDBOX_ADAPTER_ID}:{SANDBOX_OPERATION_ID}",
        }
    if adapter_id == POSTMAN_ADAPTER_ID:
        return {
            "adapter": postman_echo_provider_adapter,
            "adapter_id": POSTMAN_ADAPTER_ID,
            "operation_id": POSTMAN_OPERATION_ID,
            "environment": POSTMAN_ENVIRONMENT,
            "risk_class": RISK_CLASS,
            "credential_required": True,
            "capability": f"external:{POSTMAN_ADAPTER_ID}:{POSTMAN_OPERATION_ID}",
        }
    raise ExternalActionAuthorityError("Adapter is not allowlisted by the restricted authority")


def _request_hash(
    *,
    tenant_id: str,
    principal_id: str,
    service_identity_id: str,
    adapter_id: str,
    operation_id: str,
    environment: str,
    destination: str,
    payload_hash: str,
    idempotency_key: str,
    credential_lease_id: str | None,
    mission_id: str | None,
    schedule_id: str | None,
) -> str:
    return _canonical_hash(
        {
            "tenant_id": tenant_id,
            "principal_id": principal_id,
            "service_identity_id": service_identity_id,
            "adapter_id": adapter_id,
            "operation_id": operation_id,
            "environment": environment,
            "destination": destination,
            "risk_class": RISK_CLASS,
            "payload_hash": payload_hash,
            "idempotency_key": idempotency_key,
            "credential_lease_id": credential_lease_id,
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


async def issue_provider_credential_lease(
    db: AsyncSession,
    *,
    tenant_id: str,
    principal_id: str,
    service_identity_id: str,
    credential_ref: str,
    destination: str = POSTMAN_APPROVED_URL,
    expires_at: datetime,
    rate_limit_per_minute: int = 5,
) -> dict[str, Any]:
    spec = _adapter_spec(POSTMAN_ADAPTER_ID)
    spec["adapter"].validate_destination(destination)
    if not credential_ref.startswith("env:"):
        raise ExternalActionAuthorityError("Gate 4C credential references must use the env: resolver")
    material = _resolve_credential_ref(credential_ref)
    expires_at = _aware(expires_at)
    if expires_at <= _now():
        raise ExternalActionAuthorityError("Credential lease expiry must be in the future")
    if not 1 <= rate_limit_per_minute <= 60:
        raise ExternalActionAuthorityError("Credential lease rate limit is outside Gate 4C bounds")
    identity = await db.scalar(
        select(GovernedServiceIdentityRecord).where(
            GovernedServiceIdentityRecord.id == service_identity_id,
            GovernedServiceIdentityRecord.tenant_id == tenant_id,
        )
    )
    if identity is None or identity.status != "ACTIVE":
        raise ExternalActionAuthorityError("Credential lease requires an active service identity")
    if _aware(identity.expires_at) <= _now():
        raise ExternalActionAuthorityError("Credential lease service identity has expired")
    if spec["capability"] not in list(identity.allowed_capabilities or []):
        raise ExternalActionAuthorityError("Service identity lacks the provider-test capability")
    scoped = list(identity.scoped_folders or [])
    if scoped and destination not in scoped:
        raise ExternalActionAuthorityError("Credential lease destination exceeds identity scope")

    lease = ExternalProviderCredentialLease(
        id=f"lease-{uuid.uuid4().hex[:20]}",
        tenant_id=tenant_id,
        principal_id=principal_id,
        service_identity_id=service_identity_id,
        adapter_id=POSTMAN_ADAPTER_ID,
        environment=POSTMAN_ENVIRONMENT,
        destination=destination,
        credential_ref=credential_ref,
        credential_fingerprint=hashlib.sha256(material.encode()).hexdigest(),
        status="ACTIVE",
        issued_at=_now(),
        expires_at=expires_at,
        rate_limit_per_minute=rate_limit_per_minute,
        updated_at=_now(),
    )
    db.add(lease)
    await db.flush()
    return _lease_dict(lease)


async def revoke_provider_credential_lease(
    db: AsyncSession,
    *,
    tenant_id: str,
    lease_id: str,
    principal_id: str,
    reason: str,
) -> None:
    lease = await db.scalar(
        select(ExternalProviderCredentialLease)
        .where(
            ExternalProviderCredentialLease.id == lease_id,
            ExternalProviderCredentialLease.tenant_id == tenant_id,
        )
        .with_for_update()
    )
    if lease is None or lease.principal_id != principal_id:
        raise ExternalActionAuthorityError("Credential lease not found for Principal")
    lease.status = "REVOKED"
    lease.revoked_at = _now()
    lease.revocation_reason = reason
    lease.updated_at = _now()
    await db.flush()


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
    adapter_id: str = SANDBOX_ADAPTER_ID,
    credential_lease_id: str | None = None,
) -> dict[str, Any]:
    spec = _adapter_spec(adapter_id)
    adapter = spec["adapter"]
    adapter.validate_destination(destination)
    canonical_payload, payload_hash = adapter.canonicalize_payload(payload)
    if spec["credential_required"] and not credential_lease_id:
        raise ExternalActionAuthorityError("Provider-test intent requires a durable credential lease")
    if not spec["credential_required"] and credential_lease_id is not None:
        raise ExternalActionAuthorityError("Sandbox intent cannot attach a provider credential lease")

    request_hash = _request_hash(
        tenant_id=tenant_id,
        principal_id=principal_id,
        service_identity_id=service_identity_id,
        adapter_id=spec["adapter_id"],
        operation_id=spec["operation_id"],
        environment=spec["environment"],
        destination=destination,
        payload_hash=payload_hash,
        idempotency_key=idempotency_key,
        credential_lease_id=credential_lease_id,
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
        adapter_id=spec["adapter_id"],
        operation_id=spec["operation_id"],
        environment=spec["environment"],
        destination=destination,
        risk_class=spec["risk_class"],
        payload=canonical_payload,
        canonical_payload_hash=payload_hash,
        request_hash=request_hash,
        payload_summary=payload_summary,
        idempotency_key=idempotency_key,
        credential_ref=credential_lease_id,
        status="DRAFT",
    )
    db.add(intent)
    await db.flush()
    await _append_evidence(
        db,
        intent_id=intent.id,
        event_type="INTENT_CREATED",
        payload={
            "adapter_id": intent.adapter_id,
            "operation_id": intent.operation_id,
            "environment": intent.environment,
            "destination": destination,
            "payload_hash": payload_hash,
            "risk_class": RISK_CLASS,
            "credential_lease_id": credential_lease_id,
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
    spec = _adapter_spec(intent.adapter_id)
    receipt = spec["adapter"].preflight(destination=intent.destination, payload=dict(intent.payload))
    if receipt["payload_hash"] != intent.canonical_payload_hash:
        raise ExternalActionAuthorityError("Preflight payload hash does not match durable intent")
    if spec["credential_required"]:
        await _validate_provider_credential_lease(db, intent=intent)
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
            "network_access": bool(receipt["network_access"]),
            "credential_access": bool(receipt["credential_access"]),
            "production_reachable": bool(receipt["production_reachable"]),
            "provider_rollback_required": receipt.get("provider_rollback_required"),
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
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    intent = await _locked_intent(db, tenant_id=tenant_id, intent_id=intent_id)
    if intent is None:
        raise ExternalActionAuthorityError("External-action intent not found")
    spec = _adapter_spec(intent.adapter_id)

    if intent.status == "SUCCEEDED":
        return await _replay_succeeded_intent(db, intent=intent)
    if intent.status == "UNKNOWN_REQUIRES_RECONCILIATION":
        raise ExternalActionAuthorityError("Ambiguous provider outcome requires reconciliation before replay")
    if intent.status != "APPROVED":
        raise ExternalActionAuthorityError(f"Intent is not executable from status {intent.status}")

    destination = execution_destination if execution_destination is not None else intent.destination
    payload = execution_payload if execution_payload is not None else dict(intent.payload)
    _, execution_payload_hash = spec["adapter"].canonicalize_payload(payload)
    if destination != intent.destination:
        raise ExternalActionAuthorityError("Execution destination differs from Principal-approved destination")
    if execution_payload_hash != intent.canonical_payload_hash:
        raise ExternalActionAuthorityError("Execution payload differs from Principal-approved payload")

    approval, lease, credential_material = await _validate_authority(db, intent=intent)
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
            "credential_lease_id": lease.id if lease is not None else None,
            "payload_hash": execution_payload_hash,
            "destination": destination,
            "external_effect": False,
        },
    )

    provider_request = {
        "adapter_id": intent.adapter_id,
        "operation_id": intent.operation_id,
        "environment": intent.environment,
        "destination": destination,
        "payload_hash": execution_payload_hash,
        "idempotency_key": intent.idempotency_key,
        "credential_lease_id": lease.id if lease is not None else None,
    }
    intent.provider_request_hash = _canonical_hash(provider_request)

    if intent.adapter_id == POSTMAN_ADAPTER_ID:
        assert lease is not None
        try:
            await _consume_provider_rate_limit(db, intent=intent, lease=lease)
        except ExternalActionAuthorityError:
            intent.status = "APPROVED"
            intent.updated_at = _now()
            await _append_evidence(
                db,
                intent_id=intent.id,
                event_type="LOCAL_RATE_LIMIT_BLOCKED",
                payload={
                    "provider_request_hash": intent.provider_request_hash,
                    "external_effect": False,
                },
            )
            raise

    intent.status = "EXECUTING"
    await _append_evidence(
        db,
        intent_id=intent.id,
        event_type="EXECUTION_ATTEMPTED",
        payload={
            "provider_request_hash": intent.provider_request_hash,
            "credential_lease_id": lease.id if lease is not None else None,
            "external_effect": False,
        },
    )

    if intent.adapter_id == SANDBOX_ADAPTER_ID:
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
        await _record_sandbox_success(db, intent=intent, provider=provider)
        return {**await _intent_dict(db, intent), "provider": provider, "duplicate": provider["duplicate"]}

    attempt = await _create_provider_attempt(db, intent=intent, lease=lease)
    if simulate_ambiguous_after_write:
        attempt.outcome = "AMBIGUOUS"
        attempt.completed_at = _now()
        intent.status = "UNKNOWN_REQUIRES_RECONCILIATION"
        intent.updated_at = _now()
        await _append_evidence(
            db,
            intent_id=intent.id,
            event_type="PROVIDER_OUTCOME_AMBIGUOUS",
            payload={
                "attempt_id": attempt.id,
                "provider_request_hash": intent.provider_request_hash,
                "automatic_retry_allowed": False,
                "provider_persistent_state": False,
                "external_effect_possible": False,
            },
        )
        return {**await _intent_dict(db, intent), "provider": None, "ambiguous": True}

    try:
        receipt = await postman_echo_provider_adapter.execute_once(
            payload=payload,
            credential_header=f"Bearer {credential_material}",
            timeout_seconds=timeout_seconds,
            destination=destination,
        )
    except TimeoutError:
        attempt.outcome = "AMBIGUOUS"
        attempt.completed_at = _now()
        intent.status = "UNKNOWN_REQUIRES_RECONCILIATION"
        intent.updated_at = _now()
        await _append_evidence(
            db,
            intent_id=intent.id,
            event_type="PROVIDER_OUTCOME_AMBIGUOUS",
            payload={
                "attempt_id": attempt.id,
                "provider_request_hash": intent.provider_request_hash,
                "automatic_retry_allowed": False,
                "provider_persistent_state": False,
                "external_effect_possible": False,
                "reason": "timeout",
            },
        )
        return {**await _intent_dict(db, intent), "provider": None, "ambiguous": True}
    except ProviderBoundaryError as exc:
        attempt.outcome = "RATE_LIMITED" if "429" in str(exc) else "FAILED"
        attempt.completed_at = _now()
        intent.status = "FAILED"
        intent.updated_at = _now()
        await _append_evidence(
            db,
            intent_id=intent.id,
            event_type="PROVIDER_RATE_LIMITED" if attempt.outcome == "RATE_LIMITED" else "PROVIDER_FAILED",
            payload={
                "attempt_id": attempt.id,
                "provider_request_hash": intent.provider_request_hash,
                "reason": str(exc),
                "automatic_retry_allowed": False,
                "external_effect": False,
            },
        )
        raise ExternalActionAuthorityError(str(exc)) from exc

    await _record_provider_success(db, intent=intent, attempt=attempt, receipt=receipt)
    return {
        **await _intent_dict(db, intent),
        "provider": _provider_receipt_dict(attempt),
        "duplicate": False,
    }


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

    if intent.adapter_id == SANDBOX_ADAPTER_ID:
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
        await _record_sandbox_success(db, intent=intent, provider=provider, reconciled=True)
        return {**await _intent_dict(db, intent), "provider": provider, "reconciled": True}

    attempt = await _latest_provider_attempt(db, intent.id)
    if attempt is None or attempt.outcome != "AMBIGUOUS":
        raise ExternalActionAuthorityError("Ambiguous provider attempt ledger is missing")
    intent.status = "FAILED"
    intent.updated_at = _now()
    await _append_evidence(
        db,
        intent_id=intent.id,
        event_type="RECONCILIATION_CONFIRMED_NO_PERSISTENT_PROVIDER_STATE",
        payload={
            "attempt_id": attempt.id,
            "provider_persistent_state": False,
            "provider_rollback_required": False,
            "automatic_retry_allowed": False,
            "network_retry_performed": False,
            "external_effect": False,
        },
    )
    return {**await _intent_dict(db, intent), "provider": None, "reconciled": True}


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
        raise ExternalActionAuthorityError("Only a succeeded restricted action may be compensated")

    if intent.adapter_id == SANDBOX_ADAPTER_ID:
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
                "provider_rollback_required": True,
                "external_effect": True,
            },
        )
        return {**await _intent_dict(db, intent), "provider": provider}

    attempt = await _latest_provider_attempt(db, intent.id)
    if attempt is None or attempt.outcome != "SUCCEEDED":
        raise ExternalActionAuthorityError("Provider receipt is missing and cannot be logically compensated")
    intent.status = "COMPENSATED"
    intent.updated_at = _now()
    await _append_evidence(
        db,
        intent_id=intent.id,
        event_type="COMPENSATION_COMPLETED",
        payload={
            "reason": reason,
            "logical_compensation": True,
            "provider_rollback_required": False,
            "provider_persistent_state": False,
            "network_call_performed": False,
            "external_effect": False,
        },
    )
    return {
        **await _intent_dict(db, intent),
        "provider": _provider_receipt_dict(attempt),
        "logical_compensation": True,
    }


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
) -> tuple[ExternalActionApproval, ExternalProviderCredentialLease | None, str | None]:
    spec = _adapter_spec(intent.adapter_id)
    if intent.operation_id != spec["operation_id"]:
        raise ExternalActionAuthorityError("Adapter operation is not allowlisted")
    if intent.environment != spec["environment"] or intent.risk_class != spec["risk_class"]:
        raise ExternalActionAuthorityError("External action environment or risk class is not allowlisted")
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
    if spec["capability"] not in list(identity.allowed_capabilities or []):
        raise ExternalActionAuthorityError("Service identity lacks the exact adapter capability")
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

    if not spec["credential_required"]:
        return approval, None, None
    lease, material = await _validate_provider_credential_lease(db, intent=intent)
    return approval, lease, material


async def _validate_provider_credential_lease(
    db: AsyncSession,
    *,
    intent: ExternalActionIntent,
) -> tuple[ExternalProviderCredentialLease, str]:
    if not intent.credential_ref:
        raise ExternalActionAuthorityError("Provider-test intent is missing its credential lease")
    lease = await db.scalar(
        select(ExternalProviderCredentialLease).where(
            ExternalProviderCredentialLease.id == intent.credential_ref,
            ExternalProviderCredentialLease.tenant_id == intent.tenant_id,
        )
    )
    if lease is None or lease.status != "ACTIVE":
        raise ExternalActionAuthorityError("Provider credential lease is missing or revoked")
    if _aware(lease.expires_at) <= _now():
        raise ExternalActionAuthorityError("Provider credential lease has expired")
    if (
        lease.principal_id != intent.principal_id
        or lease.service_identity_id != intent.service_identity_id
        or lease.adapter_id != intent.adapter_id
        or lease.environment != intent.environment
        or lease.destination != intent.destination
    ):
        raise ExternalActionAuthorityError("Provider credential lease binding does not match intent")
    material = _resolve_credential_ref(lease.credential_ref)
    if hashlib.sha256(material.encode()).hexdigest() != lease.credential_fingerprint:
        raise ExternalActionAuthorityError("Provider credential material fingerprint changed after lease")
    return lease, material


def _resolve_credential_ref(credential_ref: str) -> str:
    if not credential_ref.startswith("env:"):
        raise ExternalActionAuthorityError("Unsupported provider credential resolver")
    env_name = credential_ref.removeprefix("env:")
    if not env_name or not env_name.startswith("GATE4C_"):
        raise ExternalActionAuthorityError("Provider credential reference is outside Gate 4C namespace")
    value = os.environ.get(env_name)
    if not value:
        raise ExternalActionAuthorityError("Provider credential material is unavailable")
    return value


async def _consume_provider_rate_limit(
    db: AsyncSession,
    *,
    intent: ExternalActionIntent,
    lease: ExternalProviderCredentialLease,
) -> None:
    now = _now()
    window = now.replace(second=0, microsecond=0)
    scope_key = f"{intent.tenant_id}:{intent.adapter_id}:{window.isoformat()}"
    await db.execute(
        text(
            """
            INSERT INTO external_provider_rate_buckets (
                scope_key, tenant_id, adapter_id, window_started_at,
                request_count, limit_count, updated_at
            ) VALUES (
                :scope_key, CAST(:tenant_id AS uuid), :adapter_id, :window_started_at,
                0, :limit_count, :updated_at
            ) ON CONFLICT (scope_key) DO NOTHING
            """
        ),
        {
            "scope_key": scope_key,
            "tenant_id": str(intent.tenant_id),
            "adapter_id": intent.adapter_id,
            "window_started_at": window,
            "limit_count": lease.rate_limit_per_minute,
            "updated_at": now,
        },
    )
    bucket = await db.scalar(
        select(ExternalProviderRateBucket)
        .where(ExternalProviderRateBucket.scope_key == scope_key)
        .with_for_update()
    )
    if bucket is None:
        raise ExternalActionAuthorityError("Provider rate bucket could not be established")
    if bucket.request_count >= bucket.limit_count:
        raise ExternalActionAuthorityError("Durable provider rate limit exceeded")
    bucket.request_count += 1
    bucket.updated_at = now
    await db.flush()


async def _create_provider_attempt(
    db: AsyncSession,
    *,
    intent: ExternalActionIntent,
    lease: ExternalProviderCredentialLease | None,
) -> ExternalProviderAttempt:
    current = await db.scalar(
        select(func.max(ExternalProviderAttempt.attempt_no)).where(
            ExternalProviderAttempt.intent_id == intent.id
        )
    )
    attempt = ExternalProviderAttempt(
        id=str(uuid.uuid4()),
        intent_id=intent.id,
        tenant_id=intent.tenant_id,
        adapter_id=intent.adapter_id,
        credential_lease_id=lease.id if lease is not None else None,
        attempt_no=(current or 0) + 1,
        request_hash=intent.provider_request_hash or "",
        outcome="ATTEMPTED",
        started_at=_now(),
    )
    db.add(attempt)
    await db.flush()
    return attempt


async def _latest_provider_attempt(
    db: AsyncSession,
    intent_id: str,
) -> ExternalProviderAttempt | None:
    return await db.scalar(
        select(ExternalProviderAttempt)
        .where(ExternalProviderAttempt.intent_id == intent_id)
        .order_by(ExternalProviderAttempt.attempt_no.desc())
        .limit(1)
    )


async def _record_provider_success(
    db: AsyncSession,
    *,
    intent: ExternalActionIntent,
    attempt: ExternalProviderAttempt,
    receipt: Any,
) -> None:
    attempt.response_hash = receipt.response_hash
    attempt.provider_status = receipt.status
    attempt.provider_url = receipt.provider_url
    attempt.resolved_ips = list(receipt.resolved_ips)
    attempt.outcome = "SUCCEEDED"
    attempt.completed_at = _now()
    intent.provider_response_hash = receipt.response_hash
    intent.provider_confirmation_id = f"postman-{receipt.response_hash[:20]}"
    intent.status = "SUCCEEDED"
    intent.updated_at = _now()
    await _append_evidence(
        db,
        intent_id=intent.id,
        event_type="EXECUTION_SUCCEEDED",
        payload={
            "attempt_id": attempt.id,
            "provider_request_hash": intent.provider_request_hash,
            "provider_response_hash": receipt.response_hash,
            "provider_status": receipt.status,
            "provider_url": receipt.provider_url,
            "resolved_ips": list(receipt.resolved_ips),
            "provider_persistent_state": False,
            "provider_rollback_required": False,
            "external_effect": False,
        },
    )


async def _record_sandbox_success(
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


async def _replay_succeeded_intent(
    db: AsyncSession,
    *,
    intent: ExternalActionIntent,
) -> dict[str, Any]:
    if intent.adapter_id == SANDBOX_ADAPTER_ID:
        reconciled = await sandbox_echo_adapter.reconcile_unknown_outcome(
            db,
            tenant_id=str(intent.tenant_id),
            idempotency_key=intent.idempotency_key,
        )
        if reconciled is None:
            raise ExternalActionAuthorityError("Succeeded intent is missing its sandbox provider effect")
        return {**await _intent_dict(db, intent), "provider": reconciled, "duplicate": True}
    attempt = await _latest_provider_attempt(db, intent.id)
    if attempt is None or attempt.outcome != "SUCCEEDED":
        raise ExternalActionAuthorityError("Succeeded provider intent is missing its durable receipt")
    return {
        **await _intent_dict(db, intent),
        "provider": _provider_receipt_dict(attempt),
        "duplicate": True,
    }


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


def _lease_dict(lease: ExternalProviderCredentialLease) -> dict[str, Any]:
    return {
        "lease_id": lease.id,
        "tenant_id": lease.tenant_id,
        "principal_id": lease.principal_id,
        "service_identity_id": lease.service_identity_id,
        "adapter_id": lease.adapter_id,
        "environment": lease.environment,
        "destination": lease.destination,
        "credential_ref": lease.credential_ref,
        "credential_fingerprint": lease.credential_fingerprint,
        "status": lease.status,
        "expires_at": _aware(lease.expires_at).isoformat(),
        "rate_limit_per_minute": lease.rate_limit_per_minute,
    }


def _provider_receipt_dict(attempt: ExternalProviderAttempt) -> dict[str, Any]:
    return {
        "attempt_id": attempt.id,
        "attempt_no": attempt.attempt_no,
        "request_hash": attempt.request_hash,
        "response_hash": attempt.response_hash,
        "provider_status": attempt.provider_status,
        "provider_url": attempt.provider_url,
        "resolved_ips": list(attempt.resolved_ips or []),
        "outcome": attempt.outcome,
        "provider_persistent_state": False,
        "provider_rollback_required": False,
    }


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
        "credential_lease_id": intent.credential_ref,
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

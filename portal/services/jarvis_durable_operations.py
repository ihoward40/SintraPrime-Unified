from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from portal.models.jarvis_b2_durability import JarvisOperationRecord
from portal.services.jarvis_verification_reconciliation import (
    OperationRecord,
    OperationState,
    VerificationStatus,
    idempotency_key,
)


class DurableOperationRepository:
    """Canonical B2 operation state repository; no process-local authority fallback."""

    backend = "DURABLE"

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_or_get(self, *, action_id: str, attempt_id: str, tenant_id: str, capability_contract_hash: str, lease_id: str, credential_grant_id: str, operation: str, target: str, params_hash: str, now: datetime | None = None) -> OperationRecord:
        key = idempotency_key(tenant_id=tenant_id, action_id=action_id, capability_contract_hash=capability_contract_hash, operation=operation, target=target, params_hash=params_hash)
        row = await self.session.scalar(select(JarvisOperationRecord).where(JarvisOperationRecord.idempotency_key == key))
        if row is None:
            moment = now or datetime.now(UTC)
            row = JarvisOperationRecord(operation_id=__import__("uuid").uuid4().hex, action_id=action_id, attempt_id=attempt_id, tenant_id=tenant_id, capability_contract_hash=capability_contract_hash, lease_id=lease_id, credential_grant_id=credential_grant_id, operation=operation, target=target, params_hash=params_hash, idempotency_key=key, state=OperationState.PENDING.value, created_at=moment, updated_at=moment, revision=0)
            self.session.add(row)
            await self.session.flush()
        return self._to_value(row)

    async def recover(self, operation_id: str, *, tenant_id: str) -> OperationRecord | None:
        row = await self.session.scalar(select(JarvisOperationRecord).where(
            JarvisOperationRecord.operation_id == operation_id,
            JarvisOperationRecord.tenant_id == tenant_id,
        ))
        return self._to_value(row) if row else None

    async def mark_unknown(self, operation_id: str, *, tenant_id: str, provider_operation_ref: str | None = None) -> OperationRecord:
        result = await self.session.execute(update(JarvisOperationRecord).where(
            JarvisOperationRecord.operation_id == operation_id,
            JarvisOperationRecord.tenant_id == tenant_id,
        ).values(state=OperationState.UNKNOWN.value, latest_verification_status=VerificationStatus.SIDE_EFFECT_UNKNOWN.value, provider_operation_ref=provider_operation_ref, revision=JarvisOperationRecord.revision + 1, updated_at=datetime.now(UTC)))
        if result.rowcount != 1:
            raise LookupError("OPERATION_NOT_FOUND_IN_TENANT")
        await self.session.flush()
        return await self.recover(operation_id, tenant_id=tenant_id)

    @staticmethod
    def _to_value(row: Any) -> OperationRecord:
        return OperationRecord(operation_id=row.operation_id, action_id=row.action_id, tenant_id=row.tenant_id, capability_contract_hash=row.capability_contract_hash, lease_id=row.lease_id, credential_grant_id=row.credential_grant_id, operation=row.operation, target=row.target, params_hash=row.params_hash, idempotency_key=row.idempotency_key, state=OperationState(row.state), created_at=row.created_at, attempted_at=row.attempted_at, verified_at=row.verified_at, reconciled_at=row.reconciled_at, provider_operation_ref=row.provider_operation_ref, latest_verification_status=VerificationStatus(row.latest_verification_status) if row.latest_verification_status else None, revision=row.revision)


class DurableReconciler(DurableOperationRepository):
    """Canonical runtime reconciler facade; durable repository is mandatory."""

    backend = "DURABLE"

    async def create_or_get(self, **kwargs):
        return await super().create_or_get(**kwargs)

    async def mark_attempting(self, operation_id: str, *, tenant_id: str) -> OperationRecord:
        """Record that the external mutation attempt is starting (crash window begins)."""
        result = await self.session.execute(update(JarvisOperationRecord).where(
            JarvisOperationRecord.operation_id == operation_id,
            JarvisOperationRecord.tenant_id == tenant_id,
            JarvisOperationRecord.state == OperationState.PENDING.value,
        ).values(state=OperationState.ATTEMPTING.value, attempted_at=datetime.now(UTC), revision=JarvisOperationRecord.revision + 1, updated_at=datetime.now(UTC)))
        if result.rowcount != 1:
            raise LookupError("OPERATION_NOT_PENDING_IN_TENANT")
        await self.session.flush()
        return await self.recover(operation_id, tenant_id=tenant_id)

    async def complete_verification(self, operation_id: str, *, tenant_id: str, state: OperationState, verification_status: VerificationStatus) -> OperationRecord:
        """Persist verification outcome (RECONCILING -> RECONCILED recovery closes UNKNOWN)."""
        if state not in {OperationState.VERIFIED, OperationState.FAILED_VERIFIED, OperationState.RECONCILED}:
            raise ValueError("INVALID_TERMINAL_STATE")
        result = await self.session.execute(update(JarvisOperationRecord).where(
            JarvisOperationRecord.operation_id == operation_id,
            JarvisOperationRecord.tenant_id == tenant_id,
        ).values(
            state=state.value,
            latest_verification_status=verification_status.value,
            verified_at=datetime.now(UTC) if verification_status != VerificationStatus.SIDE_EFFECT_UNKNOWN else None,
            reconciled_at=datetime.now(UTC) if state == OperationState.RECONCILED else None,
            revision=JarvisOperationRecord.revision + 1,
            updated_at=datetime.now(UTC),
        ))
        if result.rowcount != 1:
            raise LookupError("OPERATION_NOT_FOUND_IN_TENANT")
        await self.session.flush()
        return await self.recover(operation_id, tenant_id=tenant_id)

    UNCERTAIN_STATES = frozenset({OperationState.ATTEMPTING.value, OperationState.AWAITING_VERIFICATION.value, OperationState.UNKNOWN.value})

    async def reconcile_unknown_from_recovery(self, operation_id: str, *, tenant_id: str, post_state_matches: bool | None, verification_status: VerificationStatus) -> OperationRecord:
        """Recovery-time reconciliation of a persisted uncertain operation.

        Never mutates externally: the decision must come from an independent
        post-state read performed by the caller. Uncertain states (ATTEMPTING /
        AWAITING_VERIFICATION / UNKNOWN) are terminal until this explicit
        reconciliation path is invoked, so a restart can never produce a second
        external mutation.
        """
        row = await self.session.scalar(select(JarvisOperationRecord).where(
            JarvisOperationRecord.operation_id == operation_id,
            JarvisOperationRecord.tenant_id == tenant_id,
        ))
        if row is None:
            raise LookupError("OPERATION_NOT_FOUND_IN_TENANT")
        if row.state not in self.UNCERTAIN_STATES:
            raise ValueError("RECONCILIATION_REQUIRES_UNCERTAIN_STATE")
        return await self.complete_verification(
            operation_id, tenant_id=tenant_id,
            state=OperationState.RECONCILED, verification_status=verification_status,
        )

    async def attempt_once(self, record: OperationRecord, *, tenant_id: str, mutate, read_state):
        """Durable attempt: uncertain-state duplicate suppression from durable row."""
        row = await self.session.scalar(select(JarvisOperationRecord).where(
            JarvisOperationRecord.operation_id == record.operation_id,
            JarvisOperationRecord.tenant_id == tenant_id,
        ))
        if row is None:
            raise LookupError("OPERATION_NOT_FOUND_IN_TENANT")
        if row.state in self.UNCERTAIN_STATES or row.state == OperationState.MANUAL_REVIEW_REQUIRED.value or row.latest_verification_status == VerificationStatus.SIDE_EFFECT_UNKNOWN.value:
            return ("DUPLICATE_SUPPRESSED", VerificationStatus.SIDE_EFFECT_UNKNOWN)
        await self.mark_attempting(record.operation_id, tenant_id=tenant_id)
        mutate()
        outcome = read_state()
        if outcome is True:
            terminal, status = OperationState.VERIFIED, VerificationStatus.VERIFIED_SUCCESS
        elif outcome is False:
            terminal, status = OperationState.FAILED_VERIFIED, VerificationStatus.VERIFIED_FAILURE
        else:
            await self.mark_unknown(record.operation_id, tenant_id=tenant_id)
            return ("UNKNOWN_RECORDED", VerificationStatus.SIDE_EFFECT_UNKNOWN)
        await self.complete_verification(record.operation_id, tenant_id=tenant_id, state=terminal, verification_status=status)
        return ("COMPLETED", status)


class InMemoryReconciler:
    """TEST_ONLY legacy double; never selected by production factories."""

    backend = "TEST_ONLY"

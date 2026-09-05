"""Database-backed B2 authority lease transitions."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from portal.models.jarvis_b2_durability import JarvisAuthorityLeaseRecord
from portal.services.jarvis_authority_lease import AuthorityLease, LeaseDeniedError, LeaseState


class DurableAuthorityLeaseStore:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def persist(self, lease: AuthorityLease, *, now: datetime | None = None) -> None:
        moment = now or datetime.now(UTC)
        self.session.add(JarvisAuthorityLeaseRecord(
            lease_id=lease.lease_id, tenant_id=lease.tenant_id, principal_id=lease.principal_id,
            capability_id=lease.capability_id, capability_version=lease.capability_version,
            capability_contract_hash=lease.capability_contract_hash, registry_revision=lease.registry_revision,
            action_id=lease.action_id, approval_id=lease.approval_id, operation=lease.operation,
            target=lease.target, params_hash=lease.params_hash, issued_at=lease.issued_at,
            expires_at=lease.expires_at, lease_state=lease.lease_state.value, revision=lease.revision,
            created_at=moment, updated_at=moment,
        ))
        await self.session.flush()

    async def load(self, lease_id: str, *, tenant_id: str) -> AuthorityLease | None:
        """Restart-recovery read: reconstruct the immutable lease value from durable state."""
        row = await self.session.scalar(select(JarvisAuthorityLeaseRecord).where(
            JarvisAuthorityLeaseRecord.lease_id == lease_id,
            JarvisAuthorityLeaseRecord.tenant_id == tenant_id,
        ))
        if row is None:
            return None
        return AuthorityLease(
            lease_id=row.lease_id, tenant_id=row.tenant_id, principal_id=row.principal_id,
            capability_id=row.capability_id, capability_version=row.capability_version,
            capability_contract_hash=row.capability_contract_hash,
            registry_revision=row.registry_revision, action_id=row.action_id,
            approval_id=row.approval_id, operation=row.operation, target=row.target,
            params_hash=row.params_hash, issued_at=row.issued_at, expires_at=row.expires_at,
            lease_state=LeaseState(row.lease_state), revision=row.revision,
        )

    async def claim(self, lease: AuthorityLease, **context) -> AuthorityLease:
        lease.validate(**context)
        if context.get("tenant_id") != lease.tenant_id:
            raise LeaseDeniedError("TENANT_MISMATCH")
        result = await self.session.execute(update(JarvisAuthorityLeaseRecord).where(
            JarvisAuthorityLeaseRecord.lease_id == lease.lease_id,
            JarvisAuthorityLeaseRecord.tenant_id == lease.tenant_id,
            JarvisAuthorityLeaseRecord.lease_state == LeaseState.ISSUED.value,
            JarvisAuthorityLeaseRecord.revision == lease.revision,
        ).values(lease_state=LeaseState.CLAIMED.value, revision=lease.revision + 1, updated_at=datetime.now(UTC)))
        if result.rowcount != 1:
            raise LeaseDeniedError("LEASE_CLAIM_CONFLICT")
        await self.session.flush()
        return AuthorityLease(**{**lease.__dict__, "lease_state": LeaseState.CLAIMED, "revision": lease.revision + 1})

    async def consume(self, lease: AuthorityLease, **context) -> AuthorityLease:
        lease.validate(**context)
        if context.get("tenant_id") != lease.tenant_id:
            raise LeaseDeniedError("TENANT_MISMATCH")
        result = await self.session.execute(update(JarvisAuthorityLeaseRecord).where(
            JarvisAuthorityLeaseRecord.lease_id == lease.lease_id,
            JarvisAuthorityLeaseRecord.tenant_id == lease.tenant_id,
            JarvisAuthorityLeaseRecord.lease_state == LeaseState.CLAIMED.value,
            JarvisAuthorityLeaseRecord.revision == lease.revision,
        ).values(lease_state=LeaseState.CONSUMED.value, revision=lease.revision + 1, updated_at=datetime.now(UTC)))
        if result.rowcount != 1:
            raise LeaseDeniedError("LEASE_CONSUME_CONFLICT")
        await self.session.flush()
        return AuthorityLease(**{**lease.__dict__, "lease_state": LeaseState.CONSUMED, "revision": lease.revision + 1})

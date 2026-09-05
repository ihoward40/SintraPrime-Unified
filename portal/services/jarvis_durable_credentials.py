from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from portal.models.jarvis_b2_durability import JarvisCredentialStateRecord
from portal.services.jarvis_authority_lease import AuthorityLease
from portal.services.jarvis_credential_broker import (
    CredentialBroker,
    CredentialDeniedError,
    CredentialGrant,
    CredentialRequest,
    _SecretMaterial,
)


class DurableCredentialBroker(CredentialBroker):
    """The production B2 credential broker; replay state is database-backed."""

    backend = "DURABLE"

    def __init__(self, session: AsyncSession, fake_secret: str = "FAKE_B2_SECRET"):
        super().__init__(fake_secret=fake_secret)
        self.session = session

    async def issue_scoped_grant_durable(
        self, *, request: CredentialRequest, lease: AuthorityLease,
        now: datetime | None = None, effective_executable: bool = True,
        effective_state: str = "TRUSTED", attestation_valid: bool = True,
    ) -> CredentialGrant:
        moment = now or datetime.now(UTC)
        self._validate_request(request, lease, moment, effective_executable, effective_state, attestation_valid, request.resource_scope)
        nonce_hash = hashlib.sha256(request.nonce.encode()).hexdigest()
        existing = await self.session.scalar(select(JarvisCredentialStateRecord).where(JarvisCredentialStateRecord.nonce_hash == nonce_hash))
        if existing is not None:
            raise CredentialDeniedError("NONCE_REPLAY")
        grant = CredentialGrant(
            grant_id=uuid.uuid4().hex, provider_id=request.provider_id,
            tenant_id=request.tenant_id, action_id=request.action_id,
            capability_contract_hash=request.capability_contract_hash, lease_id=request.lease_id,
            resource_scope=request.resource_scope, operation=request.operation,
            expires_at=request.expires_at, single_use_nonce=request.nonce,
            _secret_material=_SecretMaterial(self._fake_secret),
        )
        self.session.add(JarvisCredentialStateRecord(
            grant_id=grant.grant_id, tenant_id=request.tenant_id, lease_id=request.lease_id,
            action_id=request.action_id, capability_contract_hash=request.capability_contract_hash,
            nonce_hash=nonce_hash, grant_status="ISSUED", expires_at=request.expires_at,
            created_at=moment,
        ))
        await self.session.flush()
        return grant

    async def consume_durable(self, *, grant: CredentialGrant, request: CredentialRequest, now: datetime | None = None) -> None:
        nonce_hash = hashlib.sha256(request.nonce.encode()).hexdigest()
        result = await self.session.execute(update(JarvisCredentialStateRecord).where(
            JarvisCredentialStateRecord.grant_id == grant.grant_id,
            JarvisCredentialStateRecord.tenant_id == request.tenant_id,
            JarvisCredentialStateRecord.nonce_hash == nonce_hash,
            JarvisCredentialStateRecord.grant_status == "ISSUED",
        ).values(grant_status="CONSUMED", consumed_at=now or datetime.now(UTC)))
        if result.rowcount != 1:
            raise CredentialDeniedError("NONCE_REPLAY")
        await self.session.flush()

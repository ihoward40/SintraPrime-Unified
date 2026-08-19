from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Dict, List

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.governed_service_identity import GovernedServiceIdentityRecord

logger = logging.getLogger(__name__)


class IdentityType(StrEnum):
    PRINCIPAL = "PRINCIPAL"
    AGENT_DELEGATED = "AGENT_DELEGATED"
    SERVICE = "SERVICE"
    SYSTEM = "SYSTEM"


class IdentityStatus(StrEnum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class GovernedIdentity(BaseModel):
    """Non-secret identity descriptor used for policy decisions.

    Credentials are never stored here. ``credential_ref`` is an opaque reference
    to a secret manager / connector identity and may be absent in local tests.
    """

    identity_id: str
    type: IdentityType
    tenant_id: str
    display_name: str
    created_by: str | None = None
    agent_id: str | None = None
    credential_ref: str | None = None
    google_account_ref: str | None = None
    scopes: List[str] = Field(default_factory=list)
    scoped_folders: List[str] = Field(default_factory=list)
    allowed_capabilities: List[str] = Field(default_factory=list)
    status: IdentityStatus = IdentityStatus.ACTIVE
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    revocation_reason: str | None = None

    def effective_status(self, now: datetime | None = None) -> IdentityStatus:
        now = now or datetime.now(UTC)
        expires_at = self.expires_at
        if expires_at is not None and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if self.status == IdentityStatus.REVOKED:
            return IdentityStatus.REVOKED
        if expires_at and expires_at <= now:
            return IdentityStatus.EXPIRED
        return IdentityStatus.ACTIVE


class DuplicateServiceIdentityConflictError(Exception):
    """Raised when an idempotency key is reused for different authority content."""

    def __init__(self, identity_id: str):
        self.identity_id = identity_id
        super().__init__("Idempotency key was already used for a different service identity request")


def canonical_service_identity_request_hash(
    *,
    display_name: str,
    agent_id: str | None,
    scopes: List[str],
    scoped_folders: List[str],
    allowed_capabilities: List[str],
    credential_ref: str | None,
    ttl_minutes: int,
) -> str:
    payload = {
        "display_name": display_name,
        "agent_id": agent_id,
        "scopes": sorted(set(scopes)),
        "scoped_folders": sorted(set(scoped_folders)),
        "allowed_capabilities": sorted(set(allowed_capabilities)),
        "credential_ref": credential_ref,
        "ttl_minutes": ttl_minutes,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class GovernedIdentityService:
    """Governed identity service.

    SERVICE identities are persisted through the canonical database. The ``identities``
    dictionary exists only for the legacy delegated-agent compatibility helper and is
    never an authority source for durable service identities.
    """

    def __init__(self):
        self.identities: Dict[str, GovernedIdentity] = {}

    async def provision_service_identity(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        created_by: str,
        display_name: str,
        agent_id: str | None = None,
        scopes: List[str] | None = None,
        scoped_folders: List[str] | None = None,
        allowed_capabilities: List[str] | None = None,
        credential_ref: str | None = None,
        ttl_minutes: int = 60,
        idempotency_key: str | None = None,
    ) -> GovernedIdentity:
        if ttl_minutes < 1 or ttl_minutes > 24 * 60:
            raise ValueError("ttl_minutes must be between 1 and 1440")

        normalized_scopes = list(dict.fromkeys(scopes or []))
        normalized_folders = list(dict.fromkeys(scoped_folders or []))
        normalized_capabilities = list(dict.fromkeys(allowed_capabilities or []))
        request_hash = canonical_service_identity_request_hash(
            display_name=display_name,
            agent_id=agent_id,
            scopes=normalized_scopes,
            scoped_folders=normalized_folders,
            allowed_capabilities=normalized_capabilities,
            credential_ref=credential_ref,
            ttl_minutes=ttl_minutes,
        )

        if idempotency_key:
            existing = await self._find_by_idempotency_key(
                db,
                tenant_id=tenant_id,
                created_by=created_by,
                idempotency_key=idempotency_key,
            )
            if existing is not None:
                if existing.request_hash != request_hash:
                    raise DuplicateServiceIdentityConflictError(existing.id)
                return self._record_to_identity(existing)

        record = GovernedServiceIdentityRecord(
            id=f"svc-{uuid.uuid4().hex[:12]}",
            tenant_id=tenant_id,
            created_by=created_by,
            display_name=display_name,
            agent_id=agent_id,
            credential_ref=credential_ref,
            scopes=normalized_scopes,
            scoped_folders=normalized_folders,
            allowed_capabilities=normalized_capabilities,
            status=IdentityStatus.ACTIVE.value,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            expires_at=datetime.now(UTC) + timedelta(minutes=ttl_minutes),
        )

        try:
            async with db.begin_nested():
                db.add(record)
                await db.flush()
        except IntegrityError as exc:
            if not idempotency_key:
                raise
            existing = await self._find_by_idempotency_key(
                db,
                tenant_id=tenant_id,
                created_by=created_by,
                idempotency_key=idempotency_key,
            )
            if existing is None:
                raise
            if existing.request_hash != request_hash:
                raise DuplicateServiceIdentityConflictError(existing.id) from exc
            return self._record_to_identity(existing)

        logger.info(
            "[IDENTITY] Persisted service identity %s for tenant %s agent=%s scopes=%d capabilities=%d",
            record.id,
            tenant_id,
            agent_id,
            len(normalized_scopes),
            len(normalized_capabilities),
        )
        return self._record_to_identity(record)

    async def list_identities(self, db: AsyncSession, *, tenant_id: str) -> List[GovernedIdentity]:
        result = await db.execute(
            select(GovernedServiceIdentityRecord)
            .where(GovernedServiceIdentityRecord.tenant_id == tenant_id)
            .order_by(GovernedServiceIdentityRecord.created_at)
        )
        return [self._record_to_identity(record) for record in result.scalars().all()]

    async def get_identity(
        self,
        db: AsyncSession,
        identity_id: str,
        *,
        tenant_id: str,
    ) -> GovernedIdentity | None:
        result = await db.execute(
            select(GovernedServiceIdentityRecord).where(
                GovernedServiceIdentityRecord.id == identity_id,
                GovernedServiceIdentityRecord.tenant_id == tenant_id,
            )
        )
        record = result.scalar_one_or_none()
        return self._record_to_identity(record) if record is not None else None

    async def revoke_identity(
        self,
        db: AsyncSession,
        identity_id: str,
        *,
        tenant_id: str,
        reason: str,
    ) -> GovernedIdentity | None:
        result = await db.execute(
            select(GovernedServiceIdentityRecord).where(
                GovernedServiceIdentityRecord.id == identity_id,
                GovernedServiceIdentityRecord.tenant_id == tenant_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        if record.status != IdentityStatus.REVOKED.value:
            record.status = IdentityStatus.REVOKED.value
            record.revoked_at = datetime.now(UTC)
            record.revocation_reason = reason
            await db.flush()
        return self._record_to_identity(record)

    async def validate_access(
        self,
        db: AsyncSession,
        identity_id: str,
        resource_id: str,
        *,
        required_scope: str | None = None,
        required_capability: str | None = None,
        tenant_id: str,
    ) -> bool:
        identity = await self.get_identity(db, identity_id, tenant_id=tenant_id)
        if identity is None or identity.effective_status() != IdentityStatus.ACTIVE:
            return False
        if required_scope and required_scope not in identity.scopes:
            return False
        if required_capability and required_capability not in identity.allowed_capabilities:
            return False
        return not identity.scoped_folders or resource_id in identity.scoped_folders

    async def _find_by_idempotency_key(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        created_by: str,
        idempotency_key: str,
    ) -> GovernedServiceIdentityRecord | None:
        result = await db.execute(
            select(GovernedServiceIdentityRecord).where(
                GovernedServiceIdentityRecord.tenant_id == tenant_id,
                GovernedServiceIdentityRecord.created_by == created_by,
                GovernedServiceIdentityRecord.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _record_to_identity(record: GovernedServiceIdentityRecord) -> GovernedIdentity:
        identity = GovernedIdentity(
            identity_id=record.id,
            type=IdentityType.SERVICE,
            tenant_id=record.tenant_id,
            display_name=record.display_name,
            created_by=record.created_by,
            agent_id=record.agent_id,
            credential_ref=record.credential_ref,
            scopes=list(record.scopes or []),
            scoped_folders=list(record.scoped_folders or []),
            allowed_capabilities=list(record.allowed_capabilities or []),
            status=IdentityStatus(record.status),
            created_at=record.created_at,
            expires_at=record.expires_at,
            revoked_at=record.revoked_at,
            revocation_reason=record.revocation_reason,
        )
        identity.status = identity.effective_status()
        return identity

    def provision_agent_identity(self, tenant_id: str, folders: List[str]) -> GovernedIdentity:
        """Backward-compatible Phase 7 helper; not a production service identity."""
        identity_id = f"agent-{uuid.uuid4().hex[:8]}"
        identity = GovernedIdentity(
            identity_id=identity_id,
            type=IdentityType.AGENT_DELEGATED,
            tenant_id=tenant_id,
            display_name=identity_id,
            google_account_ref=f"sintraprime-agent-{tenant_id}@google-workspace.iam.gserviceaccount.com",
            scoped_folders=list(dict.fromkeys(folders)),
        )
        self.identities[identity_id] = identity
        return identity


identity_service = GovernedIdentityService()

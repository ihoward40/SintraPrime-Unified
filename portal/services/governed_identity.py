from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Dict, List

from pydantic import BaseModel, Field

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
        if self.status == IdentityStatus.REVOKED:
            return IdentityStatus.REVOKED
        if self.expires_at and self.expires_at <= now:
            return IdentityStatus.EXPIRED
        return IdentityStatus.ACTIVE


class GovernedIdentityService:
    """Governed identity registry for Principal and delegated service identities.

    This registry stores descriptors only. It does not mint or persist secrets.
    Production credentials must remain in the canonical connector/secret system.
    """

    def __init__(self):
        self.identities: Dict[str, GovernedIdentity] = {}

    def provision_service_identity(
        self,
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
    ) -> GovernedIdentity:
        if ttl_minutes < 1 or ttl_minutes > 24 * 60:
            raise ValueError("ttl_minutes must be between 1 and 1440")
        identity_id = f"svc-{uuid.uuid4().hex[:12]}"
        identity = GovernedIdentity(
            identity_id=identity_id,
            type=IdentityType.SERVICE,
            tenant_id=tenant_id,
            display_name=display_name,
            created_by=created_by,
            agent_id=agent_id,
            credential_ref=credential_ref,
            scopes=list(dict.fromkeys(scopes or [])),
            scoped_folders=list(dict.fromkeys(scoped_folders or [])),
            allowed_capabilities=list(dict.fromkeys(allowed_capabilities or [])),
            expires_at=datetime.now(UTC) + timedelta(minutes=ttl_minutes),
        )
        self.identities[identity_id] = identity
        logger.info(
            "[IDENTITY] Provisioned service identity %s for tenant %s agent=%s scopes=%d capabilities=%d",
            identity_id,
            tenant_id,
            agent_id,
            len(identity.scopes),
            len(identity.allowed_capabilities),
        )
        return identity

    def provision_agent_identity(self, tenant_id: str, folders: List[str]) -> GovernedIdentity:
        """Backward-compatible Phase 7 helper for a Google-scoped delegated agent."""
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
        logger.info(
            "[IDENTITY] Provisioned legacy delegated identity %s for %s with %d scoped folders",
            identity_id,
            tenant_id,
            len(folders),
        )
        return identity

    def list_identities(self, *, tenant_id: str) -> List[GovernedIdentity]:
        return [
            identity
            for identity in self.identities.values()
            if identity.tenant_id == tenant_id
        ]

    def get_identity(self, identity_id: str, *, tenant_id: str) -> GovernedIdentity | None:
        identity = self.identities.get(identity_id)
        if identity is None or identity.tenant_id != tenant_id:
            return None
        return identity

    def revoke_identity(
        self,
        identity_id: str,
        *,
        tenant_id: str,
        reason: str,
    ) -> GovernedIdentity | None:
        identity = self.get_identity(identity_id, tenant_id=tenant_id)
        if identity is None:
            return None
        identity.status = IdentityStatus.REVOKED
        identity.revoked_at = datetime.now(UTC)
        identity.revocation_reason = reason
        self.identities[identity_id] = identity
        return identity

    def validate_access(
        self,
        identity_id: str,
        resource_id: str,
        *,
        required_scope: str | None = None,
        required_capability: str | None = None,
        tenant_id: str | None = None,
    ) -> bool:
        identity = self.identities.get(identity_id)
        if identity is None:
            return False
        if tenant_id is not None and identity.tenant_id != tenant_id:
            return False
        if identity.effective_status() != IdentityStatus.ACTIVE:
            return False
        if identity.type == IdentityType.PRINCIPAL:
            return True
        if required_scope and required_scope not in identity.scopes:
            return False
        if required_capability and required_capability not in identity.allowed_capabilities:
            return False
        return not identity.scoped_folders or resource_id in identity.scoped_folders


identity_service = GovernedIdentityService()

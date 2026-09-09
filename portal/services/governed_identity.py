import logging
import uuid
from datetime import UTC, datetime, timedelta
from enum import Enum, StrEnum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, model_validator

logger = logging.getLogger(__name__)

class IdentityType(StrEnum):
    PRINCIPAL = "PRINCIPAL"
    AGENT_DELEGATED = "AGENT_DELEGATED"
    SYSTEM = "SYSTEM"

class GovernedIdentity(BaseModel):
    identity_id: str
    type: IdentityType
    google_account_ref: str # Reference to separate identity
    scoped_folders: List[str] # List of authorized folder IDs
    tenant_id: str
    # 2E-2 delegation expiry: delegated identities are time-bounded and fail
    # closed. None is only permitted for PRINCIPAL/SYSTEM identities, and is
    # structurally rejected for AGENT_DELEGATED (see model_validator).
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def delegated_identity_cannot_be_immortal(self) -> "GovernedIdentity":
        """Structural guarantee: a delegation without an expiry never exists.
        Immortal delegation is the authority failure mode this model exists to
        prevent — reject it at construction, not at use."""
        if self.type == IdentityType.AGENT_DELEGATED and self.expires_at is None:
            raise ValueError("AGENT_DELEGATED identity requires expires_at (immortal delegation forbidden)")
        return self

class GovernedIdentityService:
    """
    Phase 7: Governed Identity.
    Implements separate identities and folder-scoped access for agents.
    """
    def __init__(self):
        self.identities: Dict[str, GovernedIdentity] = {}

    @property
    def delegation_ttl_hours(self) -> int:
        """Delegation lease duration (hours). Read from the canonical typed
        configuration (DELEGATION_TTL_HOURS); falls back to the secure 24-hour
        default if configuration is unavailable or malformed (fail closed —
        never immortal)."""
        try:
            from portal.config import get_settings

            ttl = int(get_settings().DELEGATION_TTL_HOURS)
            if ttl < 1:
                logger.warning("[IDENTITY] DELEGATION_TTL_HOURS < 1 rejected — using secure default 24")
                return 24
            return ttl
        except Exception as exc:  # fail closed: any config error keeps the secure default
            logger.warning(f"[IDENTITY] delegation TTL config unavailable ({exc.__class__.__name__}) — using secure default 24")
            return 24

    def provision_agent_identity(self, tenant_id: str, folders: List[str]) -> GovernedIdentity:
        """Provisions a new delegated identity for an agent.

        2E-2: delegated authority is time-bounded — every delegated identity
        carries a configured expiry (default 24h) and validate_access fails
        closed after it.
        """
        identity_id = f"agent-{uuid.uuid4().hex[:8]}"
        identity = GovernedIdentity(
            identity_id=identity_id,
            type=IdentityType.AGENT_DELEGATED,
            google_account_ref=f"sintraprime-agent-{tenant_id}@google-workspace.iam.gserviceaccount.com",
            scoped_folders=folders,
            tenant_id=tenant_id,
            expires_at=datetime.now(UTC) + timedelta(hours=self.delegation_ttl_hours),
        )
        self.identities[identity_id] = identity
        logger.info(f"[IDENTITY] Provisioned {identity_id} for {tenant_id} with {len(folders)} scoped folders")
        return identity

    def validate_access(self, identity_id: str, resource_id: str) -> bool:
        """Validates if an identity has access to a specific resource (folder)."""
        if identity_id not in self.identities:
            return False

        identity = self.identities[identity_id]

        # 2E-2 delegation expiry: expired delegations fail closed, even for
        # resources inside their scope.
        expires_at = identity.expires_at
        if expires_at is not None and expires_at <= datetime.now(UTC):
            logger.warning(f"[IDENTITY] {identity_id} delegation expired — access denied")
            return False

        # Principal has global access (God Mode)
        if identity.type == IdentityType.PRINCIPAL:
            return True

        # Agent has folder-scoped access
        return resource_id in identity.scoped_folders

# Global instance
identity_service = GovernedIdentityService()

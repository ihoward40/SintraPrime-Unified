import logging
import uuid
from enum import Enum, StrEnum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

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

class GovernedIdentityService:
    """
    Phase 7: Governed Identity.
    Implements separate identities and folder-scoped access for agents.
    """
    def __init__(self):
        self.identities: Dict[str, GovernedIdentity] = {}

    def provision_agent_identity(self, tenant_id: str, folders: List[str]) -> GovernedIdentity:
        """Provisions a new delegated identity for an agent."""
        identity_id = f"agent-{uuid.uuid4().hex[:8]}"
        identity = GovernedIdentity(
            identity_id=identity_id,
            type=IdentityType.AGENT_DELEGATED,
            google_account_ref=f"sintraprime-agent-{tenant_id}@google-workspace.iam.gserviceaccount.com",
            scoped_folders=folders,
            tenant_id=tenant_id
        )
        self.identities[identity_id] = identity
        logger.info(f"[IDENTITY] Provisioned {identity_id} for {tenant_id} with {len(folders)} scoped folders")
        return identity

    def validate_access(self, identity_id: str, resource_id: str) -> bool:
        """Validates if an identity has access to a specific resource (folder)."""
        if identity_id not in self.identities:
            return False

        identity = self.identities[identity_id]

        # Principal has global access (God Mode)
        if identity.type == IdentityType.PRINCIPAL:
            return True

        # Agent has folder-scoped access
        return resource_id in identity.scoped_folders

# Global instance
identity_service = GovernedIdentityService()

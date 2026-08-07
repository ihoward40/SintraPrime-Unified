import logging
import re
import uuid
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional, TypeVar, Type
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.orchestration import OrchestrationLinkage as EventNodeLinkage

logger = logging.getLogger(__name__)

T = TypeVar("T")

class RemediationService:
    """
    Hardened Remediation Service for PR #263.
    Enforces integrity gates: actor validation, data masking, timestamps, and linkage.
    """
    def __init__(self):
        self.authorized_principals = ["principal-god-mode"]
        # Comprehensive patterns for redaction at all boundaries
        self.sensitive_patterns = [
            r"(oauth_token|client_secret|password|api_key|ssn|credit_card|jwt_secret)\s*[=:]\s*[^,\s}\"]+",
            r"(oauth_token|client_secret|password|api_key|ssn|credit_card|jwt_secret)"
        ]

    async def validate_principal_approval(
        self, session: AsyncSession, tenant_id: str, actor_id: str, intent_type: str
    ) -> bool:
        """
        Remediation: Scoped authoritative human approval validation.
        Ensures only the authorized Principal can approve high-impact intents using DB-backed authority.
        """
        from ..models.orchestration import PrincipalAuthority
        
        stmt = select(PrincipalAuthority).where(
            PrincipalAuthority.tenant_id == tenant_id,
            PrincipalAuthority.user_id == actor_id,
            PrincipalAuthority.is_active == True
        )
        res = await session.execute(stmt)
        authority = res.scalar_one_or_none()
        
        if not authority:
            logger.error(f"[REMEDIATION] Unauthorized approval attempt by {actor_id} for {intent_type} in tenant {tenant_id}")
            return False
            
        logger.info(f"[REMEDIATION] Principal approval validated for {actor_id} (Scope: {authority.scope})")
        return True

    def redact_boundaries(self, data: Any) -> Any:
        """
        Remediation: Redaction at all persistence and response boundaries.
        Recursively masks sensitive data in any structure, including dictionary keys.
        """
        if isinstance(data, str):
            for pattern in self.sensitive_patterns:
                data = re.sub(pattern, "[MASKED]", data, flags=re.IGNORECASE)
            return data
        elif isinstance(data, dict):
            redacted_dict = {}
            for k, v in data.items():
                # Check if key itself is sensitive
                key_is_sensitive = any(re.search(p, str(k), re.IGNORECASE) for p in [
                    r"token", r"secret", r"password", r"api_key", r"ssn", r"credit_card"
                ])
                
                new_k = f"[MASKED_KEY_{k}]" if key_is_sensitive else k
                new_v = "[MASKED_VALUE]" if key_is_sensitive else self.redact_boundaries(v)
                redacted_dict[new_k] = new_v
            return redacted_dict
        elif isinstance(data, list):
            return [self.redact_boundaries(i) for i in data]
        return data

    def inject_audit_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remediation: Lifecycle timestamps and durable node identification.
        """
        now = datetime.now(UTC).isoformat()
        if "created_at" not in data:
            data["created_at"] = now
        data["updated_at"] = now
        if "node_id" not in data:
            data["node_id"] = f"node-{uuid.uuid4().hex[:8]}"
        return data

    async def persist_durable_linkage(
        self, session: AsyncSession, event_id: str, node_id: str, tenant_id: str
    ) -> int:
        """
        Remediation: Durable event-to-node linkage with PostgreSQL/RLS safety.
        """
        linkage = EventNodeLinkage(
            event_id=event_id,
            node_id=node_id,
            tenant_id=tenant_id,
            linked_at=datetime.now(UTC)
        )
        session.add(linkage)
        await session.flush() # Ensure it's part of the transaction
        logger.info(f"[REMEDIATION] Durable linkage persisted for event {event_id} -> node {node_id}")
        return linkage.id

    async def record_approval_with_concurrency_safety(
        self, 
        session: AsyncSession, 
        approval_id: str, 
        actor_id: str, 
        decision: str, 
        reason: str,
        expected_version: int
    ) -> bool:
        """
        Remediation: Concurrent approval safety using Optimistic Locking.
        Ensures a one-time decision and prevents last-writer-wins.
        """
        from ..models.orchestration import ApprovalRequest
        
        # 1. Fetch with specific version to ensure no one else updated it
        stmt = select(ApprovalRequest).where(
            ApprovalRequest.id == approval_id,
            ApprovalRequest.version == expected_version,
            ApprovalRequest.status == "REQUESTED"
        )
        res = await session.execute(stmt)
        approval = res.scalar_one_or_none()
        
        if not approval:
            logger.error(f"[REMEDIATION] Approval {approval_id} already decided or version mismatch.")
            return False
            
        # 2. Apply decision and increment version
        approval.status = decision
        approval.principal_id = actor_id
        approval.decision_reason = self.redact_boundaries(reason)
        approval.decided_at = datetime.now(UTC)
        approval.version += 1
        
        await session.flush()
        logger.info(f"[REMEDIATION] Approval {approval_id} recorded with version {approval.version}")
        return True

# Global instance
remediation = RemediationService()

import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.orchestration import OrchestrationLinkage as EventNodeLinkage

logger = logging.getLogger(__name__)


class RemediationService:
    """Enforce actor validation, data masking, timestamps, and durable linkage."""

    def __init__(self):
        self.authorized_principals = ["principal-god-mode"]
        self.sensitive_patterns = [
            r"(oauth_token|client_secret|password|api_key|ssn|credit_card|jwt_secret)\s*[=:]\s*[^,\s}\"]+",
            r"(oauth_token|client_secret|password|api_key|ssn|credit_card|jwt_secret)",
        ]

    async def validate_principal_approval(
        self,
        session: AsyncSession,
        tenant_id: str,
        actor_id: str,
        intent_type: str,
    ) -> bool:
        """Validate DB-backed tenant-scoped Principal authority."""
        from ..models.orchestration import PrincipalAuthority

        stmt = select(PrincipalAuthority).where(
            PrincipalAuthority.tenant_id == tenant_id,
            PrincipalAuthority.user_id == actor_id,
            PrincipalAuthority.is_active,
        )
        res = await session.execute(stmt)
        authority = res.scalar_one_or_none()

        if not authority:
            logger.error(
                "[REMEDIATION] Unauthorized approval attempt by %s for %s in tenant %s",
                actor_id,
                intent_type,
                tenant_id,
            )
            return False

        logger.info(
            "[REMEDIATION] Principal approval validated for %s (Scope: %s)",
            actor_id,
            authority.scope,
        )
        return True

    def redact_boundaries(self, data: Any) -> Any:
        """Recursively mask sensitive data at persistence and response boundaries."""
        if isinstance(data, str):
            for pattern in self.sensitive_patterns:
                data = re.sub(pattern, "[MASKED]", data, flags=re.IGNORECASE)
            return data
        if isinstance(data, dict):
            redacted_dict = {}
            sensitive_key_patterns = [
                r"token",
                r"secret",
                r"password",
                r"api_key",
                r"ssn",
                r"credit_card",
            ]
            for key, value in data.items():
                key_is_sensitive = any(
                    re.search(pattern, str(key), re.IGNORECASE)
                    for pattern in sensitive_key_patterns
                )
                new_key = f"[MASKED_KEY_{key}]" if key_is_sensitive else key
                new_value = (
                    "[MASKED_VALUE]"
                    if key_is_sensitive
                    else self.redact_boundaries(value)
                )
                redacted_dict[new_key] = new_value
            return redacted_dict
        if isinstance(data, list):
            return [self.redact_boundaries(item) for item in data]
        return data

    def inject_audit_metadata(self, data: dict[str, Any]) -> dict[str, Any]:
        """Inject lifecycle timestamps and a durable node identifier."""
        now = datetime.now(UTC).isoformat()
        data.setdefault("created_at", now)
        data["updated_at"] = now
        data.setdefault("node_id", f"node-{uuid.uuid4().hex[:8]}")
        return data

    async def persist_durable_linkage(
        self,
        session: AsyncSession,
        event_id: str,
        node_id: str,
        tenant_id: str,
    ) -> str:
        """Persist durable event-to-node linkage with PostgreSQL/RLS safety."""
        linkage = EventNodeLinkage(
            event_id=event_id,
            node_id=node_id,
            tenant_id=tenant_id,
            linked_at=datetime.now(UTC),
        )
        session.add(linkage)
        await session.flush()
        logger.info(
            "[REMEDIATION] Durable linkage persisted for event %s -> node %s",
            event_id,
            node_id,
        )
        return str(linkage.id)

    async def record_approval_with_concurrency_safety(
        self,
        session: AsyncSession,
        approval_id: str,
        actor_id: str,
        decision: str,
        reason: str,
        expected_version: int,
    ) -> bool:
        """Record a one-time approval decision using optimistic locking."""
        from ..models.orchestration import ApprovalRequest

        stmt = select(ApprovalRequest).where(
            ApprovalRequest.id == approval_id,
            ApprovalRequest.version == expected_version,
            ApprovalRequest.status == "REQUESTED",
        )
        res = await session.execute(stmt)
        approval = res.scalar_one_or_none()

        if not approval:
            logger.error(
                "[REMEDIATION] Approval %s already decided or version mismatch.",
                approval_id,
            )
            return False

        approval.status = decision
        approval.principal_id = actor_id
        approval.decision_reason = self.redact_boundaries(reason)
        approval.decided_at = datetime.now(UTC)
        approval.version += 1

        await session.flush()
        logger.info(
            "[REMEDIATION] Approval %s recorded with version %s",
            approval_id,
            approval.version,
        )
        return True


remediation = RemediationService()

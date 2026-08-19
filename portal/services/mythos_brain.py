import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.mission_control_outbox import MissionControlOutbox
from .remediation_service import remediation

logger = logging.getLogger(__name__)


class MythosBrainCoordinator:
    """Central execution coordinator with transactional outbox and remediation."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def ingest_intent(
        self,
        tenant_id: str,
        actor_id: str,
        intent_type: str,
        payload: dict[str, Any],
    ) -> str:
        """Ingest a new intent, apply remediation, and persist it to the outbox."""
        if intent_type == "PRINCIPAL_COMMAND" and not await remediation.validate_principal_approval(
            self.session,
            tenant_id,
            actor_id,
            intent_type,
        ):
            raise PermissionError("Unauthorized principal command attempt.")

        safe_payload = remediation.redact_boundaries(payload)
        audit_payload = remediation.inject_audit_metadata(safe_payload)
        intent_id = f"int-{uuid.uuid4().hex[:8]}"

        outbox_entry = MissionControlOutbox(
            tenant_id=tenant_id,
            intent_id=intent_id,
            event_type=intent_type,
            payload=audit_payload,
            status="PENDING",
            created_at=datetime.now(UTC),
        )
        self.session.add(outbox_entry)
        await self.session.flush()

        await remediation.persist_durable_linkage(
            self.session,
            event_id=f"evt-{intent_id[:4]}",
            node_id=audit_payload.get("node_id", "unknown"),
            tenant_id=tenant_id,
        )

        logger.info(
            "[MYTHOS_BRAIN] Intent %s ingested and persisted to outbox.",
            intent_id,
        )
        return intent_id

import hashlib
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.mission_control_outbox import MissionControlOutbox
from ..models.orchestration import (
    OrchestrationEvent,
    OrchestrationLinkage,
    OrchestrationNode,
    OrchestrationRun,
    OrchestrationRunStatus,
)
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
        """Ingest a new intent, apply remediation, and persist it to the outbox.

        Creates the full orchestration parent chain (Run → Event → Node)
        atomically before the durable linkage, so OrchestrationLinkage
        foreign keys reference existing rows.
        """
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

        # --- Create parent orchestration records atomically ---

        run_id = str(uuid.uuid4())
        run = OrchestrationRun(
            id=run_id,
            tenant_id=tenant_id,
            objective=f"Intent ingestion: {intent_type}",
            constraints={},
            task_type="mixed",
            sensitivity="INTERNAL",
            execution_mode="SINGLE",
            status=OrchestrationRunStatus.RUNNING,
        )
        self.session.add(run)
        await self.session.flush()

        event_id = str(uuid.uuid4())
        event_hash = hashlib.sha256(
            f"{run_id}:{intent_type}:{intent_id}".encode()
        ).hexdigest()
        event = OrchestrationEvent(
            id=event_id,
            run_id=run_id,
            sequence=1,
            event_type=intent_type,
            actor_role="WORKER",
            payload=audit_payload,
            event_hash=event_hash,
        )
        self.session.add(event)
        await self.session.flush()

        node_pk = str(uuid.uuid4())
        node = OrchestrationNode(
            id=node_pk,
            run_id=run_id,
            node_id=audit_payload.get("node_id", str(uuid.uuid4())),
            sequence=1,
            role="WORKER",
            objective=f"Execute intent {intent_id}",
        )
        self.session.add(node)
        await self.session.flush()

        # --- Create outbox entry ---
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

        # --- Create durable linkage with real FK targets ---
        linkage = OrchestrationLinkage(
            id=str(uuid.uuid4()),
            event_id=event_id,
            node_id=node_pk,
            tenant_id=tenant_id,
            linked_at=datetime.now(UTC),
        )
        self.session.add(linkage)
        await self.session.flush()

        logger.info(
            "[MYTHOS_BRAIN] Intent %s ingested and persisted to outbox. "
            "Run=%s Event=%s Node=%s Linkage=%s",
            intent_id, run_id, event_id, node_pk, linkage.id,
        )
        return intent_id

import logging
import uuid
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.mission_control_outbox import MissionControlOutbox
from .remediation_service import remediation

logger = logging.getLogger(__name__)

class MythosBrainCoordinator:
    """
    Central Execution Coordinator with Transactional Outbox and Remediation.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def ingest_intent(
        self, tenant_id: str, actor_id: str, intent_type: str, payload: Dict[str, Any]
    ) -> str:
        """
        Ingests a new intent, applies remediation, and persists to outbox.
        """
        # 1. REMEDIATION: Scoped Approval Validation
        if intent_type == "PRINCIPAL_COMMAND" and not remediation.validate_principal_approval(actor_id, intent_type):
            raise PermissionError("Unauthorized principal command attempt.")

        # 2. REMEDIATION: Redaction and Metadata
        safe_payload = remediation.redact_boundaries(payload)
        audit_payload = remediation.inject_audit_metadata(safe_payload)
        
        intent_id = f"int-{uuid.uuid4().hex[:8]}"
        
        # 3. Transactional Outbox Pattern
        outbox_entry = MissionControlOutbox(
            tenant_id=tenant_id,
            intent_id=intent_id,
            event_type=intent_type,
            payload=audit_payload,
            status="PENDING",
            created_at=datetime.now(UTC)
        )
        
        self.session.add(outbox_entry)
        await self.session.flush()
        
        # 4. REMEDIATION: Durable Linkage
        await remediation.persist_durable_linkage(
            self.session, 
            event_id=f"evt-{intent_id[:4]}", 
            node_id=audit_payload.get("node_id", "unknown"),
            tenant_id=tenant_id
        )
        
        logger.info(f"[MYTHOS_BRAIN] Intent {intent_id} ingested and persisted to outbox.")
        return intent_id

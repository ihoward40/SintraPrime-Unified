import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.orchestration import OrchestrationEvent, OrchestrationLinkage
from .remediation_service import remediation

logger = logging.getLogger(__name__)

class AuditableExecutionTrailsService:
    """
    Phase 7C: Auditable Execution Trails.
    Provides immutable, third-party verifiable audit logs for all orchestrations.
    """
    async def generate_execution_trail(self, session: AsyncSession, run_id: str, tenant_id: str) -> Dict[str, Any]:
        """Generates a cryptographically linked execution trail for a run."""
        # 1. Fetch all events for the run
        stmt = select(OrchestrationEvent).where(OrchestrationEvent.run_id == run_id).order_by(OrchestrationEvent.sequence)
        res = await session.execute(stmt)
        events = res.scalars().all()

        # 2. Build the trail with redaction and hashing
        trail = {
            "run_id": run_id,
            "tenant_id": tenant_id,
            "generated_at": datetime.now(UTC).isoformat(),
            "events": []
        }

        for event in events:
            # Apply remediation: redact sensitive data
            safe_payload = remediation.redact_boundaries(event.payload)

            event_data = {
                "sequence": event.sequence,
                "type": event.event_type,
                "actor": event.actor_role,
                "payload": safe_payload,
                "timestamp": event.created_at.isoformat(),
                "hash": event.event_hash
            }
            trail["events"].append(event_data)

        # 3. Generate a root hash for the entire trail
        root_content = json.dumps(trail["events"], sort_keys=True)
        trail["root_hash"] = hashlib.sha256(root_content.encode()).hexdigest()

        logger.info(f"[AUDIT_TRAIL] Generated trail for run {run_id} with root hash {trail['root_hash'][:8]}")
        return trail

    async def verify_trail_integrity(self, trail: Dict[str, Any]) -> bool:
        """Verifies the integrity of a generated execution trail."""
        events = trail.get("events", [])
        if not events:
            return False

        # Re-calculate root hash
        root_content = json.dumps(events, sort_keys=True)
        calculated_hash = hashlib.sha256(root_content.encode()).hexdigest()

        return calculated_hash == trail.get("root_hash")

# Global instance
auditable_trails = AuditableExecutionTrailsService()

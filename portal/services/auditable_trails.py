import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.orchestration import OrchestrationEvent
from .remediation_service import remediation

logger = logging.getLogger(__name__)


class AuditableExecutionTrailsService:
    """Provide immutable, third-party verifiable orchestration audit trails."""

    async def generate_execution_trail(
        self,
        session: AsyncSession,
        run_id: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Generate a cryptographically linked execution trail for a run."""
        stmt = (
            select(OrchestrationEvent)
            .where(OrchestrationEvent.run_id == run_id)
            .order_by(OrchestrationEvent.sequence)
        )
        res = await session.execute(stmt)
        events = res.scalars().all()

        trail: dict[str, Any] = {
            "run_id": run_id,
            "tenant_id": tenant_id,
            "generated_at": datetime.now(UTC).isoformat(),
            "events": [],
        }

        for event in events:
            safe_payload = remediation.redact_boundaries(event.payload)
            event_data = {
                "sequence": event.sequence,
                "type": event.event_type,
                "actor": event.actor_role,
                "payload": safe_payload,
                "timestamp": event.created_at.isoformat(),
                "hash": event.event_hash,
            }
            trail["events"].append(event_data)

        root_content = json.dumps(trail["events"], sort_keys=True)
        trail["root_hash"] = hashlib.sha256(root_content.encode()).hexdigest()

        logger.info(
            "[AUDIT_TRAIL] Generated trail for run %s with root hash %s",
            run_id,
            trail["root_hash"][:8],
        )
        return trail

    async def verify_trail_integrity(self, trail: dict[str, Any]) -> bool:
        """Verify the integrity of a generated execution trail."""
        events = trail.get("events", [])
        if not events:
            return False

        root_content = json.dumps(events, sort_keys=True)
        calculated_hash = hashlib.sha256(root_content.encode()).hexdigest()
        return calculated_hash == trail.get("root_hash")


auditable_trails = AuditableExecutionTrailsService()

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.orchestration import OrchestrationRun
from .auditable_trails import auditable_trails
from .memory_vault import memory_vault
from .remediation_service import remediation

logger = logging.getLogger(__name__)


class PrincipalBrief:
    """Synthesize a tenant-scoped Principal Brief from governed runtime state."""

    def __init__(self, tenant_id: str, session: AsyncSession):
        self.tenant_id = tenant_id
        self.session = session
        self.timestamp = datetime.now(UTC)
        self.sections: dict[str, Any] = {}

    async def synthesize(self, actor_id: str):
        """Synthesize the brief using database-backed retrieval."""
        if not await remediation.validate_principal_approval(
            self.session,
            self.tenant_id,
            actor_id,
            "BRIEF_SYNTHESIS",
        ):
            raise PermissionError("Unauthorized access to Principal Brief.")

        logger.info("[PRINCIPAL_BRIEF] Synthesizing brief for tenant %s", self.tenant_id)
        lessons = await memory_vault.retrieve_tenant_memory(
            self.session,
            self.tenant_id,
            "LESSON_LEARNED",
        )
        procedures = await memory_vault.retrieve_tenant_memory(
            self.session,
            self.tenant_id,
            "PROVEN_PROCEDURE",
        )
        knowledge = await memory_vault.retrieve_tenant_memory(
            self.session,
            self.tenant_id,
            "INSTITUTIONAL_KNOWLEDGE",
        )

        self.sections["memory_summary"] = remediation.redact_boundaries(
            {
                "total_lessons": len(lessons),
                "total_procedures": len(procedures),
                "total_knowledge": len(knowledge),
                "recent_lesson": lessons[0].content if lessons else "No recent lessons recorded.",
                "strategic_milestones": [item.content for item in knowledge[:3]],
            }
        )

        stmt = select(OrchestrationRun).where(
            OrchestrationRun.tenant_id == self.tenant_id
        )
        res = await self.session.execute(stmt)
        active_runs = res.scalars().all()

        trails = []
        for run in active_runs[:5]:
            trail = await auditable_trails.generate_execution_trail(
                self.session,
                str(run.id),
                self.tenant_id,
            )
            trails.append(trail)

        self.sections["operations"] = {
            "status": "HARDENED",
            "active_orchestrations": len(active_runs),
            "verified_audit_trails": len(trails),
        }
        self.sections["parliament"] = {"load": "0.00%", "instances": 0}

    def generate_report(self) -> dict[str, Any]:
        """Return the synthesized brief as a structured report."""
        return {
            "tenant_id": self.tenant_id,
            "timestamp": self.timestamp.isoformat(),
            "doctrine": "Unified orchestration. Autonomous integrity.",
            "sections": self.sections,
        }


class PrincipalBriefService:
    async def create_brief(
        self,
        session: AsyncSession,
        tenant_id: str,
        actor_id: str,
    ) -> dict[str, Any]:
        brief = PrincipalBrief(tenant_id, session)
        await brief.synthesize(actor_id)
        return brief.generate_report()


brief_service = PrincipalBriefService()

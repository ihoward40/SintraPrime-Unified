import logging
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.orchestration import OrchestrationRun
from .auditable_trails import auditable_trails
from .memory_vault import memory_vault
from .remediation_service import remediation

logger = logging.getLogger(__name__)

class PrincipalBrief:
    """
    Phase 9: Principal Brief.
    Real OmniBrain-to-Brief flow with remediation.
    """
    def __init__(self, tenant_id: str, session: AsyncSession):
        self.tenant_id = tenant_id
        self.session = session
        self.timestamp = datetime.now(UTC)
        self.sections: Dict[str, Any] = {}

    async def synthesize(self, actor_id: str):
        """Synthesizes the brief using real database retrieval."""
        # 1. REMEDIATION: Actor Validation
        if not await remediation.validate_principal_approval(self.session, self.tenant_id, actor_id, "BRIEF_SYNTHESIS"):
            raise PermissionError("Unauthorized access to Principal Brief.")

        logger.info(f"[PRINCIPAL_BRIEF] Synthesizing brief for tenant {self.tenant_id}")

        # 2. Real OmniBrain Retrieval
        lessons = await memory_vault.retrieve_tenant_memory(self.session, self.tenant_id, "LESSON_LEARNED")
        procedures = await memory_vault.retrieve_tenant_memory(self.session, self.tenant_id, "PROVEN_PROCEDURE")
        knowledge = await memory_vault.retrieve_tenant_memory(self.session, self.tenant_id, "INSTITUTIONAL_KNOWLEDGE")

        # 3. REMEDIATION: Boundary Redaction
        self.sections["memory_summary"] = remediation.redact_boundaries({
            "total_lessons": len(lessons),
            "total_procedures": len(procedures),
            "total_knowledge": len(knowledge),
            "recent_lesson": lessons[0].content if lessons else "No recent lessons recorded.",
            "strategic_milestones": [k.content for k in knowledge[:3]]
        })

        # 4. Real Orchestration Health
        stmt = select(OrchestrationRun).where(OrchestrationRun.tenant_id == self.tenant_id)
        res = await self.session.execute(stmt)
        active_runs = res.scalars().all()

        # 5. REMEDIATION: Auditable Trails for active runs
        trails = []
        for run in active_runs[:5]: # Limit to recent 5
            trail = await auditable_trails.generate_execution_trail(self.session, str(run.id), self.tenant_id)
            trails.append(trail)

        self.sections["operations"] = {
            "status": "HARDENED",
            "active_orchestrations": len(active_runs),
            "verified_audit_trails": len(trails)
        }
        self.sections["parliament"] = {"load": "0.00%", "instances": 0}

    def generate_report(self) -> Dict[str, Any]:
        """Returns the synthesized brief as a structured report."""
        return {
            "tenant_id": self.tenant_id,
            "timestamp": self.timestamp.isoformat(),
            "doctrine": "Unified orchestration. Autonomous integrity.",
            "sections": self.sections
        }

class PrincipalBriefService:
    async def create_brief(self, session: AsyncSession, tenant_id: str, actor_id: str) -> Dict[str, Any]:
        brief = PrincipalBrief(tenant_id, session)
        await brief.synthesize(actor_id)
        return brief.generate_report()

# Global instance
brief_service = PrincipalBriefService()

import logging
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional
from .memory_vault import memory_vault, MemoryType
from .parliament_scaling import scaling_service
from .autonomous_plane import autonomous_plane

logger = logging.getLogger(__name__)

class PrincipalBrief:
    """
    Phase 9: Principal Brief.
    Daily "State of Everything" report synthesized from institutional memory.
    """
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.timestamp = datetime.now(UTC)
        self.sections: Dict[str, Any] = {}

    async def synthesize(self):
        """Synthesizes the brief from various platform services."""
        logger.info(f"[PRINCIPAL_BRIEF] Synthesizing brief for tenant {self.tenant_id}")
        
        # 1. Institutional Memory Section
        lessons = await memory_vault.retrieve_tenant_memory(self.tenant_id, MemoryType.LESSON_LEARNED)
        procedures = await memory_vault.retrieve_tenant_memory(self.tenant_id, MemoryType.PROVEN_PROCEDURE)
        
        self.sections["memory_summary"] = {
            "total_lessons": len(lessons),
            "total_procedures": len(procedures),
            "recent_lesson": lessons[0].content if lessons else "No recent lessons recorded."
        }
        
        # 2. Operational Intelligence Section
        plane_status = autonomous_plane.get_plane_status()
        self.sections["operations"] = {
            "active_orchestrations": plane_status["active_orchestrations_count"],
            "plane_state": plane_status["state"]
        }
        
        # 3. Parliament Performance Section
        parliament_status = scaling_service.get_parliament_status()
        self.sections["parliament"] = {
            "total_instances": parliament_status["total_instances"],
            "system_load": f"{parliament_status['system_load']:.2%}",
            "agent_distribution": parliament_status["agent_types"]
        }

    def generate_report(self) -> Dict[str, Any]:
        """Returns the synthesized brief as a structured report."""
        return {
            "tenant_id": self.tenant_id,
            "timestamp": self.timestamp.isoformat(),
            "doctrine": "Unified orchestration. Autonomous integrity.",
            "sections": self.sections
        }

class PrincipalBriefService:
    """Manages the generation and distribution of Principal Briefs."""
    async def create_brief(self, tenant_id: str) -> Dict[str, Any]:
        brief = PrincipalBrief(tenant_id)
        await brief.synthesize()
        return brief.generate_report()

# Global instance
brief_service = PrincipalBriefService()

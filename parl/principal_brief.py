"""GOD-0 read-only Principal Brief and Mission Control snapshot."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from memory.knowledge_graph import KnowledgeGraphStore
from memory.memory_engine import MemoryEngine
from parl.god_mode import GodModeTier, PrincipalSession
from parl.orchestrator import PARLOrchestrator


@dataclass
class PrincipalBrief:
    generated_at: str
    principal_id: str
    system_health: Dict[str, Any]
    agent_parliament: Dict[str, Any]
    memory_health: Dict[str, Any]
    graph_health: Dict[str, Any]
    pending_approvals: list[Dict[str, Any]]
    critical: list[Dict[str, Any]]
    recommended_actions: list[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PrincipalBriefService:
    """Read-only aggregation service for Principal Command GOD-0."""

    def __init__(
        self,
        orchestrator: PARLOrchestrator,
        memory_engine: Optional[MemoryEngine] = None,
        graph_store: Optional[KnowledgeGraphStore] = None,
    ):
        self.orchestrator = orchestrator
        self.memory_engine = memory_engine or MemoryEngine()
        self.graph_store = graph_store or KnowledgeGraphStore()

    @staticmethod
    def _require_god0(session: PrincipalSession) -> None:
        if not session.authenticated:
            raise PermissionError("Principal Brief requires authenticated Principal Command")
        if session.expired:
            raise PermissionError("Principal Command session expired")
        if session.tier < GodModeTier.GLOBAL_READ:
            raise PermissionError("GOD-0 or higher is required")

    def build(self, session: PrincipalSession) -> PrincipalBrief:
        self._require_god0(session)
        history = self.orchestrator.task_history
        failed = [task for task in history if task.failed_count > 0]
        recent = history[-20:]
        agent_types = sorted(getattr(a, "value", str(a)) for a in self.orchestrator._agent_registry)
        critical = [
            {
                "type": "failed_task",
                "task_id": task.task_id,
                "description": task.description,
                "failed_subtasks": task.failed_count,
            }
            for task in failed[-10:]
        ]
        recommendations = []
        if failed:
            recommendations.append(
                {
                    "action": "review_failed_agent_tasks",
                    "reason": f"{len(failed)} task(s) in retained PARL history contain failures",
                    "risk_level": "read",
                }
            )
        return PrincipalBrief(
            generated_at=datetime.now(timezone.utc).isoformat(),
            principal_id=session.principal_id,
            system_health={
                "status": "attention" if critical else "nominal",
                "read_only": True,
                "god_mode_tier": int(session.tier),
            },
            agent_parliament={
                "registered_agent_types": agent_types,
                "task_history_count": len(history),
                "recent_task_count": len(recent),
                "failed_task_count": len(failed),
                "training_step": self.orchestrator.training_step,
                "buffer": self.orchestrator.buffer_stats(),
            },
            memory_health=self.memory_engine.memory_stats(),
            graph_health=self.graph_store.stats(),
            pending_approvals=[],
            critical=critical,
            recommended_actions=recommendations,
        )

    def mission_control_snapshot(self, session: PrincipalSession) -> Dict[str, Any]:
        """Backend contract for a future Mission Control UI; performs no writes."""
        brief = self.build(session)
        return {
            "mode": "GOD-0",
            "read_only": True,
            "brief": brief.to_dict(),
        }

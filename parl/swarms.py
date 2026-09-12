"""GOD-1 Council, Research, and Build swarm templates."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Dict, List, Optional

from parl.god_mode import GodModeTier, PrincipalSession
from parl.orchestrator import AgentType, Task


class SwarmMode(StrEnum):
    COUNCIL = "council"
    RESEARCH = "research"
    BUILD = "build"


@dataclass(frozen=True)
class SwarmPlan:
    mode: SwarmMode
    objective: str
    subtask_specs: List[Dict[str, Any]]


class GodOneSwarmPlanner:
    """Construct bounded multi-agent missions; never grants write authority."""

    @staticmethod
    def _require_god1(session: PrincipalSession) -> None:
        if not session.authenticated or session.expired:
            raise PermissionError("GOD-1 swarm requires an active authenticated Principal session")
        if session.tier < GodModeTier.GLOBAL_ORCHESTRATION:
            raise PermissionError("GOD-1 or higher is required for swarm orchestration")

    def plan(
        self,
        mode: SwarmMode | str,
        objective: str,
        session: PrincipalSession,
        *,
        context_scope: Optional[Dict[str, Any]] = None,
    ) -> SwarmPlan:
        self._require_god1(session)
        mode = SwarmMode(mode)
        scope = dict(context_scope or {})
        common = {"context_scope": scope, "context_query": objective, "swarm_mode": mode.value}

        if mode is SwarmMode.COUNCIL:
            roles = [
                (AgentType.CHAT, "Planner", "Develop the strongest plan and explicit assumptions."),
                (AgentType.SIGMA, "Verifier", "Challenge claims and identify what evidence would prove them."),
                (AgentType.ZERO, "Skeptic", "Find failure modes, regressions, and operational weaknesses."),
                (AgentType.NOVA, "Operator", "Assess execution feasibility and authority boundaries."),
            ]
        elif mode is SwarmMode.RESEARCH:
            roles = [
                (AgentType.CHAT, "Synthesizer", "Frame the research questions and synthesize findings."),
                (AgentType.SIGMA, "Source Auditor", "Evaluate evidence quality, contradictions, and missing proof."),
                (AgentType.ZERO, "Contrarian", "Search for counterexamples and alternative explanations."),
            ]
        else:
            roles = [
                (AgentType.CHAT, "Architect", "Define implementation structure and acceptance criteria."),
                (AgentType.ZERO, "Implementer", "Produce the smallest reversible implementation increment."),
                (AgentType.SIGMA, "Tester", "Verify behavior, regressions, and quality gates."),
            ]

        specs: List[Dict[str, Any]] = []
        for agent_type, role, instruction in roles:
            specs.append(
                {
                    "agent_type": agent_type,
                    "description": f"{role}: {objective}",
                    "risk_level": "orchestrate",
                    "capability": f"swarm:{mode.value}",
                    "payload": {
                        **common,
                        "role": role,
                        "instruction": instruction,
                        "external_writes_allowed": False,
                    },
                }
            )
        return SwarmPlan(mode=mode, objective=objective, subtask_specs=specs)

    def run(self, orchestrator: Any, plan: SwarmPlan, session: PrincipalSession) -> Task:
        self._require_god1(session)
        return orchestrator.decompose_and_run(
            description=f"{plan.mode.value.title()} swarm: {plan.objective}",
            subtask_specs=plan.subtask_specs,
            principal_session=session,
        )

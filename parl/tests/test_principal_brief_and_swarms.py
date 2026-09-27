from datetime import datetime, timedelta, timezone

import pytest

from parl.god_mode import GodModeTier, PrincipalSession
from parl.orchestrator import PARLOrchestrator
from parl.principal_brief import PrincipalBriefService
from parl.swarms import GodOneSwarmPlanner, SwarmMode


class FakeMemory:
    def memory_stats(self):
        return {"semantic": {"total_entries": 3}, "timestamp": "now"}


class FakeGraph:
    def stats(self):
        return {"nodes": 4, "edges": 5}


def session(tier):
    return PrincipalSession(
        principal_id="principal",
        tier=tier,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )


def test_principal_brief_requires_authenticated_session_and_is_read_only():
    service = PrincipalBriefService(PARLOrchestrator(), FakeMemory(), FakeGraph())
    snapshot = service.mission_control_snapshot(session(GodModeTier.GLOBAL_READ))
    assert snapshot["mode"] == "GOD-0"
    assert snapshot["read_only"] is True
    assert snapshot["brief"]["graph_health"]["edges"] == 5


def test_god_one_swarm_rejects_god_zero():
    planner = GodOneSwarmPlanner()
    with pytest.raises(PermissionError):
        planner.plan(SwarmMode.COUNCIL, "review architecture", session(GodModeTier.GLOBAL_READ))


def test_god_one_swarm_templates_are_non_external():
    planner = GodOneSwarmPlanner()
    for mode in SwarmMode:
        plan = planner.plan(
            mode,
            "review architecture",
            session(GodModeTier.GLOBAL_ORCHESTRATION),
            context_scope={"project_id": "sintraprime"},
        )
        assert plan.subtask_specs
        assert all(spec["risk_level"] == "orchestrate" for spec in plan.subtask_specs)
        assert all(spec["payload"]["external_writes_allowed"] is False for spec in plan.subtask_specs)
        assert all(spec["payload"]["context_scope"]["project_id"] == "sintraprime" for spec in plan.subtask_specs)

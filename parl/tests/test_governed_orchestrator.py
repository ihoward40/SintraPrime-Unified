from datetime import datetime, timedelta, timezone

import pytest

from parl import AgentType, GodModeTier, GovernedPARLOrchestrator, PrincipalSession


def _agent(subtask):
    return {"ok": True, "description": subtask.description}, 1.0


def _principal(tier: GodModeTier, *, step_up: bool = False):
    return PrincipalSession(
        principal_id="principal-test",
        tier=tier,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        step_up_verified=step_up,
    )


def test_read_only_swarm_runs_without_god_mode():
    orch = GovernedPARLOrchestrator(max_workers=1)
    orch.register_agent(AgentType.ZERO, _agent)
    task = orch.decompose_and_run(
        "inspect",
        [{"agent_type": AgentType.ZERO, "description": "inspect repository", "risk_level": "read"}],
    )
    assert task.failed_count == 0
    assert task.completed_count == 1


def test_controlled_write_is_denied_without_principal_session():
    orch = GovernedPARLOrchestrator(max_workers=1)
    orch.register_agent(AgentType.ZERO, _agent)
    with pytest.raises(PermissionError, match="principal session required"):
        orch.decompose_and_run(
            "edit",
            [{"agent_type": AgentType.ZERO, "description": "edit branch", "risk_level": "write"}],
        )


def test_controlled_write_runs_with_god_2_session():
    orch = GovernedPARLOrchestrator(max_workers=1)
    orch.register_agent(AgentType.ZERO, _agent)
    task = orch.decompose_and_run(
        "edit",
        [{"agent_type": AgentType.ZERO, "description": "edit branch", "risk_level": "write"}],
        principal_session=_principal(GodModeTier.CONTROLLED_WRITE),
    )
    assert task.completed_count == 1


def test_external_action_still_requires_explicit_downstream_approval():
    orch = GovernedPARLOrchestrator(max_workers=1)
    orch.register_agent(AgentType.NOVA, _agent)
    with pytest.raises(PermissionError, match="downstream approval"):
        orch.decompose_and_run(
            "send",
            [
                {
                    "agent_type": AgentType.NOVA,
                    "description": "send external message",
                    "risk_level": "external",
                    "payload": {"capability": "send_message"},
                }
            ],
            principal_session=_principal(GodModeTier.EXTERNAL_ACTION),
        )

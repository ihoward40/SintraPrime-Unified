import pytest

from agent_commons.adapters import MockAgentAdapter
from agent_commons.models import RunStatus
from agent_commons.store import AgentCommonsStore
from agent_commons.supervisor import GovernedSupervisor


@pytest.mark.asyncio
async def test_builder_and_reviewer_complete_without_owner_gate():
    store = AgentCommonsStore()
    supervisor = GovernedSupervisor(
        store,
        {
            "builder": MockAgentAdapter(
                "builder", ["build"], {"summary": "candidate", "decision": "ship"}
            ),
            "reviewer": MockAgentAdapter(
                "reviewer",
                ["review"],
                {"summary": "review passed", "approved": True, "decision": "ship"},
            ),
        },
    )

    run = await supervisor.run_objective(
        tenant_id="tenant-a",
        workspace_id="ws-1",
        channel_id="engineering",
        thread_id="thread-1",
        owner_agent="isiah",
        objective="Build a bounded feature",
        builder_agent="builder",
        reviewer_agent="reviewer",
        acceptance_criteria=["tests pass"],
        idempotency_key="objective-1",
    )

    assert run.status is RunStatus.COMPLETED
    assert run.approval_id is None
    messages = store.get_thread("tenant-a", "ws-1", "engineering", "thread-1")
    assert [message["status"] for message in messages] == [
        "ASSIGNED",
        "RESULT",
        "RESULT",
        "RESULT",
    ]


@pytest.mark.asyncio
async def test_material_disagreement_requires_owner_approval():
    store = AgentCommonsStore()
    supervisor = GovernedSupervisor(
        store,
        {
            "builder": MockAgentAdapter("builder", ["build"], {"decision": "ship"}),
            "reviewer": MockAgentAdapter(
                "reviewer",
                ["review"],
                {"approved": False, "material_disagreement": True},
            ),
        },
    )

    run = await supervisor.run_objective(
        tenant_id="tenant-a",
        workspace_id="ws-1",
        channel_id="engineering",
        thread_id="thread-2",
        owner_agent="isiah",
        objective="Review risky change",
        builder_agent="builder",
        reviewer_agent="reviewer",
        acceptance_criteria=["no material defects"],
        idempotency_key="objective-2",
    )

    assert run.status is RunStatus.WAITING_APPROVAL
    assert run.approval_id
    approved = supervisor.approve(
        "tenant-a",
        run.run_id,
        run.approval_id,
        "Owner accepts the risk",
    )
    assert approved.status is RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_prohibited_action_stops_before_agent_invocation():
    store = AgentCommonsStore()
    builder = MockAgentAdapter("builder", ["build"], {"decision": "ship"})
    reviewer = MockAgentAdapter("reviewer", ["review"], {"approved": True})
    supervisor = GovernedSupervisor(store, {"builder": builder, "reviewer": reviewer})

    run = await supervisor.run_objective(
        tenant_id="tenant-a",
        workspace_id="ws-1",
        channel_id="engineering",
        thread_id="thread-3",
        owner_agent="isiah",
        objective="Deploy to production",
        builder_agent="builder",
        reviewer_agent="reviewer",
        acceptance_criteria=[],
        idempotency_key="objective-3",
        requested_actions=["deploy"],
    )

    assert run.status is RunStatus.WAITING_APPROVAL
    assert builder.invocations == []
    assert reviewer.invocations == []


@pytest.mark.asyncio
async def test_idempotency_returns_existing_run():
    store = AgentCommonsStore()
    supervisor = GovernedSupervisor(
        store,
        {
            "builder": MockAgentAdapter("builder", ["build"], {"decision": "ship"}),
            "reviewer": MockAgentAdapter(
                "reviewer",
                ["review"],
                {"approved": True, "decision": "ship"},
            ),
        },
    )
    kwargs = {
        "tenant_id": "tenant-a",
        "workspace_id": "ws-1",
        "channel_id": "engineering",
        "thread_id": "thread-4",
        "owner_agent": "isiah",
        "objective": "Idempotent task",
        "builder_agent": "builder",
        "reviewer_agent": "reviewer",
        "acceptance_criteria": [],
        "idempotency_key": "same-key",
    }
    first = await supervisor.run_objective(**kwargs)
    second = await supervisor.run_objective(**kwargs)
    assert first.run_id == second.run_id


def test_cross_tenant_thread_access_fails_closed():
    store = AgentCommonsStore()
    assert store.get_thread("tenant-b", "ws-1", "engineering", "missing") == []

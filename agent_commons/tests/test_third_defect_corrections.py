from pathlib import Path
from types import SimpleNamespace

import pytest

from agent_commons.adapters import MockAgentAdapter
from agent_commons.events import AgentCommonsEventBus
from agent_commons.models import RunStatus, SupervisorRun
from agent_commons.store import AgentCommonsStore
from agent_commons.supervisor import GovernedSupervisor
from portal.routers import agent_commons


def test_frontend_uses_portal_token_and_authoritative_resync():
    source = Path("web/src/pages/AgentCommons.tsx").read_text(encoding="utf-8")

    assert "sintraprime_token" in source
    assert "localStorage.getItem('access_token')" not in source
    assert "'/runs?limit=50'" in source
    assert "await loadRuns();" in source


def test_runtime_uses_authoritative_portal_environment(monkeypatch):
    monkeypatch.setattr(
        agent_commons,
        "get_settings",
        lambda: SimpleNamespace(ENVIRONMENT="production"),
    )
    monkeypatch.setenv("AGENT_COMMONS_STORAGE_MODE", "sqlite")
    monkeypatch.setenv("AGENT_COMMONS_EVENT_BACKEND", "redis")

    with pytest.raises(RuntimeError, match="shared PostgreSQL"):
        agent_commons.validate_runtime_backends()


def test_multi_worker_count_blocks_in_process_events(monkeypatch):
    monkeypatch.setattr(
        agent_commons,
        "get_settings",
        lambda: SimpleNamespace(ENVIRONMENT="development"),
    )
    monkeypatch.setenv("WEB_CONCURRENCY", "4")
    monkeypatch.setenv("AGENT_COMMONS_STORAGE_MODE", "sqlite")
    monkeypatch.setenv("AGENT_COMMONS_EVENT_BACKEND", "in_process")

    with pytest.raises(RuntimeError, match="shared event broker"):
        agent_commons.validate_runtime_backends()


def test_list_runs_is_tenant_scoped_and_recent_first():
    store = AgentCommonsStore()
    first = SupervisorRun(
        tenant_id="tenant-a",
        workspace_id="ws",
        channel_id="channel",
        thread_id="thread-a",
        objective="first",
        owner_agent="owner",
        builder_agent="builder",
        reviewer_agent="reviewer",
        acceptance_criteria=[],
    )
    second = SupervisorRun(
        tenant_id="tenant-b",
        workspace_id="ws",
        channel_id="channel",
        thread_id="thread-b",
        objective="other tenant",
        owner_agent="owner",
        builder_agent="builder",
        reviewer_agent="reviewer",
        acceptance_criteria=[],
    )
    store.save_run(first, idempotency_key="first-key")
    store.save_run(second, idempotency_key="second-key")

    runs = store.list_runs("tenant-a")
    assert [run.run_id for run in runs] == [first.run_id]


@pytest.mark.asyncio
async def test_approved_action_gate_does_not_claim_completion():
    store = AgentCommonsStore()
    supervisor = GovernedSupervisor(
        store,
        {
            "builder": MockAgentAdapter("builder", ["build"], {"decision": "ship"}),
            "reviewer": MockAgentAdapter("reviewer", ["review"], {"approved": True}),
        },
    )
    run = await supervisor.run_objective(
        tenant_id="tenant-a",
        workspace_id="ws",
        channel_id="channel",
        thread_id="thread",
        owner_agent="owner",
        objective="Deploy after approval",
        builder_agent="builder",
        reviewer_agent="reviewer",
        acceptance_criteria=[],
        idempotency_key="approval-key",
        requested_actions=["deploy"],
    )
    assert run.status is RunStatus.WAITING_APPROVAL

    updated = await agent_commons.approve_run(
        run.run_id,
        agent_commons.ApprovalRequest(note="approved"),
        user=SimpleNamespace(tenant_id="tenant-a", user_id="owner"),
        supervisor=supervisor,
        events=AgentCommonsEventBus(),
    )

    assert updated["status"] == RunStatus.PENDING.value
    assert updated["reconciliation"]["execution_pending"] is True
    assert updated["builder_result"] is None

    messages = store.get_thread("tenant-a", "ws", "channel", "thread")
    statuses = [message["status"] for message in messages]
    assert statuses == ["BLOCKED", "ACK"]
    assert "CLOSED" not in statuses
    assert messages[-1]["payload"]["execution_pending"] is True

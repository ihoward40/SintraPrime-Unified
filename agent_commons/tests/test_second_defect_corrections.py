from types import SimpleNamespace

import pytest

from agent_commons.adapters import MockAgentAdapter
from agent_commons.events import AgentCommonsEventBus
from agent_commons.models import RunStatus, SupervisorRun
from agent_commons.store import AgentCommonsStore
from agent_commons.supervisor import GovernedSupervisor
from portal.routers import agent_commons


def set_environment(monkeypatch, environment: str) -> None:
    monkeypatch.setattr(
        agent_commons,
        "get_settings",
        lambda: SimpleNamespace(ENVIRONMENT=environment),
    )


@pytest.mark.asyncio
async def test_heartbeat_timeout_preserves_subscription():
    events = AgentCommonsEventBus()
    subscription = await events.open_subscription("tenant-a")
    try:
        assert await events.next_event(subscription, 0.001) is None
        await events.publish("tenant-a", {"type": "after-heartbeat"})
        delivered = await events.next_event(subscription, 0.1)
        assert delivered is not None
        assert delivered["type"] == "after-heartbeat"
    finally:
        await events.close_subscription(subscription)


class FailingAdapter(MockAgentAdapter):
    async def invoke(self, task, context):
        del task, context
        raise TimeoutError("provider timeout")


@pytest.mark.asyncio
async def test_invocation_failure_is_persisted_as_failed():
    store = AgentCommonsStore()
    supervisor = GovernedSupervisor(
        store,
        {
            "builder": FailingAdapter("builder", ["build"], {}),
            "reviewer": MockAgentAdapter("reviewer", ["review"], {"approved": True}),
        },
    )

    with pytest.raises(TimeoutError, match="provider timeout"):
        await supervisor.run_objective(
            tenant_id="tenant-a",
            workspace_id="ws",
            channel_id="engineering",
            thread_id="failure-thread",
            owner_agent="owner",
            objective="Exercise timeout handling",
            builder_agent="builder",
            reviewer_agent="reviewer",
            acceptance_criteria=[],
            idempotency_key="failure-key",
        )

    messages = store.get_thread("tenant-a", "ws", "engineering", "failure-thread")
    run_id = messages[0]["trace"]["supervisor_run_id"]
    persisted = store.get_run("tenant-a", run_id)
    assert persisted.status is RunStatus.FAILED
    assert persisted.reconciliation == {
        "summary": "Agent invocation failed.",
        "failure_type": "TimeoutError",
        "failed_agent": "builder",
    }


def test_task_and_idempotency_uniqueness_are_tenant_scoped():
    store = AgentCommonsStore()
    common = {
        "workspace_id": "ws",
        "channel_id": "engineering",
        "thread_id": "thread",
        "objective": "Tenant scoped run",
        "owner_agent": "owner",
        "builder_agent": "builder",
        "reviewer_agent": "reviewer",
        "acceptance_criteria": [],
        "task_id": "SPU-SHARED-TASK",
    }
    first = SupervisorRun(tenant_id="tenant-a", **common)
    second = SupervisorRun(tenant_id="tenant-b", **common)

    store.save_run(first, idempotency_key="shared-idempotency-key")
    store.save_run(second, idempotency_key="shared-idempotency-key")

    assert store.get_run("tenant-a", first.run_id).tenant_id == "tenant-a"
    assert store.get_run("tenant-b", second.run_id).tenant_id == "tenant-b"


def test_production_requires_shared_postgres(monkeypatch):
    set_environment(monkeypatch, "production")
    monkeypatch.setenv("AGENT_COMMONS_STORAGE_MODE", "sqlite")
    monkeypatch.setenv("AGENT_COMMONS_EVENT_BACKEND", "redis")

    with pytest.raises(RuntimeError, match="shared PostgreSQL"):
        agent_commons.validate_runtime_backends()


def test_multi_worker_requires_shared_event_broker(monkeypatch):
    set_environment(monkeypatch, "development")
    monkeypatch.setenv("WEB_CONCURRENCY", "4")
    monkeypatch.setenv("AGENT_COMMONS_STORAGE_MODE", "sqlite")
    monkeypatch.setenv("AGENT_COMMONS_EVENT_BACKEND", "in_process")

    with pytest.raises(RuntimeError, match="shared event broker"):
        agent_commons.validate_runtime_backends()


def test_unimplemented_shared_backends_remain_fail_closed(monkeypatch):
    set_environment(monkeypatch, "development")
    monkeypatch.setenv("WEB_CONCURRENCY", "1")
    monkeypatch.setenv("AGENT_COMMONS_STORAGE_MODE", "postgres")
    monkeypatch.setenv("AGENT_COMMONS_EVENT_BACKEND", "in_process")

    with pytest.raises(RuntimeError, match="not implemented"):
        agent_commons.validate_runtime_backends()

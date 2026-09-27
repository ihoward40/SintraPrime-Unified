from __future__ import annotations

import concurrent.futures
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import orchestration.orchestration_api as orchestration_api
from orchestration.a2a_protocol import A2AProtocol
from orchestration.agent_commons import (
    AgentCommonsStore,
    LoopDetectedError,
    MockAgentAdapter,
    Principal,
    SupervisorAgent,
)
from orchestration.orchestration_api import create_app


def _headers(tenant: str, principal: str, role: str) -> dict[str, str]:
    return {
        "X-Tenant-Id": tenant,
        "X-Principal-Id": principal,
        "X-Role": role,
    }


def _reset_commons() -> None:
    orchestration_api._commons_store = None
    orchestration_api._supervisor = None
    orchestration_api._a2a = None


def _client(tmp_path: Path) -> TestClient:
    _reset_commons()
    db_path = tmp_path / "agent-commons.db"
    ledger_dir = tmp_path / "ledger"
    import os

    os.environ["AGENT_COMMONS_DB_PATH"] = str(db_path)
    os.environ["AGENT_COMMONS_LEDGER_DIR"] = str(ledger_dir)
    return TestClient(create_app())


@pytest.mark.asyncio
async def test_supervisor_completes_governed_lifecycle_with_correlated_messages(tmp_path: Path):
    store = AgentCommonsStore(db_path=str(tmp_path / "commons.db"), ledger_dir=tmp_path / "ledger")
    proto = A2AProtocol()
    supervisor = SupervisorAgent(store, protocol=proto)
    supervisor.register_adapter(MockAgentAdapter("builder-agent", "Builder Agent", "worker", ["build"]))
    supervisor.register_adapter(MockAgentAdapter("reviewer-agent", "Reviewer Agent", "reviewer", ["review"]))

    workspace = store.create_workspace("tenant-a", "Governed Workspace")
    channel = store.create_channel("tenant-a", workspace["workspace_id"], "deliveries")

    thread = await supervisor.submit_objective(
        principal=Principal("tenant-a", "owner-1", "owner"),
        workspace_id=workspace["workspace_id"],
        channel_id=channel["channel_id"],
        objective="Prepare a governed implementation plan",
        acceptance_criteria=["complete the bounded task", "perform independent review"],
    )

    assert len(proto.get_all_agents()) >= 3
    assert thread["lifecycle_status"] == "CLOSED"
    assert {event["status"] for event in thread["task_events"]} >= {"ASSIGNED", "RESULT", "CLOSED"}

    correlated = [
        message for message in thread["messages"]
        if message["sender"] in {"builder-agent", "reviewer-agent"}
    ]
    assert correlated
    assert len({message["correlation_id"] for message in correlated}) == 1


@pytest.mark.asyncio
async def test_material_disagreement_creates_owner_approval_request(tmp_path: Path):
    store = AgentCommonsStore(db_path=str(tmp_path / "commons.db"), ledger_dir=tmp_path / "ledger")
    proto = A2AProtocol()
    supervisor = SupervisorAgent(store, protocol=proto)
    supervisor.register_adapter(MockAgentAdapter("builder-agent", "Builder Agent", "worker", ["build"]))
    supervisor.register_adapter(
        MockAgentAdapter("reviewer-agent", "Reviewer Agent", "reviewer", ["review"], reviewer_disagrees=True)
    )

    workspace = store.create_workspace("tenant-a", "Governed Workspace")
    channel = store.create_channel("tenant-a", workspace["workspace_id"], "deliveries")

    thread = await supervisor.submit_objective(
        principal=Principal("tenant-a", "owner-1", "owner"),
        workspace_id=workspace["workspace_id"],
        channel_id=channel["channel_id"],
        objective="Prepare a disputed result",
    )

    assert thread["lifecycle_status"] == "BLOCKED"
    assert thread["approvals"]
    assert thread["approvals"][0]["status"] == "PENDING"


def test_start_agent_run_is_idempotent_under_concurrency(tmp_path: Path):
    store = AgentCommonsStore(db_path=str(tmp_path / "commons.db"), ledger_dir=tmp_path / "ledger")
    workspace = store.create_workspace("tenant-a", "Workspace A")
    channel = store.create_channel("tenant-a", workspace["workspace_id"], "general")
    thread = store.create_thread("tenant-a", workspace["workspace_id"], channel["channel_id"], "Concurrent Thread")

    def start() -> str:
        run = store.start_agent_run(
            tenant_id="tenant-a",
            workspace_id=workspace["workspace_id"],
            channel_id=channel["channel_id"],
            thread_id=thread["thread_id"],
            task_id=thread["task_id"],
            agent_id="builder-agent",
            role="worker",
            correlation_id="corr-1",
            context={"thread_history": []},
            idempotency_key="same-run",
        )
        return run["run_id"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        first, second = [future.result() for future in [pool.submit(start), pool.submit(start)]]

    assert first == second


@pytest.mark.asyncio
async def test_objective_idempotency_reservation_releases_after_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    store = AgentCommonsStore(db_path=str(tmp_path / "commons.db"), ledger_dir=tmp_path / "ledger")
    proto = A2AProtocol()
    supervisor = SupervisorAgent(store, protocol=proto)
    supervisor.register_adapter(MockAgentAdapter("builder-agent", "Builder Agent", "worker", ["build"]))
    supervisor.register_adapter(MockAgentAdapter("reviewer-agent", "Reviewer Agent", "reviewer", ["review"]))
    workspace = store.create_workspace("tenant-a", "Governed Workspace")
    channel = store.create_channel("tenant-a", workspace["workspace_id"], "deliveries")

    original = store.create_thread

    def explode(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(store, "create_thread", explode)
    with pytest.raises(RuntimeError):
        await supervisor.submit_objective(
            principal=Principal("tenant-a", "owner-1", "owner"),
            workspace_id=workspace["workspace_id"],
            channel_id=channel["channel_id"],
            objective="Will fail once",
            idempotency_key="retryable-key",
        )

    monkeypatch.setattr(store, "create_thread", original)
    thread = await supervisor.submit_objective(
        principal=Principal("tenant-a", "owner-1", "owner"),
        workspace_id=workspace["workspace_id"],
        channel_id=channel["channel_id"],
        objective="Will fail once",
        idempotency_key="retryable-key",
    )

    assert thread["thread_id"]


def test_agent_commons_persistence_survives_restart(tmp_path: Path):
    db_path = tmp_path / "commons.db"
    ledger_dir = tmp_path / "ledger"

    store_a = AgentCommonsStore(db_path=str(db_path), ledger_dir=ledger_dir)
    workspace = store_a.create_workspace("tenant-a", "Workspace A")
    channel = store_a.create_channel("tenant-a", workspace["workspace_id"], "general")
    thread = store_a.create_thread("tenant-a", workspace["workspace_id"], channel["channel_id"], "Persistent Thread")
    store_a.add_message(
        tenant_id="tenant-a",
        workspace_id=workspace["workspace_id"],
        channel_id=channel["channel_id"],
        thread_id=thread["thread_id"],
        task_id=thread["task_id"],
        sender="owner-1",
        recipients=["chatgpt-supervisor"],
        correlation_id="corr-1",
        lifecycle_status="ASSIGNED",
        payload={"objective": "persist"},
        evidence=[{"kind": "mock", "uri": "mock://persist", "title": "Persist evidence"}],
        trace={"run_id": "run-1"},
    )
    store_a.add_task_event(
        tenant_id="tenant-a",
        workspace_id=workspace["workspace_id"],
        channel_id=channel["channel_id"],
        thread_id=thread["thread_id"],
        task_id=thread["task_id"],
        status="ASSIGNED",
        actor="owner-1",
        details={"objective": "persist", "notes": "persist event"},
        run_id="run-1",
    )

    store_b = AgentCommonsStore(db_path=str(db_path), ledger_dir=ledger_dir)
    reloaded = store_b.get_thread(thread["thread_id"], "tenant-a")
    assert reloaded is not None
    assert reloaded["messages"][0]["payload"]["objective"] == "persist"
    assert reloaded["task_events"][0]["status"] == "ASSIGNED"


def test_commons_api_enforces_tenant_isolation_and_idempotency(tmp_path: Path):
    client = _client(tmp_path)

    workspace = client.post(
        "/orchestration/commons/workspaces",
        headers=_headers("tenant-a", "owner-1", "owner"),
        json={"name": "Workspace A"},
    ).json()
    channel = client.post(
        "/orchestration/commons/channels",
        headers=_headers("tenant-a", "owner-1", "owner"),
        json={"workspace_id": workspace["workspace_id"], "name": "general"},
    ).json()

    payload = {
        "workspace_id": workspace["workspace_id"],
        "channel_id": channel["channel_id"],
        "objective": "Produce a bounded result",
        "idempotency_key": "dedupe-1",
    }
    first = client.post(
        "/orchestration/supervisor/objectives",
        headers=_headers("tenant-a", "owner-1", "owner"),
        json=payload,
    )
    second = client.post(
        "/orchestration/supervisor/objectives",
        headers=_headers("tenant-a", "owner-1", "owner"),
        json=payload,
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["thread_id"] == second.json()["thread_id"]

    forbidden = client.get(
        f"/orchestration/commons/threads/{first.json()['thread_id']}",
        headers=_headers("tenant-b", "owner-2", "owner"),
    )
    assert forbidden.status_code == 404

    cross_tenant_channel = client.post(
        "/orchestration/commons/channels",
        headers=_headers("tenant-b", "owner-2", "owner"),
        json={"workspace_id": workspace["workspace_id"], "name": "forbidden"},
    )
    assert cross_tenant_channel.status_code == 404

    cross_tenant_thread = client.post(
        "/orchestration/commons/threads",
        headers=_headers("tenant-b", "owner-2", "owner"),
        json={
            "workspace_id": workspace["workspace_id"],
            "channel_id": channel["channel_id"],
            "title": "forbidden",
        },
    )
    assert cross_tenant_thread.status_code == 404


def test_commons_api_records_manual_thread_messages_and_health(tmp_path: Path):
    client = _client(tmp_path)
    headers = _headers("tenant-a", "owner-1", "owner")

    workspace = client.post("/orchestration/commons/workspaces", headers=headers, json={"name": "Workspace A"}).json()
    channel = client.post(
        "/orchestration/commons/channels",
        headers=headers,
        json={"workspace_id": workspace["workspace_id"], "name": "general"},
    ).json()
    thread = client.post(
        "/orchestration/commons/threads",
        headers=headers,
        json={"workspace_id": workspace["workspace_id"], "channel_id": channel["channel_id"], "title": "Manual Thread"},
    ).json()

    message = client.post(
        f"/orchestration/commons/threads/{thread['thread_id']}/messages",
        headers=headers,
        json={
            "workspace_id": workspace["workspace_id"],
            "channel_id": channel["channel_id"],
            "task_id": thread["task_id"],
            "recipients": ["chatgpt-supervisor"],
            "lifecycle_status": "IN_PROGRESS",
            "payload": {"text": "hello"},
            "evidence": [{"kind": "link", "uri": "mock://evidence", "title": "Evidence"}],
            "trace": {"run_id": "manual-run"},
        },
    )

    assert message.status_code == 201
    assert message.json()["trace"]["run_id"] == "manual-run"

    rejected = client.post(
        f"/orchestration/commons/threads/{thread['thread_id']}/messages",
        headers=_headers("tenant-b", "owner-2", "owner"),
        json={
            "workspace_id": workspace["workspace_id"],
            "channel_id": channel["channel_id"],
            "task_id": thread["task_id"],
            "recipients": ["chatgpt-supervisor"],
            "lifecycle_status": "IN_PROGRESS",
            "payload": {"text": "bad tenant"},
        },
    )
    assert rejected.status_code == 404

    mismatched = client.post(
        f"/orchestration/commons/threads/{thread['thread_id']}/messages",
        headers=headers,
        json={
            "workspace_id": workspace["workspace_id"],
            "channel_id": "wrong-channel",
            "task_id": thread["task_id"],
            "recipients": ["chatgpt-supervisor"],
            "lifecycle_status": "IN_PROGRESS",
            "payload": {"text": "mismatch"},
        },
    )
    assert mismatched.status_code == 400

    health = client.get("/orchestration/commons/agents/builder-agent/health", headers=headers)
    assert health.status_code == 200
    assert health.json()["status"] in {"healthy", "degraded"}


@pytest.mark.asyncio
async def test_loop_detection_stops_recursive_delegation(tmp_path: Path):
    store = AgentCommonsStore(db_path=str(tmp_path / "commons.db"), ledger_dir=tmp_path / "ledger")
    proto = A2AProtocol()
    supervisor = SupervisorAgent(store, protocol=proto, max_delegation_depth=2)
    builder = supervisor.register_adapter(MockAgentAdapter("builder-agent", "Builder Agent", "worker", ["build"]))
    workspace = store.create_workspace("tenant-a", "Governed Workspace")
    channel = store.create_channel("tenant-a", workspace["workspace_id"], "deliveries")
    thread = store.create_thread("tenant-a", workspace["workspace_id"], channel["channel_id"], "Loop Thread")

    with pytest.raises(LoopDetectedError):
        await supervisor._delegate(
            tenant_id="tenant-a",
            workspace_id=workspace["workspace_id"],
            channel_id=channel["channel_id"],
            thread_id=thread["thread_id"],
            task_id=thread["task_id"],
            sender="chatgpt-supervisor",
            target=builder,
            objective="recursive task",
            acceptance_criteria=["avoid loops"],
            correlation_id="corr-loop",
            trace={"agent_path": ["chatgpt-supervisor", "builder-agent"], "parent_run_id": None},
            idempotency_key="loop-1",
            context={"thread_history": []},
        )

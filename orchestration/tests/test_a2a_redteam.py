from __future__ import annotations

import json

import pytest

from orchestration.a2a_audit import A2AAuditStore
from orchestration.a2a_governance import ApprovalReceipt, content_hash, issue_approval
from orchestration.a2a_protocol import A2AProtocol, Message, MessageBus, MessageType
from orchestration.agent_identity import AgentPrincipal, authenticate_agent
from orchestration.agent_policy import AgentPolicy
from orchestration.approval_store import ApprovalStore
from orchestration.execution_worker import ExecutionWorker
from orchestration.orchestration_api import SendMessageRequest, send_agent_message
from orchestration.outbox import DurableOutbox
from orchestration.tests.test_redis_a2a import FakeRedis
from orchestration.redis_a2a import RedisA2ATransport


@pytest.mark.asyncio
async def test_redteam_raw_memory_external_intent_is_blocked_and_audited(tmp_path):
    audit = A2AAuditStore(str(tmp_path / "audit.jsonl"))
    bus = MessageBus(audit_store=audit)
    message = Message("orchestrator", "dispatch_desk", MessageType.REQUEST, {"action": "send_external_message"})
    with pytest.raises(PermissionError):
        await bus.publish(message)
    assert audit.read()[-1]["reason_code"] == "raw_external_intent"


@pytest.mark.asyncio
async def test_redteam_raw_redis_external_intent_is_blocked_and_audited(tmp_path):
    audit = A2AAuditStore(str(tmp_path / "audit.jsonl"))
    transport = RedisA2ATransport(namespace="redteam", audit_store=audit)
    transport._redis = FakeRedis()
    message = Message("orchestrator", "dispatch_desk", MessageType.REQUEST, {"action": "send_external_message"})
    with pytest.raises(PermissionError):
        await transport.send(message)
    assert audit.read()[-1]["reason_code"] == "redis_delivery"
    assert audit.read()[-1]["status"] == "blocked"


@pytest.mark.asyncio
async def test_redteam_http_external_action_is_blocked(tmp_path):
    audit = A2AAuditStore(str(tmp_path / "audit.jsonl"))
    request = SendMessageRequest(from_agent="dispatch_desk", to_agent="third_party", message_type="REQUEST", payload={"action": "send_external_message"}, external_action=True)
    with pytest.raises(Exception):
        await send_agent_message(request, A2AProtocol(), None, audit, AgentPolicy(), AgentPrincipal("dispatch_desk", "tenant-a"))
    assert audit.read()[-1]["status"] == "blocked"


def test_redteam_identity_and_tenant_crossing_are_blocked(monkeypatch):
    monkeypatch.setenv("A2A_AGENT_CREDENTIALS", json.dumps({"token-a": {"agent_id": "orchestrator", "tenant_id": "tenant-a"}}))
    assert authenticate_agent("token-a", "tenant-a").agent_id == "orchestrator"
    with pytest.raises(PermissionError):
        authenticate_agent("token-a", "tenant-b")
    with pytest.raises(PermissionError):
        AgentPolicy().authorize_sender("dispatch_desk")
    with pytest.raises(PermissionError):
        AgentPolicy().authorize_sender("blackstone_verifier")


def test_redteam_approval_misuse_is_blocked(monkeypatch, tmp_path):
    monkeypatch.setenv("A2A_APPROVAL_HMAC_SECRET", "redteam-secret")
    payload_hash = content_hash({"body": "approved"})
    receipt = issue_approval(approved_by="user", approved_output_id="r", sender_agent_id="orchestrator", tenant_id="tenant-a", recipient="blackstone_verifier", final_content_hash=payload_hash, expires_at=9999999999)
    store = ApprovalStore(str(tmp_path / "approvals.jsonl"))
    store.issue(receipt)
    store.verify_and_consume(receipt)
    with pytest.raises(PermissionError):
        store.verify_and_consume(receipt)
    forged = ApprovalReceipt("user", "r", "blackstone_verifier", payload_hash, sender_agent_id="orchestrator", tenant_id="tenant-a", expires_at=9999999999)
    with pytest.raises(PermissionError):
        from orchestration.a2a_governance import verify_approval
        verify_approval(forged, sender_agent_id="orchestrator", tenant_id="tenant-a")


def test_redteam_outbox_terminal_replay_and_payload_drift_are_blocked(monkeypatch, tmp_path):
    monkeypatch.setenv("A2A_APPROVAL_HMAC_SECRET", "redteam-secret")
    payload_hash = content_hash({"body": "approved"})
    receipt = issue_approval(approved_by="user", approved_output_id="r2", sender_agent_id="orchestrator", tenant_id="tenant-a", recipient="blackstone_verifier", final_content_hash=payload_hash, expires_at=9999999999)
    approvals = ApprovalStore(str(tmp_path / "approvals.jsonl"))
    approvals.issue(receipt)
    outbox = DurableOutbox(str(tmp_path / "outbox.jsonl"))
    outbox_id = outbox.enqueue(receipt_id=receipt.receipt_id, sender_agent_id="orchestrator", tenant_id="tenant-a", recipient="blackstone_verifier", payload_hash=payload_hash)
    worker = ExecutionWorker(outbox=outbox, approval_store=approvals, agent_policy=AgentPolicy())
    result = worker.run_once(outbox_id, payload_hash=payload_hash, tenant_id="tenant-a")
    assert result["status"] == "blocked"
    with pytest.raises(PermissionError):
        worker.run_once(outbox_id, payload_hash=payload_hash, tenant_id="tenant-a")


def test_redteam_registry_has_no_external_capability():
    import json as json_module
    from pathlib import Path
    registry = json_module.loads((Path(__file__).parents[1] / "agent_registry.json").read_text())
    assert all(not agent["can_send_external"] for agent in registry["agents"])
    assert next(agent for agent in registry["agents"] if agent["agent_id"] == "dispatch_desk")["status"] == "blocked"

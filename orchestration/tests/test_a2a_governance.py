from __future__ import annotations

import pytest

from orchestration.a2a_governance import (
    ApprovalReceipt,
    ClaimStatus,
    DispatchAudit,
    EvidenceClaim,
    content_hash,
    issue_approval,
    validate_dispatch,
)
from orchestration.a2a_audit import A2AAuditStore
from orchestration.a2a_protocol import A2AProtocol, Message, MessageBus, MessageType
from orchestration.agent_policy import AgentPolicy
from orchestration.agent_identity import AgentPrincipal
from orchestration.orchestration_api import SendMessageRequest, send_agent_message


def test_internal_message_can_be_sent_without_approval():
    assert validate_dispatch(
        payload={"task": "review"},
        recipient="reviewer",
        external_action=False,
    ) == content_hash({"task": "review"})


def test_external_action_requires_approval():
    with pytest.raises(PermissionError, match="approval receipt"):
        validate_dispatch(payload={"body": "send"}, recipient="counsel", external_action=True)


def test_unsupported_claim_blocks_dispatch():
    with pytest.raises(PermissionError, match="unsupported or risky"):
        validate_dispatch(
            payload={"body": "claim"},
            recipient="reviewer",
            external_action=False,
            claims=[EvidenceClaim("claim", ClaimStatus.UNSUPPORTED)],
        )


def test_content_hash_mismatch_blocks_external_action(monkeypatch):
    monkeypatch.setenv("A2A_APPROVAL_HMAC_SECRET", "test-secret")
    approval = issue_approval(
        approved_by="user-1",
        approved_output_id="out-1",
        sender_agent_id="sender",
        recipient="counsel",
        final_content_hash=content_hash({"body": "approved"}),
        expires_at=9999999999,
    )
    with pytest.raises(PermissionError, match="content hash"):
        validate_dispatch(
            payload={"body": "changed after approval"},
            recipient="counsel",
            external_action=True,
            sender_agent_id="sender",
            approval=approval,
        )


def test_matching_approval_passes(monkeypatch):
    monkeypatch.setenv("A2A_APPROVAL_HMAC_SECRET", "test-secret")
    payload = {"body": "approved"}
    result = validate_dispatch(
        payload=payload,
        recipient="counsel",
        external_action=True,
        sender_agent_id="sender",
        approval=issue_approval(
            approved_by="user-1",
            approved_output_id="out-1",
            sender_agent_id="sender",
            recipient="counsel",
            final_content_hash=content_hash(payload),
            expires_at=9999999999,
        ),
    )
    assert result == content_hash(payload)


def test_forged_matching_approval_is_rejected(monkeypatch):
    monkeypatch.setenv("A2A_APPROVAL_HMAC_SECRET", "test-secret")
    forged = ApprovalReceipt(
        approved_by="user-1",
        approved_output_id="out-1",
        sender_agent_id="sender",
        recipient="counsel",
        final_content_hash=content_hash({"body": "approved"}),
        expires_at=9999999999,
    )
    with pytest.raises(PermissionError, match="unsigned approval"):
        validate_dispatch(
            payload={"body": "approved"},
            recipient="counsel",
            external_action=True,
            sender_agent_id="sender",
            approval=forged,
        )


def test_expired_signed_approval_is_rejected(monkeypatch):
    monkeypatch.setenv("A2A_APPROVAL_HMAC_SECRET", "test-secret")
    expired = issue_approval(
        approved_by="user-1",
        approved_output_id="out-1",
        sender_agent_id="sender",
        recipient="counsel",
        final_content_hash=content_hash({"body": "approved"}),
        expires_at=1,
    )
    with pytest.raises(PermissionError, match="expired"):
        validate_dispatch(
            payload={"body": "approved"},
            recipient="counsel",
            external_action=True,
            sender_agent_id="sender",
            approval=expired,
        )


def test_audit_store_persists_records(tmp_path):
    store = A2AAuditStore(str(tmp_path / "audit.jsonl"))
    record = {
        "mission_id": "run-1",
        "objective": "REQUEST",
        "agents_used": ("a", "b"),
        "sources_used": (),
        "claims_verified": (),
        "risks_flagged": (),
        "user_approval": "not required",
        "external_action_taken": False,
        "final_output_hash": "abc",
        "status": "done",
    }
    store.append(DispatchAudit(**record))
    assert store.read()[0]["mission_id"] == "run-1"


def test_audit_store_survives_fresh_store_reconstruction(tmp_path):
    path = tmp_path / "audit.jsonl"
    first = A2AAuditStore(str(path))
    first.append(DispatchAudit(
        mission_id="restart-run",
        objective="REQUEST",
        agents_used=("a", "b"),
        sources_used=(),
        claims_verified=(),
        risks_flagged=(),
        user_approval="not required",
        external_action_taken=False,
        final_output_hash="hash-1",
        payload_hash="hash-1",
        status="delivered",
    ))

    second = A2AAuditStore(str(path))
    records = second.read()
    assert records[0]["mission_id"] == "restart-run"
    assert records[0]["payload_hash"] == "hash-1"
    assert records[0]["status"] == "delivered"


def test_agent_registry_contains_named_specialists_with_safe_defaults():
    import json
    from pathlib import Path

    registry_path = Path(__file__).parents[2] / "orchestration" / "agent_registry.json"
    registry = json.loads(registry_path.read_text())
    agents = {agent["agent_id"]: agent for agent in registry["agents"]}
    expected = {
        "orchestrator",
        "blackstone_verifier",
        "justice_scribe",
        "source_hunter",
        "trust_vault_clerk",
        "sintraprime_builder",
        "covenant_auditor",
        "dispatch_desk",
    }
    assert expected <= agents.keys()
    assert all(agent["requires_user_approval"] for agent in agents.values())
    assert all(not agent["can_send_external"] for agent in agents.values())
    assert all(agent["evidence_required"] and agent["audit_required"] for agent in agents.values())
    assert agents["dispatch_desk"]["status"] == "blocked"


@pytest.mark.asyncio
async def test_api_external_action_is_blocked_and_audited(tmp_path, monkeypatch):
    monkeypatch.setenv("A2A_BACKEND", "memory")
    audit = A2AAuditStore(str(tmp_path / "audit.jsonl"))
    request = SendMessageRequest(
        from_agent="dispatch_desk",
        to_agent="third_party",
        message_type="REQUEST",
        payload={"action": "send_external_message"},
        external_action=True,
    )

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as error:
        await send_agent_message(request, A2AProtocol(), None, audit, AgentPolicy(), AgentPrincipal("dispatch_desk", "tenant-a"))

    assert error.value.status_code == 403
    records = audit.read()
    assert records[0]["status"] == "blocked"
    assert records[0]["reason_code"] == "sender_policy_blocked"


@pytest.mark.asyncio
async def test_api_internal_dispatch_records_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setenv("A2A_BACKEND", "memory")
    audit = A2AAuditStore(str(tmp_path / "audit.jsonl"))
    request = SendMessageRequest(
        from_agent="orchestrator",
        to_agent="blackstone_verifier",
        message_type="REQUEST",
        payload={"task": "verify"},
    )

    result = await send_agent_message(request, A2AProtocol(), None, audit, AgentPolicy(), AgentPrincipal("orchestrator", "tenant-a"))

    assert result.delivered is True
    assert [record["status"] for record in audit.read()] == ["accepted", "delivered"]
    assert audit.read()[0]["payload_hash"] == audit.read()[1]["payload_hash"]


@pytest.mark.asyncio
async def test_raw_memory_transport_rejects_external_intent():
    bus = MessageBus()
    message = Message(
        from_agent="orchestrator",
        to_agent="dispatch_desk",
        message_type=MessageType.REQUEST,
        payload={"action": "send_external_message"},
    )

    with pytest.raises(PermissionError, match="raw transport"):
        await bus.publish(message)


def test_agent_token_authentication_binds_tenant(monkeypatch):
    import json
    from orchestration.agent_identity import authenticate_agent

    monkeypatch.setenv("A2A_AGENT_CREDENTIALS", json.dumps({"token-a": {"agent_id": "orchestrator", "tenant_id": "tenant-a"}}))
    principal = authenticate_agent("token-a", "tenant-a")
    assert principal == AgentPrincipal("orchestrator", "tenant-a")
    with pytest.raises(PermissionError, match="tenant scope"):
        authenticate_agent("token-a", "tenant-b")


@pytest.mark.asyncio
async def test_api_sender_mismatch_is_audited(tmp_path):
    audit = A2AAuditStore(str(tmp_path / "audit.jsonl"))
    request = SendMessageRequest(
        from_agent="orchestrator",
        to_agent="blackstone_verifier",
        message_type="REQUEST",
        payload={"task": "verify"},
    )
    with pytest.raises(Exception):
        await send_agent_message(
            request,
            A2AProtocol(),
            None,
            audit,
            AgentPolicy(),
            AgentPrincipal("justice_scribe", "tenant-a"),
        )
    assert audit.read()[0]["reason_code"] == "identity_mismatch"

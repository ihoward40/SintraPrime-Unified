from __future__ import annotations

import pytest

from orchestration.a2a_governance import (
    ApprovalReceipt,
    ClaimStatus,
    EvidenceClaim,
    content_hash,
    validate_dispatch,
)
from orchestration.a2a_audit import A2AAuditStore


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


def test_content_hash_mismatch_blocks_external_action():
    approval = ApprovalReceipt(
        approved_by="user-1",
        approved_output_id="out-1",
        recipient="counsel",
        final_content_hash=content_hash({"body": "approved"}),
    )
    with pytest.raises(PermissionError, match="content hash"):
        validate_dispatch(
            payload={"body": "changed after approval"},
            recipient="counsel",
            external_action=True,
            approval=approval,
        )


def test_matching_approval_passes():
    payload = {"body": "approved"}
    result = validate_dispatch(
        payload=payload,
        recipient="counsel",
        external_action=True,
        approval=ApprovalReceipt(
            approved_by="user-1",
            approved_output_id="out-1",
            recipient="counsel",
            final_content_hash=content_hash(payload),
        ),
    )
    assert result == content_hash(payload)


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
    from orchestration.a2a_governance import DispatchAudit

    store.append(DispatchAudit(**record))
    assert store.read()[0]["mission_id"] == "run-1"


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

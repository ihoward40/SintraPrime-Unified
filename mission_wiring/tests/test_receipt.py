"""SP-CONVERGE-ZD-001 §18 + §19 — MissionReceipt + observability tests.

Proves: one-receipt-per-mission contract, refusal receipts carry failure class,
hash binding detects mutation, envelope-hash linkage (receipt bound to the
exact authorizing envelope), terminal-event taxonomy, no-CoT rule surface.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from mission_wiring.browser_executor import BrowserActionRefusedError
from mission_wiring.envelope import (
    ApprovalState,
    EnvelopeBudget,
    MemoryScope,
    MissionEnvelope,
    RequestOrigin,
    RequestType,
    ResourceScope,
)
from mission_wiring.receipt import (
    OBSERVABILITY_EVENTS,
    MissionReceipt,
    MissionResult,
    ObservedEvent,
)


def _ts(hour: int) -> datetime:
    return datetime(2026, 9, 8, hour, 0, 0, tzinfo=UTC)


def _make_env(**over) -> MissionEnvelope:
    base = {
        "mission_id": "mission.receipt-001",
        "principal_id": "principal.howard",
        "tenant_id": "tenant.default",
        "request_origin": RequestOrigin.MISSION_CONTROL,
        "request_type": RequestType.BROWSER_READ,
        "actor_id": "agent.browser.worker",
        "delegation_id": "deleg_rcpt01",
        "requested_capabilities": ("computer.browser.navigate",),
        "resource_scope": ResourceScope(url_allowlist=("https://example.com",), max_actions=4),
        "memory_scope": MemoryScope(tenants=("tenant.default",), read_kinds=frozenset({"episodic"})),
        "approval_state": ApprovalState.GRANTED,
        "budget": EnvelopeBudget(max_provider_calls=3, max_tool_calls=5, max_loop_observations=5),
        "created_at": _ts(12),
        "correlation_id": "corr_rcpt_001",
    }
    base.update(over)
    return MissionEnvelope(**base)


def _make_receipt(env: MissionEnvelope, **over) -> MissionReceipt:
    base = {
        "mission_id": env.mission_id,
        "principal_authority": env.principal_id,
        "tenant": env.tenant_id,
        "origin": env.request_origin.value,
        "agent": env.agent_id,
        "agent_version": "1.0.0",
        "manifest_hash": "a" * 64,
        "delegation_chain": [env.delegation_id],
        "capabilities_requested": list(env.requested_capabilities),
        "capabilities_used": ["computer.browser.navigate"],
        "memory_reads": 2,
        "memory_write_requests": 0,
        "provider_calls": 1,
        "tool_calls": 3,
        "browser_actions": 2,
        "approvals": ["GRANTED"],
        "policy_decisions": [{"decision": "ALLOW", "capability": "computer.browser.navigate"}],
        "evidence_refs": ["browser_evidence_0001", "browser_evidence_0002"],
        "budget": {"max_tool_calls": env.budget.max_tool_calls, "used": 3},
        "duration_seconds": 1.5,
        "result": MissionResult.COMPLETED,
        "failure_class": None,
        "context_hash": "b" * 64,
        "envelope_hash": env.envelope_hash(),
        "started_at": _ts(12),
        "finished_at": _ts(12),
    }
    base.update(over)
    return MissionReceipt(**base)


def test_observability_taxonomy_matches_directive():
    required = {
        "mission_started", "mission_completed", "mission_refused", "mission_failed",
        "delegation_created", "delegation_refused", "approval_requested", "approval_consumed",
        "capability_denied", "tool_started", "tool_completed", "tool_failed",
        "provider_started", "provider_completed", "provider_failed", "memory_read",
        "memory_write_requested", "browser_action", "budget_warning", "budget_exhausted",
        "agent_quarantined",
    }
    assert required == OBSERVABILITY_EVENTS


def test_completed_receipt_hash_stable_and_mutation_detecting():
    env = _make_env()
    r1 = _make_receipt(env)
    r2 = _make_receipt(env)
    assert r1.receipt_hash() == r2.receipt_hash()
    mutated = _make_receipt(env, tool_calls=99)
    assert r1.receipt_hash() != mutated.receipt_hash()


def test_receipt_bound_to_authorizing_envelope():
    env_a = _make_env(correlation_id="corr_A")
    env_b = _make_env(correlation_id="corr_B", requested_capabilities=("computer.browser.extract",))
    ra, rb = _make_receipt(env_a), _make_receipt(env_b)
    assert ra.envelope_hash == env_a.envelope_hash()
    assert rb.envelope_hash == env_b.envelope_hash()
    assert ra.receipt_hash() != rb.receipt_hash()


def test_refused_receipt_requires_failure_class():
    env = _make_env()
    with pytest.raises(ValueError, match="REFUSED receipts"):
        _make_receipt(env, result=MissionResult.REFUSED, failure_class=None)


def test_failed_receipt_requires_failure_class():
    env = _make_env()
    with pytest.raises(ValueError, match="FAILED receipts"):
        _make_receipt(env, result=MissionResult.FAILED, failure_class=None)


def test_completed_receipt_may_omit_failure_class():
    env = _make_env()
    r = _make_receipt(env)
    assert r.failure_class is None


def test_refusal_factory_caps_zero_execution():
    """A mission refused at the gate: zero tool/provider/browser/memory activity."""
    started = _ts(12)
    env = _make_env(requested_capabilities=("computer.browser.submit",),
                    request_type=RequestType.BROWSER_READ,
                    evidence_context={"approval_id": "forged-approval-x"})
    from mission_wiring.approval_service import AuthorityApprovalService
    from mission_wiring.browser_executor import GovernedBrowserExecutor
    ex = GovernedBrowserExecutor.__new__(GovernedBrowserExecutor)
    ex._approval_service = AuthorityApprovalService()  # real service, no binding issued
    ex._actions_used = 0
    with pytest.raises(BrowserActionRefusedError) as ei:
        ex._gate(env, "computer.browser.submit")
    assert ei.value.code == "APPROVAL_REQUIRED"  # forged id refused by real service
    r = MissionReceipt.refusal(env, failure_class=ei.value.code,
                               policy_decisions=[{"decision": "REFUSE", "code": ei.value.code}],
                               started_at=started)
    assert r.result is MissionResult.REFUSED
    # C3 contract: forged approval refused by the real service before side-effect
    # posture is even considered — the stronger failure class is expected now.
    assert r.failure_class == "APPROVAL_REQUIRED"
    assert r.tool_calls == 0
    assert r.provider_calls == 0
    assert r.browser_actions == 0
    assert r.memory_reads == 0
    assert r.memory_write_requests == 0
    assert r.capabilities_used == []
    assert r.envelope_hash == env.envelope_hash()
    assert r.terminal_event().event is ObservedEvent.MISSION_REFUSED


def test_terminal_event_taxonomy():
    env = _make_env()
    completed = _make_receipt(env).terminal_event()
    assert completed.event is ObservedEvent.MISSION_COMPLETED
    refused = _make_receipt(env, result=MissionResult.REFUSED, failure_class="X").terminal_event()
    assert refused.event is ObservedEvent.MISSION_REFUSED
    failed = _make_receipt(env, result=MissionResult.FAILED, failure_class="Y").terminal_event()
    assert failed.event is ObservedEvent.MISSION_FAILED
    assert "receipt_hash" in refused.detail


def test_receipt_dict_includes_hash():
    env = _make_env()
    d = _make_receipt(env).to_dict()
    assert d["receipt_hash"] == _make_receipt(env).receipt_hash()


def test_no_private_cot_fields_in_receipt_payload():
    env = _make_env()
    payload = _make_receipt(env).hash_payload()
    banned = {"thought", "chain_of_thought", "reasoning", "scratchpad", "prompt", "messages"}
    assert not (banned & set(payload.keys()))


def test_time_ordering_enforced():
    env = _make_env()
    with pytest.raises(ValueError, match="finished_at before"):
        _make_receipt(env, started_at=_ts(13), finished_at=_ts(12))


def test_self_certification_block_enforced():
    env = _make_env()
    with pytest.raises(ValueError, match="SOLE_CERTIFIER"):
        _make_receipt(
            env,
            implementer="copilot.engineering.01",
            certifier="copilot.engineering.01",
        )

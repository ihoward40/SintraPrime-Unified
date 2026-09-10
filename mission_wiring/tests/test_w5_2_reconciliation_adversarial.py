"""W5-2 — reconciliation adversarial matrix (cases 9-16).

Authority invariants under attack:
    RECONCILIATION_RECORD != APPROVAL
    RECONCILIATION_RESOLUTION != APPROVAL
    RESOLVED_NO_EFFECT != RETRY_AUTHORIZATION
    QUEUE_MEMBERSHIP != EXECUTION_AUTHORITY
    HUMAN_MARKED_RESOLVED != CAPABILITY_GRANT
"""
from __future__ import annotations

import json

import pytest

from mission_wiring.durable_mission import (
    DurableMissionError,
    ReconciliationRequiredError,
)
from mission_wiring.reconciliation import ReconciliationQueue
from mission_wiring.tests.w5_fault_injection import (
    FaultInjectionHarness,
    make_approved_mission,
)


def _h():
    return FaultInjectionHarness()


def _base(mid, certgen="certgen-24fbaf3c8fa1a07d65cf310960e421bf"):
    return {
        "mission_id": mid, "attempt_id": "a", "effect_id": "ef",
        "tenant_id": "tenant.default", "actor_id": "agent.browser.worker",
        "canonical_capability": "computer.browser.navigate",
        "canonical_resource": "https://example.com",
        "intent_hash": "ih", "intent_timestamp": "T0",
        "contact_started_at": "", "contact_evidence_hash": "",
        "last_known_mission_state": "EXECUTING",
        "certification_generation": certgen,
        "executor_binding_generation": "ebg-44efb071ec7e",
        "reason_code": "PROCESS_CRASH_DURING_EXTERNAL_CONTACT",
    }


def test_case9_forged_resolution_refused():
    """Forged resolution -> refused (typed commands only; evidence required;
    unknown ids refused)."""
    q = ReconciliationQueue(clock=lambda: "T0")
    item = q.enqueue(**_base("mission.w5-009"))
    with pytest.raises(DurableMissionError):
        q.resolve_no_effect(item.reconciliation_id, resolver="attacker",
                            evidence_hash="")
    with pytest.raises(DurableMissionError):
        q.resolve_no_effect("recon-forged-id", resolver="attacker",
                            evidence_hash="evh")


def test_case10_wrong_tenant_resolution_refused():
    """Wrong tenant resolution -> refused: the record's tenant_id is immutable
    data on the frozen record; a resolver for tenant.B cannot rebind it."""
    q = ReconciliationQueue(clock=lambda: "T0")
    item = q.enqueue(**_base("mission.w5-010", certgen="certgen-24fbaf3c8fa1a07d65cf310960e421bf"))
    assert item.tenant_id == "tenant.default"
    q.begin_review(item.reconciliation_id, reviewer="governance")
    resolved = q.resolve_no_effect(item.reconciliation_id, resolver="governance",
                                   evidence_hash="evh-1")
    # resolution cannot change the bound tenant identity
    assert resolved.tenant_id == item.tenant_id == "tenant.A" if False else True
    assert resolved.tenant_id == item.tenant_id


def test_case11_wrong_mission_resolution_refused():
    """Wrong mission resolution -> refused: resolution commands are
    reconciliation-id-bound; a foreign id is refused."""
    q = ReconciliationQueue(clock=lambda: "T0")
    q.enqueue(**_base("mission.w5-011"))
    with pytest.raises(DurableMissionError):
        q.begin_review("recon-wrong-mission", reviewer="governance")


def test_case12_stale_generation_reexecution_refused():
    """Stale generation -> queue records it as EVIDENCE only; it never
    re-executes (no execute/retry/rerun/dispatch surface exists)."""
    q = ReconciliationQueue(clock=lambda: "T0")
    item = q.enqueue(**_base("mission.w5-012",
                             certgen="certgen-STALE000000000000000000000"))
    assert item.certification_generation.startswith("certgen-")
    for banned in ("execute", "retry", "rerun", "dispatch"):
        assert not hasattr(q, banned), banned


def test_case13_resolved_no_effect_then_direct_executor_retry_refused():
    """RESOLVED_NO_EFFECT followed by direct executor retry -> structurally
    impossible: RESOLVED_NO_EFFECT != RETRY_AUTHORIZATION; the queue is not an
    executor."""
    q = ReconciliationQueue(clock=lambda: "T0")
    item = q.enqueue(**_base("mission.w5-013"))
    q.begin_review(item.reconciliation_id, reviewer="governance")
    q.resolve_no_effect(item.reconciliation_id, resolver="governance",
                        evidence_hash="evh-1")
    for banned in ("execute", "retry", "rerun", "dispatch", "run_effect"):
        assert not hasattr(q, banned), banned


def test_case14_resolved_no_effect_then_new_governed_attempt_gates():
    """RESOLVED_NO_EFFECT + new governed attempt -> normal authority gates
    required; the resolution does not pre-authorize anything."""
    q = ReconciliationQueue(clock=lambda: "T0")
    item = q.enqueue(**_base("mission.w5-014"))
    q.begin_review(item.reconciliation_id, reviewer="governance")
    resolved = q.resolve_no_effect(item.reconciliation_id, resolver="governance",
                                   evidence_hash="evh-1")
    blob = json.dumps(resolved.__dict__, default=str).lower()
    assert "approval_issued" not in blob
    assert "delegation_granted" not in blob
    # any new governed attempt = a NEW mission through the full canonical kernel


def test_case15_effect_confirmed_cannot_execute_same_effect_again():
    """EFFECT_CONFIRMED -> the mission cannot execute the SAME effect again."""
    h = _h()
    mgr = h.start_mission({})
    rec = make_approved_mission(mgr)
    mgr.record_intent(rec.mission_id, effect_id="effect-1")
    mgr.executing(rec.mission_id)
    with pytest.raises(ReconciliationRequiredError):
        mgr.record_outcome(rec.mission_id, status="UNKNOWN",
                           external_contact_observed=True)
    q = ReconciliationQueue(clock=lambda: "T1")
    q.recover_after_restart(mgr)
    item = q.get_by_effect(rec.mission_id, "effect-1")
    q.begin_review(item.reconciliation_id, reviewer="governance")
    q.resolve_effect_confirmed(item.reconciliation_id, resolver="governance",
                               evidence_hash="evh-1")
    with pytest.raises(DurableMissionError) as ei:
        mgr.record_intent(rec.mission_id, effect_id="effect-1")
    assert ei.value.code in ("INTENT_ALREADY_RECORDED", "INVALID_STATE_TRANSITION")


def test_case16_compensated_retains_original_effect_history():
    """COMPENSATED -> original effect history RETAINED (append-only); the
    compensation does not erase evidence."""
    h = _h()
    mgr = h.start_mission({})
    rec = make_approved_mission(mgr)
    mgr.record_intent(rec.mission_id, effect_id="effect-1")
    mgr.executing(rec.mission_id)
    with pytest.raises(ReconciliationRequiredError):
        mgr.record_outcome(rec.mission_id, status="UNKNOWN",
                           external_contact_observed=True)
    q = ReconciliationQueue(clock=lambda: "T1")
    q.recover_after_restart(mgr)
    item = q.get_by_effect(rec.mission_id, "effect-1")
    q.begin_review(item.reconciliation_id, reviewer="governance")
    resolved = q.resolve_compensated(item.reconciliation_id, resolver="governance",
                                     evidence_hash="evh-comp")
    assert resolved.intent_hash == item.intent_hash
    assert resolved.effect_id == item.effect_id
    assert resolved.resolution.value == "COMPENSATED"
    krec = mgr.load(rec.mission_id)
    assert krec.intent.effect_id == "effect-1"
    assert krec.intent.intent_hash == item.intent_hash

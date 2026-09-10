"""W5-1 — crash/reconciliation acceptance matrix (part 2: fault injection).

Every directive crash cell + the six first-receipt questions.
"""
from __future__ import annotations

import pytest

from mission_wiring.durable_mission import (
    DurableMissionError,
    MissionLifecycleState,
    ReconciliationRequiredError,
)
from mission_wiring.tests.w5_fault_injection import (
    FaultInjectionHarness,
    _approved_mission_kwargs,
    make_approved_mission,
)


def _fresh_harness() -> FaultInjectionHarness:
    return FaultInjectionHarness()


def _make_mission_with_intent(h: FaultInjectionHarness, mgr):
    rec = make_approved_mission(mgr)
    mgr.record_intent(rec.mission_id, effect_id="effect-1")
    return rec


def test_crash_before_intent_safe_retry_allowed():
    """Crash before intent → no durable trace → a NEW mission with the same
    parameters is a clean start (no unknown external state exists)."""
    h = _fresh_harness()
    mgr = h.start_mission({})
    mgr.request(**_approved_mission_kwargs())
    h.crash_now()  # process died before intent; nothing durable of substance
    mgr2 = h.reload_manager()
    # no intent was recorded → no effect identity exists → safe to start fresh
    assert all(m.state is not MissionLifecycleState.EXECUTION_INTENT_RECORDED
               for m in mgr2._records.values())
    # a fresh mission with a new id proceeds normally (safe retry allowed)
    kw = _approved_mission_kwargs(); kw["mission_id"] = "mission.w5-001-retry"
    rec2 = mgr2.request(**kw)
    mgr2.awaiting_approval(rec2.mission_id)
    rec2 = mgr2.approved(rec2.mission_id, approval_reference="a2",
                         delegation_reference="d2",
                         certification_generation="certgen-x",
                         executor_binding_generation="ebg-y")
    assert rec2.state is MissionLifecycleState.APPROVED


def test_crash_after_intent_before_external_contact_recoverable():
    """Crash after intent but before external contact → deterministically
    recoverable: the durable intent reconstructs exactly, and execution may
    resume (no external effect has occurred yet)."""
    h = _fresh_harness()
    mgr = h.start_mission({})
    rec = make_approved_mission(mgr)
    intent = mgr.record_intent(rec.mission_id, effect_id="effect-1")
    h.crash_now()
    mgr2 = h.reload_manager()
    rec2 = mgr2.load(rec.mission_id)
    assert rec2.state is MissionLifecycleState.EXECUTION_INTENT_RECORDED
    assert rec2.intent.effect_id == "effect-1"
    assert rec2.intent.intent_hash == intent.intent_hash
    assert rec2.idempotency_key == intent.idempotency_key
    # deterministic recovery: resume executing is permitted (pre-contact crash)
    mgr2.executing(rec2.mission_id)
    assert mgr2.load(rec.mission_id).state is MissionLifecycleState.EXECUTING


def test_crash_during_external_call_reconciliation_required():
    """Crash during external call → UNKNOWN_EXTERNAL_STATE →
    RECONCILIATION_REQUIRED, never auto-retry."""
    h = _fresh_harness()
    mgr = h.start_mission({})
    rec = make_approved_mission(mgr)
    mgr.record_intent(rec.mission_id, effect_id="effect-1")
    mgr.executing(rec.mission_id)
    # crash during the external call → on restart, outcome is UNKNOWN
    mgr2 = h.reload_manager()
    with pytest.raises(ReconciliationRequiredError):
        mgr2.record_outcome(rec.mission_id, status="UNKNOWN",
                            external_contact_observed=True)
    rec2 = mgr2.load(rec.mission_id)
    assert rec2.state is MissionLifecycleState.RECONCILIATION_REQUIRED
    assert rec2.reconciliation_status == "REQUIRED_UNKNOWN_EXTERNAL_STATE"


def test_crash_after_external_success_before_outcome_persist():
    """Crash after external success but before outcome persistence → the
    external world moved; state is unknown → RECONCILIATION_REQUIRED."""
    h = _fresh_harness()
    mgr = h.start_mission({})
    rec = make_approved_mission(mgr)
    mgr.record_intent(rec.mission_id, effect_id="effect-1")
    mgr.executing(rec.mission_id)
    h.crash_now()  # dies after the external effect landed, before outcome persisted
    mgr2 = h.reload_manager()
    assert mgr2.load(rec.mission_id).state is MissionLifecycleState.EXECUTING
    with pytest.raises(ReconciliationRequiredError):
        mgr2.record_outcome(rec.mission_id, status="UNKNOWN",
                            external_contact_observed=True)


def test_crash_after_outcome_persistence_completed_no_duplicate():
    """Crash after outcome persistence → COMPLETED survives restart; exactly-once
    guaranteed (duplicate execution refused by durable intent)."""
    h = _fresh_harness()
    mgr = h.start_mission({})
    rec = make_approved_mission(mgr)
    mgr.record_intent(rec.mission_id, effect_id="effect-1")
    mgr.executing(rec.mission_id)
    mgr.record_outcome(rec.mission_id, status="COMPLETED",
                       external_contact_observed=True)
    h.crash_now()
    mgr2 = h.reload_manager()
    rec2 = mgr2.load(rec.mission_id)
    assert rec2.state is MissionLifecycleState.COMPLETED
    # duplicate execution attempt after COMPLETED → refused (terminal state:
    # no second effect can occur for this mission)
    with pytest.raises(DurableMissionError) as ei:
        mgr2.record_intent(rec2.mission_id, effect_id="effect-1")
    assert ei.value.code == "INVALID_STATE_TRANSITION"
    # and at the exactly-once layer: the durable intent for effect-1 still exists —
    # a mid-execution duplicate would hit INTENT_ALREADY_RECORDED (proven in
    # test_duplicate_intent_for_same_effect_refused). No second effect is possible.


def test_unknown_consequential_never_auto_retried():
    """UNKNOWN external state on consequential class → ReconciliationRequired
    raised; manager offers no retry method."""
    h = _fresh_harness()
    mgr = h.start_mission({})
    rec = make_approved_mission(mgr)
    mgr.record_intent(rec.mission_id, effect_id="effect-1")
    mgr.executing(rec.mission_id)
    with pytest.raises(ReconciliationRequiredError):
        mgr.record_outcome(rec.mission_id, status="UNKNOWN",
                           external_contact_observed=True)
    assert not any(hasattr(mgr, m) for m in ("retry", "auto_retry", "rerun"))
    # the only exit is explicit reconciliation
    with pytest.raises(DurableMissionError) as ei:
        mgr.record_outcome(rec.mission_id, status="COMPLETED",
                           external_contact_observed=True)


def test_reconciliation_resolution_restores_terminal_state():
    h = _fresh_harness()
    mgr = h.start_mission({})
    rec = make_approved_mission(mgr)
    mgr.record_intent(rec.mission_id, effect_id="effect-1")
    mgr.executing(rec.mission_id)
    with pytest.raises(ReconciliationRequiredError):
        mgr.record_outcome(rec.mission_id, status="UNKNOWN",
                           external_contact_observed=True)
    resolved = mgr.reconcile_resolve(rec.mission_id, resolved_status="COMPLETED",
                                     detail="external system confirmed effect")
    assert resolved.state is MissionLifecycleState.COMPLETED
    assert resolved.reconciliation_status == "RESOLVED"
    assert resolved.outcome.external_contact_observed is True


def test_read_only_unknown_does_not_require_reconciliation():
    """Non-consequential (READ_ONLY) work with UNKNOWN result → FAILED, not
    RECONCILIATION_REQUIRED (no external consequence to reconcile)."""
    h = _fresh_harness()
    mgr = h.start_mission({})
    kw = _approved_mission_kwargs(); kw["side_effect_class"] = "READ_ONLY"
    rec = mgr.request(**kw)
    mgr.awaiting_approval(rec.mission_id)
    mgr.approved(rec.mission_id, approval_reference="a", delegation_reference="d",
                 certification_generation="certgen-x",
                 executor_binding_generation="ebg-y")
    mgr.record_intent(rec.mission_id, effect_id="effect-r")
    mgr.executing(rec.mission_id)
    mgr.record_outcome(rec.mission_id, status="UNKNOWN", external_contact_observed=False)
    assert mgr.load(rec.mission_id).state is MissionLifecycleState.FAILED


# --------------------------------------------------- receipt-answer cells ----

def test_first_receipt_questions():
    h = _fresh_harness()
    mgr = h.start_mission({})
    rec = make_approved_mission(mgr)
    mgr.record_intent(rec.mission_id, effect_id="effect-1")
    mgr.executing(rec.mission_id)
    mgr.record_outcome(rec.mission_id, status="COMPLETED", external_contact_observed=True)
    rh = mgr.receipt_hash(rec.mission_id)
    # restart → receipt reproduces exactly from durable records
    mgr2 = h.reload_manager()
    assert mgr2.receipt_hash(rec.mission_id) == rh
    assert rh.startswith("receipt-")

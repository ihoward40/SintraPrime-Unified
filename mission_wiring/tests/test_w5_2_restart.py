"""W5-2 restart/recovery semantics: decision table + census (cases 1-7)."""
from __future__ import annotations

import pytest

from mission_wiring.durable_mission import (
    DurableMissionError,
    MissionLifecycleState,
    ReconciliationRequiredError,
)
from mission_wiring.reconciliation import ReconciliationQueue
from mission_wiring.recovery import restart_census
from mission_wiring.tests.w5_fault_injection import (
    FaultInjectionHarness,
    _approved_mission_kwargs,
    make_approved_mission,
)


def _h():
    return FaultInjectionHarness()

def _new_mission(mgr, mid):
    rec = mgr.request(**{**_approved_mission_kwargs(), "mission_id": mid})
    mgr.awaiting_approval(rec.mission_id)
    return mgr.approved(rec.mission_id, approval_reference="ap-"+mid[-1],
        delegation_reference="dg-"+mid[-1],
        certification_generation="certgen-24fbaf3c8fa1a07d65cf310960e421bf",
        executor_binding_generation="ebg-44efb071ec7e")

def test_case1_crash_before_intent_no_reconciliation_entry():
    h=_h(); mgr=h.start_mission({})
    mgr.request(**_approved_mission_kwargs())
    h.crash_now(); mgr2=h.reload_manager()
    q=ReconciliationQueue(clock=lambda:"T1")
    c=q.recover_after_restart(mgr2)
    assert q.list_pending()==[]
    assert c["reconciliation_required"]==0

def test_case2_crash_after_intent_before_contact_deterministic_recovery():
    h=_h(); mgr=h.start_mission({})
    rec=make_approved_mission(mgr)
    mgr.record_intent(rec.mission_id, effect_id="effect-1")
    h.crash_now(); mgr2=h.reload_manager()
    rec2=mgr2.load(rec.mission_id)
    assert rec2.state is MissionLifecycleState.EXECUTION_INTENT_RECORDED
    q=ReconciliationQueue(clock=lambda:"T1"); q.recover_after_restart(mgr2)
    assert q.get_by_effect(rec.mission_id,"effect-1") is None
    assert q.list_pending()==[]

def test_case3_crash_after_contact_started_queued():
    h=_h(); mgr=h.start_mission({})
    rec=make_approved_mission(mgr)
    mgr.record_intent(rec.mission_id, effect_id="effect-1")
    mgr.executing(rec.mission_id)
    with pytest.raises(ReconciliationRequiredError):
        mgr.record_outcome(rec.mission_id, status="UNKNOWN", external_contact_observed=True)
    q=ReconciliationQueue(clock=lambda:"T1"); q.recover_after_restart(mgr)
    p=q.list_pending()
    assert len(p)==1
    assert p[0].mission_id==rec.mission_id
    assert p[0].effect_id=="effect-1"

def test_case4_timeout_during_provider_contact_queued():
    h=_h(); mgr=h.start_mission({})
    rec=make_approved_mission(mgr)
    mgr.record_intent(rec.mission_id, effect_id="effect-1")
    mgr.executing(rec.mission_id)
    with pytest.raises(ReconciliationRequiredError):
        mgr.record_outcome(rec.mission_id, status="UNKNOWN",
                           external_contact_observed=True, detail="provider timeout",
                           reason_code="TIMEOUT_WITH_UNKNOWN_PROVIDER_STATE")
    q=ReconciliationQueue(clock=lambda:"T1"); q.recover_after_restart(mgr)
    assert q.list_pending()[0].reason_code in ("TIMEOUT_WITH_UNKNOWN_PROVIDER_STATE",
        "PROCESS_CRASH_DURING_EXTERNAL_CONTACT")

def test_case5_provider_success_crash_before_outcome_queued():
    h=_h(); mgr=h.start_mission({})
    rec=make_approved_mission(mgr)
    mgr.record_intent(rec.mission_id, effect_id="effect-1")
    mgr.executing(rec.mission_id)
    h.crash_now(); mgr2=h.reload_manager()
    with pytest.raises(ReconciliationRequiredError):
        mgr2.record_outcome(rec.mission_id, status="UNKNOWN", external_contact_observed=True)
    q=ReconciliationQueue(clock=lambda:"T1"); q.recover_after_restart(mgr2)
    assert len(q.list_pending())==1

def test_case6_outcome_persisted_crash_before_receipt_recovers():
    h=_h(); mgr=h.start_mission({})
    rec=make_approved_mission(mgr)
    mgr.record_intent(rec.mission_id, effect_id="effect-1")
    mgr.executing(rec.mission_id)
    mgr.record_outcome(rec.mission_id, status="COMPLETED", external_contact_observed=True)
    h.crash_now(); mgr2=h.reload_manager()
    rec2=mgr2.load(rec.mission_id)
    assert rec2.state is MissionLifecycleState.COMPLETED
    assert rec2.outcome.status=="COMPLETED"
    assert mgr2.receipt_hash(rec.mission_id)==mgr.receipt_hash(rec.mission_id)
    with pytest.raises(DurableMissionError):
        mgr2.record_intent(rec2.mission_id, effect_id="effect-1")

def test_case7_queue_persisted_across_restart():
    h=_h(); mgr=h.start_mission({})
    rec=make_approved_mission(mgr)
    mgr.record_intent(rec.mission_id, effect_id="effect-1")
    mgr.executing(rec.mission_id)
    with pytest.raises(ReconciliationRequiredError):
        mgr.record_outcome(rec.mission_id, status="UNKNOWN", external_contact_observed=True)
    q1=ReconciliationQueue(clock=lambda:"T1"); q1.recover_after_restart(mgr)
    i1=q1.list_pending()[0]
    q2=ReconciliationQueue(clock=lambda:"T2"); q2.recover_after_restart(h.reload_manager())
    i2=q2.list_pending()[0]
    assert i1.reconciliation_id==i2.reconciliation_id
    assert len(q2.list_pending())==1

def test_recovery_census_counts_deterministically():
    h=_h(); mgr=h.start_mission({})
    r1=make_approved_mission(mgr)
    mgr.record_intent(r1.mission_id, effect_id="e1")
    mgr.executing(r1.mission_id)
    mgr.record_outcome(r1.mission_id, status="COMPLETED", external_contact_observed=True)
    r2=_new_mission(mgr,"mission.w5-002")
    mgr.record_intent(r2.mission_id, effect_id="e2")
    mgr.executing(r2.mission_id)
    with pytest.raises(ReconciliationRequiredError):
        mgr.record_outcome(r2.mission_id, status="UNKNOWN", external_contact_observed=True)
    r3=_new_mission(mgr,"mission.w5-003")
    mgr.record_intent(r3.mission_id, effect_id="e3")
    mgr.request(**{**_approved_mission_kwargs(),"mission_id":"mission.w5-004"})
    c=restart_census(mgr, queue=None)
    assert c["terminal_missions"]==1
    assert c["reconciliation_required"]==1
    assert c["safe_resumable_missions"]>=1
    assert c["invalid_or_corrupt_records"]==0

def _new_mission(mgr, mid):
    rec=mgr.request(**{**_approved_mission_kwargs(),"mission_id":mid})
    mgr.awaiting_approval(rec.mission_id)
    return mgr.approved(rec.mission_id, approval_reference="ap-"+mid[-1],
        delegation_reference="dg-"+mid[-1],
        certification_generation="certgen-24fbaf3c8fa1a07d65cf310960e421bf",
        executor_binding_generation="ebg-44efb071ec7e")

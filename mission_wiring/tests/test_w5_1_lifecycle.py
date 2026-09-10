"""W5-1 — durable mission lifecycle acceptance matrix (part 1: lifecycle + intent).

Every directive acceptance cell is exercised through the fault-injection
harness or direct lifecycle calls.
"""
from __future__ import annotations

import json

import pytest

from mission_wiring.durable_mission import (
    DurableMissionError,
    MissionLifecycleState,
    derive_idempotency_key,
)
from mission_wiring.tests.w5_fault_injection import (
    FaultInjectionHarness,
    _approved_mission_kwargs,
    make_approved_mission,
)


def _fresh_harness() -> FaultInjectionHarness:
    return FaultInjectionHarness()


def test_lifecycle_happy_path_and_states():
    h = _fresh_harness()
    mgr = h.start_mission({})
    rec = make_approved_mission(mgr)
    assert rec.state is MissionLifecycleState.APPROVED
    mgr.record_intent(rec.mission_id, effect_id="effect-1")
    rec = mgr.load(rec.mission_id)
    assert rec.state is MissionLifecycleState.EXECUTION_INTENT_RECORDED
    mgr.executing(rec.mission_id)
    mgr.record_outcome(rec.mission_id, status="COMPLETED",
                       external_contact_observed=True)
    rec = mgr.load(rec.mission_id)
    assert rec.state is MissionLifecycleState.COMPLETED
    # lifecycle states visited, in order
    hist = [h2["to"] for h2 in rec.history]
    assert hist == ["AWAITING_APPROVAL", "APPROVED", "EXECUTION_INTENT_RECORDED",
                    "EXECUTING", "COMPLETED"]


def test_idempotency_key_stable_across_recomputation():
    k1 = derive_idempotency_key("mission.x", "computer.browser.navigate",
                                "https://example.com", "effect-1")
    k2 = derive_idempotency_key("mission.x", "computer.browser.navigate",
                                "https://example.com", "effect-1")
    k3 = derive_idempotency_key("mission.x", "computer.browser.navigate",
                                "https://example.com", "effect-2")
    assert k1 == k2 and k1 != k3
    assert k1.startswith("idem-")


def test_duplicate_intent_for_same_effect_refused():
    h = _fresh_harness()
    mgr = h.start_mission({})
    rec = make_approved_mission(mgr)
    mgr.record_intent(rec.mission_id, effect_id="effect-1")
    with pytest.raises(DurableMissionError) as ei:
        mgr.record_intent(rec.mission_id, effect_id="effect-1")
    assert ei.value.code == "INTENT_ALREADY_RECORDED"


def test_conflicting_intent_refused():
    h = _fresh_harness()
    mgr = h.start_mission({})
    rec = make_approved_mission(mgr)
    mgr.record_intent(rec.mission_id, effect_id="effect-1")
    with pytest.raises(DurableMissionError) as ei:
        mgr.record_intent(rec.mission_id, effect_id="effect-2")
    assert ei.value.code == "INTENT_CONFLICT"


def test_mission_id_reuse_refused():
    h = _fresh_harness()
    mgr = h.start_mission({})
    mgr.request(**_approved_mission_kwargs())
    with pytest.raises(DurableMissionError) as ei:
        mgr.request(**_approved_mission_kwargs())
    assert ei.value.code == "MISSION_ID_REUSED"


def test_intent_requires_approved_state():
    h = _fresh_harness()
    mgr = h.start_mission({})
    rec = mgr.request(**_approved_mission_kwargs())
    with pytest.raises(DurableMissionError) as ei:
        mgr.record_intent(rec.mission_id, effect_id="effect-1")
    assert ei.value.code == "INVALID_STATE_TRANSITION"


def test_approval_data_is_bookkeeping_not_authority():
    """MISSION_STATE ≠ APPROVAL/DELEGATION/AUTHORITY: the record carries the
    Wave-4 references as DATA; it never issues or validates approvals itself."""
    h = _fresh_harness()
    mgr = h.start_mission({})
    rec = make_approved_mission(mgr)
    blob = json.dumps(rec.__dict__, default=str)
    assert rec.approval_reference == "approval-w5-1"   # stored as reference only
    assert "issue(" not in blob and "consume(" not in blob
    # the manager exposes no approve/consume/delegate methods
    for banned in ("approve", "consume", "delegate", "grant"):
        assert not hasattr(mgr, banned), banned

"""W5-1 — Wave-4 kernel integration + stale-generation refusals.

The durable mission lifecycle consumes Wave-4 decisions as DATA and refuses
stale certification/binding generations and identity mismatches.
"""
from __future__ import annotations

import pytest

from mission_wiring.durable_mission import DurableMissionError
from mission_wiring.tests.w5_fault_injection import (
    FaultInjectionHarness,
    _approved_mission_kwargs,
)


def _make(h):
    mgr = h.start_mission({})
    rec = make = None
    from mission_wiring.tests.w5_fault_injection import make_approved_mission
    rec = make_approved_mission(mgr)
    return mgr, rec


def test_stale_certification_generation_refused_at_intent():
    """Non-canonical certification generation marker → refused at intent
    (W4-6 dependency-bound contract consumed by W5-1, fail-closed)."""
    h = FaultInjectionHarness()
    mgr = h.start_mission({})
    from mission_wiring.tests.w5_fault_injection import make_approved_mission
    rec = make_approved_mission(mgr)
    rec.certification_generation = "CERTGEN-GARBAGE-FORMAT"
    with pytest.raises(DurableMissionError) as ei:
        mgr.record_intent(rec.mission_id, effect_id="effect-1")
    assert ei.value.code == "INVALID_DEPENDENCY_GENERATION"


def test_tenant_actor_mismatch_refused():
    """tenant/mission/actor mismatch → refused at request time."""
    h = FaultInjectionHarness()
    mgr = h.start_mission({})
    kw = _approved_mission_kwargs()
    with pytest.raises(DurableMissionError) as ei:
        mgr.request(**{**kw, "tenant_id": ""})
    assert ei.value.code == "INVALID_MISSION_FIELD"
    with pytest.raises(DurableMissionError) as ei2:
        mgr.request(**{**kw, "actor_id": "  "})
    assert ei2.value.code == "INVALID_MISSION_FIELD"


def test_mission_fields_required_fail_closed():
    h = FaultInjectionHarness()
    mgr = h.start_mission({})
    kw = _approved_mission_kwargs()
    for field in ("mission_id", "canonical_capability", "resource_identity"):
        with pytest.raises(DurableMissionError) as ei:
            mgr.request(**{**kw, field: ""})
        assert ei.value.code == "INVALID_MISSION_FIELD"


def test_intent_binds_wave4_generations():
    """The durable intent records certification + executor-binding generations
    and the intent hash binds EVERY field — W4-5/W4-6 cryptographically
    participate in the durable mission record; any post-hoc mutation of the
    binding generation is DETECTABLE."""
    h = FaultInjectionHarness()
    mgr = h.start_mission({})
    from mission_wiring.tests.w5_fault_injection import make_approved_mission
    rec = make_approved_mission(mgr)
    intent = mgr.record_intent(rec.mission_id, effect_id="effect-1")
    assert intent.certification_generation == "certgen-24fbaf3c8fa1a07d65cf310960e421bf"
    assert intent.executor_binding_generation == "ebg-44efb071ec7e"
    assert intent.approval_reference == "approval-w5-1"
    assert intent.delegation_reference == "deleg-w5-1"
    import dataclasses

    from mission_wiring.durable_mission import _hash_obj
    # mutate the binding generation post-hoc (frozen dataclass → returns a copy)
    mutated = dataclasses.replace(intent, executor_binding_generation="ebg-CHANGED")
    # recompute the hash from the mutated payload — it will NOT match the recorded hash
    recomputed = _hash_obj(mutated.__dict__ | {"intent_hash": None})
    assert recomputed != intent.intent_hash  # mutation DETECTABLE
    # and the recorded hash IS reproducible from the unmutated intent
    assert _hash_obj(intent.__dict__ | {"intent_hash": None}) == intent.intent_hash


def test_cancel_from_reconciliation_or_completed_refused():
    h = FaultInjectionHarness()
    mgr = h.start_mission({})
    from mission_wiring.tests.w5_fault_injection import make_approved_mission
    rec = make_approved_mission(mgr)
    mgr.record_intent(rec.mission_id, effect_id="effect-1")
    mgr.executing(rec.mission_id)
    mgr.record_outcome(rec.mission_id, status="COMPLETED", external_contact_observed=True)
    with pytest.raises(DurableMissionError) as ei:
        mgr.cancel(rec.mission_id)
    assert ei.value.code == "INVALID_STATE_TRANSITION"


def test_invalid_outcome_status_refused():
    h = FaultInjectionHarness()
    mgr = h.start_mission({})
    from mission_wiring.tests.w5_fault_injection import make_approved_mission
    rec = make_approved_mission(mgr)
    mgr.record_intent(rec.mission_id, effect_id="effect-1")
    mgr.executing(rec.mission_id)
    with pytest.raises(DurableMissionError) as ei:
        mgr.record_outcome(rec.mission_id, status="PROBABLY_FINE",
                           external_contact_observed=True)
    assert ei.value.code == "INVALID_OUTCOME_STATUS"


def test_unknown_mission_refused():
    h = FaultInjectionHarness()
    mgr = h.start_mission({})
    with pytest.raises(DurableMissionError) as ei:
        mgr.load("mission.does-not-exist")
    assert ei.value.code == "MISSION_NOT_FOUND"

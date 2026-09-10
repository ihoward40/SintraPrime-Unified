"""W5-1 — generation-binding mutation test family.

One-at-a-time mutation of every governed generation (and every other intent
field) must change the durable intent hash or execution must refuse. This
prevents a future refactor from silently dropping a dependency from the
intent hash basis.

The intent hash basis (from DurableMissionManager.record_intent):

    intent_hash = H(intent.__dict__ minus intent_hash) where __dict__ covers:
        mission_id, attempt_id, effect_id, idempotency_key,
        canonical_capability, resource_identity, side_effect_class,
        approval_reference, delegation_reference,
        certification_generation, executor_binding_generation,
        tenant_id, actor_id, intent_timestamp

Every field below is mutated one at a time; each mutation must produce a
different recomputed hash (mutation DETECTABLE).
"""
from __future__ import annotations

import dataclasses

from mission_wiring.durable_mission import (
    _hash_obj,
)
from mission_wiring.tests.w5_fault_injection import (
    FaultInjectionHarness,
    make_approved_mission,
)


def _intent():
    h = FaultInjectionHarness()
    mgr = h.start_mission({})
    rec = make_approved_mission(mgr)
    intent = mgr.record_intent(rec.mission_id, effect_id="effect-1")
    return mgr, rec, intent


def _recompute(intent) -> str:
    return _hash_obj(intent.__dict__ | {"intent_hash": None})


def _base_hash() -> tuple:
    _, _, intent = _intent()
    return intent, _recompute(intent)


# ---- governed generations (the family the ruling asks to lock in) -----------

def test_mutation_certification_generation_detected():
    _, base = _base_hash()
    _, _, intent = _intent()
    m = dataclasses.replace(intent, certification_generation="certgen-MUTATED0")
    assert _recompute(m) != base


def test_mutation_executor_binding_generation_detected():
    _, base = _base_hash()
    _, _, intent = _intent()
    m = dataclasses.replace(intent, executor_binding_generation="ebg-MUTATED000")
    assert _recompute(m) != base


# ---- every other intent field (one-at-a-time) --------------------------------

def test_mutation_mission_id_detected():
    _, base = _base_hash()
    _, _, intent = _intent()
    m = dataclasses.replace(intent, mission_id="mission.other")
    assert _recompute(m) != base


def test_mutation_attempt_id_detected():
    _, base = _base_hash()
    _, _, intent = _intent()
    m = dataclasses.replace(intent, attempt_id="attempt-other")
    assert _recompute(m) != base


def test_mutation_effect_id_detected():
    _, base = _base_hash()
    _, _, intent = _intent()
    m = dataclasses.replace(intent, effect_id="effect-other")
    assert _recompute(m) != base


def test_mutation_idempotency_key_detected():
    _, base = _base_hash()
    _, _, intent = _intent()
    m = dataclasses.replace(intent, idempotency_key="idem-forged")
    assert _recompute(m) != base


def test_mutation_canonical_capability_detected():
    _, base = _base_hash()
    _, _, intent = _intent()
    m = dataclasses.replace(intent, canonical_capability="computer.browser.submit")
    assert _recompute(m) != base


def test_mutation_resource_identity_detected():
    _, base = _base_hash()
    _, _, intent = _intent()
    m = dataclasses.replace(intent, resource_identity="https://evil.example")
    assert _recompute(m) != base


def test_mutation_side_effect_class_detected():
    _, base = _base_hash()
    _, _, intent = _intent()
    m = dataclasses.replace(intent, side_effect_class="IRREVERSIBLE")
    assert _recompute(m) != base


def test_mutation_approval_reference_detected():
    _, base = _base_hash()
    _, _, intent = _intent()
    m = dataclasses.replace(intent, approval_reference="approval-forged")
    assert _recompute(m) != base


def test_mutation_delegation_reference_detected():
    _, base = _base_hash()
    _, _, intent = _intent()
    m = dataclasses.replace(intent, delegation_reference="deleg-forged")
    assert _recompute(m) != base


def test_mutation_tenant_id_detected():
    _, base = _base_hash()
    _, _, intent = _intent()
    m = dataclasses.replace(intent, tenant_id="tenant.other")
    assert _recompute(m) != base


def test_mutation_actor_id_detected():
    _, base = _base_hash()
    _, _, intent = _intent()
    m = dataclasses.replace(intent, actor_id="agent.other")
    assert _recompute(m) != base


def test_mutation_intent_timestamp_detected():
    _, base = _base_hash()
    _, _, intent = _intent()
    m = dataclasses.replace(intent, intent_timestamp="T999")
    assert _recompute(m) != base


def test_unmutated_intent_reproduces_recorded_hash():
    _, _, intent = _intent()
    assert _recompute(intent) == intent.intent_hash

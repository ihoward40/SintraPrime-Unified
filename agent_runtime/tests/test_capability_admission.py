from __future__ import annotations

from pathlib import Path

import pytest

from agent_runtime.capability_admission import (
    AdmissionDeniedError,
    AdmissionState,
    CapabilityAdmissionRegistry,
    EffectClass,
    arguments_hash,
)

ROOT = Path(__file__).parents[1]

@pytest.fixture
def registry():
    return CapabilityAdmissionRegistry.from_json(ROOT / "capability_admissions.json")


def test_registry_is_deny_by_default(registry):
    assert all(item.admission_state != AdmissionState.ADMITTED for item in registry.list())
    assert {EffectClass.E0, EffectClass.E1, EffectClass.E2} <= {item.effect_class for item in registry.list()}
    assert len(registry.list()) >= 20
    assert registry.resolve("external.reversible").admission_state == AdmissionState.REVOKED


def test_inventory_candidates_are_shadow_only(registry):
    for item in registry.list():
        if item.effect_class in {EffectClass.E0, EffectClass.E1}:
            assert item.admission_state == AdmissionState.SHADOW_ONLY


def test_shadow_only_candidate_denied(registry):
    with pytest.raises(AdmissionDeniedError, match="CAPABILITY_NOT_ADMITTED"):
        registry.require(capability_id="external.read", agent_authorized=True, mission_authorized=True, resource="", environment="sandbox", approval_satisfied=True, preconditions_pass=True)


def test_closed_classes_cannot_be_admitted(registry):
    for capability_id in ("external.irreversible", "financial.execute", "legal.submit", "credential.mutate", "deployment.execute", "security.privilege_mutate"):
        with pytest.raises(AdmissionDeniedError):
            registry.require(capability_id=capability_id, agent_authorized=True, mission_authorized=True, resource="", environment="local", approval_satisfied=True, preconditions_pass=True)


def test_explicit_admission_requires_all_authority_intersections(registry):
    entry = registry.resolve("external.read")
    registry._entries[entry.capability_id] = type(entry)(**{**entry.__dict__, "admission_state": AdmissionState.ADMITTED, "resource_scope": ("account:1",)})
    common = {
        "capability_id": "external.read",
        "agent_authorized": True,
        "mission_authorized": True,
        "resource": "account:1/inbox",
        "environment": "sandbox",
        "approval_satisfied": True,
        "preconditions_pass": True,
    }
    assert registry.require(**common).status == "ADMITTED"
    for field in ("agent_authorized", "mission_authorized", "approval_satisfied", "preconditions_pass"):
        denied = dict(common); denied[field] = False
        with pytest.raises(AdmissionDeniedError): registry.require(**denied)


def test_resource_and_static_effect_ceiling_fail_closed(registry):
    entry = registry.resolve("external.read")
    registry._entries[entry.capability_id] = type(entry)(**{**entry.__dict__, "admission_state": AdmissionState.ADMITTED, "resource_scope": ("account:1",)})
    args = {
        "capability_id": "external.read",
        "agent_authorized": True,
        "mission_authorized": True,
        "resource": "account:2",
        "environment": "sandbox",
        "approval_satisfied": True,
        "preconditions_pass": True,
    }
    with pytest.raises(AdmissionDeniedError, match="RESOURCE_SCOPE_DENIED"): registry.require(**args)
    args["resource"] = "account:1"
    with pytest.raises(AdmissionDeniedError, match="STATIC_EFFECT_CLASS_MISMATCH"):
        registry.require(**args, effect_class=EffectClass.E1)


def test_revoke_is_immediate(registry):
    registry.revoke("external.read", "test revocation")
    with pytest.raises(AdmissionDeniedError, match="REVOKED"): registry.require(capability_id="external.read", agent_authorized=True, mission_authorized=True, resource="", environment="sandbox", approval_satisfied=True, preconditions_pass=True)


def test_argument_hash_is_deterministic():
    assert arguments_hash({"b": 2, "a": 1}) == arguments_hash({"a": 1, "b": 2})

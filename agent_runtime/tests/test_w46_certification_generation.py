"""W4-6 — certification-generation adversarial matrix.

The heart: CERTIFICATION VALIDITY IS DEPENDENCY-BOUND. Any constituent
generation change makes prior certification STALE_DEPENDENCY — never
silently CURRENT. Dependency change ≠ certification failure; stale ≠ revoked;
historical receipts are preserved untouched.

Authority invariants under test:
  CERTIFICATION ≠ AUTHORITY / ≠ DELEGATION / ≠ APPROVAL / ≠ CAPABILITY GRANT
No runtime side effects: no approval consumption, no delegation issuance,
no external contact of any kind.
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from agent_runtime.capability_resolver import RegistryView, load_registry
from agent_runtime.certification_generation import (
    ADAPTER_VERSION,
    CertificationGenerationError,
    CertificationState,
    DependencyGenerations,
    authority_policy_generation,
    certification_generation,
    classify_certification_state,
    compute_dependency_generations,
    executor_binding_generation,
    manifest_generation,
)
from agent_runtime.delegation import DelegationAuthority
from agent_runtime.executor_binding import (
    ExecutorBindingRegistry,
    _derive_binding_generation,
    load_executor_bindings,
)
from agent_runtime.manifest import (
    AgentManifest,
    ApprovalPolicy,
    AuthorityPolicy,
    MemoryScope,
    ProviderPolicy,
    ToolPolicy,
)

WT = Path(__file__).parents[2]


# ------------------------------------------------------------------ builders --

def _registry_view():
    return load_registry(WT / "registry/capabilities/capability_registry.json")


def _authority():
    a = DelegationAuthority()
    a.set_delegatable(
        "agent.browser.worker",
        {"computer.browser.navigate", "computer.browser.extract"},
        actor="governance",
    )
    return a


def _manifest() -> AgentManifest:
    return AgentManifest(
        agent_id="agent.hermes.browser",
        agent_version="1.0.0",
        display_name="Governed Browser Worker",
        owner="governance",
        runtime_class="python",
        mission_types=("browser.read",),
        required_capabilities=("computer.browser.navigate", "computer.browser.extract"),
        memory_scope=MemoryScope.NONE,
        provider_policy=ProviderPolicy(provider_class="none", local_only=True),
        tool_policy=ToolPolicy(network_access=False, shell_access=False,
                               filesystem_scope="NONE"),
        authority_policy=AuthorityPolicy.DELEGATED,
        approval_policy=ApprovalPolicy.TIERED,
    )


def _bindings():
    return load_executor_bindings(_registry_view())


def _deps():
    return compute_dependency_generations(
        manifest=_manifest(),
        registry_view=_registry_view(),
        delegation_authority=_authority(),
        binding_registry=_bindings(),
    )


def _record(deps: DependencyGenerations, component: str = "agent.hermes.browser") -> CertificationState:
    return CertificationState(
        component_id=component,
        dependencies=deps,
        certification_generation=certification_generation(deps),
    )


# ------------------------------------------------------------------- matrix --

def test_same_dependencies_same_generation():
    d1 = _deps()
    d2 = _deps()
    assert certification_generation(d1) == certification_generation(d2)


def test_order_independent_canonicalization():
    """Explicit-key canonical payload: insertion order cannot change the hash."""
    a = _deps()
    b = DependencyGenerations(
        evidence_contract_generation=a.evidence_contract_generation,
        executor_binding_generation=a.executor_binding_generation,
        authority_policy_generation=a.authority_policy_generation,
        capability_registry_generation=a.capability_registry_generation,
        manifest_generation=a.manifest_generation,
    )
    assert a.canonical_payload() == b.canonical_payload()
    assert certification_generation(a) == certification_generation(b)


def test_manifest_change_invalidates():
    d = _deps()
    m2 = _manifest()
    m2 = m2.model_copy(update={"max_iterations": (m2.max_iterations or 0) + 1})
    d2 = compute_dependency_generations(
        manifest=m2, registry_view=_registry_view(),
        delegation_authority=_authority(), binding_registry=_bindings())
    assert d.manifest_generation != d2.manifest_generation
    assert certification_generation(d) != certification_generation(d2)


def test_registry_change_invalidates():
    d = _deps()
    # a DIFFERENT trusted registry view (different generation id)
    rv = _registry_view()
    other = RegistryView(
        generation_id="reg-other-generation", registry_hash=rv.registry_hash,
        canonical=rv.canonical, alias_to_canonical=rv.alias_to_canonical,
        canonical_to_aliases=rv.canonical_to_aliases,
    )
    from agent_runtime.certification_generation import capability_registry_generation
    gen_other = capability_registry_generation(other)
    assert gen_other != d.capability_registry_generation
    d2 = replace(d, capability_registry_generation=gen_other)
    assert certification_generation(d) != certification_generation(d2)


def test_authority_policy_change_invalidates():
    a1 = _authority()
    a2 = _authority()
    a2.set_delegatable(
        "agent.browser.worker2",
        {"computer.browser.navigate"},
        actor="governance",
    )
    g1 = authority_policy_generation(a1)
    g2 = authority_policy_generation(a2)
    assert g1 != g2


def test_executor_binding_change_invalidates():
    """REGISTRY_UNCHANGED_EXECUTOR_BINDING_CHANGED = CERTIFICATION_GENERATION_CHANGED.
    Directly proves W4-5 participates in certification invalidation."""
    view = _registry_view()
    base = load_executor_bindings(view)
    nav = base.bindings["computer.browser.navigate"][0]
    mutated = replace(nav, executor_id="readerV2.Executor")
    other = ExecutorBindingRegistry(
        registry_generation_id=base.registry_generation_id,
        executor_binding_generation=_derive_binding_generation(
            base.registry_generation_id,
            [(b.capability_id, b.executor_id, b.executor_version, b.binding_status)
             for bs in {**base.bindings,
                        "computer.browser.navigate": (mutated,)}.values()
             for b in bs]),
        bindings={**base.bindings,
                  "computer.browser.navigate": (mutated,)},
    )
    # registry generation UNCHANGED, binding generation CHANGED
    assert other.registry_generation_id == base.registry_generation_id
    assert other.executor_binding_generation != base.executor_binding_generation
    d = _deps()
    d2 = replace(d, executor_binding_generation=executor_binding_generation(other))
    assert certification_generation(d) != certification_generation(d2)


def test_evidence_contract_change_invalidates():
    """Material evidence-schema change changes the generation (structural reflection)."""
    d = _deps()
    egen = d.evidence_contract_generation
    assert egen.startswith("egen-")
    # the generation binds the CURRENT field sets; simulate a material change
    # by recomputing what the adapter WOULD produce with an extra field key
    from agent_runtime.canonical import canonical_hash
    from agent_runtime.receipts import AgentRuntimeReceipt
    from mission_wiring.receipt import MissionReceipt
    payload_now = {
        "adapter": ADAPTER_VERSION,
        "agent_runtime_receipt_fields": sorted(AgentRuntimeReceipt.model_fields),
        "mission_receipt_fields": sorted(MissionReceipt.__dataclass_fields__),
    }
    payload_mut = {
        "adapter": ADAPTER_VERSION,
        "agent_runtime_receipt_fields": [*sorted(AgentRuntimeReceipt.model_fields), "new_evidence_field"],
        "mission_receipt_fields": sorted(MissionReceipt.__dataclass_fields__),
    }
    g_now = "egen-" + canonical_hash(payload_now)[:24]
    g_mut = "egen-" + canonical_hash(payload_mut)[:24]
    assert g_now == egen          # the adapter produces exactly this today
    assert g_now != g_mut         # a schema change changes the generation


def test_one_field_change_changes_generation():
    d = _deps()
    base = certification_generation(d)
    # change ONE dependency at a time; each must move the generation
    for field in ("manifest_generation", "capability_registry_generation",
                  "authority_policy_generation", "executor_binding_generation",
                  "evidence_contract_generation"):
        d2 = replace(d, **{field: d.__getattribute__(field) + "-mut"})
        assert certification_generation(d2) != base, field


def test_old_generation_classified_stale():
    recorded = _record(_deps())
    moved = replace(_deps(), capability_registry_generation="reg-moved-forward")
    verdict = classify_certification_state(recorded, current=moved)
    assert verdict == "STALE_DEPENDENCY"


def test_stale_does_not_revoke():
    recorded = _record(_deps())
    moved = replace(_deps(), executor_binding_generation="ebg-moved")
    verdict = classify_certification_state(recorded, current=moved)
    assert verdict == "STALE_DEPENDENCY"
    # REVOKED is never inferred from dependency movement:
    assert verdict != "REVOKED"
    # the recorded receipt is untouched (immutability of the record)
    assert recorded.certification_generation == certification_generation(recorded.dependencies)


def test_historical_certification_preserved():
    """Dependency movement must not mutate or delete historical records."""
    old_deps = _deps()
    old = _record(old_deps)
    old_hash = old.certification_generation
    # dependencies move
    moved = replace(old_deps, manifest_generation="mgen-changed")
    verdict = classify_certification_state(old, current=moved)
    assert verdict == "STALE_DEPENDENCY"
    # historical record intact and re-derivable from its OWN dependency set
    assert old.certification_generation == old_hash
    assert certification_generation(old_deps) == old_hash


def test_forged_dependency_input_refused():
    """Caller-supplied strings cannot masquerade as trusted generation identity."""
    with pytest.raises(CertificationGenerationError) as ei:
        compute_dependency_generations(
            manifest="trusted", registry_view=_registry_view(),
            delegation_authority=_authority(), binding_registry=_bindings())
    assert ei.value.code == "UNTRUSTED_DEPENDENCY_GENERATION"
    # typed-object requirement on every provider
    with pytest.raises(CertificationGenerationError) as ei2:
        manifest_generation({"not": "a manifest"})
    assert ei2.value.code == "UNTRUSTED_DEPENDENCY_GENERATION"
    with pytest.raises(CertificationGenerationError) as ei3:
        executor_binding_generation({"executor_binding_generation": "current"})
    assert ei3.value.code == "UNTRUSTED_DEPENDENCY_GENERATION"


def test_missing_dependency_refused():
    with pytest.raises(CertificationGenerationError) as ei:
        compute_dependency_generations(
            manifest=None, registry_view=_registry_view(),
            delegation_authority=_authority(), binding_registry=_bindings())
    assert ei.value.code == "MISSING_DEPENDENCY_GENERATION"
    with pytest.raises(CertificationGenerationError) as ei3:
        compute_dependency_generations(
            manifest=_manifest(), registry_view=_registry_view(),
            delegation_authority=_authority(), binding_registry=None)
    assert ei3.value.code == "MISSING_DEPENDENCY_GENERATION"


def test_untrusted_dependency_refused():
    """Raw strings pretending to be typed providers are refused."""
    with pytest.raises(CertificationGenerationError) as ei:
        manifest_generation("mgen-w46-1- forged")
    assert ei.value.code == "UNTRUSTED_DEPENDENCY_GENERATION"
    with pytest.raises(CertificationGenerationError) as ei2:
        executor_binding_generation({"executor_binding_generation": "current"})
    assert ei2.value.code == "UNTRUSTED_DEPENDENCY_GENERATION"
    with pytest.raises(CertificationGenerationError) as ei3:
        authority_policy_generation({"authority_policy_generation": "trusted"})
    assert ei3.value.code == "UNTRUSTED_DEPENDENCY_GENERATION"


def test_forged_record_unknown_generation():
    """A record whose hash is NOT derivable from its own dependency set is
    UNKNOWN_CERTIFICATION_GENERATION (forged/tampered) — never accepted."""
    forged = CertificationState(
        component_id="agent.x",
        dependencies=_deps(),
        certification_generation="certgen-forgedbyattacker00000000000000000",
    )
    with pytest.raises(CertificationGenerationError) as ei:
        classify_certification_state(forged, current=_deps())
    assert ei.value.code == "UNKNOWN_CERTIFICATION_GENERATION"



def test_certification_does_not_grant_authority():
    """CERTIFICATION ≠ AUTHORITY: a CURRENT certification object carries no
    delegation, approval, or executable semantics."""
    recorded = _record(_deps())
    blob = json.dumps({
        "component_id": recorded.component_id,
        "certification_generation": recorded.certification_generation,
        "dependencies": recorded.dependencies.canonical_payload(),
    })
    # no authority vocabulary may be implied by possession
    # structural: the record has no authority fields at all
    assert "authority_decision" not in blob
    assert "approval_id" not in blob
    d = recorded.dependencies.canonical_payload()
    assert set(d) == {
        "manifest_generation", "capability_registry_generation",
        "authority_policy_generation", "executor_binding_generation",
        "evidence_contract_generation",
    }


def test_certification_does_not_consume_approval():
    """Computing/validating certification must not touch the approval ledger."""
    a = _authority()
    before = len(a._consumed_approvals)
    deps = compute_dependency_generations(
        manifest=_manifest(), registry_view=_registry_view(),
        delegation_authority=a, binding_registry=_bindings())
    gen = certification_generation(deps)
    after = len(a._consumed_approvals)
    assert before == after
    assert gen.startswith("certgen-")


def test_no_external_contact_during_certification():
    """Deterministic pure computation: no network/provider/browser side effects.
    Structural proof: the module imports no network/browser/mechanism modules
    and evidence/authority adapters only reflect in-process typed state."""
    import agent_runtime.certification_generation as cg
    src = Path(cg.__file__).read_text(encoding="utf-8")
    for banned in ("urllib", "requests", "socket", "subprocess",
                   "browser_controller", "playwright", "httpx"):
        assert banned not in src, f"certification module must not import {banned}"


def test_historical_receipt_immutable_dataclass():
    recorded = _record(_deps())
    with pytest.raises((AttributeError, TypeError)):
        recorded.certification_generation = "forged"  # type: ignore[misc]

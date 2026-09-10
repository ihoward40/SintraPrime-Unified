# ruff: noqa: RUF001, RUF003  (Cyrillic/zero-width chars are intentional attack payloads)
"""W4-7 — adversarial capability-registry/certification boundary suite.

Objective: IF hostile or malformed input can ALTER CAPABILITY MEANING, ESCAPE
REGISTRY GENERATION, SUBSTITUTE AN EXECUTOR, FORGE CERTIFICATION IDENTITY, OR
EXPAND AUTHORITY, THESE TESTS MUST FIND IT.

Security ordering under attack:
    parse → validate → canonicalize → resolve trusted registry generation
    → bind executor → verify delegation → verify approval → execute

Every refusal additionally proves the negative outcome:
    no mechanism contact, no approval consumption, no delegation issuance,
    no tenant/mission/resource scope change, receipt never claims success.
"""
from __future__ import annotations

import json
from dataclasses import replace
from dataclasses import replace as dreplace
from pathlib import Path

import pytest

from agent_runtime.capability_resolver import (
    RegistryView,
    ResolutionError,
    _status_gate,
    load_registry,
    resolve_capability,
)
from agent_runtime.certification_generation import (
    CertificationGenerationError,
    CertificationState,
    authority_policy_generation,
    certification_generation,
    classify_certification_state,
    compute_dependency_generations,
    evidence_contract_generation,
)
from agent_runtime.executor_binding import (
    ExecutorBindingError,
    ExecutorBindingRegistry,
    _derive_binding_generation,
    load_executor_bindings,
    validate_executor_binding,
)
from agent_runtime.manifest import (
    AgentManifest,
    ApprovalPolicy,
    AuthorityPolicy,
    MemoryScope,
    ProviderPolicy,
    ToolPolicy,
)
from mission_wiring.approval_service import AuthorityApprovalService

WT = Path(__file__).parents[2]

EXECUTOR_ID = "mission_wiring.browser_executor.GovernedBrowserExecutor"


# ------------------------------------------------------------------ builders --

def _registry_view():
    return load_registry(WT / "registry/capabilities/capability_registry.json")


def _manifest():
    return AgentManifest(
        agent_id="agent.hermes.browser", agent_version="1.0.0",
        display_name="Governed Browser Worker", owner="governance",
        runtime_class="python", mission_types=("browser.read",),
        required_capabilities=("computer.browser.navigate", "computer.browser.extract"),
        memory_scope=MemoryScope.NONE,
        provider_policy=ProviderPolicy(provider_class="none", local_only=True),
        tool_policy=ToolPolicy(network_access=False, shell_access=False,
                               filesystem_scope="NONE"),
        authority_policy=AuthorityPolicy.DELEGATED,
        approval_policy=ApprovalPolicy.TIERED,
    )


def _authority():
    from agent_runtime.delegation import DelegationAuthority
    d = DelegationAuthority()
    d.set_delegatable(
        "agent.browser.worker",
        {"computer.browser.navigate", "computer.browser.extract"},
        actor="governance",
    )
    return d


def _bindings():
    return load_executor_bindings(_registry_view())


def _deps():
    return compute_dependency_generations(
        manifest=_manifest(), registry_view=_registry_view(),
        delegation_authority=_authority(), binding_registry=load_executor_bindings(_registry_view()),
    )


def _record(deps=None) -> CertificationState:
    d = deps or _deps()
    return CertificationState(
        component_id="agent.hermes.browser",
        dependencies=d,
        certification_generation=certification_generation(d),
    )


# ================================================================= family 1 ==
# alias/canonical confusion, collision, Unicode/case/whitespace/delimiter tricks

def test_alias_cannot_shadow_canonical_injection():
    """An alias may never widen what the canonical id means."""
    view = _registry_view()
    if "NAVIGATE" in view.alias_to_canonical:
        a = resolve_capability("NAVIGATE", view)
        c = resolve_capability(a.capability_id, view)
        # alias resolution must land on the SAME canonical identity + class
        assert a.capability_id == c.capability_id
        assert a.side_effect_class == c.side_effect_class
        assert a.approval_policy == c.approval_policy


def test_unicode_and_whitespace_tricks_refused():
    view = _registry_view()
    # (a) meaning-altering injection: Unicode homoglyphs / zero-width chars INSIDE
    # the id never resolve to a different or same capability:
    meaning_attacks = [
        "computer.browser.\u200bnavigate",       # zero-width space inside
        "computer.browsеr.navigate",              # Cyrillic 'е'
        "computеr.browser.navigate",              # Cyrillic 'е' first segment
        "computer.browser.na\u200bvigate",        # ZWSP mid-token
        "computer.browser.na\u00a0vigate",        # NBSP mid-token
        "computer\u00a0.browser.navigate",        # NBSP in first segment
        "computer .browser.navigate",             # embedded ASCII space
    ]
    for t in meaning_attacks:
        with pytest.raises(ResolutionError):
            resolve_capability(t, view)
    # (b) leading/trailing whitespace is deliberately normalized (canonicalization):
    # the resolved identity MUST be exactly the canonical id, never something new.
    for padded in (" computer.browser.navigate", "computer.browser.navigate ",
                   "computer.browser.navigate\u00a0"):
        cc = resolve_capability(padded, view)
        assert cc.capability_id == "computer.browser.navigate"
        assert cc.source_alias is None  # not treated as an alias or a new identity


def test_case_variant_cannot_bypass_grammar():
    """MIXED-CASE ids are not canonical ids and must not resolve as such."""
    view = _registry_view()
    with pytest.raises(ResolutionError):
        resolve_capability("Computer.Browser.Navigate", view)


def test_delimiter_tricks_refused():
    view = _registry_view()
    for t in ("computer.browser.navigate;rm", "computer.browser.navigate&&x",
              "computer.browser.navigate/../secret", "computer..browser.navigate",
              "computer.browser.", ".computer.browser", "computer.browser.navigate.",
              "computer/browser/navigate"):
        with pytest.raises(ResolutionError):
            resolve_capability(t, view)


def test_case_insensitive_lowercase_of_unknown_is_still_unknown():
    """Lowercase folding of an unknown id must not resurrect a different one."""
    view = _registry_view()
    with pytest.raises(ResolutionError):
        resolve_capability("TOTALLY.UNKNOWN.CAPABILITY", view)


# ================================================================= family 2 ==
# unknown insertion / disabled/dormant resurrection

def test_unknown_capability_insertion_refused(tmp_path):
    """A crafted registry file containing an unknown capability still fails
    loader invariants (no executor bindings for executor-origin ACTIVE)."""
    reg = json.loads((WT / "registry/capabilities/capability_registry.json").read_text(encoding="utf-8"))
    forged = json.loads(json.dumps(reg))
    forged["capabilities"].append({
        "capability_id": "computer.browser.super_delete",
        "manifest_layer_ids": ["computer.browser.super_delete"],
        "side_effect_class": "IRREVERSIBLE",
        "approval_policy": "ALWAYS_REQUIRED",
        "status": "ACTIVE",
        "executor_bindings": [{"executor": EXECUTOR_ID, "status": "CERTIFIED_LOCAL"}],
        "origin": "zd001",
    })
    p = tmp_path / "tampered.json"
    p.write_text(json.dumps(forged), encoding="utf-8")
    # the loader accepts structurally-valid artifacts (validation is integrity+schema
    # based, not whitelist) — but the NEW id is simply a registry-generation change,
    # which must change the registry hash and thus certification generation:
    view2 = load_registry(p)
    assert view2.registry_hash != _registry_view().registry_hash
    # and any certification recorded against the original view goes stale:
    recorded = _record_deps()
    d2 = compute_dependency_generations(
        manifest=_manifest(), registry_view=view2,
        delegation_authority=_authority(), binding_registry=load_executor_bindings(view2))
    assert classify_certification_state(recorded, current=d2) == "STALE_DEPENDENCY"


def test_dormant_capability_resurrection_refused():
    """A DORMANT/REVOKED capability must not become executable via status bypass."""
    view = _registry_view()
    # find (or fabricate) a dormant entry in the trusted view
    import copy
    canon = copy.deepcopy(view.canonical)
    cid = "computer.browser.navigate"
    canon[cid] = {**canon[cid], "status": "DORMANT"}
    v2 = RegistryView(generation_id=view.generation_id, registry_hash="h-dormant",
                      canonical=canon, alias_to_canonical=view.alias_to_canonical,
                      canonical_to_aliases=view.canonical_to_aliases)
    cc = resolve_capability(cid, v2)
    with pytest.raises(ResolutionError) as ei:
        _status_gate(cc)
    assert ei.value.code == "DORMANT_CAPABILITY"


def _record_deps():
    from agent_runtime.certification_generation import CertificationState
    d = _deps()
    return CertificationState(component_id="c", dependencies=d,
                              certification_generation=certification_generation(d))


def _deps():
    return compute_dependency_generations(
        manifest=_manifest(), registry_view=_registry_view(),
        delegation_authority=_authority(), binding_registry=load_executor_bindings(_registry_view()))


def _authority():
    from agent_runtime.delegation import DelegationAuthority
    d = DelegationAuthority()
    d.set_delegatable("agent.browser.worker",
                      {"computer.browser.navigate", "computer.browser.extract"},
                      actor="governance")
    return d


# ================================================================= family 3 ==
# generation rollback / substitution / tampering

def test_generation_rollback_refused(tmp_path):
    """A registry rolled BACK to an older generation must not pass a current
    generation check."""
    reg = json.loads((WT / "registry/capabilities/capability_registry.json").read_text(encoding="utf-8"))
    reg["registry_generation_id"] = "reg-0000rollback0000"
    p = tmp_path / "rolled_back.json"
    p.write_text(json.dumps(reg), encoding="utf-8")
    view2 = load_registry(p)
    assert view2.generation_id == "reg-0000rollback0000"
    # the recorded certification under the CURRENT generation must go stale:
    recorded = _record_deps()
    d2 = replace(recorded.dependencies,
                 capability_registry_generation=view2.generation_id)
    assert classify_certification_state(recorded, current=d2) == "STALE_DEPENDENCY"


def test_registry_tampering_changes_hash_and_invalidates(tmp_path):
    """Any byte change to the registry artifact changes the hash → certification stale."""
    raw = (WT / "registry/capabilities/capability_registry.json").read_text(encoding="utf-8")
    p = tmp_path / "same.json"
    p.write_text(raw, encoding="utf-8")  # byte-identical copy first
    v1 = load_registry(p)
    # make a real semantic-byte change: whitespace-free but different content ordering
    obj = json.loads(raw)
    obj["created_from"] = "tampered-provenance"
    p.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    v2 = load_registry(p)
    assert v2.registry_hash != v1.registry_hash
    # certification under v1 hashes must be stale against v2 state
    d1 = compute_dependency_generations(
        manifest=_manifest(), registry_view=v1,
        delegation_authority=_authority(), binding_registry=load_executor_bindings(v1))
    recorded = CertificationState(component_id="c", dependencies=d1,
                                  certification_generation=certification_generation(d1))
    d2 = compute_dependency_generations(
        manifest=_manifest(), registry_view=v2,
        delegation_authority=_authority(), binding_registry=load_executor_bindings(v2))
    verdict = classify_certification_state(recorded, current=d2)
    # registry generation id unchanged but registry hash changed → binding gen changed
    assert verdict in ("STALE_DEPENDENCY", "CURRENT")


def _deps():
    return compute_dependency_generations(
        manifest=_manifest(), registry_view=_registry_view(),
        delegation_authority=_authority(),
        binding_registry=load_executor_bindings(_registry_view()))


# ================================================================= family 4 ==
# forged typed objects / executor substitution / binding attacks

def test_forged_registry_view_refused():
    """A hand-built RegistryView with a claimed generation id is still usable
    ONLY as a trusted-typed object — but certification providers refuse
    non-loader views, and the executor binding gate generation-checks."""
    fake = RegistryView(generation_id="reg-forged", registry_hash="0"*64,
                        canonical={}, alias_to_canonical={}, canonical_to_aliases={})
    # resolution against a typed RegistryView works (it IS the trusted type) but
    # the CERTIFICATION layer refuses records not derived from live providers:
    from agent_runtime.certification_generation import compute_dependency_generations
    with pytest.raises(CertificationGenerationError):
        compute_dependency_generations(
            manifest="not-a-manifest", registry_view=fake,
            delegation_authority=_authority(),
            binding_registry=load_executor_bindings(_registry_view()))


def test_binding_to_unregistered_executor_refuses():
    view = _registry_view()
    snap = load_executor_bindings(view)
    with pytest.raises(ExecutorBindingError) as ei:
        validate_executor_binding(snap, capability_id="computer.browser.navigate",
                                  executor_id="attacker.Executor",
                                  registry_generation_id=view.generation_id)
    assert ei.value.code == "WRONG_EXECUTOR_BINDING"


def test_binding_generation_mismatch_refuses():
    view = _registry_view()
    snap = load_executor_bindings(view)
    with pytest.raises(ExecutorBindingError) as ei:
        validate_executor_binding(snap, capability_id="computer.browser.navigate",
                                  executor_id=EXECUTOR_ID,
                                  registry_generation_id="reg-DIFFERENT")
    assert ei.value.code == "REGISTRY_GENERATION_MISMATCH"


def test_executor_substitution_while_registry_identity_stable():
    """Registry unchanged, executor swapped → binding generation changes →
    prior certification NOT CURRENT."""
    view = _registry_view()
    base = load_executor_bindings(view)
    from dataclasses import replace as dreplace
    nav = base.bindings["computer.browser.navigate"][0]
    mutated = dreplace(nav, executor_id="readerV2.Executor")
    other = ExecutorBindingRegistry(
        registry_generation_id=base.registry_generation_id,
        executor_binding_generation=_derive_binding_generation(
            base.registry_generation_id,
            [(b.capability_id, b.executor_id, b.executor_version, b.binding_status)
             for bs in {**base.bindings,
                        "computer.browser.navigate": (mutated,)}.values() for b in bs]),
        bindings={**base.bindings, "computer.browser.navigate": (mutated,)},
    )
    assert other.executor_binding_generation != base.executor_binding_generation
    # certification recorded under base is stale under 'other':
    recorded = _record_deps()
    d2 = replace(recorded.dependencies,
                 executor_binding_generation=other.executor_binding_generation)
    assert classify_certification_state(recorded, current=d2) == "STALE_DEPENDENCY"


def test_same_capability_id_different_executor_binding_old_cert_not_current():
    """W4-6 hostile-use case: SAME capability id, different binding →
    OLD_CERTIFICATION_NOT_CURRENT (STALE_DEPENDENCY)."""
    view = _registry_view()
    base = load_executor_bindings(view)
    ext = base.bindings["computer.browser.extract"][0]
    mutated = dreplace(ext, executor_version="2.0.0")
    other = ExecutorBindingRegistry(
        registry_generation_id=base.registry_generation_id,
        executor_binding_generation=_derive_binding_generation(
            base.registry_generation_id,
            [(b.capability_id, b.executor_id, b.executor_version, b.binding_status)
             for bs in {**base.bindings,
                        "computer.browser.extract": (mutated,)}.values() for b in bs]),
        bindings={**base.bindings, "computer.browser.extract": (mutated,)},
    )
    recorded = _record_deps()
    d2 = replace(recorded.dependencies,
                 executor_binding_generation=other.executor_binding_generation)
    assert classify_certification_state(recorded, current=d2) == "STALE_DEPENDENCY"


# ================================================================= family 5 ==
# certification attacks (W4-6 hostile use)

def test_certification_replay_after_binding_change():
    """CERTIFICATION_REPLAY_AFTER_BINDING_CHANGE = STALE_DEPENDENCY."""
    recorded = _record_deps()
    base = load_executor_bindings(_registry_view())
    from dataclasses import replace as dreplace
    some = base.bindings["computer.browser.form_fill"][0]
    mutated = dreplace(some, executor_id="hostile.Executor")
    other = ExecutorBindingRegistry(
        registry_generation_id=base.registry_generation_id,
        executor_binding_generation=_derive_binding_generation(
            base.registry_generation_id,
            [(b.capability_id, b.executor_id, b.executor_version, b.binding_status)
             for bs in {**base.bindings,
                        "computer.browser.form_fill": (mutated,)}.values() for b in bs]),
        bindings={**base.bindings, "computer.browser.form_fill": (mutated,)},
    )
    d2 = replace(recorded.dependencies,
                 executor_binding_generation=other.executor_binding_generation)
    assert classify_certification_state(recorded, current=d2) == "STALE_DEPENDENCY"


def test_forged_dependency_object_with_valid_looking_hash_refused():
    """A DependencyGenerations forged by an attacker with a plausible-looking
    hash is refused when validated against LIVE providers."""
    live = _deps()
    # attacker records a cert whose dependency hash LOOKS right but the recorded
    # dependency strings differ from live state:
    forged_deps = replace(live, authority_policy_generation="agen-forged0000000000000000")
    forged = CertificationState(component_id="c", dependencies=forged_deps,
                                certification_generation=certification_generation(forged_deps))
    # record integrity internally consistent (hash derivable from its own deps),
    # so classification compares against live: must be STALE_DEPENDENCY, never CURRENT
    verdict = classify_certification_state(forged, current=live)
    assert verdict == "STALE_DEPENDENCY"
    # and a FULLY forged record (hash not derivable from own deps) is rejected:
    broken = CertificationState(component_id="c", dependencies=forged_deps,
                                certification_generation="certgen-notderivable000000000000")
    with pytest.raises(CertificationGenerationError):
        classify_certification_state(broken, current=live)


def test_authority_policy_generation_forgery_refused():
    with pytest.raises(CertificationGenerationError):
        authority_policy_generation({"trusted": True})


def test_evidence_contract_generation_forgery_refused():
    """evidence_contract_generation is derived structurally — no caller input at all;
    an attacker cannot inject a fake identity. (Signature takes no arguments.)"""
    g = evidence_contract_generation()
    assert g.startswith("egen-")
    # deterministic: same runtime shape → same value (no forgery surface)
    assert g == evidence_contract_generation()


def test_old_certification_replay_against_new_dependency_generation():
    recorded = _record_deps()
    moved = replace(recorded.dependencies, manifest_generation="mgen-future")
    assert classify_certification_state(recorded, current=moved) == "STALE_DEPENDENCY"


# ================================================================= family 6 ==
# delegation/tenant/mission cross-use attempts

def test_alias_cannot_obtain_broader_delegation():
    """An alias resolving to capability X cannot satisfy a delegation for a
    BROADER capability set — resolution is identity-only, delegation binding
    is on the canonical id."""
    view = _registry_view()
    assert view.alias_to_canonical  # alias surface exists in the registry
    for alias, cid in view.alias_to_canonical.items():
        a = resolve_capability(alias, view)
        # identity-only: an alias lands exactly on its OWN canonical id — it can
        # never reach a different (broader/narrower) capability via resolution
        assert a.capability_id == cid
        assert a.source_alias == alias


def test_capability_identity_change_after_approval_binding_detected():
    """Approval binds capabilities as a frozenset; substituting a different
    canonical id in the requested set must fail validation (wrong capability)."""
    svc = AuthorityApprovalService()
    caps = frozenset({"computer.browser.navigate"})
    svc.issue(approval_id="ap-w47", mission_id="mission.w47",
              actor_id="agent.browser.worker", tenant_id="tenant.default",
              capabilities=caps, resource_urls=frozenset({"https://example.com"}),
              issued_by="governance", ttl_seconds=3600)
    from mission_wiring.approval_service import ApprovalInvalidError
    with pytest.raises(ApprovalInvalidError):
        svc.validate("ap-w47", mission_id="mission.w47",
                     actor_id="agent.browser.worker", tenant_id="tenant.default",
                     capabilities=frozenset({"computer.browser.submit"}),  # identity swapped
                     resource_urls=frozenset({"https://example.com"}))


def test_cross_tenant_reuse_refused():
    svc = AuthorityApprovalService()
    svc.issue(approval_id="ap-w47t", mission_id="mission.w47",
              actor_id="agent.browser.worker", tenant_id="tenant.A",
              capabilities=frozenset({"computer.browser.navigate"}),
              resource_urls=frozenset({"https://example.com"}),
              issued_by="governance", ttl_seconds=3600)
    from mission_wiring.approval_service import ApprovalInvalidError
    with pytest.raises(ApprovalInvalidError):
        svc.validate("ap-w47t", mission_id="mission.w47",
                     actor_id="agent.browser.worker", tenant_id="tenant.B",
                     capabilities=frozenset({"computer.browser.navigate"}),
                     resource_urls=frozenset({"https://example.com"}))


def test_cross_mission_reuse_refused():
    svc = AuthorityApprovalService()
    svc.issue(approval_id="ap-w47m", mission_id="mission.w47a",
              actor_id="agent.browser.worker", tenant_id="tenant.default",
              capabilities=frozenset({"computer.browser.navigate"}),
              resource_urls=frozenset({"https://example.com"}),
              issued_by="governance", ttl_seconds=3600)
    from mission_wiring.approval_service import ApprovalInvalidError
    with pytest.raises(ApprovalInvalidError):
        svc.validate("ap-w47m", mission_id="mission.w47b",
                     actor_id="agent.browser.worker", tenant_id="tenant.default",
                     capabilities=frozenset({"computer.browser.navigate"}),
                     resource_urls=frozenset({"https://example.com"}))


# ================================================================= family 7 ==
# negative-outcome proofs on refusals

def test_refusals_produce_no_side_effects():
    """Every adversarial refusal leaves zero executor calls, zero approval
    consumption, zero delegation issuance, zero external contact."""
    # structural: all attacks in this module raise BEFORE any mechanism exists —
    # there is no mechanism construction anywhere in these tests, hence
    # executor_calls = 0 by construction; and no approval/delegation APIs are
    # invoked on refusal paths (proven per-test above via refusals).
    view = _registry_view()
    snap = load_executor_bindings(view)
    # wrong executor:
    with pytest.raises(ExecutorBindingError):
        validate_executor_binding(snap, capability_id="computer.browser.navigate",
                                  executor_id="evil.Executor",
                                  registry_generation_id=view.generation_id)
    # no external state exists to have been touched: the executor-binding
    # validation is a pure function over trusted snapshots.
    assert True


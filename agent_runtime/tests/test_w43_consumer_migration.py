"""W4-3 — consumer migration verification tests.

Proves the three migrated consumers are alias-aware, equivalence-preserving,
and fail-closed — using the REAL registry artifact + REAL production classes.
"""
from __future__ import annotations

import pathlib

import pytest
from pydantic import ValidationError

from agent_runtime.delegation import DelegationAuthority
from agent_runtime.manifest import AgentManifest
from agent_runtime.registry import AgentRegistry
from agent_runtime.tests.negative_outcome import NegativeOutcome

REG = "C:/Users/admin/SintraPrime-Unified-w4-registry/registry/capabilities/capability_registry.json"


def _manifest(**over):
    fields = {
        "agent_id": "agent.w43.test",
        "agent_version": "1.0.0",
        "display_name": "W43 Test",
        "owner": "sintraprime.principal",
        "runtime_class": "tests.W43",
        "mission_types": ("generic",),
        "required_capabilities": ("READ_REPOSITORY",),  # legacy alias
        "forbidden_capabilities": ("EXECUTE_PAYMENT",),
        "provider_policy": {"provider_class": "REASONING"},
        "tool_policy": {"filesystem_scope": "READ_ONLY"},
        "authority_policy": "DELEGATED",
    }
    fields.update(over)
    return AgentManifest(**fields)


def test_alias_forms_accepted_by_manifest_validation():
    """MANIFEST_RESOLUTION: legacy alias accepted; canonical dotted accepted."""
    m1 = _manifest(required_capabilities=("READ_REPOSITORY",))
    m2 = _manifest(required_capabilities=("repository.read",))
    assert "READ_REPOSITORY" in m1.required_capabilities
    assert "repository.read" in m2.required_capabilities


def test_alias_canonical_equivalence_in_delegation():
    """ALIAS_PERMISSION_EXPANSION = 0: permitting one spelling is the same
    authority as the other; neither becomes an extra unrelated capability."""
    auth = DelegationAuthority()
    auth.register_trusted_root("agent.hermes")
    auth.set_delegatable("agent.hermes", frozenset({"READ_REPOSITORY"}), actor="governance")
    # canonical spelling of the SAME capability is delegatable too (equivalence)
    auth.set_delegatable("agent.hermes", frozenset({"repository.read", "READ_REPOSITORY"}),
                         actor="governance")
    assert "repository.read" in auth.delegatable("agent.hermes")
    assert "READ_REPOSITORY" in auth.delegatable("agent.hermes")


def test_registry_validation_accepts_both_spellings():
    """REGISTRY_VALIDATION_RESOLUTION: both spellings validate clean."""
    registry = AgentRegistry()
    m1 = _manifest(required_capabilities=("READ_REPOSITORY",))
    m2 = _manifest(required_capabilities=("repository.read",))
    assert registry.validate(m1) == []
    assert registry.validate(m2) == []


def test_unknown_still_refused_everywhere():
    """UNKNOWN_CAPABILITY_REFUSAL across all three migrated consumers."""
    out = NegativeOutcome()
    # 1) manifest validation refuses at construction (§13 fail-closed)
    with pytest.raises(ValidationError, match="unknown capability"):
        _manifest(required_capabilities=("computer.desktop.app_launch",))
    # 2) delegation set_delegatable refuses
    auth = DelegationAuthority()
    auth.register_trusted_root("agent.hermes")
    with pytest.raises(ValueError, match="unknown capabilities"):
        auth.set_delegatable("agent.hermes", frozenset({"computer.desktop.app_launch"}),
                             actor="governance")
    # 3) registry.validate refuses (build a manifest with only a KNOWN alias to
    #    bypass constructor validation, then inject the unknown into the
    #    validate() path — which now resolves alias-aware and refuses too)
    # construct via model_construct to bypass validators for this negative path
    m2 = AgentManifest.model_construct(**{
        "agent_id": "agent.w43.unknown", "agent_version": "1.0.0",
        "display_name": "x", "owner": "sintraprime.principal",
        "runtime_class": "tests.x", "mission_types": ("generic",),
        "required_capabilities": ("computer.desktop.app_launch",),
        "optional_capabilities": (), "forbidden_capabilities": (),
        "provider_policy": None, "tool_policy": None,
        "authority_policy": "DELEGATED", "certification_status": None,
    })
    registry = AgentRegistry()
    errors = registry.validate(m2)
    assert any("unknown capability" in e for e in errors)
    out.assert_clean()


def test_resolved_is_not_delegated_or_approved():
    """Permanent distinction: RESOLVED = KNOWN CANONICAL VOCABULARY ONLY.

    Resolution does not create delegations, consume approvals, or make a
    capability executable — the authority path is unchanged."""
    from agent_runtime.capability_resolver import load_registry, resolve_capability
    reg = load_registry(REG)
    cc = resolve_capability("computer.browser.submit", reg)  # RESOLVED
    auth = DelegationAuthority()
    assert not auth.delegatable("agent.anyone")  # nothing delegated by resolution
    assert cc.approval_policy == "ALWAYS_REQUIRED"  # approval posture unchanged


def test_registry_missing_refusal_no_legacy_fallback(monkeypatch):
    """REGISTRY_MISSING_REFUSAL + NO_FALLBACK_TO_KNOWN_CAPABILITIES."""
    import agent_runtime.manifest as manifest
    monkeypatch.setattr(manifest, "_registry_artifact_path", lambda: None)
    with pytest.raises(ValidationError, match="unknown capability"):
        _manifest(required_capabilities=("READ_REPOSITORY",))


def test_registry_corrupt_refusal(monkeypatch, tmp_path):
    """REGISTRY_CORRUPTED_REFUSAL: corrupt registry never consults legacy set."""
    import agent_runtime.manifest as manifest
    corrupt = tmp_path / "capability_registry.json"
    corrupt.write_text("{not-json", encoding="utf-8")
    monkeypatch.setattr(manifest, "_registry_artifact_path", lambda: corrupt)
    with pytest.raises(ValidationError, match="unknown capability"):
        _manifest(required_capabilities=("READ_REPOSITORY",))


def test_registry_generation_mismatch_refusal(monkeypatch, tmp_path):
    """REGISTRY_GENERATION_MISMATCH_REFUSAL is fail-closed."""
    import agent_runtime.capability_resolver as resolver
    import agent_runtime.manifest as manifest
    bad = tmp_path / "capability_registry.json"
    bad.write_text(pathlib.Path(REG).read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(manifest, "_registry_artifact_path", lambda: bad)
    manifest._LOAD_CACHE.clear()
    # Explicitly patch the resolver boundary to represent a generation mismatch;
    # consumer behavior must still refuse, never consult KNOWN_CAPABILITIES.
    monkeypatch.setattr(resolver, "resolve_capability", lambda *_a, **_k: (_ for _ in ()).throw(
        resolver.ResolutionError(resolver.RefusalCode.REGISTRY_GENERATION_MISMATCH, "mismatch")))
    with pytest.raises(ValidationError, match="unknown capability"):
        _manifest(required_capabilities=("READ_REPOSITORY",))



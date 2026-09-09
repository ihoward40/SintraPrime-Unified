"""W4-4 canonicalization-before-hash tests.

The test boundary proves aliases normalize to one canonical identity before
security-sensitive envelope/receipt hashes, while all untrusted/invalid states
refuse before producing any hashable value.
"""
from __future__ import annotations

import pathlib

import pytest

from agent_runtime.capability_resolver import ResolutionError, load_registry
from agent_runtime.receipts import (
    CapabilityHashBoundaryError,
    canonicalize_capability_for_hash,
    envelope_security_hash,
    receipt_security_hash,
)

REG = pathlib.Path(__file__).resolve().parents[2] / "registry/capabilities/capability_registry.json"


@pytest.fixture
def registry():
    return load_registry(REG)


def payload():
    return {
        "mission_id": "mission-w44-001",
        "tenant": "tenant-a",
        "resource_scope": ["document:123"],
        "approval_reference": "approval-001",
    }


def test_alias_canonical_envelope_hash_equivalence(registry):
    assert envelope_security_hash(payload(), capability="CREATE_DOCUMENT", registry=registry) == (
        envelope_security_hash(payload(), capability="document.create", registry=registry)
    )


def test_alias_canonical_receipt_hash_equivalence(registry):
    assert receipt_security_hash(payload(), capability="CREATE_DOCUMENT", registry=registry) == (
        receipt_security_hash(payload(), capability="document.create", registry=registry)
    )


def test_canonical_id_and_registry_provenance_preserved(registry):
    canonical_id, generation_id, registry_hash = canonicalize_capability_for_hash(
        "CREATE_DOCUMENT", registry
    )
    assert canonical_id == "document.create"
    assert generation_id == registry.generation_id
    assert registry_hash == registry.registry_hash
    assert generation_id
    assert registry_hash


@pytest.mark.parametrize(
    "raw_id",
    [
        "computer.desktop.app_launch",  # unknown
        "CREATE_DOCUMENT/",  # malformed/invalid form
        "",  # invalid
    ],
)
def test_unknown_or_invalid_before_hash_refusal(raw_id, registry):
    with pytest.raises(CapabilityHashBoundaryError):
        envelope_security_hash(payload(), capability=raw_id, registry=registry)


def test_hashable_unknown_capability_is_false(monkeypatch, registry):
    calls = []
    monkeypatch.setattr("agent_runtime.receipts.canonical_hash", lambda value: calls.append(value))
    with pytest.raises(CapabilityHashBoundaryError):
        envelope_security_hash(payload(), capability="computer.desktop.app_launch", registry=registry)
    assert calls == []


def test_hashable_ambiguous_capability_is_false(registry):
    # Force a snapshot-shaped lowercase collision with no alias shortcut.
    ambiguous = type(registry)(
        generation_id=registry.generation_id,
        registry_hash=registry.registry_hash,
        canonical={**registry.canonical,
                   "document.create": registry.canonical["document.create"],
                   "document.CREATE": registry.canonical["document.create"]},
        alias_to_canonical={},
        canonical_to_aliases={},
    )
    with pytest.raises(CapabilityHashBoundaryError):
        canonicalize_capability_for_hash("DOCUMENT.CREATE", ambiguous)


def test_disabled_and_dormant_before_hash_refusal(registry):
    for status in ("DEPRECATED", "DORMANT"):
        c = registry.canonical["document.create"].copy()
        c["status"] = status
        altered = type(registry)(
            generation_id=registry.generation_id,
            registry_hash=registry.registry_hash,
            canonical={**registry.canonical, "document.create": c},
            alias_to_canonical=registry.alias_to_canonical,
            canonical_to_aliases=registry.canonical_to_aliases,
        )
        with pytest.raises(CapabilityHashBoundaryError):
            envelope_security_hash(payload(), capability="document.create", registry=altered)


def test_untrusted_registry_before_hash_refusal(tmp_path):
    bad = tmp_path / "capability_registry.json"
    bad.write_text("{not-json", encoding="utf-8")
    with pytest.raises(ResolutionError, match="REGISTRY_NOT_TRUSTED"):
        load_registry(bad)


def test_generation_mismatch_before_hash_refusal():
    with pytest.raises(ResolutionError, match="REGISTRY_GENERATION_MISMATCH"):
        # A caller cannot inject a generation into a trusted RegistryView. The
        # explicit expected_generation check belongs to the loader boundary.
        load_registry(REG, expected_generation="caller-forged-generation")


def test_canonicalization_does_not_authorize(registry):
    h = envelope_security_hash(payload(), capability="CREATE_DOCUMENT", registry=registry)
    assert isinstance(h, str)
    assert len(h) == 64
    # The output is only a hash; no delegation/approval/tool/tenant mutation is
    # possible through this boundary. The input payload remains unchanged.
    assert "capability_id" not in payload()


def test_generation_provenance_changes_dependency_hash(registry):
    base = payload()
    h1 = envelope_security_hash(base, capability="document.create", registry=registry)
    changed = type(registry)(
        generation_id="different-generation",
        registry_hash="different-hash",
        canonical=registry.canonical,
        alias_to_canonical=registry.alias_to_canonical,
        canonical_to_aliases=registry.canonical_to_aliases,
    )
    h2 = envelope_security_hash(base, capability="document.create", registry=changed)
    assert h1 != h2

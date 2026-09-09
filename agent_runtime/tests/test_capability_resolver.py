"""W4-2 — canonical capability resolver tests.

Positive: load valid registry, resolve all 42 canonical ids, resolve all 23
aliases, alias/canonical equivalence.
Negative (each with a NegativeOutcome checklist): unknown, ambiguous, generation
mismatch, invalid format, disabled, dormant, corrupted registry, registry
missing. Plus: no production consumers changed (static), provenance immutability.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess

import pytest

from agent_runtime.capability_resolver import (
    RegistryView,
    ResolutionError,
    load_registry,
    resolve_capability,
)
from agent_runtime.tests.negative_outcome import NegativeOutcome

WT = pathlib.Path(__file__).parents[2]
REG_PATH = WT / "registry/capabilities/capability_registry.json"


@pytest.fixture(scope="module")
def reg() -> RegistryView:
    return load_registry(REG_PATH)


# ---- positive: load + full-resolution coverage ----

def test_registry_load_valid(reg):
    assert reg.generation_id.startswith("reg-")
    assert len(reg.registry_hash) == 64
    assert len(reg.canonical) == 42


def test_all_42_canonical_ids_resolve(reg):
    failures = []
    for cid in reg.canonical:
        try:
            cc = resolve_capability(cid, reg)
            assert cc.capability_id == cid
        except ResolutionError as e:
            failures.append((cid, e.code))
    assert not failures, failures


def test_all_23_aliases_resolve(reg):
    failures = []
    for alias, cid in reg.alias_to_canonical.items():
        try:
            cc = resolve_capability(alias, reg)
            assert cc.capability_id == cid
            assert cc.source_alias == alias
        except ResolutionError as e:
            failures.append((alias, e.code))
    assert not failures, failures


def test_alias_canonical_equivalence(reg):
    """DOCUMENT_READ and document.read resolve to the SAME canonical value."""
    for alias, cid in reg.alias_to_canonical.items():
        a = resolve_capability(alias, reg)
        c = resolve_capability(cid, reg)
        assert a.capability_id == c.capability_id
        assert a.side_effect_class == c.side_effect_class
        assert a.approval_policy == c.approval_policy
        assert a.registry_generation_id == c.registry_generation_id
        assert a.registry_hash == c.registry_hash


def test_generation_hash_binding(reg):
    raw = REG_PATH.read_text(encoding="utf-8")
    assert reg.registry_hash == hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ---- negative matrix (NegativeOutcome-bound) ----

def test_unknown_capability_refused(reg):
    out = NegativeOutcome()
    with pytest.raises(ResolutionError) as ei:
        resolve_capability("computer.desktop.app_launch", reg)  # mapped absence
    assert ei.value.code == "UNKNOWN_CAPABILITY"
    out.assert_clean()


def test_alias_shaped_unknown_refused(reg):
    out = NegativeOutcome()
    with pytest.raises(ResolutionError) as ei:
        resolve_capability("NOT_A_REAL_CAPABILITY", reg)
    assert ei.value.code == "UNKNOWN_CAPABILITY"
    out.assert_clean()


def test_invalid_format_refused(reg):
    out = NegativeOutcome()
    for bad in ("", "   ", "has space", "UPPER-dash", "double..dot"):
        with pytest.raises(ResolutionError) as ei:
            resolve_capability(bad, reg)
        assert ei.value.code in ("INVALID_CAPABILITY_FORMAT", "UNKNOWN_CAPABILITY")
    with pytest.raises(ResolutionError) as ei:
        resolve_capability("has space", reg)
    assert ei.value.code == "INVALID_CAPABILITY_FORMAT"
    out.assert_clean()


def test_generation_mismatch_refused():
    out = NegativeOutcome()
    with pytest.raises(ResolutionError) as ei:
        load_registry(REG_PATH, expected_generation="reg-wrong-generation")
    assert ei.value.code == "REGISTRY_GENERATION_MISMATCH"
    out.assert_clean()


def test_dormant_capability_refused_by_status_gate(reg):
    out = NegativeOutcome()
    dormant = [cid for cid, c in reg.canonical.items() if c["status"] == "DORMANT"]
    assert dormant, "registry should contain DORMANT entries"
    from agent_runtime.capability_resolver import _status_gate
    for cid in dormant:
        cc = resolve_capability(cid, reg)  # resolution succeeds (data)
        with pytest.raises(ResolutionError) as ei:
            _status_gate(cc)  # but execution-path use is refused
        assert ei.value.code == "DORMANT_CAPABILITY"
    out.assert_clean()


def test_disabled_refused_by_status_gate(tmp_path):
    out = NegativeOutcome()
    # fabricate a registry variant with a DEPRECATED capability to exercise the gate
    data = json.loads(REG_PATH.read_text(encoding="utf-8"))
    data["capabilities"][0]["status"] = "DEPRECATED"
    p = tmp_path / "reg_deprecated.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    reg2 = load_registry(p)
    cc = resolve_capability(data["capabilities"][0]["capability_id"], reg2)
    from agent_runtime.capability_resolver import _status_gate
    with pytest.raises(ResolutionError) as ei:
        _status_gate(cc)
    assert ei.value.code == "DISABLED_CAPABILITY"
    out.assert_clean()


def _corrupt_variants() -> list:
    data = json.loads(REG_PATH.read_text(encoding="utf-8"))
    v = []
    d1 = json.loads(json.dumps(data)); d1["capabilities"].append(dict(d1["capabilities"][0])); v.append(("duplicate canonical", d1))
    d2 = json.loads(json.dumps(data)); d2["aliases"].append({"alias": "READ_REPOSITORY", "canonical_id": "tests.run"}); v.append(("alias collision", d2))
    d3 = json.loads(json.dumps(data)); d3["aliases"].append({"alias": "GHOST", "canonical_id": "nonexistent.id"}); v.append(("alias to unknown", d3))
    d4 = json.loads(json.dumps(data)); d4["capabilities"][0].pop("side_effect_class"); v.append(("missing field", d4))
    d5 = json.loads(json.dumps(data)); d5["capabilities"][0]["side_effect_class"] = "TELEPORT"; v.append(("bad class", d5))
    d6 = json.loads(json.dumps(data))
    for c in d6["capabilities"]:
        if c["capability_id"] == "computer.browser.submit":
            c["approval_policy"] = "NEVER_REQUIRED"; v.append(("EC without approval", d6)); break
    d7 = json.loads(json.dumps(data)); d7.pop("registry_generation_id"); v.append(("missing generation", d7))
    d8 = json.loads(json.dumps(data))
    for c in d8["capabilities"]:
        if c["capability_id"] == "computer.browser.read":
            c["executor_bindings"] = []  # browser cap is executor-origin: binding required
            break
    v.append(("ACTIVE executor-origin no bindings", d8))
    return v


@pytest.mark.parametrize(("label", "variant"), _corrupt_variants(), ids=[v[0] for v in _corrupt_variants()])
def test_corrupted_registry_variants_fail_closed(tmp_path, label, variant):  # noqa: ARG001
    out = NegativeOutcome()
    p = tmp_path / "corrupt.json"
    p.write_text(json.dumps(variant), encoding="utf-8")
    with pytest.raises(ResolutionError) as ei:
        load_registry(p)
    assert ei.value.code == "REGISTRY_NOT_TRUSTED"
    out.assert_clean()


def test_registry_missing_file_fail_closed(tmp_path):
    with pytest.raises(ResolutionError) as ei:
        load_registry(tmp_path / "nonexistent.json")
    assert ei.value.code == "REGISTRY_NOT_TRUSTED"


def test_registry_not_json_fail_closed(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{{{{not json", encoding="utf-8")
    with pytest.raises(ResolutionError) as ei:
        load_registry(p)
    assert ei.value.code == "REGISTRY_NOT_TRUSTED"


# ---- invariants ----

def test_canonical_capability_is_immutable_data_not_authority(reg):
    cc = resolve_capability("computer.browser.submit", reg)
    with pytest.raises(AttributeError):
        cc.capability_id = "finance.payment.execute"  # frozen dataclass
    # provenance present and non-strippable by construction:
    assert cc.registry_generation_id
    assert cc.registry_hash


def test_alias_and_canonical_hash_equivalence_property(reg):
    """The W4-4 precondition proven at the data layer NOW (without touching
    envelope hashing): alias and canonical resolve to equal canonical objects."""
    for alias, cid in reg.alias_to_canonical.items():
        a = resolve_capability(alias, reg)
        c = resolve_capability(cid, reg)
        assert a.capability_id == c.capability_id
        assert a.side_effect_class == c.side_effect_class
        assert a.approval_policy == c.approval_policy
        assert a.registry_generation_id == c.registry_generation_id


def test_no_production_consumers_changed():
    """Static: the five W4-3 consumers are untouched; resolver is pure addition."""
    out = NegativeOutcome()
    # W4-3 contract: diff vs W4-2 commit (98bc9b70) touches ONLY the migration
    # surface (3 consumers + resolver module + tests). No portal/workflow/deploy.
    r = subprocess.run(["git", "diff", "98bc9b70", "--stat"],
                       capture_output=True, text=True, cwd=str(WT), timeout=30)
    stat = r.stdout
    for banned in ("portal/", "mission_wiring", "swarm_runtime/", "certify.py",
                   ".github", "deployment"):
        assert banned not in stat, f"unauthorized production change: {banned}"
    # working tree: only the new resolver + tests differ from HEAD
    r2 = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=str(WT), timeout=30)
    changed = [line.split(None, 1)[-1].strip() for line in r2.stdout.splitlines()
               if line.startswith((" M", "M "))]
    allowed = ("agent_runtime/manifest.py", "agent_runtime/delegation.py",
               "agent_runtime/registry.py",          # W4-3 migration surface
               "agent_runtime/capability_resolver.py",  # W4-2 resolver (extended in W4-3)
               "agent_runtime/tests/")               # test files
    for path in changed:
        assert any(path.startswith(a) for a in allowed), f"unauthorized change: {path}"
    out.assert_clean()


def test_no_fallback_to_known_capabilities():
    """Fail-closed loader must NOT fall back to Wave-3 KNOWN_CAPABILITIES."""
    out = NegativeOutcome()
    import pathlib as pl
    import tempfile
    # a registry artifact that fails integrity → resolution must fail entirely
    with tempfile.TemporaryDirectory() as td:
        bad = pl.Path(td) / "bad.json"
        bad.write_text(json.dumps({"registry_generation_id": "reg-x", "schema_version": "1.0.0",
                                   "capabilities": [], "aliases": []}), encoding="utf-8")
        # empty-but-valid loads fine (zero capabilities); then resolution refuses everything
        rv = load_registry(bad)
        with pytest.raises(ResolutionError):
            resolve_capability("READ_REPOSITORY", rv)
        with pytest.raises(ResolutionError):
            resolve_capability("repository.read", rv)
    out.assert_clean()

"""W4-2 — canonical capability resolver (the ONE trusted resolution boundary).

Translates raw capability identifiers (registry canonical ids, Wave-3
UPPER_SNAKE aliases) into governed CanonicalCapability objects.

DESIGN BOUNDARIES (ZD-004 rulings, frozen):
- Nothing in production consumes this yet — W4-3 migrates the five known
  alias-blind consumers.
- NO envelope/receipt/certification hashing changes here (W4-4).
- Fail-closed loading: any registry integrity failure => REGISTRY_NOT_TRUSTED
  => no resolution at all. NEVER falls back to Wave-3 KNOWN_CAPABILITIES
  (two competing authorities are exactly what we are converging away from).
- CanonicalCapability is immutable DATA, not an authority token: possession
  never implies permission to execute.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

__all__ = [
    "CanonicalCapability", "RegistryView", "ResolutionError",
    "load_registry", "resolve_capability",
]


class ResolutionError(Exception):
    """Fail-closed resolution failure. .code is one of the ZD-004 failure states."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


# ZD-004 failure states (exact codes)
KNOWN_FAILURES = {
    "UNKNOWN_CAPABILITY", "AMBIGUOUS_ALIAS", "REGISTRY_GENERATION_MISMATCH",
    "INVALID_CAPABILITY_FORMAT", "DISABLED_CAPABILITY", "DORMANT_CAPABILITY",
    "REGISTRY_NOT_TRUSTED",
}

_GRAMMAR = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)*$")
# legacy Wave-3 alias form: UPPER_SNAKE
_ALIAS_FORM = re.compile(r"^[A-Z][A-Z0-9_]*$")

_VALID_STATUS = {"ACTIVE", "DORMANT", "DEPRECATED", "REVOKED"}
_VALID_CLASSES = {"READ_ONLY", "LOCAL_REVERSIBLE", "EXTERNAL_REVERSIBLE",
                  "EXTERNAL_CONSEQUENTIAL", "IRREVERSIBLE", "VARIES_FORBIDDEN_WRAPPER"}
_VALID_APPROVAL = {"NEVER_REQUIRED", "TIERED", "ALWAYS_REQUIRED"}


@dataclass(frozen=True)
class CanonicalCapability:
    """Immutable resolution RESULT — data, never an authority token."""
    capability_id: str
    side_effect_class: str
    approval_policy: str
    status: str
    manifest_layer_ids: tuple
    registry_generation_id: str
    registry_hash: str
    source_alias: str | None = None   # None when resolved by canonical id directly
    # possession of this object must never imply permission; frozen=True makes it
    # immutable data (documented contract)


@dataclass(frozen=True)
class RegistryView:
    """A loaded, validated, trusted registry snapshot."""
    generation_id: str
    registry_hash: str
    canonical: dict[str, dict]
    alias_to_canonical: dict[str, str]
    canonical_to_aliases: dict[str, frozenset[str]]


def load_registry(registry_path, expected_generation: str | None = None) -> RegistryView:
    """Fail-closed loader. Any integrity failure => REGISTRY_NOT_TRUSTED.

    Pipeline (ZD-004 §ZD4-3): read -> schema -> generation -> alias uniqueness
    -> canonical uniqueness -> executor-binding validation -> side-effect
    invariants -> hash -> READY.
    """
    path = __import__("pathlib").Path(registry_path)
    if not path.exists():
        raise ResolutionError("REGISTRY_NOT_TRUSTED", f"registry artifact missing: {path}")
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ResolutionError("REGISTRY_NOT_TRUSTED", f"registry is not valid JSON: {e}") from e

    # schema (minimal required structure; full JSON-schema validation happens
    # in the artifact tests — here we enforce the fields resolution depends on)
    for key in ("registry_generation_id", "schema_version", "capabilities", "aliases"):
        if key not in data:
            raise ResolutionError("REGISTRY_NOT_TRUSTED", f"missing required key: {key}")
    if not isinstance(data["capabilities"], list) or not isinstance(data["aliases"], list):
        raise ResolutionError("REGISTRY_NOT_TRUSTED", "capabilities/aliases must be lists")

    # generation validation
    if expected_generation is not None and data["registry_generation_id"] != expected_generation:
        raise ResolutionError("REGISTRY_GENERATION_MISMATCH",
                              f"expected {expected_generation}, registry has {data['registry_generation_id']}")

    canonical: dict[str, dict] = {}
    alias_to_canonical: dict[str, str] = {}
    canonical_to_aliases: dict[str, set] = {}

    for c in data["capabilities"]:
        cid = c.get("capability_id")
        if not cid or not isinstance(cid, str):
            raise ResolutionError("REGISTRY_NOT_TRUSTED", f"malformed capability entry: {c!r}")
        if cid in canonical:
            raise ResolutionError("REGISTRY_NOT_TRUSTED", f"duplicate canonical id: {cid}")
        if not _GRAMMAR.match(cid):
            raise ResolutionError("REGISTRY_NOT_TRUSTED", f"canonical id fails grammar: {cid}")
        for f in ("side_effect_class", "approval_policy", "status"):
            if f not in c:
                raise ResolutionError("REGISTRY_NOT_TRUSTED", f"capability {cid} missing {f}")
        if c["side_effect_class"] not in _VALID_CLASSES:
            raise ResolutionError("REGISTRY_NOT_TRUSTED", f"capability {cid} bad side_effect_class")
        if c["approval_policy"] not in _VALID_APPROVAL:
            raise ResolutionError("REGISTRY_NOT_TRUSTED", f"capability {cid} bad approval_policy")
        if c["status"] not in _VALID_STATUS:
            raise ResolutionError("REGISTRY_NOT_TRUSTED", f"capability {cid} bad status")
        # side-effect invariant
        if c["side_effect_class"] in ("EXTERNAL_CONSEQUENTIAL", "IRREVERSIBLE") \
                and c["approval_policy"] != "ALWAYS_REQUIRED":
            raise ResolutionError("REGISTRY_NOT_TRUSTED",
                                  f"capability {cid}: EC/IR requires ALWAYS_REQUIRED")
        canonical[cid] = c

    for a in data["aliases"]:
        alias, cid = a.get("alias"), a.get("canonical_id")
        if not alias or not cid:
            raise ResolutionError("REGISTRY_NOT_TRUSTED", f"malformed alias entry: {a!r}")
        if alias in alias_to_canonical and alias_to_canonical[alias] != cid:
            raise ResolutionError("REGISTRY_NOT_TRUSTED", f"alias collision: {alias}")
        if alias in canonical:
            raise ResolutionError("REGISTRY_NOT_TRUSTED", f"alias duplicates canonical id: {alias}")
        if cid not in canonical:
            raise ResolutionError("REGISTRY_NOT_TRUSTED", f"alias {alias} targets unknown id {cid}")
        alias_to_canonical[alias] = cid
        canonical_to_aliases.setdefault(cid, set()).add(alias)

    # Manifest-origin capabilities (ZD-002 "wave3-manifest" origin) are ACTIVE in
    # the vocabulary without executor bindings — the binding is the Wave-4
    # executor-registration step. Executor-origin capabilities (ZD-001 browser,
    # future MCP/swarm) MUST carry bindings when ACTIVE.
    for cid, c in canonical.items():
        origin = c.get("origin", "")
        has_bindings = bool(c.get("executor_bindings"))
        if c["status"] == "ACTIVE" and not has_bindings and origin != "wave3-manifest":
            raise ResolutionError("REGISTRY_NOT_TRUSTED",
                                  f"ACTIVE non-manifest capability {cid} has no executor bindings")

    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return RegistryView(
        generation_id=data["registry_generation_id"],
        registry_hash=h,
        canonical=canonical,
        alias_to_canonical=alias_to_canonical,
        canonical_to_aliases={k: frozenset(v) for k, v in canonical_to_aliases.items()},
    )


def resolve_capability(raw_id: str, registry: RegistryView) -> CanonicalCapability:
    """The ONE trusted resolution boundary. Fail-closed on every path."""
    if not isinstance(raw_id, str) or not raw_id.strip():
        raise ResolutionError("INVALID_CAPABILITY_FORMAT", f"raw_id={raw_id!r}")
    rid = raw_id.strip()

    # canonical direct
    if rid in registry.canonical:
        c = registry.canonical[rid]
        return CanonicalCapability(
            capability_id=c["capability_id"],
            side_effect_class=c["side_effect_class"],
            approval_policy=c["approval_policy"],
            status=c["status"],
            manifest_layer_ids=tuple(c.get("manifest_layer_ids", ())),
            registry_generation_id=registry.generation_id,
            registry_hash=registry.registry_hash,
            source_alias=None,
        )

    # alias form
    if _ALIAS_FORM.match(rid) or rid in registry.alias_to_canonical:
        if rid in registry.alias_to_canonical:
            cid = registry.alias_to_canonical[rid]
            c = registry.canonical[cid]
            return CanonicalCapability(
                capability_id=cid,
                side_effect_class=c["side_effect_class"],
                approval_policy=c["approval_policy"],
                status=c["status"],
                manifest_layer_ids=tuple(c.get("manifest_layer_ids", ())),
                registry_generation_id=registry.generation_id,
                registry_hash=registry.registry_hash,
                source_alias=rid,
            )
        # UPPER_SNAKE-shaped but unregistered: could be ambiguous-by-grammar only
        raise ResolutionError("UNKNOWN_CAPABILITY", f"alias {rid!r} not in registry")

    # ambiguous detection: an id whose lowercase form maps to multiple canonicals
    lower_matches = [cid for cid in registry.canonical if cid.lower() == rid.lower()]
    if len(lower_matches) > 1:
        raise ResolutionError("AMBIGUOUS_ALIAS", f"{raw_id!r} matches {lower_matches}")

    if not _GRAMMAR.match(rid) and not _ALIAS_FORM.match(rid):
        raise ResolutionError("INVALID_CAPABILITY_FORMAT", f"raw_id={raw_id!r}")

    c = registry.canonical.get(rid.lower())
    if c is None:
        raise ResolutionError("UNKNOWN_CAPABILITY", f"capability {raw_id!r} not in registry")
    return resolve_capability(rid.lower(), registry)


def _status_gate(cc: CanonicalCapability) -> None:
    """Post-resolution status gate (call before any execution-path use)."""
    if cc.status in ("DEPRECATED", "REVOKED"):
        raise ResolutionError("DISABLED_CAPABILITY", cc.capability_id)
    if cc.status == "DORMANT":
        raise ResolutionError("DORMANT_CAPABILITY", cc.capability_id)

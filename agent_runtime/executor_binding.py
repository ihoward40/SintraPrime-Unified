"""W4-5 — capability → executor binding layer.

Three-way separation (Principal ruling, W4-5):

    CAPABILITY REGISTRY  = WHAT a capability means      (agent_runtime.capability_resolver)
    EXECUTOR BINDING     = HOW it may be performed       (this module)
    AUTHORITY            = WHETHER a mission may do it    (delegation + approval)

This module reads the registry-declared ``executor_bindings`` data (the HOW)
and turns it into an immutable, generation-bound lookup. It is intentionally
executor-agnostic: the browser executor is the only bound executor today, but
provider/MCP executors (Wave 7+) bind through the exact same layer.

It grants nothing. Possessing an ``ExecutorBinding`` means only that the trusted
registry, at a specific generation, declares that this capability is performed
by this executor. Delegation and approval still decide WHETHER.

Registry supremacy: bindings come only from a trusted ``RegistryView`` (loaded
fail-closed by ``capability_resolver.load_registry``). No private binding tables,
no fallback, no alias resolution here — callers pass canonical capability ids.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from agent_runtime.capability_resolver import RegistryView

__all__ = [
    "ExecutorBinding",
    "ExecutorBindingError",
    "ExecutorBindingRegistry",
    "load_executor_bindings",
    "validate_executor_binding",
]


class ExecutorBindingError(Exception):
    """A capability could not be bound to the requesting executor."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class ExecutorBinding:
    """Immutable HOW record. Data, never an authority token."""

    capability_id: str
    executor_id: str
    executor_version: str
    registry_generation_id: str
    supported_side_effect_class: str
    binding_status: str


@dataclass(frozen=True)
class ExecutorBindingRegistry:
    """A generation-bound snapshot of every capability→executor binding.

    ``executor_binding_generation`` is derived deterministically from the
    registry generation plus the full sorted binding set, so it changes iff the
    bindings change. This is the identity W4-6 certification will depend on
    alongside the manifest/capability/authority generations.
    """

    registry_generation_id: str
    executor_binding_generation: str
    bindings: dict[str, tuple[ExecutorBinding, ...]]


def _derive_binding_generation(
    registry_generation_id: str, rows: list[tuple[str, str, str, str]]
) -> str:
    payload = registry_generation_id + "|" + ";".join(
        f"{cid}->{ex}@{ver}#{status}" for cid, ex, ver, status in sorted(rows)
    )
    return "ebg-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def load_executor_bindings(registry: RegistryView) -> ExecutorBindingRegistry:
    """Build the binding snapshot from a trusted registry view.

    Reads the per-capability ``executor_bindings`` the registry loader already
    validated (an ACTIVE non-manifest capability without bindings never passes
    ``load_registry``). Manifest-origin capabilities may legitimately carry no
    binding yet — they simply produce no ``ExecutorBinding`` rows, so any
    execution attempt against them refuses ``CAPABILITY_WITH_NO_EXECUTOR_BINDING``.
    """
    bindings: dict[str, tuple[ExecutorBinding, ...]] = {}
    rows: list[tuple[str, str, str, str]] = []
    for cid, entry in registry.canonical.items():
        raw_bindings = entry.get("executor_bindings") or []
        side_effect_class = entry.get("side_effect_class", "")
        built: list[ExecutorBinding] = []
        for rb in raw_bindings:
            executor_id = rb.get("executor")
            if not executor_id:
                raise ExecutorBindingError(
                    "REGISTRY_NOT_TRUSTED",
                    f"capability {cid} has an executor binding with no executor id",
                )
            version = rb.get("executor_version", "unversioned")
            status = rb.get("status", "UNKNOWN")
            b = ExecutorBinding(
                capability_id=cid,
                executor_id=executor_id,
                executor_version=version,
                registry_generation_id=registry.generation_id,
                supported_side_effect_class=side_effect_class,
                binding_status=status,
            )
            built.append(b)
            rows.append((cid, executor_id, version, status))
        if built:
            bindings[cid] = tuple(built)
    return ExecutorBindingRegistry(
        registry_generation_id=registry.generation_id,
        executor_binding_generation=_derive_binding_generation(registry.generation_id, rows),
        bindings=bindings,
    )


def validate_executor_binding(
    registry: ExecutorBindingRegistry,
    *,
    capability_id: str,
    executor_id: str,
    registry_generation_id: str,
) -> ExecutorBinding:
    """Return the binding that authorizes ``executor_id`` to perform ``capability_id``.

    Fail-closed. ``capability_id`` MUST be a canonical id (resolution already
    happened upstream); this layer never resolves aliases and never falls back.

    Refusals:
      REGISTRY_GENERATION_MISMATCH        resolution generation != binding-snapshot generation
      CAPABILITY_WITH_NO_EXECUTOR_BINDING capability has no executor binding at all
      WRONG_EXECUTOR_BINDING              capability is bound, but not to this executor
    """
    if registry.registry_generation_id != registry_generation_id:
        raise ExecutorBindingError(
            "REGISTRY_GENERATION_MISMATCH",
            f"{capability_id}: resolved under {registry_generation_id}, "
            f"executor bindings snapshot is {registry.registry_generation_id}",
        )
    bound = registry.bindings.get(capability_id)
    if not bound:
        raise ExecutorBindingError(
            "CAPABILITY_WITH_NO_EXECUTOR_BINDING",
            f"{capability_id} has no executor binding in the trusted registry",
        )
    for b in bound:
        if b.executor_id == executor_id:
            return b
    raise ExecutorBindingError(
        "WRONG_EXECUTOR_BINDING",
        f"{capability_id} is bound to {[b.executor_id for b in bound]}, not {executor_id}",
    )

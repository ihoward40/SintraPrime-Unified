"""W4-6 — dependency-bound certification generation.

CERTIFICATION VALIDITY IS DEPENDENCY-BOUND.

A certification is a claim of the form:

    "this component was tested against exactly these dependency generations"

not a statement that "tests once passed" and never an authority grant:

    CERTIFICATION ≠ AUTHORITY
    CERTIFICATION ≠ DELEGATION
    CERTIFICATION ≠ APPROVAL
    CERTIFICATION ≠ CAPABILITY GRANT

    CertificationGeneration = H(
        manifest_generation,
        capability_registry_generation,
        authority_policy_generation,
        executor_binding_generation,
        evidence_contract_generation)

Determinism contract: equivalent security state produces the identical
generation on different machines. No timestamps, filesystem paths, hostnames,
PIDs, random UUIDs, or worktree state participate in the digest.

Canonicalize first, hash second (W4-4 lesson): the payload has explicit keys
and stable serialization via ``canonical_hash`` over a canonical dict.
Security logic consumes structured objects, never presentation text.

Dependency generations must come from TRUSTED providers — typed objects
produced by the certified loaders (RegistryView, ExecutorBindingRegistry,
AgentManifest, DelegationAuthority) or canonical adapters over existing
authority/evidence contract state. Arbitrary caller strings are refused at
the grammar gate; any unresolvable dependency fails closed
(CERTIFICATION_GENERATION_UNAVAILABLE) — no best-effort hash.

Dependency change semantics:

    DEPENDENCY CHANGE  =  RECERTIFICATION REQUIRED  (= STALE_DEPENDENCY)
    DEPENDENCY CHANGE  ≠  CERTIFICATION FAILURE
    STALE_DEPENDENCY   ≠  REVOKED  (revocation is an explicit governance act)

Historical receipts are never mutated or deleted because dependencies move.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from agent_runtime.canonical import canonical_hash

__all__ = [
    "CertificationGenerationError",
    "CertificationState",
    "DependencyGenerations",
    "authority_policy_generation",
    "capability_registry_generation",
    "certification_generation",
    "classify_certification_state",
    "compute_dependency_generations",
    "evidence_contract_generation",
    "executor_binding_generation",
    "manifest_generation",
    "validate_certification_generation",
]

# Adapter contract versions (W4-6's OWN identity). Bump when an adapter's
# extraction logic changes semantics — that must invalidate certifications too.
ADAPTER_VERSION = "w46-1"

_DEP_KEYS = (
    "manifest_generation",
    "capability_registry_generation",
    "authority_policy_generation",
    "executor_binding_generation",
    "evidence_contract_generation",
)


class CertificationGenerationError(Exception):
    """Fail-closed certification-generation computation or validation."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _require_generation_string(value: Any, name: str) -> str:
    """Grammar gate for a single generation string (fail-closed)."""
    if value is None:
        raise CertificationGenerationError(
            "MISSING_DEPENDENCY_GENERATION", f"{name} not provided"
        )
    if not isinstance(value, str):
        raise CertificationGenerationError(
            "INVALID_DEPENDENCY_GENERATION",
            f"{name} must be a canonical generation string, got {type(value).__name__}",
        )
    v = value.strip()
    if not v:
        raise CertificationGenerationError(
            "MISSING_DEPENDENCY_GENERATION", f"{name} is empty"
        )
    if len(v) > 256:
        raise CertificationGenerationError(
            "INVALID_DEPENDENCY_GENERATION", f"{name} exceeds canonical length"
        )
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_ ")
    if not set(v) <= allowed:
        raise CertificationGenerationError(
            "INVALID_DEPENDENCY_GENERATION",
            f"{name} contains non-canonical characters",
        )
    return v


@dataclass(frozen=True)
class DependencyGenerations:
    """The five trusted dependency identities certified together.

    Construct through ``compute_dependency_generations`` (trusted providers)
    or from a previously certified, hash-bound record. Raw arbitrary strings
    are grammar-checked here and provenance-checked in
    ``validate_certification_generation`` when matched against live providers.
    """

    manifest_generation: str
    capability_registry_generation: str
    authority_policy_generation: str
    executor_binding_generation: str
    evidence_contract_generation: str

    def canonical_payload(self) -> dict[str, str]:
        """Explicit-key canonical representation (canonicalize FIRST)."""
        return {
            "authority_policy_generation": self.authority_policy_generation,
            "capability_registry_generation": self.capability_registry_generation,
            "evidence_contract_generation": self.evidence_contract_generation,
            "executor_binding_generation": self.executor_binding_generation,
            "manifest_generation": self.manifest_generation,
        }


def certification_generation(deps: DependencyGenerations) -> str:
    """Deterministic digest over the canonical dependency payload.

    Order-independent (canonical_hash sorts keys), environment-free. No
    timestamps, paths, hostnames, PIDs, random UUIDs, or worktree state.
    Equivalent dependency state on different machines yields the identical
    value.
    """
    payload = {
        **deps.canonical_payload(),
        "certification_generation_spec": ADAPTER_VERSION,
    }
    return "certgen-" + canonical_hash(payload)[:32]


@dataclass(frozen=True)
class CertificationState:
    """A dependency-bound certification record: identity + dependency set.

    Immutable data. Never an authority token.
    """

    component_id: str
    dependencies: DependencyGenerations
    certification_generation: str


def compute_dependency_generations(
    *,
    manifest: Any = None,
    registry_view: Any = None,
    delegation_authority: Any = None,
    binding_registry: Any = None,
) -> DependencyGenerations:
    """Build the dependency set from TRUSTED providers only (fail-closed).

    Every dependency must resolve from its certified canonical provider:
      manifest_generation        <- validated AgentManifest (W3/W4)
      capability_registry_generation <- RegistryView (W4-2 fail-closed loader)
      authority_policy_generation    <- DelegationAuthority structural snapshot
      executor_binding_generation    <- ExecutorBindingRegistry (W4-5)
      evidence_contract_generation   <- structural shape of the receipt contracts
    """
    if manifest is None:
        raise CertificationGenerationError(
            "MISSING_DEPENDENCY_GENERATION", "manifest not provided"
        )
    if registry_view is None:
        raise CertificationGenerationError(
            "MISSING_DEPENDENCY_GENERATION", "registry_view not provided"
        )
    if delegation_authority is None:
        raise CertificationGenerationError(
            "MISSING_DEPENDENCY_GENERATION", "delegation_authority not provided"
        )
    if binding_registry is None:
        raise CertificationGenerationError(
            "MISSING_DEPENDENCY_GENERATION", "binding_registry not provided"
        )
    return DependencyGenerations(
        manifest_generation=manifest_generation(manifest),
        capability_registry_generation=capability_registry_generation(registry_view),
        authority_policy_generation=authority_policy_generation(delegation_authority),
        executor_binding_generation=executor_binding_generation(binding_registry),
        evidence_contract_generation=evidence_contract_generation(),
    )


def validate_certification_generation(
    recorded: CertificationState,
    *,
    current: DependencyGenerations,
) -> str:
    """Compare a recorded certification against the CURRENT dependency state.

    Returns the classification; never mutates the recorded receipt.

      CURRENT           — recorded generation == recomputed generation
      STALE_DEPENDENCY  — recorded generation valid-shaped but dependencies moved
      UNKNOWN_CERTIFICATION_GENERATION — recorded hash not derivable from its
                          own recorded dependencies (tampered/forged record)
    """
    _validate_recorded_integrity(recorded)
    live = certification_generation(current)
    if recorded.certification_generation == live:
        return "CURRENT"
    return "STALE_DEPENDENCY"


def _validate_recorded_integrity(recorded: CertificationState) -> None:
    """The recorded generation must be exactly derivable from its OWN
    recorded dependencies. Otherwise the record is forged/tampered
    (UNKNOWN_CERTIFICATION_GENERATION) — never silently accepted."""
    expected = certification_generation(recorded.dependencies)
    if recorded.certification_generation != expected:
        raise CertificationGenerationError(
            "UNKNOWN_CERTIFICATION_GENERATION",
            f"recorded generation {recorded.certification_generation!r} is not "
            f"derivable from the recorded dependency set (expected {expected!r})",
        )


def classify_certification_state(
    recorded: CertificationState,
    *,
    current: DependencyGenerations,
) -> str:
    """Full lifecycle classification (dependency view only).

    Dependency semantics ONLY — SUPERSEDED and REVOKED are explicit
    governance/lifecycle acts that this module never infers:

      CURRENT                     — dependencies unchanged
      STALE_DEPENDENCY            — dependencies moved; recertification required
      UNKNOWN_CERTIFICATION_GENERATION — raised (forged/tampered record)
    """
    return validate_certification_generation(recorded, current=current)


# ---- trusted providers -----------------------------------------------------

def manifest_generation(manifest: Any) -> str:
    """From a TRUSTED AgentManifest: manifest_hash (canonical hash over all
    authority-relevant semantics) + adapter version."""
    from agent_runtime.manifest import AgentManifest, manifest_hash

    if not isinstance(manifest, AgentManifest):
        raise CertificationGenerationError(
            "UNTRUSTED_DEPENDENCY_GENERATION",
            f"manifest_generation requires a validated AgentManifest, got {type(manifest).__name__}",
        )
    return f"mgen-{ADAPTER_VERSION}-{manifest_hash(manifest)[:24]}"


def capability_registry_generation(registry_view: Any) -> str:
    """From a TRUSTED RegistryView (W4-2 fail-closed loader)."""
    from agent_runtime.capability_resolver import RegistryView

    if not isinstance(registry_view, RegistryView):
        raise CertificationGenerationError(
            "UNTRUSTED_DEPENDENCY_GENERATION",
            "capability_registry_generation requires a RegistryView from the "
            "fail-closed loader",
        )
    _require_generation_string(registry_view.generation_id, "capability_registry_generation")
    return registry_view.generation_id


def authority_policy_generation(delegation_authority: Any) -> str:
    """Smallest deterministic adapter over the EXISTING canonical authority
    state (DelegationAuthority). No second policy registry; W4-6 OBSERVES
    authority-policy identity, it does not own authority policy.

    Identity = adapter version + structural policy constants + trusted-root
    set + delegatable map (order-independent). Granting/revoking delegatable
    authority changes the generation → prior certifications STALE_DEPENDENCY.
    """
    from agent_runtime.delegation import GOVERNANCE_ROOT_ACTOR, DelegationAuthority

    if not isinstance(delegation_authority, DelegationAuthority):
        raise CertificationGenerationError(
            "UNTRUSTED_DEPENDENCY_GENERATION",
            f"authority_policy_generation requires a DelegationAuthority, got {type(delegation_authority).__name__}",
        )
    snapshot = {
        "adapter": ADAPTER_VERSION,
        "governance_root_actor": GOVERNANCE_ROOT_ACTOR,
        "trusted_roots": sorted(delegation_authority._trusted_roots),
        "max_provenance_depth": 16,
        "delegatable": {
            agent: sorted(caps)
            for agent, caps in delegation_authority._delegatable.items()
        },
    }
    blob = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    return "agen-" + canonical_hash(json.loads(blob))[:24]


def executor_binding_generation(binding_registry: Any) -> str:
    """From a TRUSTED ExecutorBindingRegistry (W4-5)."""
    from agent_runtime.executor_binding import ExecutorBindingRegistry

    if not isinstance(binding_registry, ExecutorBindingRegistry):
        raise CertificationGenerationError(
            "UNTRUSTED_DEPENDENCY_GENERATION",
            f"executor_binding_generation requires an ExecutorBindingRegistry, got {type(binding_registry).__name__}",
        )
    return binding_registry.executor_binding_generation


def evidence_contract_generation() -> str:
    """Deterministic identity of the CURRENT receipt/evidence hash contracts
    (not the future Evidence Ledger).

    Derived from the structural field sets of both contracts: the Wave-3
    AgentRuntimeReceipt and the mission-wiring MissionReceipt hash payload
    keys. A material schema change changes the generation → prior
    certifications STALE_DEPENDENCY. Pure structural reflection; no I/O.
    """
    from agent_runtime.receipts import AgentRuntimeReceipt
    from mission_wiring.receipt import MissionReceipt

    receipt_fields = sorted(AgentRuntimeReceipt.model_fields)
    mission_fields = sorted(MissionReceipt.__dataclass_fields__)  # dataclass fields
    payload = {
        "adapter": ADAPTER_VERSION,
        "agent_runtime_receipt_fields": receipt_fields,
        "mission_receipt_fields": mission_fields,
    }
    return "egen-" + canonical_hash(payload)[:24]

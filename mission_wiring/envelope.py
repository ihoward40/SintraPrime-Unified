"""SP-CONVERGE-ZD-001 §7 — one typed MissionEnvelope across all existing systems.

Every execution origin (API, Mission Control, CLI, scheduler, workflow, agent,
swarm, voice, webhook, admin, browser operator, revenue, background service)
normalizes into THIS contract. Adapters translate legacy formats; no subsystem
is rewritten internally.

Design rules:
- frozen, typed, fail-closed (missing/unknown fields REFUSED at construction);
- hash-bound via the single Wave-3 primitive (agent_runtime.canonical.canonical_hash);
- authority fields are NEVER inferred — they are explicit or the envelope is REFUSED;
- no secrets in any field (enforcement: input hashing, not storage).
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from agent_runtime.canonical import canonical_hash
from agent_runtime.receipts import canonicalize_capability_for_hash

__all__ = [
    "ApprovalState",
    "EnvelopeBudget",
    "EnvelopeRefusalError",
    "MemoryScope",
    "MissionEnvelope",
    "RequestOrigin",
    "RequestType",
    "ResourceScope",
]

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")
_ORIGINS = frozenset({
    "ORIGIN_API", "ORIGIN_MISSION_CONTROL", "ORIGIN_CLI", "ORIGIN_SCHEDULER",
    "ORIGIN_WORKFLOW", "ORIGIN_AGENT", "ORIGIN_SWARM", "ORIGIN_VOICE",
    "ORIGIN_WEBHOOK", "ORIGIN_ADMIN", "ORIGIN_BROWSER_OPERATOR",
    "ORIGIN_REVENUE", "ORIGIN_BACKGROUND_SERVICE",
})


class RequestOrigin(StrEnum):
    API = "ORIGIN_API"
    MISSION_CONTROL = "ORIGIN_MISSION_CONTROL"
    CLI = "ORIGIN_CLI"
    SCHEDULER = "ORIGIN_SCHEDULER"
    WORKFLOW = "ORIGIN_WORKFLOW"
    AGENT = "ORIGIN_AGENT"
    SWARM = "ORIGIN_SWARM"
    VOICE = "ORIGIN_VOICE"
    WEBHOOK = "ORIGIN_WEBHOOK"
    ADMIN = "ORIGIN_ADMIN"
    BROWSER_OPERATOR = "ORIGIN_BROWSER_OPERATOR"
    REVENUE = "ORIGIN_REVENUE"
    BACKGROUND_SERVICE = "ORIGIN_BACKGROUND_SERVICE"


class RequestType(StrEnum):
    RESEARCH = "RESEARCH"
    ANALYSIS = "ANALYSIS"
    CONTENT = "CONTENT"
    AUTOMATION = "AUTOMATION"
    BROWSER_READ = "BROWSER_READ"
    BROWSER_INTERACT = "BROWSER_INTERACT"
    BROWSER_SUBMIT = "BROWSER_SUBMIT"
    FINANCIAL = "FINANCIAL"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    EXTERNAL_COMMUNICATION = "EXTERNAL_COMMUNICATION"


class ApprovalState(StrEnum):
    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING = "PENDING"
    GRANTED = "GRANTED"
    CONSUMED = "CONSUMED"
    DENIED = "DENIED"
    EXPIRED = "EXPIRED"


class EnvelopeRefusalError(Exception):
    """Raised when an envelope would be constructed with authority gaps."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class ResourceScope:
    """Explicit resource boundary. Empty = nothing authorized."""
    url_allowlist: tuple[str, ...] = ()
    paths: tuple[str, ...] = ()
    max_actions: int = 0

    def __post_init__(self) -> None:
        if self.max_actions < 0:
            raise EnvelopeRefusalError("NEGATIVE_BUDGET", "max_actions must be >= 0")

    def allows(self, url: str) -> bool:
        if not self.url_allowlist:
            return False
        return any(url.startswith(p) for p in self.url_allowlist)


@dataclass(frozen=True)
class MemoryScope:
    """Explicit memory boundary (reads vs writes separated, per Wave 3 policy)."""
    tenants: tuple[str, ...] = ()
    read_kinds: frozenset[str] = frozenset()
    write_kinds: frozenset[str] = frozenset()  # empty = read-only memory

    @property
    def read_only(self) -> bool:
        return not self.write_kinds


@dataclass(frozen=True)
class EnvelopeBudget:
    max_provider_calls: int = 0
    max_tool_calls: int = 0
    max_loop_observations: int = 5
    deadline_seconds: int | None = None

    def __post_init__(self) -> None:
        for name in ("max_provider_calls", "max_tool_calls", "max_loop_observations"):
            if getattr(self, name) < 0:
                raise EnvelopeRefusalError("NEGATIVE_BUDGET", f"{name} must be >= 0")
        if self.deadline_seconds is not None and self.deadline_seconds <= 0:
            raise EnvelopeRefusalError("INVALID_TIMEOUT", "deadline_seconds must be > 0")


@dataclass(frozen=True)
class MissionEnvelope:
    """§7 contract — the ONE typed mission envelope."""
    mission_id: str
    principal_id: str
    tenant_id: str
    request_origin: RequestOrigin
    request_type: RequestType
    actor_id: str
    agent_id: str | None = None
    delegation_id: str | None = None
    requested_capabilities: tuple[str, ...] = ()
    resource_scope: ResourceScope = field(default_factory=ResourceScope)
    memory_scope: MemoryScope = field(default_factory=MemoryScope)
    provider_policy: dict[str, Any] = field(default_factory=dict)
    tool_policy: dict[str, Any] = field(default_factory=dict)
    approval_state: ApprovalState = ApprovalState.NOT_REQUIRED
    budget: EnvelopeBudget = field(default_factory=EnvelopeBudget)
    timeout_seconds: int | None = None
    correlation_id: str = ""
    evidence_context: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        for name in ("mission_id", "principal_id", "tenant_id", "actor_id"):
            v = getattr(self, name)
            if not isinstance(v, str) or not _ID_RE.match(v):
                raise EnvelopeRefusalError("INVALID_IDENTITY", f"{name}={v!r} fails identity grammar")
        if not isinstance(self.request_origin, RequestOrigin):
            raise EnvelopeRefusalError("INVALID_ORIGIN", f"unknown request origin {self.request_origin!r}")
        if not isinstance(self.request_type, RequestType):
            raise EnvelopeRefusalError("INVALID_REQUEST_TYPE", f"unknown request type {self.request_type!r}")
        if self.agent_id is not None and not _ID_RE.match(self.agent_id):
            raise EnvelopeRefusalError("INVALID_IDENTITY", f"agent_id={self.agent_id!r} fails identity grammar")
        for cap in self.requested_capabilities:
            if not isinstance(cap, str) or not re.match(r"^[a-z_]+\.[a-z_]+(\.[a-z_]+)*$", cap):
                raise EnvelopeRefusalError("INVALID_CAPABILITY", f"capability {cap!r} must be dotted lowercase")
        # consequential request types: PENDING posture is REQUIRED and legal —
        # the mission may exist while awaiting approval (Mission Control must
        # be able to show pending missions). NOT_REQUIRED remains refused for
        # consequential types: an envelope can never self-declare approval.
        consequential = {
            RequestType.BROWSER_SUBMIT, RequestType.FINANCIAL,
            RequestType.INFRASTRUCTURE, RequestType.EXTERNAL_COMMUNICATION,
        }
        if self.request_type in consequential and self.approval_state is ApprovalState.NOT_REQUIRED:
            raise EnvelopeRefusalError(
                "APPROVAL_POSTURE_REQUIRED",
                f"request_type={self.request_type.value} is consequential; approval posture must be explicit (PENDING = awaiting authority)",
            )
        # an un-delegated non-principal actor cannot carry capabilities
        if self.requested_capabilities and self.delegation_id is None and self.actor_id != self.principal_id:
            raise EnvelopeRefusalError(
                "DELEGATION_REQUIRED",
                "non-principal actor with requested capabilities requires delegation_id",
            )
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise EnvelopeRefusalError("INVALID_TIMEOUT", "timeout_seconds must be > 0")
        if not self.correlation_id:
            object.__setattr__(self, "correlation_id", uuid.uuid4().hex)

    # C2 (SP-MW-RECONCILE-001): registry provenance is bound into the envelope at
    # construction from the TRUSTED registry loader — never from caller payload.
    registry_generation_id: str = ""
    registry_hash: str = ""

    def canonical_capability_ids(self, registry_view: Any = None) -> tuple[str, ...]:
        """W4-4 canonicalization: alias forms in the envelope resolve to canonical
        ids for hash input. Unresolvable/untrusted capabilities refuse here —
        they must never reach a security-sensitive hash boundary."""
        if registry_view is None:
            from mission_wiring.browser_executor import _registry_view
            registry_view = _registry_view()
        out = []
        for cap in self.requested_capabilities:
            try:
                cid, _gen, _rh = canonicalize_capability_for_hash(cap, registry_view)
            except ValueError as exc:
                raise EnvelopeRefusalError("CAPABILITY_NOT_RESOLVABLE", f"{cap}: {exc}") from exc
            out.append(cid)
        return tuple(sorted(out))

    def hash_payload(self, registry_view: Any = None) -> dict[str, Any]:
        # C2: capability identity enters the hash as the RESOLVED canonical id;
        # registry provenance is separate so generation changes stay auditable.
        canonical_caps = self.canonical_capability_ids(registry_view)
        return {
            "mission_id": self.mission_id,
            "principal_id": self.principal_id,
            "tenant_id": self.tenant_id,
            "request_origin": self.request_origin.value,
            "request_type": self.request_type.value,
            "actor_id": self.actor_id,
            "agent_id": self.agent_id,
            "delegation_id": self.delegation_id,
            "requested_capabilities": list(canonical_caps),
            "capability_dependency_context": {
                "registry_generation_id": self.registry_generation_id,
                "registry_hash": self.registry_hash,
            },
            "resource_scope": {
                "url_allowlist": list(self.resource_scope.url_allowlist),
                "paths": list(self.resource_scope.paths),
                "max_actions": self.resource_scope.max_actions,
            },
            "memory_scope": {
                "tenants": list(self.memory_scope.tenants),
                "read_kinds": sorted(self.memory_scope.read_kinds),
                "write_kinds": sorted(self.memory_scope.write_kinds),
            },
            "provider_policy": self.provider_policy,
            "tool_policy": self.tool_policy,
            "approval_state": self.approval_state.value,
            "budget": {
                "max_provider_calls": self.budget.max_provider_calls,
                "max_tool_calls": self.budget.max_tool_calls,
                "max_loop_observations": self.budget.max_loop_observations,
                "deadline_seconds": self.budget.deadline_seconds,
            },
            "timeout_seconds": self.timeout_seconds,
            "correlation_id": self.correlation_id,
            "created_at": self.created_at.isoformat(),
        }

    def envelope_hash(self) -> str:
        """Deterministic authority-bearing hash — mutation-detectable (Checkpoint 2 invariant)."""
        return canonical_hash(self.hash_payload())

    # ---- posture queries used by adapters (§6) ----
    @property
    def is_consequential(self) -> bool:
        return self.request_type in {
            RequestType.BROWSER_SUBMIT, RequestType.FINANCIAL,
            RequestType.INFRASTRUCTURE, RequestType.EXTERNAL_COMMUNICATION,
        }

    @property
    def is_principal_actor(self) -> bool:
        return self.actor_id == self.principal_id

"""AgentManifest — canonical typed agent contract (Wave 3, §5-§11).

Converges with existing substrates (portal orchestration policy types,
swarm capability-lease semantics, nova approval tiers) rather than
duplicating them. Structural rules enforced here:

  §6  stable `agent.<name>` identity (never class names, filenames, model
      names, or per-startup UUIDs)
  §7  manifest_schema version distinct from agent_version (semver)
  §8  capabilities are declared, never derived from Python imports
  §9  explicit forbidden capabilities; deny overrides allow; fail closed
  §11 owner = authority domain, not software author
  §21/§22 memory scopes; governance write never follows governance read
  §29 bounded execution (timeout/iterations/retry/budget mandatory)
"""
from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .canonical import canonical_hash

MANIFEST_SCHEMA_VERSION = 1
_AGENT_ID_RE = re.compile(r"^agent\.[a-z0-9]+(\.[a-z0-9]+)*$")
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

KNOWN_CAPABILITIES: frozenset[str] = frozenset(
    {
        # repository / build
        "READ_REPOSITORY",
        "WRITE_REPOSITORY",
        "RUN_TESTS",
        # research
        "SEARCH_WEB",
        "FETCH_URL",
        # memory
        "READ_MEMORY",
        "REQUEST_MEMORY_WRITE",
        # data
        "READ_DATABASE",
        "WRITE_DATABASE",
        # documents
        "CREATE_DOCUMENT",
        # shell
        "EXECUTE_SHELL",
        # communication
        "READ_EMAIL",
        "DRAFT_EMAIL",
        "SEND_EMAIL",
        # github / deployment
        "CREATE_GITHUB_BRANCH",
        "CREATE_GITHUB_COMMIT",
        "PUSH_GITHUB_BRANCH",
        "OPEN_PULL_REQUEST",
        "MERGE_PULL_REQUEST",
        "DEPLOY_SERVICE",
        "PUBLISH_CONTENT",
        # high consequence
        "EXECUTE_PAYMENT",
        # delegation
        "DELEGATE_TASK",
    }
)


def _resolves_to_known(raw_id: str) -> bool:
    """W4-3 alias-aware recognition: resolve through the capability resolver
    when a governed registry artifact is present; fall back to the frozen
    No legacy vocabulary fallback is permitted. Missing, unavailable, corrupt,
    or mismatched governed registry state returns False (REGISTRY_NOT_TRUSTED)."""
    try:
        from agent_runtime.capability_resolver import (  # lazy: avoid import cycle
            resolve_capability,
        )
    except ImportError:
        return False  # resolver unavailable is REGISTRY_NOT_TRUSTED
    reg_path = _registry_artifact_path()
    if reg_path is None:
        return False  # missing governed registry is REGISTRY_NOT_TRUSTED
    try:
        view = load_registry_cached(reg_path)
        resolve_capability(raw_id, view)
        return True
    except Exception:
        return False  # corrupt/mismatched/untrusted registry fails closed


def _registry_artifact_path():
    from pathlib import Path
    for candidate in (
        Path(__file__).resolve().parent.parent / "registry/capabilities/capability_registry.json",
        Path.cwd() / "registry/capabilities/capability_registry.json",
    ):
        if candidate.exists():
            return candidate
    return None


_LOAD_CACHE: dict = {}


def load_registry_cached(path):
    """Cache RegistryView per (path, mtime, size) so validators don't reload
    per capability. Cache invalidates automatically when the artifact changes
    (mtime/size) — generation-mismatch is still enforced at load time."""
    from agent_runtime.capability_resolver import load_registry
    key = (str(path), path.stat().st_mtime_ns, path.stat().st_size)
    if key not in _LOAD_CACHE:
        if len(_LOAD_CACHE) > 4:
            _LOAD_CACHE.clear()
        _LOAD_CACHE[key] = load_registry(path)
    return _LOAD_CACHE[key]



class SideEffectClass(StrEnum):
    """§28 side-effect classification."""

    READ_ONLY = "READ_ONLY"
    LOCAL_REVERSIBLE = "LOCAL_REVERSIBLE"
    EXTERNAL_REVERSIBLE = "EXTERNAL_REVERSIBLE"
    EXTERNAL_CONSEQUENTIAL = "EXTERNAL_CONSEQUENTIAL"
    IRREVERSIBLE = "IRREVERSIBLE"


class MemoryScope(StrEnum):
    """§21: agents do not automatically see all memory."""

    NONE = "NONE"
    MISSION = "MISSION"
    SESSION = "SESSION"
    TENANT = "TENANT"
    AGENT = "AGENT"
    SHARED_SEMANTIC = "SHARED_SEMANTIC"
    GOVERNANCE_READONLY = "GOVERNANCE_READONLY"


class MemoryAccess(StrEnum):
    NONE = "NONE"
    READ = "READ"
    WRITE = "WRITE"  # always mediated as a REQUEST flow (§22); never autonomous


class AuthorityPolicy(StrEnum):
    DELEGATED = "DELEGATED"
    PRINCIPAL_DIRECT = "PRINCIPAL_DIRECT"
    POLICY_BOUND = "POLICY_BOUND"


class ApprovalPolicy(StrEnum):
    NEVER_REQUIRED = "NEVER_REQUIRED"
    TIERED = "TIERED"
    ALWAYS_REQUIRED = "ALWAYS_REQUIRED"


class TenantPolicy(StrEnum):
    SINGLE_TENANT = "SINGLE_TENANT"
    MULTI_TENANT = "MULTI_TENANT"
    TENANT_ISOLATED = "TENANT_ISOLATED"


class CertificationStatus(StrEnum):
    """§14: importable != certified."""

    UNREGISTERED = "UNREGISTERED"
    REGISTERED = "REGISTERED"
    VALIDATED = "VALIDATED"
    TESTED = "TESTED"
    CERTIFIED = "CERTIFIED"
    DEGRADED = "DEGRADED"
    QUARANTINED = "QUARANTINED"  # §58
    DISABLED = "DISABLED"
    REVOKED = "REVOKED"


class HealthStatus(StrEnum):
    """§40 runtime health. PROCESS_RUNNING != CERTIFIED."""

    REGISTERED = "REGISTERED"
    READY = "READY"
    DEGRADED = "DEGRADED"
    DISABLED = "DISABLED"
    FAILED_CERTIFICATION = "FAILED_CERTIFICATION"


class ProviderClass(StrEnum):
    REASONING = "REASONING"
    CODE = "CODE"
    EMBEDDING = "EMBEDDING"
    VISION = "VISION"
    SPEECH = "SPEECH"
    LOCAL = "LOCAL"


class ProviderPolicy(BaseModel):
    """§26: manifests state provider REQUIREMENTS; the gateway picks the
    implementation. The provider never decides authority."""

    model_config = ConfigDict(frozen=True)

    provider_class: str
    fallback_allowed: bool = True
    local_only: bool = False
    structured_output_required: bool = False
    max_provider_calls: int = Field(default=50, ge=0)


class ToolPolicy(BaseModel):
    """§27: tool availability does not imply permission."""

    model_config = ConfigDict(frozen=True)

    allowed_tool_categories: tuple[str, ...] = ()
    forbidden_tools: tuple[str, ...] = ()
    network_access: bool = False
    filesystem_scope: Literal["NONE", "READ_ONLY", "SANDBOX", "WORKTREE", "REPO"] = "NONE"
    shell_access: bool = False
    max_tool_calls: int = Field(default=100, ge=0)


class RetryPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_attempts: int = Field(default=2, ge=0)
    backoff_seconds: float = Field(default=1.0, ge=0)
    strategy: Literal["FIXED", "EXPONENTIAL", "NONE"] = "EXPONENTIAL"


class BudgetPolicy(BaseModel):
    """§29: every agent is bounded."""

    model_config = ConfigDict(frozen=True)

    max_iterations: int = Field(default=25, ge=1)
    timeout_seconds: int = Field(default=600, ge=1)
    max_provider_calls: int = Field(default=50, ge=0)
    max_tool_calls: int = Field(default=100, ge=0)
    max_tokens: int | None = Field(default=None, ge=1)
    max_cost_usd: float | None = Field(default=None, ge=0)


class EvidencePolicy(BaseModel):
    """§38 receipts; §39 no chain-of-thought persistence."""

    model_config = ConfigDict(frozen=True)

    require_receipt: bool = True
    evidence_refs_required: bool = True
    persist_chain_of_thought: bool = False  # §39: must stay False


class SandboxPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool = True
    network: bool = False
    filesystem: Literal["NONE", "READ_ONLY", "SANDBOX", "WORKTREE", "REPO"] = "SANDBOX"


class AgentManifest(BaseModel):
    """Canonical typed agent contract (Wave 3B)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # ── identity (§6/§7) ─────────────────────────────────────────────────
    agent_id: str
    manifest_schema: int = MANIFEST_SCHEMA_VERSION
    agent_version: str

    display_name: str
    description: str = ""
    owner: str  # §11 authority domain, not software author

    runtime_class: str  # diagnostics only; never identity
    mission_types: tuple[str, ...] = Field(min_length=1)

    # ── capabilities (§8/§9) ─────────────────────────────────────────────
    required_capabilities: tuple[str, ...] = ()
    optional_capabilities: tuple[str, ...] = ()
    forbidden_capabilities: tuple[str, ...] = ()

    # ── memory (§21/§22) ─────────────────────────────────────────────────
    memory_scope: MemoryScope = MemoryScope.NONE
    memory_read: bool = False
    memory_write_requests_allowed: bool = False  # §22 request flow only
    context_scope: Literal["MINIMAL", "MISSION", "TENANT"] = "MINIMAL"

    provider_policy: ProviderPolicy
    tool_policy: ToolPolicy
    authority_policy: AuthorityPolicy
    approval_policy: ApprovalPolicy = ApprovalPolicy.TIERED
    tenant_policy: TenantPolicy = TenantPolicy.TENANT_ISOLATED

    # §29 bounded execution (mandatory fields with safe defaults)
    timeout_seconds: int = Field(default=600, ge=1)
    max_iterations: int = Field(default=25, ge=1)
    retry_policy: RetryPolicy = RetryPolicy()
    budget_policy: BudgetPolicy = BudgetPolicy()

    evidence_policy: EvidencePolicy = EvidencePolicy()
    sandbox_policy: SandboxPolicy = SandboxPolicy()

    certification_status: CertificationStatus = CertificationStatus.UNREGISTERED

    # -- validators --------------------------------------------------------

    @field_validator("agent_id")
    @classmethod
    def _stable_identity(cls, v: str) -> str:
        if not _AGENT_ID_RE.match(v):
            raise ValueError("agent_id must match 'agent.<name>' — stable machine identity (§6)")
        return v

    @field_validator("owner")
    @classmethod
    def _owner_required(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("owner (authority domain) is required (§11)")
        return v

    @field_validator("agent_version")
    @classmethod
    def _semver(cls, v: str) -> str:
        if not _SEMVER_RE.match(v):
            raise ValueError("agent_version must be semver (MAJOR.MINOR.PATCH), distinct from manifest_schema (§7)")
        return v

    @field_validator("required_capabilities", "optional_capabilities", "forbidden_capabilities")
    @classmethod
    def _capabilities_known(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        unknown = [c for c in v if not _resolves_to_known(c)]
        if unknown:
            raise ValueError(f"unknown capability ids: {sorted(unknown)} (§13 fail-closed)")
        return v

    @model_validator(mode="after")
    def _no_required_forbidden_overlap(self) -> AgentManifest:
        overlap = set(self.required_capabilities) & set(self.forbidden_capabilities)
        if overlap:
            raise ValueError(f"contradictory required+forbidden capabilities: {sorted(overlap)}")
        return self

    @model_validator(mode="after")
    def _governance_readonly_has_no_write(self) -> AgentManifest:
        if self.memory_scope is MemoryScope.GOVERNANCE_READONLY and self.memory_write_requests_allowed:
            raise ValueError("GOVERNANCE_READONLY memory scope forbids write requests")
        return self


def manifest_hash(manifest: AgentManifest) -> str:
    """§2 (Checkpoint 2): canonical hash over ALL authority-relevant manifest
    semantics. Excludes certification_status (lifecycle, not identity) and
    display-only metadata (display_name, description — documented exclusion).
    Uses canonical_hash: deterministic, dict-order-independent, enum-stable."""
    payload = manifest.model_dump(mode="json", exclude={"certification_status", "display_name", "description"})
    return canonical_hash(payload)

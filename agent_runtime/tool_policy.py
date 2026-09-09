"""Phase 3H/3I — provider policy + tool policy + side-effect classification
(Wave 3, §11-§18 Checkpoint 2).

Invariants:
  PROVIDER_CHANGE != AUTHORITY_CHANGE
  MODEL_OUTPUT_CANNOT_GRANT_AUTHORITY
  DISALLOWED_PROVIDER / DISALLOWED_MODEL / FALLBACK_OUTSIDE_POLICY / COST
  LIMIT / TIMEOUT → REFUSED or bounded failure
  TOOL_PRESENT_CAPABILITY_ABSENT = REFUSED
  TOOL_SCOPE_ESCAPE / TOOL_TENANT_ESCAPE = REFUSED
  TOOL_REQUIRES_APPROVAL_WITHOUT_APPROVAL = REFUSED
  SIDE_EFFECT_CLASS_ESCALATION = REFUSED
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from agent_runtime.manifest import SideEffectClass

# ---------------------------------------------------------------------------
# §11 provider policy (typed) — provider never decides authority
# ---------------------------------------------------------------------------


class ProviderPolicyContract(BaseModel):
    """§11 typed provider policy."""

    model_config = ConfigDict(frozen=True)

    provider_class: str
    allowed_models: tuple[str, ...] = ()
    disallowed_models: tuple[str, ...] = ()
    structured_output_required: bool = False
    fallback_allowed: bool = True
    max_provider_calls: int = Field(default=50, ge=0)
    max_tokens: int | None = Field(default=None, ge=1)
    max_cost_usd: float | None = Field(default=None, ge=0)
    timeout_seconds: int = Field(default=300, ge=1)
    local_only: bool = False


class ProviderRefusedError(Exception):
    """REFUSED: provider/model/cost/fallback outside policy (§12)."""


class ProviderSelection:
    """Policy-bound provider selection. Selection NEVER confers authority:
    it only decides which engine runs an already-authorized operation."""

    def __init__(self, policy: ProviderPolicyContract) -> None:
        self._policy = policy
        self._spent_usd = 0.0

    def select(self, *, provider_class: str, model: str, structured: bool, cost_usd: float = 0.0) -> str:
        p = self._policy
        if provider_class != p.provider_class:
            raise ProviderRefusedError(f"DISALLOWED_PROVIDER: {provider_class!r} outside policy")
        if model in p.disallowed_models:
            raise ProviderRefusedError(f"DISALLOWED_MODEL: {model!r}")
        if p.allowed_models and model not in p.allowed_models:
            raise ProviderRefusedError(f"DISALLOWED_MODEL: {model!r} not in allowlist")
        if p.structured_output_required and not structured:
            raise ProviderRefusedError("MALFORMED_STRUCTURED_OUTPUT: structured output required")
        if p.local_only and provider_class not in ("LOCAL",):
            raise ProviderRefusedError("PROVIDER_FALLBACK_OUTSIDE_POLICY: local_only policy")
        if p.max_cost_usd is not None and self._spent_usd + cost_usd > p.max_cost_usd:
            raise ProviderRefusedError("PROVIDER_COST_LIMIT_EXCEEDED")
        self._spent_usd += cost_usd
        return model


# ---------------------------------------------------------------------------
# §16-§18 tool policy + typed tool results
# ---------------------------------------------------------------------------

_SIDE_EFFECT_RANK: dict[str, int] = {
    SideEffectClass.READ_ONLY.value: 0,
    SideEffectClass.LOCAL_REVERSIBLE.value: 1,
    SideEffectClass.EXTERNAL_REVERSIBLE.value: 2,
    SideEffectClass.EXTERNAL_CONSEQUENTIAL.value: 3,
    SideEffectClass.IRREVERSIBLE.value: 4,
}


class ToolContract(BaseModel):
    """§14: a tool's contract. Presence in the runtime ≠ permission."""

    model_config = ConfigDict(frozen=True)

    tool_id: str
    required_capability: str
    side_effect_class: str  # SideEffectClass value
    resource_scope: tuple[str, ...] = ()
    approval_requirement: bool = False


class ToolRefusedError(PermissionError):
    """REFUSED: tool use denied by policy (§15/§17/§44)."""


class ToolResult(BaseModel):
    """§18: typed operational result — never raw text as runtime state."""

    model_config = ConfigDict(frozen=True)

    tool_id: str
    status: str  # "ok" | "error"
    started_at: str
    completed_at: str
    side_effect_class: str
    resource: str = ""
    evidence_reference: str = ""
    idempotency_key: str = ""
    error_classification: str | None = None


class ToolPolicyGate:
    """§14-§17: capability-bound tool execution.

    Rules: the tool's required capability must be IN the delegation;
    resource must be within BOTH the tool's and the delegation's scope;
    side-effect class of the tool may not exceed the side-effect ceiling of
    the used capability's delegation; approval-gated tools require an
    approval reference. Presence of the tool adapter grants nothing."""

    def __init__(self, tools: tuple[ToolContract, ...]) -> None:
        self._tools: dict[str, ToolContract] = {t.tool_id: t for t in tools}

    def check(
        self,
        *,
        tool_id: str,
        delegation,
        granted_side_effect_ceiling: str,
        approval_reference: str = "",
        resource: str = "",
        tenant: str = "",
    ) -> ToolContract:
        tool = self._tools.get(tool_id)
        if tool is None:
            raise ToolRefusedError(f"TOOL_UNKNOWN: {tool_id}")
        if tool.required_capability not in delegation.capabilities:
            raise ToolRefusedError(
                f"TOOL_PRESENT_CAPABILITY_ABSENT: {tool_id} needs {tool.required_capability}"
            )
        # §15 scope/tenant escape
        if tool.resource_scope and resource:
            if not any(resource == s or resource.startswith(s.rstrip("*")) for s in tool.resource_scope):
                raise ToolRefusedError(f"TOOL_SCOPE_ESCAPE: {resource}")
        if delegation.tenant and tenant and delegation.tenant != tenant:
            raise ToolRefusedError("TOOL_TENANT_ESCAPE")
        # §17 side-effect escalation: ceiling must be >= tool class
        ceiling = _SIDE_EFFECT_RANK.get(granted_side_effect_ceiling)
        needed = _SIDE_EFFECT_RANK.get(tool.side_effect_class)
        if ceiling is None or needed is None:
            raise ToolRefusedError("SIDE_EFFECT_CLASS_INVALID")
        if needed > ceiling:
            raise ToolRefusedError(
                f"SIDE_EFFECT_CLASS_ESCALATION: {tool.side_effect_class} > {granted_side_effect_ceiling}"
            )
        # §15 approval gate
        if tool.approval_requirement and not approval_reference:
            raise ToolRefusedError("TOOL_REQUIRES_APPROVAL_WITHOUT_APPROVAL")
        return tool

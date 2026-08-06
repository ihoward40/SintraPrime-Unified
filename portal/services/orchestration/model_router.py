"""Policy-driven provider routing."""

from __future__ import annotations

from .budget_policy import check_budget
from .schemas import (
    BudgetUsageSnapshot,
    ClassificationResult,
    ProviderCapability,
    Role,
    RoutingDecisionSchema,
    TaskType,
)


def route_provider(
    *,
    role: Role,
    classification: ClassificationResult,
    budget: BudgetUsageSnapshot,
    providers: list[ProviderCapability],
    required_tools: list[str] | None = None,
    exclude_provider_ids: set[str] | None = None,
) -> RoutingDecisionSchema:
    """Choose a provider using declared capabilities and governance policy."""
    required_tools = required_tools or []
    exclude_provider_ids = exclude_provider_ids or set()
    candidates: list[tuple[ProviderCapability, float]] = []
    rejected: list[dict[str, str]] = []

    for provider in providers:
        rejection = _rejection_reason(provider, classification, budget, required_tools, exclude_provider_ids)
        if rejection:
            rejected.append({"provider_id": provider.provider_id, "reason": rejection})
            continue
        candidates.append((provider, _score_provider(provider, role, classification.task_type)))

    if not candidates:
        return RoutingDecisionSchema(
            candidate_providers=[],
            rejected_providers=rejected,
            selected_provider=None,
            selection_reason="No provider satisfied declared capability, sensitivity, budget, and governance policy.",
            policy_applied=_policy(role, classification, required_tools),
            estimated_cost=0.0,
        )

    selected, score = sorted(candidates, key=lambda item: (-item[1], item[0].provider_id))[0]
    return RoutingDecisionSchema(
        candidate_providers=[provider.provider_id for provider, _score in candidates],
        rejected_providers=rejected,
        selected_provider=selected.provider_id,
        selection_reason=f"Selected by task fit, role fit, sensitivity policy, and budget; score={score:.2f}.",
        policy_applied=_policy(role, classification, required_tools),
        estimated_cost=0.0,
    )


def _rejection_reason(
    provider: ProviderCapability,
    classification: ClassificationResult,
    budget: BudgetUsageSnapshot,
    required_tools: list[str],
    exclude_provider_ids: set[str],
) -> str | None:
    if provider.provider_id in exclude_provider_ids:
        return "excluded_for_independence"
    if not provider.enabled:
        return "provider_disabled"
    if provider.availability != "available":
        return "provider_unavailable"
    if classification.task_type not in provider.supported_task_types and TaskType.MIXED not in provider.supported_task_types:
        return "task_type_not_supported"
    if classification.sensitivity not in provider.allowed_sensitivity:
        return "sensitivity_not_allowed"
    missing_tools = [tool for tool in required_tools if tool not in provider.tool_support]
    if missing_tools:
        return f"missing_tools:{','.join(missing_tools)}"
    budget_check = check_budget(budget, provider_id=provider.provider_id, task_type=classification.task_type)
    if not budget_check.allowed:
        return budget_check.reason or "budget_rejected"
    if provider.data_policy.get("external") or provider.data_policy.get("paid"):
        return "external_or_paid_provider_blocked"
    return None


def _score_provider(provider: ProviderCapability, role: Role, task_type: TaskType) -> float:
    task_fit = 1.0 if task_type in provider.supported_task_types else 0.5
    role_fit = {
        Role.PLANNER: provider.reasoning_strength,
        Role.THINKER: provider.reasoning_strength,
        Role.RESEARCHER: provider.research_strength,
        Role.WORKER: max(provider.coding_strength, provider.reasoning_strength, provider.research_strength),
        Role.CHECKER: provider.verification_strength,
        Role.SECURITY_REVIEWER: max(provider.verification_strength, provider.coding_strength),
        Role.GOVERNANCE_REVIEWER: provider.verification_strength,
        Role.RECONCILER: provider.reasoning_strength,
        Role.PRINCIPAL: 0.0,
    }[role]
    latency_bonus = 0.1 if provider.latency_class == "fast" else 0.0
    history_bonus = float(provider.confidence_history.get(task_type.value, 0.0)) * 0.1
    return task_fit + role_fit + latency_bonus + history_bonus


def _policy(role: Role, classification: ClassificationResult, required_tools: list[str]) -> dict:
    return {
        "role": role.value,
        "task_type": classification.task_type.value,
        "sensitivity": classification.sensitivity.value,
        "required_tools": required_tools,
        "external_providers": "blocked",
        "paid_providers": "blocked",
        "benchmark_only_routing": "prohibited",
    }

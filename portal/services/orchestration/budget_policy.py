"""Budget limit enforcement for orchestration runs."""

from __future__ import annotations

from dataclasses import dataclass

from .schemas import BudgetLimits, BudgetUsageSnapshot, TaskType


@dataclass(frozen=True)
class BudgetCheck:
    allowed: bool
    reason: str | None = None


def initial_budget_usage(limits: BudgetLimits | None = None) -> BudgetUsageSnapshot:
    return BudgetUsageSnapshot(limits=limits or BudgetLimits())


def check_budget(
    usage: BudgetUsageSnapshot,
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
    provider_cost: float = 0.0,
    nodes: int = 0,
    retries: int = 0,
    provider_id: str | None = None,
    task_type: TaskType | None = None,
) -> BudgetCheck:
    limits = usage.limits
    checks = [
        (usage.input_tokens_used + input_tokens <= limits.maximum_input_tokens, "maximum_input_tokens"),
        (usage.output_tokens_used + output_tokens <= limits.maximum_output_tokens, "maximum_output_tokens"),
        (usage.provider_cost_used + provider_cost <= limits.maximum_provider_cost, "maximum_provider_cost"),
        (usage.nodes_used + nodes <= limits.maximum_nodes, "maximum_nodes"),
        (usage.retries_used + retries <= limits.maximum_retries, "maximum_retries"),
    ]
    if provider_id and limits.approved_providers and provider_id not in limits.approved_providers:
        return BudgetCheck(False, "provider_not_approved")
    if task_type and limits.approved_task_types and task_type not in limits.approved_task_types:
        return BudgetCheck(False, "task_type_not_approved")
    for allowed, reason in checks:
        if not allowed:
            return BudgetCheck(False, reason)
    return BudgetCheck(True)


def consume_budget(
    usage: BudgetUsageSnapshot,
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
    provider_cost: float = 0.0,
    nodes: int = 0,
    retries: int = 0,
) -> BudgetUsageSnapshot:
    check = check_budget(
        usage,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        provider_cost=provider_cost,
        nodes=nodes,
        retries=retries,
    )
    return usage.model_copy(
        update={
            "input_tokens_used": usage.input_tokens_used + input_tokens,
            "output_tokens_used": usage.output_tokens_used + output_tokens,
            "provider_cost_used": usage.provider_cost_used + provider_cost,
            "nodes_used": usage.nodes_used + nodes,
            "retries_used": usage.retries_used + retries,
            "hard_limit_reached": not check.allowed,
            "limit_reason": check.reason,
        }
    )

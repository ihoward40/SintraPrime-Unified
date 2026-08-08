"""Budget governor — hard-stop enforcement.

Every workflow receives budgets. The governor tracks consumption
and emits structured telemetry. Hard-stop when ceilings are hit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import BudgetSpec, WorkflowBudget


@dataclass
class BudgetEnvelope:
    """Envelope with hard-stop enforcement for a single workflow run."""

    budget: WorkflowBudget

    def consume_tokens(self, input_tokens: int = 0, output_tokens: int = 0) -> str | None:
        """Consume tokens. Returns reason string if ceiling hit, else None."""
        self.budget.tokens_used += input_tokens + output_tokens
        return self.budget.is_exceeded()

    def consume_cost(self, cost: float) -> str | None:
        self.budget.provider_cost_used += cost
        return self.budget.is_exceeded()

    def consume_agent_call(self) -> str | None:
        self.budget.agent_calls_used += 1
        return self.budget.is_exceeded()

    def consume_wall_time(self, seconds: float) -> str | None:
        self.budget.wall_time_used_seconds += seconds
        return self.budget.is_exceeded()

    def check(self) -> str | None:
        return self.budget.is_exceeded()

    def snapshot(self) -> dict[str, Any]:
        return {
            "tokens_used": self.budget.tokens_used,
            "max_tokens": self.budget.max_tokens,
            "provider_cost_used": self.budget.provider_cost_used,
            "max_provider_cost": self.budget.max_provider_cost,
            "agent_calls_used": self.budget.agent_calls_used,
            "max_agent_calls": self.budget.max_agent_calls,
            "wall_time_used_seconds": round(self.budget.wall_time_used_seconds, 2),
            "max_wall_time_seconds": self.budget.max_wall_time_seconds,
        }


def budget_from_spec(spec: BudgetSpec) -> WorkflowBudget:
    return WorkflowBudget(
        max_tokens=spec.max_tokens,
        max_provider_cost=spec.max_provider_cost,
        max_wall_time_seconds=spec.max_wall_time_seconds,
        max_agent_calls=spec.max_agent_calls,
    )

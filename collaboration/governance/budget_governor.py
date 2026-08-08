"""Budget governor — hard enforcement (§34, §140)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class BudgetState:
    tokens_used: int = 0
    calls: int = 0
    cost: float = 0.0
    started_at: str = ""
    status: str = "OK"  # OK | PAUSED_BUDGET | BLOCKED_BUDGET


class BudgetGovernor:
    """max_tokens / max_calls / max_cost — hard-enforced, no unbounded spend."""

    def __init__(
        self,
        *,
        max_tokens: int = 12000,
        max_calls: int = 50,
        max_cost: float = 25.0,
        max_tokens_per_hour: int = 100000,
    ):
        self.max_tokens = max_tokens
        self.max_calls = max_calls
        self.max_cost = max_cost
        self.max_tokens_per_hour = max_tokens_per_hour
        self._state = BudgetState(started_at=_now())

    def can_spend(self, *, tokens: int = 0, calls: int = 1, cost: float = 0.0) -> bool:
        s = self._state
        if s.status in ("PAUSED_BUDGET", "BLOCKED_BUDGET"):
            return False
        if s.tokens_used + tokens > self.max_tokens:
            return False
        if s.calls + calls > self.max_calls:
            return False
        return not s.cost + cost > self.max_cost

    def record(self, *, tokens: int = 0, cost: float = 0.0, calls: int = 1) -> str:
        s = self._state
        if not self.can_spend(tokens=tokens, calls=calls, cost=cost):
            s.status = "BLOCKED_BUDGET"
            return s.status
        s.tokens_used += tokens
        s.calls += calls
        s.cost += cost
        if s.tokens_used >= self.max_tokens or s.calls >= self.max_calls or s.cost >= self.max_cost:
            s.status = "BLOCKED_BUDGET"
        return s.status

    def snapshot(self) -> dict:
        s = self._state
        return {
            "tokens_used": s.tokens_used,
            "calls": s.calls,
            "cost": s.cost,
            "max_tokens": self.max_tokens,
            "max_calls": self.max_calls,
            "max_cost": self.max_cost,
            "status": s.status,
        }

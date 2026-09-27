"""Execution budgets, checkpoints, manifests, receipts and promotion gates."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field


@dataclass
class ExecutionBudget:
    max_input_tokens: int = 12000
    max_output_tokens: int = 4096
    max_cost_usd: float = 0.0
    max_repairs: int = 3
    used_input_tokens: int = 0
    used_output_tokens: int = 0
    used_cost_usd: float = 0.0

    def charge(self, *, input_tokens: int = 0, output_tokens: int = 0, cost_usd: float = 0.0) -> None:
        if min(input_tokens, output_tokens) < 0 or cost_usd < 0:
            raise ValueError("budget charges cannot be negative")
        if self.used_input_tokens + input_tokens > self.max_input_tokens:
            raise RuntimeError("INPUT_TOKEN_BUDGET_EXCEEDED")
        if self.used_output_tokens + output_tokens > self.max_output_tokens:
            raise RuntimeError("OUTPUT_TOKEN_BUDGET_EXCEEDED")
        if self.used_cost_usd + cost_usd > self.max_cost_usd:
            raise RuntimeError("COST_BUDGET_EXCEEDED")
        self.used_input_tokens += input_tokens
        self.used_output_tokens += output_tokens
        self.used_cost_usd += cost_usd


@dataclass(frozen=True)
class Checkpoint:
    checkpoint_id: str
    ref: str
    changed_files: tuple[str, ...] = ()


@dataclass
class ChangedFileManifest:
    before_ref: str
    after_ref: str
    files: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TestDeltaReceipt:
    before_passed: int
    before_failed: int
    after_passed: int
    after_failed: int

    @property
    def regression(self) -> bool:
        return self.after_failed > self.before_failed or self.after_passed < self.before_passed


class CircuitBreaker:
    def __init__(self, failure_limit: int = 3):
        if failure_limit < 1:
            raise ValueError("failure_limit must be >= 1")
        self.failure_limit = failure_limit
        self.failures = 0
        self.open = False

    def record(self, ok: bool) -> None:
        if ok:
            self.failures = 0
            return
        self.failures += 1
        if self.failures >= self.failure_limit:
            self.open = True

    def assert_closed(self) -> None:
        if self.open:
            raise RuntimeError("REPAIR_CIRCUIT_OPEN")


@dataclass(frozen=True)
class BenchmarkResult:
    model_id: str
    suite: str
    score: float
    evidence_ref: str


class ModelPromotionGate:
    def __init__(self, minimum_score: float):
        self.minimum_score = minimum_score

    def admit(self, results: Iterable[BenchmarkResult], *, required_suites: Iterable[str]) -> tuple[bool, str]:
        by_suite: dict[str, BenchmarkResult] = {r.suite: r for r in results}
        for suite in required_suites:
            result = by_suite.get(suite)
            if result is None:
                return False, f"MISSING_BENCHMARK:{suite}"
            if not result.evidence_ref:
                return False, f"MISSING_EVIDENCE:{suite}"
            if result.score < self.minimum_score:
                return False, f"BELOW_FLOOR:{suite}"
        return True, "PROMOTED"

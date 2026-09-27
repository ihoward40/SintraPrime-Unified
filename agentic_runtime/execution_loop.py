"""Governed plan -> execute -> verify -> heal loop.

No raw execution authority lives here. Authorization, execution, verification,
repair generation and evidence recording are injected from SintraPrime.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import StrEnum

from .controls import CircuitBreaker, ExecutionBudget


class ExecutionMode(StrEnum):
    BUILD = "build"
    AUTOHEAL = "autoheal"
    JANITOR = "janitor"


@dataclass
class StepResult:
    action: str
    ok: bool
    output: str = ""
    healthy: bool | None = None
    changed_files: list[str] = field(default_factory=list)
    attempt: int = 1
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class GovernedExecutionLoop:
    def __init__(
        self,
        *,
        authorize: Callable[[str, dict], bool],
        execute: Callable[[str], StepResult],
        verify: Callable[[], StepResult],
        repair: Callable[[StepResult, int], str | None],
        record: Callable[[str, dict], None],
        max_heal_attempts: int = 3,
        budget: ExecutionBudget | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        if max_heal_attempts < 0:
            raise ValueError("max_heal_attempts cannot be negative")
        self.authorize = authorize
        self.execute = execute
        self.verify = verify
        self.repair = repair
        self.record = record
        self.max_heal_attempts = max_heal_attempts
        self.budget = budget
        self.circuit_breaker = circuit_breaker or CircuitBreaker(max(1, max_heal_attempts or 1))

    def _account(self, result: StepResult) -> None:
        if self.budget:
            self.budget.charge(
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                cost_usd=result.cost_usd,
            )

    def run(self, actions: Iterable[str], mode: ExecutionMode = ExecutionMode.BUILD) -> list[StepResult]:
        results: list[StepResult] = []
        for action in actions:
            context = {"mode": mode.value, "action": action}
            if not self.authorize(action, context):
                denied = StepResult(action=action, ok=False, output="DENIED_BY_POLICY")
                self.record("action_denied", context)
                results.append(denied)
                return results
            result = self.execute(action)
            self._account(result)
            self.record("action_executed", {**context, "ok": result.ok, "changed_files": result.changed_files})
            results.append(result)
            if not result.ok:
                return results

        verification = self.verify()
        verification_healthy = verification.healthy if verification.healthy is not None else verification.ok
        self._account(verification)
        self.record("verification", {"ok": verification.ok, "healthy": verification_healthy, "output": verification.output})
        results.append(verification)
        if not verification.ok:
            return results
        if verification_healthy or mode == ExecutionMode.JANITOR:
            return results

        failure = verification
        for attempt in range(1, self.max_heal_attempts + 1):
            try:
                self.circuit_breaker.assert_closed()
            except RuntimeError:
                results.append(
                    StepResult(
                        action="autoheal",
                        ok=False,
                        output="REPAIR_CIRCUIT_OPEN",
                        attempt=attempt,
                    )
                )
                break
            repair_action = self.repair(failure, attempt)
            if not repair_action:
                results.append(
                    StepResult(
                        action="autoheal",
                        ok=False,
                        output="REPAIR_UNAVAILABLE",
                        attempt=attempt,
                    )
                )
                break
            context = {
                "mode": mode.value,
                "repair_mode": ExecutionMode.AUTOHEAL.value,
                "action": repair_action,
                "attempt": attempt,
            }
            if not self.authorize(repair_action, context):
                self.record("repair_denied", context)
                results.append(
                    StepResult(
                        action=repair_action,
                        ok=False,
                        output="REPAIR_DENIED_BY_POLICY",
                        attempt=attempt,
                    )
                )
                break
            repaired = self.execute(repair_action)
            repaired.attempt = attempt
            self._account(repaired)
            results.append(repaired)
            self.record("repair_executed", {**context, "ok": repaired.ok, "changed_files": repaired.changed_files})
            if not repaired.ok:
                failure = repaired
                self.circuit_breaker.record(False)
                continue
            failure = self.verify()
            failure_healthy = failure.healthy if failure.healthy is not None else failure.ok
            self._account(failure)
            results.append(failure)
            self.record(
                "verification",
                {"ok": failure.ok, "healthy": failure_healthy, "attempt": attempt, "output": failure.output},
            )
            if not failure.ok:
                self.circuit_breaker.record(False)
                return results
            self.circuit_breaker.record(failure_healthy)
            if failure_healthy:
                break
            if attempt == self.max_heal_attempts:
                results.append(
                    StepResult(
                        action="autoheal",
                        ok=False,
                        output="REPAIR_BUDGET_EXHAUSTED",
                        attempt=attempt,
                    )
                )
        return results

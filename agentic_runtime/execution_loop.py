"""Governed plan -> execute -> verify -> heal loop.

This module deliberately does not execute shell commands itself. Every action
is delegated to injected callbacks so existing SintraPrime approval, sandbox,
audit, and evidence boundaries remain authoritative.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Iterable, List, Optional


class ExecutionMode(str, Enum):
    BUILD = "build"
    AUTOHEAL = "autoheal"
    JANITOR = "janitor"


@dataclass
class StepResult:
    action: str
    ok: bool
    output: str = ""
    changed_files: List[str] = field(default_factory=list)
    attempt: int = 1


class GovernedExecutionLoop:
    def __init__(
        self,
        *,
        authorize: Callable[[str, dict], bool],
        execute: Callable[[str], StepResult],
        verify: Callable[[], StepResult],
        repair: Callable[[StepResult, int], Optional[str]],
        record: Callable[[str, dict], None],
        max_heal_attempts: int = 3,
    ) -> None:
        if max_heal_attempts < 0:
            raise ValueError("max_heal_attempts cannot be negative")
        self.authorize = authorize
        self.execute = execute
        self.verify = verify
        self.repair = repair
        self.record = record
        self.max_heal_attempts = max_heal_attempts

    def run(self, actions: Iterable[str], mode: ExecutionMode = ExecutionMode.BUILD) -> List[StepResult]:
        results: List[StepResult] = []
        for action in actions:
            context = {"mode": mode.value, "action": action}
            if not self.authorize(action, context):
                denied = StepResult(action=action, ok=False, output="DENIED_BY_POLICY")
                self.record("action_denied", context)
                results.append(denied)
                return results
            result = self.execute(action)
            self.record("action_executed", {**context, "ok": result.ok, "changed_files": result.changed_files})
            results.append(result)
            if not result.ok:
                return results

        verification = self.verify()
        self.record("verification", {"ok": verification.ok, "output": verification.output})
        results.append(verification)
        if verification.ok or mode == ExecutionMode.JANITOR:
            return results

        failure = verification
        for attempt in range(1, self.max_heal_attempts + 1):
            repair_action = self.repair(failure, attempt)
            if not repair_action:
                break
            context = {"mode": ExecutionMode.AUTOHEAL.value, "action": repair_action, "attempt": attempt}
            if not self.authorize(repair_action, context):
                self.record("repair_denied", context)
                break
            repaired = self.execute(repair_action)
            repaired.attempt = attempt
            results.append(repaired)
            self.record("repair_executed", {**context, "ok": repaired.ok, "changed_files": repaired.changed_files})
            if not repaired.ok:
                failure = repaired
                continue
            failure = self.verify()
            results.append(failure)
            self.record("verification", {"ok": failure.ok, "attempt": attempt, "output": failure.output})
            if failure.ok:
                break
        return results

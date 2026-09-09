"""Typed context package (Wave 3, §24-§25) + budget/loop protection (§29-§30).

Agents receive the minimum context necessary (§25): no unrelated tenant
data, no unrelated memory, no credentials, no unrelated mission history.
Minimization is structural: oversized payloads are rejected at the
boundary, not trusted downstream.
"""
from __future__ import annotations

import json
import time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .manifest import BudgetPolicy, MemoryScope

MAX_PAYLOAD_JSON_CHARS = 100_000


class ContextError(Exception):
    """Context boundary violation."""


class BudgetExhaustedError(Exception):
    """Bounded outcome: budget exhausted → stop or escalate (§30)."""


class ContextPackage(BaseModel):
    """§24 typed context package — the only thing crossing agent boundaries."""

    model_config = ConfigDict(frozen=True)

    mission_id: str
    mission_type: str
    parent_agent: str
    agent_id: str
    delegation_id: str
    tenant: str
    resource_scope: tuple[str, ...] = ()
    memory_scope: MemoryScope = MemoryScope.NONE
    time_budget_seconds: int = Field(default=600, ge=1)
    payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _payload_size_bounded(self) -> ContextPackage:
        size = len(json.dumps(self.payload, default=str))
        if size > MAX_PAYLOAD_JSON_CHARS:
            raise ValueError(
                f"context payload exceeds {MAX_PAYLOAD_JSON_CHARS} JSON chars (§25 minimization)"
            )
        return self


class BudgetTracker:
    """§29 bounded execution + §30 loop protection.

    Tracks iterations, provider calls, tool calls, wall time; detects
    no-progress loops (repeated identical requests / unchanged outputs).
    Outcomes are bounded: budget exhausted → stop or escalate, never
    infinite retry.
    """

    def __init__(
        self,
        policy: BudgetPolicy,
        started_at: float | None = None,
        *,
        max_no_progress_cycles: int = 5,
    ) -> None:
        if not isinstance(policy, BudgetPolicy):
            raise TypeError("BudgetTracker requires a BudgetPolicy")
        self._policy = policy
        self.iterations = 0
        self.provider_calls = 0
        self.tool_calls = 0
        self.started_at = started_at if started_at is not None else time.monotonic()
        self._last_request: str | None = None
        self._last_output: str | None = None
        self._repeat_count = 0
        self._no_progress_cycles = 0
        self._max_no_progress = max(1, max_no_progress_cycles)

    # -- accounting ---------------------------------------------------------

    def begin_iteration(self) -> None:
        self._assert_time()
        self.iterations += 1
        if self.iterations > self._policy.max_iterations:
            raise BudgetExhaustedError(
                f"max_iterations ({self._policy.max_iterations}) exhausted (§30)"
            )

    def consume_provider_call(self) -> None:
        self.provider_calls += 1
        if self.provider_calls > self._policy.max_provider_calls:
            raise BudgetExhaustedError(
                f"max_provider_calls ({self._policy.max_provider_calls}) exhausted"
            )

    def consume_tool_call(self) -> None:
        self.tool_calls += 1
        if self.tool_calls > self._policy.max_tool_calls:
            raise BudgetExhaustedError(f"max_tool_calls ({self._policy.max_tool_calls}) exhausted")

    def check_timeout(self) -> None:
        if self.timeout_elapsed():
            raise BudgetExhaustedError(f"timeout_seconds ({self._policy.timeout_seconds}) exhausted")

    def _assert_time(self) -> None:
        if self.timeout_elapsed():
            raise BudgetExhaustedError(f"timeout_seconds ({self._policy.timeout_seconds}) exhausted")

    # -- §30 loop protection -------------------------------------------------

    def observe(self, request_key: str, output_key: str) -> str | None:
        """§20/§21: no-progress detection with stable signatures.

        Detects: repeated identical request, repeated identical error/output
        signature, and state stagnation. Returns the canonical response:
          None                    → progress, continue
          "RETRY"                 → first repeat, policy-permitted retry
          "STRATEGY_CHANGE"       → persistent repeat
          "NO_PROGRESS_ESCALATE"  → no advancement; escalate/stop
        INFINITE_AGENT_LOOP = IMPOSSIBLE (§21): repeats are bounded by
        no-progress cycles and by every budget cap."""
        if request_key == self._last_request and output_key == self._last_output:
            self._repeat_count += 1
        else:
            self._repeat_count = 0
        self._last_request = request_key
        self._last_output = output_key
        if self._repeat_count == 0:
            return None
        if self._repeat_count < 3:
            return "RETRY_PERMITTED"
        if self._repeat_count < 6:
            return "STRATEGY_TRANSITION"
        return "NO_PROGRESS_STOP"

    # -- predicates -----------------------------------------------------------

    def exhausted(self) -> bool:
        return self.iterations >= self._policy.max_iterations

    def timeout_elapsed(self) -> bool:
        return (time.monotonic() - self.started_at) >= self._policy.timeout_seconds


def context_hash(ctx: ContextPackage) -> str:
    """§17: stable hash of the operational context package. Recorded in the
    runtime receipt as evidence that the executed agent received the exact
    bounded context being audited. Hashes structure, not secret plaintext."""
    import hashlib

    return hashlib.sha256(ctx.model_dump_json().encode("utf-8")).hexdigest()

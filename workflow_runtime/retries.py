"""Bounded retry + circuit breaker.

Every retry is capped. Infinite loops are forbidden.
The circuit breaker halts on repeated identical failures.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    initial_interval: float = 1.0
    backoff_coefficient: float = 2.0
    max_interval: float = 60.0
    jitter: bool = True

    def next_delay(self, attempt: int) -> float:
        delay = min(
            self.initial_interval * (self.backoff_coefficient**attempt),
            self.max_interval,
        )
        if self.jitter:
            delay *= 0.75 + random.random() * 0.5
        return delay


@dataclass
class CircuitBreaker:
    """Halts a node after repeated identical failures.

    Circuit-breaker state:
    - CLOSED (normal): failures counted; opens after threshold.
    - OPEN (halted): workflow enters BLOCKED_SAFETY.
    """

    failure_threshold: int = 3
    consecutive_identical_failures: int = 0
    last_error_signature: str = ""
    open: bool = False

    def record(self, error: str) -> bool:
        """Record an error. Returns True if the circuit is now OPEN."""
        sig = error[:120]
        if sig == self.last_error_signature:
            self.consecutive_identical_failures += 1
        else:
            self.consecutive_identical_failures = 1
            self.last_error_signature = sig
        if self.consecutive_identical_failures >= self.failure_threshold:
            self.open = True
        return self.open

    def reset(self) -> None:
        self.consecutive_identical_failures = 0
        self.last_error_signature = ""
        self.open = False

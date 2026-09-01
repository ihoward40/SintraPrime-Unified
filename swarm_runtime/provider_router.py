"""Provider router with health registry, timeout, and failover.

The model is replaceable. The worker is persistent.
If one provider stalls, the WORKER survives and switches providers.

Provider states:
    HEALTHY    — accepting work, responding within thresholds
    DEGRADED   — slow responses, still functional
    COOLDOWN   — temporarily removed from critical path
    UNAVAILABLE — repeated failures, not assigned new work
"""
from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from enum import Enum


class ProviderState(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    COOLDOWN = "cooldown"
    UNAVAILABLE = "unavailable"


@dataclass
class ProviderHealth:
    """Tracks health metrics for a provider."""
    provider: str
    model: str = ""
    state: ProviderState = ProviderState.HEALTHY

    # Metrics
    response_times: list[float] = field(default_factory=list)
    success_count: int = 0
    timeout_count: int = 0
    failure_count: int = 0
    tool_call_success_count: int = 0
    tool_call_count: int = 0

    # Timing
    last_success: float | None = None
    last_failure: float | None = None
    cooldown_until: float | None = None

    # Thresholds
    first_byte_timeout: float = 30.0
    progress_timeout: float = 60.0
    max_attempts: int = 2

    def record_success(self, response_time: float) -> None:
        self.success_count += 1
        self.response_times.append(response_time)
        if len(self.response_times) > 50:
            self.response_times = self.response_times[-50:]
        self.last_success = time.time()
        if self.state == ProviderState.DEGRADED and self._recent_failure_rate() < 0.2:
            self.state = ProviderState.HEALTHY

    def record_timeout(self) -> None:
        self.timeout_count += 1
        self.last_failure = time.time()
        self._check_circuit_breaker()

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure = time.time()
        self._check_circuit_breaker()

    def record_tool_call(self, success: bool) -> None:
        self.tool_call_count += 1
        if success:
            self.tool_call_success_count += 1

    def is_available(self) -> bool:
        if self.state == ProviderState.UNAVAILABLE:
            return False
        if self.state == ProviderState.COOLDOWN:
            if self.cooldown_until and time.time() < self.cooldown_until:
                return False
            self.state = ProviderState.DEGRADED
            self.cooldown_until = None
        return True

    def median_response_time(self) -> float:
        if not self.response_times:
            return 0.0
        return statistics.median(self.response_times)

    def success_rate(self) -> float:
        total = self.success_count + self.failure_count + self.timeout_count
        if total == 0:
            return 1.0
        return self.success_count / total

    def timeout_rate(self) -> float:
        total = self.success_count + self.failure_count + self.timeout_count
        if total == 0:
            return 0.0
        return self.timeout_count / total

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "state": self.state.value,
            "success_rate": self.success_rate(),
            "median_first_token": self.median_response_time(),
            "timeout_rate": self.timeout_rate(),
            "tool_call_success_rate": (
                self.tool_call_success_count / self.tool_call_count
                if self.tool_call_count > 0 else 1.0
            ),
            "last_failure": self.last_failure,
            "cooldown_until": self.cooldown_until,
        }

    def _recent_failure_rate(self) -> float:
        total = self.success_count + self.failure_count + self.timeout_count
        if total == 0:
            return 0.0
        return (self.failure_count + self.timeout_count) / total

    def _check_circuit_breaker(self) -> None:
        """Circuit breaker: 3 failures in 10 minutes → 30 min cooldown."""
        now = time.time()
        if self.timeout_count >= 3 and self.last_failure:
            if now - self.last_failure < 600:  # 10 minutes
                self.state = ProviderState.COOLDOWN
                self.cooldown_until = now + 1800  # 30 minutes


class ProviderRouter:
    """Routes worker requests to providers with failover."""

    def __init__(self) -> None:
        self._providers: dict[str, ProviderHealth] = {}
        self._provider_order: list[str] = []

    def register_provider(self, name: str, model: str = "",
                          first_byte_timeout: float = 30.0) -> ProviderHealth:
        health = ProviderHealth(
            provider=name, model=model,
            first_byte_timeout=first_byte_timeout,
        )
        self._providers[name] = health
        self._provider_order.append(name)
        return health

    def select_provider(self, primary: str = "",
                        fallbacks: list[str] | None = None) -> ProviderHealth | None:
        """Select the best available provider, respecting priority order."""
        candidates = [primary] + (fallbacks or []) + self._provider_order
        seen = set()
        for name in candidates:
            if name in seen or not name:
                continue
            seen.add(name)
            health = self._providers.get(name)
            if health and health.is_available():
                return health
        return None

    def get_health(self, provider: str) -> ProviderHealth | None:
        return self._providers.get(provider)

    def all_health(self) -> dict[str, dict]:
        return {name: h.to_dict() for name, h in self._providers.items()}

    def mark_timeout(self, provider: str) -> None:
        health = self._providers.get(provider)
        if health:
            health.record_timeout()

    def mark_failure(self, provider: str) -> None:
        health = self._providers.get(provider)
        if health:
            health.record_failure()

    def mark_success(self, provider: str, response_time: float) -> None:
        health = self._providers.get(provider)
        if health:
            health.record_success(response_time)

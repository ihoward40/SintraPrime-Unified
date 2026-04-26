"""
Metrics Collector for SintraPrime-Unified
Counter, Gauge, Histogram with Prometheus-compatible text output.
"""

from __future__ import annotations

import math
import threading
import time
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Base metric
# ---------------------------------------------------------------------------

class Metric:
    def __init__(self, name: str, help_text: str, labels: Optional[Dict[str, str]] = None) -> None:
        self.name = name
        self.help_text = help_text
        self.labels: Dict[str, str] = labels or {}
        self._lock = threading.Lock()

    def _label_str(self) -> str:
        if not self.labels:
            return ""
        parts = [f'{k}="{v}"' for k, v in sorted(self.labels.items())]
        return "{" + ",".join(parts) + "}"


# ---------------------------------------------------------------------------
# Counter
# ---------------------------------------------------------------------------

class Counter(Metric):
    """Monotonically increasing counter."""

    def __init__(self, name: str, help_text: str = "", labels: Optional[Dict[str, str]] = None) -> None:
        super().__init__(name, help_text, labels)
        self._value: float = 0.0

    def inc(self, amount: float = 1.0) -> None:
        if amount < 0:
            raise ValueError("Counter can only increase")
        with self._lock:
            self._value += amount

    @property
    def value(self) -> float:
        with self._lock:
            return self._value

    def reset(self) -> None:
        with self._lock:
            self._value = 0.0

    def prometheus_text(self) -> str:
        lines = [
            f"# HELP {self.name} {self.help_text}",
            f"# TYPE {self.name} counter",
            f"{self.name}{self._label_str()} {self._value}",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Gauge
# ---------------------------------------------------------------------------

class Gauge(Metric):
    """Arbitrary numeric value that can go up or down."""

    def __init__(self, name: str, help_text: str = "", labels: Optional[Dict[str, str]] = None) -> None:
        super().__init__(name, help_text, labels)
        self._value: float = 0.0

    def set(self, value: float) -> None:
        with self._lock:
            self._value = value

    def inc(self, amount: float = 1.0) -> None:
        with self._lock:
            self._value += amount

    def dec(self, amount: float = 1.0) -> None:
        with self._lock:
            self._value -= amount

    @property
    def value(self) -> float:
        with self._lock:
            return self._value

    def prometheus_text(self) -> str:
        lines = [
            f"# HELP {self.name} {self.help_text}",
            f"# TYPE {self.name} gauge",
            f"{self.name}{self._label_str()} {self._value}",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Histogram
# ---------------------------------------------------------------------------

_DEFAULT_BUCKETS = (
    0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf")
)


class Histogram(Metric):
    """Tracks value distributions across configurable buckets."""

    def __init__(
        self,
        name: str,
        help_text: str = "",
        buckets: Tuple[float, ...] = _DEFAULT_BUCKETS,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(name, help_text, labels)
        self._buckets = sorted(buckets)
        if self._buckets[-1] != float("inf"):
            self._buckets.append(float("inf"))
        self._counts: List[int] = [0] * len(self._buckets)
        self._sum: float = 0.0
        self._total_count: int = 0

    def observe(self, value: float) -> None:
        with self._lock:
            self._sum += value
            self._total_count += 1
            for i, bound in enumerate(self._buckets):
                if value <= bound:
                    self._counts[i] += 1

    @property
    def sum(self) -> float:
        with self._lock:
            return self._sum

    @property
    def count(self) -> int:
        with self._lock:
            return self._total_count

    def percentile(self, p: float) -> Optional[float]:
        """Estimate percentile (0..100) from bucket data."""
        with self._lock:
            if self._total_count == 0:
                return None
            target = math.ceil(p / 100 * self._total_count)
            cumulative = 0
            for bound, cnt in zip(self._buckets, self._counts):
                cumulative += cnt
                if cumulative >= target:
                    return bound if bound != float("inf") else None
        return None

    def prometheus_text(self) -> str:
        label_str = self._label_str()
        lines = [
            f"# HELP {self.name} {self.help_text}",
            f"# TYPE {self.name} histogram",
        ]
        cumulative = 0
        for bound, cnt in zip(self._buckets, self._counts):
            cumulative += cnt
            le = "+Inf" if bound == float("inf") else str(bound)
            if label_str:
                inner = label_str[1:-1] + f',le="{le}"'
                bucket_label = "{" + inner + "}"
            else:
                bucket_label = '{' + f'le="{le}"' + "}"
            lines.append(f"{self.name}_bucket{bucket_label} {cumulative}")
        lines.append(f"{self.name}_sum{label_str} {self._sum}")
        lines.append(f"{self.name}_count{label_str} {self._total_count}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# MetricsRegistry
# ---------------------------------------------------------------------------

class MetricsRegistry:
    """Central registry that owns all metric instances."""

    def __init__(self) -> None:
        self._metrics: Dict[str, Metric] = {}
        self._lock = threading.Lock()

    def register(self, metric: Metric) -> Metric:
        with self._lock:
            self._metrics[metric.name] = metric
        return metric

    def get(self, name: str) -> Optional[Metric]:
        return self._metrics.get(name)

    def all_metrics(self) -> List[Metric]:
        return list(self._metrics.values())

    def prometheus_text(self) -> str:
        parts: List[str] = []
        for metric in self._metrics.values():
            parts.append(metric.prometheus_text())
        return "\n\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Built-in SintraPrime metrics
# ---------------------------------------------------------------------------

class SintraMetrics:
    """
    Pre-built metrics for the SintraPrime-Unified agent system.

    Usage:
        m = SintraMetrics()
        m.agent_calls_total.inc()
        m.latency_ms.observe(42.5)
        print(m.registry.prometheus_text())
    """

    def __init__(self) -> None:
        self.registry = MetricsRegistry()

        self.agent_calls_total = self.registry.register(
            Counter(
                "agent_calls_total",
                "Total number of agent invocations across all agents",
            )
        )
        self.agent_errors_total = self.registry.register(
            Counter(
                "agent_errors_total",
                "Total number of agent errors",
            )
        )
        self.latency_ms = self.registry.register(
            Histogram(
                "agent_latency_ms",
                "Agent call latency in milliseconds",
                buckets=(1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, float("inf")),
            )
        )
        self.token_usage = self.registry.register(
            Counter(
                "token_usage_total",
                "Total LLM tokens consumed",
            )
        )
        self.active_agents = self.registry.register(
            Gauge(
                "active_agents",
                "Number of currently active agent instances",
            )
        )
        self.error_rate = self.registry.register(
            Gauge(
                "error_rate",
                "Rolling error rate (errors / calls)",
            )
        )
        self.thought_steps_total = self.registry.register(
            Counter(
                "thought_steps_total",
                "Total reasoning steps recorded by the thought debugger",
            )
        )
        self.snapshots_total = self.registry.register(
            Counter(
                "snapshots_total",
                "Total time-travel snapshots captured",
            )
        )
        self.trace_spans_total = self.registry.register(
            Counter(
                "trace_spans_total",
                "Total distributed trace spans created",
            )
        )

    def update_error_rate(self) -> None:
        calls = self.agent_calls_total.value
        errors = self.agent_errors_total.value
        if calls > 0:
            self.error_rate.set(errors / calls)

    def record_call(self, duration_ms: float, tokens: int = 0, error: bool = False) -> None:
        self.agent_calls_total.inc()
        self.latency_ms.observe(duration_ms)
        if tokens:
            self.token_usage.inc(tokens)
        if error:
            self.agent_errors_total.inc()
        self.update_error_rate()

    def prometheus_output(self) -> str:
        return self.registry.prometheus_text()

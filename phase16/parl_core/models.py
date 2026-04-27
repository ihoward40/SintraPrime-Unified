"""Phase 16G — PARL Core Integration: data models."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time


@dataclass
class SubagentContext:
    """Isolated execution context for a single subagent."""
    agent_id: str
    task_description: str
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    ttl: float = 300.0  # seconds
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl


@dataclass
class SubagentResult:
    """Result produced by a single subagent."""
    agent_id: str
    success: bool
    output: Any
    duration_seconds: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CriticalPathMetrics:
    """Metrics for the critical execution path in a PARL episode."""
    critical_path_duration: float
    total_parallel_duration: float
    num_subagents: int
    parallelism_efficiency: float  # critical_path / total if sequential
    bottleneck_agent_id: Optional[str] = None


@dataclass
class PARLEpisode:
    """A complete PARL training episode."""
    task_id: str
    task_description: str
    subagent_results: List[SubagentResult] = field(default_factory=list)
    total_reward: float = 0.0
    r_parallel: float = 0.0
    r_finish: float = 0.0
    r_perf: float = 0.0
    critical_path: Optional[CriticalPathMetrics] = None
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    step: int = 0

    @property
    def duration(self) -> float:
        if self.completed_at:
            return self.completed_at - self.started_at
        return time.time() - self.started_at

    @property
    def success_rate(self) -> float:
        if not self.subagent_results:
            return 0.0
        return sum(1 for r in self.subagent_results if r.success) / len(self.subagent_results)


@dataclass
class AnnealingSchedule:
    """Lambda annealing schedule for PARL reward shaping."""
    schedule_type: str  # "linear", "cosine", "exponential"
    lambda1_init: float = 0.5
    lambda2_init: float = 0.1
    total_steps: int = 10_000
    min_value: float = 0.0

    def get_lambda1(self, step: int) -> float:
        return self._anneal(self.lambda1_init, step)

    def get_lambda2(self, step: int) -> float:
        return self._anneal(self.lambda2_init, step)

    def _anneal(self, init: float, step: int) -> float:
        import math
        progress = min(step / max(self.total_steps, 1), 1.0)
        if self.schedule_type == "linear":
            return max(self.min_value, init * (1.0 - progress))
        elif self.schedule_type == "cosine":
            return max(self.min_value, init * 0.5 * (1.0 + math.cos(math.pi * progress)))
        elif self.schedule_type == "exponential":
            return max(self.min_value, init * math.exp(-5.0 * progress))
        return init


@dataclass
class SynthesisResult:
    """Merged output from multiple subagent contexts."""
    task_id: str
    merged_outputs: List[Any] = field(default_factory=list)
    consensus: Optional[Any] = None
    confidence: float = 0.0
    num_sources: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

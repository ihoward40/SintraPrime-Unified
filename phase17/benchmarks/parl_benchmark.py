"""Phase 17B — PARL Performance Benchmarking.

Profiles parallel agent execution across 1, 10, 25, 50, and 100 subagents,
measuring throughput, latency, parallelism efficiency, and reward convergence.
"""
from __future__ import annotations

import time
import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Data models
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SubagentBenchmarkResult:
    """Result for a single subagent run."""
    agent_id: str
    duration_seconds: float
    success: bool
    output: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkRun:
    """Result of a single benchmark run at a given concurrency level."""
    run_id: str
    n_subagents: int
    total_duration_seconds: float
    subagent_results: List[SubagentBenchmarkResult] = field(default_factory=list)
    total_reward: float = 0.0
    r_parallel: float = 0.0
    r_finish: float = 0.0
    r_perf: float = 0.0
    parallelism_efficiency: float = 0.0
    throughput_agents_per_second: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    errors: int = 0

    @property
    def success_rate(self) -> float:
        if not self.subagent_results:
            return 0.0
        return sum(1 for r in self.subagent_results if r.success) / len(self.subagent_results)


@dataclass
class BenchmarkReport:
    """Aggregated benchmark report across all concurrency levels."""
    report_id: str
    runs: List[BenchmarkRun] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None

    def summary(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "total_runs": len(self.runs),
            "concurrency_levels": [r.n_subagents for r in self.runs],
            "best_throughput": max((r.throughput_agents_per_second for r in self.runs), default=0.0),
            "best_efficiency": max((r.parallelism_efficiency for r in self.runs), default=0.0),
            "all_success_rates": {r.n_subagents: r.success_rate for r in self.runs},
        }

    def get_run(self, n_subagents: int) -> Optional[BenchmarkRun]:
        for r in self.runs:
            if r.n_subagents == n_subagents:
                return r
        return None

    def scaling_factor(self, baseline_n: int, target_n: int) -> float:
        """Compute throughput scaling factor between two concurrency levels."""
        baseline = self.get_run(baseline_n)
        target = self.get_run(target_n)
        if not baseline or not target or baseline.throughput_agents_per_second == 0:
            return 0.0
        return target.throughput_agents_per_second / baseline.throughput_agents_per_second


# ─────────────────────────────────────────────────────────────────────────────
# Benchmark runner
# ─────────────────────────────────────────────────────────────────────────────

class PARLBenchmark:
    """Profiles the PARL engine across different concurrency levels."""

    DEFAULT_LEVELS = [1, 10, 25, 50, 100]

    def __init__(
        self,
        concurrency_levels: Optional[List[int]] = None,
        task_complexity_ms: float = 5.0,
        max_workers: int = 16,
    ):
        self.concurrency_levels = concurrency_levels or self.DEFAULT_LEVELS
        self.task_complexity_ms = task_complexity_ms
        self.max_workers = max_workers
        self._report: Optional[BenchmarkReport] = None

    # ── public API ────────────────────────────────────────────────────────────

    def run(self) -> BenchmarkReport:
        """Execute the full benchmark suite and return a report."""
        import uuid
        report = BenchmarkReport(report_id=f"bench_{uuid.uuid4().hex[:8]}")

        for n in self.concurrency_levels:
            run = self._run_level(n)
            report.runs.append(run)

        report.finished_at = time.time()
        self._report = report
        return report

    def run_single(self, n_subagents: int) -> BenchmarkRun:
        """Run benchmark at a single concurrency level."""
        return self._run_level(n_subagents)

    @property
    def last_report(self) -> Optional[BenchmarkReport]:
        return self._report

    # ── internal ──────────────────────────────────────────────────────────────

    def _run_level(self, n_subagents: int) -> BenchmarkRun:
        from phase16.parl_core.parl_engine import PARLEngine
        import uuid

        engine = PARLEngine(max_workers=self.max_workers)
        complexity = self.task_complexity_ms / 1000.0  # convert to seconds

        def make_spec(i: int) -> Dict[str, Any]:
            return {
                "name": f"bench_agent_{i}",
                "complexity_seconds": complexity,
                "payload": {"index": i},
            }

        specs = [make_spec(i) for i in range(n_subagents)]

        t0 = time.perf_counter()
        episode = engine.run_parallel(
            task=f"benchmark_{n_subagents}_agents",
            subagent_specs=specs,
        )
        total_duration = time.perf_counter() - t0

        # Collect per-subagent latencies
        latencies_ms = [
            r.duration_seconds * 1000.0
            for r in episode.subagent_results
        ]

        p50 = statistics.median(latencies_ms) if latencies_ms else 0.0
        p95 = self._percentile(latencies_ms, 95)
        p99 = self._percentile(latencies_ms, 99)

        throughput = n_subagents / total_duration if total_duration > 0 else 0.0

        subagent_results = [
            SubagentBenchmarkResult(
                agent_id=r.agent_id,
                duration_seconds=r.duration_seconds,
                success=r.success,
                output=r.output if isinstance(r.output, dict) else {},
            )
            for r in episode.subagent_results
        ]

        errors = sum(1 for r in subagent_results if not r.success)

        return BenchmarkRun(
            run_id=f"run_{uuid.uuid4().hex[:6]}",
            n_subagents=n_subagents,
            total_duration_seconds=total_duration,
            subagent_results=subagent_results,
            total_reward=episode.total_reward,
            r_parallel=episode.r_parallel,
            r_finish=episode.r_finish,
            r_perf=episode.r_perf,
            parallelism_efficiency=episode.critical_path.parallelism_efficiency,
            throughput_agents_per_second=throughput,
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            errors=errors,
        )

    @staticmethod
    def _percentile(data: List[float], pct: float) -> float:
        if not data:
            return 0.0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * pct / 100.0
        lo, hi = int(k), min(int(k) + 1, len(sorted_data) - 1)
        return sorted_data[lo] + (sorted_data[hi] - sorted_data[lo]) * (k - lo)


# ─────────────────────────────────────────────────────────────────────────────
# Reward convergence tracker
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ConvergencePoint:
    step: int
    total_reward: float
    r_parallel: float
    r_finish: float
    r_perf: float
    lambda1: float
    lambda2: float


class RewardConvergenceTracker:
    """Tracks how PARL reward components evolve over training steps."""

    def __init__(self, total_steps: int = 1000, sample_every: int = 100):
        self.total_steps = total_steps
        self.sample_every = sample_every
        self.history: List[ConvergencePoint] = []

    def run(self) -> List[ConvergencePoint]:
        """Simulate reward convergence over training steps."""
        from phase16.parl_core.parl_engine import PARLEngine

        engine = PARLEngine(total_training_steps=self.total_steps)
        self.history.clear()

        for step in range(0, self.total_steps, self.sample_every):
            # Simulate an episode at this training step
            episode = engine.run_parallel(
                task=f"convergence_step_{step}",
                subagent_specs=[
                    {"name": f"agent_{i}", "payload": {}} for i in range(4)
                ],
            )
            # Anneal lambdas and capture current values
            lambda1, lambda2 = engine.anneal_lambdas(step)

            self.history.append(ConvergencePoint(
                step=step,
                total_reward=episode.total_reward,
                r_parallel=episode.r_parallel,
                r_finish=episode.r_finish,
                r_perf=episode.r_perf,
                lambda1=lambda1,
                lambda2=lambda2,
            ))

        return self.history

    @property
    def final_lambda1(self) -> float:
        return self.history[-1].lambda1 if self.history else 0.0

    @property
    def final_lambda2(self) -> float:
        return self.history[-1].lambda2 if self.history else 0.0

    @property
    def reward_trend(self) -> str:
        """Return 'increasing', 'decreasing', or 'stable'."""
        if len(self.history) < 2:
            return "stable"
        first = self.history[0].total_reward
        last = self.history[-1].total_reward
        delta = last - first
        if delta > 0.05:
            return "increasing"
        if delta < -0.05:
            return "decreasing"
        return "stable"

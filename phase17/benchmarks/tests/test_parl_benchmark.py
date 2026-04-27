"""Phase 17B — PARL Benchmark Tests (55 tests)."""
import pytest
import time
from phase17.benchmarks.parl_benchmark import (
    SubagentBenchmarkResult, BenchmarkRun, BenchmarkReport,
    PARLBenchmark, RewardConvergenceTracker, ConvergencePoint,
)


# ─────────────────────────────────────────────────────────────────────────────
# SubagentBenchmarkResult (5 tests)
# ─────────────────────────────────────────────────────────────────────────────
class TestSubagentBenchmarkResult:
    def test_agent_id(self):
        r = SubagentBenchmarkResult("a1", 0.05, True)
        assert r.agent_id == "a1"

    def test_duration(self):
        r = SubagentBenchmarkResult("a1", 0.123, True)
        assert r.duration_seconds == pytest.approx(0.123)

    def test_success_true(self):
        r = SubagentBenchmarkResult("a1", 0.05, True)
        assert r.success is True

    def test_success_false(self):
        r = SubagentBenchmarkResult("a1", 0.05, False)
        assert r.success is False

    def test_output_default_empty(self):
        r = SubagentBenchmarkResult("a1", 0.05, True)
        assert r.output == {}


# ─────────────────────────────────────────────────────────────────────────────
# BenchmarkRun (10 tests)
# ─────────────────────────────────────────────────────────────────────────────
class TestBenchmarkRun:
    def _make_run(self, n=5, errors=0):
        results = [
            SubagentBenchmarkResult(f"a{i}", 0.01 * (i + 1), i >= errors)
            for i in range(n)
        ]
        return BenchmarkRun(
            run_id="run_test",
            n_subagents=n,
            total_duration_seconds=0.1,
            subagent_results=results,
            total_reward=1.1,
            r_parallel=0.5,
            r_finish=1.0,
            r_perf=0.9,
            parallelism_efficiency=0.85,
            throughput_agents_per_second=float(n) / 0.1,
            p50_latency_ms=30.0,
            p95_latency_ms=50.0,
            p99_latency_ms=60.0,
            errors=errors,
        )

    def test_run_id(self):
        run = self._make_run()
        assert run.run_id == "run_test"

    def test_n_subagents(self):
        run = self._make_run(10)
        assert run.n_subagents == 10

    def test_success_rate_all_pass(self):
        run = self._make_run(5, errors=0)
        assert run.success_rate == 1.0

    def test_success_rate_with_errors(self):
        run = self._make_run(10, errors=2)
        assert run.success_rate == pytest.approx(0.8)

    def test_success_rate_empty(self):
        run = BenchmarkRun(run_id="r", n_subagents=0, total_duration_seconds=0.0)
        assert run.success_rate == 0.0

    def test_throughput(self):
        run = self._make_run(10)
        assert run.throughput_agents_per_second == pytest.approx(100.0)

    def test_parallelism_efficiency(self):
        run = self._make_run()
        assert run.parallelism_efficiency == pytest.approx(0.85)

    def test_p50_latency(self):
        run = self._make_run()
        assert run.p50_latency_ms == pytest.approx(30.0)

    def test_p95_latency(self):
        run = self._make_run()
        assert run.p95_latency_ms == pytest.approx(50.0)

    def test_total_reward(self):
        run = self._make_run()
        assert run.total_reward == pytest.approx(1.1)


# ─────────────────────────────────────────────────────────────────────────────
# BenchmarkReport (10 tests)
# ─────────────────────────────────────────────────────────────────────────────
class TestBenchmarkReport:
    def _make_report(self):
        report = BenchmarkReport(report_id="rep_test")
        for n in [1, 10, 25]:
            report.runs.append(BenchmarkRun(
                run_id=f"run_{n}",
                n_subagents=n,
                total_duration_seconds=0.1,
                throughput_agents_per_second=float(n) * 8.0,
                parallelism_efficiency=0.7 + n * 0.005,
            ))
        return report

    def test_report_id(self):
        r = BenchmarkReport(report_id="rep_test")
        assert r.report_id == "rep_test"

    def test_total_runs(self):
        r = self._make_report()
        assert len(r.runs) == 3

    def test_summary_keys(self):
        r = self._make_report()
        s = r.summary()
        assert "total_runs" in s
        assert "best_throughput" in s
        assert "best_efficiency" in s

    def test_summary_total_runs(self):
        r = self._make_report()
        assert r.summary()["total_runs"] == 3

    def test_summary_best_throughput(self):
        r = self._make_report()
        assert r.summary()["best_throughput"] == pytest.approx(25 * 8.0)

    def test_get_run_found(self):
        r = self._make_report()
        run = r.get_run(10)
        assert run is not None
        assert run.n_subagents == 10

    def test_get_run_not_found(self):
        r = self._make_report()
        assert r.get_run(999) is None

    def test_scaling_factor(self):
        r = self._make_report()
        # n=1: throughput=8, n=10: throughput=80 → factor=10
        factor = r.scaling_factor(1, 10)
        assert factor == pytest.approx(10.0)

    def test_scaling_factor_missing_baseline(self):
        r = self._make_report()
        assert r.scaling_factor(999, 10) == 0.0

    def test_finished_at_none_initially(self):
        r = BenchmarkReport(report_id="r")
        assert r.finished_at is None


# ─────────────────────────────────────────────────────────────────────────────
# PARLBenchmark (20 tests)
# ─────────────────────────────────────────────────────────────────────────────
class TestPARLBenchmark:
    @pytest.fixture(scope="class")
    def bench_1(self):
        b = PARLBenchmark(concurrency_levels=[1], task_complexity_ms=1.0)
        return b.run_single(1)

    @pytest.fixture(scope="class")
    def bench_10(self):
        b = PARLBenchmark(concurrency_levels=[10], task_complexity_ms=1.0)
        return b.run_single(10)

    @pytest.fixture(scope="class")
    def full_bench(self):
        b = PARLBenchmark(concurrency_levels=[1, 5, 10], task_complexity_ms=1.0)
        return b.run()

    def test_run_single_returns_run(self, bench_1):
        assert isinstance(bench_1, BenchmarkRun)

    def test_run_single_n_subagents(self, bench_1):
        assert bench_1.n_subagents == 1

    def test_run_single_has_results(self, bench_1):
        assert len(bench_1.subagent_results) == 1

    def test_run_single_duration_positive(self, bench_1):
        assert bench_1.total_duration_seconds > 0

    def test_run_single_throughput_positive(self, bench_1):
        assert bench_1.throughput_agents_per_second > 0

    def test_run_single_success_rate(self, bench_1):
        assert bench_1.success_rate == 1.0

    def test_run_10_agents(self, bench_10):
        assert bench_10.n_subagents == 10

    def test_run_10_all_results(self, bench_10):
        assert len(bench_10.subagent_results) == 10

    def test_run_10_throughput_higher_than_1(self, bench_1, bench_10):
        assert bench_10.throughput_agents_per_second > bench_1.throughput_agents_per_second

    def test_run_10_p50_positive(self, bench_10):
        assert bench_10.p50_latency_ms > 0

    def test_run_10_p95_gte_p50(self, bench_10):
        assert bench_10.p95_latency_ms >= bench_10.p50_latency_ms

    def test_run_10_p99_gte_p95(self, bench_10):
        assert bench_10.p99_latency_ms >= bench_10.p95_latency_ms

    def test_run_10_total_reward_positive(self, bench_10):
        assert bench_10.total_reward > 0

    def test_run_10_parallelism_efficiency(self, bench_10):
        assert 0.0 <= bench_10.parallelism_efficiency <= 1.0

    def test_full_bench_returns_report(self, full_bench):
        assert isinstance(full_bench, BenchmarkReport)

    def test_full_bench_3_runs(self, full_bench):
        assert len(full_bench.runs) == 3

    def test_full_bench_finished_at_set(self, full_bench):
        assert full_bench.finished_at is not None

    def test_full_bench_summary_levels(self, full_bench):
        levels = full_bench.summary()["concurrency_levels"]
        assert 1 in levels and 5 in levels and 10 in levels

    def test_full_bench_last_report(self):
        b = PARLBenchmark(concurrency_levels=[2], task_complexity_ms=1.0)
        b.run()
        assert b.last_report is not None

    def test_full_bench_scaling_factor(self, full_bench):
        factor = full_bench.scaling_factor(1, 10)
        assert factor > 0


# ─────────────────────────────────────────────────────────────────────────────
# RewardConvergenceTracker (10 tests)
# ─────────────────────────────────────────────────────────────────────────────
class TestRewardConvergenceTracker:
    @pytest.fixture(scope="class")
    def tracker(self):
        t = RewardConvergenceTracker(total_steps=200, sample_every=50)
        t.run()
        return t

    def test_history_not_empty(self, tracker):
        assert len(tracker.history) > 0

    def test_history_length(self, tracker):
        # 200 steps / 50 sample_every = 4 points
        assert len(tracker.history) == 4

    def test_history_steps_ascending(self, tracker):
        steps = [p.step for p in tracker.history]
        assert steps == sorted(steps)

    def test_first_step_zero(self, tracker):
        assert tracker.history[0].step == 0

    def test_convergence_point_has_reward(self, tracker):
        for pt in tracker.history:
            assert pt.total_reward >= 0

    def test_lambda1_positive_initially(self, tracker):
        assert tracker.history[0].lambda1 > 0

    def test_lambda2_positive_initially(self, tracker):
        assert tracker.history[0].lambda2 > 0

    def test_reward_trend_string(self, tracker):
        assert tracker.reward_trend in ("increasing", "decreasing", "stable")

    def test_final_lambda1_accessible(self, tracker):
        assert tracker.final_lambda1 >= 0

    def test_final_lambda2_accessible(self, tracker):
        assert tracker.final_lambda2 >= 0

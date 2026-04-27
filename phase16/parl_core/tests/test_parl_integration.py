"""Phase 16G — PARL Core Integration tests (28 tests)."""
import math
import time
import pytest
from phase16.parl_core.models import (
    AnnealingSchedule, CriticalPathMetrics, PARLEpisode,
    SubagentContext, SubagentResult, SynthesisResult,
)
from phase16.parl_core.context_isolation import ContextIsolationLayer
from phase16.parl_core.parl_engine import PARLEngine


# ─────────────────────────────────────────────────────────────
# Reward function tests (6)
# ─────────────────────────────────────────────────────────────
class TestRewardFunction:
    def _make_engine(self):
        return PARLEngine(max_workers=4, total_training_steps=1000)

    def test_reward_all_success(self):
        eng = self._make_engine()
        specs = [{"agent_id": f"a{i}", "description": "task", "payload": {}} for i in range(3)]
        ep = eng.run_parallel("test", specs)
        assert ep.total_reward >= 0
        assert ep.r_perf == 1.0

    def test_reward_partial_failure(self):
        eng = self._make_engine()
        def bad_executor(ctx):
            if ctx.agent_id == "fail":
                raise RuntimeError("fail")
            return "ok"
        specs = [
            {"agent_id": "ok1", "description": "t", "payload": {}},
            {"agent_id": "fail", "description": "t", "payload": {}},
        ]
        ep = eng.run_parallel("test", specs, executor_fn=bad_executor)
        assert ep.r_finish < 1.0
        assert ep.r_perf < 1.0

    def test_reward_empty_episode(self):
        eng = self._make_engine()
        ep = eng.run_parallel("empty", [])
        assert ep.r_finish == 1.0
        assert ep.total_reward >= 0

    def test_reward_single_agent(self):
        eng = self._make_engine()
        ep = eng.run_parallel("single", [{"agent_id": "a0", "description": "t", "payload": {}}])
        assert ep.r_parallel == 0.0  # no parallelism with 1 agent
        assert ep.r_perf == 1.0

    def test_reward_components_sum(self):
        eng = PARLEngine(max_workers=4, total_training_steps=100)
        specs = [{"agent_id": f"a{i}", "description": "t", "payload": {}} for i in range(4)]
        ep = eng.run_parallel("test", specs)
        λ1, λ2 = eng.anneal_lambdas(ep.step)
        expected = λ1 * ep.r_parallel + λ2 * ep.r_finish + ep.r_perf
        assert abs(ep.total_reward - expected) < 1e-9

    def test_reward_increases_with_success(self):
        eng = self._make_engine()
        specs_good = [{"agent_id": f"a{i}", "description": "t", "payload": {}} for i in range(3)]
        ep_good = eng.run_parallel("good", specs_good)
        assert ep_good.r_perf == 1.0


# ─────────────────────────────────────────────────────────────
# Annealing schedule tests (3)
# ─────────────────────────────────────────────────────────────
class TestAnnealingSchedules:
    def test_linear_annealing(self):
        sched = AnnealingSchedule("linear", lambda1_init=1.0, lambda2_init=0.5, total_steps=100)
        assert sched.get_lambda1(0) == pytest.approx(1.0)
        assert sched.get_lambda1(50) == pytest.approx(0.5)
        assert sched.get_lambda1(100) == pytest.approx(0.0)

    def test_cosine_annealing(self):
        sched = AnnealingSchedule("cosine", lambda1_init=1.0, lambda2_init=0.5, total_steps=100)
        val_mid = sched.get_lambda1(50)
        assert 0.0 < val_mid < 1.0

    def test_exponential_annealing(self):
        sched = AnnealingSchedule("exponential", lambda1_init=1.0, total_steps=100)
        val_start = sched.get_lambda1(0)
        val_end = sched.get_lambda1(100)
        assert val_start > val_end
        assert val_end >= 0.0


# ─────────────────────────────────────────────────────────────
# Critical path tests (3)
# ─────────────────────────────────────────────────────────────
class TestCriticalPath:
    def test_critical_path_computed(self):
        eng = PARLEngine(max_workers=4)
        specs = [{"agent_id": f"a{i}", "description": "t", "payload": {}} for i in range(4)]
        ep = eng.run_parallel("test", specs)
        cp = ep.critical_path
        assert cp is not None
        assert cp.num_subagents == 4
        assert cp.critical_path_duration > 0

    def test_critical_path_bottleneck(self):
        eng = PARLEngine(max_workers=4)
        def slow_executor(ctx):
            if ctx.agent_id == "slow":
                time.sleep(0.05)
            return "ok"
        specs = [
            {"agent_id": "slow", "description": "t", "payload": {}},
            {"agent_id": "fast1", "description": "t", "payload": {}},
            {"agent_id": "fast2", "description": "t", "payload": {}},
        ]
        ep = eng.run_parallel("test", specs, executor_fn=slow_executor)
        assert ep.critical_path.bottleneck_agent_id == "slow"

    def test_critical_path_efficiency(self):
        eng = PARLEngine(max_workers=4)
        specs = [{"agent_id": f"a{i}", "description": "t", "payload": {}} for i in range(4)]
        ep = eng.run_parallel("test", specs)
        cp = ep.critical_path
        assert 0.0 < cp.parallelism_efficiency <= 1.0


# ─────────────────────────────────────────────────────────────
# Context isolation tests (5)
# ─────────────────────────────────────────────────────────────
class TestContextIsolation:
    def test_create_and_retrieve(self):
        layer = ContextIsolationLayer()
        ctx = layer.create_context("agent1", "do something", {"key": "val"})
        retrieved = layer.get("agent1")
        assert retrieved is not None
        assert retrieved.agent_id == "agent1"

    def test_isolation_deep_copy(self):
        layer = ContextIsolationLayer()
        ctx = layer.create_context("a1", "task", {"data": [1, 2, 3]})
        isolated = layer.isolate(ctx)
        isolated.payload["data"].append(99)
        original = layer.get("a1")
        assert 99 not in original.payload["data"]

    def test_ttl_expiry(self):
        layer = ContextIsolationLayer(default_ttl=0.01)
        layer.create_context("a1", "task")
        time.sleep(0.05)
        assert layer.get("a1") is None

    def test_lru_eviction(self):
        layer = ContextIsolationLayer(max_contexts=3)
        for i in range(4):
            layer.create_context(f"a{i}", "task")
        stats = layer.get_stats()
        assert stats["total_contexts"] <= 3

    def test_manual_evict(self):
        layer = ContextIsolationLayer()
        layer.create_context("a1", "task")
        assert layer.evict("a1") is True
        assert layer.get("a1") is None


# ─────────────────────────────────────────────────────────────
# Result synthesis tests (3)
# ─────────────────────────────────────────────────────────────
class TestResultSynthesis:
    def test_merge_multiple_contexts(self):
        layer = ContextIsolationLayer()
        ctxs = [layer.create_context(f"a{i}", "task", {"v": i}) for i in range(3)]
        result = layer.merge_results(ctxs, outputs=["A", "A", "B"])
        assert result.num_sources == 3
        assert result.consensus == "A"

    def test_merge_empty(self):
        layer = ContextIsolationLayer()
        result = layer.merge_results([])
        assert result.num_sources == 0

    def test_merge_single(self):
        layer = ContextIsolationLayer()
        ctx = layer.create_context("a1", "task", {"v": 42})
        result = layer.merge_results([ctx], outputs=["output_42"])
        assert result.num_sources == 1
        assert result.consensus == "output_42"


# ─────────────────────────────────────────────────────────────
# Full pipeline tests (2)
# ─────────────────────────────────────────────────────────────
class TestFullPipelines:
    def test_10_agent_pipeline(self):
        eng = PARLEngine(max_workers=10, total_training_steps=1000)
        specs = [{"agent_id": f"agent_{i}", "description": f"subtask {i}", "payload": {"idx": i}}
                 for i in range(10)]
        ep = eng.run_parallel("10-agent task", specs)
        assert len(ep.subagent_results) == 10
        assert ep.success_rate == 1.0
        assert ep.total_reward > 0

    def test_episode_history_tracked(self):
        eng = PARLEngine(max_workers=4)
        for _ in range(3):
            eng.run_parallel("task", [{"agent_id": "a0", "description": "t", "payload": {}}])
        history = eng.get_episode_history()
        assert len(history) == 3


# ─────────────────────────────────────────────────────────────
# Edge case tests (6)
# ─────────────────────────────────────────────────────────────
class TestEdgeCases:
    def test_all_agents_fail(self):
        eng = PARLEngine(max_workers=4)
        def always_fail(ctx):
            raise RuntimeError("always fails")
        specs = [{"agent_id": f"a{i}", "description": "t", "payload": {}} for i in range(3)]
        ep = eng.run_parallel("fail all", specs, executor_fn=always_fail)
        assert ep.r_perf == 0.0
        assert ep.r_finish == 0.0

    def test_step_counter_increments(self):
        eng = PARLEngine(max_workers=2)
        assert eng.current_step == 0
        eng.run_parallel("t", [{"agent_id": "a0", "description": "t", "payload": {}}])
        assert eng.current_step == 1

    def test_lambda_at_end_of_training(self):
        eng = PARLEngine(total_training_steps=100)
        λ1, λ2 = eng.anneal_lambdas(100)
        assert λ1 == pytest.approx(0.0, abs=1e-6)
        assert λ2 == pytest.approx(0.0, abs=1e-6)

    def test_context_stats(self):
        eng = PARLEngine(max_workers=2)
        stats = eng.get_context_stats()
        assert "total_contexts" in stats
        assert "max_capacity" in stats

    def test_large_payload(self):
        eng = PARLEngine(max_workers=4)
        big_payload = {"data": list(range(1000))}
        specs = [{"agent_id": "big", "description": "t", "payload": big_payload}]
        ep = eng.run_parallel("big payload", specs)
        assert ep.subagent_results[0].success

    def test_duplicate_agent_ids(self):
        eng = PARLEngine(max_workers=4)
        specs = [{"agent_id": "dup", "description": f"task {i}", "payload": {}} for i in range(3)]
        ep = eng.run_parallel("dup ids", specs)
        # Should complete without error even with duplicate IDs
        assert len(ep.subagent_results) == 3

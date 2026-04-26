"""
Comprehensive test suite for the SintraPrime PARL framework.

Tests cover:
- PARLReward: three-term reward, lambda annealing, batch computation
- CriticalStepsMetric: critical path calculation, parallelism efficiency
- LambdaScheduler: linear, cosine, exponential schedules
- SharedReplayBuffer: add, sample, priority, thread-safety
- AgentExperienceCollector: record, episode counting
- PolicyStore: register, push gradient, apply, rollback
- PARLOrchestrator: decompose_and_run, parallel execution, reward integration
- Agent adapters: Zero, Sigma, Nova, Chat
"""

import threading
import time
import uuid
from typing import Any, Tuple
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from parl.reward_engine import (
    PARLReward,
    CriticalStepsMetric,
    LambdaScheduler,
    EpisodeData,
    RewardBreakdown,
    compute_instantiation_reward,
    compute_finish_reward,
    compute_task_quality,
)
from parl.experience_replay import (
    SharedReplayBuffer,
    AgentExperienceCollector,
    Experience,
)
from parl.policy_sync import (
    PolicyStore,
    PolicyVersion,
    GradientAccumulator,
)
from parl.orchestrator import (
    PARLOrchestrator,
    AgentType,
    Task,
    Subtask,
    SubtaskStatus,
)
from parl.agent_adapters import (
    ZeroPARLAdapter,
    SigmaPARLAdapter,
    NovaPARLAdapter,
    ChatPARLAdapter,
    create_adapter,
)


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def reward_fn():
    return PARLReward(
        lambda1_init=0.1,
        lambda1_final=0.0,
        lambda2_init=0.1,
        lambda2_final=0.0,
        total_training_steps=1000,
    )


@pytest.fixture
def episode():
    return EpisodeData(
        num_subagents=25,
        assigned_subtasks=25,
        completed_subtasks=20,
        success=1.0,
        trajectory_score=0.85,
        training_step=500,
    )


@pytest.fixture
def replay_buffer():
    return SharedReplayBuffer(capacity=100, strategy="priority")


@pytest.fixture
def policy_store():
    store = PolicyStore()
    store.register_agent_type("zero", {"lr": 0.01, "epsilon": 0.1})
    store.register_agent_type("sigma", {"threshold": 0.8})
    return store


@pytest.fixture
def orchestrator():
    orch = PARLOrchestrator(
        max_workers=4,
        total_training_steps=1000,
        max_subagents=10,
    )
    # Register all four agent types
    orch.register_agent(AgentType.ZERO, ZeroPARLAdapter())
    orch.register_agent(AgentType.SIGMA, SigmaPARLAdapter())
    orch.register_agent(AgentType.NOVA, NovaPARLAdapter())
    orch.register_agent(AgentType.CHAT, ChatPARLAdapter())
    return orch


# ===========================================================================
# 1. Standalone reward component tests
# ===========================================================================

class TestComputeInstantiationReward:
    def test_zero_subagents(self):
        assert compute_instantiation_reward(0, 100) == 0.0

    def test_full_capacity(self):
        assert compute_instantiation_reward(100, 100) == 1.0

    def test_partial(self):
        r = compute_instantiation_reward(25, 100)
        assert abs(r - 0.25) < 1e-6

    def test_over_capacity_clamped(self):
        r = compute_instantiation_reward(150, 100)
        assert r == 1.0

    def test_zero_max_subagents(self):
        assert compute_instantiation_reward(10, 0) == 0.0


class TestComputeFinishReward:
    def test_all_completed(self):
        assert abs(compute_finish_reward(10, 10) - 1.0) < 1e-5

    def test_none_completed(self):
        assert compute_finish_reward(0, 10) < 0.01

    def test_partial_completion(self):
        r = compute_finish_reward(7, 10)
        assert 0.69 < r < 0.71

    def test_no_subtasks_assigned(self):
        # trivially finished
        assert compute_finish_reward(0, 0) == 1.0

    def test_over_completed_clamped(self):
        r = compute_finish_reward(15, 10)
        assert r == 1.0


class TestComputeTaskQuality:
    def test_perfect_success(self):
        r = compute_task_quality(1.0, 1.0)
        assert r == 1.0

    def test_zero_success(self):
        r = compute_task_quality(0.9, 0.0)
        assert r == 0.0

    def test_partial(self):
        r = compute_task_quality(0.8, 0.5)
        assert abs(r - 0.4) < 1e-6

    def test_clamped_above_one(self):
        r = compute_task_quality(2.0, 1.0)
        assert r == 1.0

    def test_clamped_below_zero(self):
        r = compute_task_quality(-0.5, 1.0)
        assert r == 0.0


# ===========================================================================
# 2. LambdaScheduler tests
# ===========================================================================

class TestLambdaScheduler:
    def test_linear_start(self):
        s = LambdaScheduler(lambda1_init=0.1, lambda1_final=0.0, total_training_steps=100)
        assert abs(s.lambda1(0) - 0.1) < 1e-6

    def test_linear_end(self):
        s = LambdaScheduler(lambda1_init=0.1, lambda1_final=0.0, total_training_steps=100)
        assert abs(s.lambda1(100) - 0.0) < 1e-6

    def test_linear_midpoint(self):
        s = LambdaScheduler(lambda1_init=0.1, lambda1_final=0.0, total_training_steps=100)
        assert abs(s.lambda1(50) - 0.05) < 1e-6

    def test_cosine_schedule(self):
        s = LambdaScheduler(
            lambda1_init=0.1, lambda1_final=0.0,
            total_training_steps=100, schedule="cosine"
        )
        mid = s.lambda1(50)
        assert 0.0 < mid < 0.1  # should be between final and init

    def test_exponential_schedule(self):
        s = LambdaScheduler(
            lambda1_init=0.1, lambda1_final=0.001,
            total_training_steps=100, schedule="exponential"
        )
        assert s.lambda1(0) > s.lambda1(50) > s.lambda1(100)

    def test_invalid_schedule_raises(self):
        with pytest.raises(ValueError):
            LambdaScheduler(schedule="invalid")

    def test_lambda2_independent(self):
        s = LambdaScheduler(
            lambda1_init=0.2, lambda1_final=0.0,
            lambda2_init=0.05, lambda2_final=0.0,
            total_training_steps=100,
        )
        assert abs(s.lambda1(0) - 0.2) < 1e-6
        assert abs(s.lambda2(0) - 0.05) < 1e-6

    def test_beyond_total_steps_clamped(self):
        s = LambdaScheduler(lambda1_init=0.1, lambda1_final=0.0, total_training_steps=100)
        assert s.lambda1(9999) == 0.0


# ===========================================================================
# 3. PARLReward tests
# ===========================================================================

class TestPARLReward:
    def test_compute_returns_breakdown(self, reward_fn, episode):
        bd = reward_fn.compute(episode)
        assert isinstance(bd, RewardBreakdown)
        assert bd.total_reward >= 0.0

    def test_total_reward_components(self, reward_fn, episode):
        bd = reward_fn.compute(episode)
        expected = bd.instantiation_component + bd.finish_component + bd.task_component
        assert abs(bd.total_reward - expected) < 1e-6

    def test_lambda_anneals_to_zero(self):
        fn = PARLReward(
            lambda1_init=0.1, lambda1_final=0.0,
            lambda2_init=0.1, lambda2_final=0.0,
            total_training_steps=1000,
        )
        ep = EpisodeData(
            num_subagents=10, assigned_subtasks=10, completed_subtasks=10,
            success=1.0, trajectory_score=0.9, training_step=1000,
        )
        bd = fn.compute(ep)
        assert abs(bd.lambda1) < 1e-6
        assert abs(bd.lambda2) < 1e-6
        # At step 1000, total_reward ≈ r_perf only
        assert abs(bd.total_reward - bd.r_perf) < 1e-5

    def test_batch_compute(self, reward_fn):
        episodes = [
            EpisodeData(num_subagents=i, assigned_subtasks=10, completed_subtasks=i,
                        success=1.0, trajectory_score=0.5, training_step=100)
            for i in range(1, 6)
        ]
        results = reward_fn.compute_batch(episodes)
        assert len(results) == 5
        assert all(isinstance(r, RewardBreakdown) for r in results)

    def test_history_accumulates(self, reward_fn, episode):
        for _ in range(5):
            reward_fn.compute(episode)
        assert len(reward_fn.history) == 5

    def test_mean_reward(self, reward_fn):
        episodes = [
            EpisodeData(num_subagents=5, assigned_subtasks=5, completed_subtasks=5,
                        success=1.0, trajectory_score=0.8, training_step=i)
            for i in range(10)
        ]
        reward_fn.compute_batch(episodes)
        mean = reward_fn.mean_reward()
        assert 0.0 < mean <= 1.0

    def test_mean_reward_last_n(self, reward_fn, episode):
        for _ in range(20):
            reward_fn.compute(episode)
        mean_all = reward_fn.mean_reward()
        mean_5 = reward_fn.mean_reward(last_n=5)
        assert abs(mean_all - mean_5) < 0.5  # both should be similar for same episode

    def test_clear_history(self, reward_fn, episode):
        reward_fn.compute(episode)
        reward_fn.clear_history()
        assert len(reward_fn.history) == 0

    def test_zero_subagents_episode(self, reward_fn):
        ep = EpisodeData(
            num_subagents=0, assigned_subtasks=0, completed_subtasks=0,
            success=0.0, trajectory_score=0.0, training_step=0,
        )
        bd = reward_fn.compute(ep)
        # r_parallel=0 (no subagents), r_perf=0 (success=0),
        # r_finish=1.0 (trivially finished: 0/0 = 1.0), lambda2=0.1
        # total = 0 + 0.1*1.0 + 0 = 0.1
        assert bd.r_parallel == 0.0
        assert bd.r_perf == 0.0
        assert bd.total_reward <= 0.15  # dominated by trivial finish bonus only

    def test_perfect_episode(self, reward_fn):
        ep = EpisodeData(
            num_subagents=100, assigned_subtasks=100, completed_subtasks=100,
            success=1.0, trajectory_score=1.0, training_step=0,
        )
        bd = reward_fn.compute(ep)
        assert bd.total_reward > 0.9  # near maximum


# ===========================================================================
# 4. CriticalStepsMetric tests
# ===========================================================================

class TestCriticalStepsMetric:
    def test_single_stage_no_subagents(self):
        m = CriticalStepsMetric()
        result = m.compute([1.0], [[]])
        assert result == 1.0

    def test_single_stage_with_subagents(self):
        m = CriticalStepsMetric()
        result = m.compute([1.0], [[3.0, 5.0, 2.0]])
        # S_main + max_sub = 1 + 5 = 6
        assert result == 6.0

    def test_multi_stage(self):
        m = CriticalStepsMetric()
        result = m.compute(
            [1.0, 1.0, 1.0],
            [[3.0, 2.0], [4.0, 1.0], [2.0, 2.0]]
        )
        # (1+3) + (1+4) + (1+2) = 4 + 5 + 3 = 12
        assert result == 12.0

    def test_mismatched_lengths_raises(self):
        m = CriticalStepsMetric()
        with pytest.raises(ValueError):
            m.compute([1.0, 1.0], [[2.0]])

    def test_parallelism_efficiency_single_agent(self):
        m = CriticalStepsMetric()
        # No subagents → efficiency = 1.0 (no parallelism benefit)
        eff = m.parallelism_efficiency([1.0, 1.0], [[], []])
        assert abs(eff - 1.0) < 1e-6

    def test_parallelism_efficiency_with_subagents(self):
        m = CriticalStepsMetric()
        # 2 stages: main=1, subs=[5,5] each stage
        # critical = (1+5) + (1+5) = 12
        # serial = 1+5+5 + 1+5+5 = 22
        # efficiency = 22/12 ≈ 1.83
        eff = m.parallelism_efficiency([1.0, 1.0], [[5.0, 5.0], [5.0, 5.0]])
        assert eff > 1.0  # parallelism is beneficial

    def test_empty_stages(self):
        m = CriticalStepsMetric()
        result = m.compute([], [])
        assert result == 0.0


# ===========================================================================
# 5. SharedReplayBuffer tests
# ===========================================================================

def _make_experience(agent_type: str = "zero", reward: float = 1.0) -> Experience:
    return Experience(
        agent_id=f"{agent_type}-001",
        agent_type=agent_type,
        state={"obs": "test"},
        action={"cmd": "run"},
        reward=reward,
        next_state={"obs": "done"},
        done=True,
        priority=abs(reward),
    )


class TestSharedReplayBuffer:
    def test_add_and_len(self, replay_buffer):
        replay_buffer.add(_make_experience())
        assert len(replay_buffer) == 1

    def test_add_batch(self, replay_buffer):
        exps = [_make_experience(reward=float(i)) for i in range(5)]
        replay_buffer.add_batch(exps)
        assert len(replay_buffer) == 5

    def test_capacity_eviction(self):
        buf = SharedReplayBuffer(capacity=3)
        for i in range(5):
            buf.add(_make_experience(reward=float(i)))
        assert len(buf) == 3

    def test_sample_uniform(self):
        buf = SharedReplayBuffer(capacity=100, strategy="uniform")
        for i in range(20):
            buf.add(_make_experience(reward=float(i)))
        samples = buf.sample(5)
        assert len(samples) == 5

    def test_sample_priority(self, replay_buffer):
        for i in range(20):
            replay_buffer.add(_make_experience(reward=float(i)))
        samples = replay_buffer.sample(5)
        assert len(samples) == 5

    def test_sample_recency(self):
        buf = SharedReplayBuffer(capacity=100, strategy="recency")
        for i in range(20):
            buf.add(_make_experience(reward=float(i)))
        samples = buf.sample(5)
        assert len(samples) == 5

    def test_sample_empty_buffer(self, replay_buffer):
        samples = replay_buffer.sample(5)
        assert samples == []

    def test_sample_fewer_than_n(self, replay_buffer):
        replay_buffer.add(_make_experience())
        samples = replay_buffer.sample(10)
        assert len(samples) == 1

    def test_sample_by_agent_type(self, replay_buffer):
        for _ in range(5):
            replay_buffer.add(_make_experience("zero"))
        for _ in range(5):
            replay_buffer.add(_make_experience("sigma"))
        zero_samples = replay_buffer.sample_by_type("zero", 3)
        assert all(e.agent_type == "zero" for e in zero_samples)

    def test_update_priority(self, replay_buffer):
        exp = _make_experience(reward=0.5)
        replay_buffer.add(exp)
        result = replay_buffer.update_priority(exp.experience_id, 0.9)
        assert result is True

    def test_update_priority_not_found(self, replay_buffer):
        result = replay_buffer.update_priority("nonexistent-id", 0.9)
        assert result is False

    def test_stats(self, replay_buffer):
        for i in range(10):
            replay_buffer.add(_make_experience("zero", reward=float(i)))
        stats = replay_buffer.stats()
        assert stats.buffer_size == 10
        assert stats.total_stored == 10
        assert "zero" in stats.agent_counts

    def test_thread_safety(self, replay_buffer):
        errors = []

        def writer():
            try:
                for _ in range(50):
                    replay_buffer.add(_make_experience())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert len(replay_buffer) <= 100  # capacity respected

    def test_clear(self, replay_buffer):
        replay_buffer.add(_make_experience())
        replay_buffer.clear()
        assert len(replay_buffer) == 0

    def test_invalid_strategy_raises(self):
        with pytest.raises(ValueError):
            SharedReplayBuffer(strategy="invalid")


# ===========================================================================
# 6. AgentExperienceCollector tests
# ===========================================================================

class TestAgentExperienceCollector:
    def test_record_adds_to_buffer(self, replay_buffer):
        collector = AgentExperienceCollector("zero-001", "zero", replay_buffer)
        collector.record(
            state={"obs": "start"},
            action={"cmd": "fix"},
            reward=0.8,
            next_state={"obs": "done"},
            done=True,
        )
        assert len(replay_buffer) == 1

    def test_episode_count_increments(self, replay_buffer):
        collector = AgentExperienceCollector("zero-001", "zero", replay_buffer)
        collector.record({}, {}, 1.0, {}, done=False)
        assert collector.episode_count == 0
        collector.record({}, {}, 1.0, {}, done=True)
        assert collector.episode_count == 1

    def test_step_count_increments(self, replay_buffer):
        collector = AgentExperienceCollector("zero-001", "zero", replay_buffer)
        for _ in range(5):
            collector.record({}, {}, 1.0, {}, done=False)
        assert collector.step_count == 5

    def test_priority_from_reward(self, replay_buffer):
        collector = AgentExperienceCollector("zero-001", "zero", replay_buffer)
        exp = collector.record({}, {}, 0.9, {}, done=True)
        assert exp.priority >= 0.9


# ===========================================================================
# 7. PolicyStore tests
# ===========================================================================

class TestPolicyStore:
    def test_register_and_get(self, policy_store):
        params = policy_store.get_parameters("zero")
        assert params is not None
        assert "lr" in params

    def test_unregistered_type_returns_none(self, policy_store):
        params = policy_store.get_parameters("unknown_agent")
        assert params is None

    def test_push_and_apply_gradient(self, policy_store):
        policy_store.push_gradient("zero", {"lr": 0.001}, weight=1.0)
        assert policy_store.pending_gradients("zero") == 1
        new_version = policy_store.apply_gradients("zero", learning_rate=0.1, training_step=1)
        assert new_version is not None
        assert policy_store.pending_gradients("zero") == 0

    def test_apply_updates_parameters(self, policy_store):
        original = policy_store.get_parameters("zero")
        policy_store.push_gradient("zero", {"lr": 1.0}, weight=1.0)
        policy_store.apply_gradients("zero", learning_rate=0.1, training_step=1)
        updated = policy_store.get_parameters("zero")
        # lr should have increased: 0.01 + 0.1 * 1.0 = 0.11
        assert updated["lr"] != original["lr"]

    def test_rollback(self, policy_store):
        original_params = policy_store.get_parameters("zero")
        policy_store.push_gradient("zero", {"lr": 100.0}, weight=1.0)
        policy_store.apply_gradients("zero", learning_rate=1.0, training_step=1)
        rolled = policy_store.rollback("zero", steps=1)
        assert rolled is not None
        restored = policy_store.get_parameters("zero")
        assert abs(restored["lr"] - original_params["lr"]) < 1e-6

    def test_rollback_to_best(self, policy_store):
        # Apply a good update
        policy_store.push_gradient("zero", {"lr": 0.001}, weight=1.0)
        policy_store.apply_gradients("zero", learning_rate=0.01, training_step=1, mean_reward=0.9)
        # Apply a bad update
        policy_store.push_gradient("zero", {"lr": -999.0}, weight=1.0)
        policy_store.apply_gradients("zero", learning_rate=1.0, training_step=2, mean_reward=0.1)
        # Rollback to best
        best = policy_store.rollback_to_best("zero")
        assert best is not None
        assert best.mean_reward == 0.9

    def test_registered_types(self, policy_store):
        types = policy_store.registered_types()
        assert "zero" in types
        assert "sigma" in types

    def test_sync_counts(self, policy_store):
        policy_store.get_parameters("zero")
        policy_store.get_parameters("zero")
        counts = policy_store.sync_counts()
        assert counts["zero"] >= 2

    def test_no_gradients_apply_returns_none(self, policy_store):
        result = policy_store.apply_gradients("zero", training_step=99)
        assert result is None

    def test_gradient_accumulator_aggregate(self):
        acc = GradientAccumulator(agent_type="test")
        acc.add({"a": 1.0, "b": 2.0}, weight=1.0)
        acc.add({"a": 3.0, "b": 4.0}, weight=1.0)
        agg = acc.aggregate()
        assert abs(agg["a"] - 2.0) < 1e-6
        assert abs(agg["b"] - 3.0) < 1e-6

    def test_gradient_accumulator_weighted(self):
        acc = GradientAccumulator(agent_type="test")
        acc.add({"x": 0.0}, weight=1.0)
        acc.add({"x": 1.0}, weight=3.0)
        agg = acc.aggregate()
        # weighted avg: (0*1 + 1*3) / 4 = 0.75
        assert abs(agg["x"] - 0.75) < 1e-6

    def test_gradient_accumulator_clear(self):
        acc = GradientAccumulator()
        acc.add({"x": 1.0})
        acc.clear()
        assert len(acc) == 0


# ===========================================================================
# 8. PARLOrchestrator tests
# ===========================================================================

class TestPARLOrchestrator:
    def test_single_subtask(self, orchestrator):
        task = orchestrator.decompose_and_run(
            description="Fix import errors",
            subtask_specs=[
                {"agent_type": AgentType.ZERO, "description": "Fix import errors",
                 "payload": {"errors_to_fix": 3}},
            ],
        )
        assert task is not None
        assert task.completed_count >= 0

    def test_parallel_subtasks(self, orchestrator):
        task = orchestrator.decompose_and_run(
            description="Audit and test",
            subtask_specs=[
                {"agent_type": AgentType.ZERO, "description": "Fix imports"},
                {"agent_type": AgentType.SIGMA, "description": "Run test suite",
                 "payload": {"pass_rate": 0.95}},
                {"agent_type": AgentType.NOVA, "description": "Execute actions",
                 "payload": {"actions_total": 3, "actions_completed": 3}},
                {"agent_type": AgentType.CHAT, "description": "Chat with user"},
            ],
        )
        assert len(task.subtasks) == 4
        assert task.reward_breakdown is not None
        assert task.reward_breakdown.total_reward >= 0.0

    def test_reward_breakdown_populated(self, orchestrator):
        task = orchestrator.decompose_and_run(
            description="Test task",
            subtask_specs=[
                {"agent_type": AgentType.ZERO, "description": "fix errors"},
            ],
        )
        bd = task.reward_breakdown
        assert bd.r_parallel >= 0.0
        assert bd.r_finish >= 0.0
        assert bd.r_perf >= 0.0

    def test_training_step_increments(self, orchestrator):
        initial_step = orchestrator.training_step
        orchestrator.decompose_and_run(
            description="Step test",
            subtask_specs=[{"agent_type": AgentType.ZERO, "description": "fix"}],
        )
        assert orchestrator.training_step == initial_step + 1

    def test_unregistered_agent_fails_gracefully(self, orchestrator):
        task = orchestrator.decompose_and_run(
            description="Unknown agent task",
            subtask_specs=[
                {"agent_type": AgentType.GENERIC, "description": "do something"},
            ],
        )
        # Should complete (with failure) not raise
        assert task is not None
        assert task.failed_count >= 0

    def test_task_history_accumulates(self, orchestrator):
        for _ in range(3):
            orchestrator.decompose_and_run(
                description="History test",
                subtask_specs=[{"agent_type": AgentType.ZERO, "description": "fix"}],
            )
        assert len(orchestrator.task_history) == 3

    def test_buffer_stats(self, orchestrator):
        orchestrator.decompose_and_run(
            description="Buffer test",
            subtask_specs=[
                {"agent_type": AgentType.ZERO, "description": "fix"},
                {"agent_type": AgentType.SIGMA, "description": "test"},
            ],
        )
        stats = orchestrator.buffer_stats()
        assert stats["total_stored"] >= 2

    def test_mean_reward_after_tasks(self, orchestrator):
        for _ in range(5):
            orchestrator.decompose_and_run(
                description="Reward test",
                subtask_specs=[
                    {"agent_type": AgentType.ZERO, "description": "fix",
                     "payload": {"errors_to_fix": 2}},
                ],
            )
        mean = orchestrator.mean_reward()
        assert 0.0 <= mean <= 1.0

    def test_update_policies(self, orchestrator):
        # Run some tasks to accumulate gradients
        for _ in range(3):
            orchestrator.decompose_and_run(
                description="Policy update test",
                subtask_specs=[
                    {"agent_type": AgentType.ZERO, "description": "fix imports"},
                ],
            )
        results = orchestrator.update_policies(learning_rate=0.01)
        # Should return dict for each registered agent type
        assert isinstance(results, dict)


# ===========================================================================
# 9. Agent adapter tests
# ===========================================================================

class TestZeroPARLAdapter:
    def test_basic_execution(self):
        adapter = ZeroPARLAdapter()
        subtask = Subtask(
            description="Fix import errors",
            payload={"errors_to_fix": 2},
        )
        result, score = adapter(subtask)
        assert isinstance(result, dict)
        assert 0.0 <= score <= 1.0

    def test_score_improves_with_more_fixes(self):
        adapter = ZeroPARLAdapter()
        s1 = Subtask(description="Fix imports", payload={"errors_to_fix": 1})
        s2 = Subtask(description="Fix imports", payload={"errors_to_fix": 5})
        _, score1 = adapter(s1)
        _, score2 = adapter(s2)
        assert score2 >= score1

    def test_success_rate_tracking(self):
        adapter = ZeroPARLAdapter()
        for _ in range(3):
            adapter(Subtask(description="fix", payload={}))
        assert adapter.success_rate == 1.0


class TestSigmaPARLAdapter:
    def test_high_pass_rate_high_score(self):
        adapter = SigmaPARLAdapter()
        subtask = Subtask(
            description="Run test suite",
            payload={"pass_rate": 0.98},
        )
        _, score = adapter(subtask)
        assert score >= 0.9

    def test_security_issues_reduce_score(self):
        adapter = SigmaPARLAdapter()
        s_clean = Subtask(description="security scan", payload={"security_issues": 0})
        s_issues = Subtask(description="security scan", payload={"security_issues": 5})
        _, score_clean = adapter(s_clean)
        _, score_issues = adapter(s_issues)
        assert score_clean >= score_issues


class TestNovaPARLAdapter:
    def test_full_completion_high_score(self):
        adapter = NovaPARLAdapter()
        subtask = Subtask(
            description="Execute actions",
            payload={"actions_total": 5, "actions_completed": 5, "approval_level": "AUTO"},
        )
        _, score = adapter(subtask)
        assert score >= 0.85

    def test_partial_completion_lower_score(self):
        adapter = NovaPARLAdapter()
        s_full = Subtask(description="execute", payload={"actions_total": 5, "actions_completed": 5})
        s_partial = Subtask(description="execute", payload={"actions_total": 5, "actions_completed": 2})
        _, score_full = adapter(s_full)
        _, score_partial = adapter(s_partial)
        assert score_full > score_partial


class TestChatPARLAdapter:
    def test_conversation_intent_high_score(self):
        adapter = ChatPARLAdapter()
        subtask = Subtask(description="Chat and respond to user query")
        _, score = adapter(subtask)
        assert score >= 0.85

    def test_delegation_to_zero(self):
        adapter = ChatPARLAdapter()
        subtask = Subtask(description="Fix the broken import error")
        result, _ = adapter(subtask)
        assert result["delegated_to"] == "zero"

    def test_delegation_to_sigma(self):
        adapter = ChatPARLAdapter()
        subtask = Subtask(description="Run the test suite and check coverage")
        result, _ = adapter(subtask)
        assert result["delegated_to"] == "sigma"

    def test_delegation_to_nova(self):
        adapter = ChatPARLAdapter()
        subtask = Subtask(description="Execute the action and dispatch file")
        result, _ = adapter(subtask)
        assert result["delegated_to"] == "nova"

    def test_memory_hits_boost_score(self):
        adapter = ChatPARLAdapter()
        s_no_mem = Subtask(description="chat", payload={"memory_hits": 0})
        s_with_mem = Subtask(description="chat", payload={"memory_hits": 10})
        _, score_no_mem = adapter(s_no_mem)
        _, score_with_mem = adapter(s_with_mem)
        assert score_with_mem >= score_no_mem


class TestCreateAdapter:
    def test_create_zero(self):
        adapter = create_adapter("zero")
        assert isinstance(adapter, ZeroPARLAdapter)

    def test_create_sigma(self):
        adapter = create_adapter("sigma")
        assert isinstance(adapter, SigmaPARLAdapter)

    def test_create_nova(self):
        adapter = create_adapter("nova")
        assert isinstance(adapter, NovaPARLAdapter)

    def test_create_chat(self):
        adapter = create_adapter("chat")
        assert isinstance(adapter, ChatPARLAdapter)

    def test_create_unknown_raises(self):
        with pytest.raises(ValueError):
            create_adapter("unknown_agent_type")

    def test_create_with_policy_store(self, policy_store):
        adapter = create_adapter("zero", policy_store=policy_store)
        assert adapter.policy_store is policy_store


# ===========================================================================
# 10. Integration test — full PARL loop
# ===========================================================================

class TestPARLFullLoop:
    def test_end_to_end_reward_loop(self):
        """Full PARL loop: register agents → run tasks → update policies → verify rewards."""
        orch = PARLOrchestrator(
            max_workers=4,
            total_training_steps=100,
            max_subagents=10,
        )
        orch.register_agent(AgentType.ZERO, ZeroPARLAdapter(policy_store=orch.policy_store))
        orch.register_agent(AgentType.SIGMA, SigmaPARLAdapter(policy_store=orch.policy_store))
        orch.register_agent(AgentType.NOVA, NovaPARLAdapter(policy_store=orch.policy_store))
        orch.register_agent(AgentType.CHAT, ChatPARLAdapter(policy_store=orch.policy_store))

        rewards = []
        for step in range(5):
            task = orch.decompose_and_run(
                description=f"Full loop task {step}",
                subtask_specs=[
                    {"agent_type": AgentType.ZERO, "description": "fix imports",
                     "payload": {"errors_to_fix": 2}},
                    {"agent_type": AgentType.SIGMA, "description": "run tests",
                     "payload": {"pass_rate": 0.95}},
                    {"agent_type": AgentType.NOVA, "description": "execute actions",
                     "payload": {"actions_total": 3, "actions_completed": 3}},
                    {"agent_type": AgentType.CHAT, "description": "chat with user"},
                ],
                training_step=step * 10,
            )
            rewards.append(task.reward_breakdown.total_reward)
            orch.update_policies(learning_rate=0.01)

        assert len(rewards) == 5
        assert all(r >= 0.0 for r in rewards)
        # Buffer should have experiences from all agents
        stats = orch.buffer_stats()
        assert stats["total_stored"] >= 20  # 4 agents × 5 tasks

    def test_lambda_annealing_reduces_parallel_reward(self):
        """Verify that λ1·r_parallel decreases as training progresses."""
        fn = PARLReward(
            lambda1_init=0.1, lambda1_final=0.0,
            lambda2_init=0.1, lambda2_final=0.0,
            total_training_steps=1000,
        )
        ep_early = EpisodeData(
            num_subagents=50, assigned_subtasks=50, completed_subtasks=50,
            success=1.0, trajectory_score=0.9, training_step=0,
        )
        ep_late = EpisodeData(
            num_subagents=50, assigned_subtasks=50, completed_subtasks=50,
            success=1.0, trajectory_score=0.9, training_step=1000,
        )
        bd_early = fn.compute(ep_early)
        bd_late = fn.compute(ep_late)
        assert bd_early.instantiation_component > bd_late.instantiation_component
        assert bd_early.finish_component > bd_late.finish_component

    def test_critical_steps_less_than_serial(self):
        """Parallel execution should reduce critical steps vs serial."""
        m = CriticalStepsMetric()
        # 3 stages, each with 4 subagents taking 5 steps each
        main_steps = [1.0, 1.0, 1.0]
        sub_steps = [[5.0, 5.0, 5.0, 5.0]] * 3

        critical = m.compute(main_steps, sub_steps)
        serial = sum(main_steps) + sum(sum(s) for s in sub_steps)

        # Critical = (1+5)+(1+5)+(1+5) = 18
        # Serial = 3 + 60 = 63
        assert critical < serial
        assert m.parallelism_efficiency(main_steps, sub_steps) > 1.0

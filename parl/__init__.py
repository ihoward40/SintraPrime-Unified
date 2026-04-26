"""
PARL — Parallel-Agent Reinforcement Learning for SintraPrime.

Implements the Kimi K2.5 PARL training paradigm:

    r_PARL(x, y) = λ1·r_parallel + λ2·r_finish + r_perf(x, y)

Key components:
- PARLReward          : Three-term reward function with λ1/λ2 annealing
- CriticalStepsMetric : Latency-oriented evaluation (critical path)
- SharedReplayBuffer  : Multi-agent shared experience replay
- PolicyStore         : Centralised parameter server (CTDE pattern)
- PARLOrchestrator    : Task decomposition + parallel subagent execution

Quick start::

    from parl import PARLOrchestrator, AgentType

    orch = PARLOrchestrator(max_workers=4)
    orch.register_agent(AgentType.ZERO, my_zero_fn)
    orch.register_agent(AgentType.SIGMA, my_sigma_fn)

    task = orch.decompose_and_run(
        description="Audit and test the codebase",
        subtask_specs=[
            {"agent_type": AgentType.ZERO, "description": "Fix import errors"},
            {"agent_type": AgentType.SIGMA, "description": "Run test suite"},
        ],
    )
    print(f"PARL reward: {task.reward_breakdown.total_reward:.4f}")
"""

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
    ReplayStats,
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
    SubagentRunner,
)

__version__ = "1.0.0"
__author__ = "SintraPrime"
__license__ = "Apache-2.0"

__all__ = [
    # Reward engine
    "PARLReward",
    "CriticalStepsMetric",
    "LambdaScheduler",
    "EpisodeData",
    "RewardBreakdown",
    "compute_instantiation_reward",
    "compute_finish_reward",
    "compute_task_quality",
    # Experience replay
    "SharedReplayBuffer",
    "AgentExperienceCollector",
    "Experience",
    "ReplayStats",
    # Policy sync
    "PolicyStore",
    "PolicyVersion",
    "GradientAccumulator",
    # Orchestrator
    "PARLOrchestrator",
    "AgentType",
    "Task",
    "Subtask",
    "SubtaskStatus",
    "SubagentRunner",
]

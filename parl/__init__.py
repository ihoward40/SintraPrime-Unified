"""
PARL — Parallel-Agent Reinforcement Learning for SintraPrime.

Adds governed Principal Command, OmniBrain context injection, read-only GOD-0
Mission Control snapshots, and bounded GOD-1 swarm planning on top of the
existing PARL coordinator.
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
from parl.experience_replay import SharedReplayBuffer, AgentExperienceCollector, Experience, ReplayStats
from parl.policy_sync import PolicyStore, PolicyVersion, GradientAccumulator
from parl.orchestrator import PARLOrchestrator, AgentType, Task, Subtask, SubtaskStatus, SubagentRunner
from parl.god_mode import ActionRisk, GodModeTier, PolicyDecision, PrincipalCommandPolicy, PrincipalSession
from parl.governed_orchestrator import GovernedPARLOrchestrator
from parl.principal_brief import PrincipalBrief, PrincipalBriefService
from parl.swarms import GodOneSwarmPlanner, SwarmMode, SwarmPlan

__version__ = "1.2.0"
__author__ = "SintraPrime"
__license__ = "Apache-2.0"

__all__ = [
    "PARLReward",
    "CriticalStepsMetric",
    "LambdaScheduler",
    "EpisodeData",
    "RewardBreakdown",
    "compute_instantiation_reward",
    "compute_finish_reward",
    "compute_task_quality",
    "SharedReplayBuffer",
    "AgentExperienceCollector",
    "Experience",
    "ReplayStats",
    "PolicyStore",
    "PolicyVersion",
    "GradientAccumulator",
    "PARLOrchestrator",
    "GovernedPARLOrchestrator",
    "AgentType",
    "Task",
    "Subtask",
    "SubtaskStatus",
    "SubagentRunner",
    "ActionRisk",
    "GodModeTier",
    "PolicyDecision",
    "PrincipalCommandPolicy",
    "PrincipalSession",
    "PrincipalBrief",
    "PrincipalBriefService",
    "SwarmMode",
    "SwarmPlan",
    "GodOneSwarmPlanner",
]

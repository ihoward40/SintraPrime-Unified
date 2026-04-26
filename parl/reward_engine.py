"""
PARL Reward Engine — Pure-Python implementation of the Kimi K2.5 PARL reward.

Implements the three-term reward function:

    r_PARL(x, y) = λ1·r_parallel + λ2·r_finish + r_perf(x, y)

where:
- r_parallel  : instantiation reward — incentivises subagent creation (mitigates serial collapse)
- r_finish    : sub-agent finish rate — rewards completed subtasks (prevents spurious parallelism)
- r_perf(x,y) : task-level outcome — evaluates overall success and solution quality
- λ1, λ2      : annealed to zero over training so the final policy optimises r_perf

Critical Steps metric (latency-oriented evaluation):

    CriticalSteps = Σ_t (S_main^(t) + max_i S_sub,i^(t))

This module is PyTorch-free (pure Python + math) so it runs in any SintraPrime environment.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class EpisodeData:
    """Snapshot of one training episode for reward computation."""
    episode_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    num_subagents: int = 0
    assigned_subtasks: int = 0
    completed_subtasks: int = 0
    success: float = 0.0          # 0.0 = failure, 1.0 = success
    trajectory_score: float = 0.0  # quality signal in [0, 1]
    training_step: int = 0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class RewardBreakdown:
    """Full breakdown of a PARL reward computation."""
    episode_id: str
    total_reward: float
    r_parallel: float
    r_finish: float
    r_perf: float
    lambda1: float
    lambda2: float
    instantiation_component: float   # λ1 * r_parallel
    finish_component: float          # λ2 * r_finish
    task_component: float            # r_perf
    training_step: int
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict:
        return {
            "episode_id": self.episode_id,
            "total_reward": round(self.total_reward, 6),
            "r_parallel": round(self.r_parallel, 6),
            "r_finish": round(self.r_finish, 6),
            "r_perf": round(self.r_perf, 6),
            "lambda1": round(self.lambda1, 6),
            "lambda2": round(self.lambda2, 6),
            "instantiation_component": round(self.instantiation_component, 6),
            "finish_component": round(self.finish_component, 6),
            "task_component": round(self.task_component, 6),
            "training_step": self.training_step,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Lambda annealing
# ---------------------------------------------------------------------------

class LambdaScheduler:
    """
    Anneals λ1 and λ2 from their initial values to zero (or a final value)
    over the course of training.

    Supports three schedules:
    - 'linear'      : λ decreases linearly from init → final
    - 'cosine'      : λ follows a cosine decay curve
    - 'exponential' : λ decays exponentially
    """

    SCHEDULES = ("linear", "cosine", "exponential")

    def __init__(
        self,
        lambda1_init: float = 0.1,
        lambda1_final: float = 0.0,
        lambda2_init: float = 0.1,
        lambda2_final: float = 0.0,
        total_training_steps: int = 10_000,
        schedule: str = "linear",
    ):
        if schedule not in self.SCHEDULES:
            raise ValueError(f"schedule must be one of {self.SCHEDULES}")
        self.lambda1_init = lambda1_init
        self.lambda1_final = lambda1_final
        self.lambda2_init = lambda2_init
        self.lambda2_final = lambda2_final
        self.total_training_steps = max(1, total_training_steps)
        self.schedule = schedule

    def _anneal(self, init: float, final: float, step: int) -> float:
        progress = min(1.0, max(0.0, step / self.total_training_steps))
        if self.schedule == "linear":
            return init + (final - init) * progress
        elif self.schedule == "cosine":
            return final + (init - final) * 0.5 * (1.0 + math.cos(math.pi * progress))
        else:  # exponential
            if init == 0.0:
                return 0.0
            decay = math.exp(math.log(max(final, 1e-10) / max(init, 1e-10)) * progress)
            return init * decay

    def lambda1(self, step: int) -> float:
        return self._anneal(self.lambda1_init, self.lambda1_final, step)

    def lambda2(self, step: int) -> float:
        return self._anneal(self.lambda2_init, self.lambda2_final, step)


# ---------------------------------------------------------------------------
# Core reward components
# ---------------------------------------------------------------------------

def compute_instantiation_reward(
    num_subagents: int, max_subagents: int = 100
) -> float:
    """
    r_parallel: incentivises subagent creation and concurrent execution.

    Normalised count of spawned subagents. Mitigates serial collapse by
    rewarding the orchestrator for actually using parallel capacity.
    """
    if max_subagents <= 0:
        return 0.0
    return min(1.0, max(0.0, num_subagents / max_subagents))


def compute_finish_reward(
    completed_subtasks: int, assigned_subtasks: int, eps: float = 1e-8
) -> float:
    """
    r_finish: sub-agent finish rate.

    Prevents spurious parallelism — spawning many subagents without
    meaningful task decomposition. Rewards the fraction of assigned
    subtasks that were actually completed.
    """
    if assigned_subtasks <= 0:
        return 1.0  # no subtasks assigned → trivially finished
    return min(1.0, max(0.0, completed_subtasks / (assigned_subtasks + eps)))


def compute_task_quality(
    trajectory_score: float, success: float
) -> float:
    """
    r_perf: task-level outcome.

    Combines a trajectory quality signal (in [0, 1]) with a binary or
    continuous success indicator. This is the primary objective that
    dominates once λ1 and λ2 have annealed to zero.
    """
    quality = max(0.0, min(1.0, trajectory_score))
    success_weight = max(0.0, min(1.0, success))
    return quality * success_weight


# ---------------------------------------------------------------------------
# PARLReward — main reward engine
# ---------------------------------------------------------------------------

class PARLReward:
    """
    Parallel-Agent Reinforcement Learning Reward Function.

    Implements the three-term PARL reward from the Kimi K2.5 technical report:

        r_PARL(x, y) = λ1·r_parallel + λ2·r_finish + r_perf(x, y)

    Usage::

        reward_fn = PARLReward(total_training_steps=10_000)
        ep = EpisodeData(
            num_subagents=25,
            assigned_subtasks=25,
            completed_subtasks=20,
            success=1.0,
            trajectory_score=0.85,
            training_step=5000,
        )
        breakdown = reward_fn.compute(ep)
        print(breakdown.total_reward)
    """

    def __init__(
        self,
        lambda1_init: float = 0.1,
        lambda1_final: float = 0.0,
        lambda2_init: float = 0.1,
        lambda2_final: float = 0.0,
        total_training_steps: int = 10_000,
        max_subagents: int = 100,
        schedule: str = "linear",
    ):
        self.scheduler = LambdaScheduler(
            lambda1_init=lambda1_init,
            lambda1_final=lambda1_final,
            lambda2_init=lambda2_init,
            lambda2_final=lambda2_final,
            total_training_steps=total_training_steps,
            schedule=schedule,
        )
        self.max_subagents = max_subagents
        self._history: List[RewardBreakdown] = []

    # ------------------------------------------------------------------
    # Core computation
    # ------------------------------------------------------------------

    def compute(self, episode: EpisodeData) -> RewardBreakdown:
        """Compute the full PARL reward for a single episode."""
        lam1 = self.scheduler.lambda1(episode.training_step)
        lam2 = self.scheduler.lambda2(episode.training_step)

        r_parallel = compute_instantiation_reward(
            episode.num_subagents, self.max_subagents
        )
        r_finish = compute_finish_reward(
            episode.completed_subtasks, episode.assigned_subtasks
        )
        r_perf = compute_task_quality(episode.trajectory_score, episode.success)

        total = lam1 * r_parallel + lam2 * r_finish + r_perf

        breakdown = RewardBreakdown(
            episode_id=episode.episode_id,
            total_reward=total,
            r_parallel=r_parallel,
            r_finish=r_finish,
            r_perf=r_perf,
            lambda1=lam1,
            lambda2=lam2,
            instantiation_component=lam1 * r_parallel,
            finish_component=lam2 * r_finish,
            task_component=r_perf,
            training_step=episode.training_step,
        )
        self._history.append(breakdown)
        return breakdown

    def compute_batch(self, episodes: List[EpisodeData]) -> List[RewardBreakdown]:
        """Compute rewards for a batch of episodes."""
        return [self.compute(ep) for ep in episodes]

    # ------------------------------------------------------------------
    # History / statistics
    # ------------------------------------------------------------------

    def mean_reward(self, last_n: Optional[int] = None) -> float:
        """Mean total reward over history (or last N episodes)."""
        history = self._history[-last_n:] if last_n else self._history
        if not history:
            return 0.0
        return sum(b.total_reward for b in history) / len(history)

    def clear_history(self) -> None:
        self._history.clear()

    @property
    def history(self) -> List[RewardBreakdown]:
        return list(self._history)


# ---------------------------------------------------------------------------
# CriticalStepsMetric
# ---------------------------------------------------------------------------

class CriticalStepsMetric:
    """
    Latency-oriented evaluation metric from the PARL paper.

    CriticalSteps = Σ_t (S_main^(t) + max_i S_sub,i^(t))

    - S_main^(t)    : steps taken by the main orchestrator agent in stage t (typically 1)
    - S_sub,i^(t)   : steps taken by the i-th subagent in stage t
    - The duration of stage t is governed by the longest-running subagent (critical path)

    Lower critical steps = better parallelism efficiency.
    """

    def __init__(self, orchestration_overhead: float = 0.1):
        self.orchestration_overhead = orchestration_overhead

    def compute(
        self,
        main_steps_per_stage: Sequence[float],
        sub_steps_per_stage: Sequence[Sequence[float]],
    ) -> float:
        """
        Compute total critical steps.

        Args:
            main_steps_per_stage: Steps taken by the main agent per stage.
                                  Typically [1, 1, 1, ...].
            sub_steps_per_stage:  For each stage, a list of step counts for
                                  each subagent. Empty list means no subagents.

        Returns:
            Total critical steps (float). Lower is better.
        """
        if len(main_steps_per_stage) != len(sub_steps_per_stage):
            raise ValueError(
                "main_steps_per_stage and sub_steps_per_stage must have the same length"
            )

        total = 0.0
        for s_main, sub_steps in zip(main_steps_per_stage, sub_steps_per_stage):
            max_sub = max(sub_steps) if sub_steps else 0.0
            total += s_main + max_sub

        return total

    def parallelism_efficiency(
        self,
        main_steps_per_stage: Sequence[float],
        sub_steps_per_stage: Sequence[Sequence[float]],
    ) -> float:
        """
        Ratio of serial steps to critical steps.

        efficiency = serial_steps / critical_steps

        A value close to 1.0 means little parallelism benefit.
        A value > 1.0 means parallelism reduced total latency.
        """
        critical = self.compute(main_steps_per_stage, sub_steps_per_stage)
        if critical == 0:
            return 1.0

        # Serial steps = sum of all steps (main + all sub)
        serial = sum(main_steps_per_stage)
        for sub_steps in sub_steps_per_stage:
            serial += sum(sub_steps)

        return serial / critical if critical > 0 else 1.0

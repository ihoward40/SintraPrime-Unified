"""
PARL Orchestrator — Central coordinator for the SintraPrime parallel agent swarm.

The Orchestrator implements the trainable central coordinator from the PARL paper:
- Decomposes complex tasks into parallel subtasks
- Spawns and manages subagent instances (Zero, Sigma, Nova, Chat)
- Tracks execution progress and computes PARL rewards
- Feeds experience into the shared replay buffer
- Synchronises policy updates across the swarm

Architecture (per PARL paper):

    ┌─────────────────────────────────────────────┐
    │         Orchestrator Agent                  │
    │  (Trainable Central Coordinator)            │
    │  - Decomposes tasks into subtasks           │
    │  - Manages parallel execution               │
    │  - Coordinates subagent workflows           │
    └──────────────┬──────────────────────────────┘
                   │
                   ├──────────┬──────────┬─────────┐
                   │          │          │         │
              ┌────▼───┐ ┌───▼────┐ ┌──▼────┐  ┌─▼──────┐
              │Subagent│ │Subagent│ │Subagent│  │Subagent│
              │  Zero  │ │ Sigma  │ │  Nova  │  │  Chat  │
              └────────┘ └────────┘ └────────┘  └────────┘
"""

from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from parl.reward_engine import PARLReward, EpisodeData, RewardBreakdown
from parl.experience_replay import SharedReplayBuffer, AgentExperienceCollector, Experience
from parl.policy_sync import PolicyStore


# ---------------------------------------------------------------------------
# Enums and data models
# ---------------------------------------------------------------------------

class SubtaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentType(str, Enum):
    ZERO = "zero"
    SIGMA = "sigma"
    NOVA = "nova"
    CHAT = "chat"
    GENERIC = "generic"


@dataclass
class Subtask:
    """A single unit of work assigned to one subagent."""
    subtask_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""
    agent_type: AgentType = AgentType.GENERIC
    description: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    status: SubtaskStatus = SubtaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    steps_taken: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    reward: float = 0.0

    def mark_started(self) -> None:
        self.status = SubtaskStatus.RUNNING
        self.started_at = datetime.now(timezone.utc).isoformat()

    def mark_completed(self, result: Any, steps: int = 1) -> None:
        self.status = SubtaskStatus.COMPLETED
        self.result = result
        self.steps_taken = steps
        self.completed_at = datetime.now(timezone.utc).isoformat()

    def mark_failed(self, error: str) -> None:
        self.status = SubtaskStatus.FAILED
        self.error = error
        self.completed_at = datetime.now(timezone.utc).isoformat()


@dataclass
class Task:
    """A complex task decomposed into parallel subtasks."""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    subtasks: List[Subtask] = field(default_factory=list)
    status: SubtaskStatus = SubtaskStatus.PENDING
    reward_breakdown: Optional[RewardBreakdown] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    completed_at: Optional[str] = None
    training_step: int = 0

    @property
    def completed_count(self) -> int:
        return sum(1 for s in self.subtasks if s.status == SubtaskStatus.COMPLETED)

    @property
    def failed_count(self) -> int:
        return sum(1 for s in self.subtasks if s.status == SubtaskStatus.FAILED)

    @property
    def success_rate(self) -> float:
        if not self.subtasks:
            return 0.0
        return self.completed_count / len(self.subtasks)

    @property
    def is_done(self) -> bool:
        return all(
            s.status in (SubtaskStatus.COMPLETED, SubtaskStatus.FAILED, SubtaskStatus.CANCELLED)
            for s in self.subtasks
        )


# ---------------------------------------------------------------------------
# SubagentRunner — executes a single subtask
# ---------------------------------------------------------------------------

SubagentFn = Callable[[Subtask], Tuple[Any, float]]  # (result, trajectory_score)


class SubagentRunner:
    """
    Wraps a callable agent function and executes subtasks, recording
    experiences into the shared replay buffer.
    """

    def __init__(
        self,
        agent_id: str,
        agent_type: AgentType,
        agent_fn: SubagentFn,
        collector: AgentExperienceCollector,
    ):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.agent_fn = agent_fn
        self.collector = collector

    def run(self, subtask: Subtask) -> Subtask:
        """Execute a subtask and record the experience."""
        subtask.mark_started()
        state = {
            "task_id": subtask.task_id,
            "description": subtask.description,
            "payload": subtask.payload,
        }
        try:
            result, trajectory_score = self.agent_fn(subtask)
            subtask.mark_completed(result, steps=1)
            reward = trajectory_score
            subtask.reward = reward
            next_state = {"result": str(result)[:200], "success": True}
            self.collector.record(
                state=state,
                action={"subtask_id": subtask.subtask_id, "agent_type": self.agent_type.value},
                reward=reward,
                next_state=next_state,
                done=True,
                episode_id=subtask.task_id,
            )
        except Exception as exc:
            subtask.mark_failed(str(exc))
            self.collector.record(
                state=state,
                action={"subtask_id": subtask.subtask_id, "agent_type": self.agent_type.value},
                reward=-0.5,
                next_state={"error": str(exc), "success": False},
                done=True,
                episode_id=subtask.task_id,
            )
        return subtask


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class PARLOrchestrator:
    """
    Central PARL orchestrator for SintraPrime.

    Decomposes tasks, spawns parallel subagents, computes PARL rewards,
    and synchronises policy updates across the swarm.

    Usage::

        orchestrator = PARLOrchestrator(max_workers=8)

        # Register agent handlers
        orchestrator.register_agent(AgentType.ZERO, my_zero_fn)
        orchestrator.register_agent(AgentType.SIGMA, my_sigma_fn)

        # Execute a task
        task = orchestrator.decompose_and_run(
            description="Audit codebase and run tests",
            subtask_specs=[
                {"agent_type": AgentType.ZERO, "description": "Fix import errors"},
                {"agent_type": AgentType.SIGMA, "description": "Run test suite"},
            ]
        )
        print(task.reward_breakdown.total_reward)
    """

    def __init__(
        self,
        max_workers: int = 8,
        buffer_capacity: int = 10_000,
        total_training_steps: int = 10_000,
        max_subagents: int = 100,
        reward_schedule: str = "linear",
    ):
        self.max_workers = max_workers
        self._training_step = 0
        self._task_history: List[Task] = []
        self._lock = threading.Lock()

        # PARL components
        self.reward_fn = PARLReward(
            total_training_steps=total_training_steps,
            max_subagents=max_subagents,
            schedule=reward_schedule,
        )
        self.replay_buffer = SharedReplayBuffer(
            capacity=buffer_capacity,
            strategy="priority",
        )
        self.policy_store = PolicyStore()

        # Agent registry: agent_type → (agent_fn, runner)
        self._agent_registry: Dict[AgentType, SubagentRunner] = {}
        self._collectors: Dict[AgentType, AgentExperienceCollector] = {}

    # ------------------------------------------------------------------
    # Agent registration
    # ------------------------------------------------------------------

    def register_agent(
        self,
        agent_type: AgentType,
        agent_fn: SubagentFn,
        initial_parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register an agent handler for a given agent type."""
        agent_id = f"{agent_type.value}-{str(uuid.uuid4())[:8]}"
        collector = AgentExperienceCollector(
            agent_id=agent_id,
            agent_type=agent_type.value,
            shared_buffer=self.replay_buffer,
        )
        runner = SubagentRunner(
            agent_id=agent_id,
            agent_type=agent_type,
            agent_fn=agent_fn,
            collector=collector,
        )
        self._agent_registry[agent_type] = runner
        self._collectors[agent_type] = collector
        self.policy_store.register_agent_type(
            agent_type.value, initial_parameters or {}
        )

    # ------------------------------------------------------------------
    # Task decomposition and execution
    # ------------------------------------------------------------------

    def decompose_and_run(
        self,
        description: str,
        subtask_specs: List[Dict[str, Any]],
        training_step: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> Task:
        """
        Decompose a task into subtasks and execute them in parallel.

        Args:
            description:    High-level task description.
            subtask_specs:  List of dicts with keys:
                            - agent_type (AgentType)
                            - description (str)
                            - payload (dict, optional)
            training_step:  Override the current training step.
            timeout:        Per-subtask timeout in seconds.

        Returns:
            Completed Task with PARL reward breakdown.
        """
        with self._lock:
            step = training_step if training_step is not None else self._training_step
            self._training_step = step + 1

        task = Task(
            description=description,
            training_step=step,
        )

        # Build subtasks
        for spec in subtask_specs:
            subtask = Subtask(
                task_id=task.task_id,
                agent_type=spec.get("agent_type", AgentType.GENERIC),
                description=spec.get("description", ""),
                payload=spec.get("payload", {}),
            )
            task.subtasks.append(subtask)

        task.status = SubtaskStatus.RUNNING

        # Execute subtasks in parallel
        self._execute_parallel(task, timeout=timeout)

        # Compute PARL reward
        task.reward_breakdown = self._compute_task_reward(task)
        task.status = (
            SubtaskStatus.COMPLETED if task.failed_count == 0 else SubtaskStatus.FAILED
        )
        task.completed_at = datetime.now(timezone.utc).isoformat()

        with self._lock:
            self._task_history.append(task)

        return task

    def _execute_parallel(self, task: Task, timeout: Optional[float] = None) -> None:
        """Execute all subtasks in parallel using a thread pool."""
        futures: Dict[Future, Subtask] = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for subtask in task.subtasks:
                runner = self._agent_registry.get(subtask.agent_type)
                if runner is None:
                    # No handler registered — mark as failed
                    subtask.mark_failed(
                        f"No agent registered for type: {subtask.agent_type.value}"
                    )
                    continue
                future = executor.submit(runner.run, subtask)
                futures[future] = subtask

            for future in as_completed(futures, timeout=timeout):
                subtask = futures[future]
                try:
                    future.result()
                except Exception as exc:
                    if subtask.status != SubtaskStatus.FAILED:
                        subtask.mark_failed(str(exc))

    def _compute_task_reward(self, task: Task) -> RewardBreakdown:
        """Compute the PARL reward for a completed task."""
        num_subagents = len(task.subtasks)
        assigned = num_subagents
        completed = task.completed_count

        # trajectory_score = mean reward across completed subtasks
        completed_subtasks = [s for s in task.subtasks if s.status == SubtaskStatus.COMPLETED]
        trajectory_score = (
            sum(s.reward for s in completed_subtasks) / len(completed_subtasks)
            if completed_subtasks else 0.0
        )
        trajectory_score = max(0.0, min(1.0, trajectory_score))

        success = 1.0 if task.failed_count == 0 and completed > 0 else (
            completed / assigned if assigned > 0 else 0.0
        )

        episode = EpisodeData(
            episode_id=task.task_id,
            num_subagents=num_subagents,
            assigned_subtasks=assigned,
            completed_subtasks=completed,
            success=success,
            trajectory_score=trajectory_score,
            training_step=task.training_step,
        )
        return self.reward_fn.compute(episode)

    # ------------------------------------------------------------------
    # Policy update
    # ------------------------------------------------------------------

    def update_policies(
        self,
        learning_rate: float = 0.01,
    ) -> Dict[str, Any]:
        """
        Apply accumulated gradients and update all registered agent policies.

        Returns a dict of {agent_type: new_version or None}.
        """
        results = {}
        mean_reward = self.reward_fn.mean_reward(last_n=100)
        for agent_type in self._agent_registry:
            new_version = self.policy_store.apply_gradients(
                agent_type=agent_type.value,
                learning_rate=learning_rate,
                training_step=self._training_step,
                mean_reward=mean_reward,
            )
            results[agent_type.value] = new_version
        return results

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def training_step(self) -> int:
        return self._training_step

    @property
    def task_history(self) -> List[Task]:
        with self._lock:
            return list(self._task_history)

    def mean_reward(self, last_n: int = 100) -> float:
        return self.reward_fn.mean_reward(last_n=last_n)

    def buffer_stats(self) -> Dict[str, Any]:
        stats = self.replay_buffer.stats()
        return {
            "buffer_size": stats.buffer_size,
            "capacity": stats.capacity,
            "total_stored": stats.total_stored,
            "total_sampled": stats.total_sampled,
            "agent_counts": stats.agent_counts,
            "mean_reward": stats.mean_reward,
        }

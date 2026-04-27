"""Phase 16G — PARLEngine: orchestrates parallel subagents with PARL reward shaping."""
from __future__ import annotations
import math
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Tuple

from phase16.parl_core.models import (
    AnnealingSchedule, CriticalPathMetrics, PARLEpisode,
    SubagentContext, SubagentResult, SynthesisResult,
)
from phase16.parl_core.context_isolation import ContextIsolationLayer


class PARLEngine:
    """Parallel Agent Reinforcement Learning engine for SintraPrime Phase 16.

    Implements the three-term PARL reward:
        r_PARL = λ1·r_parallel + λ2·r_finish + r_perf

    λ1 and λ2 anneal to zero over training so the reward signal transitions
    from "spawn more parallel agents" → "pure task quality".
    """

    def __init__(
        self,
        max_workers: int = 8,
        total_training_steps: int = 10_000,
        annealing_schedule: str = "cosine",
        lambda1_init: float = 0.5,
        lambda2_init: float = 0.1,
        context_ttl: float = 300.0,
    ):
        self.max_workers = max_workers
        self.total_steps = total_training_steps
        self._schedule = AnnealingSchedule(
            schedule_type=annealing_schedule,
            lambda1_init=lambda1_init,
            lambda2_init=lambda2_init,
            total_steps=total_training_steps,
        )
        self._isolation = ContextIsolationLayer(default_ttl=context_ttl)
        self._step = 0
        self._lock = threading.Lock()
        self._episode_history: List[PARLEpisode] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_parallel(
        self,
        task: str,
        subagent_specs: List[Dict[str, Any]],
        executor_fn: Optional[Callable[[SubagentContext], Any]] = None,
        n_workers: Optional[int] = None,
    ) -> PARLEpisode:
        """Run subagents in parallel and return a completed PARLEpisode.

        Args:
            task: High-level task description.
            subagent_specs: List of dicts with keys: agent_id, description, payload.
            executor_fn: Callable(SubagentContext)->Any. Defaults to a mock executor.
            n_workers: Override max_workers for this episode.
        """
        workers = n_workers or self.max_workers
        episode = PARLEpisode(
            task_id=f"ep_{int(time.time()*1000)}",
            task_description=task,
            step=self._step,
        )

        if not subagent_specs:
            episode.completed_at = time.time()
            episode.r_finish = 1.0
            episode.total_reward = self._schedule.get_lambda2(self._step) * 1.0
            return episode

        fn = executor_fn or self._default_executor

        # Create isolated contexts
        contexts: List[SubagentContext] = []
        for spec in subagent_specs:
            ctx = self._isolation.create_context(
                agent_id=spec.get("agent_id", f"agent_{len(contexts)}"),
                task_description=spec.get("description", task),
                payload=spec.get("payload", {}),
            )
            contexts.append(ctx)

        # Execute in parallel
        results: List[SubagentResult] = []
        start_times: Dict[str, float] = {}
        end_times: Dict[str, float] = {}

        with ThreadPoolExecutor(max_workers=workers) as pool:
            future_map = {}
            for ctx in contexts:
                isolated = self._isolation.isolate(ctx)
                start_times[ctx.agent_id] = time.time()
                future_map[pool.submit(fn, isolated)] = ctx.agent_id

            for future in as_completed(future_map):
                agent_id = future_map[future]
                end_times[agent_id] = time.time()
                duration = end_times[agent_id] - start_times[agent_id]
                try:
                    output = future.result()
                    results.append(SubagentResult(
                        agent_id=agent_id,
                        success=True,
                        output=output,
                        duration_seconds=duration,
                    ))
                except Exception as exc:
                    results.append(SubagentResult(
                        agent_id=agent_id,
                        success=False,
                        output=None,
                        duration_seconds=duration,
                        error=str(exc),
                    ))

        episode.subagent_results = results
        episode.completed_at = time.time()
        episode.critical_path = self._compute_critical_path(
            results, start_times, end_times
        )

        # Compute reward
        reward, r_par, r_fin, r_perf = self._compute_reward_components(episode)
        episode.total_reward = reward
        episode.r_parallel = r_par
        episode.r_finish = r_fin
        episode.r_perf = r_perf

        with self._lock:
            self._step += 1
            self._episode_history.append(episode)

        # Evict contexts
        for ctx in contexts:
            self._isolation.evict(ctx.agent_id)

        return episode

    def compute_reward(self, episode: PARLEpisode) -> float:
        """Compute total PARL reward for a completed episode."""
        reward, _, _, _ = self._compute_reward_components(episode)
        return reward

    def anneal_lambdas(self, step: Optional[int] = None) -> Tuple[float, float]:
        """Return (λ1, λ2) at the given training step."""
        s = step if step is not None else self._step
        return self._schedule.get_lambda1(s), self._schedule.get_lambda2(s)

    def get_critical_path(self, episode: PARLEpisode) -> CriticalPathMetrics:
        """Return or recompute critical path metrics for an episode."""
        if episode.critical_path:
            return episode.critical_path
        # Reconstruct from results
        if not episode.subagent_results:
            return CriticalPathMetrics(0.0, 0.0, 0, 1.0)
        durations = [r.duration_seconds for r in episode.subagent_results]
        cp = max(durations)
        total_seq = sum(durations)
        efficiency = cp / total_seq if total_seq > 0 else 1.0
        bottleneck = max(episode.subagent_results, key=lambda r: r.duration_seconds).agent_id
        return CriticalPathMetrics(
            critical_path_duration=cp,
            total_parallel_duration=episode.duration,
            num_subagents=len(episode.subagent_results),
            parallelism_efficiency=efficiency,
            bottleneck_agent_id=bottleneck,
        )

    def get_context_stats(self) -> Dict[str, Any]:
        return self._isolation.get_stats()

    def get_episode_history(self) -> List[PARLEpisode]:
        with self._lock:
            return list(self._episode_history)

    @property
    def current_step(self) -> int:
        return self._step

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_reward_components(
        self, episode: PARLEpisode
    ) -> Tuple[float, float, float, float]:
        """Return (total, r_parallel, r_finish, r_perf)."""
        λ1 = self._schedule.get_lambda1(episode.step)
        λ2 = self._schedule.get_lambda2(episode.step)

        n = len(episode.subagent_results)
        n_success = sum(1 for r in episode.subagent_results if r.success)

        # r_parallel: reward for effective parallelism
        if n > 1 and episode.critical_path:
            cp = episode.critical_path
            seq_time = sum(r.duration_seconds for r in episode.subagent_results)
            r_parallel = 1.0 - (cp.critical_path_duration / seq_time) if seq_time > 0 else 0.0
        elif n == 1:
            r_parallel = 0.0
        else:
            r_parallel = 0.0

        # r_finish: fraction of subagents that completed successfully
        r_finish = n_success / n if n > 0 else 1.0

        # r_perf: task quality (success rate as proxy)
        r_perf = episode.success_rate

        total = λ1 * r_parallel + λ2 * r_finish + r_perf
        return total, r_parallel, r_finish, r_perf

    def _compute_critical_path(
        self,
        results: List[SubagentResult],
        start_times: Dict[str, float],
        end_times: Dict[str, float],
    ) -> CriticalPathMetrics:
        if not results:
            return CriticalPathMetrics(0.0, 0.0, 0, 1.0)

        durations = {r.agent_id: r.duration_seconds for r in results}
        cp_duration = max(durations.values()) if durations else 0.0
        total_seq = sum(durations.values())
        efficiency = cp_duration / total_seq if total_seq > 0 else 1.0
        bottleneck = max(durations, key=durations.get) if durations else None

        # Actual wall-clock parallel duration
        if start_times and end_times:
            wall_start = min(start_times.values())
            wall_end = max(end_times.values())
            parallel_duration = wall_end - wall_start
        else:
            parallel_duration = cp_duration

        return CriticalPathMetrics(
            critical_path_duration=cp_duration,
            total_parallel_duration=parallel_duration,
            num_subagents=len(results),
            parallelism_efficiency=efficiency,
            bottleneck_agent_id=bottleneck,
        )

    @staticmethod
    def _default_executor(ctx: SubagentContext) -> Dict[str, Any]:
        """Mock executor: simulates work proportional to payload size."""
        import random
        rng = random.Random(hash(ctx.agent_id) % (2**31))
        delay = rng.uniform(0.001, 0.01)
        time.sleep(delay)
        return {"agent_id": ctx.agent_id, "result": "ok", "payload_keys": list(ctx.payload.keys())}

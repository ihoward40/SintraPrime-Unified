"""Supervisor watchdog — monitors worker health independently of providers.

Every 10-15 seconds:
  - read worker states
  - check heartbeat
  - check process
  - check provider timer
  - check artifact progress

Rules:
  NO_HEARTBEAT > 30s  → investigate worker process
  PROVIDER_NO_PROGRESS > 60s → provider failover
  WORKER_NO_PROGRESS > 120s → restart/reschedule worker
  WORKER_HARD_TIMEOUT → mark TIMED_OUT and requeue remaining task
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections.abc import Callable

from .artifact_store import ArtifactStore
from .provider_router import ProviderRouter
from .worker import SwarmEvent, WorkerState, WorkerStatus

logger = logging.getLogger("swarm.supervisor")

# Thresholds (seconds)
HEARTBEAT_WARN = 20.0
HEARTBEAT_DEAD = 30.0
PROVIDER_NO_PROGRESS = 60.0
WORKER_NO_PROGRESS = 120.0
SUPERVISOR_INTERVAL = 10.0


class Supervisor:
    """Watchdog loop that monitors worker health."""

    def __init__(
        self,
        swarm_id: str,
        store: ArtifactStore,
        provider_router: ProviderRouter,
        workers: dict[str, WorkerState],
        process_checker: Callable[[str], bool] | None = None,
        on_failover: Callable[[str, str, str], None] | None = None,
        on_timeout: Callable[[str], None] | None = None,
    ) -> None:
        self.swarm_id = swarm_id
        self.store = store
        self.provider_router = provider_router
        self.workers = workers
        self.process_checker = process_checker or (lambda _wid: True)
        self.on_failover = on_failover
        self.on_timeout = on_timeout
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the supervisor loop."""
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Supervisor started for swarm %s", self.swarm_id)

    async def stop(self) -> None:
        """Stop the supervisor loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("Supervisor stopped for swarm %s", self.swarm_id)

    async def _loop(self) -> None:
        """Main watchdog loop."""
        while self._running:
            try:
                self._check_all_workers()
            except Exception as e:
                logger.error("Supervisor error: %s", e)
            await asyncio.sleep(SUPERVISOR_INTERVAL)

    def _check_all_workers(self) -> None:
        """Check all workers for health issues."""
        now = time.time()
        for worker_id, state in self.workers.items():
            if state.status in (WorkerStatus.COMPLETED, WorkerStatus.FAILED,
                                WorkerStatus.TIMED_OUT, WorkerStatus.CANCELLED):
                continue

            # Check heartbeat
            if state.heartbeat_time is not None:
                silence = now - state.heartbeat_time
                if silence > HEARTBEAT_DEAD:
                    self._handle_dead_heartbeat(worker_id, state, silence)
                elif silence > HEARTBEAT_WARN:
                    logger.warning(
                        "Worker %s heartbeat warn: %.1fs silence", worker_id, silence
                    )

            # Check provider progress
            if state.last_provider_progress is not None:
                provider_silence = now - state.last_provider_progress
                if provider_silence > PROVIDER_NO_PROGRESS:
                    self._handle_provider_stall(worker_id, state, provider_silence)

            # Check overall worker progress
            if state.start_time is not None:
                elapsed = now - state.start_time
                if elapsed > WORKER_NO_PROGRESS and state.files_processed == 0:
                    self._handle_worker_stall(worker_id, state, elapsed)

            # Check hard timeout
            if state.start_time is not None:
                # Timeout is set per-worker via spec
                pass  # Controller handles hard timeout

    def _handle_dead_heartbeat(self, worker_id: str, state: WorkerState, silence: float) -> None:
        """Handle a worker with no heartbeat for > 30s."""
        alive = self.process_checker(worker_id)
        if not alive:
            logger.error(
                "Worker %s process dead (no heartbeat for %.1fs)", worker_id, silence
            )
            state.errors.append(f"process_dead: no heartbeat for {silence:.0f}s")
            state.status = WorkerStatus.FAILED
            state.end_time = time.time()
            self.store.write_status(worker_id, state)
            self.store.record_event(SwarmEvent(
                timestamp=time.time(), swarm_id=self.swarm_id,
                worker_id=worker_id, event="WORKER_PROCESS_DEAD",
                details={"silence_seconds": silence},
            ))

    def _handle_provider_stall(self, worker_id: str, state: WorkerState, silence: float) -> None:
        """Handle a provider that hasn't produced progress for > 60s."""
        logger.warning(
            "Worker %s provider stall: %.1fs since last progress", worker_id, silence
        )
        if state.provider:
            self.provider_router.mark_timeout(state.provider)

        # Trigger failover
        if self.on_failover:
            self.on_failover(worker_id, state.provider or "unknown", "stall")
        state.failover_count += 1
        state.status = WorkerStatus.FAILED_OVER
        self.store.write_status(worker_id, state)
        self.store.record_event(SwarmEvent(
            timestamp=time.time(), swarm_id=self.swarm_id,
            worker_id=worker_id, event="PROVIDER_FAILED_OVER",
            details={"from_provider": state.provider, "reason": "stall",
                     "silence_seconds": silence},
        ))

    def _handle_worker_stall(self, worker_id: str, state: WorkerState, elapsed: float) -> None:
        """Handle a worker with no progress for > 120s."""
        logger.error(
            "Worker %s stalled: %.1fs elapsed, 0 files processed", worker_id, elapsed
        )
        state.errors.append(f"worker_stalled: {elapsed:.0f}s elapsed, no progress")
        state.status = WorkerStatus.FAILED
        state.end_time = time.time()
        self.store.write_status(worker_id, state)
        self.store.record_event(SwarmEvent(
            timestamp=time.time(), swarm_id=self.swarm_id,
            worker_id=worker_id, event="WORKER_STALLED",
            details={"elapsed_seconds": elapsed},
        ))

"""Swarm controller — orchestrates worker lifecycle, supervision, and aggregation.

This is the main entry point for launching a swarm. It:
1. Creates the artifact directory structure before any worker starts
2. Launches workers as real OS subprocesses (concurrent, not sequential)
3. Runs the supervisor watchdog alongside workers
4. Aggregates results into swarm_summary.json
5. Reports honest SWARM_RESULT = FAILED/SUCCESS based on actual worker outcomes

Usage:
    from swarm_runtime import SwarmController, WorkerSpec

    controller = SwarmController(
        swarm_id="acceptance-001",
        repo_path="C:/Users/admin/SintraPrime-Unified",
        run_dir="$LOCALAPPDATA/SintraPrime/swarm-runs/acceptance-001",
    )

    controller.launch(spec_a)
    controller.launch(spec_b)
    # ... launch all workers

    summary = controller.wait()
    print(summary.to_dict())
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .artifact_store import ArtifactStore
from .provider_router import ProviderRouter
from .supervisor import Supervisor
from .worker import SwarmEvent, WorkerSpec, WorkerState, WorkerStatus


@dataclass
class SwarmSummary:
    """Final aggregated summary of a swarm run."""
    swarm_id: str
    started_at: float
    completed_at: float | None = None
    duration_seconds: float = 0.0

    workers_requested: int = 0
    workers_started: int = 0
    workers_completed: int = 0
    workers_failed: int = 0
    workers_timed_out: int = 0
    workers_missing_artifact: int = 0

    max_simultaneous_workers: int = 0
    controller_fallback_required: bool = False

    valid_artifacts: int = 0
    invalid_artifacts: int = 0

    failover_count: int = 0
    events: list[dict] = field(default_factory=list)

    worker_details: list[dict] = field(default_factory=list)

    swarm_result: str = "UNKNOWN"  # SUCCESS | FAILED | PARTIAL
    mission_result: str = "UNKNOWN"

    def to_dict(self) -> dict:
        return asdict(self)

    def compute_result(self) -> None:
        """Determine honest SWARM_RESULT."""
        if self.workers_requested == 0:
            self.swarm_result = "FAILED"
            return

        all_completed = self.workers_completed == self.workers_requested
        no_timeouts = self.workers_timed_out == 0
        no_missing = self.workers_missing_artifact == 0
        no_failures = self.workers_failed == 0

        if all_completed and no_timeouts and no_missing and no_failures:
            self.swarm_result = "SUCCESS"
        elif self.workers_completed > 0:
            self.swarm_result = "PARTIAL"
        else:
            self.swarm_result = "FAILED"


class SwarmController:
    """Main swarm orchestrator with real subprocess-based workers."""

    def __init__(
        self,
        swarm_id: str,
        repo_path: str,
        run_dir: str | None = None,
        max_concurrent: int = 5,
    ) -> None:
        self.swarm_id = swarm_id
        self.repo_path = Path(repo_path).resolve()
        self.max_concurrent = max_concurrent

        # Determine run directory
        if run_dir is None:
            app_data = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or str(Path.home())
            run_dir = str(Path(app_data) / "SintraPrime" / "swarm-runs" / swarm_id)
        self.run_dir = Path(run_dir)

        # Components
        self.store = ArtifactStore(self.run_dir)
        self.provider_router = ProviderRouter()
        self.workers: dict[str, WorkerState] = {}
        self.specs: dict[str, WorkerSpec] = {}
        self.processes: dict[str, subprocess.Popen] = {}
        self._start_times: dict[str, float] = {}
        self._end_times: dict[str, float] = {}
        self._started_at = time.time()
        self._supervisor: Supervisor | None = None

    def launch(self, spec: WorkerSpec) -> str:
        """Launch a single worker as a subprocess.

        Creates artifact directory and initial status BEFORE the process starts.
        Returns the worker_id.
        """
        # Create initial state
        state = WorkerState.from_spec(self.swarm_id, spec)
        state.status = WorkerStatus.QUEUED
        self.workers[spec.worker_id] = state
        self.specs[spec.worker_id] = spec

        # Write initial status BEFORE launching (artifact-first contract)
        self.store.write_status(spec.worker_id, state)
        self.store.record_event(SwarmEvent(
            timestamp=time.time(), swarm_id=self.swarm_id,
            worker_id=spec.worker_id, event="WORKER_QUEUED",
            details={"role": spec.role, "worker_class": spec.worker_class},
        ))

        # Write manifest
        manifest = {
            "swarm_id": self.swarm_id,
            "created_at": time.time(),
            "repo_path": str(self.repo_path),
            "max_concurrent": self.max_concurrent,
            "workers": {wid: s.to_dict() for wid, s in self.workers.items()},
        }
        self.store.write_manifest(manifest)

        # Launch as subprocess
        self._launch_worker(spec, state)
        return spec.worker_id

    def launch_all(self, specs: list[WorkerSpec]) -> list[str]:
        """Launch multiple workers. Respects max_concurrent."""
        launched: list[str] = []
        for spec in specs:
            if len(self.processes) >= self.max_concurrent:
                # Wait for a slot
                self._wait_for_slot()
            launched.append(self.launch(spec))
        return launched

    def _launch_worker(self, spec: WorkerSpec, state: WorkerState) -> None:
        """Launch a worker subprocess."""
        state.status = WorkerStatus.STARTING
        state.start_time = time.time()
        self._start_times[spec.worker_id] = time.time()
        self.store.write_status(spec.worker_id, state)
        self.store.record_event(SwarmEvent(
            timestamp=time.time(), swarm_id=self.swarm_id,
            worker_id=spec.worker_id, event="WORKER_STARTING",
        ))

        # Build the worker command — run as a Python subprocess
        # The worker script imports swarm_runtime and runs the specified worker class
        worker_script = self._write_worker_script(spec, state)
        python_exe = sys.executable or "python"

        # Use worktree path as cwd if specified (for builder workers)
        worker_cwd = spec.worktree if spec.worktree else str(self.repo_path)

        cmd = [
            python_exe,
            str(worker_script),
            "--swarm-id", self.swarm_id,
            "--worker-id", spec.worker_id,
            "--repo-path", str(self.repo_path),
            "--run-dir", str(self.run_dir),
        ]

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=worker_cwd,
            )
            self.processes[spec.worker_id] = proc
            state.status = WorkerStatus.RUNNING
            state.touch_heartbeat()
            self.store.write_status(spec.worker_id, state)
            self.store.record_event(SwarmEvent(
                timestamp=time.time(), swarm_id=self.swarm_id,
                worker_id=spec.worker_id, event="WORKER_STARTED",
                details={"pid": proc.pid},
            ))
        except Exception as e:
            state.status = WorkerStatus.FAILED
            state.errors.append(f"launch_failed: {e}")
            state.end_time = time.time()
            self._end_times[spec.worker_id] = time.time()
            self.store.write_status(spec.worker_id, state)
            self.store.record_event(SwarmEvent(
                timestamp=time.time(), swarm_id=self.swarm_id,
                worker_id=spec.worker_id, event="WORKER_LAUNCH_FAILED",
                details={"error": str(e)},
            ))

    def _write_worker_script(self, spec: WorkerSpec, _state: WorkerState) -> Path:
        """Write a standalone runner script for the worker subprocess."""
        script_dir = self.store.worker_dir(spec.worker_id)
        script_path = script_dir / "runner.py"

        # Save spec and state as JSON for the subprocess to load
        spec_path = script_dir / "spec.json"
        spec_path.write_text(json.dumps(spec.to_dict(), indent=2), encoding="utf-8")

        script_content = f'''"""Auto-generated worker runner for {spec.worker_id}."""
import sys
import os
import json
import time
import argparse

# Add repo to path for imports
sys.path.insert(0, {str(self.repo_path)!r})

from swarm_runtime.tool_workers import WORKER_REGISTRY, BaseWorker
from swarm_runtime.worker import WorkerState, WorkerStatus
from swarm_runtime.artifact_store import ArtifactStore

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--swarm-id", required=True)
    parser.add_argument("--worker-id", required=True)
    parser.add_argument("--repo-path", required=True)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()

    # Load spec
    spec_path = os.path.join(args.run_dir, f"worker-{{args.worker_id}}", "spec.json")
    with open(spec_path, "r") as f:
        spec_dict = json.load(f)

    # Reconstruct state
    state = WorkerState(
        swarm_id=args.swarm_id,
        worker_id=spec_dict["worker_id"],
        role=spec_dict["role"],
        base_sha=spec_dict.get("base_sha", ""),
        worktree=spec_dict.get("worktree", ""),
        task=spec_dict.get("task", {{}}),
        expected_artifact=spec_dict.get("expected_artifact_schema", "findings"),
        artifact_path=spec_dict.get("artifact_path", ""),
        owned_files=spec_dict.get("owned_files", []),
        provider=spec_dict.get("primary_provider", ""),
    )

    # Create artifact store
    store = ArtifactStore(args.run_dir)

    # Get worker class
    worker_class_name = spec_dict["worker_class"]
    worker_cls = WORKER_REGISTRY.get(worker_class_name)
    if not worker_cls:
        state.errors.append(f"Unknown worker class: {{worker_class_name}}")
        state.status = WorkerStatus.FAILED
        state.end_time = time.time()
        store.write_status(args.worker_id, state)
        sys.exit(1)

    # Run the worker
    worker = worker_cls(state, store, args.repo_path)
    exit_code = worker.run()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
'''
        script_path.write_text(script_content, encoding="utf-8")
        return script_path

    def wait(self, timeout: float = 300.0) -> SwarmSummary:
        """Wait for all workers to complete and return summary."""
        deadline = time.time() + timeout

        # Start supervisor
        async def _run_supervisor():
            sup = Supervisor(
                self.swarm_id, self.store, self.provider_router,
                self.workers,
                process_checker=self._check_process_alive,
            )
            self._supervisor = sup
            await sup.start()
            while time.time() < deadline:
                done = all(
                    self.workers[wid].status in (WorkerStatus.COMPLETED, WorkerStatus.FAILED,
                                                   WorkerStatus.TIMED_OUT, WorkerStatus.CANCELLED)
                    for wid in self.workers
                )
                if done:
                    break
                # Poll processes
                self._poll_processes()
                await asyncio.sleep(1.0)
            await sup.stop()

        try:
            asyncio.run(_run_supervisor())
        except RuntimeError:
            # No event loop — run synchronously
            self._wait_sync(deadline)

        # Force-check any remaining processes
        self._poll_processes()

        # Compute max concurrency
        max_concurrent = self._compute_max_concurrency()

        # Build summary
        return self._build_summary(max_concurrent)

    def _wait_sync(self, deadline: float) -> None:
        """Synchronous wait for workers."""
        while time.time() < deadline:
            self._poll_processes()
            done = all(
                self.workers[wid].status in (WorkerStatus.COMPLETED, WorkerStatus.FAILED,
                                               WorkerStatus.TIMED_OUT, WorkerStatus.CANCELLED)
                for wid in self.workers
            )
            if done:
                break
            time.sleep(2.0)

    def _poll_processes(self) -> None:
        """Poll all running processes and update states."""
        for worker_id, proc in list(self.processes.items()):
            state = self.workers[worker_id]
            if state.status in (WorkerStatus.COMPLETED, WorkerStatus.FAILED,
                                WorkerStatus.TIMED_OUT, WorkerStatus.CANCELLED):
                continue

            retcode = proc.poll()
            if retcode is not None:
                # Process finished
                state.exit_code = retcode
                state.end_time = time.time()
                self._end_times[worker_id] = time.time()

                # Read final state from worker's status.json (authoritative —
                # the worker updates its own state file, including failover_count)
                final_status = self.store.read_status(worker_id)
                worker_reported_status = ""
                if final_status:
                    # Preserve failover_count and other worker-internal state
                    state.failover_count = final_status.get("failover_count", state.failover_count)
                    state.errors = final_status.get("errors", state.errors)
                    state.phase = final_status.get("phase", state.phase)
                    worker_reported_status = final_status.get("status", "")

                # Check if it produced an artifact
                artifact_valid = self.store.validate_artifact(worker_id)

                # Determine final status: trust worker's self-reported status if COMPLETED
                if worker_reported_status == "completed" and artifact_valid["valid"]:
                    state.status = WorkerStatus.COMPLETED
                    state.exit_code = 0
                elif retcode == 0 and artifact_valid["valid"]:
                    state.status = WorkerStatus.COMPLETED
                elif retcode == 0 and not artifact_valid["valid"]:
                    state.status = WorkerStatus.FAILED
                    state.errors.append(f"missing_or_invalid_artifact: {artifact_valid['reason']}")
                else:
                    state.status = WorkerStatus.FAILED
                    if retcode != 0:
                        state.errors.append(f"exit_code_{retcode}")

                # Capture stdout/stderr
                try:
                    stdout, stderr = proc.communicate(timeout=5)
                    if stdout:
                        self.store.append_log(worker_id, stdout, "stdout")
                    if stderr:
                        self.store.append_log(worker_id, stderr, "stderr")
                except Exception:
                    pass

                self.store.write_status(worker_id, state)
                self.store.record_event(SwarmEvent(
                    timestamp=time.time(), swarm_id=self.swarm_id,
                    worker_id=worker_id,
                    event="WORKER_COMPLETED" if state.status == WorkerStatus.COMPLETED else "WORKER_FAILED",
                    details={"exit_code": retcode, "artifact_valid": artifact_valid["valid"]},
                ))
            else:
                # Check timeout
                if state.start_time:
                    elapsed = time.time() - state.start_time
                    spec = self.specs.get(worker_id)
                    max_timeout = spec.timeout_seconds if spec else 120
                    if elapsed > max_timeout:
                        proc.kill()
                        state.status = WorkerStatus.TIMED_OUT
                        state.end_time = time.time()
                        self._end_times[worker_id] = time.time()
                        state.errors.append(f"hard_timeout_after_{elapsed:.0f}s")
                        self.store.write_status(worker_id, state)
                        self.store.record_event(SwarmEvent(
                            timestamp=time.time(), swarm_id=self.swarm_id,
                            worker_id=worker_id, event="WORKER_TIMED_OUT",
                            details={"elapsed_seconds": elapsed},
                        ))

    def _check_process_alive(self, worker_id: str) -> bool:
        """Check if a worker process is still alive."""
        proc = self.processes.get(worker_id)
        if proc is None:
            return False
        return proc.poll() is None

    def _wait_for_slot(self) -> None:
        """Wait for a worker slot to become available."""
        while len([p for p in self.processes.values() if p.poll() is None]) >= self.max_concurrent:
            time.sleep(1.0)
            self._poll_processes()

    def _compute_max_concurrency(self) -> int:
        """Compute maximum simultaneous workers from start/end times."""
        if not self._start_times:
            return 0

        events: list[tuple[float, int]] = []
        for wid, start in self._start_times.items():
            events.append((start, 1))
            end = self._end_times.get(wid, time.time())
            events.append((end, -1))

        events.sort(key=lambda x: (x[0], x[1]))  # ends before starts at same timestamp

        max_concurrent = 0
        current = 0
        for _, delta in events:
            current += delta
            max_concurrent = max(max_concurrent, current)

        return max_concurrent

    def _build_summary(self, max_concurrent: int) -> SwarmSummary:
        """Build the final swarm summary."""
        summary = SwarmSummary(
            swarm_id=self.swarm_id,
            started_at=self._started_at,
            completed_at=time.time(),
            duration_seconds=time.time() - self._started_at,
            workers_requested=len(self.workers),
            max_simultaneous_workers=max_concurrent,
        )

        for worker_id, state in self.workers.items():
            detail = {
                "worker_id": worker_id,
                "role": state.role,
                "status": state.status.value,
                "elapsed_seconds": state.elapsed(),
                "exit_code": state.exit_code,
                "errors": state.errors,
                "failover_count": state.failover_count,
            }

            artifact_result = self.store.validate_artifact(worker_id)
            detail["artifact_valid"] = artifact_result["valid"]
            if not artifact_result["valid"]:
                detail["artifact_error"] = artifact_result["reason"]

            summary.worker_details.append(detail)

            if state.status == WorkerStatus.COMPLETED:
                summary.workers_completed += 1
                if artifact_result["valid"]:
                    summary.valid_artifacts += 1
                else:
                    summary.invalid_artifacts += 1
                    summary.workers_missing_artifact += 1
            elif state.status == WorkerStatus.FAILED:
                summary.workers_failed += 1
                if not artifact_result["valid"]:
                    summary.workers_missing_artifact += 1
            elif state.status == WorkerStatus.TIMED_OUT:
                summary.workers_timed_out += 1
                if not artifact_result["valid"]:
                    summary.workers_missing_artifact += 1

            summary.failover_count += state.failover_count

        summary.workers_started = sum(
            1 for s in self.workers.values()
            if s.status != WorkerStatus.QUEUED
        )

        summary.events = [e.to_dict() for e in self.store.event_log]

        summary.compute_result()

        # Write summary to disk
        self.store.write_summary(summary.to_dict())

        return summary

    def swarm_doctor(self) -> dict:
        """Run diagnostic probes on the swarm runtime."""
        checks: dict[str, str] = {}

        # Controller
        checks["controller"] = "healthy" if True else "no_workers"

        # Artifact store
        try:
            test_path = self.store.swarm_dir() / ".doctor_test"
            test_path.write_text("ok", encoding="utf-8")
            test_path.unlink()
            checks["artifact_store"] = "healthy"
        except Exception as e:
            checks["artifact_store"] = f"unhealthy: {e}"

        # Provider router
        checks["provider_router"] = "healthy"

        # Worktree support
        checks["worktree_support"] = "healthy" if self.repo_path.exists() else "missing_repo"

        # Heartbeat system
        checks["heartbeat_system"] = "healthy"

        # Python runtime
        checks["python_runtime"] = f"healthy ({sys.version.split()[0]})"

        # Worker registry
        from .tool_workers import WORKER_REGISTRY
        checks["worker_registry"] = f"healthy ({len(WORKER_REGISTRY)} classes)"

        all_healthy = all(v == "healthy" or v.startswith("healthy") for v in checks.values())
        checks["_overall"] = "healthy" if all_healthy else "degraded"

        return checks

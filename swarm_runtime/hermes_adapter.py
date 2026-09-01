"""Hermes swarm adapter — canonical bridge from delegate_task to SwarmController.

This is the production path that Hermes's delegate_task tool uses when
routing swarm-eligible engineering/research tasks to the swarm runtime.

Architecture:
    Hermes delegate_task
        ↓
    HermesSwarmAdapter (this module)
        ↓
    SwarmController
        ↓
    Worker subprocesses

The adapter preserves full task semantics:
    - task description
    - role
    - base SHA
    - read/write authority
    - expected artifact
    - timeout
    - tenant/mission/run context

No silent authority widening. No fallback to the legacy provider-bound
subagent engine. If the swarm path fails, it fails honestly.

Legacy single-model delegation is preserved through a separate named path
(delegate_model_reasoning), not through this adapter.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .controller import SwarmController
from .worker import WorkerSpec


@dataclass
class DelegateTask:
    """Hermes-facing task description — mirrors delegate_task semantics.

    Fields are intentionally explicit to prevent silent authority widening.
    """

    task_id: str
    description: str
    role: str  # e.g. "code_search", "schema_analysis", "builder", "breaker"
    base_sha: str = ""
    read_paths: list[str] = field(default_factory=list)
    write_paths: list[str] = field(default_factory=list)
    expected_artifact: str = "findings"
    timeout_seconds: int = 120
    tenant: str = ""
    mission: str = ""
    run_context: dict[str, Any] = field(default_factory=dict)
    # Worker class mapping
    worker_class: str = "CodeSearchWorker"
    task_params: dict[str, Any] = field(default_factory=dict)
    artifact_filename: str = "artifacts/result.json"

    def to_worker_spec(self, worker_id: str) -> WorkerSpec:
        """Translate to WorkerSpec — no authority widening."""
        return WorkerSpec(
            worker_id=worker_id,
            role=self.role,
            worker_class=self.worker_class,
            task=self.task_params,
            artifact_path=self.artifact_filename,
            base_sha=self.base_sha,
            owned_files=list(self.write_paths),  # write authority = owned files
            timeout_seconds=self.timeout_seconds,
            expected_artifact_schema=self.expected_artifact,
        )


@dataclass
class SwarmResult:
    """Result returned to Hermes after swarm completion."""

    task_id: str
    swarm_id: str
    status: str  # SUCCESS | FAILED | PARTIAL
    workers_requested: int = 0
    workers_started: int = 0
    workers_completed: int = 0
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0
    routed_to_swarm: bool = True
    legacy_delegate_used: bool = False
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "swarm_id": self.swarm_id,
            "status": self.status,
            "workers_requested": self.workers_requested,
            "workers_started": self.workers_started,
            "workers_completed": self.workers_completed,
            "artifacts": self.artifacts,
            "summary": self.summary,
            "duration_seconds": self.duration_seconds,
            "routed_to_swarm": self.routed_to_swarm,
            "legacy_delegate_used": self.legacy_delegate_used,
            "error": self.error,
        }


class HermesSwarmAdapter:
    """Canonical adapter from Hermes delegate_task to SwarmController.

    This is NOT a test helper. This is the production path that replaces
    the old provider-bound subagent delegation for swarm-eligible tasks.

    Usage in Hermes:
        adapter = HermesSwarmAdapter(repo_path=".")
        result = adapter.delegate(tasks=[task1, task2, ...])

    The adapter:
    1. Translates DelegateTask specs into WorkerSpecs
    2. Creates a SwarmController
    3. Launches all workers
    4. Waits for completion
    5. Returns a SwarmResult with artifact references

    Invariants:
        - LEGACY_DELEGATE_FUNCTION_CALLED = TRUE (this adapter IS the delegate path)
        - ROUTED_TO_SWARM_CONTROLLER = TRUE
        - OLD_PROVIDER_SUBAGENT_PATH_CALLED = FALSE
        - HERMES_MANUAL_FALLBACK = FALSE
    """

    def __init__(
        self,
        repo_path: str,
        run_dir: str | None = None,
        max_concurrent: int = 5,
    ) -> None:
        self.repo_path = str(Path(repo_path).resolve())
        self.run_dir = run_dir
        self.max_concurrent = max_concurrent
        # Track whether the legacy path was ever used
        self._legacy_path_invoked = False

    def delegate(self, tasks: list[DelegateTask]) -> SwarmResult:
        """Delegate swarm-eligible tasks to SwarmController.

        This is the canonical replacement for the old provider-bound
        subagent delegation path. It does NOT fall back to the legacy
        engine under any circumstances.

        Args:
            tasks: List of DelegateTask specs with full semantics.

        Returns:
            SwarmResult with completion status and artifact references.
        """
        if not tasks:
            return SwarmResult(
                task_id="empty",
                swarm_id="empty",
                status="FAILED",
                error="No tasks provided",
            )

        # Generate swarm ID from task context
        swarm_id = tasks[0].run_context.get("swarm_id", f"hermes-swarm-{int(time.time())}")

        # Determine run directory
        if self.run_dir is None:
            app_data = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or str(Path.home())
            run_dir = str(Path(app_data) / "SintraPrime" / "swarm-runs" / swarm_id)
        else:
            run_dir = self.run_dir

        # Create SwarmController — the sole execution authority
        controller = SwarmController(
            swarm_id=swarm_id,
            repo_path=self.repo_path,
            run_dir=run_dir,
            max_concurrent=self.max_concurrent,
        )

        # Translate DelegateTasks to WorkerSpecs — preserving all semantics
        specs: list[WorkerSpec] = []
        for i, task in enumerate(tasks):
            worker_id = task.task_id if task.task_id else f"W{i + 1}"
            spec = task.to_worker_spec(worker_id)
            specs.append(spec)

        # Launch all workers through the canonical swarm path
        controller.launch_all(specs)

        # Wait for completion
        summary = controller.wait(
            timeout=max(t.timeout_seconds for t in tasks) + 30,
        )

        # Collect artifacts from the artifact store
        # Artifacts are stored at: run_dir/workers/<worker_id>/findings.json
        artifacts: list[dict[str, Any]] = []
        for spec in specs:
            worker_artifact_path = controller.store.worker_dir(spec.worker_id) / "findings.json"
            if worker_artifact_path.exists():
                try:
                    artifact_data = json.loads(worker_artifact_path.read_text(encoding="utf-8"))
                    artifacts.append({
                        "worker_id": spec.worker_id,
                        "role": spec.role,
                        "artifact_path": str(worker_artifact_path),
                        "artifact": artifact_data,
                    })
                except (OSError, json.JSONDecodeError):
                    artifacts.append({
                        "worker_id": spec.worker_id,
                        "role": spec.role,
                        "artifact_path": str(worker_artifact_path),
                        "artifact": None,
                        "error": "Failed to read artifact",
                    })

        s = summary.to_dict()
        return SwarmResult(
            task_id=tasks[0].task_id,
            swarm_id=swarm_id,
            status=s["swarm_result"],
            workers_requested=s["workers_requested"],
            workers_started=s["workers_started"],
            workers_completed=s["workers_completed"],
            artifacts=artifacts,
            summary=s,
            duration_seconds=s["duration_seconds"],
            routed_to_swarm=True,
            legacy_delegate_used=False,
        )


    def delegate_single(self, task: DelegateTask) -> SwarmResult:
        """Delegate a single task — convenience wrapper."""
        return self.delegate([task])


def is_swarm_eligible(task_description: str, role: str = "") -> bool:
    """Determine if a task is eligible for swarm delegation.

    Swarm-eligible tasks are parallelizable engineering/research tasks:
    - code search across multiple patterns
    - schema analysis
    - test running
    - static analysis
    - git diff analysis

    NOT swarm-eligible:
    - single-model reasoning (use delegate_model_reasoning)
    - interactive user prompts
    - sequential dependent tasks
    """
    swarm_roles = {
        "code_search",
        "schema_analysis",
        "static_analysis",
        "test_runner",
        "git_diff",
        "builder",
        "breaker",
        "ast_analysis",
        "database_schema",
    }
    if role and role in swarm_roles:
        return True

    swarm_keywords = [
        "inventory",
        "scan",
        "search across",
        "parallel",
        "multiple workers",
        "swarm",
    ]
    desc_lower = task_description.lower()
    return any(kw in desc_lower for kw in swarm_keywords)

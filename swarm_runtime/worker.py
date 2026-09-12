"""Worker state model and specification.

Every worker has a unique identity, lifecycle state, and artifact contract.
States transition: QUEUED → STARTING → RUNNING → COMPLETED | FAILED | TIMED_OUT | CANCELLED
Intermediate states: WAITING_PROVIDER, RETRYING, FAILED_OVER
"""
from __future__ import annotations

import enum
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

_ACTOR_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")


class WorkerStatus(enum.Enum):
    """Worker lifecycle states — no invisible worker state."""
    QUEUED = "queued"
    STARTING = "starting"
    RUNNING = "running"
    WAITING_PROVIDER = "waiting_provider"
    RETRYING = "retrying"
    FAILED_OVER = "failed_over"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


@dataclass
class WorkerSpec:
    """Specification for a swarm worker — created before execution begins."""
    worker_id: str
    role: str
    worker_class: str  # e.g. "CodeSearchWorker", "ModelReasoningWorker"
    task: dict[str, Any]
    artifact_path: str  # relative to swarm run directory
    base_sha: str = ""
    worktree: str = ""  # path to git worktree, if builder
    owned_files: list[str] = field(default_factory=list)  # file ownership for builders
    primary_provider: str = ""
    fallback_providers: list[str] = field(default_factory=list)
    timeout_seconds: int = 120
    expected_artifact_schema: str = "findings"
    heartbeat_interval: int = 10
    # Canonical WorkOrder envelope bindings (backward compatible optional fields)
    mission_id: str = ""
    work_order_id: str = ""
    actor_id: str = ""
    owner: str = ""
    authority_class: str = ""
    context_hash: str = ""
    lease_id: str = ""
    lease_expires_at: float = 0.0
    parent_coordinator: str = ""
    authority_source: str = "NONE"
    control_plane: bool = False
    execution_posture: str = ""
    environment: str = ""
    data_reality: str = ""
    expected_output: str = ""
    evidence_required: bool = True
    dependencies: list[str] = field(default_factory=list)
    read_allowlist: list[str] = field(default_factory=list)
    write_allowlist: list[str] = field(default_factory=list)
    branch: str = ""
    merge_base: str = ""
    starting_clean_state: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    def validate_contract(self) -> None:
        if self.actor_id and not _ACTOR_ID_RE.match(self.actor_id):
            raise ValueError(f"INVALID_ACTOR_ID: {self.actor_id!r}")
        if self.actor_id == "hermes.canonical":
            raise ValueError("WORKER_IMPERSONATION_REFUSED")
        if self.actor_id == "copilot.engineering.01":
            if self.parent_coordinator != "hermes.canonical":
                raise ValueError("COPILOT_PARENT_MISMATCH")
            if self.authority_source != "NONE":
                raise ValueError("COPILOT_AUTHORITY_SOURCE_ELEVATION_REFUSED")
            if self.control_plane:
                raise ValueError("COPILOT_CONTROL_PLANE_FORBIDDEN")
        if self.worktree:
            wt = Path(self.worktree)
            if not wt.exists():
                raise ValueError("WORKTREE_NOT_FOUND")
        if self.owned_files and self.actor_id == "copilot.engineering.01":
            if not self.worktree:
                raise ValueError("WRITE_TASK_REQUIRES_ISOLATED_WORKTREE")
            if not self.starting_clean_state:
                raise ValueError("WORKTREE_MUST_START_CLEAN")
            if not self.branch:
                raise ValueError("WORKTREE_BRANCH_REQUIRED")


@dataclass
class WorkerState:
    """Live state of a worker — persisted to status.json in artifact store."""
    # Identity
    swarm_id: str
    worker_id: str
    role: str
    provider: str = ""
    model: str = ""
    base_sha: str = ""
    worktree: str = ""

    # Lifecycle
    status: WorkerStatus = WorkerStatus.QUEUED
    start_time: float | None = None
    end_time: float | None = None
    heartbeat_time: float | None = None
    exit_code: int | None = None

    # Task
    task: dict[str, Any] = field(default_factory=dict)
    expected_artifact: str = ""
    artifact_path: str = ""

    # Progress
    phase: str = ""
    files_processed: int = 0
    files_pending: int = 0
    cursor: str = ""  # checkpoint position
    partial_findings: list[dict] = field(default_factory=list)

    # Provider tracking
    provider_attempts: int = 0
    provider_state: str = ""
    last_provider_progress: float | None = None
    failover_count: int = 0

    # Errors
    errors: list[str] = field(default_factory=list)

    # Owned scope
    owned_scope: str = ""
    owned_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_spec(cls, swarm_id: str, spec: WorkerSpec) -> WorkerState:
        return cls(
            swarm_id=swarm_id,
            worker_id=spec.worker_id,
            role=spec.role,
            base_sha=spec.base_sha,
            worktree=spec.worktree,
            task=spec.task,
            expected_artifact=spec.expected_artifact_schema,
            artifact_path=spec.artifact_path,
            owned_files=spec.owned_files,
            owned_scope=", ".join(spec.owned_files) if spec.owned_files else spec.role,
            provider=spec.primary_provider,
        )

    def touch_heartbeat(self) -> None:
        self.heartbeat_time = time.time()

    def is_alive(self, max_silence: float = 30.0) -> bool:
        if self.status in (WorkerStatus.COMPLETED, WorkerStatus.FAILED, WorkerStatus.TIMED_OUT, WorkerStatus.CANCELLED):
            return False
        if self.heartbeat_time is None:
            return True  # just started
        return (time.time() - self.heartbeat_time) < max_silence

    def elapsed(self) -> float:
        if self.start_time is None:
            return 0.0
        end = self.end_time if self.end_time is not None else time.time()
        return end - self.start_time


@dataclass
class SwarmEvent:
    """Event ledger entry for swarm state transitions."""
    timestamp: float
    swarm_id: str
    worker_id: str
    event: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

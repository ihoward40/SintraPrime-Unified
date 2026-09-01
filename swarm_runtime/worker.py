"""Worker state model and specification.

Every worker has a unique identity, lifecycle state, and artifact contract.
States transition: QUEUED → STARTING → RUNNING → COMPLETED | FAILED | TIMED_OUT | CANCELLED
Intermediate states: WAITING_PROVIDER, RETRYING, FAILED_OVER
"""
from __future__ import annotations

import enum
import time
from dataclasses import asdict, dataclass, field
from typing import Any


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

    def to_dict(self) -> dict:
        return asdict(self)


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

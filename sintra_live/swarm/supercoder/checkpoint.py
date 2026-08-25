"""SuperCoder checkpoints — durable snapshots for crash recovery and worker rotation."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import json
import os
import tempfile


@dataclass(frozen=True)
class Checkpoint:
    """A single durable checkpoint snapshot."""
    checkpoint_id: str
    mission_id: str
    worker_id: str
    timestamp: str
    baseline_commit: str
    current_commit: str
    worktree: str
    active_task: str
    completed_tasks: Tuple[str, ...]
    next_task: str
    files_inspected: Tuple[str, ...]
    files_changed: Tuple[str, ...]
    hashes: Dict[str, str]  # path -> sha256
    test_results: Optional[Dict[str, Any]] = None
    findings: Tuple[str, ...] = ()
    unresolved_questions: Tuple[str, ...] = ()
    exact_resume_instruction: str = ""
    sequence: int = 0

    def to_json(self) -> bytes:
        return json.dumps(
            {
                "checkpoint_id": self.checkpoint_id,
                "mission_id": self.mission_id,
                "worker_id": self.worker_id,
                "timestamp": self.timestamp,
                "baseline_commit": self.baseline_commit,
                "current_commit": self.current_commit,
                "worktree": self.worktree,
                "active_task": self.active_task,
                "completed_tasks": list(self.completed_tasks),
                "next_task": self.next_task,
                "files_inspected": list(self.files_inspected),
                "files_changed": list(self.files_changed),
                "hashes": dict(self.hashes),
                "test_results": self.test_results,
                "findings": list(self.findings),
                "unresolved_questions": list(self.unresolved_questions),
                "exact_resume_instruction": self.exact_resume_instruction,
                "sequence": self.sequence,
            },
            sort_keys=True,
        ).encode()

    def checkpoint_hash(self) -> str:
        return hashlib.sha256(self.to_json()).hexdigest()


@dataclass
class CheckpointSequence:
    """Ordered sequence of checkpoints for a mission."""
    mission_id: str
    checkpoints: List[Checkpoint] = field(default_factory=list)

    def latest(self) -> Optional[Checkpoint]:
        return self.checkpoints[-1] if self.checkpoints else None

    def append(self, cp: Checkpoint) -> None:
        self.checkpoints.append(cp)

    def count(self) -> int:
        return len(self.checkpoints)


class CheckpointStore:
    """Durable file-backed checkpoint storage with atomic writes.

    Checkpoints survive worker timeouts, process crashes, and restarts.
    """

    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _mission_dir(self, mission_id: str) -> Path:
        d = self.root / mission_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _checkpoint_path(self, mission_id: str, checkpoint_id: str) -> Path:
        return self._mission_dir(mission_id) / f"{checkpoint_id}.json"

    def save(self, cp: Checkpoint) -> Path:
        """Atomically save a checkpoint to disk."""
        target = self._checkpoint_path(cp.mission_id, cp.checkpoint_id)
        tmp = target.with_suffix(".tmp")
        raw = cp.to_json()
        with open(tmp, "wb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        os.replace(str(tmp), str(target))
        # Verify readback
        with open(target, "rb") as f:
            readback = f.read()
        if readback != raw:
            raise IOError(f"Checkpoint readback mismatch for {cp.checkpoint_id}")
        return target

    def load(self, mission_id: str, checkpoint_id: str) -> Checkpoint:
        """Load a specific checkpoint."""
        path = self._checkpoint_path(mission_id, checkpoint_id)
        with open(path, "rb") as f:
            data = json.loads(f.read())
        return Checkpoint(
            checkpoint_id=data["checkpoint_id"],
            mission_id=data["mission_id"],
            worker_id=data["worker_id"],
            timestamp=data["timestamp"],
            baseline_commit=data["baseline_commit"],
            current_commit=data["current_commit"],
            worktree=data["worktree"],
            active_task=data["active_task"],
            completed_tasks=tuple(data["completed_tasks"]),
            next_task=data["next_task"],
            files_inspected=tuple(data["files_inspected"]),
            files_changed=tuple(data["files_changed"]),
            hashes=dict(data["hashes"]),
            test_results=data.get("test_results"),
            findings=tuple(data.get("findings", [])),
            unresolved_questions=tuple(data.get("unresolved_questions", [])),
            exact_resume_instruction=data.get("exact_resume_instruction", ""),
            sequence=data.get("sequence", 0),
        )

    def load_latest(self, mission_id: str) -> Optional[Checkpoint]:
        """Load the most recent checkpoint for a mission (by sequence number)."""
        d = self._mission_dir(mission_id)
        files = sorted(d.glob("*.json"))
        if not files:
            return None
        # Load all and find the one with the highest sequence
        latest = None
        latest_seq = -1
        for f in files:
            with open(f, "rb") as fh:
                data = json.loads(fh.read())
            seq = data.get("sequence", 0)
            if seq > latest_seq:
                latest_seq = seq
                latest = data
        return self.load(mission_id, latest["checkpoint_id"])

    def list_checkpoints(self, mission_id: str) -> List[str]:
        """List all checkpoint IDs for a mission."""
        d = self._mission_dir(mission_id)
        return sorted(p.stem for p in d.glob("*.json"))

    def load_sequence(self, mission_id: str) -> CheckpointSequence:
        """Load all checkpoints for a mission in order."""
        seq = CheckpointSequence(mission_id=mission_id)
        for cp_id in self.list_checkpoints(mission_id):
            seq.append(self.load(mission_id, cp_id))
        return seq


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def create_checkpoint(
    mission_id: str,
    worker_id: str,
    baseline_commit: str,
    current_commit: str,
    worktree: str,
    active_task: str,
    completed_tasks: Tuple[str, ...],
    next_task: str,
    files_inspected: Tuple[str, ...] = (),
    files_changed: Tuple[str, ...] = (),
    hashes: Optional[Dict[str, str]] = None,
    test_results: Optional[Dict[str, Any]] = None,
    findings: Tuple[str, ...] = (),
    unresolved_questions: Tuple[str, ...] = (),
    exact_resume_instruction: str = "",
    sequence: int = 0,
) -> Checkpoint:
    """Factory for creating a checkpoint with timestamp and ID."""
    timestamp = _utc_now()
    checkpoint_id = hashlib.sha256(
        f"{mission_id}:{worker_id}:{timestamp}:{sequence}".encode()
    ).hexdigest()[:24]
    return Checkpoint(
        checkpoint_id=checkpoint_id,
        mission_id=mission_id,
        worker_id=worker_id,
        timestamp=timestamp,
        baseline_commit=baseline_commit,
        current_commit=current_commit,
        worktree=worktree,
        active_task=active_task,
        completed_tasks=completed_tasks,
        next_task=next_task,
        files_inspected=files_inspected,
        files_changed=files_changed,
        hashes=hashes or {},
        test_results=test_results,
        findings=findings,
        unresolved_questions=unresolved_questions,
        exact_resume_instruction=exact_resume_instruction,
        sequence=sequence,
    )
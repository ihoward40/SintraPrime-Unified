"""Artifact store — atomic file writes for worker outputs.

Every worker must produce a structured artifact. The controller creates the
worker directory and initial status file BEFORE execution begins. Artifacts
are written atomically: write to .tmp → fsync → rename.
"""
from __future__ import annotations

import contextlib
import json
import os
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from .worker import SwarmEvent, WorkerState

ARTIFACT_SCHEMA_VERSION = "1.0.0"


class ArtifactStore:
    """Manages on-disk artifacts for a swarm run."""

    def __init__(self, run_dir: str | Path) -> None:
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.event_log: list[SwarmEvent] = []
        self._event_log_path = self.run_dir / "event_log.jsonl"
        self._write_lock = threading.RLock()

    def swarm_dir(self) -> Path:
        return self.run_dir

    def worker_dir(self, worker_id: str) -> Path:
        d = self.run_dir / f"worker-{worker_id}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def write_status(self, worker_id: str, state: WorkerState) -> None:
        """Write worker status.json atomically."""
        path = self.worker_dir(worker_id) / "status.json"
        self._atomic_write_json(path, state.to_dict())

    def read_status(self, worker_id: str) -> dict | None:
        """Read worker status.json."""
        path = self.worker_dir(worker_id) / "status.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def write_heartbeat(self, worker_id: str, state: WorkerState) -> None:
        """Write heartbeat.json atomically."""
        hb = {
            "worker_id": worker_id,
            "state": state.status.value,
            "phase": state.phase,
            "provider_state": state.provider_state,
            "last_progress_at": state.last_provider_progress,
            "files_processed": state.files_processed,
            "files_pending": state.files_pending,
            "timestamp": time.time(),
        }
        path = self.worker_dir(worker_id) / "heartbeat.json"
        self._atomic_write_json(path, hb)

    def read_heartbeat(self, worker_id: str) -> dict | None:
        path = self.worker_dir(worker_id) / "heartbeat.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def write_findings(self, worker_id: str, findings: dict[str, Any],
                       state: WorkerState, evidence: list | None = None) -> Path:
        """Write findings.json atomically with full schema."""
        artifact = {
            "schema_version": ARTIFACT_SCHEMA_VERSION,
            "swarm_id": state.swarm_id,
            "worker_id": worker_id,
            "base_sha": state.base_sha,
            "task_hash": _hash_task(state.task),
            "started_at": state.start_time,
            "updated_at": time.time(),
            "state": state.status.value,
            "findings": findings,
            "evidence": evidence or [],
            "errors": state.errors,
        }
        path = self.worker_dir(worker_id) / "findings.json"
        self._atomic_write_json(path, artifact)
        return path

    def write_checkpoint(self, worker_id: str, state: WorkerState) -> None:
        """Write checkpoint.json for resume support."""
        ckpt = {
            "worker_id": worker_id,
            "cursor": state.cursor,
            "processed_files": state.files_processed,
            "pending_files": state.files_pending,
            "partial_findings": state.partial_findings,
            "phase": state.phase,
            "timestamp": time.time(),
        }
        path = self.worker_dir(worker_id) / "checkpoint.json"
        self._atomic_write_json(path, ckpt)

    def read_checkpoint(self, worker_id: str) -> dict | None:
        path = self.worker_dir(worker_id) / "checkpoint.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def append_log(self, worker_id: str, line: str, stream: str = "stdout") -> None:
        """Append a line to the worker's log file."""
        path = self.worker_dir(worker_id) / f"{stream}.log"
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def write_manifest(self, manifest: dict) -> None:
        """Write the swarm manifest.json."""
        path = self.run_dir / "manifest.json"
        self._atomic_write_json(path, manifest)

    def write_summary(self, summary: dict) -> Path:
        """Write the final swarm_summary.json."""
        path = self.run_dir / "swarm_summary.json"
        self._atomic_write_json(path, summary)
        return path

    def record_event(self, event: SwarmEvent) -> None:
        """Record an event to the event ledger (JSONL format)."""
        self.event_log.append(event)
        with open(self._event_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict()) + "\n")

    def validate_artifact(self, worker_id: str) -> dict:
        """Validate that a worker produced a valid findings.json artifact."""
        path = self.worker_dir(worker_id) / "findings.json"
        if not path.exists():
            return {"valid": False, "reason": "findings.json missing", "path": str(path)}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            return {"valid": False, "reason": f"invalid JSON: {e}", "path": str(path)}
        required = ["schema_version", "swarm_id", "worker_id", "findings", "state"]
        missing = [k for k in required if k not in data]
        if missing:
            return {"valid": False, "reason": f"missing fields: {missing}", "path": str(path)}
        if data.get("state") != "completed":
            return {"valid": False, "reason": f"state is '{data.get('state')}', not 'completed'", "path": str(path)}
        return {"valid": True, "path": str(path), "findings_count": len(data.get("findings", {}))}

    def _atomic_write_json(self, path: Path, data: dict) -> None:
        """Write JSON atomically: unique same-directory temp, then replace."""
        payload = json.dumps(data, indent=2, default=str)
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._write_lock:
            fd, tmp_name = tempfile.mkstemp(
                prefix=f".{path.name}.{os.getpid()}.{threading.get_ident()}.",
                suffix=f".{uuid.uuid4().hex}.tmp",
                dir=str(path.parent),
                text=True,
            )
            tmp = Path(tmp_name)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                try:
                    os.replace(str(tmp), str(path))
                except PermissionError:
                    with contextlib.suppress(FileNotFoundError, PermissionError):
                        tmp.unlink()
                    raise
            finally:
                with contextlib.suppress(FileNotFoundError, PermissionError):
                    tmp.unlink()


def _hash_task(task: dict) -> str:
    """Create a stable hash of the task for deduplication."""
    import hashlib
    raw = json.dumps(task, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]

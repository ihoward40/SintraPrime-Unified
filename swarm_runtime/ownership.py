"""File ownership enforcement — prevents cross-worker write collisions.

Ownership is enforced by runtime policy, not merely prompt instructions.
If a worker attempts to write outside its owned files:
  WRITE_DENIED = TRUE
  Security event recorded
  File unchanged
  Worker fails closed
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class OwnershipViolation:
    """Recorded when a worker attempts to write outside its authority."""
    worker_id: str
    attempted_path: str
    owned_paths: list[str]
    timestamp: float
    action: str = "WRITE_DENIED"
    file_changed: bool = False


class OwnershipRegistry:
    """Tracks file ownership across workers in a swarm.

    Enforces that only the designated owner of a file may write to it.
    """
    def __init__(self) -> None:
        self._ownership: dict[str, set[str]] = {}  # worker_id → set of owned paths
        self._path_to_owner: dict[str, str] = {}  # path → worker_id
        self._violations: list[OwnershipViolation] = []

    def register(self, worker_id: str, owned_files: list[str]) -> None:
        """Register a worker's owned files."""
        owned_set = set()
        for path in owned_files:
            normalized = str(Path(path)).replace("\\", "/")
            owned_set.add(normalized)
            self._path_to_owner[normalized] = worker_id
        self._ownership[worker_id] = owned_set

    def can_write(self, worker_id: str, path: str) -> bool:
        """Check if a worker is allowed to write to a path."""
        normalized = str(Path(path)).replace("\\", "/")
        owner = self._path_to_owner.get(normalized)
        if owner is None:
            # Unclaimed path — allow if worker has no ownership restriction
            # or if the path is in the worker's owned_files list
            self._ownership.get(worker_id, set())
            # If worker has no ownership declared, deny by default
            # (DENY_UNDECLARED_CAPABILITY = TRUE)
            return False
        return owner == worker_id

    def check_and_record(self, worker_id: str, path: str) -> OwnershipViolation | None:
        """Check write permission and record violation if denied."""
        if self.can_write(worker_id, path):
            return None

        violation = OwnershipViolation(
            worker_id=worker_id,
            attempted_path=str(Path(path)).replace("\\", "/"),
            owned_paths=list(self._ownership.get(worker_id, set())),
            timestamp=time.time(),
            action="WRITE_DENIED",
            file_changed=False,
        )
        self._violations.append(violation)
        return violation

    def get_violations(self) -> list[OwnershipViolation]:
        return list(self._violations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ownership_map": {k: list(v) for k, v in self._ownership.items()},
            "path_to_owner": self._path_to_owner,
            "violations": [
                {
                    "worker_id": v.worker_id,
                    "attempted_path": v.attempted_path,
                    "owned_paths": v.owned_paths,
                    "timestamp": v.timestamp,
                    "action": v.action,
                    "file_changed": v.file_changed,
                }
                for v in self._violations
            ],
        }

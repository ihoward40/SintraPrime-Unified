"""File ownership enforcement — prevents cross-worker write collisions.

Ownership is enforced by runtime policy, not merely prompt instructions.
If a worker attempts to write outside its owned files:
  WRITE_DENIED = TRUE
  Security event recorded
  File unchanged
  Worker fails closed
"""
from __future__ import annotations

import fnmatch
import time
from dataclasses import dataclass
from pathlib import PurePosixPath
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
        self._claims: dict[str, str] = {}  # normalized claim pattern/path → worker_id
        self._violations: list[OwnershipViolation] = []

    def register(self, worker_id: str, owned_files: list[str]) -> None:
        """Register a worker's owned files."""
        owned_set = set()
        for path in owned_files:
            normalized = self._normalize(path)
            owned_set.add(normalized)
            current_owner = self._claims.get(normalized)
            if current_owner is not None and current_owner != worker_id:
                raise ValueError(
                    f"WRITE_SCOPE_CONFLICT: {normalized} already owned by {current_owner}"
                )
            for claimed, owner in self._claims.items():
                if owner == worker_id:
                    continue
                if self._claims_overlap(claimed, normalized):
                    raise ValueError(
                        f"WRITE_SCOPE_OVERLAP: {normalized} conflicts with {claimed} ({owner})"
                    )
            self._claims[normalized] = worker_id
        self._ownership[worker_id] = owned_set

    def can_write(self, worker_id: str, path: str) -> bool:
        """Check if a worker is allowed to write to a path."""
        normalized = self._normalize(path)
        matching_owners = {
            owner for claim, owner in self._claims.items() if self._path_matches_claim(normalized, claim)
        }
        if not matching_owners:
            return False
        return matching_owners == {worker_id}

    def check_and_record(self, worker_id: str, path: str) -> OwnershipViolation | None:
        """Check write permission and record violation if denied."""
        if self.can_write(worker_id, path):
            return None

        violation = OwnershipViolation(
            worker_id=worker_id,
            attempted_path=self._normalize(path),
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
            "path_to_owner": self._claims,
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

    @staticmethod
    def _normalize(path: str) -> str:
        p = str(PurePosixPath(str(path).replace("\\", "/")))
        if p.startswith("./"):
            return p[2:]
        return p

    @staticmethod
    def _path_matches_claim(path: str, claim: str) -> bool:
        if claim.endswith("/**"):
            base = claim[:-3].rstrip("/")
            return path == base or path.startswith(base + "/")
        if "*" in claim or "?" in claim or "[" in claim:
            return fnmatch.fnmatch(path, claim)
        return path == claim

    @classmethod
    def _claims_overlap(cls, a: str, b: str) -> bool:
        if a == b:
            return True
        if a.endswith("/**"):
            base = a[:-3].rstrip("/")
            if b == base or b.startswith(base + "/"):
                return True
        if b.endswith("/**"):
            base = b[:-3].rstrip("/")
            if a == base or a.startswith(base + "/"):
                return True
        if any(tok in a for tok in ("*", "?", "[")) and cls._path_matches_claim(b, a):
            return True
        if any(tok in b for tok in ("*", "?", "[")) and cls._path_matches_claim(a, b):
            return True
        return False

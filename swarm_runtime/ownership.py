"""File ownership enforcement — prevents cross-worker write collisions.

Ownership is enforced by runtime policy, not merely prompt instructions.
If a worker attempts to write outside its owned files:
  WRITE_DENIED = TRUE
  Security event recorded
  File unchanged
  Worker fails closed
"""
from __future__ import annotations

import re
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
            return PurePosixPath(path).match(claim)
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
        a_glob = any(tok in a for tok in ("*", "?", "["))
        b_glob = any(tok in b for tok in ("*", "?", "["))
        if a_glob and not b_glob and cls._path_matches_claim(b, a):
            return True
        if b_glob and not a_glob and cls._path_matches_claim(a, b):
            return True
        if a_glob and b_glob:
            if cls._glob_might_overlap(a, b):
                return True
        return False

    @staticmethod
    def _static_prefix(pattern: str) -> str:
        first_glob = len(pattern)
        for tok in ("*", "?", "["):
            idx = pattern.find(tok)
            if idx != -1:
                first_glob = min(first_glob, idx)
        return pattern[:first_glob].rstrip("/")

    @staticmethod
    def _is_same_or_parent(parent: str, child: str) -> bool:
        if not parent:
            return True
        return child == parent or child.startswith(parent + "/")

    @classmethod
    def _glob_might_overlap(cls, a: str, b: str) -> bool:
        a_prefix = cls._static_prefix(a)
        b_prefix = cls._static_prefix(b)
        if not (cls._is_same_or_parent(a_prefix, b_prefix) or cls._is_same_or_parent(b_prefix, a_prefix)):
            return False
        if cls._root_glob_overlap(a, b):
            return True
        if cls._glob_disjoint_by_extension(a, b):
            return False
        if cls._glob_disjoint_by_filename_pattern(a, b):
            return False
        return True

    @staticmethod
    def _glob_disjoint_by_extension(a: str, b: str) -> bool:
        if "**" in a or "**" in b:
            return False
        a_dir, _, a_name = a.rpartition("/")
        b_dir, _, b_name = b.rpartition("/")
        if a_dir != b_dir:
            return False
        ext_pattern = re.compile(r"^\*\.([A-Za-z0-9_-]+)$")
        a_match = ext_pattern.match(a_name)
        b_match = ext_pattern.match(b_name)
        if not a_match or not b_match:
            return False
        return a_match.group(1) != b_match.group(1)

    @staticmethod
    def _glob_disjoint_by_filename_pattern(a: str, b: str) -> bool:
        if "**" in a or "**" in b:
            return False
        a_dir, _, a_name = a.rpartition("/")
        b_dir, _, b_name = b.rpartition("/")
        if a_dir != b_dir:
            return False
        a_parts = OwnershipRegistry._simple_wildcard_parts(a_name)
        b_parts = OwnershipRegistry._simple_wildcard_parts(b_name)
        if not a_parts or not b_parts:
            return False
        a_prefix, a_suffix = a_parts
        b_prefix, b_suffix = b_parts
        if a_suffix != b_suffix:
            return False
        return not (a_prefix.startswith(b_prefix) or b_prefix.startswith(a_prefix))

    @staticmethod
    def _simple_wildcard_parts(name: str) -> tuple[str, str] | None:
        if "?" in name or "[" in name:
            return None
        if name.count("*") != 1:
            return None
        prefix, suffix = name.split("*", 1)
        return prefix, suffix

    @staticmethod
    def _root_glob_overlap(a: str, b: str) -> bool:
        root_ext = re.compile(r"^\*\.([A-Za-z0-9_-]+)$")
        a_root = root_ext.match(a)
        b_root = root_ext.match(b)
        if a_root and b.endswith(f".{a_root.group(1)}"):
            return True
        if b_root and a.endswith(f".{b_root.group(1)}"):
            return True
        return False

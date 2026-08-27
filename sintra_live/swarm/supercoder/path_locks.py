"""SuperCoder path locks — single-writer enforcement for concurrent missions."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional
import hashlib


@dataclass
class PathLock:
    """A write lock on a specific file path."""
    path: str
    mission_id: str
    packet_id: str
    worker_id: str
    acquired_at: str

    def is_expired(self, timeout_seconds: int = 600) -> bool:
        """Locks expire after timeout to prevent deadlocks from crashed workers."""
        acquired = datetime.fromisoformat(self.acquired_at.replace("Z", "+00:00"))
        elapsed = (datetime.now(timezone.utc) - acquired).total_seconds()
        return elapsed > timeout_seconds


class PathLockRegistry:
    """Enforces ONE active writer per path across all concurrent missions.

    Multiple readers are always allowed.
    Parallel writes to the same path are prohibited.
    """

    def __init__(self, lock_timeout_seconds: int = 600):
        self._locks: Dict[str, PathLock] = {}
        self._lock_timeout = lock_timeout_seconds

    @property
    def lock_timeout_seconds(self) -> int:
        return self._lock_timeout

    def restore_lock(self, lock: PathLock) -> None:
        """Restore a persisted lock fail-closed for restart reconciliation."""
        if lock.path in self._locks:
            raise ValueError(f"Duplicate restored path lock {lock.path}")
        self._locks[lock.path] = lock

    def acquire(self, path: str, mission_id: str, packet_id: str, worker_id: str) -> bool:
        """Try to acquire a write lock. Returns True if acquired."""
        # Check if existing lock exists and is still valid
        existing = self._locks.get(path)
        if existing is not None:
            if not existing.is_expired(self._lock_timeout):
                # Lock is held by someone else
                if existing.mission_id == mission_id and existing.worker_id == worker_id:
                    return True  # Re-acquiring own lock
                return False
            # Expired lock — remove it

        self._locks[path] = PathLock(
            path=path,
            mission_id=mission_id,
            packet_id=packet_id,
            worker_id=worker_id,
            acquired_at=_utc_now(),
        )
        return True

    def release(self, path: str, mission_id: str, worker_id: str) -> bool:
        """Release a write lock. Returns True if released."""
        existing = self._locks.get(path)
        if existing is None:
            return True  # Already released
        if existing.mission_id == mission_id and existing.worker_id == worker_id:
            del self._locks[path]
            return True
        return False

    def release_all_for_worker(self, mission_id: str, worker_id: str) -> int:
        """Release all locks held by a specific worker. Returns count released."""
        to_release = [
            path for path, lock in self._locks.items()
            if lock.mission_id == mission_id and lock.worker_id == worker_id
        ]
        for path in to_release:
            del self._locks[path]
        return len(to_release)

    def is_locked(self, path: str) -> bool:
        """Check if a path is currently locked."""
        existing = self._locks.get(path)
        if existing is None:
            return False
        if existing.is_expired(self._lock_timeout):
            del self._locks[path]
            return False
        return True

    def locked_paths(self) -> Dict[str, PathLock]:
        """Return all currently locked paths."""
        # Clean expired locks first
        expired = [
            path for path, lock in self._locks.items()
            if lock.is_expired(self._lock_timeout)
        ]
        for path in expired:
            del self._locks[path]
        return dict(self._locks)

    def acquire_batch(self, paths: list[str], mission_id: str, packet_id: str, worker_id: str) -> bool:
        """Try to acquire locks for multiple paths atomically.
        If any fail, release all acquired and return False.
        """
        acquired = []
        for path in paths:
            if self.acquire(path, mission_id, packet_id, worker_id):
                acquired.append(path)
            else:
                # Rollback
                for p in acquired:
                    self.release(p, mission_id, worker_id)
                return False
        return True

    def release_batch(self, paths: list[str], mission_id: str, worker_id: str) -> int:
        """Release locks for multiple paths. Returns count released."""
        count = 0
        for path in paths:
            if self.release(path, mission_id, worker_id):
                count += 1
        return count


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
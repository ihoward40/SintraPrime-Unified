"""Durable SuperCoder V2.1 runtime state and lease-based supervisor locking."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

from .context_capsule import ContextCapsule
from .path_locks import PathLock, PathLockRegistry
from .role_registry import QualityLevel, RoleAssignment, RoleRegistry, SuperCoderRole
from .work_packet import PacketScheduler, PacketStatus, WorkPacket


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _payload_hash(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _atomic_integrity_write(path: Path, kind: str, payload: Dict[str, Any]) -> Path:
    envelope = {kind: payload, f"{kind}_sha256": _payload_hash(payload)}
    raw = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with open(temp, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)
    if path.read_bytes() != raw:
        raise IOError(f"{kind} readback mismatch: {path}")
    return path


def _integrity_read(path: Path, kind: str) -> Dict[str, Any]:
    envelope = json.loads(path.read_bytes())
    payload = envelope[kind]
    if _payload_hash(payload) != envelope.get(f"{kind}_sha256"):
        raise ValueError(f"{kind} integrity verification failed: {path}")
    return payload


@dataclass(frozen=True)
class SupervisorLease:
    mission_id: str
    owner_id: str
    epoch: int
    acquired_at: str
    heartbeat_at: str
    expires_at: str

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        return (now or _now()) >= _parse(self.expires_at)


class SupervisorLeaseStore:
    """Cross-process mission lease using atomic exclusive file creation."""

    def __init__(self, root: Path | str, lease_seconds: int = 60):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.lease_seconds = lease_seconds

    def _path(self, mission_id: str) -> Path:
        return self.root / f"{mission_id}.lease.json"

    def _epoch_path(self, mission_id: str) -> Path:
        return self.root / f"{mission_id}.epoch"

    def _next_epoch(self, mission_id: str) -> int:
        path = self._epoch_path(mission_id)
        previous = int(path.read_text(encoding="utf-8")) if path.exists() else 0
        epoch = previous + 1
        temp = path.with_suffix(".tmp")
        temp.write_text(str(epoch), encoding="utf-8")
        os.replace(temp, path)
        return epoch

    def current(self, mission_id: str) -> Optional[SupervisorLease]:
        path = self._path(mission_id)
        if not path.exists():
            return None
        data = _integrity_read(path, "lease")
        return SupervisorLease(**data)

    def acquire(self, mission_id: str, owner_id: str) -> SupervisorLease:
        path = self._path(mission_id)
        for _ in range(3):
            existing = self.current(mission_id)
            if existing and not existing.is_expired():
                if existing.owner_id == owner_id:
                    return existing
                raise RuntimeError(
                    f"Mission {mission_id} already has active supervisor {existing.owner_id}"
                )
            if existing and existing.is_expired():
                stale = path.with_name(path.name + f".stale.{existing.epoch}")
                try:
                    os.replace(path, stale)
                except FileNotFoundError:
                    continue
            epoch = self._next_epoch(mission_id)
            now = _now()
            lease = SupervisorLease(
                mission_id=mission_id,
                owner_id=owner_id,
                epoch=epoch,
                acquired_at=_iso(now),
                heartbeat_at=_iso(now),
                expires_at=_iso(now + timedelta(seconds=self.lease_seconds)),
            )
            payload = asdict(lease)
            envelope = {
                "lease": payload,
                "lease_sha256": _payload_hash(payload),
            }
            raw = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
            try:
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, "wb") as handle:
                    handle.write(raw)
                    handle.flush()
                    os.fsync(handle.fileno())
                return lease
            except FileExistsError:
                continue
        raise RuntimeError(f"Unable to acquire active supervisor lease for {mission_id}")

    def heartbeat(self, mission_id: str, owner_id: str, epoch: int) -> SupervisorLease:
        lease = self.current(mission_id)
        if not lease or lease.owner_id != owner_id or lease.epoch != epoch or lease.is_expired():
            raise PermissionError("Supervisor lease is absent, stale, or owned by another process")
        now = _now()
        renewed = SupervisorLease(
            mission_id=mission_id,
            owner_id=owner_id,
            epoch=epoch,
            acquired_at=lease.acquired_at,
            heartbeat_at=_iso(now),
            expires_at=_iso(now + timedelta(seconds=self.lease_seconds)),
        )
        _atomic_integrity_write(self._path(mission_id), "lease", asdict(renewed))
        return renewed

    def release(self, mission_id: str, owner_id: str, epoch: int) -> None:
        lease = self.current(mission_id)
        if not lease:
            return
        if lease.owner_id != owner_id or lease.epoch != epoch:
            raise PermissionError("Cannot release another supervisor's lease")
        self._path(mission_id).unlink(missing_ok=True)

    def force_expire_for_test(self, mission_id: str) -> None:
        lease = self.current(mission_id)
        if not lease:
            return
        expired = SupervisorLease(
            mission_id=lease.mission_id,
            owner_id=lease.owner_id,
            epoch=lease.epoch,
            acquired_at=lease.acquired_at,
            heartbeat_at=lease.heartbeat_at,
            expires_at=_iso(_now() - timedelta(seconds=1)),
        )
        _atomic_integrity_write(self._path(mission_id), "lease", asdict(expired))


class RuntimeStateStore:
    """Integrity-checked persistence for scheduler, roles, path locks, and capsules."""

    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, mission_id: str, kind: str) -> Path:
        return self.root / mission_id / f"{kind}.json"

    def save_scheduler(self, mission_id: str, scheduler: PacketScheduler) -> Path:
        packets = [json.loads(packet.to_json()) for packet in scheduler.all_packets()]
        payload = {"mission_id": mission_id, "packets": packets}
        return _atomic_integrity_write(self._path(mission_id, "scheduler"), "scheduler", payload)

    def load_scheduler(self, mission_id: str) -> PacketScheduler:
        data = _integrity_read(self._path(mission_id, "scheduler"), "scheduler")
        scheduler = PacketScheduler(mission_id)
        for item in data["packets"]:
            packet = WorkPacket(
                packet_id=item["packet_id"], mission_id=item["mission_id"],
                objective=item["objective"], exact_files=tuple(item["exact_files"]),
                required_reads=tuple(item["required_reads"]),
                starting_checkpoint_id=item.get("starting_checkpoint_id"),
                expected_delta=item.get("expected_delta", ""), tests=tuple(item.get("tests", ())),
                prohibited_actions=tuple(item.get("prohibited_actions", ())),
                completion_condition=item.get("completion_condition", ""),
                handoff_condition=item.get("handoff_condition", ""),
                worker_id=item.get("worker_id", ""), status=PacketStatus(item["status"]),
                created_at=item.get("created_at", ""), sequence=item.get("sequence", 0),
            )
            scheduler.restore_packet(packet)
        return scheduler

    def save_roles(self, mission_id: str, roles: RoleRegistry) -> Path:
        payload = {
            "mission_id": mission_id,
            "assignments": [
                {"role": a.role.value, "worker_id": a.worker_id, "packet_id": a.packet_id,
                 "mission_id": a.mission_id}
                for a in roles.get_assignments_for_mission(mission_id)
            ],
            "quality": roles.get_quality(mission_id).value,
        }
        return _atomic_integrity_write(self._path(mission_id, "roles"), "roles", payload)

    def load_roles(self, mission_id: str) -> RoleRegistry:
        data = _integrity_read(self._path(mission_id, "roles"), "roles")
        roles = RoleRegistry()
        roles.set_quality(mission_id, QualityLevel(data["quality"]))
        for item in data["assignments"]:
            roles.assign(SuperCoderRole(item["role"]), item["worker_id"], item["packet_id"], mission_id)
        return roles

    def save_path_locks(self, mission_id: str, locks: PathLockRegistry) -> Path:
        payload = {
            "mission_id": mission_id,
            "locks": [asdict(lock) for lock in locks.locked_paths().values()],
            "lock_timeout": locks.lock_timeout_seconds,
        }
        return _atomic_integrity_write(self._path(mission_id, "path_locks"), "path_locks", payload)

    def load_path_locks(self, mission_id: str) -> PathLockRegistry:
        data = _integrity_read(self._path(mission_id, "path_locks"), "path_locks")
        locks = PathLockRegistry(lock_timeout_seconds=data["lock_timeout"])
        for item in data["locks"]:
            locks.restore_lock(PathLock(**item))
        return locks

    def save_context_capsule(self, mission_id: str, capsule: ContextCapsule) -> Path:
        payload = json.loads(capsule.to_json())
        return _atomic_integrity_write(self._path(mission_id, "capsule"), "capsule", payload)

    def load_context_capsule(self, mission_id: str) -> ContextCapsule:
        data = _integrity_read(self._path(mission_id, "capsule"), "capsule")
        return ContextCapsule(
            mission_id=data["mission_id"], mission_objective=data["mission_objective"],
            architecture_rules=tuple(data["architecture_rules"]), current_baseline=data["current_baseline"],
            owned_paths=tuple(data["owned_paths"]), current_phase=data["current_phase"],
            completed_packets=tuple(data["completed_packets"]), active_packet=data.get("active_packet"),
            last_checkpoint_id=data.get("last_checkpoint_id"), relevant_apis=tuple(data["relevant_apis"]),
            discoveries=tuple(data["discoveries"]), failing_tests=tuple(data["failing_tests"]),
            next_action=data["next_action"], prohibited_actions=tuple(data["prohibited_actions"]),
            authority_delta=data.get("authority_delta", 0), side_effects=data.get("side_effects", 0),
        )

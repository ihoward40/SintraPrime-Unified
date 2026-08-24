"""Crash-safe cross-process CAS store for immutable L2-I1 missions."""

from __future__ import annotations

import os
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator, Optional

from .errors import (
    DenialCode,
    IntegrityError,
    LockTimeoutError,
    MissionStoreError,
    PersistenceError,
    SchemaError,
    TransitionOutcome,
    TransitionResult,
)
from .model import (
    EVENT_SCHEMA_VERSION,
    MissionAggregate,
    MissionEvent,
    MissionIdentity,
    MissionScope,
    TransitionRequest,
    utc_now,
)
from .state import MissionState, is_i1_transition_enabled, is_terminal

if os.name == "nt":
    import msvcrt
else:  # pragma: no cover - exercised on POSIX CI only
    import fcntl


class MissionStore:
    """One canonical mission document per mission ID, guarded by file locks."""

    def __init__(self, store_root: Path | str, *, lock_timeout_ms: int = 5000):
        if isinstance(lock_timeout_ms, bool) or not isinstance(lock_timeout_ms, int) or lock_timeout_ms < 1:
            raise ValueError("lock_timeout_ms must be a positive integer")
        self.root = Path(store_root)
        self.missions_dir = self.root / "missions"
        self.locks_dir = self.root / "locks"
        self.lock_timeout_ms = lock_timeout_ms
        self.missions_dir.mkdir(parents=True, exist_ok=True)
        self.locks_dir.mkdir(parents=True, exist_ok=True)

    def _target_path(self, mission_id: str) -> Path:
        # MissionIdentity performs the frozen safe identifier validation.
        MissionIdentity(
            program_id="validation",
            gate_id="validation",
            mission_id=mission_id,
            request_id="validation",
            request_sha256="0" * 64,
            principal_identity_reference="validation",
            mission_scope_sha256="0" * 64,
            authority_snapshot_reference="validation",
        )
        return self.missions_dir / f"{mission_id}.json"

    def _lock_path(self, mission_id: str) -> Path:
        self._target_path(mission_id)
        return self.locks_dir / f"{mission_id}.lock"

    def _temp_paths(self, mission_id: str) -> list[Path]:
        return sorted(self.missions_dir.glob(f".{mission_id}.*.tmp"))

    @contextmanager
    def _mission_lock(self, mission_id: str) -> Iterator[None]:
        lock_path = self._lock_path(mission_id)
        handle = open(lock_path, "a+b", buffering=0)
        if handle.seek(0, os.SEEK_END) == 0:
            handle.write(b"\0")
        deadline = time.monotonic() + self.lock_timeout_ms / 1000
        acquired = False
        try:
            while not acquired:
                try:
                    handle.seek(0)
                    if os.name == "nt":
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    else:  # pragma: no cover
                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                except (OSError, BlockingIOError):
                    if time.monotonic() >= deadline:
                        raise LockTimeoutError(f"lock timeout for mission {mission_id}")
                    time.sleep(0.01)
            yield
        finally:
            if acquired:
                handle.seek(0)
                if os.name == "nt":
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:  # pragma: no cover
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

    def create(self, identity: MissionIdentity, scope: MissionScope, *, created_at: str) -> MissionAggregate:
        mission_id = identity.mission_id
        target = self._target_path(mission_id)
        proposed = MissionAggregate.genesis(identity, scope, created_at)
        with self._mission_lock(mission_id):
            self._deny_stale_temps(mission_id)
            if target.exists():
                existing = self._read_verified(target)
                if existing.canonical_bytes() == proposed.canonical_bytes():
                    return existing
                raise MissionStoreError("MISSION_COLLISION")
            self._durable_commit(target, proposed.canonical_bytes(), mission_id)
            return self._read_verified(target)

    def load(self, mission_id: str, *, allow_stale_temp_read: bool = True) -> MissionAggregate:
        target = self._target_path(mission_id)
        with self._mission_lock(mission_id):
            temps = self._temp_paths(mission_id)
            if not target.exists():
                if temps:
                    raise IntegrityError("temporary file exists without committed mission")
                raise MissionStoreError("MISSION_NOT_FOUND")
            aggregate = self._read_verified(target)
            if temps and not allow_stale_temp_read:
                raise MissionStoreError("RECOVERY_REQUIRED")
            return aggregate

    def reconstruct(self, mission_id: str) -> MissionAggregate:
        return self.load(mission_id, allow_stale_temp_read=True)

    def transition(self, request: TransitionRequest) -> TransitionResult:
        mission_id = request.mission_id
        target = self._target_path(mission_id)
        try:
            with self._mission_lock(mission_id):
                self._deny_stale_temps(mission_id)
                if not target.exists():
                    return self._denied(request, DenialCode.MISSION_NOT_FOUND, "mission not found")
                current = self._read_verified(target)
                replay = current.replay_event(request.idempotency_key)
                if replay:
                    if replay.transition_request_sha256 == request.transition_request_sha256:
                        return TransitionResult(
                            TransitionOutcome.REPLAYED,
                            mission_id,
                            None,
                            "identical committed transition replayed",
                            current.version,
                            current.current_state.value,
                            replay.event_sha256,
                            current.aggregate_sha256,
                            {"original_event_index": replay.event_index},
                        )
                    return self._denied(request, DenialCode.IDEMPOTENCY_CONFLICT, "idempotency key reused with different content", current)
                if request.expected_version != current.version:
                    return self._denied(request, DenialCode.CAS_CONFLICT, "version mismatch", current)
                if request.expected_state is not current.current_state:
                    return self._denied(request, DenialCode.CAS_CONFLICT, "state mismatch", current)
                if request.expected_previous_event_sha256 != current.previous_event_sha256:
                    return self._denied(request, DenialCode.CAS_CONFLICT, "prior event hash mismatch", current)
                if is_terminal(current.current_state):
                    return self._denied(request, DenialCode.TERMINAL_STATE, "terminal state cannot be reopened", current)
                if request.to_state is MissionState.CANCELLED:
                    if request.cancellation_authority_reference != current.scope.cancellation_authority:
                        return self._denied(request, DenialCode.IMMUTABLE_FIELD_CHANGE, "cancellation authority mismatch", current)
                elif request.cancellation_authority_reference is not None:
                    return self._denied(request, DenialCode.IMMUTABLE_FIELD_CHANGE, "unexpected cancellation authority", current)
                if not is_i1_transition_enabled(current.current_state, request.to_state):
                    return self._denied(request, DenialCode.INVALID_TRANSITION, "transition not enabled in I1", current)

                event = MissionEvent(
                    schema_version=EVENT_SCHEMA_VERSION,
                    event_index=current.version + 1,
                    mission_id=mission_id,
                    idempotency_key=request.idempotency_key,
                    transition_request_sha256=request.transition_request_sha256,
                    from_state=current.current_state,
                    to_state=request.to_state,
                    committed_at=utc_now(),
                    reason=request.reason,
                    evidence_sha256=request.evidence_sha256,
                    actor_reference=request.actor_reference,
                    previous_event_sha256=current.previous_event_sha256,
                )
                events = current.events + (event,)
                index = current.idempotency_index + ((event.idempotency_key, event.transition_request_sha256, event.event_index),)
                next_aggregate = MissionAggregate(
                    schema_version=current.schema_version,
                    identity=current.identity,
                    scope=current.scope,
                    created_at=current.created_at,
                    current_state=event.to_state,
                    version=current.version + 1,
                    previous_event_sha256=event.event_sha256,
                    events=events,
                    idempotency_index=index,
                    terminal=is_terminal(event.to_state),
                    cancelled=event.to_state is MissionState.CANCELLED,
                )
                if next_aggregate.immutable_fingerprint() != current.immutable_fingerprint():
                    return self._denied(request, DenialCode.IMMUTABLE_FIELD_CHANGE, "immutable mission data changed", current)
                self._durable_commit(target, next_aggregate.canonical_bytes(), mission_id)
                committed = self._read_verified(target)
                return TransitionResult(
                    TransitionOutcome.APPLIED,
                    mission_id,
                    None,
                    "transition durably applied",
                    committed.version,
                    committed.current_state.value,
                    event.event_sha256,
                    committed.aggregate_sha256,
                    {"event_index": event.event_index},
                )
        except LockTimeoutError:
            return self._denied(request, DenialCode.LOCK_TIMEOUT, "mission lock timeout")
        except IntegrityError as exc:
            return self._denied(request, DenialCode.INTEGRITY_FAILURE, str(exc))
        except (PersistenceError, OSError) as exc:
            return self._denied(request, DenialCode.PERSISTENCE_FAILURE, str(exc))
        except MissionStoreError as exc:
            code = DenialCode.RECOVERY_REQUIRED if "RECOVERY_REQUIRED" in str(exc) else DenialCode.INTEGRITY_FAILURE
            return self._denied(request, code, str(exc))

    def cancel(self, request: TransitionRequest) -> TransitionResult:
        if request.to_state is not MissionState.CANCELLED:
            return self._denied(request, DenialCode.INVALID_TRANSITION, "cancel requires CANCELLED target")
        return self.transition(request)

    def _denied(
        self,
        request: TransitionRequest,
        code: DenialCode,
        reason: str,
        current: Optional[MissionAggregate] = None,
    ) -> TransitionResult:
        return TransitionResult(
            TransitionOutcome.DENIED,
            request.mission_id,
            code,
            reason,
            current.version if current else request.expected_version,
            current.current_state.value if current else request.expected_state.value,
            current.previous_event_sha256 if current else request.expected_previous_event_sha256,
            current.aggregate_sha256 if current else "",
            {},
        )

    def _deny_stale_temps(self, mission_id: str) -> None:
        if self._temp_paths(mission_id):
            raise MissionStoreError("RECOVERY_REQUIRED: stale temporary file present")

    def _read_verified(self, target: Path) -> MissionAggregate:
        try:
            raw = target.read_bytes()
            return MissionAggregate.from_bytes(raw)
        except (OSError, SchemaError, IntegrityError) as exc:
            if isinstance(exc, IntegrityError):
                raise
            raise IntegrityError(f"durable mission integrity failure: {exc}") from exc

    def _durable_commit(self, target: Path, raw: bytes, mission_id: str) -> None:
        operation_id = uuid.uuid4().hex
        temp = target.parent / f".{mission_id}.{operation_id}.tmp"
        replaced = False
        try:
            with open(temp, "xb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, target)
            replaced = True
            # Windows requires a writable descriptor for FlushFileBuffers,
            # which is what Python's os.fsync delegates to.
            with open(target, "r+b") as handle:
                os.fsync(handle.fileno())
                handle.seek(0)
                readback = handle.read()
            if readback != raw:
                raise PersistenceError("target readback mismatch")
            MissionAggregate.from_bytes(readback)
            self._fsync_directory(target.parent)
        except Exception as exc:
            if temp.exists():
                try:
                    temp.unlink()
                except OSError:
                    pass
            if isinstance(exc, (PersistenceError, IntegrityError)):
                raise
            raise PersistenceError(f"durable commit failed after_replace={replaced}: {exc}") from exc

    @staticmethod
    def _fsync_directory(directory: Path) -> bool:
        if os.name == "nt":
            return False
        try:  # pragma: no cover - POSIX-only behavior
            descriptor = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            return True
        except OSError:
            return False

    # Test-only fault-injection seam. It does not add a force-state or bypass API.
    def _write_temp_without_replace(self, aggregate: MissionAggregate) -> Path:
        mission_id = aggregate.identity.mission_id
        temp = self.missions_dir / f".{mission_id}.{uuid.uuid4().hex}.tmp"
        with open(temp, "xb") as handle:
            handle.write(aggregate.canonical_bytes())
            handle.flush()
            os.fsync(handle.fileno())
        return temp


__all__ = ["MissionStore"]

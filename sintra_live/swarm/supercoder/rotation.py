"""SuperCoder worker rotation — automatic worker replacement on timeout."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import hashlib

from .checkpoint import Checkpoint, CheckpointStore, create_checkpoint
from .recovery import RecoveryEngine, TimeoutRecovery, RecoveryState
from .work_packet import WorkPacket, PacketStatus


@dataclass
class WorkerSession:
    """One worker's session within a mission."""
    worker_id: str
    mission_id: str
    packet_id: str
    started_at: str
    ended_at: Optional[str] = None
    checkpoint_id: Optional[str] = None
    timed_out: bool = False
    completed: bool = False

    def duration_seconds(self) -> float:
        end = self.ended_at or _utc_now()
        start = datetime.fromisoformat(self.started_at.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
        return (end_dt - start).total_seconds()


class WorkerRotation:
    """Manages worker lifecycle and automatic rotation.

    Timing policy:
    - 210s: mandatory checkpoint
    - 240s: stop coding, write handoff
    - 270s: emergency stop
    - 300s: platform hard limit (never reached if we checkpoint at 210)
    """

    def __init__(
        self,
        checkpoint_store: CheckpointStore,
        recovery_engine: RecoveryEngine,
        worktree: str,
        checkpoint_at_seconds: int = 210,
        stop_at_seconds: int = 240,
        emergency_at_seconds: int = 270,
    ):
        self.checkpoint_store = checkpoint_store
        self.recovery_engine = recovery_engine
        self.worktree = worktree
        self.checkpoint_at = checkpoint_at_seconds
        self.stop_at = stop_at_seconds
        self.emergency_at = emergency_at_seconds
        self._sessions: List[WorkerSession] = []
        self._worker_counter = 0

    def next_worker_id(self, mission_id: str) -> str:
        self._worker_counter += 1
        h = hashlib.sha256(f"{mission_id}:{self._worker_counter}".encode()).hexdigest()[:12]
        return f"worker-{h}"

    def start_session(self, mission_id: str, packet_id: str) -> WorkerSession:
        worker_id = self.next_worker_id(mission_id)
        session = WorkerSession(
            worker_id=worker_id,
            mission_id=mission_id,
            packet_id=packet_id,
            started_at=_utc_now(),
        )
        self._sessions.append(session)
        return session

    def end_session(self, worker_id: str, checkpoint_id: Optional[str] = None, timed_out: bool = False, completed: bool = False) -> WorkerSession:
        for s in reversed(self._sessions):
            if s.worker_id == worker_id:
                s.ended_at = _utc_now()
                s.checkpoint_id = checkpoint_id
                s.timed_out = timed_out
                s.completed = completed or (not timed_out)
                return s
        raise KeyError(f"Worker session {worker_id} not found")

    def recover_timed_out(self, mission_id: str, worker_id: str) -> TimeoutRecovery:
        """Recover state after a worker timeout."""
        return self.recovery_engine.recover(mission_id, worker_id)

    def should_checkpoint(self, session: WorkerSession) -> bool:
        """Check if the worker should checkpoint now."""
        return session.duration_seconds() >= self.checkpoint_at

    def should_stop(self, session: WorkerSession) -> bool:
        """Check if the worker should stop and hand off now."""
        return session.duration_seconds() >= self.stop_at

    def should_emergency_stop(self, session: WorkerSession) -> bool:
        """Check if the worker must emergency stop immediately."""
        return session.duration_seconds() >= self.emergency_at

    def all_sessions(self) -> List[WorkerSession]:
        return list(self._sessions)

    def session_count(self) -> int:
        return len(self._sessions)

    def timed_out_count(self) -> int:
        return sum(1 for s in self._sessions if s.timed_out)

    def completed_count(self) -> int:
        return sum(1 for s in self._sessions if s.completed)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
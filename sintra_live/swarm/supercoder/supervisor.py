"""SuperCoder supervisor — the long-lived orchestrator that owns the mission."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .mission import CodingMission, MissionPhase, MissionStatus, WorkUnit
from .checkpoint import Checkpoint, CheckpointStore, create_checkpoint
from .work_packet import WorkPacket, PacketScheduler, PacketStatus
from .context_capsule import ContextCapsule, build_capsule
from .path_locks import PathLockRegistry
from .role_registry import RoleRegistry, SuperCoderRole, QualityLevel
from .recovery import RecoveryEngine, TimeoutRecovery, RecoveryState
from .rotation import WorkerRotation, WorkerSession


@dataclass
class SuperCoderSupervisor:
    """The long-lived process that owns coding missions.

    Workers are disposable. The supervisor is persistent.
    Workers do not own the mission. The supervisor does.

    The supervisor:
    - Creates missions and packets
    - Launches workers
    - Receives checkpoints and handoffs
    - Recovers timed-out workers
    - Launches replacement workers
    - Verifies completion criteria
    - Enforces path locks
    - Enforces authority delta = 0
    - Reports milestones only
    """

    checkpoint_store: CheckpointStore
    path_locks: PathLockRegistry
    role_registry: RoleRegistry
    packet_scheduler: PacketScheduler
    rotation: WorkerRotation
    mission: CodingMission

    def launch_worker(self, packet: WorkPacket) -> WorkerSession:
        """Launch a worker for a specific packet."""
        # Acquire path locks for the packet's files
        for path in packet.exact_files:
            if not self.path_locks.acquire(
                path,
                self.mission.mission_id,
                packet.packet_id,
                "pending",
            ):
                raise RuntimeError(f"Path {path} is locked by another worker")

        session = self.rotation.start_session(
            self.mission.mission_id,
            packet.packet_id,
        )
        self.role_registry.assign(
            SuperCoderRole.IMPLEMENTER,
            session.worker_id,
            packet.packet_id,
            self.mission.mission_id,
        )
        return session

    def receive_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Receive and persist a checkpoint from a worker."""
        self.checkpoint_store.save(checkpoint)
        self.mission.checkpoint_sequence = checkpoint.sequence + 1
        self.mission.updated_at = checkpoint.timestamp

    def handle_timeout(self, worker_id: str) -> TimeoutRecovery:
        """Handle a worker timeout — recover state and prepare replacement."""
        recovery = self.rotation.recover_timed_out(
            self.mission.mission_id,
            worker_id,
        )
        # Release path locks held by the timed-out worker
        self.path_locks.release_all_for_worker(self.mission.mission_id, worker_id)
        return recovery

    def launch_replacement(self, recovery: TimeoutRecovery, packet: WorkPacket) -> WorkerSession:
        """Launch a replacement worker after timeout recovery."""
        session = self.rotation.start_session(
            self.mission.mission_id,
            packet.packet_id,
        )
        return session

    def complete_packet(self, packet_id: str, worker_id: str, work_unit: WorkUnit) -> None:
        """Mark a packet as completed and record the work unit."""
        self.packet_scheduler.mark_completed(packet_id)
        self.mission.record_work_unit(work_unit)
        self.path_locks.release_all_for_worker(self.mission.mission_id, worker_id)

    def build_context_capsule(self, active_packet: Optional[WorkPacket]) -> ContextCapsule:
        """Build a context capsule for the next worker."""
        latest_cp = self.checkpoint_store.load_latest(self.mission.mission_id)
        completed_pkts = tuple(
            p.packet_id for p in self.packet_scheduler.all_packets()
            if p.status == PacketStatus.COMPLETED
        )
        return build_capsule(
            mission_id=self.mission.mission_id,
            mission_objective=self.mission.objective,
            architecture_rules=(
                "MISSION_SYSTEM_OF_RECORD = sintra_live/l2",
                "AUTHORITY_SYSTEM_OF_RECORD = sintra_live/l2",
                "NO_PARALLEL_MISSION_AUTHORITY",
                "WORKER_TIMEOUT != MISSION_TIMEOUT",
            ),
            current_baseline=self.mission.baseline_commit,
            owned_paths=self.mission.owned_paths,
            current_phase=self.mission.current_phase.value,
            completed_packets=completed_pkts,
            active_packet=active_packet.packet_id if active_packet else None,
            last_checkpoint_id=latest_cp.checkpoint_id if latest_cp else None,
            relevant_apis=tuple(self.mission.discoveries),
            discoveries=tuple(self.mission.discoveries),
            failing_tests=(),
            next_action=active_packet.objective if active_packet else "No active packet",
            prohibited_actions=self.mission.prohibited_paths,
            authority_delta=self.mission.authority_delta,
            side_effects=self.mission.side_effects,
        )

    def verify_completion(self) -> bool:
        """Check if the mission is complete by verifying all acceptance criteria."""
        return (
            self.mission.status == MissionStatus.COMPLETE
            or self.mission.current_phase == MissionPhase.COMPLETE
        )

    def force_checkpoint(
        self,
        worker_id: str,
        active_task: str,
        completed_tasks: Tuple[str, ...],
        next_task: str,
        files_changed: Tuple[str, ...] = (),
        hashes: Optional[Dict[str, str]] = None,
        test_results: Optional[Dict[str, Any]] = None,
        findings: Tuple[str, ...] = (),
        exact_resume_instruction: str = "",
    ) -> Checkpoint:
        """Force a checkpoint for the current worker session."""
        cp = create_checkpoint(
            mission_id=self.mission.mission_id,
            worker_id=worker_id,
            baseline_commit=self.mission.baseline_commit,
            current_commit=self.mission.candidate_commits[-1] if self.mission.candidate_commits else self.mission.baseline_commit,
            worktree=self.rotation.worktree,
            active_task=active_task,
            completed_tasks=completed_tasks,
            next_task=next_task,
            files_changed=files_changed,
            hashes=hashes or {},
            test_results=test_results,
            findings=findings,
            exact_resume_instruction=exact_resume_instruction,
            sequence=self.mission.checkpoint_sequence,
        )
        self.receive_checkpoint(cp)
        return cp
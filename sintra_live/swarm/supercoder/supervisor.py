"""SuperCoder supervisor — the long-lived orchestrator that owns the mission."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .mission import CodingMission, CodingMissionStore, MissionPhase, MissionStatus, WorkUnit
from .checkpoint import Checkpoint, CheckpointStore, create_checkpoint
from .work_packet import WorkPacket, PacketScheduler, PacketStatus
from .context_capsule import ContextCapsule, build_capsule
from .path_locks import PathLockRegistry
from .role_registry import RoleRegistry, SuperCoderRole, QualityLevel
from .recovery import RecoveryEngine, TimeoutRecovery, RecoveryState
from .rotation import WorkerRotation, WorkerSession
from .persistence import RuntimeStateStore, SupervisorLeaseStore


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
    mission_store: Optional[CodingMissionStore] = None
    runtime_store: Optional[RuntimeStateStore] = None
    lease_store: Optional[SupervisorLeaseStore] = None
    supervisor_id: str = ""
    supervisor_epoch: int = 0

    def acquire_mission(self) -> int:
        if self.lease_store is None or not self.supervisor_id:
            raise RuntimeError("Supervisor lease store and identity are required")
        lease = self.lease_store.acquire(self.mission.mission_id, self.supervisor_id)
        self.supervisor_epoch = lease.epoch
        if self.mission_store is not None:
            try:
                self.mission = self.mission_store.load(self.mission.mission_id)
            except FileNotFoundError:
                self.mission_store.save(self.mission)
        return self.supervisor_epoch

    def accept_worker_result(self, worker_id: str, supervisor_epoch: int) -> None:
        if supervisor_epoch != self.supervisor_epoch:
            raise PermissionError("Worker result carries stale supervisor epoch")
        if self.lease_store is not None:
            lease = self.lease_store.current(self.mission.mission_id)
            if not lease or lease.owner_id != self.supervisor_id or lease.epoch != self.supervisor_epoch:
                raise PermissionError("Worker result rejected: supervisor lease is no longer authoritative")

    def persist_runtime_state(self) -> None:
        if self.runtime_store is None:
            raise RuntimeError("Runtime state store is required")
        self.runtime_store.save_scheduler(self.mission.mission_id, self.packet_scheduler)
        self.runtime_store.save_roles(self.mission.mission_id, self.role_registry)
        self.runtime_store.save_path_locks(self.mission.mission_id, self.path_locks)
        capsule = self.build_context_capsule(self.packet_scheduler.next_pending())
        self.runtime_store.save_context_capsule(self.mission.mission_id, capsule)
        if self.mission_store is not None:
            self.mission_store.save(self.mission)

    @classmethod
    def recover(
        cls,
        root: Path | str,
        mission_id: str,
        supervisor_id: str,
        lease_seconds: int = 60,
    ) -> "SuperCoderSupervisor":
        root = Path(root)
        mission_store = CodingMissionStore(root / "missions")
        mission = mission_store.load(mission_id)
        checkpoints = CheckpointStore(root / "checkpoints")
        runtime = RuntimeStateStore(root / "runtime")
        scheduler = runtime.load_scheduler(mission_id)
        roles = runtime.load_roles(mission_id)
        locks = runtime.load_path_locks(mission_id)
        recovery = RecoveryEngine(checkpoints, str(root / "worktree"))
        rotation = WorkerRotation(checkpoints, recovery, str(root / "worktree"))
        supervisor = cls(
            checkpoint_store=checkpoints,
            path_locks=locks,
            role_registry=roles,
            packet_scheduler=scheduler,
            rotation=rotation,
            mission=mission,
            mission_store=mission_store,
            runtime_store=runtime,
            lease_store=SupervisorLeaseStore(root / "leases", lease_seconds=lease_seconds),
            supervisor_id=supervisor_id,
        )
        supervisor.acquire_mission()
        return supervisor

    def rotate_recovered_packet(self, packet_id: str) -> WorkerSession:
        packet = self.packet_scheduler.get_packet(packet_id)
        old_worker = packet.worker_id
        if old_worker:
            self.path_locks.release_all_for_worker(self.mission.mission_id, old_worker)
        session = self.rotation.start_session(self.mission.mission_id, packet_id)
        if not self.path_locks.acquire_batch(
            list(packet.exact_files), self.mission.mission_id, packet_id, session.worker_id
        ):
            raise RuntimeError("Recovered packet path-lock conflict")
        self.packet_scheduler.mark_active(packet_id, session.worker_id)
        self.role_registry.assign(
            SuperCoderRole.IMPLEMENTER, session.worker_id, packet_id, self.mission.mission_id
        )
        return session

    def _assert_packet_scope(self, packet: WorkPacket) -> None:
        def owns(path: str) -> bool:
            return any(path == root or path.startswith(root.rstrip("/") + "/") for root in self.mission.owned_paths)

        for path in packet.exact_files:
            if path in self.mission.prohibited_paths:
                raise PermissionError(f"Path {path} is prohibited by mission scope")
            if not owns(path):
                raise PermissionError(f"Path {path} is outside mission owned paths")

    def launch_worker(self, packet: WorkPacket) -> WorkerSession:
        """Launch a worker for a specific packet."""
        session = self.rotation.start_session(
            self.mission.mission_id,
            packet.packet_id,
        )
        self._assert_packet_scope(packet)
        if not self.path_locks.acquire_batch(
            list(packet.exact_files),
            self.mission.mission_id,
            packet.packet_id,
            session.worker_id,
        ):
            self.rotation.end_session(session.worker_id, completed=False)
            raise RuntimeError("One or more packet paths are locked by another worker")
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
        if self.mission_store is not None:
            self.mission_store.save(self.mission)

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
            and self.mission.current_phase == MissionPhase.COMPLETE
            and self.mission.authority_delta == 0
            and self.mission.side_effects == 0
            and self.mission.tests_failed == 0
            and not self.mission.blockers
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
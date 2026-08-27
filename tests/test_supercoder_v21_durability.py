"""SuperCoder Runtime V2.1 process-durability acceptance tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from sintra_live.swarm.supercoder.checkpoint import CheckpointStore
from sintra_live.swarm.supercoder.context_capsule import build_capsule
from sintra_live.swarm.supercoder.mission import CodingMission, CodingMissionStore, MissionPhase, MissionStatus
from sintra_live.swarm.supercoder.path_locks import PathLockRegistry
from sintra_live.swarm.supercoder.persistence import RuntimeStateStore, SupervisorLeaseStore
from sintra_live.swarm.supercoder.recovery import RecoveryEngine
from sintra_live.swarm.supercoder.role_registry import RoleRegistry, SuperCoderRole
from sintra_live.swarm.supercoder.rotation import WorkerRotation
from sintra_live.swarm.supercoder.supervisor import SuperCoderSupervisor
from sintra_live.swarm.supercoder.work_packet import PacketScheduler, PacketStatus


def _mission() -> CodingMission:
    return CodingMission(
        mission_id="restart-mission-001",
        objective="Survive supervisor restart",
        acceptance_criteria=("tests pass", "authority delta zero"),
        baseline_commit="4602bc6d",
        integration_branch="integration/sp-final-product-swarm",
        owned_paths=("sintra_live/swarm/supercoder",),
    )


def _supervisor(root: Path, owner_id: str, acquire: bool = True) -> SuperCoderSupervisor:
    mission = _mission()
    checkpoints = CheckpointStore(root / "checkpoints")
    mission_store = CodingMissionStore(root / "missions")
    runtime_store = RuntimeStateStore(root / "runtime")
    leases = SupervisorLeaseStore(root / "leases", lease_seconds=60)
    scheduler = PacketScheduler(mission.mission_id)
    roles = RoleRegistry()
    locks = PathLockRegistry()
    recovery = RecoveryEngine(checkpoints, str(root / "worktree"))
    rotation = WorkerRotation(checkpoints, recovery, str(root / "worktree"))
    supervisor = SuperCoderSupervisor(
        checkpoint_store=checkpoints,
        path_locks=locks,
        role_registry=roles,
        packet_scheduler=scheduler,
        rotation=rotation,
        mission=mission,
        mission_store=mission_store,
        runtime_store=runtime_store,
        lease_store=leases,
        supervisor_id=owner_id,
    )
    if acquire:
        supervisor.acquire_mission()
    return supervisor


def test_packet_scheduler_round_trip(tmp_path):
    store = RuntimeStateStore(tmp_path)
    scheduler = PacketScheduler("m1")
    packet = scheduler.create_packet(
        objective="persist packet",
        exact_files=("sintra_live/swarm/supercoder/mission.py",),
    )
    scheduler.mark_active(packet.packet_id, "worker-a")
    store.save_scheduler("m1", scheduler)
    restored = store.load_scheduler("m1")
    packet2 = restored.get_packet(packet.packet_id)
    assert packet2.status == PacketStatus.ACTIVE
    assert packet2.worker_id == "worker-a"


def test_role_registry_round_trip(tmp_path):
    store = RuntimeStateStore(tmp_path)
    roles = RoleRegistry()
    roles.assign(SuperCoderRole.IMPLEMENTER, "worker-a", "packet-a", "m1")
    store.save_roles("m1", roles)
    restored = store.load_roles("m1")
    assert restored.get_role_for_packet("packet-a") == SuperCoderRole.IMPLEMENTER


def test_path_locks_round_trip(tmp_path):
    store = RuntimeStateStore(tmp_path)
    locks = PathLockRegistry()
    assert locks.acquire("a.py", "m1", "p1", "worker-a")
    store.save_path_locks("m1", locks)
    restored = store.load_path_locks("m1")
    lock = restored.locked_paths()["a.py"]
    assert lock.worker_id == "worker-a"
    assert lock.mission_id == "m1"


def test_context_capsule_round_trip(tmp_path):
    store = RuntimeStateStore(tmp_path)
    capsule = build_capsule(
        mission_id="m1",
        mission_objective="continue exactly",
        architecture_rules=("L2 authoritative",),
        current_baseline="abc",
        owned_paths=("a.py",),
        current_phase="IMPLEMENTING",
        completed_packets=("p0",),
        active_packet="p1",
        last_checkpoint_id="cp1",
        next_action="resume tests",
    )
    store.save_context_capsule("m1", capsule)
    restored = store.load_context_capsule("m1")
    assert restored.capsule_hash() == capsule.capsule_hash()
    assert restored.next_action == "resume tests"


def test_second_supervisor_collision_is_denied(tmp_path):
    supervisor_a = _supervisor(tmp_path, "supervisor-a")
    with pytest.raises(RuntimeError, match="active supervisor"):
        _supervisor(tmp_path, "supervisor-b")
    assert supervisor_a.lease_store.current("restart-mission-001").owner_id == "supervisor-a"


def test_stale_lease_reconciles_with_new_epoch(tmp_path):
    supervisor_a = _supervisor(tmp_path, "supervisor-a")
    lease_a = supervisor_a.lease_store.current("restart-mission-001")
    supervisor_a.lease_store.force_expire_for_test("restart-mission-001")
    supervisor_b = _supervisor(tmp_path, "supervisor-b")
    lease_b = supervisor_b.lease_store.current("restart-mission-001")
    assert lease_b.owner_id == "supervisor-b"
    assert lease_b.epoch == lease_a.epoch + 1


def test_stale_worker_epoch_is_rejected(tmp_path):
    supervisor_a = _supervisor(tmp_path, "supervisor-a")
    old_epoch = supervisor_a.supervisor_epoch
    supervisor_a.lease_store.force_expire_for_test("restart-mission-001")
    supervisor_b = _supervisor(tmp_path, "supervisor-b")
    with pytest.raises(PermissionError, match="stale supervisor epoch"):
        supervisor_b.accept_worker_result("worker-old", old_epoch)
    supervisor_b.accept_worker_result("worker-new", supervisor_b.supervisor_epoch)


def test_checkpoint_store_serializes_concurrent_writer(tmp_path):
    store_a = CheckpointStore(tmp_path)
    store_b = CheckpointStore(tmp_path)
    with store_a.exclusive_process_lock("m1", "writer-a"):
        with pytest.raises(RuntimeError, match="store lock"):
            with store_b.exclusive_process_lock("m1", "writer-b"):
                pass


def test_mission_store_serializes_concurrent_writer(tmp_path):
    store_a = CodingMissionStore(tmp_path)
    store_b = CodingMissionStore(tmp_path)
    with store_a.exclusive_process_lock("m1", "writer-a"):
        with pytest.raises(RuntimeError, match="store lock"):
            with store_b.exclusive_process_lock("m1", "writer-b"):
                pass


def test_super_coder_survives_process_restart(tmp_path):
    # Supervisor A starts mission and assigns a packet.
    supervisor_a = _supervisor(tmp_path, "supervisor-a")
    packet = supervisor_a.packet_scheduler.create_packet(
        objective="persisted implementation",
        exact_files=("sintra_live/swarm/supercoder/mission.py",),
    )
    session = supervisor_a.launch_worker(packet)
    supervisor_a.packet_scheduler.mark_active(packet.packet_id, session.worker_id)
    supervisor_a.role_registry.assign(
        SuperCoderRole.TEST_ENGINEER, "tester-a", packet.packet_id, supervisor_a.mission.mission_id
    )
    supervisor_a.force_checkpoint(
        worker_id=session.worker_id,
        active_task="editing mission.py",
        completed_tasks=("inspection",),
        next_task="run tests",
        files_changed=("sintra_live/swarm/supercoder/mission.py",),
        hashes={"sintra_live/swarm/supercoder/mission.py": "hash-25"},
        exact_resume_instruction="Run focused tests; do not repeat edit.",
    )
    supervisor_a.persist_runtime_state()
    old_epoch = supervisor_a.supervisor_epoch

    # Abrupt process termination: only expire the lease; durable files remain.
    supervisor_a.lease_store.force_expire_for_test(supervisor_a.mission.mission_id)

    # Supervisor B starts and recovers exact mission/runtime state.
    supervisor_b = SuperCoderSupervisor.recover(
        root=tmp_path,
        mission_id="restart-mission-001",
        supervisor_id="supervisor-b",
        lease_seconds=60,
    )
    restored_packet = supervisor_b.packet_scheduler.get_packet(packet.packet_id)
    assert restored_packet.status == PacketStatus.ACTIVE
    assert supervisor_b.role_registry.get_role_for_packet(packet.packet_id) is not None
    assert "sintra_live/swarm/supercoder/mission.py" in supervisor_b.path_locks.locked_paths()
    assert supervisor_b.checkpoint_store.load_latest("restart-mission-001").next_task == "run tests"
    assert supervisor_b.supervisor_epoch == old_epoch + 1

    # Old worker is fenced; replacement resumes and completes.
    with pytest.raises(PermissionError):
        supervisor_b.accept_worker_result(session.worker_id, old_epoch)
    replacement = supervisor_b.rotate_recovered_packet(packet.packet_id)
    supervisor_b.accept_worker_result(replacement.worker_id, supervisor_b.supervisor_epoch)
    supervisor_b.packet_scheduler.mark_completed(packet.packet_id)
    supervisor_b.mission.tests_run = 1
    supervisor_b.mission.tests_passed = 1
    supervisor_b.mission.tests_failed = 0
    supervisor_b.mission.authority_delta = 0
    supervisor_b.mission.side_effects = 0
    supervisor_b.mission.status = MissionStatus.COMPLETE
    supervisor_b.mission.current_phase = MissionPhase.COMPLETE
    assert supervisor_b.verify_completion()
    assert supervisor_b.mission.changed_files.get("sintra_live/swarm/supercoder/mission.py") is None
    assert supervisor_b.supervisor_epoch != old_epoch

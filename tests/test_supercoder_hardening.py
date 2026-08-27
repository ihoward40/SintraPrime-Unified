"""Adversarial hardening tests for SuperCoder Runtime V2.

These tests encode mission-durability, single-writer, scope, integrity,
and independent-certification invariants that the initial V2 acceptance
simulation did not exercise.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from sintra_live.swarm.supercoder.certification import CertStep, CertificationChain
from sintra_live.swarm.supercoder.checkpoint import CheckpointStore, create_checkpoint
from sintra_live.swarm.supercoder.mission import (
    CodingMission,
    CodingMissionStore,
    MissionPhase,
    MissionStatus,
)
from sintra_live.swarm.supercoder.path_locks import PathLockRegistry
from sintra_live.swarm.supercoder.recovery import RecoveryEngine
from sintra_live.swarm.supercoder.role_registry import RoleRegistry
from sintra_live.swarm.supercoder.rotation import WorkerRotation
from sintra_live.swarm.supercoder.supervisor import SuperCoderSupervisor
from sintra_live.swarm.supercoder.work_packet import PacketScheduler


def _mission() -> CodingMission:
    return CodingMission(
        mission_id="hardening-001",
        objective="Prove hardened runtime invariants",
        acceptance_criteria=("tests pass",),
        baseline_commit="abc123",
        integration_branch="integration/test",
        owned_paths=("sintra_live/swarm/supercoder", "tests/test_owned.py"),
        prohibited_paths=("sintra_live/swarm/supercoder/secret.py",),
    )


def _supervisor(tmp_path: Path) -> SuperCoderSupervisor:
    checkpoint_store = CheckpointStore(tmp_path / "checkpoints")
    path_locks = PathLockRegistry()
    roles = RoleRegistry()
    packets = PacketScheduler("hardening-001")
    recovery = RecoveryEngine(checkpoint_store, str(tmp_path))
    rotation = WorkerRotation(checkpoint_store, recovery, str(tmp_path))
    return SuperCoderSupervisor(
        checkpoint_store=checkpoint_store,
        path_locks=path_locks,
        role_registry=roles,
        packet_scheduler=packets,
        rotation=rotation,
        mission=_mission(),
        mission_store=CodingMissionStore(tmp_path / "missions"),
    )


def test_worker_owns_and_releases_exact_path_lock(tmp_path):
    supervisor = _supervisor(tmp_path)
    packet = supervisor.packet_scheduler.create_packet(
        objective="Edit owned file",
        exact_files=("sintra_live/swarm/supercoder/mission.py",),
    )
    session = supervisor.launch_worker(packet)
    lock = supervisor.path_locks.locked_paths()[packet.exact_files[0]]
    assert lock.worker_id == session.worker_id
    assert supervisor.path_locks.release_all_for_worker(
        supervisor.mission.mission_id, session.worker_id
    ) == 1
    assert not supervisor.path_locks.is_locked(packet.exact_files[0])


def test_supervisor_rejects_packet_outside_owned_paths(tmp_path):
    supervisor = _supervisor(tmp_path)
    packet = supervisor.packet_scheduler.create_packet(
        objective="Unauthorized edit",
        exact_files=("portal/main.py",),
    )
    with pytest.raises(PermissionError, match="outside mission owned paths"):
        supervisor.launch_worker(packet)


def test_supervisor_rejects_explicitly_prohibited_path(tmp_path):
    supervisor = _supervisor(tmp_path)
    packet = supervisor.packet_scheduler.create_packet(
        objective="Prohibited edit",
        exact_files=("sintra_live/swarm/supercoder/secret.py",),
    )
    with pytest.raises(PermissionError, match="prohibited"):
        supervisor.launch_worker(packet)


def test_checkpoint_corruption_fails_closed(tmp_path):
    store = CheckpointStore(tmp_path)
    cp = create_checkpoint(
        mission_id="m1",
        worker_id="w1",
        baseline_commit="abc",
        current_commit="def",
        worktree=str(tmp_path),
        active_task="edit",
        completed_tasks=(),
        next_task="test",
        sequence=0,
    )
    path = store.save(cp)
    raw = path.read_text(encoding="utf-8")
    path.write_text(raw.replace('"active_task":"edit"', '"active_task":"forged"'), encoding="utf-8")
    with pytest.raises(ValueError, match="integrity"):
        store.load("m1", cp.checkpoint_id)


def test_coding_mission_survives_store_restart(tmp_path):
    root = tmp_path / "missions"
    mission = _mission()
    store1 = CodingMissionStore(root)
    store1.save(mission)
    store2 = CodingMissionStore(root)
    loaded = store2.load(mission.mission_id)
    assert loaded.mission_id == mission.mission_id
    assert loaded.objective == mission.objective
    assert loaded.mission_hash() == mission.mission_hash()


def test_coding_mission_corruption_fails_closed(tmp_path):
    store = CodingMissionStore(tmp_path)
    mission = _mission()
    path = store.save(mission)
    raw = path.read_text(encoding="utf-8")
    path.write_text(raw.replace("Prove hardened runtime invariants", "forged"), encoding="utf-8")
    with pytest.raises(ValueError, match="integrity"):
        store.load(mission.mission_id)


def test_checkpoint_persists_updated_mission_state(tmp_path):
    supervisor = _supervisor(tmp_path)
    supervisor.mission.advance_phase(MissionPhase.IMPLEMENTING)
    supervisor.force_checkpoint(
        worker_id="worker-1",
        active_task="implement",
        completed_tasks=("inspect",),
        next_task="test",
    )
    loaded = supervisor.mission_store.load(supervisor.mission.mission_id)
    assert loaded.current_phase == MissionPhase.IMPLEMENTING
    assert loaded.checkpoint_sequence == 1


def test_certification_requires_independent_reviewers():
    chain = CertificationChain("m1")
    chain.submit(CertStep.IMPLEMENTED, True, "same-worker")
    chain.submit(CertStep.TESTED, True, "same-worker")
    chain.submit(CertStep.CODE_REVIEWED, True, "same-worker")
    assert not chain.is_fully_certified()


def test_certification_passes_with_distinct_builder_tester_reviewer():
    chain = CertificationChain("m1")
    chain.submit(CertStep.IMPLEMENTED, True, "builder")
    chain.submit(CertStep.TESTED, True, "tester")
    chain.submit(CertStep.CODE_REVIEWED, True, "reviewer")
    assert chain.is_fully_certified()


def test_supervisor_completion_fails_closed_on_authority_delta(tmp_path):
    supervisor = _supervisor(tmp_path)
    supervisor.mission.status = MissionStatus.COMPLETE
    supervisor.mission.current_phase = MissionPhase.COMPLETE
    supervisor.mission.authority_delta = 1
    assert not supervisor.verify_completion()


def test_supervisor_completion_fails_closed_on_failed_tests(tmp_path):
    supervisor = _supervisor(tmp_path)
    supervisor.mission.status = MissionStatus.COMPLETE
    supervisor.mission.current_phase = MissionPhase.COMPLETE
    supervisor.mission.tests_failed = 1
    assert not supervisor.verify_completion()


def test_supervisor_completion_accepts_clean_complete_mission(tmp_path):
    supervisor = _supervisor(tmp_path)
    supervisor.mission.status = MissionStatus.COMPLETE
    supervisor.mission.current_phase = MissionPhase.COMPLETE
    assert supervisor.verify_completion()

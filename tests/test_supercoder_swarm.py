"""SuperCoder tests: checkpoint, timeout recovery, context capsule, path locks, no lost work."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from sintra_live.swarm.supercoder.mission import (
    CodingMission,
    MissionPhase,
    MissionStatus,
    WorkUnit,
)
from sintra_live.swarm.supercoder.checkpoint import (
    Checkpoint,
    CheckpointStore,
    CheckpointSequence,
    create_checkpoint,
)
from sintra_live.swarm.supercoder.work_packet import (
    WorkPacket,
    PacketStatus,
    PacketScheduler,
)
from sintra_live.swarm.supercoder.context_capsule import (
    ContextCapsule,
    build_capsule,
)
from sintra_live.swarm.supercoder.path_locks import (
    PathLock,
    PathLockRegistry,
)
from sintra_live.swarm.supercoder.role_registry import (
    SuperCoderRole,
    QualityLevel,
    RoleRegistry,
)
from sintra_live.swarm.supercoder.recovery import (
    TimeoutRecovery,
    RecoveryState,
    RecoveryEngine,
)
from sintra_live.swarm.supercoder.rotation import (
    WorkerRotation,
    WorkerSession,
)
from sintra_live.swarm.supercoder.supervisor import SuperCoderSupervisor
from sintra_live.swarm.supercoder.certification import (
    CertStep,
    CertificationChain,
)


# ─── Checkpoint tests ───

class TestCheckpoint:
    def test_checkpoint_is_durable(self, tmp_path):
        store = CheckpointStore(tmp_path)
        cp = create_checkpoint(
            mission_id="test-mission",
            worker_id="worker-001",
            baseline_commit="abc123",
            current_commit="def456",
            worktree="/tmp/worktree",
            active_task="implement feature X",
            completed_tasks=("inspect", "plan"),
            next_task="write tests",
            files_changed=("file1.py",),
            hashes={"file1.py": "abc123"},
            sequence=0,
        )
        store.save(cp)
        loaded = store.load("test-mission", cp.checkpoint_id)
        assert loaded.checkpoint_id == cp.checkpoint_id
        assert loaded.mission_id == "test-mission"
        assert loaded.active_task == "implement feature X"
        assert loaded.files_changed == ("file1.py",)
        assert loaded.hashes == {"file1.py": "abc123"}

    def test_load_latest(self, tmp_path):
        store = CheckpointStore(tmp_path)
        cp1 = create_checkpoint(
            mission_id="m1", worker_id="w1", baseline_commit="a",
            current_commit="b", worktree="/tmp", active_task="task1",
            completed_tasks=(), next_task="task2", sequence=0,
        )
        cp2 = create_checkpoint(
            mission_id="m1", worker_id="w2", baseline_commit="a",
            current_commit="c", worktree="/tmp", active_task="task2",
            completed_tasks=("task1",), next_task="task3", sequence=1,
        )
        store.save(cp1)
        store.save(cp2)
        latest = store.load_latest("m1")
        assert latest is not None
        assert latest.checkpoint_id == cp2.checkpoint_id

    def test_checkpoint_survives_restart(self, tmp_path):
        store1 = CheckpointStore(tmp_path)
        cp = create_checkpoint(
            mission_id="m2", worker_id="w1", baseline_commit="a",
            current_commit="b", worktree="/tmp", active_task="task1",
            completed_tasks=(), next_task="task2", sequence=0,
        )
        store1.save(cp)
        # Simulate restart by creating a new store instance
        store2 = CheckpointStore(tmp_path)
        loaded = store2.load_latest("m2")
        assert loaded is not None
        assert loaded.active_task == "task1"


# ─── Path lock tests ───

class TestPathLocks:
    def test_acquire_and_release(self):
        registry = PathLockRegistry()
        assert registry.acquire("file1.py", "m1", "p1", "w1")
        assert registry.is_locked("file1.py")
        assert registry.release("file1.py", "m1", "w1")
        assert not registry.is_locked("file1.py")

    def test_cannot_acquire_locked_path(self):
        registry = PathLockRegistry()
        assert registry.acquire("file1.py", "m1", "p1", "w1")
        assert not registry.acquire("file1.py", "m2", "p2", "w2")

    def test_batch_acquire_atomic(self):
        registry = PathLockRegistry()
        assert registry.acquire_batch(["a.py", "b.py", "c.py"], "m1", "p1", "w1")
        assert registry.is_locked("a.py")
        assert registry.is_locked("b.py")
        assert registry.is_locked("c.py")

    def test_batch_acquire_rollback(self):
        registry = PathLockRegistry()
        registry.acquire("b.py", "m1", "p1", "w1")
        # Should fail and rollback a.py
        assert not registry.acquire_batch(["a.py", "b.py"], "m2", "p2", "w2")
        assert not registry.is_locked("a.py")

    def test_release_all_for_worker(self):
        registry = PathLockRegistry()
        registry.acquire("a.py", "m1", "p1", "w1")
        registry.acquire("b.py", "m1", "p1", "w1")
        count = registry.release_all_for_worker("m1", "w1")
        assert count == 2
        assert not registry.is_locked("a.py")
        assert not registry.is_locked("b.py")


# ─── Context capsule tests ───

class TestContextCapsule:
    def test_capsule_is_deterministic(self):
        c1 = build_capsule(
            mission_id="m1", mission_objective="test",
            architecture_rules=("rule1",), current_baseline="abc",
            owned_paths=("file1.py",), current_phase="IMPLEMENTING",
            completed_packets=("pkt1",), active_packet="pkt2",
            last_checkpoint_id="cp1", relevant_apis=("api1",),
            discoveries=("discovery1",), failing_tests=(),
            next_action="continue", prohibited_actions=("ext_write",),
        )
        c2 = build_capsule(
            mission_id="m1", mission_objective="test",
            architecture_rules=("rule1",), current_baseline="abc",
            owned_paths=("file1.py",), current_phase="IMPLEMENTING",
            completed_packets=("pkt1",), active_packet="pkt2",
            last_checkpoint_id="cp1", relevant_apis=("api1",),
            discoveries=("discovery1",), failing_tests=(),
            next_action="continue", prohibited_actions=("ext_write",),
        )
        assert c1.capsule_hash() == c2.capsule_hash()

    def test_capsule_summary(self):
        c = build_capsule(
            mission_id="mission-abc-def-ghi", mission_objective="test",
            architecture_rules=(), current_baseline="abc",
            owned_paths=(), current_phase="IMPLEMENTING",
            completed_packets=(), active_packet=None,
            last_checkpoint_id=None, next_action="continue implementation",
        )
        s = c.summary()
        assert "mission-abc-def" in s
        assert "IMPLEMENTING" in s


# ─── Work packet tests ───

class TestWorkPacket:
    def test_packet_creation(self):
        scheduler = PacketScheduler("m1")
        pkt = scheduler.create_packet(
            objective="Replace hardcoded dispatch",
            exact_files=("swarm.py",),
            tests=("test_dispatch.py",),
        )
        assert pkt.mission_id == "m1"
        assert pkt.status == PacketStatus.PENDING
        assert pkt.objective == "Replace hardcoded dispatch"

    def test_packet_lifecycle(self):
        scheduler = PacketScheduler("m1")
        pkt = scheduler.create_packet(
            objective="Test objective",
            exact_files=("file1.py",),
        )
        assert scheduler.pending_count() == 1
        scheduler.mark_active(pkt.packet_id, "w1")
        assert scheduler.pending_count() == 0
        scheduler.mark_completed(pkt.packet_id)
        assert scheduler.completed_count() == 1


# ─── Recovery tests ───

class TestTimeoutRecovery:
    def test_recovery_from_checkpoint(self, tmp_path):
        store = CheckpointStore(tmp_path)
        cp = create_checkpoint(
            mission_id="m1", worker_id="w1", baseline_commit="a",
            current_commit="b", worktree=str(tmp_path), active_task="implement",
            completed_tasks=("inspect",), next_task="write tests",
            files_changed=("file1.py",), hashes={"file1.py": "abc"},
            sequence=0,
        )
        store.save(cp)
        engine = RecoveryEngine(store, str(tmp_path))
        recovery = engine.recover("m1", "w1")
        assert recovery.recovery_state == RecoveryState.PARTIAL_IMPLEMENTATION
        assert recovery.latest_checkpoint is not None
        assert "file1.py" in recovery.files_changed

    def test_recovery_no_work(self, tmp_path):
        store = CheckpointStore(tmp_path)
        engine = RecoveryEngine(store, str(tmp_path))
        recovery = engine.recover("m1", "w1")
        assert recovery.recovery_state == RecoveryState.NO_WORK
        assert recovery.latest_checkpoint is None

    def test_recovery_test_failure(self, tmp_path):
        store = CheckpointStore(tmp_path)
        cp = create_checkpoint(
            mission_id="m1", worker_id="w1", baseline_commit="a",
            current_commit="b", worktree=str(tmp_path), active_task="test",
            completed_tasks=("implement",), next_task="fix failures",
            files_changed=("file1.py",), hashes={"file1.py": "abc"},
            test_results={"total": 5, "passed": 3, "failed": 2},
            sequence=0,
        )
        store.save(cp)
        engine = RecoveryEngine(store, str(tmp_path))
        recovery = engine.recover("m1", "w1")
        assert recovery.recovery_state == RecoveryState.TEST_FAILURE
        assert recovery.test_results["failed"] == 2


# ─── Certification chain tests ───

class TestCertificationChain:
    def test_full_certification(self):
        chain = CertificationChain("m1")
        chain.submit(CertStep.IMPLEMENTED, True, "implementer-001")
        chain.submit(CertStep.TESTED, True, "tester-001")
        chain.submit(CertStep.CODE_REVIEWED, True, "reviewer-001")
        assert chain.is_fully_certified()

    def test_partial_certification_not_complete(self):
        chain = CertificationChain("m1")
        chain.submit(CertStep.IMPLEMENTED, True, "implementer-001")
        chain.submit(CertStep.TESTED, True, "tester-001")
        assert not chain.is_fully_certified()

    def test_failed_certification(self):
        chain = CertificationChain("m1")
        chain.submit(CertStep.IMPLEMENTED, True, "impl-001")
        chain.submit(CertStep.TESTED, False, "tester-001", findings=["test_x failed"])
        assert chain.any_failed()
        assert not chain.is_fully_certified()

    def test_authority_delta_zero(self):
        chain = CertificationChain("m1")
        chain.submit(CertStep.IMPLEMENTED, True, "impl-001", authority_delta=0)
        chain.submit(CertStep.TESTED, True, "test-001", authority_delta=0)
        assert chain.authority_delta_total() == 0


# ─── Role registry tests ───

class TestRoleRegistry:
    def test_separate_certifier(self):
        registry = RoleRegistry()
        registry.assign(SuperCoderRole.IMPLEMENTER, "w1", "p1", "m1")
        registry.assign(SuperCoderRole.TEST_ENGINEER, "w2", "p1", "m1")
        assert registry.has_separate_certifier("m1")

    def test_no_separate_certifier(self):
        registry = RoleRegistry()
        registry.assign(SuperCoderRole.IMPLEMENTER, "w1", "p1", "m1")
        assert not registry.has_separate_certifier("m1")

    def test_quality_levels(self):
        registry = RoleRegistry()
        registry.set_quality("m1", QualityLevel.DEEP)
        roles = registry.required_roles_for_quality(QualityLevel.DEEP)
        assert SuperCoderRole.SECURITY_REVIEWER in roles
        assert SuperCoderRole.INTEGRATOR in roles


# ─── Mission tests ───

class TestCodingMission:
    def test_mission_creation(self):
        m = CodingMission(
            mission_id="m1",
            objective="Fix orchestration",
            acceptance_criteria=("tests pass", "no hardcoded output"),
            baseline_commit="abc123",
            integration_branch="integration/test",
            owned_paths=("file1.py",),
        )
        assert m.status == MissionStatus.ACTIVE
        assert m.current_phase == MissionPhase.PLANNED
        assert m.authority_delta == 0

    def test_mission_records_work_unit(self):
        m = CodingMission(
            mission_id="m1", objective="test",
            acceptance_criteria=(), baseline_commit="abc",
            integration_branch="test", owned_paths=(),
        )
        unit = WorkUnit(
            unit_id="u1", description="implemented feature",
            files_changed=("file1.py",), file_hashes={"file1.py": "abc"},
            test_results={"total": 5, "passed": 5, "failed": 0},
        )
        m.record_work_unit(unit)
        assert len(m.completed_work_units) == 1
        assert m.tests_run == 5
        assert m.tests_passed == 5
        assert m.changed_files["file1.py"] == "abc"

    def test_mission_hash_deterministic(self):
        m = CodingMission(
            mission_id="m1", objective="test",
            acceptance_criteria=(), baseline_commit="abc",
            integration_branch="test", owned_paths=(),
        )
        h1 = m.mission_hash()
        h2 = m.mission_hash()
        assert h1 == h2


# ─── THE KEY ACCEPTANCE TEST ───

class TestSuperCoderSurvivesRepeatedWorkerTimeouts:
    """The critical acceptance case: workers die repeatedly, mission completes."""

    def test_super_coder_survives_repeated_worker_timeouts(self, tmp_path):
        """
        SCENARIO:
        worker A writes 25% → forced timeout
        → worker B resumes → writes 25% → forced timeout
        → worker C resumes → tests → forced timeout
        → worker D resumes → fixes failure
        → worker E certifies

        EXPECTED:
        MISSION COMPLETE
        NO LOST WORK
        NO DUPLICATED EDITS
        NO AUTHORITY EXPANSION
        """
        store_root = tmp_path / "checkpoints"
        worktree = str(tmp_path / "worktree")
        Path(worktree).mkdir(parents=True, exist_ok=True)

        checkpoint_store = CheckpointStore(store_root)
        path_locks = PathLockRegistry()
        role_registry = RoleRegistry()
        recovery_engine = RecoveryEngine(checkpoint_store, worktree)
        rotation = WorkerRotation(checkpoint_store, recovery_engine, worktree)

        # Create mission
        mission = CodingMission(
            mission_id="survive-timeouts-001",
            objective="Implement a feature across multiple worker sessions",
            acceptance_criteria=("implementation complete", "tests pass", "no authority expansion"),
            baseline_commit="baseline-abc",
            integration_branch="integration/test",
            owned_paths=("feature.py",),
        )

        scheduler = PacketScheduler(mission.mission_id)
        supervisor = SuperCoderSupervisor(
            checkpoint_store=checkpoint_store,
            path_locks=path_locks,
            role_registry=role_registry,
            packet_scheduler=scheduler,
            rotation=rotation,
            mission=mission,
        )

        # Create work packets
        pkt1 = scheduler.create_packet(
            objective="Implement 25% of feature",
            exact_files=("feature.py",),
            completion_condition="file1.py has first section",
        )
        pkt2 = scheduler.create_packet(
            objective="Implement next 25% of feature",
            exact_files=("feature.py",),
            completion_condition="file1.py has second section",
        )
        pkt3 = scheduler.create_packet(
            objective="Run tests on implementation",
            exact_files=("test_feature.py",),
            completion_condition="tests pass",
        )
        pkt4 = scheduler.create_packet(
            objective="Fix any test failures",
            exact_files=("feature.py",),
            completion_condition="all tests green",
        )
        pkt5 = scheduler.create_packet(
            objective="Certify completion",
            exact_files=(),
            completion_condition="certification chain passes",
        )

        # ─── Worker A: starts, writes 25%, checkpoints, times out ───
        session_a = supervisor.launch_worker(pkt1)
        scheduler.mark_active(pkt1.packet_id, session_a.worker_id)

        cp_a = supervisor.force_checkpoint(
            worker_id=session_a.worker_id,
            active_task="implementing 25%",
            completed_tasks=("inspect",),
            next_task="implement next 25%",
            files_changed=("feature.py",),
            hashes={"feature.py": "hash-25pct"},
            exact_resume_instruction="Continue implementing next 25% of feature.py",
        )
        rotation.end_session(session_a.worker_id, cp_a.checkpoint_id, timed_out=True)

        # ─── Worker B: recovers, writes 25%, checkpoints, times out ───
        recovery_b = supervisor.handle_timeout(session_a.worker_id)
        assert recovery_b.recovery_state != RecoveryState.NO_WORK
        assert recovery_b.latest_checkpoint is not None

        session_b = supervisor.launch_replacement(recovery_b, pkt2)
        scheduler.mark_active(pkt2.packet_id, session_b.worker_id)

        cp_b = supervisor.force_checkpoint(
            worker_id=session_b.worker_id,
            active_task="implementing next 25%",
            completed_tasks=("inspect", "implement 25%"),
            next_task="run tests",
            files_changed=("feature.py",),
            hashes={"feature.py": "hash-50pct"},
            exact_resume_instruction="Run tests on 50% implementation",
        )
        rotation.end_session(session_b.worker_id, cp_b.checkpoint_id, timed_out=True)

        # ─── Worker C: recovers, runs tests, times out ───
        recovery_c = supervisor.handle_timeout(session_b.worker_id)
        assert recovery_c.recovery_state != RecoveryState.NO_WORK

        session_c = supervisor.launch_replacement(recovery_c, pkt3)
        scheduler.mark_active(pkt3.packet_id, session_c.worker_id)

        cp_c = supervisor.force_checkpoint(
            worker_id=session_c.worker_id,
            active_task="running tests",
            completed_tasks=("inspect", "implement 25%", "implement 25%", "run tests"),
            next_task="fix test failures",
            files_changed=("feature.py",),
            hashes={"feature.py": "hash-50pct"},
            test_results={"total": 4, "passed": 3, "failed": 1},
            exact_resume_instruction="Fix the 1 failing test",
        )
        rotation.end_session(session_c.worker_id, cp_c.checkpoint_id, timed_out=True)

        # ─── Worker D: recovers, fixes failure, completes ───
        recovery_d = supervisor.handle_timeout(session_c.worker_id)
        assert recovery_d.recovery_state == RecoveryState.TEST_FAILURE

        session_d = supervisor.launch_replacement(recovery_d, pkt4)
        scheduler.mark_active(pkt4.packet_id, session_d.worker_id)

        # Worker D completes successfully
        work_unit = WorkUnit(
            unit_id="wu-final",
            description="Fixed test failure and completed implementation",
            files_changed=("feature.py",),
            file_hashes={"feature.py": "hash-final"},
            test_results={"total": 4, "passed": 4, "failed": 0},
            worker_id=session_d.worker_id,
        )
        supervisor.complete_packet(pkt4.packet_id, session_d.worker_id, work_unit)
        rotation.end_session(session_d.worker_id, completed=True)

        # ─── Worker E: certifies ───
        session_e = supervisor.launch_worker(pkt5)
        cert_chain = CertificationChain(mission.mission_id)
        cert_chain.submit(CertStep.IMPLEMENTED, True, session_e.worker_id)
        cert_chain.submit(CertStep.TESTED, True, session_e.worker_id)
        cert_chain.submit(CertStep.CODE_REVIEWED, True, session_e.worker_id)
        rotation.end_session(session_e.worker_id, completed=True)

        # ─── VERIFY: Mission survived repeated timeouts ───
        assert cert_chain.is_fully_certified()
        assert cert_chain.authority_delta_total() == 0
        assert mission.authority_delta == 0
        assert mission.tests_passed == 4
        assert mission.tests_failed == 0
        assert len(mission.completed_work_units) == 1
        assert mission.changed_files["feature.py"] == "hash-final"

        # No lost work: all checkpoints from timed-out workers are durable
        # Workers A, B, C timed out and checkpointed. Worker D completed without timeout.
        all_cps = checkpoint_store.list_checkpoints(mission.mission_id)
        assert len(all_cps) == 3

        # No duplicated edits: only 1 work unit recorded
        assert len(mission.completed_work_units) == 1

        # Worker rotation tracked correctly
        assert rotation.session_count() == 5
        assert rotation.timed_out_count() == 3
        assert rotation.completed_count() == 2

        # Mission complete
        mission.advance_phase(MissionPhase.COMPLETE)
        assert mission.is_complete()
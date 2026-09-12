from __future__ import annotations

from pathlib import Path

import pytest

from swarm_runtime.capability_lease import WorkerCapabilityLease
from swarm_runtime.hermes_adapter import DelegateTask
from swarm_runtime.ownership import OwnershipRegistry
from swarm_runtime.worker import WorkerSpec


def test_delegate_task_maps_workorder_fields():
    task = DelegateTask(
        task_id="WO-1",
        description="Implement bounded UI change",
        role="builder",
        worker_class="BuilderWorker",
        mission_id="M-1",
        work_order_id="WO-1",
        actor_id="copilot.engineering.01",
        owner="copilot.engineering.01",
        parent_coordinator="hermes.canonical",
        authority_source="NONE",
        control_plane=False,
        write_paths=["web/src/pages/mission-control/**"],
        run_context={"mission_id": "M-1", "context_hash": "abc"},
        context_hash="abc",
    )
    task.validate_scope_binding()
    spec = task.to_worker_spec("WO-1")
    assert spec.mission_id == "M-1"
    assert spec.work_order_id == "WO-1"
    assert spec.actor_id == "copilot.engineering.01"
    assert spec.write_allowlist == ["web/src/pages/mission-control/**"]


def test_delegate_task_does_not_derive_unbound_context_hash():
    task = DelegateTask(
        task_id="WO-ctx-1",
        description="Scoped task",
        role="builder",
        worker_class="BuilderWorker",
        run_context={"mission_id": "M-ctx"},
    )
    spec = task.to_worker_spec("WO-ctx-1")
    assert spec.context_hash == ""


def test_delegate_task_rejects_unbound_context_hash_in_run_context():
    task = DelegateTask(
        task_id="WO-ctx-2",
        description="Scoped task",
        role="builder",
        worker_class="BuilderWorker",
        run_context={"context_hash": "abc"},
    )
    with pytest.raises(ValueError, match="CONTEXT_HASH_UNBOUND"):
        task.validate_scope_binding()


def test_delegate_task_rejects_forged_parent():
    task = DelegateTask(
        task_id="WO-2",
        description="x",
        role="builder",
        worker_class="BuilderWorker",
        actor_id="copilot.engineering.01",
        parent_coordinator="hermes.telegram.01",
        authority_source="NONE",
    )
    with pytest.raises(ValueError, match="FORGED"):
        task.validate_scope_binding()


def test_ownership_glob_overlap_rejected():
    registry = OwnershipRegistry()
    registry.register("copilot", ["web/**"])
    with pytest.raises(ValueError, match="OVERLAP"):
        registry.register("qa", ["web/src/App.tsx"])


def test_ownership_recursive_directory_overlap_rejected():
    registry = OwnershipRegistry()
    registry.register("copilot", ["web/**"])
    with pytest.raises(ValueError, match="OVERLAP"):
        registry.register("qa", ["web/src/**"])


def test_ownership_glob_vs_glob_overlap_rejected():
    registry = OwnershipRegistry()
    registry.register("copilot", ["web/**/*.ts"])
    with pytest.raises(ValueError, match="OVERLAP"):
        registry.register("qa", ["web/src/*.ts"])


def test_ownership_glob_vs_glob_sibling_prefix_not_overlap():
    registry = OwnershipRegistry()
    registry.register("copilot", ["web/src/*.ts"])
    registry.register("qa", ["web/src2/*.ts"])
    assert registry.can_write("copilot", "web/src/main.ts")
    assert not registry.can_write("qa", "web/src/main.ts")
    assert registry.can_write("qa", "web/src2/main.ts")
    assert not registry.can_write("copilot", "web/src2/main.ts")


def test_ownership_glob_vs_glob_same_prefix_disjoint_extensions_not_overlap():
    registry = OwnershipRegistry()
    registry.register("copilot", ["web/src/*.ts"])
    registry.register("qa", ["web/src/*.js"])
    assert registry.can_write("copilot", "web/src/main.ts")
    assert registry.can_write("qa", "web/src/main.js")
    assert not registry.can_write("copilot", "web/src/main.js")
    assert not registry.can_write("qa", "web/src/main.ts")


def test_ownership_glob_vs_glob_disjoint_literal_prefix_not_overlap():
    registry = OwnershipRegistry()
    registry.register("copilot", ["web/src/foo*.ts"])
    registry.register("qa", ["web/src/bar*.ts"])
    assert registry.can_write("copilot", "web/src/foobar.ts")
    assert registry.can_write("qa", "web/src/barbaz.ts")


def test_ownership_glob_vs_glob_disjoint_depth_not_overlap():
    registry = OwnershipRegistry()
    registry.register("copilot", ["web/*/*.ts"])
    registry.register("qa", ["web/*.ts"])
    assert registry.can_write("copilot", "web/src/main.ts")
    assert registry.can_write("qa", "web/main.ts")


def test_ownership_glob_vs_glob_root_pattern_does_not_overlap_nested_scope():
    registry = OwnershipRegistry()
    registry.register("copilot", ["*.ts"])
    registry.register("qa", ["src/*.ts"])
    assert registry.can_write("copilot", "main.ts")
    assert registry.can_write("qa", "src/main.ts")


def test_ownership_glob_character_class_overlap_rejected():
    registry = OwnershipRegistry()
    registry.register("copilot", ["src/file[0-9].ts"])
    with pytest.raises(ValueError, match="OVERLAP"):
        registry.register("qa", ["src/file[5-7].ts"])


def test_write_allowlist_and_lease_gates(tmp_path: Path):
    worktree = tmp_path / "wt"
    worktree.mkdir()
    (worktree / "safe").mkdir()
    lease = WorkerCapabilityLease.create(
        "copilot",
        actor_id="copilot.engineering.01",
        work_order_id="WO-3",
        mission_id="M-3",
        allowed_paths=["safe/**"],
        worktree_path=str(worktree),
        authority_write_permitted=True,
        task_active=True,
        ttl_seconds=30,
    )

    ok, code = lease.validate_write_request(
        actor_id="copilot.engineering.01",
        target_path="safe/file.ts",
        worktree_path=str(worktree),
    )
    assert ok is True
    assert code == "PASS"

    blocked, code = lease.validate_write_request(
        actor_id="copilot.engineering.01",
        target_path="../escape.ts",
        worktree_path=str(worktree),
    )
    assert blocked is False
    assert code == "PATH_TRAVERSAL_BLOCK"

    blocked, code = lease.validate_write_request(
        actor_id="not-copilot",
        target_path="safe/file.ts",
        worktree_path=str(worktree),
    )
    assert blocked is False
    assert code == "WRONG_ACTOR_BLOCK"


def test_write_blocked_for_new_file_under_symlinked_parent(tmp_path: Path):
    worktree = tmp_path / "wt"
    worktree.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (worktree / "safe").symlink_to(outside, target_is_directory=True)

    lease = WorkerCapabilityLease.create(
        "copilot",
        actor_id="copilot.engineering.01",
        allowed_paths=["safe/**"],
        worktree_path=str(worktree),
        authority_write_permitted=True,
        task_active=True,
        ttl_seconds=30,
    )

    blocked, code = lease.validate_write_request(
        actor_id="copilot.engineering.01",
        target_path="safe/new.ts",
        worktree_path=str(worktree),
    )
    assert blocked is False
    assert code == "SYMLINK_ESCAPE_BLOCK"


def test_exact_file_allowlist_does_not_allow_descendants(tmp_path: Path):
    worktree = tmp_path / "wt"
    worktree.mkdir()
    lease = WorkerCapabilityLease.create(
        "copilot",
        actor_id="copilot.engineering.01",
        allowed_paths=["safe/file.ts"],
        worktree_path=str(worktree),
        authority_write_permitted=True,
        task_active=True,
        ttl_seconds=30,
    )
    allowed, code = lease.validate_write_request(
        actor_id="copilot.engineering.01",
        target_path="safe/file.ts",
        worktree_path=str(worktree),
    )
    assert allowed is True
    assert code == "PASS"
    allowed_dot, code = lease.validate_write_request(
        actor_id="copilot.engineering.01",
        target_path="safe/./file.ts",
        worktree_path=str(worktree),
    )
    assert allowed_dot is True
    assert code == "PASS"
    blocked, code = lease.validate_write_request(
        actor_id="copilot.engineering.01",
        target_path="safe/file.ts/extra",
        worktree_path=str(worktree),
    )
    assert blocked is False
    assert code == "OUTSIDE_ALLOWLIST_BLOCK"


def test_recursive_glob_allows_zero_segment_match(tmp_path: Path):
    worktree = tmp_path / "wt"
    worktree.mkdir()
    lease = WorkerCapabilityLease.create(
        "copilot",
        actor_id="copilot.engineering.01",
        allowed_paths=["safe/**/file.ts"],
        worktree_path=str(worktree),
        authority_write_permitted=True,
        task_active=True,
        ttl_seconds=30,
    )
    allowed, code = lease.validate_write_request(
        actor_id="copilot.engineering.01",
        target_path="safe/file.ts",
        worktree_path=str(worktree),
    )
    assert allowed is True
    assert code == "PASS"


def test_directory_allowlist_marker_preserved_for_descendants(tmp_path: Path):
    worktree = tmp_path / "wt"
    worktree.mkdir()
    lease = WorkerCapabilityLease.create(
        "copilot",
        actor_id="copilot.engineering.01",
        allowed_paths=["safe/"],
        worktree_path=str(worktree),
        authority_write_permitted=True,
        task_active=True,
        ttl_seconds=30,
    )
    allowed, code = lease.validate_write_request(
        actor_id="copilot.engineering.01",
        target_path="safe/file.ts",
        worktree_path=str(worktree),
    )
    assert allowed is True
    assert code == "PASS"


def test_unbound_worktree_lease_rejected_for_write_validation(tmp_path: Path):
    lease = WorkerCapabilityLease.create(
        "copilot",
        actor_id="copilot.engineering.01",
        allowed_paths=["safe/**"],
        authority_write_permitted=True,
        task_active=True,
        ttl_seconds=30,
    )
    blocked, code = lease.validate_write_request(
        actor_id="copilot.engineering.01",
        target_path="safe/file.ts",
        worktree_path=str(tmp_path / "wt"),
    )
    assert blocked is False
    assert code == "WORKTREE_UNBOUND_BLOCK"


def test_recursive_pattern_preserved_in_ownership_matching():
    registry = OwnershipRegistry()
    registry.register("copilot", ["web/**/file.ts"])
    assert registry.can_write("copilot", "web/file.ts")
    assert registry.can_write("copilot", "web/src/file.ts")


def _copilot_write_spec(worktree: str, **overrides: object) -> WorkerSpec:
    data: dict[str, object] = {
        "worker_id": "w1",
        "role": "builder",
        "worker_class": "BuilderWorker",
        "task": {},
        "artifact_path": "artifacts/result.json",
        "actor_id": "copilot.engineering.01",
        "parent_coordinator": "hermes.canonical",
        "authority_source": "NONE",
        "control_plane": False,
        "worktree": worktree,
        "branch": "copilot-branch",
        "starting_clean_state": True,
        "write_allowlist": ["portal/foo.py"],
        "owned_files": [],
    }
    data.update(overrides)
    return WorkerSpec(**data)


def test_worker_contract_write_scope_uses_allowlist_when_owned_files_empty(tmp_path: Path):
    spec = _copilot_write_spec(str(tmp_path))
    spec.validate_contract()


def test_worker_contract_refuses_owned_file_outside_allowlist(tmp_path: Path):
    spec = _copilot_write_spec(
        str(tmp_path),
        owned_files=["portal/bar.py"],
        write_allowlist=["portal/foo.py"],
    )
    with pytest.raises(ValueError, match="OWNED_FILE_OUTSIDE_WRITE_ALLOWLIST"):
        spec.validate_contract()


def test_worker_contract_refuses_missing_allowlist_with_owned_files(tmp_path: Path):
    spec = _copilot_write_spec(
        str(tmp_path),
        write_allowlist=[],
        owned_files=["portal/foo.py"],
    )
    with pytest.raises(ValueError, match="WRITE_ALLOWLIST_REQUIRED"):
        spec.validate_contract()


def test_worker_contract_refuses_write_indicators_without_allowlist(tmp_path: Path):
    spec = _copilot_write_spec(
        str(tmp_path),
        write_allowlist=[],
        owned_files=[],
    )
    with pytest.raises(ValueError, match="WRITE_ALLOWLIST_REQUIRED"):
        spec.validate_contract()


def test_integrity_fields_propagate_delegate_to_worker_spec():
    task = DelegateTask(
        task_id="TASK-123",
        mission_id="MISSION-123",
        work_order_id="WO-123",
        description="bounded task",
        role="builder",
        worker_class="BuilderWorker",
        actor_id="copilot.engineering.01",
        owner="copilot.engineering.01",
        parent_coordinator="hermes.canonical",
        authority_source="NONE",
        authority_class="C3",
        context_hash="ctx-123",
        write_allowlist=["portal/foo.py"],
        lease_id="lease-123",
        execution_posture="SIMULATED",
        data_reality="SANDBOX",
        branch="branch-123",
        run_context={"mission_id": "MISSION-123", "context_hash": "ctx-123"},
    )
    task.validate_scope_binding()
    spec = task.to_worker_spec("worker-123")
    assert spec.work_order_id == "WO-123"
    assert spec.mission_id == "MISSION-123"
    assert spec.actor_id == "copilot.engineering.01"
    assert spec.parent_coordinator == "hermes.canonical"
    assert spec.authority_source == "NONE"
    assert spec.context_hash == "ctx-123"
    assert spec.write_allowlist == ["portal/foo.py"]
    assert spec.worktree == ""
    assert spec.lease_id == "lease-123"
    assert spec.execution_posture == "SIMULATED"
    assert spec.data_reality == "SANDBOX"

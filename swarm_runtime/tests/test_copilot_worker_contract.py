from __future__ import annotations

from pathlib import Path

import pytest

from swarm_runtime.capability_lease import WorkerCapabilityLease
from swarm_runtime.hermes_adapter import DelegateTask
from swarm_runtime.ownership import OwnershipRegistry


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

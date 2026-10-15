"""GOD-1 -> swarm_runtime governed execution bridge (SP-GOD1X Phase 16).

Lets a GOD-1 swarm task that requires real local/shadow execution be admitted
through the swarm_runtime ExecutionAdmissionGate. Proves the Phase 16 invariants:

  - TASK_RUNNING only when an admitted execution is actually running
  - task completion / failure reflect the governed backend
  - an empty authority intersection (MORE AGENTS != MORE AUTHORITY) denies
    execution — no consensus, confidence, or role title creates authority
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from swarm_runtime.controller import SwarmController
from swarm_runtime.governed_execution import (
    AuthorityEnvelope,
    ExecutionClass,
    ExecutionRequest,
    ExecutionResult,
    WorktreeClaim,
)

from .swarms import SwarmRoleManifest, SwarmTask, TaskStatus

_STATUS_MAP = {
    "RUNNING": TaskStatus.RUNNING,
    "COMPLETED": TaskStatus.COMPLETE,
    "FAILED": TaskStatus.FAILED,
    "TIMED_OUT": TaskStatus.FAILED,
    "DENIED": TaskStatus.BLOCKED,
    "CANCELLED": TaskStatus.CANCELLED,
}


def build_envelope_from_intersection(
    *,
    task: SwarmTask,
    manifest: SwarmRoleManifest,
    mission_id: str,
    swarm_id: str,
    authority_id: str,
    context_package_id: str,
    mission_authority: Iterable[str],
    swarm_authority: Iterable[str],
    parent_delegable: Iterable[str],
) -> AuthorityEnvelope:
    """Derive the admission envelope from the GOD-1 authority intersection.

    role_allowed is FALSE when the intersection is empty — this is the
    constitutional rule made operational: no effective authority => no execution.
    """
    effective = manifest.effective_authority(
        mission_authority, swarm_authority, parent_delegable
    )
    return AuthorityEnvelope(
        mission_id=mission_id,
        swarm_id=swarm_id,
        task_id=task.task_id,
        agent_id=task.role,
        authority_id=authority_id,
        role_id=manifest.role_id,
        context_package_id=context_package_id,
        mission_active=True,
        swarm_authorized=True,
        task_ready=task.status in (TaskStatus.PENDING, TaskStatus.READY),
        agent_authorized=True,
        authority_valid=True,
        context_valid=True,
        role_allowed=bool(effective),
        resource_allowed=True,
        revoked=False,
    )


def dispatch_task_to_runtime(
    *,
    task: SwarmTask,
    manifest: SwarmRoleManifest,
    mission_id: str,
    swarm_id: str,
    authority_id: str,
    context_package_id: str,
    worker_class: str,
    task_params: dict,
    working_directory: str,
    repo_path: str,
    run_dir: str,
    mission_authority: Iterable[str],
    swarm_authority: Iterable[str],
    parent_delegable: Iterable[str],
    worktree_claim: WorktreeClaim | None = None,
    timeout_seconds: int = 120,
) -> tuple[ExecutionResult | None, AuthorityEnvelope, SwarmController]:
    """Admit a GOD-1 task through the governed execution backend.

    Returns (result, envelope, controller). When the authority intersection is
    empty, result is None and the task is marked BLOCKED — no subprocess is
    spawned. Otherwise the controller is live and the caller may ``wait()`` then
    ``reflect_task_status``.
    """
    envelope = build_envelope_from_intersection(
        task=task,
        manifest=manifest,
        mission_id=mission_id,
        swarm_id=swarm_id,
        authority_id=authority_id,
        context_package_id=context_package_id,
        mission_authority=mission_authority,
        swarm_authority=swarm_authority,
        parent_delegable=parent_delegable,
    )
    ctrl = SwarmController(swarm_id=swarm_id, repo_path=repo_path, run_dir=run_dir)
    if not envelope.role_allowed:
        task.status = TaskStatus.BLOCKED
        return None, envelope, ctrl

    effect_class = (
        ExecutionClass.BUILD_EXECUTION.value
        if manifest.role_type.upper() in ("BUILDER", "BUILD")
        else ExecutionClass.READ_ONLY_INSPECTION.value
    )
    req = ExecutionRequest(
        execution_request_id=f"req-{task.task_id}",
        mission_id=mission_id,
        swarm_id=swarm_id,
        task_id=task.task_id,
        agent_id=task.role,
        authority_id=authority_id,
        context_package_id=context_package_id,
        role_id=manifest.role_id,
        working_directory=working_directory,
        timeout_seconds=timeout_seconds,
        effect_class=effect_class,
        worker_class=worker_class,
        task_params=task_params,
        artifact_path="findings.json",
        owned_files=list(task.mutable_resources),
        read_paths=[working_directory],
        write_paths=list(task.mutable_resources),
    )
    res = ctrl.launch_governed(req, envelope, worktree_claim=worktree_claim)
    if res.status == "DENIED":
        task.status = TaskStatus.BLOCKED
    elif res.status == "RUNNING":
        task.status = TaskStatus.RUNNING
        if task.started_at is None:
            task.started_at = datetime.now(UTC)
    return res, envelope, ctrl


def reflect_task_status(task: SwarmTask, result: ExecutionResult | None) -> None:
    """Reflect the governed backend result back onto the GOD-1 task (Phase 16)."""
    if result is None:
        return
    mapped = _STATUS_MAP.get(result.status)
    if mapped is not None:
        task.status = mapped
        if mapped is TaskStatus.COMPLETE and task.completed_at is None:
            task.completed_at = datetime.now(UTC)

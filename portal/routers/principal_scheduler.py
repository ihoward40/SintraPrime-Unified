"""Principal-only API for the canonical PostgreSQL governed scheduler (Gate 3).

This surface schedules and dispatches bounded internal SintraPrime orchestration only.
No external connector, browser, email, payment, filing, or publication adapter is
activated by these endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.rbac import CurrentUser, Permission, require_permissions
from ..database import get_db
from ..services.audit_service import audit
from ..services.governed_scheduler import (
    SchedulerIdempotencyConflictError,
    SchedulerStateError,
    cancel_schedule,
    create_schedule,
    dispatch_due_schedule,
    get_schedule,
    list_schedules,
    replay_schedule,
)
from ..services.orchestration.budget_policy import BudgetLimits
from ..services.orchestration.schemas import ExecutionMode

router = APIRouter(prefix="/api/v1/principal/schedules", tags=["principal-scheduler"])


class PrincipalScheduleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective: str = Field(min_length=1, max_length=10000)
    constraints: dict[str, Any] = Field(default_factory=dict)
    execution_mode: ExecutionMode = ExecutionMode.THINK_WORK_CHECK
    budget_limits: BudgetLimits | None = None
    run_at: datetime
    idempotency_key: str = Field(min_length=16, max_length=128)
    service_identity_id: str | None = Field(default=None, max_length=36)


class PrincipalScheduleCancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=1, max_length=2000)


class PrincipalScheduleDispatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    worker_id: str = Field(min_length=1, max_length=128)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_principal_schedule(
    body: PrincipalScheduleRequest,
    current_user: CurrentUser = Depends(
        require_permissions(Permission.MISSION_COMMAND_ADMIN, Permission.ORCHESTRATION_CREATE)
    ),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    try:
        schedule = await create_schedule(
            db,
            tenant_id=current_user.tenant_id,
            created_by=current_user.user_id,
            objective=body.objective,
            constraints=body.constraints,
            execution_mode=body.execution_mode.value,
            budget_limits=body.budget_limits.model_dump() if body.budget_limits else None,
            run_at=body.run_at,
            idempotency_key=body.idempotency_key,
            service_identity_id=body.service_identity_id,
        )
    except SchedulerIdempotencyConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "SCHEDULER_IDEMPOTENCY_CONFLICT",
                "schedule_id": exc.schedule_id,
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    await audit(
        db,
        action="ike_runtime_schedule_created",
        user_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        resource_type="governed_schedule",
        resource_id=schedule["schedule_id"],
        resource_name="principal_schedule",
        details={
            "run_at": schedule["run_at"],
            "status": schedule["status"],
            "persistence": "postgresql-durable-scheduler",
            "external_action_performed": False,
        },
    )
    return schedule


@router.get("")
async def list_principal_schedules(
    current_user: CurrentUser = Depends(
        require_permissions(Permission.MISSION_COMMAND_ADMIN, Permission.ORCHESTRATION_READ)
    ),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    return await list_schedules(db, tenant_id=current_user.tenant_id)


@router.get("/{schedule_id}")
async def get_principal_schedule(
    schedule_id: str,
    current_user: CurrentUser = Depends(
        require_permissions(Permission.MISSION_COMMAND_ADMIN, Permission.ORCHESTRATION_READ)
    ),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    schedule = await get_schedule(db, schedule_id=schedule_id, tenant_id=current_user.tenant_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.post("/{schedule_id}/cancel")
async def cancel_principal_schedule(
    schedule_id: str,
    body: PrincipalScheduleCancelRequest,
    current_user: CurrentUser = Depends(
        require_permissions(Permission.MISSION_COMMAND_ADMIN, Permission.ORCHESTRATION_CANCEL)
    ),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    try:
        schedule = await cancel_schedule(
            db,
            schedule_id=schedule_id,
            tenant_id=current_user.tenant_id,
            actor_id=current_user.user_id,
            reason=body.reason,
        )
    except SchedulerStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    await audit(
        db,
        action="ike_runtime_schedule_cancelled",
        user_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        resource_type="governed_schedule",
        resource_id=schedule_id,
        resource_name="principal_schedule_cancel",
        details={
            "reason": body.reason,
            "persistence": "postgresql-durable-scheduler",
            "external_action_performed": False,
        },
    )
    return schedule


@router.post("/{schedule_id}/replay")
async def replay_principal_schedule(
    schedule_id: str,
    current_user: CurrentUser = Depends(
        require_permissions(Permission.MISSION_COMMAND_ADMIN, Permission.ORCHESTRATION_READ)
    ),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    try:
        replay = await replay_schedule(
            db,
            schedule_id=schedule_id,
            tenant_id=current_user.tenant_id,
        )
    except SchedulerStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if replay is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    await audit(
        db,
        action="ike_runtime_schedule_replayed",
        user_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        resource_type="governed_schedule",
        resource_id=schedule_id,
        resource_name="principal_schedule_replay",
        details={
            "event_count": replay["event_count"],
            "head_hash": replay["head_hash"],
            "projection_matches": replay["projection_matches"],
            "persistence": "postgresql-durable-scheduler",
            "external_action_performed": False,
        },
    )
    return replay


@router.post("/{schedule_id}/dispatch-due")
async def dispatch_principal_schedule(
    schedule_id: str,
    body: PrincipalScheduleDispatchRequest,
    current_user: CurrentUser = Depends(
        require_permissions(Permission.MISSION_COMMAND_ADMIN, Permission.ORCHESTRATION_CREATE)
    ),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Bounded Gate 3 dispatch into durable orchestration; no external adapter runs."""
    try:
        schedule = await dispatch_due_schedule(
            db,
            schedule_id=schedule_id,
            tenant_id=current_user.tenant_id,
            worker_id=body.worker_id,
        )
    except SchedulerStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found or currently claimed")
    await audit(
        db,
        action="ike_runtime_schedule_dispatched",
        user_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        resource_type="governed_schedule",
        resource_id=schedule_id,
        resource_name="principal_schedule_dispatch",
        details={
            "worker_id": body.worker_id,
            "dispatched_run_id": schedule.get("dispatched_run_id"),
            "persistence": "postgresql-durable-scheduler",
            "external_action_performed": False,
        },
    )
    return schedule

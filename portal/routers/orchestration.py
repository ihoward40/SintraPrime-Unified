"""Governed adaptive orchestration API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.rbac import CurrentUser, Permission, require_permissions
from ..database import get_db
from ..services.orchestration import orchestrator, persistence
from ..services.orchestration.budget_policy import BudgetLimits
from ..services.orchestration.schemas import ExecutionMode

router = APIRouter(prefix="/api/orchestration", tags=["orchestration"])


class OrchestrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective: str = Field(min_length=1)
    constraints: dict[str, Any] = Field(default_factory=dict)
    execution_mode: ExecutionMode = ExecutionMode.THINK_WORK_CHECK
    budget_limits: BudgetLimits | None = None


class CancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1)


class ApprovalDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved: bool
    reason: str | None = None


@router.post("/plan")
async def plan(
    request: OrchestrationRequest,
    current_user: CurrentUser = Depends(require_permissions(Permission.ORCHESTRATION_CREATE)),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    run = orchestrator.plan_run(
        objective=request.objective,
        constraints=request.constraints,
        execution_mode=request.execution_mode,
        budget_limits=request.budget_limits,
        tenant_id=current_user.tenant_id,
        created_by=current_user.user_id,
    )
    await persistence.save_run(db, run)
    return run


@router.post("/execute")
async def execute(
    request: OrchestrationRequest,
    current_user: CurrentUser = Depends(require_permissions(Permission.ORCHESTRATION_CREATE)),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    run = orchestrator.execute_run(
        objective=request.objective,
        constraints=request.constraints,
        execution_mode=request.execution_mode,
        budget_limits=request.budget_limits,
        tenant_id=current_user.tenant_id,
        created_by=current_user.user_id,
    )
    await persistence.save_run(db, run)
    return run


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    current_user: CurrentUser = Depends(require_permissions(Permission.ORCHESTRATION_READ)),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    run = await persistence.get_run(db, run_id, tenant_id=current_user.tenant_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orchestration run not found")
    return run


@router.get("/runs/{run_id}/events")
async def get_run_events(
    run_id: str,
    current_user: CurrentUser = Depends(require_permissions(Permission.ORCHESTRATION_READ)),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    events = await persistence.get_events(db, run_id, tenant_id=current_user.tenant_id)
    if events is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orchestration run not found")
    return events


@router.post("/runs/{run_id}/cancel")
async def cancel(
    run_id: str,
    request: CancelRequest,
    current_user: CurrentUser = Depends(require_permissions(Permission.ORCHESTRATION_CANCEL)),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    existing = await persistence.get_run(db, run_id, tenant_id=current_user.tenant_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orchestration run not found")
    orchestrator.RUNS[run_id] = existing
    try:
        run = orchestrator.cancel_run(
            run_id,
            tenant_id=current_user.tenant_id,
            actor_id=current_user.user_id,
            reason=request.reason,
        )
    except orchestrator.OrchestrationStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orchestration run not found")
    await persistence.save_run(db, run)
    return run


@router.post("/runs/{run_id}/approve")
async def approve(
    run_id: str,
    request: ApprovalDecisionRequest,
    current_user: CurrentUser = Depends(require_permissions(Permission.ORCHESTRATION_APPROVE)),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    existing = await persistence.get_run(db, run_id, tenant_id=current_user.tenant_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orchestration run not found")
    orchestrator.RUNS[run_id] = existing
    try:
        run = orchestrator.approve_run(
            run_id,
            tenant_id=current_user.tenant_id,
            principal_id=current_user.user_id,
            approved=request.approved,
            reason=request.reason,
        )
    except orchestrator.OrchestrationStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orchestration run not found")
    await persistence.save_run(db, run)
    return run

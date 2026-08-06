"""Governed adaptive orchestration API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from ..services.orchestration import orchestrator
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

    principal_id: str = Field(min_length=1)
    approved: bool
    reason: str | None = None


@router.post("/plan")
async def plan(request: OrchestrationRequest) -> dict[str, Any]:
    return orchestrator.plan_run(
        objective=request.objective,
        constraints=request.constraints,
        execution_mode=request.execution_mode,
        budget_limits=request.budget_limits,
    )


@router.post("/execute")
async def execute(request: OrchestrationRequest) -> dict[str, Any]:
    return orchestrator.execute_run(
        objective=request.objective,
        constraints=request.constraints,
        execution_mode=request.execution_mode,
        budget_limits=request.budget_limits,
    )


@router.get("/runs/{run_id}")
async def get_run(run_id: str) -> dict[str, Any]:
    run = orchestrator.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orchestration run not found")
    return run


@router.get("/runs/{run_id}/events")
async def get_run_events(run_id: str) -> list[dict[str, Any]]:
    events = orchestrator.get_events(run_id)
    if events is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orchestration run not found")
    return events


@router.post("/runs/{run_id}/cancel")
async def cancel(run_id: str, request: CancelRequest) -> dict[str, Any]:
    run = orchestrator.cancel_run(run_id, request.reason)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orchestration run not found")
    return run


@router.post("/runs/{run_id}/approve")
async def approve(run_id: str, request: ApprovalDecisionRequest) -> dict[str, Any]:
    run = orchestrator.approve_run(run_id, request.principal_id, request.approved, request.reason)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orchestration run not found")
    return run

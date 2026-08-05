"""Mission Control read model.

This router intentionally exposes observation only. Command endpoints belong to
the governed execution layer and must not be simulated by the UI.

Foundation phase additions:
- GET /intents — list command projections (tenant-scoped)
- GET /intents/{command_id} — single command detail with events and receipts
- GET /run-controls — list run-control projections (tenant-scoped)
- GET /run-controls/{run_control_id} — single run-control detail with events
- GET /intents/{command_id}/causation-chain — causation chain assembly
- GET /cancellation-status — Sigma gate and cancellation control status
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.rbac import CurrentUser, Permission, require_permissions
from ..database import get_db
from ..schemas.mission_control_projection import (
    CancellationControlStatus,
    CausationChain,
    CommandListResponse,
    CommandProjection,
    RunControlListResponse,
    RunControlProjection,
)
from ..services.mission_control_projection_service import (
    get_causation_chain,
    get_command,
    get_run_control,
    list_commands,
    list_run_controls,
)
from ..services.sigma_gate import get_cancellation_status
from .system_health import (
    _check_agents,
    _check_database,
    _check_evidence_platform,
    _check_recovery_api,
    _check_scheduler,
)

router = APIRouter(prefix="/api/v1/mission-control", tags=["mission-control"])


class Metric(BaseModel):
    value: int | float | str | None
    status: Literal["verified", "unknown", "unavailable"] = "verified"


class MissionControlSummary(BaseModel):
    environment: str
    health: Literal["healthy", "degraded", "offline"]
    telemetry_updated_at: datetime
    telemetry_source: str = "portal.system_health"
    active_agents: Metric
    active_runs: Metric
    pending_decisions: Metric
    open_incidents: Metric
    daily_spend_usd: Metric
    kill_switch: Metric
    evidence_items: Metric
    scheduled_jobs: Metric
    subsystems: dict[str, dict] = Field(default_factory=dict)


@router.get("/summary", response_model=MissionControlSummary)
async def get_summary(
    _: CurrentUser = Depends(require_permissions(Permission.ADMIN_DASHBOARD)),
) -> MissionControlSummary:
    """Return a telemetry-backed executive summary.

    Values for which SintraPrime has no authoritative source are explicitly
    marked unavailable rather than inferred or fabricated.
    """
    database = _check_database()
    recovery = _check_recovery_api()
    evidence = _check_evidence_platform()
    scheduler = _check_scheduler()
    agents = _check_agents()
    subsystems = {
        "database": database,
        "recovery": recovery,
        "evidence": evidence,
        "scheduler": scheduler,
        "agents": agents,
    }
    degraded = any(item.get("status") not in {"healthy"} for item in subsystems.values())

    evidence_count = sum(int(case.get("evidence_items", 0)) for case in evidence.get("cases", []))
    return MissionControlSummary(
        environment="production" if database.get("type") != "sqlite" else "local",
        health="degraded" if degraded else "healthy",
        telemetry_updated_at=datetime.now(UTC),
        active_agents=Metric(value=agents.get("running"), status="verified"),
        active_runs=Metric(value=None, status="unavailable"),
        pending_decisions=Metric(value=None, status="unavailable"),
        open_incidents=Metric(value=None, status="unavailable"),
        daily_spend_usd=Metric(value=None, status="unavailable"),
        kill_switch=Metric(value=recovery.get("external_action", "unknown"), status="verified"),
        evidence_items=Metric(value=evidence_count, status="verified"),
        scheduled_jobs=Metric(value=scheduler.get("jobs"), status="verified"),
        subsystems=subsystems,
    )


# ── Foundation: Intent projection (read-only) ────────────────────────────────


@router.get("/intents", response_model=CommandListResponse)
async def list_intents(
    current_user: CurrentUser = Depends(require_permissions(Permission.MISSION_COMMAND_READ)),
    db: AsyncSession = Depends(get_db),
    state: str | None = Query(default=None),
    command_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> CommandListResponse:
    """List command (intent) projections for the current tenant.

    All results are scoped to the authenticated user's tenant_id. No
    cross-tenant access is possible.
    """
    return await list_commands(
        db,
        tenant_id=current_user.tenant_id,
        state=state,
        command_type=command_type,
        limit=limit,
        offset=offset,
    )


@router.get("/intents/{command_id}", response_model=CommandProjection)
async def get_intent(
    command_id: str,
    current_user: CurrentUser = Depends(require_permissions(Permission.MISSION_COMMAND_READ)),
    db: AsyncSession = Depends(get_db),
) -> CommandProjection:
    """Return a single command projection with events and receipts.

    Returns 404 if the command does not exist or belongs to a different
    tenant.
    """
    projection = await get_command(db, tenant_id=current_user.tenant_id, command_id=command_id)
    if projection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Command not found or not accessible within tenant scope.",
        )
    return projection


# ── Foundation: Execution-state projection (read-only) ───────────────────────


@router.get("/run-controls", response_model=RunControlListResponse)
async def list_run_controls_route(
    current_user: CurrentUser = Depends(require_permissions(Permission.MISSION_COMMAND_READ)),
    db: AsyncSession = Depends(get_db),
    state: str | None = Query(default=None),
    workflow_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> RunControlListResponse:
    """List run-control projections for the current tenant.

    All results are scoped to the authenticated user's tenant_id.
    """
    return await list_run_controls(
        db,
        tenant_id=current_user.tenant_id,
        state=state,
        workflow_id=workflow_id,
        limit=limit,
        offset=offset,
    )


@router.get("/run-controls/{run_control_id}", response_model=RunControlProjection)
async def get_run_control_route(
    run_control_id: str,
    current_user: CurrentUser = Depends(require_permissions(Permission.MISSION_COMMAND_READ)),
    db: AsyncSession = Depends(get_db),
) -> RunControlProjection:
    """Return a single run-control projection with transition events.

    Returns 404 if the run-control does not exist or belongs to a different
    tenant.
    """
    projection = await get_run_control(
        db,
        tenant_id=current_user.tenant_id,
        run_control_id=run_control_id,
    )
    if projection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run control not found or not accessible within tenant scope.",
        )
    return projection


# ── Foundation: Correlation / causation chain (read-only) ────────────────────


@router.get(
    "/intents/{command_id}/causation-chain",
    response_model=CausationChain,
)
async def get_causation_chain_route(
    command_id: str,
    current_user: CurrentUser = Depends(require_permissions(Permission.MISSION_COMMAND_READ)),
    db: AsyncSession = Depends(get_db),
) -> CausationChain:
    """Assemble and return the causation chain for a command.

    The chain links command events, receipts, and any run-control events
    that reference the command. Returns 404 if the command does not exist
    or belongs to a different tenant.
    """
    chain = await get_causation_chain(
        db,
        tenant_id=current_user.tenant_id,
        command_id=command_id,
    )
    if chain is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Command not found or not accessible within tenant scope.",
        )
    return chain


# ── Foundation: Sigma gate and cancellation status (read-only) ────────────────


@router.get("/sigma-gate", response_model=CancellationControlStatus)
async def get_sigma_gate(
    _: CurrentUser = Depends(require_permissions(Permission.MISSION_COMMAND_READ)),
) -> CancellationControlStatus:
    """Return the read-only Sigma gate and cancellation control status.

    The SIGMA_LEASE_EXPIRY_CONTINUATION_GATE is BLOCKED in the Foundation
    phase. All cancellation controls are DISABLED. This endpoint is
    read-only — no mutation surface exists.
    """
    return get_cancellation_status()

"""Mission Control read model.

This router intentionally exposes observation only. Command endpoints belong to
the governed execution layer and must not be simulated by the UI.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..auth.rbac import CurrentUser, Permission, require_permissions
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

    evidence_count = sum(
        int(case.get("evidence_items", 0)) for case in evidence.get("cases", [])
    )
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

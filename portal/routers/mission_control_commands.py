"""Governed Mission Control command ingestion."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.rbac import CurrentUser, Permission, require_permissions
from ..database import get_db
from ..models.mission_control_execution import Mission, Run
from ..services.audit_service import audit
from ..services.durable_orchestration_authority import DurableOrchestrationAuthority
from ..services.mission_control_command_service import (
    IDEMPOTENCY_KEY_MAX_LENGTH,
    IDEMPOTENCY_KEY_MIN_LENGTH,
    CommandSubmission,
    CommandTargetType,
    CommandType,
    DuplicateCommandConflictError,
    submit_canonical_command,
)
from ..services.orchestration_runtime import get_canonical_durable_engine

router = APIRouter(prefix="/api/v1/mission-control", tags=["mission-control"])


mission_control_execution_authority = DurableOrchestrationAuthority(
    engine=get_canonical_durable_engine()
)

COMMAND_PERMISSIONS: dict[CommandType, Permission] = {
    CommandType.START_GOVERNED_RUN: Permission.MISSION_RUN_START,
    CommandType.PAUSE_RUN: Permission.MISSION_RUN_PAUSE,
    CommandType.RESUME_RUN: Permission.MISSION_RUN_RESUME,
    CommandType.CANCEL_RUN: Permission.MISSION_RUN_CANCEL,
    CommandType.ASSIGN_AGENT: Permission.MISSION_AGENT_ASSIGN,
    CommandType.REASSIGN_AGENT: Permission.MISSION_AGENT_REASSIGN,
}

COMMAND_TARGET_COMPATIBILITY: dict[CommandType, frozenset[CommandTargetType]] = {
    CommandType.START_GOVERNED_RUN: frozenset({CommandTargetType.MISSION}),
    CommandType.PAUSE_RUN: frozenset({CommandTargetType.RUN}),
    CommandType.RESUME_RUN: frozenset({CommandTargetType.RUN}),
    CommandType.CANCEL_RUN: frozenset({CommandTargetType.RUN}),
    CommandType.ASSIGN_AGENT: frozenset(
        {CommandTargetType.RUN, CommandTargetType.TASK, CommandTargetType.MISSION}
    ),
    CommandType.REASSIGN_AGENT: frozenset(
        {CommandTargetType.RUN, CommandTargetType.TASK, CommandTargetType.MISSION}
    ),
}


class MissionControlCommandRequest(BaseModel):
    command_type: CommandType
    target_type: CommandTargetType
    target_id: str = Field(min_length=1, max_length=128)
    idempotency_key: str = Field(
        min_length=IDEMPOTENCY_KEY_MIN_LENGTH,
        max_length=IDEMPOTENCY_KEY_MAX_LENGTH,
    )
    reason: str | None = Field(default=None, max_length=2000)
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def canonical_payload(self) -> dict[str, Any]:
        """Only server-recognized input reaches the canonical execution lane."""
        raw_input = self.payload.get("input_data")
        return {"input_data": raw_input} if isinstance(raw_input, dict) else {}


class MissionControlCommandResponse(BaseModel):
    command_id: str
    command_type: str
    target_type: str
    target_id: str
    state: str
    reason_code: str | None
    reason: str | None
    duplicate: bool
    idempotency_key: str
    request_hash: str
    audit_log_id: str | None
    event_ids: list[str]
    receipt_id: str | None
    mission_id: str | None
    run_id: str | None
    execution_ref: str | None
    created_at: datetime | None
    completed_at: datetime | None


class MissionCreateResponse(BaseModel):
    mission_id: str
    status: str


class MissionReadModelResponse(BaseModel):
    missions: list[dict[str, Any]]
    runs: list[dict[str, Any]]


@router.post("/missions", response_model=MissionCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_mission(
    current_user: CurrentUser = Depends(require_permissions(Permission.MISSION_RUN_START)),
    db: AsyncSession = Depends(get_db),
) -> MissionCreateResponse:
    mission = Mission(tenant_id=str(current_user.tenant_id), created_by=str(current_user.user_id), status="ACTIVE")
    db.add(mission)
    await db.flush()
    await audit(db, action="mission_created", user_id=current_user.user_id,
                tenant_id=current_user.tenant_id, resource_type="mission",
                resource_id=mission.mission_id, status="success",
                details={"mission_id": mission.mission_id})
    return MissionCreateResponse(mission_id=mission.mission_id, status=mission.status)


@router.get("/missions", response_model=MissionReadModelResponse)
async def read_missions(
    current_user: CurrentUser = Depends(require_permissions(Permission.MISSION_COMMAND_READ)),
    db: AsyncSession = Depends(get_db),
) -> MissionReadModelResponse:
    tenant_id = str(current_user.tenant_id)
    missions = list((await db.execute(select(Mission).where(Mission.tenant_id == tenant_id))).scalars().all())
    runs = list((await db.execute(select(Run).where(Run.tenant_id == tenant_id))).scalars().all())
    return MissionReadModelResponse(
        missions=[{"mission_id": item.mission_id, "status": item.status} for item in missions],
        runs=[{"run_id": item.run_id, "mission_id": item.mission_id,
               "status": item.status, "execution_ref": item.execution_ref} for item in runs],
    )


@router.post(
    "/commands",
    response_model=MissionControlCommandResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_command(
    body: MissionControlCommandRequest,
    response: Response,
    current_user: CurrentUser = Depends(require_permissions(Permission.MISSION_COMMAND_CREATE)),
    db: AsyncSession = Depends(get_db),
) -> MissionControlCommandResponse:
    allowed_targets = COMMAND_TARGET_COMPATIBILITY[body.command_type]
    if body.target_type not in allowed_targets:
        allowed = sorted(target.value for target in allowed_targets)
        raise HTTPException(
            status_code=422,
            detail={
                "reason_code": "INVALID_COMMAND_TARGET",
                "allowed_target_types": allowed,
            },
        )

    specific_permission = COMMAND_PERMISSIONS[body.command_type]
    if not current_user.has_permission(specific_permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing permissions: {specific_permission}",
        )

    submission = CommandSubmission(
        command_type=body.command_type,
        target_type=body.target_type,
        target_id=body.target_id,
        idempotency_key=body.idempotency_key,
        reason=body.reason,
        payload=body.canonical_payload(),
        metadata=body.metadata,
    )
    try:
        result = await submit_canonical_command(
            db,
            submission,
            current_user,
            mission_control_execution_authority,
        )
    except DuplicateCommandConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "state": "DUPLICATE_CONFLICT",
                "reason_code": "IDEMPOTENCY_KEY_CONFLICT",
                "command_id": exc.command_id,
            },
        ) from exc

    if result.duplicate:
        response.status_code = status.HTTP_200_OK

    command = result.command
    return MissionControlCommandResponse(
        command_id=str(command.id),
        command_type=command.command_type,
        target_type=command.target_type,
        target_id=command.target_id,
        state=command.state,
        reason_code=command.reason_code,
        reason=command.reason,
        duplicate=result.duplicate,
        idempotency_key=command.idempotency_key,
        request_hash=command.request_hash,
        audit_log_id=str(command.audit_log_id) if command.audit_log_id else None,
        event_ids=result.event_ids,
        receipt_id=result.receipt_id,
        mission_id=result.mission_id,
        run_id=result.run_id,
        execution_ref=result.execution_ref,
        created_at=command.created_at,
        completed_at=command.completed_at,
    )

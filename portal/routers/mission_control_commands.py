"""Governed Mission Control command ingestion."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.rbac import CurrentUser, Permission, require_permissions
from ..database import get_db
from ..services.mission_control_command_service import (
    CommandSubmission,
    CommandTargetType,
    CommandType,
    DuplicateCommandConflictError,
    submit_refusal_only_command,
)

router = APIRouter(prefix="/api/v1/mission-control", tags=["mission-control"])


COMMAND_PERMISSIONS: dict[CommandType, Permission] = {
    CommandType.START_GOVERNED_RUN: Permission.MISSION_RUN_START,
    CommandType.PAUSE_RUN: Permission.MISSION_RUN_PAUSE,
    CommandType.RESUME_RUN: Permission.MISSION_RUN_RESUME,
    CommandType.CANCEL_RUN: Permission.MISSION_RUN_CANCEL,
    CommandType.ASSIGN_AGENT: Permission.MISSION_AGENT_ASSIGN,
    CommandType.REASSIGN_AGENT: Permission.MISSION_AGENT_REASSIGN,
}


class MissionControlCommandRequest(BaseModel):
    command_type: CommandType
    target_type: CommandTargetType
    target_id: str = Field(min_length=1, max_length=128)
    idempotency_key: str = Field(min_length=1, max_length=128)
    reason: str | None = Field(default=None, max_length=2000)
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


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
    created_at: datetime | None
    completed_at: datetime | None


@router.post(
    "/commands",
    response_model=MissionControlCommandResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_command(
    body: MissionControlCommandRequest,
    current_user: CurrentUser = Depends(require_permissions(Permission.MISSION_COMMAND_CREATE)),
    db: AsyncSession = Depends(get_db),
) -> MissionControlCommandResponse:
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
        payload=body.payload,
        metadata=body.metadata,
    )
    try:
        result = await submit_refusal_only_command(db, submission, current_user)
    except DuplicateCommandConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "state": "DUPLICATE_CONFLICT",
                "reason_code": "IDEMPOTENCY_KEY_CONFLICT",
                "command_id": exc.command_id,
            },
        ) from exc

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
        created_at=command.created_at,
        completed_at=command.completed_at,
    )

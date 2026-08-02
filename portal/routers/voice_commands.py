"""SP-VOICE-001 Increment Two — governed voice command API.

Every endpoint here is RBAC-gated, tenant-scoped from the verified JWT (never
from client-supplied identifiers), and can only ever produce mock/sandboxed
outcomes — see ``voice_concierge.governed.mock_providers`` and
``portal/services/voice_command_service.py``. No endpoint in this router can
place a real phone call, send a real email/message, create a real calendar
event, submit a real filing, or move real money.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from voice_concierge.governed.command_envelope import VoiceSource

from ..auth.rbac import CurrentUser, Permission, require_permissions
from ..database import get_db
from ..models.voice_command import VoiceCommand
from ..services.voice_command_service import (
    VoiceCommandNotFoundError,
    VoiceCommandStateError,
    VoiceCommandSubmission,
    cancel_voice_command,
    confirm_voice_command,
    get_voice_command,
    list_voice_commands,
    submit_voice_command,
)

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])


# ── Schemas ────────────────────────────────────────────────────────────────────


class VoiceCommandSubmitRequest(BaseModel):
    raw_transcript: str = Field(min_length=1, max_length=8000)
    source: VoiceSource = VoiceSource.DESKTOP_VOICE
    voice_session_id: str | None = Field(default=None, max_length=80)
    requested_capability: str | None = Field(default=None, max_length=40)
    target_resource: str | None = Field(default=None, max_length=255)
    normalized_intent: str | None = Field(default=None, max_length=8000)


class VoiceCommandConfirmRequest(BaseModel):
    utterance: str = Field(min_length=1, max_length=200)
    current_target: str | None = Field(default=None, max_length=255)


class VoiceCommandCancelRequest(BaseModel):
    reason: str = Field(default="cancelled by principal", max_length=2000)


class VoiceCommandResponse(BaseModel):
    command_id: str
    voice_session_id: str
    correlation_id: str
    source: str
    normalized_intent: str
    resolved_capability: str
    target_resource: str | None
    risk_class: str
    policy_decision: str
    confirmation_state: str
    session_state: str
    result: str
    reason: str | None
    provider_capability: str | None
    provider_resource_id: str | None
    provider_mock: bool | None
    artifacts: list[Any]
    audit_log_id: str | None
    created_at: datetime | None
    updated_at: datetime | None
    completed_at: datetime | None

    @classmethod
    def from_model(cls, command: VoiceCommand) -> VoiceCommandResponse:
        return cls(
            command_id=command.command_id,
            voice_session_id=command.voice_session_id,
            correlation_id=command.correlation_id,
            source=command.source,
            normalized_intent=command.normalized_intent,
            resolved_capability=command.resolved_capability,
            target_resource=command.target_resource,
            risk_class=command.risk_class,
            policy_decision=command.policy_decision,
            confirmation_state=command.confirmation_state,
            session_state=command.session_state,
            result=command.result,
            reason=command.reason,
            provider_capability=command.provider_capability,
            provider_resource_id=command.provider_resource_id,
            provider_mock=command.provider_mock,
            artifacts=list(command.artifacts or []),
            audit_log_id=command.audit_log_id,
            created_at=command.created_at,
            updated_at=command.updated_at,
            completed_at=command.completed_at,
        )


# ── Routes ─────────────────────────────────────────────────────────────────────


@router.post(
    "/commands",
    response_model=VoiceCommandResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_command(
    body: VoiceCommandSubmitRequest,
    current_user: CurrentUser = Depends(require_permissions(Permission.VOICE_COMMAND_CREATE)),
    db: AsyncSession = Depends(get_db),
) -> VoiceCommandResponse:
    submission = VoiceCommandSubmission(
        raw_transcript=body.raw_transcript,
        source=body.source,
        voice_session_id=body.voice_session_id,
        requested_capability=body.requested_capability,
        target_resource=body.target_resource,
        normalized_intent=body.normalized_intent,
    )
    result = await submit_voice_command(db, submission, current_user)
    return VoiceCommandResponse.from_model(result.command)


@router.get("/commands/{command_id}", response_model=VoiceCommandResponse)
async def get_command(
    command_id: str,
    current_user: CurrentUser = Depends(require_permissions(Permission.VOICE_COMMAND_READ)),
    db: AsyncSession = Depends(get_db),
) -> VoiceCommandResponse:
    try:
        command = await get_voice_command(db, command_id, current_user)
    except VoiceCommandNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="voice command not found") from exc
    return VoiceCommandResponse.from_model(command)


@router.get("/commands", response_model=list[VoiceCommandResponse])
async def list_commands(
    voice_session_id: str | None = None,
    current_user: CurrentUser = Depends(require_permissions(Permission.VOICE_COMMAND_READ)),
    db: AsyncSession = Depends(get_db),
) -> list[VoiceCommandResponse]:
    commands = await list_voice_commands(db, current_user, voice_session_id=voice_session_id)
    return [VoiceCommandResponse.from_model(c) for c in commands]


@router.post("/commands/{command_id}/confirm", response_model=VoiceCommandResponse)
async def confirm_command(
    command_id: str,
    body: VoiceCommandConfirmRequest,
    current_user: CurrentUser = Depends(require_permissions(Permission.VOICE_COMMAND_CONFIRM)),
    db: AsyncSession = Depends(get_db),
) -> VoiceCommandResponse:
    try:
        result = await confirm_voice_command(
            db,
            command_id,
            body.utterance,
            current_user,
            current_target=body.current_target,
        )
    except VoiceCommandNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="voice command not found") from exc
    except VoiceCommandStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return VoiceCommandResponse.from_model(result.command)


@router.post("/commands/{command_id}/cancel", response_model=VoiceCommandResponse)
async def cancel_command(
    command_id: str,
    body: VoiceCommandCancelRequest,
    current_user: CurrentUser = Depends(require_permissions(Permission.VOICE_COMMAND_CANCEL)),
    db: AsyncSession = Depends(get_db),
) -> VoiceCommandResponse:
    try:
        result = await cancel_voice_command(db, command_id, current_user, reason=body.reason)
    except VoiceCommandNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="voice command not found") from exc
    except VoiceCommandStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return VoiceCommandResponse.from_model(result.command)

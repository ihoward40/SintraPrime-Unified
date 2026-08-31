"""Mission Control command ledger service."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.rbac import CurrentUser
from ..models.mission_control_command import (
    MissionControlCommand,
    MissionControlCommandEvent,
    MissionControlCommandReceipt,
)
from ..models.mission_control_execution import Run
from ..services.audit_service import audit
from ..websocket.connection_manager import ws_manager
from .mission_control_command_guard import refuse_increment_one_execution
from .durable_orchestration_authority import DurableDispatchError, DurableOrchestrationAuthority
from .orchestration_runtime import get_canonical_durable_engine
from .mission_control_capability_policy import (
    CapabilityDecision,
    CapabilityPolicyError,
    resolve_capability_policy,
)
from .mission_control_execution_binding import (
    ExecutionBindingError,
    resolve_mission_capability,
)

log = structlog.get_logger(__name__)


class CommandType(StrEnum):
    START_GOVERNED_RUN = "START_GOVERNED_RUN"
    PAUSE_RUN = "PAUSE_RUN"
    RESUME_RUN = "RESUME_RUN"
    CANCEL_RUN = "CANCEL_RUN"
    ASSIGN_AGENT = "ASSIGN_AGENT"
    REASSIGN_AGENT = "REASSIGN_AGENT"


class CommandState(StrEnum):
    RECEIVED = "RECEIVED"
    VALIDATING = "VALIDATING"
    REFUSED = "REFUSED"
    DUPLICATE_REPLAYED = "DUPLICATE_REPLAYED"
    DUPLICATE_CONFLICT = "DUPLICATE_CONFLICT"
    COMPLETED = "COMPLETED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    FAILED = "FAILED"


class CommandTargetType(StrEnum):
    RUN = "run"
    AGENT = "agent"
    TASK = "task"
    MISSION = "mission"


IDEMPOTENCY_KEY_MIN_LENGTH = 16
IDEMPOTENCY_KEY_MAX_LENGTH = 128


@dataclass(frozen=True)
class CommandSubmission:
    command_type: CommandType
    target_type: CommandTargetType
    target_id: str
    idempotency_key: str
    reason: str | None
    payload: dict[str, Any]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class CommandResult:
    command: MissionControlCommand
    event_ids: list[str]
    receipt_id: str | None
    duplicate: bool = False
    mission_id: str | None = None
    run_id: str | None = None
    execution_ref: str | None = None


class DuplicateCommandConflictError(Exception):
    """Raised when an idempotency key is reused with a different request hash."""

    def __init__(self, command_id: str):
        self.command_id = command_id
        super().__init__("Idempotency key was already used for a different command request")


def canonical_request_hash(submission: CommandSubmission) -> str:
    """Hash only client-intended command content, never server identity context."""
    body = {
        "command_type": submission.command_type.value,
        "target_type": submission.target_type.value,
        "target_id": submission.target_id,
        "reason": submission.reason,
        "payload": submission.payload,
        "metadata": submission.metadata,
    }
    return _sha256_json(body)


def compute_event_hash(
    *,
    command_id: str,
    sequence: int,
    event_type: str,
    state: str,
    payload: dict[str, Any],
    previous_hash: str | None,
) -> str:
    return _sha256_json(
        {
            "command_id": command_id,
            "sequence": sequence,
            "event_type": event_type,
            "state": state,
            "payload": payload,
            "previous_hash": previous_hash,
        }
    )


def compute_receipt_hash(
    *,
    command_id: str,
    request_hash: str,
    reason_code: str,
    audit_log_id: str,
    terminal_event_hash: str,
) -> str:
    return _sha256_json(
        {
            "command_id": command_id,
            "request_hash": request_hash,
            "reason_code": reason_code,
            "audit_log_id": audit_log_id,
            "terminal_event_hash": terminal_event_hash,
        }
    )


async def submit_refusal_only_command(
    db: AsyncSession,
    submission: CommandSubmission,
    current_user: CurrentUser,
) -> CommandResult:
    request_hash = canonical_request_hash(submission)
    existing = await _find_existing(db, current_user, submission.idempotency_key)
    if existing:
        if existing.request_hash != request_hash:
            raise DuplicateCommandConflictError(str(existing.id))
        return await _duplicate_result(db, existing)

    command_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    reason_code = refuse_increment_one_execution().value
    command = MissionControlCommand(
        id=command_id,
        tenant_id=str(current_user.tenant_id),
        requested_by=str(current_user.user_id),
        command_type=submission.command_type.value,
        target_type=submission.target_type.value,
        target_id=submission.target_id,
        idempotency_key=submission.idempotency_key,
        request_hash=request_hash,
        state=CommandState.REFUSED.value,
        reason_code=reason_code,
        reason=submission.reason,
        payload=submission.payload,
        metadata_json=submission.metadata,
        completed_at=now,
    )
    db.add(command)
    try:
        await db.flush()
    except IntegrityError as exc:
        if not _is_idempotency_collision(exc):
            raise
        await db.rollback()
        existing_after_collision = await _find_existing(
            db,
            current_user,
            submission.idempotency_key,
        )
        if existing_after_collision is None:
            raise
        if existing_after_collision.request_hash != request_hash:
            raise DuplicateCommandConflictError(str(existing_after_collision.id)) from exc
        return await _duplicate_result(db, existing_after_collision)

    events = _build_events(command, reason_code)
    db.add_all(events)
    await db.flush()

    audit_entry = await audit(
        db,
        action="mission_control_command_refused",
        user_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        resource_type="mission_control_command",
        resource_id=command_id,
        resource_name=submission.command_type.value,
        status="refused",
        details={
            "command_type": submission.command_type.value,
            "target_type": submission.target_type.value,
            "target_id": submission.target_id,
            "idempotency_key": submission.idempotency_key,
            "request_hash": request_hash,
            "reason_code": reason_code,
            "mutation_enabled": False,
        },
    )
    await db.flush()
    command.audit_log_id = str(audit_entry.id)

    receipt = MissionControlCommandReceipt(
        id=str(uuid.uuid4()),
        command_id=command_id,
        receipt_type="REFUSAL",
        receipt_hash=compute_receipt_hash(
            command_id=command_id,
            request_hash=request_hash,
            reason_code=reason_code,
            audit_log_id=str(audit_entry.id),
            terminal_event_hash=events[-1].event_hash,
        ),
        audit_log_id=str(audit_entry.id),
        evidence_refs=[],
    )
    db.add(receipt)
    await db.flush()

    await _publish_status(current_user, command, receipt.id)
    return CommandResult(
        command=command,
        event_ids=[str(event.id) for event in events],
        receipt_id=str(receipt.id),
    )


async def submit_canonical_command(
    db: AsyncSession,
    submission: CommandSubmission,
    current_user: CurrentUser,
    authority: DurableOrchestrationAuthority | None = None,
) -> CommandResult:
    """Execute only ratified START/CANCEL; preserve refusal-only commands."""
    if submission.command_type not in {CommandType.START_GOVERNED_RUN, CommandType.CANCEL_RUN}:
        return await submit_refusal_only_command(db, submission, current_user)
    request_hash = canonical_request_hash(submission)
    existing = await _find_existing(db, current_user, submission.idempotency_key)
    if existing:
        if existing.request_hash != request_hash:
            raise DuplicateCommandConflictError(str(existing.id))
        result = await _duplicate_result(db, existing)
        meta = existing.metadata_json
        return CommandResult(command=result.command, event_ids=result.event_ids,
                             receipt_id=result.receipt_id, duplicate=True,
                             mission_id=meta.get("mission_id"), run_id=meta.get("run_id"),
                             execution_ref=meta.get("execution_ref"))

    authority = authority or DurableOrchestrationAuthority(
        engine=get_canonical_durable_engine()
    )
    tenant_id, actor_id = str(current_user.tenant_id), str(current_user.user_id)
    command = MissionControlCommand(
        id=str(uuid.uuid4()), tenant_id=tenant_id, requested_by=actor_id,
        command_type=submission.command_type.value, target_type=submission.target_type.value,
        target_id=submission.target_id, idempotency_key=submission.idempotency_key,
        request_hash=request_hash, state=CommandState.VALIDATING.value,
        reason=submission.reason, payload=submission.payload, metadata_json=submission.metadata,
    )
    db.add(command)
    await db.flush()
    run: Run | None = None
    try:
        if submission.command_type == CommandType.START_GOVERNED_RUN:
            capability = await resolve_mission_capability(
                db, mission_id=submission.target_id, tenant_id=tenant_id
            )
            policy = resolve_capability_policy(authority.engine, capability=capability)
            input_data = submission.payload.get("input_data") or {}
            run = await authority.start_run(
                db, mission_id=submission.target_id, tenant_id=tenant_id,
                created_by=actor_id,
                workflow_type=capability,
                input_data=input_data,
                policy_decision=policy,
            )
            if policy == CapabilityDecision.APPROVAL_REQUIRED:
                command.state = CommandState.APPROVAL_REQUIRED.value
                command.reason_code = "APPROVAL_REQUIRED"
            else:
                command.state = CommandState.COMPLETED.value
                command.reason_code = None
        else:
            run = await authority.get_run(db, run_id=submission.target_id, tenant_id=tenant_id)
            if run is None:
                raise ValueError("RUN_NOT_FOUND")
            cancelled = await authority.cancel_run(db, run_id=run.run_id, tenant_id=tenant_id)
            command.state = CommandState.COMPLETED.value if cancelled else CommandState.FAILED.value
            command.reason_code = None if cancelled else (run.failure_reason or "CANCEL_FAILED")
        command.completed_at = datetime.now(UTC)
    except (ExecutionBindingError, CapabilityPolicyError) as exc:
        command.state, command.reason_code = CommandState.REFUSED.value, str(exc)
        command.completed_at = datetime.now(UTC)
    except DurableDispatchError as exc:
        run = await authority.get_run(db, run_id=exc.run_id, tenant_id=tenant_id)
        command.state, command.reason_code = CommandState.FAILED.value, "DURABLE_DISPATCH_FAILED"
        command.completed_at = datetime.now(UTC)
    except ValueError as exc:
        command.state, command.reason_code = CommandState.REFUSED.value, str(exc)
        command.completed_at = datetime.now(UTC)
    except Exception as exc:
        reason = str(exc)
        if reason in {"MISSION_NOT_FOUND", "RUN_NOT_FOUND"}:
            command.state, command.reason_code = CommandState.REFUSED.value, reason
        else:
            command.state, command.reason_code = CommandState.FAILED.value, "DURABLE_DISPATCH_FAILED"
        command.completed_at = datetime.now(UTC)

    mission_id = run.mission_id if run else (submission.target_id if submission.target_type == CommandTargetType.MISSION else None)
    run_id, execution_ref = (run.run_id if run else None), (run.execution_ref if run else None)
    command.metadata_json = {**submission.metadata, "mission_id": mission_id,
                             "run_id": run_id, "execution_ref": execution_ref}
    events = _build_terminal_events(command)
    db.add_all(events)
    await db.flush()
    audit_entry = await audit(
        db, action="mission_control_command_processed", user_id=actor_id, tenant_id=tenant_id,
        resource_type="mission_control_command", resource_id=str(command.id),
        resource_name=command.command_type, status=command.state.lower(),
        details={"command_id": str(command.id), "mission_id": mission_id,
                 "run_id": run_id, "execution_ref": execution_ref, "state": command.state},
    )
    command.audit_log_id = str(audit_entry.id)
    receipt = MissionControlCommandReceipt(
        id=str(uuid.uuid4()), command_id=str(command.id), receipt_type="OUTCOME",
        receipt_hash=compute_receipt_hash(
            command_id=str(command.id), request_hash=request_hash,
            reason_code=command.reason_code or command.state,
            audit_log_id=str(audit_entry.id), terminal_event_hash=events[-1].event_hash,
        ), audit_log_id=str(audit_entry.id),
        evidence_refs=[ref for ref in [mission_id, run_id, execution_ref] if ref],
    )
    db.add(receipt)
    await db.flush()
    return CommandResult(command=command, event_ids=[str(event.id) for event in events],
                         receipt_id=str(receipt.id), mission_id=mission_id,
                         run_id=run_id, execution_ref=execution_ref)


def _build_terminal_events(command: MissionControlCommand) -> list[MissionControlCommandEvent]:
    specs = [
        ("COMMAND_RECEIVED", CommandState.RECEIVED.value, {}),
        ("COMMAND_VALIDATING", CommandState.VALIDATING.value, {}),
        ("COMMAND_TERMINAL", command.state, {"reason_code": command.reason_code}),
    ]
    previous_hash = None
    events = []
    for sequence, (event_type, state, payload) in enumerate(specs, start=1):
        event_hash = compute_event_hash(command_id=str(command.id), sequence=sequence,
                                        event_type=event_type, state=state, payload=payload,
                                        previous_hash=previous_hash)
        events.append(MissionControlCommandEvent(
            id=str(uuid.uuid4()), command_id=str(command.id), sequence=sequence,
            event_type=event_type, state=state, payload=payload,
            previous_hash=previous_hash, event_hash=event_hash,
        ))
        previous_hash = event_hash
    return events


def _is_idempotency_collision(exc: IntegrityError) -> bool:
    message = str(exc.orig).lower() if exc.orig else str(exc).lower()
    return "uq_mission_control_command_idempotency" in message or (
        "mission_control_commands.tenant_id" in message
        and "mission_control_commands.requested_by" in message
        and "mission_control_commands.idempotency_key" in message
    )


async def _find_existing(
    db: AsyncSession,
    current_user: CurrentUser,
    idempotency_key: str,
) -> MissionControlCommand | None:
    result = await db.execute(
        select(MissionControlCommand).where(
            MissionControlCommand.tenant_id == str(current_user.tenant_id),
            MissionControlCommand.requested_by == str(current_user.user_id),
            MissionControlCommand.idempotency_key == idempotency_key,
        )
    )
    return result.scalar_one_or_none()


async def _duplicate_result(
    db: AsyncSession,
    command: MissionControlCommand,
) -> CommandResult:
    event_result = await db.execute(
        select(MissionControlCommandEvent)
        .where(MissionControlCommandEvent.command_id == str(command.id))
        .order_by(MissionControlCommandEvent.sequence)
    )
    receipt_result = await db.execute(
        select(MissionControlCommandReceipt).where(
            MissionControlCommandReceipt.command_id == str(command.id),
            MissionControlCommandReceipt.receipt_type == "REFUSAL",
        )
    )
    events = list(event_result.scalars().all())
    receipt = receipt_result.scalar_one_or_none()
    return CommandResult(
        command=command,
        event_ids=[str(event.id) for event in events],
        receipt_id=str(receipt.id) if receipt else None,
        duplicate=True,
    )


def _build_events(
    command: MissionControlCommand,
    reason_code: str,
) -> list[MissionControlCommandEvent]:
    specs = [
        ("COMMAND_RECEIVED", CommandState.RECEIVED.value, {}),
        ("COMMAND_VALIDATING", CommandState.VALIDATING.value, {}),
        (
            "COMMAND_REFUSED",
            CommandState.REFUSED.value,
            {"reason_code": reason_code, "mutation_enabled": False},
        ),
    ]
    previous_hash = None
    events = []
    for sequence, (event_type, state, payload) in enumerate(specs, start=1):
        event_hash = compute_event_hash(
            command_id=str(command.id),
            sequence=sequence,
            event_type=event_type,
            state=state,
            payload=payload,
            previous_hash=previous_hash,
        )
        events.append(
            MissionControlCommandEvent(
                id=str(uuid.uuid4()),
                command_id=str(command.id),
                sequence=sequence,
                event_type=event_type,
                state=state,
                payload=payload,
                previous_hash=previous_hash,
                event_hash=event_hash,
            )
        )
        previous_hash = event_hash
    return events


async def _publish_status(
    current_user: CurrentUser,
    command: MissionControlCommand,
    receipt_id: str,
) -> None:
    event = {
        "type": "mission_control.command_status",
        "command_id": str(command.id),
        "state": command.state,
        "reason_code": command.reason_code,
        "target_type": command.target_type,
        "target_id": command.target_id,
        "receipt_id": receipt_id,
    }
    try:
        await ws_manager.send_to_user(str(current_user.user_id), event)
    except Exception as exc:
        log.warning(
            "mission_control.command_realtime_delivery_failed",
            command_id=str(command.id),
            user_id=str(current_user.user_id),
            error=str(exc),
        )


def _sha256_json(data: dict[str, Any]) -> str:
    serialized = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

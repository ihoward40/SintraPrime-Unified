"""Durable Mission Control execution path for explicitly activated orchestration commands."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.rbac import CurrentUser
from ..models.production_authority import (
    ProductionMissionControlCommand as MissionControlCommand,
    ProductionMissionControlCommandEvent as MissionControlCommandEvent,
    ProductionMissionControlCommandReceipt as MissionControlCommandReceipt,
)
from .durable_orchestration_authority import (
    DurableOrchestrationStateError,
    cancel_durable_run,
    start_durable_run,
)
from .mission_control_command_service import (
    CommandResult,
    CommandSubmission,
    CommandType,
    DuplicateCommandConflictError,
    canonical_request_hash,
    compute_event_hash,
    compute_receipt_hash,
)
from .orchestration.budget_policy import BudgetLimits
from .orchestration.schemas import ExecutionMode
from .production_authority_audit import append_production_authority_audit

ACTIVATION_MODE = "durable-orchestration-v1"
EXECUTABLE_COMMANDS = {CommandType.START_GOVERNED_RUN, CommandType.CANCEL_RUN}


class DurableCommandValidationError(ValueError):
    """Raised when an activated command lacks the bounded durable contract."""


async def submit_durable_orchestration_command(
    db: AsyncSession,
    submission: CommandSubmission,
    current_user: CurrentUser,
) -> tuple[CommandResult, str | None]:
    if submission.command_type not in EXECUTABLE_COMMANDS:
        raise DurableCommandValidationError("Command is not enabled for durable orchestration")
    if submission.payload.get("activation_mode") != ACTIVATION_MODE:
        raise DurableCommandValidationError("Durable orchestration activation mode is required")

    request_hash = canonical_request_hash(submission)
    existing = await _find_existing(db, current_user, submission.idempotency_key)
    if existing is not None:
        if existing.request_hash != request_hash:
            raise DuplicateCommandConflictError(str(existing.id))
        result, execution_ref = await _duplicate_result(db, existing)
        return result, execution_ref

    command = MissionControlCommand(
        id=str(uuid.uuid4()),
        tenant_id=str(current_user.tenant_id),
        requested_by=str(current_user.user_id),
        command_type=submission.command_type.value,
        target_type=submission.target_type.value,
        target_id=submission.target_id,
        idempotency_key=submission.idempotency_key,
        request_hash=request_hash,
        state="EXECUTING",
        reason_code="DURABLE_ORCHESTRATION_EXECUTION",
        reason=submission.reason,
        payload=submission.payload,
        metadata_json=submission.metadata,
    )
    try:
        async with db.begin_nested():
            db.add(command)
            await db.flush()
    except IntegrityError as exc:
        existing = await _find_existing(db, current_user, submission.idempotency_key)
        if existing is None:
            raise
        if existing.request_hash != request_hash:
            raise DuplicateCommandConflictError(str(existing.id)) from exc
        return await _duplicate_result(db, existing)

    execution_ref: str | None = None
    outcome_payload: dict[str, Any]
    try:
        if submission.command_type == CommandType.START_GOVERNED_RUN:
            run = await _start_run(db, submission, current_user)
            execution_ref = str(run["run_id"])
            outcome_payload = {
                "orchestration_run_id": execution_ref,
                "run_status": run["status"],
                "persistence": "postgresql-durable-orchestration",
                "external_action_performed": False,
            }
        else:
            run = await cancel_durable_run(
                db,
                run_id=submission.target_id,
                tenant_id=str(current_user.tenant_id),
                actor_id=str(current_user.user_id),
                reason=submission.reason or "Mission Control cancellation",
            )
            if run is None:
                raise DurableOrchestrationStateError("Orchestration run not found")
            execution_ref = str(run["run_id"])
            outcome_payload = {
                "orchestration_run_id": execution_ref,
                "run_status": run["status"],
                "persistence": "postgresql-durable-orchestration",
                "external_action_performed": False,
            }
        command.state = "COMPLETED"
        command.reason_code = "DURABLE_ORCHESTRATION_COMPLETED"
    except (DurableCommandValidationError, DurableOrchestrationStateError, ValueError) as exc:
        command.state = "FAILED"
        command.reason_code = "DURABLE_ORCHESTRATION_FAILED"
        outcome_payload = {
            "error": str(exc),
            "persistence": "postgresql-durable-orchestration",
            "external_action_performed": False,
        }

    command.completed_at = datetime.now(UTC)
    events = _build_execution_events(command, outcome_payload)
    db.add_all(events)
    await db.flush()

    audit_entry = await append_production_authority_audit(
        db,
        action="mission_control_durable_orchestration_command",
        user_id=str(current_user.user_id),
        tenant_id=str(current_user.tenant_id),
        resource_type="mission_control_command",
        resource_id=str(command.id),
        resource_name=command.command_type,
        status="success" if command.state == "COMPLETED" else "failed",
        details={
            "command_type": command.command_type,
            "target_type": command.target_type,
            "target_id": command.target_id,
            "request_hash": request_hash,
            "execution_ref": execution_ref,
            "state": command.state,
            "external_action_performed": False,
        },
    )
    command.audit_log_id = str(audit_entry.id)
    receipt = MissionControlCommandReceipt(
        id=str(uuid.uuid4()),
        command_id=str(command.id),
        receipt_type="EXECUTION",
        receipt_hash=compute_receipt_hash(
            command_id=str(command.id),
            request_hash=request_hash,
            reason_code=command.reason_code or "DURABLE_ORCHESTRATION",
            audit_log_id=str(audit_entry.id),
            terminal_event_hash=events[-1].event_hash,
        ),
        audit_log_id=str(audit_entry.id),
        evidence_refs=[
            {
                "type": "orchestration_run",
                "id": execution_ref,
                "durable": True,
            }
        ] if execution_ref else [],
    )
    db.add(receipt)
    await db.flush()
    return (
        CommandResult(
            command=command,
            event_ids=[str(event.id) for event in events],
            receipt_id=str(receipt.id),
        ),
        execution_ref,
    )


async def _start_run(
    db: AsyncSession,
    submission: CommandSubmission,
    current_user: CurrentUser,
) -> dict[str, Any]:
    objective = submission.payload.get("objective")
    if not isinstance(objective, str) or not objective.strip():
        raise DurableCommandValidationError("START_GOVERNED_RUN requires payload.objective")
    constraints = submission.payload.get("constraints", {})
    if not isinstance(constraints, dict):
        raise DurableCommandValidationError("payload.constraints must be an object")
    try:
        execution_mode = ExecutionMode(
            submission.payload.get("execution_mode", ExecutionMode.THINK_WORK_CHECK.value)
        )
    except ValueError as exc:
        raise DurableCommandValidationError("Invalid payload.execution_mode") from exc
    budget_payload = submission.payload.get("budget_limits")
    if budget_payload is not None and not isinstance(budget_payload, dict):
        raise DurableCommandValidationError("payload.budget_limits must be an object")
    budget_limits = BudgetLimits(**budget_payload) if budget_payload else None
    return await start_durable_run(
        db,
        objective=objective,
        constraints=constraints,
        execution_mode=execution_mode,
        budget_limits=budget_limits,
        tenant_id=str(current_user.tenant_id),
        created_by=str(current_user.user_id),
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
) -> tuple[CommandResult, str | None]:
    event_result = await db.execute(
        select(MissionControlCommandEvent)
        .where(MissionControlCommandEvent.command_id == str(command.id))
        .order_by(MissionControlCommandEvent.sequence)
    )
    receipt_result = await db.execute(
        select(MissionControlCommandReceipt).where(
            MissionControlCommandReceipt.command_id == str(command.id),
            MissionControlCommandReceipt.receipt_type == "EXECUTION",
        )
    )
    events = list(event_result.scalars().all())
    receipt = receipt_result.scalar_one_or_none()
    execution_ref = None
    if receipt:
        for ref in receipt.evidence_refs or []:
            if isinstance(ref, dict) and ref.get("type") == "orchestration_run":
                execution_ref = ref.get("id")
                break
    return (
        CommandResult(
            command=command,
            event_ids=[str(event.id) for event in events],
            receipt_id=str(receipt.id) if receipt else None,
            duplicate=True,
        ),
        str(execution_ref) if execution_ref else None,
    )


def _build_execution_events(
    command: MissionControlCommand,
    outcome_payload: dict[str, Any],
) -> list[MissionControlCommandEvent]:
    terminal_event_type = "COMMAND_COMPLETED" if command.state == "COMPLETED" else "COMMAND_FAILED"
    specs = [
        ("COMMAND_RECEIVED", "RECEIVED", {}),
        ("COMMAND_VALIDATING", "VALIDATING", {"activation_mode": ACTIVATION_MODE}),
        ("COMMAND_EXECUTING", "EXECUTING", {"mutation_scope": "durable_orchestration_only"}),
        (terminal_event_type, command.state, outcome_payload),
    ]
    previous_hash = None
    events: list[MissionControlCommandEvent] = []
    for sequence, (event_type, state, payload) in enumerate(specs, start=1):
        event_hash = compute_event_hash(
            command_id=str(command.id),
            sequence=sequence,
            event_type=event_type,
            state=state,
            payload=payload,
            previous_hash=previous_hash,
        )
        event = MissionControlCommandEvent(
            id=str(uuid.uuid4()),
            command_id=str(command.id),
            sequence=sequence,
            event_type=event_type,
            state=state,
            payload=payload,
            previous_hash=previous_hash,
            event_hash=event_hash,
        )
        events.append(event)
        previous_hash = event_hash
    return events
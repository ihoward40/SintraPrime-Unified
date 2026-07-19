"""Mission Control run-control transition service."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.mission_control_run_control import (
    MissionControlRunControl,
    MissionControlRunControlEvent,
    RunControlState,
)

PROJECTION_SCHEMA_VERSION = 1
EVENT_SCHEMA_VERSION = 1


class RunControlConflictError(Exception):
    """Raised when a state transition loses an optimistic concurrency race."""


class RunControlInvalidTransitionError(Exception):
    """Raised when a requested state transition is not allowed."""


class RunControlEventType(StrEnum):
    CREATED = "CREATED"
    STATE_TRANSITIONED = "STATE_TRANSITIONED"
    TERMINAL_PROJECTED = "TERMINAL_PROJECTED"
    PAUSE_TIMED_OUT = "PAUSE_TIMED_OUT"
    SUPERSEDED = "SUPERSEDED"


TERMINAL_STATES = {
    RunControlState.COMPLETED,
    RunControlState.FAILED,
    RunControlState.CANCELLED,
    RunControlState.COMPENSATED,
}

ALLOWED_TRANSITIONS: dict[RunControlState, set[RunControlState]] = {
    RunControlState.RUNNING: {
        RunControlState.PAUSE_REQUESTED,
        RunControlState.COMPLETED,
        RunControlState.FAILED,
        RunControlState.CANCELLED,
        RunControlState.COMPENSATING,
    },
    RunControlState.PAUSE_REQUESTED: {
        RunControlState.PAUSING,
        RunControlState.PAUSE_FAILED,
        RunControlState.PAUSE_TIMED_OUT,
        RunControlState.SUPERSEDED,
        RunControlState.COMPLETED,
        RunControlState.FAILED,
        RunControlState.CANCELLED,
        RunControlState.COMPENSATING,
    },
    RunControlState.PAUSING: {
        RunControlState.PAUSED,
        RunControlState.PAUSE_FAILED,
        RunControlState.PAUSE_TIMED_OUT,
        RunControlState.SUPERSEDED,
        RunControlState.COMPLETED,
        RunControlState.FAILED,
        RunControlState.CANCELLED,
        RunControlState.COMPENSATING,
    },
    RunControlState.PAUSED: set(),
    RunControlState.PAUSE_FAILED: set(),
    RunControlState.PAUSE_TIMED_OUT: set(),
    RunControlState.SUPERSEDED: set(),
    RunControlState.COMPLETED: set(),
    RunControlState.FAILED: set(),
    RunControlState.CANCELLED: set(),
    RunControlState.COMPENSATING: {RunControlState.COMPENSATED},
    RunControlState.COMPENSATED: set(),
}


@dataclass(slots=True)
class RunControlTransitionResult:
    run_control: MissionControlRunControl
    event: MissionControlRunControlEvent


async def create_run_control(
    db: AsyncSession,
    *,
    tenant_id: str,
    workflow_id: str,
    workflow_status_snapshot: str,
    workflow_status_observed_at: datetime | None = None,
    workflow_source: str | None = None,
    workflow_version_snapshot: int | None = None,
    state: RunControlState = RunControlState.RUNNING,
    command_id: str | None = None,
    requested_by: str | None = None,
    pause_reason: str | None = None,
    confirmation_ref: str | None = None,
    acknowledged_by: str | None = None,
    acknowledged_at: datetime | None = None,
    paused_at: datetime | None = None,
    failed_at: datetime | None = None,
    timed_out_at: datetime | None = None,
    superseded_at: datetime | None = None,
    incident_id: str | None = None,
    recovery_ref: str | None = None,
    terminal_reason_code: str | None = None,
    last_error: str | None = None,
    projection_schema_version: int = PROJECTION_SCHEMA_VERSION,
) -> MissionControlRunControl:
    existing = await _load_run_control_by_workflow(db, tenant_id=tenant_id, workflow_id=workflow_id)
    if existing is not None:
        return existing

    now = datetime.now(UTC)
    control = MissionControlRunControl(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        command_id=command_id,
        state=state.value,
        workflow_status_snapshot=workflow_status_snapshot,
        workflow_status_observed_at=workflow_status_observed_at or now,
        workflow_source=workflow_source,
        workflow_version_snapshot=workflow_version_snapshot,
        state_version=1,
        projection_schema_version=projection_schema_version,
        pause_reason=pause_reason,
        requested_by=requested_by,
        requested_at=now if requested_by else None,
        confirmation_ref=confirmation_ref,
        acknowledged_by=acknowledged_by,
        acknowledged_at=acknowledged_at,
        paused_at=paused_at,
        failed_at=failed_at,
        timed_out_at=timed_out_at,
        superseded_at=superseded_at,
        incident_id=incident_id,
        recovery_ref=recovery_ref,
        terminal_reason_code=terminal_reason_code,
        last_error=last_error,
        created_at=now,
        updated_at=now,
    )
    db.add(control)
    await db.flush()

    event_payload = {
        "workflow_id": workflow_id,
        "workflow_source": workflow_source,
        "workflow_status_snapshot": workflow_status_snapshot,
        "workflow_status_observed_at": _isoformat(workflow_status_observed_at or now),
        "workflow_version_snapshot": workflow_version_snapshot,
        "projection_schema_version": projection_schema_version,
        "state": state.value,
        "terminal_reason_code": terminal_reason_code,
        "confirmation_ref": confirmation_ref,
        "acknowledged_by": acknowledged_by,
        "acknowledged_at": _isoformat(acknowledged_at),
        "paused_at": _isoformat(paused_at),
        "failed_at": _isoformat(failed_at),
        "timed_out_at": _isoformat(timed_out_at),
        "superseded_at": _isoformat(superseded_at),
        "incident_id": incident_id,
        "recovery_ref": recovery_ref,
        "last_error": last_error,
    }
    event = MissionControlRunControlEvent(
        id=str(uuid.uuid4()),
        run_control_id=control.id,
        sequence=1,
        event_type=RunControlEventType.CREATED.value,
        previous_state=state.value,
        new_state=state.value,
        previous_version=0,
        new_version=1,
        principal_id=requested_by,
        command_id=command_id,
        reason=pause_reason,
        payload=event_payload,
        workflow_status_observed_at=workflow_status_observed_at or now,
        previous_event_hash=None,
        event_hash=_compute_event_hash(
            run_control_id=control.id,
            sequence=1,
            event_type=RunControlEventType.CREATED.value,
            previous_state=state.value,
            new_state=state.value,
            previous_version=0,
            new_version=1,
            principal_id=requested_by,
            command_id=command_id,
            reason=pause_reason,
            payload=event_payload,
            previous_event_hash=None,
            workflow_status_observed_at=workflow_status_observed_at or now,
            event_schema_version=EVENT_SCHEMA_VERSION,
        ),
        event_schema_version=EVENT_SCHEMA_VERSION,
    )
    db.add(event)
    await db.flush()
    return control


async def transition_run_control(
    db: AsyncSession,
    *,
    tenant_id: str,
    run_control_id: str,
    expected_version: int,
    new_state: RunControlState,
    requested_by: str | None,
    reason: str | None,
    command_id: str | None,
    workflow_status_snapshot: str,
    workflow_status_observed_at: datetime | None = None,
    workflow_source: str | None = None,
    workflow_version_snapshot: int | None = None,
    confirmation_ref: str | None = None,
    acknowledged_by: str | None = None,
    acknowledged_at: datetime | None = None,
    paused_at: datetime | None = None,
    failed_at: datetime | None = None,
    timed_out_at: datetime | None = None,
    superseded_at: datetime | None = None,
    incident_id: str | None = None,
    recovery_ref: str | None = None,
    terminal_reason_code: str | None = None,
    last_error: str | None = None,
    projection_schema_version: int = PROJECTION_SCHEMA_VERSION,
    event_type: RunControlEventType = RunControlEventType.STATE_TRANSITIONED,
) -> MissionControlRunControl:
    control = await _load_run_control(db, tenant_id=tenant_id, run_control_id=run_control_id)
    if control is None:
        raise RunControlInvalidTransitionError(f"run control not found: {run_control_id}")

    current_state = RunControlState(control.state)
    if control.state_version != expected_version:
        raise RunControlConflictError(
            f"stale version for {run_control_id}: expected {expected_version}, found {control.state_version}"
        )

    if not _transition_allowed(current_state, new_state):
        raise RunControlInvalidTransitionError(f"transition {current_state.value} -> {new_state.value} is not allowed")

    if current_state in TERMINAL_STATES:
        raise RunControlInvalidTransitionError(f"terminal state {current_state.value} cannot be changed")

    now = datetime.now(UTC)
    observed_at = workflow_status_observed_at or now
    next_version = expected_version + 1
    effective_paused_at = paused_at or (now if new_state == RunControlState.PAUSED else control.paused_at)
    effective_failed_at = failed_at or (now if new_state == RunControlState.PAUSE_FAILED else control.failed_at)
    effective_timed_out_at = timed_out_at or (now if new_state == RunControlState.PAUSE_TIMED_OUT else control.timed_out_at)
    effective_superseded_at = superseded_at or (now if new_state == RunControlState.SUPERSEDED else control.superseded_at)
    effective_terminal_reason_code = terminal_reason_code or control.terminal_reason_code
    if new_state in TERMINAL_STATES and effective_terminal_reason_code is None:
        effective_terminal_reason_code = reason

    update_values: dict[str, Any] = {
        "state": new_state.value,
        "workflow_status_snapshot": workflow_status_snapshot,
        "workflow_status_observed_at": observed_at,
        "workflow_source": workflow_source if workflow_source is not None else control.workflow_source,
        "workflow_version_snapshot": (
            workflow_version_snapshot if workflow_version_snapshot is not None else control.workflow_version_snapshot
        ),
        "state_version": next_version,
        "projection_schema_version": projection_schema_version,
        "updated_at": now,
        "command_id": command_id if command_id is not None else control.command_id,
        "requested_by": requested_by if requested_by is not None else control.requested_by,
        "requested_at": now if new_state == RunControlState.PAUSE_REQUESTED and requested_by else control.requested_at,
        "pause_reason": reason if reason is not None else control.pause_reason,
        "confirmation_ref": confirmation_ref if confirmation_ref is not None else control.confirmation_ref,
        "acknowledged_by": acknowledged_by if acknowledged_by is not None else control.acknowledged_by,
        "acknowledged_at": acknowledged_at if acknowledged_at is not None else control.acknowledged_at,
        "paused_at": effective_paused_at,
        "failed_at": effective_failed_at,
        "timed_out_at": effective_timed_out_at,
        "superseded_at": effective_superseded_at,
        "incident_id": incident_id if incident_id is not None else control.incident_id,
        "recovery_ref": recovery_ref if recovery_ref is not None else control.recovery_ref,
        "terminal_reason_code": effective_terminal_reason_code,
        "last_error": last_error if last_error is not None else control.last_error,
    }

    result = await db.execute(
        update(MissionControlRunControl)
        .where(
            and_(
                MissionControlRunControl.id == run_control_id,
                MissionControlRunControl.state_version == expected_version,
                MissionControlRunControl.state == current_state.value,
            )
        )
        .values(**update_values)
    )
    if getattr(result, "rowcount", 0) != 1:
        raise RunControlConflictError(f"run control {run_control_id} changed concurrently")

    await db.flush()
    updated = await _load_run_control(db, tenant_id=tenant_id, run_control_id=run_control_id)
    if updated is None:
        raise RunControlInvalidTransitionError(f"run control missing after update: {run_control_id}")

    previous_event_hash = await _last_event_hash(db, run_control_id)
    event_payload = {
        "workflow_status_snapshot": workflow_status_snapshot,
        "workflow_status_observed_at": _isoformat(observed_at),
        "workflow_source": workflow_source if workflow_source is not None else control.workflow_source,
        "workflow_version_snapshot": workflow_version_snapshot if workflow_version_snapshot is not None else control.workflow_version_snapshot,
        "projection_schema_version": projection_schema_version,
        "confirmation_ref": confirmation_ref,
        "acknowledged_by": acknowledged_by,
        "acknowledged_at": _isoformat(acknowledged_at),
        "paused_at": _isoformat(effective_paused_at),
        "failed_at": _isoformat(effective_failed_at),
        "timed_out_at": _isoformat(effective_timed_out_at),
        "superseded_at": _isoformat(effective_superseded_at),
        "incident_id": incident_id,
        "recovery_ref": recovery_ref,
        "terminal_reason_code": effective_terminal_reason_code,
        "last_error": last_error,
    }
    event = MissionControlRunControlEvent(
        id=str(uuid.uuid4()),
        run_control_id=run_control_id,
        sequence=next_version,
        event_type=event_type.value,
        previous_state=current_state.value,
        new_state=new_state.value,
        previous_version=expected_version,
        new_version=next_version,
        principal_id=requested_by,
        command_id=command_id,
        reason=reason,
        payload=event_payload,
        workflow_status_observed_at=observed_at,
        previous_event_hash=previous_event_hash,
        event_hash=_compute_event_hash(
            run_control_id=run_control_id,
            sequence=next_version,
            event_type=event_type.value,
            previous_state=current_state.value,
            new_state=new_state.value,
            previous_version=expected_version,
            new_version=next_version,
            principal_id=requested_by,
            command_id=command_id,
            reason=reason,
            payload=event_payload,
            previous_event_hash=previous_event_hash,
            workflow_status_observed_at=observed_at,
            event_schema_version=EVENT_SCHEMA_VERSION,
        ),
        event_schema_version=EVENT_SCHEMA_VERSION,
    )
    db.add(event)
    await db.flush()
    return updated


async def _load_run_control(
    db: AsyncSession,
    *,
    tenant_id: str,
    run_control_id: str,
) -> MissionControlRunControl | None:
    result = await db.execute(
        select(MissionControlRunControl).where(
            MissionControlRunControl.id == run_control_id,
            MissionControlRunControl.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def _load_run_control_by_workflow(
    db: AsyncSession,
    *,
    tenant_id: str,
    workflow_id: str,
) -> MissionControlRunControl | None:
    result = await db.execute(
        select(MissionControlRunControl).where(
            MissionControlRunControl.tenant_id == tenant_id,
            MissionControlRunControl.workflow_id == workflow_id,
        )
    )
    return result.scalar_one_or_none()


async def _last_event_hash(db: AsyncSession, run_control_id: str) -> str | None:
    result = await db.execute(
        select(MissionControlRunControlEvent.event_hash)
        .where(MissionControlRunControlEvent.run_control_id == run_control_id)
        .order_by(MissionControlRunControlEvent.sequence.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def _transition_allowed(current_state: RunControlState, new_state: RunControlState) -> bool:
    if current_state in TERMINAL_STATES:
        return False
    allowed = ALLOWED_TRANSITIONS.get(current_state, set())
    return new_state in allowed


def _compute_event_hash(
    *,
    run_control_id: str,
    sequence: int,
    event_type: str,
    previous_state: str,
    new_state: str,
    previous_version: int,
    new_version: int,
    principal_id: str | None,
    command_id: str | None,
    reason: str | None,
    payload: dict[str, Any],
    previous_event_hash: str | None,
    workflow_status_observed_at: datetime,
    event_schema_version: int,
) -> str:
    data = {
        "run_control_id": run_control_id,
        "sequence": sequence,
        "event_type": event_type,
        "previous_state": previous_state,
        "new_state": new_state,
        "previous_version": previous_version,
        "new_version": new_version,
        "principal_id": principal_id,
        "command_id": command_id,
        "reason": reason,
        "payload": payload,
        "previous_event_hash": previous_event_hash,
        "workflow_status_observed_at": _isoformat(workflow_status_observed_at),
        "event_schema_version": event_schema_version,
    }
    serialized = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _isoformat(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat() if value else None

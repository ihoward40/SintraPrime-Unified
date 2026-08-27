"""Canonical PostgreSQL scheduler authority for bounded governed missions (Gate 3)."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.production_scheduler_authority import (
    ProductionGovernedSchedule as GovernedSchedule,
)
from ..models.production_scheduler_authority import (
    ProductionGovernedScheduleEvent as GovernedScheduleEvent,
)
from .durable_orchestration_authority import start_durable_run
from .orchestration.budget_policy import BudgetLimits
from .orchestration.schemas import ExecutionMode


class SchedulerStateError(ValueError):
    """Raised when a scheduler lifecycle transition is invalid."""


class SchedulerIdempotencyConflictError(ValueError):
    """Raised when an idempotency key is reused for different scheduler content."""

    def __init__(self, schedule_id: str):
        self.schedule_id = schedule_id
        super().__init__("Idempotency key was already used for a different schedule request")


def _canonical_hash(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def canonical_schedule_request_hash(
    *,
    objective: str,
    constraints: dict[str, Any],
    execution_mode: str,
    budget_limits: dict[str, Any] | None,
    run_at: datetime,
    service_identity_id: str | None,
) -> str:
    return _canonical_hash(
        {
            "objective": objective,
            "constraints": constraints,
            "execution_mode": execution_mode,
            "budget_limits": budget_limits,
            "run_at": run_at.astimezone(UTC).isoformat(),
            "service_identity_id": service_identity_id,
            "schedule_kind": "ONCE",
        }
    )


def _event_hash(
    *,
    schedule_id: str,
    sequence: int,
    event_type: str,
    status: str,
    payload: dict[str, Any],
    previous_hash: str | None,
    created_at: datetime,
) -> str:
    return _canonical_hash(
        {
            "schedule_id": schedule_id,
            "sequence": sequence,
            "event_type": event_type,
            "status": status,
            "payload": payload,
            "previous_hash": previous_hash,
            "created_at": created_at.isoformat(),
        }
    )


async def create_schedule(
    db: AsyncSession,
    *,
    tenant_id: str,
    created_by: str,
    objective: str,
    constraints: dict[str, Any] | None,
    execution_mode: str,
    budget_limits: dict[str, Any] | None,
    run_at: datetime,
    idempotency_key: str,
    service_identity_id: str | None = None,
) -> dict[str, Any]:
    """Create one durable ONCE schedule; repeated identical requests are replay-safe."""
    if run_at.tzinfo is None:
        raise ValueError("run_at must include a timezone")
    normalized_run_at = run_at.astimezone(UTC)
    normalized_constraints = constraints or {}
    request_hash = canonical_schedule_request_hash(
        objective=objective,
        constraints=normalized_constraints,
        execution_mode=execution_mode,
        budget_limits=budget_limits,
        run_at=normalized_run_at,
        service_identity_id=service_identity_id,
    )

    existing = await _find_by_idempotency_key(
        db,
        tenant_id=tenant_id,
        created_by=created_by,
        idempotency_key=idempotency_key,
    )
    if existing is not None:
        if existing.request_hash != request_hash:
            raise SchedulerIdempotencyConflictError(str(existing.id))
        return await get_schedule(db, schedule_id=str(existing.id), tenant_id=tenant_id)  # type: ignore[return-value]

    schedule_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    row = GovernedSchedule(
        id=schedule_id,
        tenant_id=tenant_id,
        created_by=created_by,
        service_identity_id=service_identity_id,
        objective=objective,
        constraints=normalized_constraints,
        execution_mode=execution_mode,
        budget_limits=budget_limits,
        schedule_kind="ONCE",
        run_at=normalized_run_at,
        status="SCHEDULED",
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        created_at=now,
        updated_at=now,
    )
    try:
        async with db.begin_nested():
            db.add(row)
            await db.flush()
            await _append_event(
                db,
                schedule_id=schedule_id,
                event_type="SCHEDULE_CREATED",
                status="SCHEDULED",
                payload={
                    "run_at": normalized_run_at.isoformat(),
                    "request_hash": request_hash,
                    "external_action_performed": False,
                },
            )
            await db.flush()
    except IntegrityError as exc:
        existing = await _find_by_idempotency_key(
            db,
            tenant_id=tenant_id,
            created_by=created_by,
            idempotency_key=idempotency_key,
        )
        if existing is None:
            raise
        if existing.request_hash != request_hash:
            raise SchedulerIdempotencyConflictError(str(existing.id)) from exc
        return await get_schedule(db, schedule_id=str(existing.id), tenant_id=tenant_id)  # type: ignore[return-value]

    result = await get_schedule(db, schedule_id=schedule_id, tenant_id=tenant_id)
    if result is None:
        raise RuntimeError("Governed schedule was not persisted")
    return result


async def get_schedule(
    db: AsyncSession,
    *,
    schedule_id: str,
    tenant_id: str,
) -> dict[str, Any] | None:
    row = (
        await db.execute(
            select(GovernedSchedule).where(
                GovernedSchedule.id == schedule_id,
                GovernedSchedule.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    events = list(
        (
            await db.execute(
                select(GovernedScheduleEvent)
                .where(GovernedScheduleEvent.schedule_id == schedule_id)
                .order_by(GovernedScheduleEvent.sequence)
            )
        ).scalars()
    )
    return _serialize_schedule(row, events)


async def list_schedules(db: AsyncSession, *, tenant_id: str) -> list[dict[str, Any]]:
    rows = list(
        (
            await db.execute(
                select(GovernedSchedule)
                .where(GovernedSchedule.tenant_id == tenant_id)
                .order_by(GovernedSchedule.run_at, GovernedSchedule.created_at)
            )
        ).scalars()
    )
    results: list[dict[str, Any]] = []
    for row in rows:
        item = await get_schedule(db, schedule_id=str(row.id), tenant_id=tenant_id)
        if item is not None:
            results.append(item)
    return results


async def cancel_schedule(
    db: AsyncSession,
    *,
    schedule_id: str,
    tenant_id: str,
    actor_id: str,
    reason: str,
) -> dict[str, Any] | None:
    row = await _locked_schedule(db, schedule_id=schedule_id, tenant_id=tenant_id)
    if row is None:
        return None
    if row.status == "CANCELLED":
        return await get_schedule(db, schedule_id=schedule_id, tenant_id=tenant_id)
    if row.status in {"DISPATCHED", "FAILED"}:
        raise SchedulerStateError(f"Cannot cancel schedule in terminal state {row.status}")
    if row.status == "CLAIMED":
        raise SchedulerStateError("Cannot cancel a schedule while dispatch is claimed")

    now = datetime.now(UTC)
    row.status = "CANCELLED"
    row.cancelled_at = now
    row.cancellation_reason = reason
    row.updated_at = now
    await _append_event(
        db,
        schedule_id=schedule_id,
        event_type="SCHEDULE_CANCELLED",
        status="CANCELLED",
        payload={"actor_id": actor_id, "reason": reason, "external_action_performed": False},
    )
    await db.flush()
    return await get_schedule(db, schedule_id=schedule_id, tenant_id=tenant_id)


async def dispatch_due_schedule(
    db: AsyncSession,
    *,
    schedule_id: str,
    tenant_id: str,
    worker_id: str,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    """Claim and dispatch one due schedule into durable orchestration exactly once.

    This creates only a bounded internal orchestration run. It does not invoke an
    external adapter or consequential side effect.
    """
    effective_now = (now or datetime.now(UTC)).astimezone(UTC)
    row = await _locked_schedule(db, schedule_id=schedule_id, tenant_id=tenant_id, skip_locked=True)
    if row is None:
        return None
    if row.status == "DISPATCHED":
        return await get_schedule(db, schedule_id=schedule_id, tenant_id=tenant_id)
    if row.status != "SCHEDULED":
        raise SchedulerStateError(f"Schedule is not dispatchable from state {row.status}")
    run_at = row.run_at
    if run_at.tzinfo is None:
        run_at = run_at.replace(tzinfo=UTC)
    if run_at > effective_now:
        raise SchedulerStateError("Schedule is not due yet")

    row.status = "CLAIMED"
    row.claimed_at = effective_now
    row.claimed_by = worker_id
    row.updated_at = effective_now
    await _append_event(
        db,
        schedule_id=schedule_id,
        event_type="SCHEDULE_CLAIMED",
        status="CLAIMED",
        payload={"worker_id": worker_id, "claimed_at": effective_now.isoformat()},
    )
    await db.flush()

    budget_limits = BudgetLimits(**row.budget_limits) if row.budget_limits else None
    run = await start_durable_run(
        db,
        objective=row.objective,
        constraints=row.constraints or {},
        execution_mode=ExecutionMode(row.execution_mode),
        budget_limits=budget_limits,
        tenant_id=str(row.tenant_id),
        created_by=str(row.created_by),
    )

    dispatched_at = datetime.now(UTC)
    row.status = "DISPATCHED"
    row.dispatched_run_id = str(run["run_id"])
    row.dispatched_at = dispatched_at
    row.updated_at = dispatched_at
    await _append_event(
        db,
        schedule_id=schedule_id,
        event_type="SCHEDULE_DISPATCHED",
        status="DISPATCHED",
        payload={
            "worker_id": worker_id,
            "run_id": str(run["run_id"]),
            "orchestration_status": run["status"],
            "external_action_performed": False,
        },
    )
    await db.flush()
    return await get_schedule(db, schedule_id=schedule_id, tenant_id=tenant_id)


async def replay_schedule(
    db: AsyncSession,
    *,
    schedule_id: str,
    tenant_id: str,
) -> dict[str, Any] | None:
    """Verify the immutable event chain and reconstruct the authoritative state."""
    schedule = await get_schedule(db, schedule_id=schedule_id, tenant_id=tenant_id)
    if schedule is None:
        return None
    previous_hash: str | None = None
    replay_status: str | None = None
    for event in schedule["events"]:
        created_at = datetime.fromisoformat(str(event["created_at"]).replace("Z", "+00:00"))
        expected_hash = _event_hash(
            schedule_id=schedule_id,
            sequence=int(event["sequence"]),
            event_type=str(event["event_type"]),
            status=str(event["status"]),
            payload=dict(event["payload"]),
            previous_hash=previous_hash,
            created_at=created_at,
        )
        if event["previous_hash"] != previous_hash or event["event_hash"] != expected_hash:
            raise SchedulerStateError("Scheduler event hash chain verification failed")
        replay_status = str(event["status"])
        previous_hash = str(event["event_hash"])
    if replay_status != schedule["status"]:
        raise SchedulerStateError("Scheduler replay status does not match durable projection")
    return {
        "schedule_id": schedule_id,
        "status": replay_status,
        "event_count": len(schedule["events"]),
        "head_hash": previous_hash,
        "projection_matches": True,
        "dispatched_run_id": schedule.get("dispatched_run_id"),
    }


async def _find_by_idempotency_key(
    db: AsyncSession,
    *,
    tenant_id: str,
    created_by: str,
    idempotency_key: str,
) -> GovernedSchedule | None:
    return (
        await db.execute(
            select(GovernedSchedule).where(
                GovernedSchedule.tenant_id == tenant_id,
                GovernedSchedule.created_by == created_by,
                GovernedSchedule.idempotency_key == idempotency_key,
            )
        )
    ).scalar_one_or_none()


async def _locked_schedule(
    db: AsyncSession,
    *,
    schedule_id: str,
    tenant_id: str,
    skip_locked: bool = False,
) -> GovernedSchedule | None:
    statement = select(GovernedSchedule).where(
        GovernedSchedule.id == schedule_id,
        GovernedSchedule.tenant_id == tenant_id,
    )
    if skip_locked:
        statement = statement.with_for_update(skip_locked=True)
    else:
        statement = statement.with_for_update()
    return (await db.execute(statement)).scalar_one_or_none()


async def _append_event(
    db: AsyncSession,
    *,
    schedule_id: str,
    event_type: str,
    status: str,
    payload: dict[str, Any],
) -> GovernedScheduleEvent:
    events = list(
        (
            await db.execute(
                select(GovernedScheduleEvent)
                .where(GovernedScheduleEvent.schedule_id == schedule_id)
                .order_by(GovernedScheduleEvent.sequence.desc())
                .limit(1)
            )
        ).scalars()
    )
    previous = events[0] if events else None
    previous_hash = previous.event_hash if previous else None
    sequence = (previous.sequence if previous else 0) + 1
    created_at = datetime.now(UTC)
    event = GovernedScheduleEvent(
        id=str(uuid.uuid4()),
        schedule_id=schedule_id,
        sequence=sequence,
        event_type=event_type,
        status=status,
        payload=payload,
        previous_hash=previous_hash,
        event_hash=_event_hash(
            schedule_id=schedule_id,
            sequence=sequence,
            event_type=event_type,
            status=status,
            payload=payload,
            previous_hash=previous_hash,
            created_at=created_at,
        ),
        created_at=created_at,
    )
    db.add(event)
    return event


def _serialize_schedule(row: GovernedSchedule, events: list[GovernedScheduleEvent]) -> dict[str, Any]:
    return {
        "schedule_id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "created_by": str(row.created_by),
        "service_identity_id": row.service_identity_id,
        "objective": row.objective,
        "constraints": row.constraints or {},
        "execution_mode": row.execution_mode,
        "budget_limits": row.budget_limits,
        "schedule_kind": row.schedule_kind,
        "run_at": row.run_at.isoformat(),
        "status": row.status,
        "idempotency_key": row.idempotency_key,
        "request_hash": row.request_hash,
        "dispatched_run_id": str(row.dispatched_run_id) if row.dispatched_run_id else None,
        "claimed_at": row.claimed_at.isoformat() if row.claimed_at else None,
        "claimed_by": row.claimed_by,
        "dispatched_at": row.dispatched_at.isoformat() if row.dispatched_at else None,
        "cancelled_at": row.cancelled_at.isoformat() if row.cancelled_at else None,
        "cancellation_reason": row.cancellation_reason,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
        "persistence": "postgresql-durable-scheduler",
        "events": [
            {
                "sequence": event.sequence,
                "event_type": event.event_type,
                "status": event.status,
                "payload": event.payload or {},
                "previous_hash": event.previous_hash,
                "event_hash": event.event_hash,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ],
    }

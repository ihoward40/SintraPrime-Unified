"""Canonical durable authority for bounded governed orchestration lifecycle."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.orchestration import (
    ApprovalRequest,
    OrchestrationEvent,
    OrchestrationNode,
    OrchestrationRun,
)
from .orchestration import orchestrator
from .orchestration.budget_policy import BudgetLimits
from .orchestration.persistence import get_run as get_persisted_run
from .orchestration.persistence import save_run
from .orchestration.schemas import ExecutionMode


class DurableOrchestrationStateError(ValueError):
    """Raised when a durable lifecycle transition violates the current state."""


def _event_hash(
    *,
    run_id: str,
    sequence: int,
    event_type: str,
    actor_role: str | None,
    payload: dict[str, Any],
    previous_hash: str | None,
    created_at: datetime,
) -> str:
    canonical = json.dumps(
        {
            "run_id": run_id,
            "sequence": sequence,
            "event_type": event_type,
            "actor_role": actor_role,
            "payload": payload,
            "previous_event_hash": previous_hash,
            "created_at": created_at.isoformat(),
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def start_durable_run(
    db: AsyncSession,
    *,
    objective: str,
    constraints: dict[str, Any] | None,
    execution_mode: ExecutionMode,
    budget_limits: BudgetLimits | None,
    tenant_id: str,
    created_by: str,
) -> dict[str, Any]:
    """Run the bounded deterministic planner/worker, then persist its full projection."""
    run = orchestrator.execute_run(
        objective=objective,
        constraints=constraints,
        execution_mode=execution_mode,
        budget_limits=budget_limits,
        tenant_id=tenant_id,
        created_by=created_by,
    )
    await save_run(db, run)
    await db.flush()
    persisted = await get_persisted_run(db, run["run_id"], tenant_id)
    if persisted is None:
        raise RuntimeError("Durable orchestration projection was not persisted")
    return persisted


async def get_durable_run(
    db: AsyncSession,
    *,
    run_id: str,
    tenant_id: str,
) -> dict[str, Any] | None:
    return await get_persisted_run(db, run_id, tenant_id)


async def approve_durable_run(
    db: AsyncSession,
    *,
    run_id: str,
    tenant_id: str,
    principal_id: str,
    approved: bool,
    reason: str | None,
) -> dict[str, Any] | None:
    row = await _locked_run(db, run_id=run_id, tenant_id=tenant_id)
    if row is None:
        return None
    if row.status != "APPROVAL_REQUIRED":
        raise DurableOrchestrationStateError("No pending Principal approval exists for this run")

    approval_result = await db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.run_id == run_id,
            ApprovalRequest.status == "REQUESTED",
        )
    )
    approvals = list(approval_result.scalars().all())
    if not approvals:
        raise DurableOrchestrationStateError("No pending Principal approval exists for this run")

    now = datetime.now(UTC)
    decision_status = "APPROVED" if approved else "DENIED"
    for approval in approvals:
        approval.status = decision_status
        approval.principal_id = principal_id
        approval.decided_at = now
        approval.decision_reason = reason
        approval.updated_at = now

    row.status = "COMPLETED" if approved else "BLOCKED"
    row.updated_at = now
    if approved:
        row.completed_at = now
    await _append_event(
        db,
        run_id=run_id,
        event_type="APPROVAL_DECIDED",
        actor_role="PRINCIPAL",
        payload={
            "status": decision_status,
            "reason": reason,
            "principal_id": principal_id,
        },
    )
    await db.flush()
    return await get_persisted_run(db, run_id, tenant_id)


async def cancel_durable_run(
    db: AsyncSession,
    *,
    run_id: str,
    tenant_id: str,
    actor_id: str,
    reason: str,
) -> dict[str, Any] | None:
    row = await _locked_run(db, run_id=run_id, tenant_id=tenant_id)
    if row is None:
        return None
    if row.status in {"COMPLETED", "FAILED", "CANCELLED"}:
        raise DurableOrchestrationStateError("Cannot cancel a terminal orchestration run")

    now = datetime.now(UTC)
    row.status = "CANCELLED"
    row.cancellation_reason = reason
    row.completed_at = now
    row.updated_at = now

    node_result = await db.execute(select(OrchestrationNode).where(OrchestrationNode.run_id == run_id))
    for node in node_result.scalars().all():
        if node.status not in {"COMPLETED", "FAILED"}:
            node.status = "CANCELLED"
            node.updated_at = now

    approval_result = await db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.run_id == run_id,
            ApprovalRequest.status == "REQUESTED",
        )
    )
    for approval in approval_result.scalars().all():
        approval.status = "CANCELLED"
        approval.principal_id = actor_id
        approval.decided_at = now
        approval.decision_reason = reason
        approval.updated_at = now

    await _append_event(
        db,
        run_id=run_id,
        event_type="RUN_CANCELLED",
        actor_role="PRINCIPAL",
        payload={"reason": reason, "actor_id": actor_id},
    )
    await db.flush()
    return await get_persisted_run(db, run_id, tenant_id)


async def _locked_run(
    db: AsyncSession,
    *,
    run_id: str,
    tenant_id: str,
) -> OrchestrationRun | None:
    result = await db.execute(
        select(OrchestrationRun)
        .where(OrchestrationRun.id == run_id, OrchestrationRun.tenant_id == tenant_id)
        .with_for_update()
    )
    return result.scalar_one_or_none()


async def _append_event(
    db: AsyncSession,
    *,
    run_id: str,
    event_type: str,
    actor_role: str | None,
    payload: dict[str, Any],
) -> OrchestrationEvent:
    max_sequence = await db.scalar(
        select(func.max(OrchestrationEvent.sequence)).where(OrchestrationEvent.run_id == run_id)
    )
    sequence = int(max_sequence or 0) + 1
    previous_result = await db.execute(
        select(OrchestrationEvent)
        .where(OrchestrationEvent.run_id == run_id)
        .order_by(OrchestrationEvent.sequence.desc())
        .limit(1)
    )
    previous = previous_result.scalar_one_or_none()
    previous_hash = previous.event_hash if previous else None
    created_at = datetime.now(UTC)
    event = OrchestrationEvent(
        id=str(uuid.uuid4()),
        run_id=run_id,
        node_id=None,
        sequence=sequence,
        event_type=event_type,
        actor_role=actor_role,
        payload=payload,
        previous_event_hash=previous_hash,
        event_hash=_event_hash(
            run_id=run_id,
            sequence=sequence,
            event_type=event_type,
            actor_role=actor_role,
            payload=payload,
            previous_hash=previous_hash,
            created_at=created_at,
        ),
        created_at=created_at,
    )
    db.add(event)
    return event

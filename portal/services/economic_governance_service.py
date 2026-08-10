"""Transactional SP-EG-001 Phase 2 persistence service.

This service records and reserves governed economic decisions. It deliberately exposes
no payment-provider, banking, brokerage, borrowing, or trust-asset execution adapter.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from packages.economic_governance.phase2 import canonical_digest

from ..auth.rbac import CurrentUser
from ..models.economic_budget import EconomicMissionBudget
from ..models.economic_governance import EconomicBudgetReservation, EconomicLedgerEvent


class TenantContextRequiredError(ValueError):
    pass


class ReservationConflictError(ValueError):
    pass


class BudgetExceededError(ValueError):
    pass


class ReservationStateError(ValueError):
    pass


def _tenant_id(current_user: CurrentUser) -> str:
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise TenantContextRequiredError("economic governance requires tenant context")
    return str(tenant_id)


async def _bind_tenant(db: AsyncSession, tenant_id: str) -> None:
    """Bind PostgreSQL RLS tenant context; non-PostgreSQL tests rely on service filters."""
    bind = db.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        await db.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
            {"tenant_id": tenant_id},
        )


async def reserve_budget(
    db: AsyncSession,
    *,
    current_user: CurrentUser,
    mission_id: str,
    spend_request_id: str,
    idempotency_key: str,
    request_payload: dict,
    amount: Decimal,
    expires_at: datetime,
) -> EconomicBudgetReservation:
    """Atomically reserve mission budget with idempotent replay semantics."""
    tenant_id = _tenant_id(current_user)
    await _bind_tenant(db, tenant_id)
    request_digest = canonical_digest(request_payload)

    existing_result = await db.execute(
        select(EconomicBudgetReservation).where(
            EconomicBudgetReservation.tenant_id == tenant_id,
            EconomicBudgetReservation.mission_id == mission_id,
            EconomicBudgetReservation.idempotency_key == idempotency_key,
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        if existing.request_digest != request_digest:
            raise ReservationConflictError("idempotency key reused with different payload")
        return existing

    budget_result = await db.execute(
        select(EconomicMissionBudget)
        .where(
            EconomicMissionBudget.tenant_id == tenant_id,
            EconomicMissionBudget.mission_id == mission_id,
        )
        .with_for_update()
    )
    budget = budget_result.scalar_one_or_none()
    if budget is None:
        raise BudgetExceededError("no authorized mission budget exists")

    active_total_result = await db.execute(
        select(func.coalesce(func.sum(EconomicBudgetReservation.amount), 0)).where(
            EconomicBudgetReservation.tenant_id == tenant_id,
            EconomicBudgetReservation.mission_id == mission_id,
            EconomicBudgetReservation.state.in_(("reserved", "committed")),
        )
    )
    active_total = Decimal(str(active_total_result.scalar_one()))
    if active_total + amount > Decimal(str(budget.authorized_amount)):
        raise BudgetExceededError("reservation exceeds remaining mission budget")

    reservation = EconomicBudgetReservation(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        mission_id=mission_id,
        spend_request_id=spend_request_id,
        idempotency_key=idempotency_key,
        request_digest=request_digest,
        amount=amount,
        state="reserved",
        expires_at=expires_at,
    )
    db.add(reservation)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        await _bind_tenant(db, tenant_id)
        replay = await db.execute(
            select(EconomicBudgetReservation).where(
                EconomicBudgetReservation.tenant_id == tenant_id,
                EconomicBudgetReservation.mission_id == mission_id,
                EconomicBudgetReservation.idempotency_key == idempotency_key,
            )
        )
        row = replay.scalar_one_or_none()
        if row is None or row.request_digest != request_digest:
            raise ReservationConflictError("concurrent idempotency collision") from exc
        return row
    return reservation


async def commit_reservation(
    db: AsyncSession,
    *,
    current_user: CurrentUser,
    reservation_id: str,
    now: datetime | None = None,
) -> EconomicBudgetReservation:
    tenant_id = _tenant_id(current_user)
    await _bind_tenant(db, tenant_id)
    now = now or datetime.now(UTC)
    result = await db.execute(
        select(EconomicBudgetReservation)
        .where(
            EconomicBudgetReservation.id == reservation_id,
            EconomicBudgetReservation.tenant_id == tenant_id,
        )
        .with_for_update()
    )
    reservation = result.scalar_one_or_none()
    if reservation is None:
        raise ReservationStateError("reservation not found in tenant")
    if reservation.state != "reserved":
        raise ReservationStateError("only reserved budget may commit")
    if now >= reservation.expires_at:
        reservation.state = "expired"
        await db.flush()
        raise ReservationStateError("expired reservation cannot commit")
    reservation.state = "committed"
    reservation.committed_at = now
    await db.flush()
    return reservation


async def release_reservation(
    db: AsyncSession,
    *,
    current_user: CurrentUser,
    reservation_id: str,
    now: datetime | None = None,
) -> EconomicBudgetReservation:
    tenant_id = _tenant_id(current_user)
    await _bind_tenant(db, tenant_id)
    result = await db.execute(
        select(EconomicBudgetReservation)
        .where(
            EconomicBudgetReservation.id == reservation_id,
            EconomicBudgetReservation.tenant_id == tenant_id,
        )
        .with_for_update()
    )
    reservation = result.scalar_one_or_none()
    if reservation is None or reservation.state != "reserved":
        raise ReservationStateError("only an in-tenant reserved budget may release")
    reservation.state = "released"
    reservation.released_at = now or datetime.now(UTC)
    await db.flush()
    return reservation


async def append_ledger_event(
    db: AsyncSession,
    *,
    current_user: CurrentUser,
    mission_id: str,
    decision_type: str,
    policy_version: str,
    payload: dict,
    evidence_refs: list[str] | None = None,
) -> EconomicLedgerEvent:
    """Append the next immutable hash-chained event for one tenant/mission."""
    tenant_id = _tenant_id(current_user)
    await _bind_tenant(db, tenant_id)
    latest_result = await db.execute(
        select(EconomicLedgerEvent)
        .where(
            EconomicLedgerEvent.tenant_id == tenant_id,
            EconomicLedgerEvent.mission_id == mission_id,
        )
        .order_by(EconomicLedgerEvent.sequence.desc())
        .limit(1)
        .with_for_update()
    )
    previous = latest_result.scalar_one_or_none()
    sequence = 1 if previous is None else previous.sequence + 1
    previous_hash = None if previous is None else previous.event_hash
    material = {
        "tenant_id": tenant_id,
        "mission_id": mission_id,
        "actor_id": str(current_user.user_id),
        "sequence": sequence,
        "decision_type": decision_type,
        "policy_version": policy_version,
        "evidence_refs": evidence_refs or [],
        "payload": payload,
        "previous_hash": previous_hash,
    }
    event = EconomicLedgerEvent(
        id=str(uuid.uuid4()),
        **material,
        event_hash=canonical_digest(material),
    )
    db.add(event)
    await db.flush()
    return event

"""SP-EG-001 Phase 2 integrity controls.

Pure control logic only. No external financial execution adapter exists here.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from .models import SpendCategory

HARD_DENY_CATEGORIES = frozenset(
    {
        SpendCategory.TRANSFER_TO_HUMAN,
        SpendCategory.BORROWING,
        SpendCategory.OPEN_ACCOUNT,
        SpendCategory.SECURITIES,
        SpendCategory.TRUST_ASSET_MOVEMENT,
    }
)


def canonical_digest(payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ApprovalReceipt:
    approval_request_id: str
    tenant_id: str
    mission_id: str
    principal_id: str
    request_digest: str
    policy_version: str
    approved: bool
    issued_at: datetime
    expires_at: datetime
    receipt_hash: str

    @classmethod
    def issue(
        cls,
        *,
        approval_request_id: str,
        tenant_id: str,
        mission_id: str,
        principal_id: str,
        request_digest: str,
        policy_version: str,
        approved: bool,
        issued_at: datetime,
        expires_at: datetime,
    ) -> ApprovalReceipt:
        payload = {
            "approval_request_id": approval_request_id,
            "tenant_id": tenant_id,
            "mission_id": mission_id,
            "principal_id": principal_id,
            "request_digest": request_digest,
            "policy_version": policy_version,
            "approved": approved,
            "issued_at": issued_at.isoformat(),
            "expires_at": expires_at.isoformat(),
        }
        return cls(**payload, receipt_hash=canonical_digest(payload))

    def validates(self, *, tenant_id: str, mission_id: str, request_digest: str, now: datetime) -> bool:
        if not self.approved or now >= self.expires_at:
            return False
        if (tenant_id, mission_id, request_digest) != (
            self.tenant_id,
            self.mission_id,
            self.request_digest,
        ):
            return False
        payload = {
            "approval_request_id": self.approval_request_id,
            "tenant_id": self.tenant_id,
            "mission_id": self.mission_id,
            "principal_id": self.principal_id,
            "request_digest": self.request_digest,
            "policy_version": self.policy_version,
            "approved": self.approved,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }
        return self.receipt_hash == canonical_digest(payload)


class ReservationState(StrEnum):
    RESERVED = "reserved"
    COMMITTED = "committed"
    RELEASED = "released"
    EXPIRED = "expired"


@dataclass(frozen=True)
class BudgetReservation:
    tenant_id: str
    mission_id: str
    idempotency_key: str
    request_digest: str
    amount: Decimal
    expires_at: datetime
    state: ReservationState = ReservationState.RESERVED

    def commit(self, now: datetime) -> BudgetReservation:
        if now >= self.expires_at:
            raise ValueError("expired reservation cannot commit")
        if self.state is not ReservationState.RESERVED:
            raise ValueError("only reserved budget may commit")
        return replace(self, state=ReservationState.COMMITTED)

    def release(self) -> BudgetReservation:
        if self.state is not ReservationState.RESERVED:
            raise ValueError("only reserved budget may release")
        return replace(self, state=ReservationState.RELEASED)


class ReservationBook:
    """Deterministic in-memory reference semantics for DB idempotency tests."""

    def __init__(self, budget: Decimal):
        self.budget = budget
        self._items: dict[tuple[str, str, str], BudgetReservation] = {}

    def reserve(self, reservation: BudgetReservation, now: datetime) -> BudgetReservation:
        key = (reservation.tenant_id, reservation.mission_id, reservation.idempotency_key)
        existing = self._items.get(key)
        if existing:
            if existing.request_digest != reservation.request_digest:
                raise ValueError("idempotency key reused with different payload")
            return existing
        if now >= reservation.expires_at:
            raise ValueError("cannot create an already-expired reservation")
        active = sum(
            (
                item.amount
                for item in self._items.values()
                if item.tenant_id == reservation.tenant_id
                and item.mission_id == reservation.mission_id
                and item.state in {ReservationState.RESERVED, ReservationState.COMMITTED}
            ),
            Decimal("0"),
        )
        if active + reservation.amount > self.budget:
            raise ValueError("reservation exceeds remaining mission budget")
        self._items[key] = reservation
        return reservation


@dataclass(frozen=True)
class LedgerEvent:
    tenant_id: str
    mission_id: str
    actor_id: str
    sequence: int
    decision_type: str
    policy_version: str
    evidence_refs: tuple[str, ...]
    payload: dict
    previous_hash: str | None
    event_hash: str
    created_at: datetime

    @classmethod
    def append(
        cls,
        *,
        tenant_id: str,
        mission_id: str,
        actor_id: str,
        sequence: int,
        decision_type: str,
        policy_version: str,
        evidence_refs: tuple[str, ...],
        payload: dict,
        previous_hash: str | None,
        created_at: datetime | None = None,
    ) -> LedgerEvent:
        created_at = created_at or datetime.now(UTC)
        material = {
            "tenant_id": tenant_id,
            "mission_id": mission_id,
            "actor_id": actor_id,
            "sequence": sequence,
            "decision_type": decision_type,
            "policy_version": policy_version,
            "evidence_refs": evidence_refs,
            "payload": payload,
            "previous_hash": previous_hash,
            "created_at": created_at.isoformat(),
        }
        return cls(**material, event_hash=canonical_digest(material))


def verify_chain(events: list[LedgerEvent]) -> bool:
    previous: str | None = None
    for expected_sequence, event in enumerate(events, start=1):
        if event.sequence != expected_sequence or event.previous_hash != previous:
            return False
        material = {
            "tenant_id": event.tenant_id,
            "mission_id": event.mission_id,
            "actor_id": event.actor_id,
            "sequence": event.sequence,
            "decision_type": event.decision_type,
            "policy_version": event.policy_version,
            "evidence_refs": event.evidence_refs,
            "payload": event.payload,
            "previous_hash": event.previous_hash,
            "created_at": event.created_at.isoformat(),
        }
        if event.event_hash != canonical_digest(material):
            return False
        previous = event.event_hash
    return True


def execution_allowed(category: SpendCategory, receipt: ApprovalReceipt | None) -> bool:
    """Phase 2 never authorizes hard-denied real-money actions, even with a receipt."""
    if category in HARD_DENY_CATEGORIES:
        return False
    return receipt is not None

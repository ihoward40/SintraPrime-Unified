"""SP-EG-001 Phase 2 persistence models.

These models persist economic-governance decisions and reservations only. They do not
execute payments, open accounts, trade securities, borrow funds, or move trust assets.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .types import PortableUUIDString


class EconomicSpendRequest(Base):
    __tablename__ = "economic_spend_requests"

    id: Mapped[str] = mapped_column(PortableUUIDString, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(PortableUUIDString, ForeignKey("tenants.id"), nullable=False)
    mission_id: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_id: Mapped[str] = mapped_column(PortableUUIDString, ForeignKey("users.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "request_digest", name="uq_economic_spend_request_digest"),
        Index("ix_economic_spend_requests_tenant_mission", "tenant_id", "mission_id", "created_at"),
    )


class EconomicSpendEvaluation(Base):
    __tablename__ = "economic_spend_evaluations"

    id: Mapped[str] = mapped_column(PortableUUIDString, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(PortableUUIDString, ForeignKey("tenants.id"), nullable=False)
    spend_request_id: Mapped[str] = mapped_column(
        PortableUUIDString,
        ForeignKey("economic_spend_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    requires_principal_approval: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_economic_spend_evaluations_request", "tenant_id", "spend_request_id"),
    )


class EconomicPrincipalApprovalReceipt(Base):
    __tablename__ = "economic_principal_approval_receipts"

    id: Mapped[str] = mapped_column(PortableUUIDString, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(PortableUUIDString, ForeignKey("tenants.id"), nullable=False)
    approval_request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    principal_id: Mapped[str] = mapped_column(PortableUUIDString, ForeignKey("users.id"), nullable=False)
    mission_id: Mapped[str] = mapped_column(String(128), nullable=False)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[str] = mapped_column(String(16), nullable=False)
    receipt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "approval_request_id", name="uq_economic_approval_request"),
        Index("ix_economic_approval_digest", "tenant_id", "mission_id", "request_digest"),
    )


class EconomicBudgetReservation(Base):
    __tablename__ = "economic_budget_reservations"

    id: Mapped[str] = mapped_column(PortableUUIDString, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(PortableUUIDString, ForeignKey("tenants.id"), nullable=False)
    mission_id: Mapped[str] = mapped_column(String(128), nullable=False)
    spend_request_id: Mapped[str] = mapped_column(
        PortableUUIDString,
        ForeignKey("economic_spend_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    state: Mapped[str] = mapped_column(String(24), nullable=False, default="reserved")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "mission_id",
            "idempotency_key",
            name="uq_economic_budget_reservation_idempotency",
        ),
        Index("ix_economic_budget_reservations_state", "tenant_id", "mission_id", "state"),
    )


class EconomicLedgerEvent(Base):
    __tablename__ = "economic_ledger_events"

    id: Mapped[str] = mapped_column(PortableUUIDString, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(PortableUUIDString, ForeignKey("tenants.id"), nullable=False)
    mission_id: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_id: Mapped[str] = mapped_column(PortableUUIDString, ForeignKey("users.id"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    decision_type: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "mission_id", "sequence", name="uq_economic_ledger_sequence"),
        UniqueConstraint("tenant_id", "event_hash", name="uq_economic_ledger_event_hash"),
        Index("ix_economic_ledger_chain", "tenant_id", "mission_id", "sequence"),
    )

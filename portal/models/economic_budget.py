"""Mission-scoped economic budget authority for SP-EG-001 Phase 2."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .types import PortableUUIDString


class EconomicMissionBudget(Base):
    """Tenant/mission budget row used as the concurrency lock for reservations."""

    __tablename__ = "economic_mission_budgets"

    id: Mapped[str] = mapped_column(PortableUUIDString, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(PortableUUIDString, ForeignKey("tenants.id"), nullable=False)
    mission_id: Mapped[str] = mapped_column(String(128), nullable=False)
    authorized_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "mission_id", name="uq_economic_mission_budget"),
        Index("ix_economic_mission_budget_tenant", "tenant_id", "mission_id"),
    )

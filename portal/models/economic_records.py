"""Persistent SP-EG-001 evidentiary and planning projections."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .types import PortableUUIDString


class EconomicAssetProvenanceRecord(Base):
    __tablename__ = "economic_asset_provenance_records"

    id: Mapped[str] = mapped_column(PortableUUIDString, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(PortableUUIDString, ForeignKey("tenants.id"), nullable=False)
    asset_id: Mapped[str] = mapped_column(String(128), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(80), nullable=False)
    claim_maturity: Mapped[str] = mapped_column(String(40), nullable=False)
    legal_effect: Mapped[str] = mapped_column(String(40), nullable=False)
    public_filing_reference: Mapped[str | None] = mapped_column(String(256), nullable=True)
    provenance_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    evidence: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    missing_elements: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "asset_id", name="uq_economic_asset_provenance_asset"),
        Index("ix_economic_asset_provenance_tenant", "tenant_id", "asset_type"),
    )


class EconomicValueAccrualRecord(Base):
    __tablename__ = "economic_value_accrual_records"

    id: Mapped[str] = mapped_column(PortableUUIDString, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(PortableUUIDString, ForeignKey("tenants.id"), nullable=False)
    asset_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    accrued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_economic_value_accrual_asset", "tenant_id", "asset_id", "accrued_at"),)


class EconomicScenarioRecord(Base):
    __tablename__ = "economic_scenario_records"

    id: Mapped[str] = mapped_column(PortableUUIDString, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(PortableUUIDString, ForeignKey("tenants.id"), nullable=False)
    scenario_id: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    assumptions: Mapped[list] = mapped_column(JSON, nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), nullable=False)
    failure_conditions: Mapped[list] = mapped_column(JSON, nullable=False)
    time_horizon: Mapped[str] = mapped_column(String(128), nullable=False)
    decision_use: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "scenario_id", name="uq_economic_scenario_record"),
        Index("ix_economic_scenario_tenant", "tenant_id", "created_at"),
    )


class EconomicCapitalReserveTarget(Base):
    __tablename__ = "economic_capital_reserve_targets"

    id: Mapped[str] = mapped_column(PortableUUIDString, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(PortableUUIDString, ForeignKey("tenants.id"), nullable=False)
    reserve_policy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    layer: Mapped[int] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    target_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "reserve_policy_id", "layer", name="uq_economic_capital_reserve_layer"
        ),
        Index("ix_economic_capital_reserve_tenant", "tenant_id", "reserve_policy_id"),
    )

"""Authoritative Mission and governed Run identity models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .user import Tenant, User  # noqa: F401 - register FK targets with metadata


class Mission(Base):
    """Tenant-scoped authoritative mission identity."""

    __tablename__ = "missions"

    mission_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    workflow_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    runs: Mapped[list[Run]] = relationship("Run", back_populates="mission", lazy="selectin")

    __table_args__ = (Index("ix_missions_tenant_status", "tenant_id", "status"),)


class Run(Base):
    """Authoritative governed run correlated to one durable engine workflow."""

    __tablename__ = "runs"

    run_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    mission_id: Mapped[str] = mapped_column(String(36), ForeignKey("missions.mission_id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING")
    execution_ref: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    workflow_type: Mapped[str] = mapped_column(String(128), nullable=False)
    input_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    input_data_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    mission: Mapped[Mission] = relationship("Mission", back_populates="runs")

    __table_args__ = (
        Index("ix_runs_tenant_status", "tenant_id", "status"),
        Index("ix_runs_tenant_mission", "tenant_id", "mission_id"),
    )

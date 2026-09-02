"""Run-bound Principal approval artifact model.

Durable record of a constitutional Principal's decision on one specific Run.
This table is the authoritative state for approval; AuditLog is evidence only.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .types import PortableUUID


class RunApproval(Base):
    """Durable run-bound Principal approval artifact.

    One approval per (tenant_id, run_id).  The Principal's explicit decision
    (APPROVED or REJECTED) is recorded here.  The approval is consumed exactly
    once during activation.
    """

    __tablename__ = "mission_control_run_approvals"

    approval_id: Mapped[str] = mapped_column(
        PortableUUID, primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str] = mapped_column(
        PortableUUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    principal_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[str] = mapped_column(
        PortableUUID, ForeignKey("runs.run_id", ondelete="CASCADE"), nullable=False
    )

    # Principal decision: APPROVED or REJECTED
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    # Artifact state: PENDING, CONSUMED, REJECTED
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")

    # Hash of the Run's input_data at approval time — proves immutability
    input_data_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Optional correlation fields
    mission_id: Mapped[uuid.UUID | None] = mapped_column(PortableUUID, nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # execution_ref written after activation consumes this approval
    execution_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "run_id", name="uq_run_approvals_tenant_run"),
        Index("ix_run_approvals_tenant_run", "tenant_id", "run_id"),
    )

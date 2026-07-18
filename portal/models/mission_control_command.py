"""Mission Control governed command ledger models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class MissionControlCommand(Base):
    """Tenant-scoped command request projection."""

    __tablename__ = "mission_control_commands"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    command_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target_id: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    state: Mapped[str] = mapped_column(String(40), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)

    audit_log_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("audit_logs.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    events: Mapped[list[MissionControlCommandEvent]] = relationship(
        "MissionControlCommandEvent",
        back_populates="command",
        lazy="selectin",
        order_by="MissionControlCommandEvent.sequence",
    )
    receipts: Mapped[list[MissionControlCommandReceipt]] = relationship(
        "MissionControlCommandReceipt",
        back_populates="command",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "requested_by",
            "idempotency_key",
            name="uq_mission_control_command_idempotency",
        ),
        Index("ix_mission_control_commands_tenant_state_created", "tenant_id", "state", "created_at"),
        Index("ix_mission_control_commands_target", "tenant_id", "target_type", "target_id"),
    )


class MissionControlCommandEvent(Base):
    """Append-only command lifecycle event with a per-command hash chain."""

    __tablename__ = "mission_control_command_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    command_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("mission_control_commands.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    command: Mapped[MissionControlCommand] = relationship(
        "MissionControlCommand",
        back_populates="events",
    )

    __table_args__ = (
        UniqueConstraint("command_id", "sequence", name="uq_mission_control_command_event_seq"),
        Index("ix_mission_control_command_events_command", "command_id"),
    )


class MissionControlCommandReceipt(Base):
    """Immutable command receipt linking the refusal outcome to audit/evidence."""

    __tablename__ = "mission_control_command_receipts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    command_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("mission_control_commands.id", ondelete="CASCADE"),
        nullable=False,
    )
    receipt_type: Mapped[str] = mapped_column(String(40), nullable=False)
    receipt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    audit_log_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("audit_logs.id"), nullable=True)
    evidence_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    command: Mapped[MissionControlCommand] = relationship(
        "MissionControlCommand",
        back_populates="receipts",
    )

    __table_args__ = (
        UniqueConstraint("command_id", "receipt_type", name="uq_mission_control_command_receipt"),
        Index("ix_mission_control_command_receipts_command", "command_id"),
    )

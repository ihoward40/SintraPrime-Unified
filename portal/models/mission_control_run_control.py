"""Mission Control run-control governance projection models."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

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


class RunControlState(StrEnum):
    RUNNING = "RUNNING"
    PAUSE_REQUESTED = "PAUSE_REQUESTED"
    PAUSING = "PAUSING"
    PAUSED = "PAUSED"
    PAUSE_FAILED = "PAUSE_FAILED"
    PAUSE_TIMED_OUT = "PAUSE_TIMED_OUT"
    SUPERSEDED = "SUPERSEDED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    COMPENSATING = "COMPENSATING"
    COMPENSATED = "COMPENSATED"


class MissionControlRunControl(Base):
    """Governance-only projection for Mission Control run state.

    The durable workflow engine remains the execution authority. This table
    stores operator intent, checkpoints, and evidence for future governed pause
    behavior without mutating the runner.
    """

    __tablename__ = "mission_control_run_controls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    workflow_id: Mapped[str] = mapped_column(String(128), nullable=False)
    command_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("mission_control_commands.id", ondelete="SET NULL"),
        nullable=True,
    )

    state: Mapped[str] = mapped_column(String(40), nullable=False)
    workflow_status_snapshot: Mapped[str] = mapped_column(String(40), nullable=False)
    workflow_status_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    workflow_source: Mapped[str | None] = mapped_column(String(80), nullable=True)
    workflow_version_snapshot: Mapped[int | None] = mapped_column(Integer, nullable=True)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    projection_schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    pause_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmation_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timed_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    incident_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    recovery_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    terminal_reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    events: Mapped[list[MissionControlRunControlEvent]] = relationship(
        "MissionControlRunControlEvent",
        back_populates="run_control",
        lazy="selectin",
        order_by="MissionControlRunControlEvent.sequence",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "workflow_id", name="uq_mission_control_run_controls_tenant_workflow"),
        Index("ix_mission_control_run_controls_tenant_state", "tenant_id", "state"),
        Index("ix_mission_control_run_controls_tenant_workflow", "tenant_id", "workflow_id"),
        Index("ix_mission_control_run_controls_command", "command_id"),
        Index("ix_mission_control_run_controls_state_version", "tenant_id", "state_version"),
    )


class MissionControlRunControlEvent(Base):
    """Append-only run-control transition event with a hash chain."""

    __tablename__ = "mission_control_run_control_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_control_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("mission_control_run_controls.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    previous_state: Mapped[str] = mapped_column(String(40), nullable=False)
    new_state: Mapped[str] = mapped_column(String(40), nullable=False)
    previous_version: Mapped[int] = mapped_column(Integer, nullable=False)
    new_version: Mapped[int] = mapped_column(Integer, nullable=False)
    principal_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    command_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("mission_control_commands.id", ondelete="SET NULL"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    workflow_status_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    previous_event_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    event_schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run_control: Mapped[MissionControlRunControl] = relationship(
        "MissionControlRunControl",
        back_populates="events",
    )

    __table_args__ = (
        UniqueConstraint("run_control_id", "sequence", name="uq_mission_control_run_control_event_seq"),
        Index("ix_mission_control_run_control_events_control", "run_control_id"),
    )

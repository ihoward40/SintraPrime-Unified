"""SP-VOICE-001 Increment Two — governed voice command ledger models.

Mirrors the Mission Control governed command ledger pattern
(``portal/models/mission_control_command.py``): a mutable, tenant-scoped
projection row tracks current lifecycle state, an append-only, hash-chained
event table records every transition, and an immutable receipt closes out
each terminal outcome. Nothing in this module executes any action — it is
pure persistence for outcomes produced by ``voice.governed`` (mock-only
execution).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class VoiceCommand(Base):
    """Tenant-scoped, mutable projection of a single voice command's lifecycle.

    ``command_id`` is the ``vcmd-...`` identifier minted by
    ``voice.governed.command_envelope``; it is unique per tenant so a voice
    command can be looked up, confirmed, or cancelled by callers holding only
    the id and their own tenant/session context.
    """

    __tablename__ = "voice_commands"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    principal_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    command_id: Mapped[str] = mapped_column(String(80), nullable=False)
    voice_session_id: Mapped[str] = mapped_column(String(80), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(80), nullable=False)

    source: Mapped[str] = mapped_column(String(40), nullable=False)
    raw_transcript_hash: Mapped[str] = mapped_column(String(80), nullable=False)
    raw_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)  # only when retention=full
    normalized_intent: Mapped[str] = mapped_column(Text, nullable=False)
    requested_capability: Mapped[str | None] = mapped_column(String(40), nullable=True)
    resolved_capability: Mapped[str] = mapped_column(String(40), nullable=False)
    target_resource: Mapped[str | None] = mapped_column(String(255), nullable=True)

    risk_class: Mapped[str] = mapped_column(String(40), nullable=False)
    policy_decision: Mapped[str] = mapped_column(String(40), nullable=False)
    confirmation_state: Mapped[str] = mapped_column(String(40), nullable=False)
    session_state: Mapped[str] = mapped_column(String(40), nullable=False)
    result: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    provider_capability: Mapped[str | None] = mapped_column(String(40), nullable=True)
    provider_resource_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider_mock: Mapped[bool | None] = mapped_column(nullable=True)
    artifacts: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    audit_log_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("audit_logs.id"), nullable=True)
    # Timestamps are set client-side (never server_default/onupdate). Under the
    # async engine, reading a column back after flush() (not commit()+refresh())
    # to satisfy a column with a *server-side* default/onupdate expression can
    # trigger a synchronous lazy reload outside a greenlet context
    # (``sqlalchemy.exc.MissingGreenlet``). Callers must always set these
    # explicitly (see ``portal/services/voice_command_service.py``).
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    events: Mapped[list[VoiceCommandEvent]] = relationship(
        "VoiceCommandEvent",
        back_populates="command",
        lazy="selectin",
        order_by="VoiceCommandEvent.sequence",
    )
    receipts: Mapped[list[VoiceCommandReceipt]] = relationship(
        "VoiceCommandReceipt",
        back_populates="command",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "command_id", name="uq_voice_command_tenant_command_id"),
        Index("ix_voice_commands_tenant_state_created", "tenant_id", "session_state", "created_at"),
        Index("ix_voice_commands_tenant_session", "tenant_id", "voice_session_id"),
        Index("ix_voice_commands_tenant_principal", "tenant_id", "principal_id"),
    )


class VoiceCommandEvent(Base):
    """Append-only voice command lifecycle event with a per-command hash chain."""

    __tablename__ = "voice_command_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    command_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("voice_commands.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    command: Mapped[VoiceCommand] = relationship("VoiceCommand", back_populates="events")

    __table_args__ = (
        UniqueConstraint("command_id", "sequence", name="uq_voice_command_event_seq"),
        Index("ix_voice_command_events_command", "command_id"),
    )


class VoiceCommandReceipt(Base):
    """Immutable receipt linking a voice command's terminal outcome to audit/evidence."""

    __tablename__ = "voice_command_receipts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    command_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("voice_commands.id", ondelete="CASCADE"),
        nullable=False,
    )
    receipt_type: Mapped[str] = mapped_column(String(40), nullable=False)
    receipt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[str] = mapped_column(String(40), nullable=False)
    audit_log_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("audit_logs.id"), nullable=True)
    evidence_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    command: Mapped[VoiceCommand] = relationship("VoiceCommand", back_populates="receipts")

    __table_args__ = (
        UniqueConstraint("command_id", "receipt_type", name="uq_voice_command_receipt"),
        Index("ix_voice_command_receipts_command", "command_id"),
    )

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class MissionControlOutbox(Base):
    """
    Transactional outbox for reliable dispatch of intents to executors.
    Ensures that intent state changes and dispatch records are committed atomically.
    """

    __tablename__ = "mission_control_outbox"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    command_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("mission_control_commands.id", ondelete="CASCADE"), nullable=True
    )

    # Dispatch metadata
    executor_type: Mapped[str] = mapped_column(
        String(60), nullable=False
    )  # e.g., "nova", "workflow"
    message_type: Mapped[str] = mapped_column(
        String(60), nullable=False
    )  # e.g., "EXECUTE_INTENT", "CANCEL_INTENT"
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Reliability and retry state
    state: Mapped[str] = mapped_column(
        String(40), nullable=False, default="PENDING"
    )  # PENDING, DISPATCHED, FAILED, DEAD_LETTER
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Audit and correlation
    correlation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    causation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_mission_control_outbox_state_next", "state", "next_attempt_at"),
        Index("ix_mission_control_outbox_tenant", "tenant_id"),
        Index("ix_mission_control_outbox_command", "command_id"),
    )

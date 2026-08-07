from datetime import UTC, datetime
from typing import Any, Dict, Optional
from sqlalchemy import JSON, DateTime, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base

class MissionControlOutbox(Base):
    """
    Transactional Outbox for Mission Control intents.
    Ensures durable dispatch of intents and events.
    """
    __tablename__ = "mission_control_outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    intent_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String, default="PENDING", index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

class MemoryEntry(Base):
    """
    OmniBrain Memory Vault (SP-MEMORY-001).
    Stores institutional intelligence, learned lessons, and proven procedures.
    """
    __tablename__ = "memory_vault"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    type: Mapped[str] = mapped_column(String, index=True, nullable=False) # LESSON_LEARNED, PROVEN_PROCEDURE, etc.
    content: Mapped[Any] = mapped_column(JSON, nullable=False)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default={})
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

class EventNodeLinkage(Base):
    """
    Remediation: Dedicated event-to-node linkage for auditing.
    """
    __tablename__ = "event_node_linkage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    node_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    linked_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

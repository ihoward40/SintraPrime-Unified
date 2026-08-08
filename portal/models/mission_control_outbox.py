from datetime import UTC, datetime
from typing import Any, Dict, Optional
from sqlalchemy import JSON, DateTime, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base
from ..models.types import PortableUUIDString

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



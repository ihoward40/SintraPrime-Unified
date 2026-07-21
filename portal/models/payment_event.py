"""Payment event model — authoritative webhook acknowledgment and idempotency record."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class PaymentEvent(Base):
    """Authoritative webhook acknowledgment and idempotency record.

    The payment_events row is the authoritative webhook acknowledgment and
    idempotency record. result_reference stores a deterministic acknowledgment
    identifier. No separate receipt table exists.

    Audit envelopes remain the audit-event authority. This table does not
    replace the audit envelope and introduces no competing evidence hash authority.
    """

    __tablename__ = "payment_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_account_id: Mapped[str] = mapped_column(
        String(255), nullable=False, default="__platform__"
    )
    provider_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    operation: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="reserved")
    correlation_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    result_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    expiry_at: Mapped[datetime | None] = mapped_column(nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (
        Index(
            "uq_provider_event",
            "provider",
            "provider_account_id",
            "provider_event_id",
            unique=True,
        ),
    )
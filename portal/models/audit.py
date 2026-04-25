"""
Immutable, hash-chained audit log.
Every action is recorded and cannot be modified or deleted.
7-year retention for legal compliance.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime, ForeignKey, Index, String, Text, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class AuditLog(Base):
    """
    Append-only audit log.
    - hash_chain: SHA-256(previous_hash + entry_content) — tamper detection
    - No soft-delete column — this table is NEVER modified after insert
    """
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID]            = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    user_id: Mapped[Optional[uuid.UUID]]   = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Who
    actor_email: Mapped[Optional[str]]  = mapped_column(String(255), nullable=True)
    actor_role: Mapped[Optional[str]]   = mapped_column(String(50), nullable=True)
    actor_ip: Mapped[Optional[str]]     = mapped_column(String(45), nullable=True)  # supports IPv6
    actor_user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    session_id: Mapped[Optional[str]]   = mapped_column(String(255), nullable=True)

    # What
    action: Mapped[str]              = mapped_column(String(100), nullable=False)
    # login | logout | login_failed | mfa_enabled | password_changed
    # doc_upload | doc_download | doc_view | doc_share | doc_delete | doc_sign
    # case_create | case_update | case_close | case_delete
    # client_create | client_update | client_delete
    # invoice_create | invoice_send | payment_received
    # message_send | thread_create
    # user_invite | user_deactivate | role_change
    # api_key_create | api_key_revoke
    # settings_update | branding_update

    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[Optional[str]]   = mapped_column(String(255), nullable=True)
    resource_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Outcome
    status: Mapped[str]              = mapped_column(String(10), default="success")  # success | failure | error

    # Details
    details: Mapped[Optional[dict]]  = mapped_column(JSONB, nullable=True)
    changes: Mapped[Optional[dict]]  = mapped_column(JSONB, nullable=True)  # before/after for updates
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Request context
    request_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    http_method: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    http_path: Mapped[Optional[str]]   = mapped_column(Text, nullable=True)

    # Hash chain for tamper detection
    hash_chain: Mapped[Optional[str]]  = mapped_column(String(64), nullable=True)  # SHA-256 hex

    # Timestamp (UTC, server-set — NOT user-settable)
    created_at: Mapped[datetime]     = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_audit_tenant_id", "tenant_id"),
        Index("ix_audit_user_id", "user_id"),
        Index("ix_audit_action", "action"),
        Index("ix_audit_resource", "resource_type", "resource_id"),
        Index("ix_audit_created_at", "created_at"),
        Index("ix_audit_actor_ip", "actor_ip"),
        Index("ix_audit_session", "session_id"),
    )

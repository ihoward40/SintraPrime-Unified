"""
Secure messaging models: MessageThread, Message, MessageAttachment.
End-to-end encrypted in-platform messaging between attorneys and clients.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class MessageThread(Base):
    __tablename__ = "message_threads"

    id: Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    subject: Mapped[str]            = mapped_column(String(500), nullable=False)
    category: Mapped[str]           = mapped_column(String(50), default="general")
    # general | case_discussion | document_review | billing | urgent

    # Context
    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)
    case_id: Mapped[Optional[uuid.UUID]]   = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=True)

    # Participants: list of user_ids
    participants: Mapped[list]       = mapped_column(JSONB, nullable=False, default=list)

    is_archived: Mapped[bool]        = mapped_column(Boolean, default=False)
    is_pinned: Mapped[bool]          = mapped_column(Boolean, default=False)
    is_encrypted: Mapped[bool]       = mapped_column(Boolean, default=True)

    # Retention policy
    retention_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # None = forever
    purge_after: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    message_count: Mapped[int]       = mapped_column(Integer, default=0)

    created_by: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime]     = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime]     = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    messages: Mapped[List["Message"]] = relationship("Message", back_populates="thread", order_by="Message.created_at.asc()", lazy="select")
    creator: Mapped["User"]           = relationship("User", foreign_keys=[created_by])

    __table_args__ = (
        Index("ix_threads_tenant_id", "tenant_id"),
        Index("ix_threads_client_id", "client_id"),
        Index("ix_threads_case_id", "case_id"),
        Index("ix_threads_last_message", "last_message_at"),
        Index("ix_threads_participants", "participants", postgresql_using="gin"),
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("message_threads.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    sender_id: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Content (stored encrypted if thread.is_encrypted)
    content: Mapped[str]            = mapped_column(Text, nullable=False)
    content_encrypted: Mapped[bool] = mapped_column(Boolean, default=True)
    encryption_iv: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Mentions: list of user_ids
    mentions: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)

    # State
    is_edited: Mapped[bool]         = mapped_column(Boolean, default=False)
    edited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_deleted: Mapped[bool]        = mapped_column(Boolean, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Reply to
    reply_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True)

    # Read receipts: {user_id: iso_timestamp}
    read_by: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)

    created_at: Mapped[datetime]    = mapped_column(DateTime(timezone=True), server_default=func.now())

    thread: Mapped["MessageThread"] = relationship("MessageThread", back_populates="messages")
    sender: Mapped["User"]          = relationship("User", foreign_keys=[sender_id])
    attachments: Mapped[List["MessageAttachment"]] = relationship("MessageAttachment", back_populates="message", lazy="selectin")
    reply_to: Mapped[Optional["Message"]] = relationship("Message", remote_side="Message.id", foreign_keys=[reply_to_id])

    __table_args__ = (
        Index("ix_messages_thread_id", "thread_id"),
        Index("ix_messages_sender_id", "sender_id"),
        Index("ix_messages_created_at", "created_at"),
    )


class MessageAttachment(Base):
    """Document attachments within a message (references vault documents)."""
    __tablename__ = "message_attachments"

    id: Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)

    # For external attachments not in vault
    file_name: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    storage_key: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    created_at: Mapped[datetime]    = mapped_column(DateTime(timezone=True), server_default=func.now())

    message: Mapped["Message"]      = relationship("Message", back_populates="attachments")

    __table_args__ = (Index("ix_msg_attachments_message_id", "message_id"),)

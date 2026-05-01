"""Pydantic v2 schemas for Messaging."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    import uuid
    from datetime import datetime


class ThreadCreate(BaseModel):
    subject: str = Field(..., min_length=1, max_length=500)
    category: str = Field("general", pattern=r"^(general|case_discussion|document_review|billing|urgent)$")
    client_id: uuid.UUID | None = None
    case_id: uuid.UUID | None = None
    participant_ids: list[uuid.UUID] = Field(..., min_length=1)
    retention_days: int | None = Field(None, ge=1)


class ThreadResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    subject: str
    category: str
    client_id: uuid.UUID | None = None
    case_id: uuid.UUID | None = None
    participants: list[str]  # user IDs
    is_archived: bool
    is_pinned: bool
    is_encrypted: bool
    message_count: int
    last_message_at: datetime | None = None
    created_by: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class ThreadListResponse(BaseModel):
    items: list[ThreadResponse]
    total: int
    page: int
    page_size: int


class MessageSend(BaseModel):
    content: str = Field(..., min_length=1, max_length=50000)
    mentions: list[uuid.UUID] | None = None
    reply_to_id: uuid.UUID | None = None
    attachment_document_ids: list[uuid.UUID] | None = None


class MessageResponse(BaseModel):
    id: uuid.UUID
    thread_id: uuid.UUID
    sender_id: uuid.UUID
    content: str  # decrypted content
    mentions: list[str] | None = None
    is_edited: bool
    edited_at: datetime | None = None
    is_deleted: bool
    reply_to_id: uuid.UUID | None = None
    read_by: dict | None = None
    attachments: list[dict] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageListResponse(BaseModel):
    items: list[MessageResponse]
    total: int
    page: int
    page_size: int


class ReadReceiptUpdate(BaseModel):
    message_ids: list[uuid.UUID]

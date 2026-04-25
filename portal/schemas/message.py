"""Pydantic v2 schemas for Messaging."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ThreadCreate(BaseModel):
    subject: str = Field(..., min_length=1, max_length=500)
    category: str = Field("general", pattern=r"^(general|case_discussion|document_review|billing|urgent)$")
    client_id: Optional[uuid.UUID] = None
    case_id: Optional[uuid.UUID] = None
    participant_ids: List[uuid.UUID] = Field(..., min_length=1)
    retention_days: Optional[int] = Field(None, ge=1)


class ThreadResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    subject: str
    category: str
    client_id: Optional[uuid.UUID] = None
    case_id: Optional[uuid.UUID] = None
    participants: List[str]  # user IDs
    is_archived: bool
    is_pinned: bool
    is_encrypted: bool
    message_count: int
    last_message_at: Optional[datetime] = None
    created_by: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class ThreadListResponse(BaseModel):
    items: List[ThreadResponse]
    total: int
    page: int
    page_size: int


class MessageSend(BaseModel):
    content: str = Field(..., min_length=1, max_length=50000)
    mentions: Optional[List[uuid.UUID]] = None
    reply_to_id: Optional[uuid.UUID] = None
    attachment_document_ids: Optional[List[uuid.UUID]] = None


class MessageResponse(BaseModel):
    id: uuid.UUID
    thread_id: uuid.UUID
    sender_id: uuid.UUID
    content: str  # decrypted content
    mentions: Optional[List[str]] = None
    is_edited: bool
    edited_at: Optional[datetime] = None
    is_deleted: bool
    reply_to_id: Optional[uuid.UUID] = None
    read_by: Optional[dict] = None
    attachments: List[dict] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageListResponse(BaseModel):
    items: List[MessageResponse]
    total: int
    page: int
    page_size: int


class ReadReceiptUpdate(BaseModel):
    message_ids: List[uuid.UUID]

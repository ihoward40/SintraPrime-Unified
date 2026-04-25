"""Pydantic v2 schemas for Documents, Versions, and Shares."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    id: uuid.UUID
    name: str
    mime_type: str
    file_extension: str
    size_bytes: int
    current_version: int
    storage_key: str
    virus_scan_result: Optional[str] = None
    ocr_completed: bool
    ai_category: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: Optional[str] = None
    mime_type: str
    file_extension: str
    size_bytes: int
    client_id: Optional[uuid.UUID] = None
    case_id: Optional[uuid.UUID] = None
    matter_id: Optional[uuid.UUID] = None
    folder_id: Optional[uuid.UUID] = None
    uploaded_by: uuid.UUID
    current_version: int
    status: str
    is_confidential: bool
    requires_signature: bool
    signed_at: Optional[datetime] = None
    ai_category: Optional[str] = None
    ai_tags: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    watermark_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    folder_id: Optional[uuid.UUID] = None
    is_confidential: Optional[bool] = None
    requires_signature: Optional[bool] = None
    tags: Optional[List[str]] = None
    custom_fields: Optional[dict] = None
    watermark_enabled: Optional[bool] = None
    watermark_text: Optional[str] = None


class DocumentVersionResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    version_number: int
    size_bytes: int
    checksum_sha256: str
    mime_type: str
    change_summary: Optional[str] = None
    uploaded_by: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentShareCreate(BaseModel):
    expires_in_hours: int = Field(24, ge=1, le=2160)  # 1h to 90 days
    password: Optional[str] = None
    max_downloads: Optional[int] = Field(None, ge=1, le=100)
    can_download: bool = True
    can_print: bool = True
    apply_watermark: bool = False
    watermark_text: Optional[str] = None
    shared_with_email: Optional[str] = None


class DocumentShareResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    share_token: str
    share_url: str
    expires_at: Optional[datetime] = None
    can_download: bool
    max_downloads: Optional[int] = None
    download_count: int
    view_count: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    total: int
    page: int
    page_size: int


class DocumentSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    client_id: Optional[uuid.UUID] = None
    case_id: Optional[uuid.UUID] = None
    mime_type: Optional[str] = None
    category: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class FolderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    parent_id: Optional[uuid.UUID] = None
    client_id: Optional[uuid.UUID] = None
    case_id: Optional[uuid.UUID] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class FolderResponse(BaseModel):
    id: uuid.UUID
    name: str
    path: str
    parent_id: Optional[uuid.UUID] = None
    client_id: Optional[uuid.UUID] = None
    case_id: Optional[uuid.UUID] = None
    color: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BulkDocumentRequest(BaseModel):
    document_ids: List[uuid.UUID] = Field(..., min_length=1, max_length=100)
    operation: str = Field(..., pattern=r"^(move|delete|archive|download_zip)$")
    target_folder_id: Optional[uuid.UUID] = None  # for move

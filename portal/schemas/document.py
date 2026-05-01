"""Pydantic v2 schemas for Documents, Versions, and Shares."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    import uuid
    from datetime import datetime


class DocumentUploadResponse(BaseModel):
    id: uuid.UUID
    name: str
    mime_type: str
    file_extension: str
    size_bytes: int
    current_version: int
    storage_key: str
    virus_scan_result: str | None = None
    ocr_completed: bool
    ai_category: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None = None
    mime_type: str
    file_extension: str
    size_bytes: int
    client_id: uuid.UUID | None = None
    case_id: uuid.UUID | None = None
    matter_id: uuid.UUID | None = None
    folder_id: uuid.UUID | None = None
    uploaded_by: uuid.UUID
    current_version: int
    status: str
    is_confidential: bool
    requires_signature: bool
    signed_at: datetime | None = None
    ai_category: str | None = None
    ai_tags: list[str] | None = None
    tags: list[str] | None = None
    watermark_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    folder_id: uuid.UUID | None = None
    is_confidential: bool | None = None
    requires_signature: bool | None = None
    tags: list[str] | None = None
    custom_fields: dict | None = None
    watermark_enabled: bool | None = None
    watermark_text: str | None = None


class DocumentVersionResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    version_number: int
    size_bytes: int
    checksum_sha256: str
    mime_type: str
    change_summary: str | None = None
    uploaded_by: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentShareCreate(BaseModel):
    expires_in_hours: int = Field(24, ge=1, le=2160)  # 1h to 90 days
    password: str | None = None
    max_downloads: int | None = Field(None, ge=1, le=100)
    can_download: bool = True
    can_print: bool = True
    apply_watermark: bool = False
    watermark_text: str | None = None
    shared_with_email: str | None = None


class DocumentShareResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    share_token: str
    share_url: str
    expires_at: datetime | None = None
    can_download: bool
    max_downloads: int | None = None
    download_count: int
    view_count: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int


class DocumentSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    client_id: uuid.UUID | None = None
    case_id: uuid.UUID | None = None
    mime_type: str | None = None
    category: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class FolderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    parent_id: uuid.UUID | None = None
    client_id: uuid.UUID | None = None
    case_id: uuid.UUID | None = None
    color: str | None = None
    icon: str | None = None


class FolderResponse(BaseModel):
    id: uuid.UUID
    name: str
    path: str
    parent_id: uuid.UUID | None = None
    client_id: uuid.UUID | None = None
    case_id: uuid.UUID | None = None
    color: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BulkDocumentRequest(BaseModel):
    document_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=100)
    operation: str = Field(..., pattern=r"^(move|delete|archive|download_zip)$")
    target_folder_id: uuid.UUID | None = None  # for move

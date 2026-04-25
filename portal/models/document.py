"""
Document vault models: Document, DocumentVersion, DocumentShare, DocumentFolder.
Supports versioning, encryption, sharing with access controls, and OCR.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func, Numeric
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class DocumentFolder(Base):
    """Hierarchical folder structure for organizing documents."""
    __tablename__ = "document_folders"

    id: Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("document_folders.id", ondelete="SET NULL"), nullable=True)

    name: Mapped[str]               = mapped_column(String(255), nullable=False)
    path: Mapped[str]               = mapped_column(Text, nullable=False)  # materialized path: /root/parent/folder

    # Context: can belong to a client, case, or be global
    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)
    case_id: Mapped[Optional[uuid.UUID]]   = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=True)

    created_by: Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    color: Mapped[Optional[str]]    = mapped_column(String(7), nullable=True)  # hex color
    icon: Mapped[Optional[str]]     = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime]           = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime]           = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    children: Mapped[List["DocumentFolder"]] = relationship("DocumentFolder", lazy="select")
    documents: Mapped[List["Document"]]      = relationship("Document", back_populates="folder", lazy="select")

    __table_args__ = (
        Index("ix_doc_folders_tenant", "tenant_id"),
        Index("ix_doc_folders_parent", "parent_id"),
        Index("ix_doc_folders_path", "path", postgresql_using="btree"),
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Ownership context
    client_id: Mapped[Optional[uuid.UUID]]  = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)
    case_id: Mapped[Optional[uuid.UUID]]    = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=True)
    matter_id: Mapped[Optional[uuid.UUID]]  = mapped_column(UUID(as_uuid=True), ForeignKey("matters.id"), nullable=True)
    folder_id: Mapped[Optional[uuid.UUID]]  = mapped_column(UUID(as_uuid=True), ForeignKey("document_folders.id"), nullable=True)
    uploaded_by: Mapped[uuid.UUID]          = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # File metadata
    name: Mapped[str]               = mapped_column(String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str]          = mapped_column(String(255), nullable=False)
    file_extension: Mapped[str]     = mapped_column(String(20), nullable=False)
    size_bytes: Mapped[int]         = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str]    = mapped_column(String(64), nullable=False)

    # Storage
    storage_key: Mapped[str]        = mapped_column(String(1024), nullable=False, unique=True)
    storage_bucket: Mapped[str]     = mapped_column(String(255), nullable=False)
    is_encrypted: Mapped[bool]      = mapped_column(Boolean, default=True)
    encryption_iv: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Virus scan
    virus_scanned: Mapped[bool]     = mapped_column(Boolean, default=False)
    virus_scan_result: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # clean | infected | failed
    virus_scanned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # OCR / AI processing
    ocr_completed: Mapped[bool]     = mapped_column(Boolean, default=False)
    ocr_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ai_tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)

    # Document state
    status: Mapped[str]             = mapped_column(String(20), default="active")  # active | archived | deleted
    is_template: Mapped[bool]       = mapped_column(Boolean, default=False)
    is_confidential: Mapped[bool]   = mapped_column(Boolean, default=False)
    requires_signature: Mapped[bool] = mapped_column(Boolean, default=False)

    # Digital signature
    signed_at: Mapped[Optional[datetime]]       = mapped_column(DateTime(timezone=True), nullable=True)
    signed_by: Mapped[Optional[uuid.UUID]]      = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    signature_data: Mapped[Optional[dict]]      = mapped_column(JSONB, nullable=True)

    # Full-text search
    search_vector: Mapped[Optional[str]]        = mapped_column(TSVECTOR, nullable=True)

    # Version tracking
    current_version: Mapped[int]    = mapped_column(Integer, default=1)

    # Custom metadata
    custom_fields: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)
    tags: Mapped[Optional[list]]    = mapped_column(JSONB, nullable=True, default=list)

    # Watermark
    watermark_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    watermark_text: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Timestamps
    created_at: Mapped[datetime]           = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime]           = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    versions: Mapped[List["DocumentVersion"]] = relationship("DocumentVersion", back_populates="document", order_by="DocumentVersion.version_number.desc()", lazy="select")
    shares: Mapped[List["DocumentShare"]]     = relationship("DocumentShare", back_populates="document", lazy="select")
    folder: Mapped[Optional["DocumentFolder"]] = relationship("DocumentFolder", back_populates="documents")
    uploader: Mapped["User"]                  = relationship("User", foreign_keys=[uploaded_by])

    __table_args__ = (
        Index("ix_documents_tenant_id", "tenant_id"),
        Index("ix_documents_client_id", "client_id"),
        Index("ix_documents_case_id", "case_id"),
        Index("ix_documents_uploaded_by", "uploaded_by"),
        Index("ix_documents_status", "status"),
        Index("ix_documents_search", "search_vector", postgresql_using="gin"),
        Index("ix_documents_deleted", "deleted_at"),
    )


class DocumentVersion(Base):
    """Immutable version history for documents."""
    __tablename__ = "document_versions"

    id: Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int]     = mapped_column(Integer, nullable=False)

    # File details for this version
    storage_key: Mapped[str]        = mapped_column(String(1024), nullable=False)
    size_bytes: Mapped[int]         = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str]    = mapped_column(String(64), nullable=False)
    mime_type: Mapped[str]          = mapped_column(String(255), nullable=False)

    change_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    is_encrypted: Mapped[bool]      = mapped_column(Boolean, default=True)
    encryption_iv: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    created_at: Mapped[datetime]    = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped["Document"]    = relationship("Document", back_populates="versions")
    uploader: Mapped["User"]        = relationship("User", foreign_keys=[uploaded_by])

    __table_args__ = (
        Index("ix_doc_versions_document_id", "document_id"),
    )


class DocumentShare(Base):
    """Secure share links for documents (internal or external)."""
    __tablename__ = "document_shares"

    id: Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    share_token: Mapped[str]        = mapped_column(String(64), unique=True, nullable=False, index=True)
    created_by: Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Share target (optional — if None, it's a public link)
    shared_with_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    shared_with_email: Mapped[Optional[str]]         = mapped_column(String(255), nullable=True)

    # Access controls
    can_download: Mapped[bool]      = mapped_column(Boolean, default=True)
    can_print: Mapped[bool]         = mapped_column(Boolean, default=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    max_downloads: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    download_count: Mapped[int]     = mapped_column(Integer, default=0)
    view_count: Mapped[int]         = mapped_column(Integer, default=0)
    is_active: Mapped[bool]         = mapped_column(Boolean, default=True)

    # Expiry
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Watermark override
    apply_watermark: Mapped[bool]   = mapped_column(Boolean, default=False)
    watermark_text: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Timestamps
    created_at: Mapped[datetime]           = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[Optional[datetime]]       = mapped_column(DateTime(timezone=True), nullable=True)

    # Access log (stored as JSONB list)
    access_log: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)

    document: Mapped["Document"]    = relationship("Document", back_populates="shares")
    creator: Mapped["User"]         = relationship("User", foreign_keys=[created_by])

    __table_args__ = (
        Index("ix_doc_shares_document_id", "document_id"),
        Index("ix_doc_shares_token", "share_token"),
        Index("ix_doc_shares_expires", "expires_at"),
    )

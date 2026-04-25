"""Secure document share link creation and validation."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.document import Document, DocumentShare
from ..schemas.document import DocumentShareCreate


async def create_share_link(
    db: AsyncSession,
    doc: Document,
    body: DocumentShareCreate,
    current_user,
) -> DocumentShare:
    """Create a new secure share link for a document."""
    token = secrets.token_urlsafe(32)

    # Hash password if set
    password_hash = None
    if body.password:
        password_hash = hashlib.sha256(body.password.encode()).hexdigest()

    share = DocumentShare(
        document_id=doc.id,
        tenant_id=doc.tenant_id,
        created_by=current_user.user_id,
        share_token=token,
        expires_at=body.expires_at,
        password_hash=password_hash,
        max_downloads=body.max_downloads,
        max_views=body.max_views,
        can_download=body.can_download,
        can_view_only=body.can_view_only,
        is_watermarked=body.is_watermarked,
        shared_with_emails=body.shared_with_emails or [],
        notes=body.notes,
    )
    db.add(share)
    await db.commit()
    await db.refresh(share)
    return share


async def validate_share_access(share: DocumentShare, password: str | None) -> None:
    """Validate that a share link is still valid and accessible."""
    now = datetime.now(timezone.utc)

    if share.expires_at and share.expires_at < now:
        raise HTTPException(status_code=410, detail="This share link has expired")

    if share.is_revoked:
        raise HTTPException(status_code=410, detail="This share link has been revoked")

    if share.max_views and share.view_count >= share.max_views:
        raise HTTPException(status_code=410, detail="View limit reached for this link")

    if share.max_downloads and share.download_count >= share.max_downloads:
        raise HTTPException(status_code=410, detail="Download limit reached for this link")

    if share.password_hash:
        if not password:
            raise HTTPException(status_code=401, detail="Password required")
        if hashlib.sha256(password.encode()).hexdigest() != share.password_hash:
            raise HTTPException(status_code=401, detail="Incorrect password")

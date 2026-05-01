"""Notification center router."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..auth.rbac import CurrentUser, get_current_user
from ..database import Base, get_db

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


# ── Notification model (inline for simplicity) ────────────────────────────────

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    event_type: Mapped[str]         = mapped_column(String(50), nullable=False)
    title: Mapped[str]              = mapped_column(String(500), nullable=False)
    body: Mapped[str | None]     = mapped_column(Text, nullable=True)
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[str | None]   = mapped_column(String(255), nullable=True)
    actor_id: Mapped[str | None]      = mapped_column(String(255), nullable=True)
    metadata: Mapped[dict | None]     = mapped_column(JSONB, nullable=True)

    is_read: Mapped[bool]           = mapped_column(Boolean, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    email_sent: Mapped[bool]        = mapped_column(Boolean, default=False)
    push_sent: Mapped[bool]         = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime]    = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_notifications_user_id", "user_id"),
        Index("ix_notifications_is_read", "is_read"),
        Index("ix_notifications_created_at", "created_at"),
    )


# ── Schemas ───────────────────────────────────────────────────────────────────

class NotificationResponse(BaseModel):
    id: uuid.UUID
    event_type: str
    title: str
    body: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    unread_count: int
    page: int
    page_size: int


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    is_read: bool | None = Query(None),
    event_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Notification).where(
        Notification.user_id == current_user.user_id,
        Notification.tenant_id == current_user.tenant_id,
    )
    if is_read is not None:
        stmt = stmt.where(Notification.is_read == is_read)
    if event_type:
        stmt = stmt.where(Notification.event_type == event_type)

    total_q = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_q.scalar() or 0

    unread_q = await db.execute(
        select(func.count()).select_from(
            select(Notification).where(
                Notification.user_id == current_user.user_id,
                not Notification.is_read,
            ).subquery()
        )
    )
    unread_count = unread_q.scalar() or 0

    stmt = stmt.offset((page-1)*page_size).limit(page_size).order_by(Notification.created_at.desc())
    result = await db.execute(stmt)
    notifs = result.scalars().all()

    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in notifs],
        total=total,
        unread_count=unread_count,
        page=page,
        page_size=page_size,
    )


@router.put("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.user_id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404)
    notif.is_read = True
    notif.read_at = datetime.now(timezone.utc)
    await db.commit()


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import update
    now = datetime.now(timezone.utc)
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.user_id, not Notification.is_read)
        .values(is_read=True, read_at=now)
    )
    await db.commit()


@router.get("/unread-count")
async def get_unread_count(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.user_id,
            not Notification.is_read,
        )
    )
    return {"unread_count": result.scalar() or 0}

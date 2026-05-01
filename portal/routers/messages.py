"""Secure messaging router — threads, messages, read receipts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from ..auth.rbac import CurrentUser, Permission, require_permissions
from ..database import get_db
from ..models.message import Message, MessageAttachment, MessageThread
from ..schemas.message import (
    MessageListResponse,
    MessageResponse,
    MessageSend,
    ReadReceiptUpdate,
    ThreadCreate,
    ThreadListResponse,
    ThreadResponse,
)
from ..services.audit_service import audit
from ..services.encryption_service import decrypt_text, encrypt_text
from ..services.notification_service import notify_users
from ..websocket.connection_manager import ws_manager

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/threads", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED)
async def create_thread(
    body: ThreadCreate,
    current_user: CurrentUser = Depends(require_permissions(Permission.MSG_CREATE_THREAD)),
    db: AsyncSession = Depends(get_db),
):
    participants = list(set([str(current_user.user_id)] + [str(p) for p in body.participant_ids]))
    thread = MessageThread(
        tenant_id=current_user.tenant_id,
        subject=body.subject,
        category=body.category,
        client_id=body.client_id,
        case_id=body.case_id,
        participants=participants,
        retention_days=body.retention_days,
        created_by=current_user.user_id,
        is_encrypted=True,
    )
    db.add(thread)
    await db.commit()
    await db.refresh(thread)
    await audit(db, action="thread_create", user_id=current_user.user_id,
                tenant_id=current_user.tenant_id,
                resource_type="thread", resource_id=str(thread.id), resource_name=thread.subject)
    return ThreadResponse.model_validate(thread)


@router.get("/threads", response_model=ThreadListResponse)
async def list_threads(
    category: str | None = Query(None),
    client_id: uuid.UUID | None = Query(None),
    case_id: uuid.UUID | None = Query(None),
    is_archived: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(require_permissions(Permission.MSG_READ)),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(MessageThread).where(
        MessageThread.tenant_id == current_user.tenant_id,
        MessageThread.deleted_at.is_(None),
        MessageThread.is_archived == is_archived,
        MessageThread.participants.contains([str(current_user.user_id)]),
    )
    if category:
        stmt = stmt.where(MessageThread.category == category)
    if client_id:
        stmt = stmt.where(MessageThread.client_id == client_id)
    if case_id:
        stmt = stmt.where(MessageThread.case_id == case_id)

    total_q = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_q.scalar() or 0

    stmt = stmt.offset((page - 1) * page_size).limit(page_size).order_by(
        MessageThread.last_message_at.desc().nullslast()
    )
    result = await db.execute(stmt)
    threads = result.scalars().all()

    return ThreadListResponse(
        items=[ThreadResponse.model_validate(t) for t in threads],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/threads/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permissions(Permission.MSG_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MessageThread).where(
            MessageThread.id == thread_id,
            MessageThread.tenant_id == current_user.tenant_id,
        )
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404)
    if str(current_user.user_id) not in (thread.participants or []):
        raise HTTPException(status_code=403, detail="Not a thread participant")
    return ThreadResponse.model_validate(thread)


@router.post("/threads/{thread_id}/send", response_model=MessageResponse, status_code=201)
async def send_message(
    thread_id: uuid.UUID,
    body: MessageSend,
    current_user: CurrentUser = Depends(require_permissions(Permission.MSG_SEND)),
    db: AsyncSession = Depends(get_db),
):
    # Verify thread membership
    result = await db.execute(
        select(MessageThread).where(
            MessageThread.id == thread_id,
            MessageThread.tenant_id == current_user.tenant_id,
            MessageThread.deleted_at.is_(None),
        )
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404)
    if str(current_user.user_id) not in (thread.participants or []):
        raise HTTPException(status_code=403, detail="Not a participant")

    # Encrypt content
    encrypted_content, iv = encrypt_text(body.content)

    msg = Message(
        thread_id=thread_id,
        tenant_id=current_user.tenant_id,
        sender_id=current_user.user_id,
        content=encrypted_content,
        content_encrypted=True,
        encryption_iv=iv.hex(),
        mentions=[str(m) for m in (body.mentions or [])],
        reply_to_id=body.reply_to_id,
        read_by={str(current_user.user_id): datetime.now(timezone.utc).isoformat()},
    )
    db.add(msg)

    # Update thread
    thread.last_message_at = datetime.now(timezone.utc)
    thread.message_count += 1

    await db.flush()

    # Handle attachments
    if body.attachment_document_ids:
        for doc_id in body.attachment_document_ids:
            attachment = MessageAttachment(
                message_id=msg.id,
                document_id=doc_id,
            )
            db.add(attachment)

    await db.commit()
    await db.refresh(msg)

    # Decrypt for response
    response_content = body.content

    # Push via WebSocket to all participants
    event = {
        "type": "new_message",
        "thread_id": str(thread_id),
        "message_id": str(msg.id),
        "sender_id": str(current_user.user_id),
        "preview": body.content[:100],
    }
    for participant_id in (thread.participants or []):
        if participant_id != str(current_user.user_id):
            await ws_manager.send_to_user(participant_id, event)

    # Notify via email/push
    await notify_users(
        db=db,
        tenant_id=current_user.tenant_id,
        event_type="new_message",
        resource_id=str(thread_id),
        resource_name=thread.subject,
        actor_id=current_user.user_id,
        recipient_ids=[p for p in (thread.participants or []) if p != str(current_user.user_id)],
    )

    await audit(db, action="message_send", user_id=current_user.user_id,
                tenant_id=current_user.tenant_id,
                resource_type="message", resource_id=str(msg.id))

    # Build response with decrypted content
    resp_data = MessageResponse.model_validate(msg)
    resp_data.content = response_content
    return resp_data


@router.get("/threads/{thread_id}/messages", response_model=MessageListResponse)
async def list_messages(
    thread_id: uuid.UUID,
    before_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(require_permissions(Permission.MSG_READ)),
    db: AsyncSession = Depends(get_db),
):
    # Verify membership
    thread_result = await db.execute(
        select(MessageThread).where(MessageThread.id == thread_id)
    )
    thread = thread_result.scalar_one_or_none()
    if not thread or str(current_user.user_id) not in (thread.participants or []):
        raise HTTPException(status_code=403)

    stmt = select(Message).where(
        Message.thread_id == thread_id,
        not Message.is_deleted,
    )
    if before_id:
        # Cursor-based pagination
        before_result = await db.execute(select(Message.created_at).where(Message.id == before_id))
        before_ts = before_result.scalar_one_or_none()
        if before_ts:
            stmt = stmt.where(Message.created_at < before_ts)

    total_q = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_q.scalar() or 0

    stmt = stmt.order_by(Message.created_at.desc()).offset((page-1)*page_size).limit(page_size)
    result = await db.execute(stmt)
    messages = result.scalars().all()

    # Decrypt all messages
    items = []
    for msg in messages:
        resp = MessageResponse.model_validate(msg)
        if msg.content_encrypted and msg.encryption_iv:
            try:
                iv = bytes.fromhex(msg.encryption_iv)
                resp.content = decrypt_text(msg.content, iv)
            except Exception:
                resp.content = "[Decryption failed]"
        items.append(resp)

    return MessageListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/threads/{thread_id}/read-receipts", status_code=status.HTTP_204_NO_CONTENT)
async def mark_as_read(
    thread_id: uuid.UUID,
    body: ReadReceiptUpdate,
    current_user: CurrentUser = Depends(require_permissions(Permission.MSG_READ)),
    db: AsyncSession = Depends(get_db),
):
    now_iso = datetime.now(timezone.utc).isoformat()
    for msg_id in body.message_ids:
        result = await db.execute(
            select(Message).where(Message.id == msg_id, Message.thread_id == thread_id)
        )
        msg = result.scalar_one_or_none()
        if msg and msg.read_by is not None:
            msg.read_by[str(current_user.user_id)] = now_iso
    await db.commit()

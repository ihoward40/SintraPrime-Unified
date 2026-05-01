"""
Real-time WebSocket message routing.
Handles incoming client messages and routes them appropriately.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

import structlog

from .connection_manager import ws_manager

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger()


class MessageHandler:
    """Processes incoming WebSocket messages and dispatches to handlers."""

    SUPPORTED_EVENTS = {
        "ping",
        "subscribe_thread",
        "unsubscribe_thread",
        "typing_start",
        "typing_stop",
    }

    async def handle(
        self,
        event: dict[str, Any],
        user_id: str,
        tenant_id: str,
        db: AsyncSession,
    ) -> None:
        event_type = event.get("type")
        if not event_type:
            log.warning("ws.invalid_event", user_id=user_id, event=event)
            return

        handler = getattr(self, f"_handle_{event_type}", None)
        if not handler:
            log.debug("ws.unknown_event", event_type=event_type)
            return

        await handler(event, user_id, tenant_id, db)

    async def _handle_ping(self, event: dict, user_id: str, tenant_id: str, db: AsyncSession) -> None:
        await ws_manager.send_to_user(user_id, {"type": "pong"})

    async def _handle_typing_start(self, event: dict, user_id: str, tenant_id: str, db: AsyncSession) -> None:
        thread_id = event.get("thread_id")
        if not thread_id:
            return
        # Broadcast typing indicator to thread participants
        from sqlalchemy import select

        from ..models.message import MessageThread
        result = await db.execute(select(MessageThread).where(MessageThread.id == uuid.UUID(thread_id)))
        thread = result.scalar_one_or_none()
        if not thread:
            return
        for participant_id in (thread.participants or []):
            if participant_id != user_id:
                await ws_manager.send_to_user(participant_id, {
                    "type": "typing",
                    "thread_id": thread_id,
                    "user_id": user_id,
                    "is_typing": True,
                })

    async def _handle_typing_stop(self, event: dict, user_id: str, tenant_id: str, db: AsyncSession) -> None:
        thread_id = event.get("thread_id")
        if not thread_id:
            return
        from sqlalchemy import select

        from ..models.message import MessageThread
        result = await db.execute(select(MessageThread).where(MessageThread.id == uuid.UUID(thread_id)))
        thread = result.scalar_one_or_none()
        if not thread:
            return
        for participant_id in (thread.participants or []):
            if participant_id != user_id:
                await ws_manager.send_to_user(participant_id, {
                    "type": "typing",
                    "thread_id": thread_id,
                    "user_id": user_id,
                    "is_typing": False,
                })


# Singleton
message_handler = MessageHandler()

"""
Real-time WebSocket message routing.
Handles incoming client messages and routes them appropriately.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict

import structlog
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from .connection_manager import ws_manager

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
        event: Dict[str, Any],
        user_id: str,
        tenant_id: str,
        db: AsyncSession,
    ) -> None:
        event_type = event.get("type")
        if not event_type:
            log.warning("ws.invalid_event", user_id=user_id, event_data=event)
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
        from ..models.message import MessageThread
        from sqlalchemy import select
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
        from ..models.message import MessageThread
        from sqlalchemy import select
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

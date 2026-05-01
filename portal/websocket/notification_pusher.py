"""Push notifications to connected WebSocket clients."""

from __future__ import annotations

from .connection_manager import ws_manager


async def push_notification(
    user_id: str,
    event_type: str,
    title: str,
    body: str | None = None,
    resource_id: str | None = None,
    resource_type: str | None = None,
    metadata: dict | None = None,
) -> None:
    """Push a real-time notification to a user's WebSocket connections."""
    event = {
        "type": "notification",
        "event_type": event_type,
        "title": title,
        "body": body,
        "resource_id": resource_id,
        "resource_type": resource_type,
        "metadata": metadata or {},
    }
    await ws_manager.send_to_user(user_id, event)


async def push_to_users(
    user_ids: list[str],
    event_type: str,
    title: str,
    body: str | None = None,
    resource_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    """Push a notification to multiple users."""
    event = {
        "type": "notification",
        "event_type": event_type,
        "title": title,
        "body": body,
        "resource_id": resource_id,
        "metadata": metadata or {},
    }
    for uid in user_ids:
        await ws_manager.send_to_user(uid, event)


async def push_case_update(tenant_id: str, case_id: str, update: dict) -> None:
    """Broadcast a case update to all connected users in the tenant."""
    await ws_manager.broadcast_to_tenant(tenant_id, {
        "type": "case_update",
        "case_id": case_id,
        **update,
    })


async def push_document_event(user_id: str, document_id: str, event_type: str) -> None:
    await ws_manager.send_to_user(user_id, {
        "type": "document_event",
        "event_type": event_type,
        "document_id": document_id,
    })

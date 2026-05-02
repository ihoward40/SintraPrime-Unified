"""
WebSocket connection pool manager.
Maintains authenticated WebSocket connections per user and tenant.
Supports fan-out to all connections for a user.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict

import structlog
from fastapi import WebSocket

log = structlog.get_logger()


class ConnectionManager:
    """Thread-safe WebSocket connection registry."""

    def __init__(self) -> None:
        # user_id → set of WebSocket connections
        self._user_connections: dict[str, set[WebSocket]] = defaultdict(set)
        # tenant_id → set of user_ids
        self._tenant_users: dict[str, set[str]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        tenant_id: str,
    ) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self._user_connections[user_id].add(websocket)
            self._tenant_users[tenant_id].add(user_id)
        log.info("ws.connected", user_id=user_id, tenant_id=tenant_id)

    async def disconnect(
        self,
        websocket: WebSocket,
        user_id: str,
        tenant_id: str,
    ) -> None:
        """Remove a WebSocket from the registry."""
        async with self._lock:
            self._user_connections[user_id].discard(websocket)
            if not self._user_connections[user_id]:
                del self._user_connections[user_id]
                self._tenant_users[tenant_id].discard(user_id)
        log.info("ws.disconnected", user_id=user_id)

    async def send_to_user(self, user_id: str, event: dict) -> None:
        """Send an event to all connections for a specific user."""
        connections = set(self._user_connections.get(user_id, set()))
        if not connections:
            return

        dead = []
        for ws in connections:
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    self._user_connections[user_id].discard(ws)

    async def broadcast_to_tenant(self, tenant_id: str, event: dict) -> None:
        """Broadcast an event to all connected users in a tenant."""
        user_ids = set(self._tenant_users.get(tenant_id, set()))
        for user_id in user_ids:
            await self.send_to_user(user_id, event)

    async def broadcast_to_users(self, user_ids: list[str], event: dict) -> None:
        """Send an event to a list of specific users."""
        tasks = [self.send_to_user(uid, event) for uid in user_ids]
        await asyncio.gather(*tasks, return_exceptions=True)

    @property
    def connection_count(self) -> int:
        return sum(len(conns) for conns in self._user_connections.values())

    def get_online_users(self, tenant_id: str) -> list[str]:
        return list(self._tenant_users.get(tenant_id, set()))


# Singleton
ws_manager = ConnectionManager()

"""WebSocket transport hardening: capacity, rate, timeout, and abuse controls.

All controls are process-local (single-process architecture).
Multi-process or distributed deployments require a shared backend.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

import structlog
from fastapi import WebSocket

log = structlog.get_logger()


@dataclass
class WSHardeningSettings:
    """Configuration for WebSocket transport hardening."""

    global_connection_limit: int = 100
    per_actor_connection_limit: int = 10
    per_tenant_connection_limit: int = 50
    per_address_connection_limit: int = 20
    min_send_interval_seconds: float = 1.0
    payload_max_bytes: int = 65536
    idle_timeout_seconds: float = 300.0
    max_connection_lifetime_seconds: float = 3600.0
    auth_failure_window_seconds: float = 60.0
    auth_failure_limit: int = 5
    query_token_enabled: bool = True
    query_token_deprecated: bool = True


@dataclass
class ConnectionMetadata:
    """Immutable metadata for a registered WebSocket connection."""

    websocket_id: int
    user_id: str
    tenant_id: str
    client_address: str
    connected_at: float = field(default_factory=time.monotonic)
    last_send_at: float = field(default_factory=time.monotonic)


class WSCapacityController:
    """Process-local capacity accounting for WebSocket connections.

    Tracks concurrent connections by:
    - global count
    - per-actor count
    - per-tenant count
    - per-client-address count

    All limits are process-local. Not cluster-wide.
    """

    def __init__(self, settings: WSHardeningSettings) -> None:
        self._settings = settings
        self._lock = asyncio.Lock()
        self._global_count: int = 0
        self._actor_counts: dict[str, int] = {}
        self._tenant_counts: dict[str, int] = {}
        self._address_counts: dict[str, int] = {}
        self._connections: dict[int, ConnectionMetadata] = {}

    async def try_register(
        self,
        websocket: WebSocket,
        user_id: str,
        tenant_id: str,
        client_address: str,
    ) -> tuple[bool, str | None]:
        """Attempt to register a new connection.

        Returns (success, denial_reason).
        If denied, no counters are modified.
        """
        async with self._lock:
            ws_id = id(websocket)
            if ws_id in self._connections:
                return False, "duplicate_registration"

            # Check limits
            if self._global_count >= self._settings.global_connection_limit:
                return False, "global_limit"

            actor_count = self._actor_counts.get(user_id, 0)
            if actor_count >= self._settings.per_actor_connection_limit:
                return False, "per_actor_limit"

            tenant_count = self._tenant_counts.get(tenant_id, 0)
            if tenant_count >= self._settings.per_tenant_connection_limit:
                return False, "per_tenant_limit"

            addr_count = self._address_counts.get(client_address, 0)
            if addr_count >= self._settings.per_address_connection_limit:
                return False, "per_address_limit"

            # Register
            metadata = ConnectionMetadata(
                websocket_id=ws_id,
                user_id=user_id,
                tenant_id=tenant_id,
                client_address=client_address,
            )
            self._connections[ws_id] = metadata
            self._global_count += 1
            self._actor_counts[user_id] = actor_count + 1
            self._tenant_counts[tenant_id] = tenant_count + 1
            self._address_counts[client_address] = addr_count + 1

            return True, None

    async def unregister(self, websocket: WebSocket) -> None:
        """Unregister a connection. Idempotent — safe to call multiple times."""
        async with self._lock:
            ws_id = id(websocket)
            metadata = self._connections.pop(ws_id, None)
            if metadata is None:
                return  # Already unregistered (idempotent)

            self._global_count = max(0, self._global_count - 1)

            actor_count = self._actor_counts.get(metadata.user_id, 0)
            if actor_count <= 1:
                self._actor_counts.pop(metadata.user_id, None)
            else:
                self._actor_counts[metadata.user_id] = actor_count - 1

            tenant_count = self._tenant_counts.get(metadata.tenant_id, 0)
            if tenant_count <= 1:
                self._tenant_counts.pop(metadata.tenant_id, None)
            else:
                self._tenant_counts[metadata.tenant_id] = tenant_count - 1

            addr_count = self._address_counts.get(metadata.client_address, 0)
            if addr_count <= 1:
                self._address_counts.pop(metadata.client_address, None)
            else:
                self._address_counts[metadata.client_address] = addr_count - 1

    @property
    def global_count(self) -> int:
        return self._global_count

    def get_actor_count(self, user_id: str) -> int:
        return self._actor_counts.get(user_id, 0)

    def get_tenant_count(self, tenant_id: str) -> int:
        return self._tenant_counts.get(tenant_id, 0)

    def get_address_count(self, client_address: str) -> int:
        return self._address_counts.get(client_address, 0)


class AuthFailureThrottle:
    """Process-local sliding-window throttle for WebSocket authentication failures."""

    def __init__(self, window_seconds: float, limit: int) -> None:
        self._window_seconds = window_seconds
        self._limit = limit
        self._failures: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    async def record_failure(self, key: str, now: float | None = None) -> None:
        """Record an authentication failure for the given key."""
        async with self._lock:
            current = now if now is not None else time.monotonic()
            if key not in self._failures:
                self._failures[key] = []
            self._failures[key].append(current)
            # Prune old entries
            cutoff = current - self._window_seconds
            self._failures[key] = [t for t in self._failures[key] if t > cutoff]
            if not self._failures[key]:
                self._failures.pop(key, None)

    async def is_throttled(self, key: str, now: float | None = None) -> bool:
        """Check if the key is currently throttled."""
        async with self._lock:
            current = now if now is not None else time.monotonic()
            cutoff = current - self._window_seconds
            failures = self._failures.get(key, [])
            recent = [t for t in failures if t > cutoff]
            return len(recent) >= self._limit

    async def cleanup_expired(self, now: float | None = None) -> None:
        """Remove expired entries to bound memory."""
        async with self._lock:
            current = now if now is not None else time.monotonic()
            cutoff = current - self._window_seconds
            for key in list(self._failures.keys()):
                self._failures[key] = [t for t in self._failures[key] if t > cutoff]
                if not self._failures[key]:
                    self._failures.pop(key, None)

    @property
    def tracked_keys(self) -> int:
        return len(self._failures)


def get_effective_client_address(
    websocket: WebSocket,
    trusted_proxy_addresses: set[str] | None = None,
) -> str:
    """Derive the effective client address.

    Default: use socket peer address, ignore X-Forwarded-For unless
    the direct peer is a configured trusted proxy.
    """
    client = websocket.client
    if client is None:
        return "unknown"

    peer_address = client.host or "unknown"

    if trusted_proxy_addresses is None:
        return peer_address

    if peer_address not in trusted_proxy_addresses:
        return peer_address

    # Peer is a trusted proxy — check X-Forwarded-For
    forwarded = websocket.headers.get("x-forwarded-for", "")
    if forwarded:
        # Take the first (leftmost) address
        first = forwarded.split(",")[0].strip()
        if first:
            return first

    return peer_address


# Singleton instances (process-local)
_ws_capacity_controller: WSCapacityController | None = None
_auth_failure_throttle: AuthFailureThrottle | None = None


def get_ws_capacity_controller(settings: WSHardeningSettings | None = None) -> WSCapacityController:
    global _ws_capacity_controller
    if _ws_capacity_controller is None or settings is not None:
        s = settings or WSHardeningSettings()
        _ws_capacity_controller = WSCapacityController(s)
    return _ws_capacity_controller


def get_auth_failure_throttle(settings: WSHardeningSettings | None = None) -> AuthFailureThrottle:
    global _auth_failure_throttle
    if _auth_failure_throttle is None or settings is not None:
        s = settings or WSHardeningSettings()
        _auth_failure_throttle = AuthFailureThrottle(
            window_seconds=s.auth_failure_window_seconds,
            limit=s.auth_failure_limit,
        )
    return _auth_failure_throttle

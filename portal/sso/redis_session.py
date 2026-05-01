"""
Phase 21F: Redis Session Store
Asynchronous session persistence using Redis with automatic expiry.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class RedisSessionStore:
    """
    Asynchronous Redis-backed session store.
    Stores sessions with automatic TTL expiry.
    Falls back gracefully when Redis is unavailable.
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0", prefix: str = "sso:session:"):
        self.redis_url = redis_url
        self.prefix = prefix
        self._client = None
        self._connected = False

    async def connect(self) -> bool:
        """Connect to Redis. Returns True if successful."""
        try:
            import redis.asyncio as aioredis
            self._client = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            await self._client.ping()
            self._connected = True
            logger.info("Redis session store connected: %s", self.redis_url)
            return True
        except Exception as e:
            logger.warning("Redis connection failed (falling back to in-memory): %s", e)
            self._connected = False
            return False

    async def disconnect(self):
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            self._connected = False

    def _key(self, session_id: str) -> str:
        """Generate Redis key for session."""
        return f"{self.prefix}{session_id}"

    async def store(self, session_id: str, data: dict, ttl_seconds: int = 3600) -> bool:
        """Store session data with TTL."""
        if not self._connected or not self._client:
            return False
        try:
            serialized = json.dumps(data, default=str)
            await self._client.setex(self._key(session_id), ttl_seconds, serialized)
            logger.debug("Session stored: %s (TTL: %ds)", session_id[:8], ttl_seconds)
            return True
        except Exception as e:
            logger.error("Failed to store session %s: %s", session_id[:8], e)
            return False

    async def retrieve(self, session_id: str) -> Optional[dict]:
        """Retrieve session data. Returns None if not found or expired."""
        if not self._connected or not self._client:
            return None
        try:
            raw = await self._client.get(self._key(session_id))
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.error("Failed to retrieve session %s: %s", session_id[:8], e)
            return None

    async def delete(self, session_id: str) -> bool:
        """Delete a session."""
        if not self._connected or not self._client:
            return False
        try:
            result = await self._client.delete(self._key(session_id))
            return result > 0
        except Exception as e:
            logger.error("Failed to delete session %s: %s", session_id[:8], e)
            return False

    async def exists(self, session_id: str) -> bool:
        """Check if session exists."""
        if not self._connected or not self._client:
            return False
        try:
            return await self._client.exists(self._key(session_id)) > 0
        except Exception:
            return False

    async def refresh_ttl(self, session_id: str, ttl_seconds: int = 3600) -> bool:
        """Refresh TTL on existing session."""
        if not self._connected or not self._client:
            return False
        try:
            return await self._client.expire(self._key(session_id), ttl_seconds)
        except Exception as e:
            logger.error("Failed to refresh TTL for %s: %s", session_id[:8], e)
            return False

    async def get_active_count(self) -> int:
        """Get count of active sessions."""
        if not self._connected or not self._client:
            return 0
        try:
            cursor = 0
            count = 0
            while True:
                cursor, keys = await self._client.scan(cursor, match=f"{self.prefix}*", count=100)
                count += len(keys)
                if cursor == 0:
                    break
            return count
        except Exception:
            return 0

    @property
    def is_connected(self) -> bool:
        return self._connected

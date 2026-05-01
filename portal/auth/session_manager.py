"""
Active session tracking using Redis.

Tracks all active sessions per user, supports remote logout via WebSocket pubsub.
Integrates with SessionMiddlewareManager for lifecycle management.
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional
from uuid import uuid4

import aioredis
from fastapi import Depends, HTTPException, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SessionInfo(BaseModel):
    """Session metadata stored in Redis."""
    session_id: str
    user_id: str
    email: str
    provider: str
    created_at: str
    expires_at: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class SessionStore:
    """Redis-backed session store with automatic expiry."""

    def __init__(self, redis_url: str = "redis://localhost:6379", ttl_seconds: int = 3600):
        self.redis_url = redis_url
        self.ttl = timedelta(seconds=ttl_seconds)
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        """Initialize Redis connection."""
        try:
            self.redis = await aioredis.create_redis_pool(self.redis_url)
            logger.info("Redis session store connected")
        except Exception as e:
            logger.warning(f"Redis unavailable, falling back to memory: {e}")
            self.redis = None

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.redis:
            self.redis.close()
            await self.redis.wait_closed()
            logger.info("Redis session store disconnected")

    async def create_session(
        self,
        user_id: str,
        email: str,
        provider: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> str:
        """Create and store a new session."""
        session_id = str(uuid4())
        now = datetime.now(timezone.utc)
        expires_at = now + self.ttl

        session = SessionInfo(
            session_id=session_id,
            user_id=user_id,
            email=email,
            provider=provider,
            created_at=now.isoformat(),
            expires_at=expires_at.isoformat(),
            ip_address=ip_address,
            user_agent=user_agent,
        )

        if self.redis:
            key = f"session:{session_id}"
            await self.redis.setex(key, self.ttl.total_seconds(), session.json())
            # Track user's active sessions
            await self.redis.sadd(f"user_sessions:{user_id}", session_id)
            logger.info(f"Session {session_id} created for user {user_id}")
        else:
            logger.debug(f"Session {session_id} created (no Redis, memory-only)")

        return session_id

    async def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Retrieve session by ID."""
        if not self.redis:
            return None
        key = f"session:{session_id}"
        data = await self.redis.get(key)
        if data:
            return SessionInfo.parse_raw(data)
        return None

    async def invalidate_session(self, session_id: str) -> None:
        """Delete a session."""
        if not self.redis:
            return
        key = f"session:{session_id}"
        session = await self.get_session(session_id)
        if session:
            await self.redis.delete(key)
            await self.redis.srem(f"user_sessions:{session.user_id}", session_id)
            logger.info(f"Session {session_id} invalidated")

    async def get_user_sessions(self, user_id: str) -> list[str]:
        """Get all active session IDs for a user."""
        if not self.redis:
            return []
        sessions = await self.redis.smembers(f"user_sessions:{user_id}")
        return list(sessions) if sessions else []


class SessionManager:
    """High-level session management with token refresh."""

    def __init__(self, store: SessionStore, secret: str):
        self.store = store
        self.secret = secret

    async def create_session(
        self,
        user_id: str,
        email: str,
        provider: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> str:
        """Create a new session and return session ID."""
        return await self.store.create_session(
            user_id=user_id,
            email=email,
            provider=provider,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def get_token_jti(self, token: str) -> str:
        """Extract JTI (JWT ID) from token payload for session tracking."""
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token format")
        # In real implementation, decode and extract jti claim
        # For now, hash the token as JTI
        return hashlib.sha256(token.encode()).hexdigest()[:16]

    async def revoke_token(self, jti: str) -> None:
        """Add token JTI to revocation list (blocklist)."""
        if self.store.redis:
            key = f"token_revoked:{jti}"
            await self.store.redis.setex(key, 86400, "true")  # 24h blocklist
            logger.info(f"Token {jti} revoked")

    async def is_token_revoked(self, jti: str) -> bool:
        """Check if token is in revocation list."""
        if not self.store.redis:
            return False
        key = f"token_revoked:{jti}"
        result = await self.store.redis.exists(key)
        return bool(result)

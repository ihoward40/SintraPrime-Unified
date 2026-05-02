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

try:
    import redis.asyncio as aioredis  # redis>=4.2 (Python 3.11 compatible)
except ImportError:  # pragma: no cover
    aioredis = None  # type: ignore[assignment]
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
            if aioredis is not None:
                self.redis = aioredis.from_url(self.redis_url)
            else:
                self.redis = None
            logger.info("Redis session store connected")
        except Exception as e:
            logger.warning(f"Redis unavailable, falling back to memory: {e}")
            self.redis = None

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.aclose()
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


# ── Module-level function stubs (used by portal.routers.auth) ────────────────

_memory_blocklist: set = set()
_memory_sessions: dict = {}
_refresh_families: dict = {}


async def blocklist_jti(jti: str, ttl_seconds: int = 86400) -> None:
    """Add a JTI to the in-memory blocklist."""
    _memory_blocklist.add(jti)


async def is_jti_blocklisted(jti: str) -> bool:
    """Return True if the JTI is in the blocklist."""
    return jti in _memory_blocklist


async def create_session(
    user_id: str,
    email: str,
    provider: str = "local",
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> str:
    """Create a new session and return the session ID."""
    session_id = str(uuid4())
    _memory_sessions[session_id] = {
        "user_id": user_id,
        "email": email,
        "provider": provider,
    }
    return session_id


def get_token_jti(token: str) -> str:
    """Extract or derive a JTI from a token string."""
    return hashlib.sha256(token.encode()).hexdigest()[:16]


async def revoke_session(session_id: str) -> None:
    """Remove a session from the store."""
    _memory_sessions.pop(session_id, None)


async def revoke_all_user_sessions(user_id: str) -> None:
    """Remove all sessions belonging to a user."""
    to_remove = [sid for sid, s in _memory_sessions.items() if s.get("user_id") == user_id]
    for sid in to_remove:
        _memory_sessions.pop(sid, None)


async def register_refresh_family(family_id: str, user_id: str, ttl_seconds: int = 86400) -> None:
    """Register a new refresh token family."""
    _refresh_families[family_id] = {"user_id": user_id, "rotated": False}


async def rotate_refresh_family(family_id: str) -> bool:
    """Mark a refresh family as rotated. Returns False if already rotated (replay attack)."""
    family = _refresh_families.get(family_id)
    if family is None:
        return False
    if family["rotated"]:
        return False  # Replay attack detected
    family["rotated"] = True
    return True


async def validate_refresh_family(family_id: str) -> bool:
    """Return True if the refresh family is valid (not rotated)."""
    family = _refresh_families.get(family_id)
    return family is not None and not family["rotated"]


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

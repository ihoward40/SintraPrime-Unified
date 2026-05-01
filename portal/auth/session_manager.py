"""
Active session tracking using Redis.
Tracks all active sessions per user, supports remote logout (revocation).
Also maintains a JWT blocklist (blacklisted JTIs).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import redis.asyncio as aioredis
import structlog

from ..config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

# Redis key prefixes
SESSION_PREFIX   = "session:"       # session:{session_id} → session data
USER_SESSIONS    = "user_sessions:"  # user_sessions:{user_id} → set of session IDs
JTI_BLOCKLIST    = "jti_block:"     # jti_block:{jti} → "1" (blocklisted)
REFRESH_FAMILY   = "refresh_fam:"   # refresh_fam:{family_id} → last jti

_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = await aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
    return _redis_client


# ── Session management ────────────────────────────────────────────────────────

async def create_session(
    user_id: str,
    tenant_id: str,
    role: str,
    device_info: str = "",
    ip_address: str = "",
    refresh_token_jti: str = "",
    access_token_jti: str = "",
) -> str:
    """Create and store a new session. Returns session_id."""
    redis = await get_redis()
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    session_data = {
        "session_id": session_id,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "device_info": device_info,
        "ip_address": ip_address,
        "refresh_token_jti": refresh_token_jti,
        "access_token_jti": access_token_jti,
        "created_at": now,
        "last_active": now,
        "is_active": "true",
    }

    ttl = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400

    async with redis.pipeline() as pipe:
        pipe.setex(
            f"{SESSION_PREFIX}{session_id}",
            ttl,
            json.dumps(session_data),
        )
        pipe.sadd(f"{USER_SESSIONS}{user_id}", session_id)
        pipe.expire(f"{USER_SESSIONS}{user_id}", ttl)
        await pipe.execute()

    logger.info("session.created", session_id=session_id, user_id=user_id)
    return session_id


async def get_session(session_id: str) -> dict | None:
    """Retrieve session data. Returns None if not found or expired."""
    redis = await get_redis()
    raw = await redis.get(f"{SESSION_PREFIX}{session_id}")
    if not raw:
        return None
    return json.loads(raw)


async def update_session_activity(session_id: str) -> None:
    """Update last_active timestamp on a session."""
    redis = await get_redis()
    raw = await redis.get(f"{SESSION_PREFIX}{session_id}")
    if raw:
        data = json.loads(raw)
        data["last_active"] = datetime.now(timezone.utc).isoformat()
        ttl = await redis.ttl(f"{SESSION_PREFIX}{session_id}")
        await redis.setex(f"{SESSION_PREFIX}{session_id}", max(ttl, 1), json.dumps(data))


async def revoke_session(session_id: str) -> None:
    """Revoke a single session."""
    redis = await get_redis()
    raw = await redis.get(f"{SESSION_PREFIX}{session_id}")
    if raw:
        data = json.loads(raw)
        user_id = data.get("user_id")
        access_jti = data.get("access_token_jti")
        refresh_jti = data.get("refresh_token_jti")

        # Blocklist tokens
        if access_jti:
            await blocklist_jti(access_jti, ttl=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        if refresh_jti:
            await blocklist_jti(refresh_jti, ttl=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400)

        # Remove session
        async with redis.pipeline() as pipe:
            pipe.delete(f"{SESSION_PREFIX}{session_id}")
            if user_id:
                pipe.srem(f"{USER_SESSIONS}{user_id}", session_id)
            await pipe.execute()

    logger.info("session.revoked", session_id=session_id)


async def revoke_all_user_sessions(user_id: str) -> int:
    """Revoke all sessions for a user (force logout everywhere). Returns count."""
    redis = await get_redis()
    session_ids = await redis.smembers(f"{USER_SESSIONS}{user_id}")
    count = 0
    for sid in session_ids:
        await revoke_session(sid)
        count += 1
    await redis.delete(f"{USER_SESSIONS}{user_id}")
    logger.info("session.revoked_all", user_id=user_id, count=count)
    return count


async def get_user_sessions(user_id: str) -> list[dict]:
    """List all active sessions for a user."""
    redis = await get_redis()
    session_ids = await redis.smembers(f"{USER_SESSIONS}{user_id}")
    sessions = []
    for sid in session_ids:
        data = await get_session(sid)
        if data:
            sessions.append(data)
    return sessions


# ── JWT blocklist ─────────────────────────────────────────────────────────────

async def blocklist_jti(jti: str, ttl: int = 3600) -> None:
    """Add a JWT ID to the blocklist. TTL = token's remaining lifetime."""
    redis = await get_redis()
    await redis.setex(f"{JTI_BLOCKLIST}{jti}", ttl, "1")


async def is_jti_blocklisted(jti: str) -> bool:
    """Check if a JTI is in the blocklist."""
    redis = await get_redis()
    return await redis.exists(f"{JTI_BLOCKLIST}{jti}") == 1


# ── Refresh token family rotation ─────────────────────────────────────────────

async def register_refresh_family(family_id: str, jti: str) -> None:
    """Register the current JTI for a refresh token family."""
    redis = await get_redis()
    ttl = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400
    await redis.setex(f"{REFRESH_FAMILY}{family_id}", ttl, jti)


async def validate_refresh_family(family_id: str, jti: str) -> bool:
    """
    Validate that this JTI is the latest for this family.
    If not, it means the refresh token was reused → revoke entire family.
    """
    redis = await get_redis()
    stored_jti = await redis.get(f"{REFRESH_FAMILY}{family_id}")
    if stored_jti is None:
        return False  # Family doesn't exist / expired
    if stored_jti != jti:
        # REUSE DETECTED — invalidate family
        await redis.delete(f"{REFRESH_FAMILY}{family_id}")
        logger.warning("security.refresh_token_reuse_detected", family=family_id)
        return False
    return True


async def rotate_refresh_family(family_id: str, new_jti: str) -> None:
    """Update the stored JTI for a family after successful rotation."""
    redis = await get_redis()
    ttl = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400
    await redis.setex(f"{REFRESH_FAMILY}{family_id}", ttl, new_jti)


def get_token_jti(payload: dict) -> str | None:
    """Extract the JTI (JWT ID) claim from a decoded token payload."""
    return payload.get("jti")

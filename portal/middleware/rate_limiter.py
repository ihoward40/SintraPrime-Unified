"""
Per-user rate limiting middleware using sliding window algorithm.
Backed by Redis for distributed deployments.
- Default: 100 req/min per authenticated user
- Auth endpoints: 10 req/min per IP
"""

from __future__ import annotations

import time

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import get_settings

log = structlog.get_logger()
settings = get_settings()

AUTH_PATHS = ["/auth/login", "/auth/refresh", "/auth/mfa"]
AUTH_LIMIT = 10   # per minute per IP
DEFAULT_LIMIT = 100  # per minute per user

# In-memory fallback (non-distributed)
_rate_store: dict = {}


def _get_redis():
    try:
        import redis
        client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
        )
        client.ping()
        return client
    except Exception:
        return None


_redis = None


def _get_redis_client():
    global _redis
    if _redis is None:
        _redis = _get_redis()
    return _redis


def _sliding_window_check(
    key: str,
    limit: int,
    window_seconds: int = 60,
    use_redis: bool = True,
) -> tuple[bool, int, int]:
    """
    Check rate limit using sliding window.

    Returns:
        (allowed, remaining, reset_in_seconds)
    """
    r = _get_redis_client() if use_redis else None
    now = int(time.time())
    window_start = now - window_seconds

    if r:
        try:
            pipe = r.pipeline()
            pipe.zremrangebyscore(key, "-inf", window_start)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, window_seconds + 1)
            results = pipe.execute()
            request_count = results[2]

            allowed = request_count <= limit
            remaining = max(0, limit - request_count)
            return allowed, remaining, window_seconds
        except Exception as exc:
            log.error("rate_limiter.redis_error", error=str(exc))
            # Fall through to in-memory

    # In-memory fallback (not distributed-safe)
    bucket = _rate_store.setdefault(key, [])
    # Prune old timestamps
    bucket[:] = [ts for ts in bucket if ts > window_start]
    bucket.append(now)

    count = len(bucket)
    allowed = count <= limit
    remaining = max(0, limit - count)
    return allowed, remaining, window_seconds


class RateLimiterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Determine limit and key
        is_auth = any(path.startswith(p) for p in AUTH_PATHS)
        if is_auth:
            limit = AUTH_LIMIT
            identifier = request.client.host if request.client else "unknown"
            key = f"rl:auth:{identifier}"
        else:
            user_id = getattr(request.state, "user_id", None)
            if not user_id:
                return await call_next(request)
            limit = DEFAULT_LIMIT
            key = f"rl:user:{user_id}"

        allowed, remaining, reset_in = _sliding_window_check(key, limit)

        if not allowed:
            log.warning("rate_limit.exceeded", key=key, limit=limit)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_in),
                    "Retry-After": str(reset_in),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_in)
        return response

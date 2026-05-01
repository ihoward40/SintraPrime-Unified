"""Core middleware stack (DTZ011 compliant)."""
from datetime import datetime, timezone
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from portal.config import get_settings


settings = get_settings()


class TimestampMiddleware(BaseHTTPMiddleware):
    """Adds UTC-aware request/response timestamps (DTZ011)."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_time_utc = datetime.now(timezone.utc)
        request.state.request_time = request_time_utc
        response = await call_next(request)
        response_time_utc = datetime.now(timezone.utc)
        response.headers["X-Request-Time"] = request_time_utc.isoformat()
        response.headers["X-Response-Time"] = response_time_utc.isoformat()
        return response


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Simple rate limiter with UTC-aware tracking (DTZ011)."""

    def __init__(self, app, requests_per_minute: int = 100):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_history = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        now_utc = datetime.now(timezone.utc)

        if client_ip not in self.request_history:
            self.request_history[client_ip] = [(
         cutoff = datetime.fromtimestamp(now_utc.timestamp() - 60, tz=timezone.utc)
        self.request_history[client_ip] = [
            req_time for req_time in self.request_history[client_ip]
            if req_time > cutoff
        ]

        if len(self.request_history[client_ip]) >= self.requests_per_minute:
            return Response(content="Rate limit exceeded", status_code=429)

        self.request_history[client_ip].append(now_utc)
        return await call_next(request)


def setup_middleware(app):
    """Initialize all middleware in correct order."""
    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TimestampMiddleware)
    app.add_middleware(RateLimiterMiddleware, requests_per_minute=100)

"""JWT authentication middleware — validates tokens on every request."""

from __future__ import annotations

import time

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..auth.jwt_handler import decode_access_token
from ..config import get_settings

log = structlog.get_logger()
settings = get_settings()

# Paths that don't require authentication
PUBLIC_PATHS = {
    "/",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/auth/login",
    "/auth/refresh",
    "/auth/mfa/verify",
    "/documents/share/",  # shared link access
}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Allow public paths
        if any(path.startswith(p) for p in PUBLIC_PATHS):
            return await call_next(request)

        # WebSocket: auth handled in endpoint
        if request.scope.get("type") == "websocket":
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header"},
            )

        token = auth_header[7:]
        try:
            payload = decode_access_token(token)
            request.state.user_id = payload.get("sub")
            request.state.tenant_id = payload.get("tenant_id")
            request.state.role = payload.get("role")
        except Exception as exc:
            log.warning("auth.invalid_token", path=path, error=str(exc))
            return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})

        response = await call_next(request)
        return response

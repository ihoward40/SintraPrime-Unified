"""
Audit middleware — logs every authenticated HTTP request.
Captures: user, method, path, status, IP, user-agent, duration.
"""

from __future__ import annotations

import time
from typing import Callable

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

log = structlog.get_logger()

# Don't audit these noisy paths
SKIP_AUDIT_PATHS = {"/health", "/metrics", "/docs", "/openapi.json", "/redoc"}


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        start = time.monotonic()
        path = request.url.path

        # Let the request through
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 1)

        if path in SKIP_AUDIT_PATHS:
            return response

        user_id = getattr(request.state, "user_id", None)
        tenant_id = getattr(request.state, "tenant_id", None)
        role = getattr(request.state, "role", None)

        log.info(
            "http.request",
            method=request.method,
            path=path,
            status=response.status_code,
            user_id=user_id,
            tenant_id=str(tenant_id) if tenant_id else None,
            role=role,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            duration_ms=duration_ms,
        )

        return response

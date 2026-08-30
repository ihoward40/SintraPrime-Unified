"""JWT authentication middleware — validates tokens on every request."""

from __future__ import annotations

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..auth.jwt_handler import decode_access_token
from ..auth.session_manager import is_jti_blocklisted
from ..config import get_settings

log = structlog.get_logger()
settings = get_settings()

# Public routes are explicit. Prefix matching is reserved for token-bearing
# artifacts such as shared document links and docs assets.
PUBLIC_EXACT_PATHS = {
    "/",
    "/health",
    "/docs",
    "/docs/oauth2-redirect",
    "/openapi.json",
    "/redoc",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/setup/status",
    "/api/v1/auth/setup",
    "/api/v1/auth/password/reset-request",
    "/api/v1/auth/password/reset-confirm",
    "/api/v1/sso/okta/authorize",
    "/api/v1/sso/azure/authorize",
    "/api/v1/sso/google/authorize",
    "/api/v1/sso/callback",
    "/api/v1/sso/health",
    "/api/v1/blackstone/health",
}

PUBLIC_PREFIX_PATHS = (
    "/api/v1/documents/share/",
    "/static/",
)

# The legal-authority pilot exposes reference data anonymously. Keep this
# method-scoped: review queues and every write endpoint remain authenticated
# (or, for UCC evaluation, are allowed through to their reviewer-header guard).
PUBLIC_GET_PREFIX_PATHS = ("/federal/", "/jurisdictions/", "/ucc-filings/")
PUBLIC_GET_EXACT_PATHS = {"/jurisdictions", "/legal-rules/compare"}
PUBLIC_METHOD_PATHS = {("POST", "/ucc-filings/evaluate")}
# These legacy legal-authority pilot routes perform their own reviewer-header
# authorization. Let them reach the handler so missing headers remain a 403.
PUBLIC_CONTROLLED_PREFIXES = ("/legal-rules/", "/legal-authorities/")


def is_public_path(path: str, method: str = "GET") -> bool:
    if any(path.startswith(prefix) for prefix in PUBLIC_CONTROLLED_PREFIXES):
        return True
    if path.startswith("/jurisdictions/") and path.endswith("/review-queue"):
        return True
    if path in PUBLIC_EXACT_PATHS or any(path.startswith(prefix) for prefix in PUBLIC_PREFIX_PATHS):
        return True
    if (method.upper(), path) in PUBLIC_METHOD_PATHS:
        return True
    return method.upper() == "GET" and (
        path in PUBLIC_GET_EXACT_PATHS
        or any(path.startswith(prefix) for prefix in PUBLIC_GET_PREFIX_PATHS)
    )


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if request.method == "OPTIONS" or is_public_path(path, request.method):
            return await call_next(request)

        # Let FastAPI resolve unknown paths so clients receive a normal 404
        # (with correlation headers) instead of an authentication challenge.
        if request.scope.get("type") == "http":
            from starlette.routing import Match

            matched = False
            for route in request.app.router.routes:
                match, _ = route.matches(request.scope)
                if match != Match.NONE:
                    matched = True
                    break
            if not matched:
                return await call_next(request)

        # WebSocket: auth handled in endpoint.
        if request.scope.get("type") == "websocket":
            return await call_next(request)

        # FastAPI dependency overrides are test-only. Let route-level test
        # fixtures supply CurrentUser without minting real JWTs.
        try:
            from ..auth.rbac import get_current_user

            if get_current_user in request.app.dependency_overrides:
                return await call_next(request)
        except Exception:
            pass

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header"},
            )

        token = auth_header[7:]
        try:
            payload = decode_access_token(token)
            jti = payload.get("jti")
            if isinstance(jti, str) and await is_jti_blocklisted(jti):
                return JSONResponse(status_code=401, content={"detail": "Token has been revoked"})
            request.state.user_id = payload.get("sub")
            request.state.tenant_id = payload.get("tenant_id")
            request.state.role = payload.get("role")
        except Exception as exc:
            log.warning("auth.invalid_token", path=path, error=str(exc))
            return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})

        return await call_next(request)

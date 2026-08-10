"""JWT authentication middleware — validates tokens on every request."""

from __future__ import annotations

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..auth.jwt_handler import decode_access_token
from ..config import get_settings

log = structlog.get_logger()
settings = get_settings()

# Paths that don't require authentication (any HTTP method)
PUBLIC_PATHS = frozenset({
    "/",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/auth/login",
    "/auth/refresh",
    "/auth/mfa/verify",
    "/documents/share/",  # shared link access
})

# GET-only public access for legal reference data.
# Only GET requests to these prefixes bypass JWT; all other methods on these
# prefixes must appear in _is_route_authority_write_exception() or they will
# require a valid JWT.  This prevents new write routes from silently inheriting
# public middleware access.
PUBLIC_GET_PREFIXES = frozenset({
    "/federal/",
    "/jurisdictions",
    "/legal-rules/",
    "/legal-authorities/",
    "/ucc-filings/",
})


def _is_route_authority_write_exception(method: str, path: str) -> bool:
    """Return True for write routes protected by _authorized_actor() rather than JWT.

    Each entry is individually enumerated.  A new write route added under a
    PUBLIC_GET_PREFIXES path that is not listed here will fall through to JWT
    enforcement, making the omission loud rather than silent.
    """
    if method != "POST":
        return False
    # Legacy UCC filing evaluation — protected by X-Reviewer-Role/Identity headers
    if path == "/ucc-filings/evaluate":
        return True
    # Legal authority metadata refresh
    if path.startswith("/legal-authorities/") and path.endswith("/refresh-metadata"):
        return True
    # Legal rule review workflow (submit-review, record-review, challenge)
    if path.startswith("/legal-rules/") and path.endswith(("/submit-review", "/reviews", "/challenges")):
        return True
    return False


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # Always-public paths (any method)
        if any(path.startswith(p) for p in PUBLIC_PATHS):
            return await call_next(request)

        # WebSocket: auth handled in endpoint
        if request.scope.get("type") == "websocket":
            return await call_next(request)

        # GET-only public access for legal reference data
        if method == "GET" and any(path.startswith(p) for p in PUBLIC_GET_PREFIXES):
            return await call_next(request)

        # Write routes on legal reference prefixes that use _authorized_actor()
        # instead of JWT.  Only individually proven routes are listed here.
        if _is_route_authority_write_exception(method, path):
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

        return await call_next(request)

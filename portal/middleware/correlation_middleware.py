"""HTTP correlation middleware for request-ID propagation and context binding.

Establishes a CorrelationContext before downstream application execution,
validates inbound X-Request-ID headers, generates secure identifiers when
missing or invalid, and returns the authoritative request ID in the response.
"""

from __future__ import annotations

import re
import secrets
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from ..auth.correlation import (
    CorrelationContext,
    reset_current_context,
    reset_request_context_tokens,
    set_current_context,
)

log = structlog.get_logger()

# Conservative character set for request IDs: alphanumeric, dash, underscore, dot, colon.
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._\-:]{1,128}$")
_DEFAULT_MAX_LENGTH = 128
_HEADER_NAME = "X-Request-ID"

# Client-supplied identity headers that must NEVER be trusted.
_UNTRUSTED_IDENTITY_HEADERS = frozenset({
    "x-actor-id",
    "x-user-id",
    "x-tenant-id",
    "x-role",
})


def validate_inbound_request_id(value: str | None, max_length: int = _DEFAULT_MAX_LENGTH) -> tuple[str, str | None]:
    """Validate an inbound request ID.

    Returns (authoritative_id, rejection_reason).
    If the inbound ID is valid, it is preserved.
    If missing or invalid, a new secure ID is generated and a reason is returned.
    """
    if value is None:
        return generate_request_id(), "missing"

    stripped = value.strip() if isinstance(value, str) else ""
    if not stripped:
        return generate_request_id(), "empty"

    if len(stripped) > max_length:
        return generate_request_id(), "too_long"

    # Check for control characters, CR, LF, null, backslash, forward slash, whitespace
    if any(c in stripped for c in "\r\n\x00\\/\t "):
        return generate_request_id(), "control_character"

    # Check against the valid character set
    if not _VALID_REQUEST_ID.match(stripped):
        return generate_request_id(), "unsupported_character"

    return stripped, None


def generate_request_id() -> str:
    """Generate a cryptographically unpredictable, URL/header-safe request ID."""
    prefix = secrets.token_hex(4)
    suffix = str(uuid.uuid4())
    return f"req-{prefix}-{suffix}"


class CorrelationMiddleware(BaseHTTPMiddleware):
    """HTTP middleware that establishes correlation context and propagates request IDs.

    - Validates inbound X-Request-ID header
    - Generates a secure ID if missing/invalid
    - Binds a CorrelationContext for the request lifecycle
    - Returns X-Request-ID in the response header
    - Cleans up context in a finally block
    """

    def __init__(
        self,
        app: ASGIApp,
        max_length: int = _DEFAULT_MAX_LENGTH,
        response_enabled: bool = True,
    ) -> None:
        super().__init__(app)
        self._max_length = max_length
        self._response_enabled = response_enabled

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Extract and validate inbound request ID via the single authoritative validator
        inbound_id = request.headers.get(_HEADER_NAME)
        authoritative_id, rejection_reason = validate_inbound_request_id(inbound_id, self._max_length)

        # Validate X-Correlation-ID through the same authoritative validator.
        # Whitespace-only and empty values are treated as missing (no double validation).
        inbound_corr = request.headers.get("X-Correlation-ID")
        if inbound_corr is not None and isinstance(inbound_corr, str) and inbound_corr.strip():
            corr_valid, corr_reason = validate_inbound_request_id(inbound_corr, self._max_length)
            correlation_id = corr_valid
            if corr_reason is not None:
                log.info(
                    "correlation.correlation_id_replaced",
                    correlation_id=correlation_id,
                    reason=corr_reason,
                )
        else:
            # Missing or blank X-Correlation-ID: derive from the authoritative request ID
            correlation_id = authoritative_id

        # Reject any client-supplied identity headers (do not trust them)
        for untrusted_header in _UNTRUSTED_IDENTITY_HEADERS:
            if untrusted_header in {k.lower() for k in request.headers}:
                log.warning(
                    "correlation.rejected_client_identity_header",
                    request_id=authoritative_id,
                    header=untrusted_header,
                )

        # Establish correlation context
        ctx = CorrelationContext(
            request_id=authoritative_id,
            correlation_id=correlation_id,
            causation_id=None,
            actor_id=None,  # Will be enriched after authentication
            tenant_id=None,  # Will be enriched after authentication
            invocation_type="http",
            source_transport="http",
        )

        if rejection_reason is not None:
            log.info(
                "correlation.request_id_replaced",
                request_id=authoritative_id,
                reason=rejection_reason,
            )

        # Bind context and process request.
        # We use the public set_current_context API so that we own the token
        # and can deterministically restore the pre-request context.
        # Authentication enrichment (get_current_user) may register additional
        # reset tokens on request.state; we reset those in reverse (LIFO)
        # order before restoring our own bind token, ensuring no
        # cross-request leakage and no unmanaged tokens.
        bind_token = set_current_context(ctx)
        try:
            response = await call_next(request)
        finally:
            # Any downstream exception must propagate with its original type.
            # Cleanup happens here exactly once; double-resetting the bind token
            # raises RuntimeError and masks the original failure.
            _reset_auth_tokens(request)
            reset_current_context(bind_token)

        # Add the authoritative request ID to the response
        if self._response_enabled:
            # Do not overwrite if already set (shouldn't happen, but be safe)
            if _HEADER_NAME.lower() not in {k.lower() for k in response.headers}:
                response.headers[_HEADER_NAME] = authoritative_id

        return response


def _reset_auth_tokens(request: Request) -> None:
    """Reset authentication-enrichment ContextVar tokens in reverse (LIFO) order.

    Delegates to ``reset_request_context_tokens`` in ``correlation.py``.
    Tokens registered on ``request.state`` by ``get_current_user`` are
    reset here so that the ContextVar is restored to the state established
    by the middleware's own ``set_current_context`` call before the
    middleware resets its own bind token.
    """
    reset_request_context_tokens(request)

"""WebSocket authentication, authorization, and correlation binding.

Provides the security layer for WebSocket connections: authentication
before accept, authorization via RBAC permissions, tenant isolation,
correlation context binding, and audit event emission.
"""

from __future__ import annotations

import contextlib
from typing import Any

import structlog
from fastapi import WebSocket, WebSocketDisconnect

from ..auth.jwt_handler import TokenError, decode_access_token
from ..auth.rbac import CurrentUser, Permission
from ..services.audit_service import audit
from .audit_envelope import ActorType, Outcome, Transport, build_audit_event, serialize_for_log
from .correlation import CorrelationContext, create_context

log = structlog.get_logger()

# Safe WebSocket close codes (custom 4xxx range per RFC 6455).
WS_CLOSE_CODES: dict[int, str] = {
    4401: "authentication required",
    4403: "forbidden",
    4404: "not found",
    4408: "connection lifetime exceeded",
    4413: "payload too large",
    4429: "too many connections",
    4400: "bad request",
}


async def authenticate_websocket(websocket: WebSocket) -> CurrentUser:
    """Extract and validate the JWT from the WebSocket connection.

    Supports token via query parameter "token" or Sec-WebSocket-Protocol header.
    Raises WebSocketDisconnect with code 4401 on authentication failure.
    """
    token = _extract_token(websocket)
    if not token:
        await _safe_reject(websocket, 4401)
        raise WebSocketDisconnect(code=4401)

    try:
        payload = decode_access_token(token)
        return CurrentUser(payload)
    except TokenError as exc:
        log.warning("ws.auth_failed", reason=str(exc))
        await _safe_reject(websocket, 4401)
        raise WebSocketDisconnect(code=4401) from exc
    except Exception as exc:
        log.warning("ws.auth_error", error=str(exc))
        await _safe_reject(websocket, 4401)
        raise WebSocketDisconnect(code=4401) from exc


def _extract_token(websocket: WebSocket) -> str | None:
    """Extract the JWT from query param or subprotocol."""
    # Query parameter: ws://host/path?token=xxx
    token = websocket.query_params.get("token")
    if token and isinstance(token, str) and token.strip():
        return token.strip()

    # Subprotocol: Sec-WebSocket-Protocol: bearer.xxx
    protocols = websocket.headers.get("sec-websocket-protocol", "")
    if protocols:
        for proto in protocols.split(","):
            proto = proto.strip()
            if proto.lower().startswith("bearer."):
                extracted = proto[7:]
                if extracted.strip():
                    return extracted.strip()

    return None


async def authorize_websocket_connection(
    user: CurrentUser,
    required_permission: Permission | None = None,
) -> None:
    """Check that the user has the required permission.

    Raises WebSocketDisconnect with code 4403 on authorization denial.
    """
    if required_permission is not None and not user.has_permission(required_permission):
        raise WebSocketDisconnect(code=4403)


def bind_websocket_context(user: CurrentUser, websocket: WebSocket) -> CorrelationContext:
    """Create and bind a correlation context for the WebSocket lifecycle."""
    return create_context(
        actor_id=user.user_id,
        tenant_id=user.tenant_id,
        invocation_type="websocket",
        source_transport="websocket",
        inbound_request_id=websocket.query_params.get("request_id"),
        inbound_correlation_id=websocket.query_params.get("correlation_id"),
    )


async def safe_close(websocket: WebSocket, code: int, reason: str | None = None) -> None:
    """Close a WebSocket with a safe, non-sensitive reason string."""
    safe_reason = WS_CLOSE_CODES.get(code, reason or "closing")
    with contextlib.suppress(Exception):
        await websocket.close(code=code, reason=safe_reason)


async def _safe_reject(websocket: WebSocket, code: int) -> None:
    """Reject a WebSocket connection before accepting it."""
    await safe_close(websocket, code)


async def audit_websocket_event(
    db: Any | None,
    action: str,
    user: CurrentUser,
    websocket: WebSocket,
    outcome: Outcome = Outcome.SUCCESS,
    denial_reason: str | None = None,
) -> None:
    """Emit an audit event for a WebSocket lifecycle event.

    Uses the bound correlation context if available.
    """
    event = build_audit_event(
        action=action,
        actor_id=user.user_id,
        actor_type=ActorType.USER,
        tenant_id=user.tenant_id,
        resource_type="websocket",
        resource_id=str(id(websocket)),
        source_transport=Transport.WEBSOCKET,
        source_entrypoint=websocket.url.path,
        outcome=outcome,
        denial_reason=denial_reason,
        metadata={"path": websocket.url.path},
    )

    log.info("ws.audit", **serialize_for_log(event))

    # If a DB session is available, also write to the audit log.
    if db is not None:
        try:
            await audit(
                db,
                action=action,
                user_id=user.user_id,
                tenant_id=user.tenant_id,
                resource_type="websocket",
                resource_id=str(id(websocket)),
                status=event.outcome,
                details={"request_id": event.request_id, "correlation_id": event.correlation_id},
            )
        except Exception as exc:
            log.warning("ws.audit_write_failed", error=str(exc))

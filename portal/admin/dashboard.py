"""Admin Dashboard — Real-time metrics & WebSocket updates."""
import asyncio
import contextlib
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from portal.auth.audit_envelope import Outcome
from portal.auth.correlation import bind_context
from portal.auth.rbac import CurrentUser, Permission, require_permissions
from portal.auth.websocket_auth import (
    audit_websocket_event,
    authenticate_websocket,
    authorize_websocket_connection,
    bind_websocket_context,
    safe_close,
)
from portal.auth.ws_hardening import (
    WSHardeningSettings,
    get_auth_failure_throttle,
    get_effective_client_address,
    get_ws_capacity_controller,
)
from portal.config import get_settings
from portal.websocket.connection_manager import ws_manager

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()

# WebSocket hardening settings
ws_hardening_settings = WSHardeningSettings()
ws_capacity = get_ws_capacity_controller(ws_hardening_settings)
auth_throttle = get_auth_failure_throttle(ws_hardening_settings)

# In-memory metrics store
metrics_store = {
    "requests_total": 0,
    "requests_per_sec": 0.0,
    "avg_response_time_ms": 0.0,
    "error_rate": 0.0,
    "active_sessions": 0,
    "uptime_seconds": 0,
    "last_updated": datetime.now(UTC).isoformat(),
}


# ── Inbound WebSocket Policy ───────────────────────────────────────────────────
#
# Policy B — receive and validate limited heartbeat messages.
#
# The server is stream-only for application data, but clients may send
# minimal heartbeat frames for liveness.  Only a single schema is accepted:
#   {"type": "ping"}
#
# Inbound payload policy:
#   - payload_max_bytes applies to every inbound text and binary frame;
#   - oversized inbound frames are closed with code 4413;
#   - under-limit but unsupported/malformed frames are closed with code 4403;
#   - a valid heartbeat updates last_client_activity;
#   - no inbound payload content is written to logs or audit metadata.
#
# Outbound payload policy:
#   - payload_max_bytes applies to every outbound metrics payload;
#   - oversized outbound payloads are skipped (metrics are non-critical).
#
# Task ownership:
#   - receiver task exclusively calls websocket.receive()
#   - sender/coordinator task exclusively calls websocket.send_text()
#   - endpoint coordinator exclusively decides and performs close
#   - child tasks must not independently close the WebSocket


_HEARTBEAT_SCHEMA = frozenset({"ping"})


# ── Typed inbound events ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class InboundEvent:
    """Typed event published by the receiver task for the coordinator.

    The receiver task NEVER closes the WebSocket.  It publishes one of
    these events to the asyncio.Queue and the coordinator decides the
    appropriate action (including close).
    """

    kind: str  # HEARTBEAT | CLIENT_DISCONNECT | PAYLOAD_TOO_LARGE | UNSUPPORTED_MESSAGE | RECEIVE_FAILURE
    client_activity_at: float | None = None
    close_code: int | None = None  # suggested close code for the coordinator


# Event kind constants
_HEARTBEAT = "HEARTBEAT"
_CLIENT_DISCONNECT = "CLIENT_DISCONNECT"
_PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"
_UNSUPPORTED_MESSAGE = "UNSUPPORTED_MESSAGE"
_RECEIVE_FAILURE = "RECEIVE_FAILURE"


async def _inbound_frame_handler(
    websocket: WebSocket,
    hardening_settings: WSHardeningSettings,
    event_queue: asyncio.Queue[InboundEvent],
) -> None:
    """Receive and validate inbound WebSocket frames.

    Exclusively owns ``websocket.receive()``.  Publishes typed
    ``InboundEvent`` results to ``event_queue``.  NEVER calls
    ``safe_close`` — the endpoint coordinator is the sole close owner.

    On any terminal condition (disconnect, violation, failure), this
    task publishes the event and returns, leaving close to the
    coordinator.
    """
    while True:
        try:
            msg = await websocket.receive()
        except WebSocketDisconnect:
            await event_queue.put(InboundEvent(kind=_CLIENT_DISCONNECT))
            return
        except asyncio.CancelledError:
            raise
        except Exception:
            await event_queue.put(InboundEvent(kind=_RECEIVE_FAILURE))
            return

        # ── ASGI disconnect message (not raised as WebSocketDisconnect) ──
        if msg.get("type") == "websocket.disconnect":
            await event_queue.put(InboundEvent(kind=_CLIENT_DISCONNECT))
            return

        # ── text frame ───────────────────────────────────────────────
        text_data = msg.get("text")
        if text_data is not None:
            encoded_len = len(text_data.encode("utf-8"))
            if encoded_len > hardening_settings.payload_max_bytes:
                await event_queue.put(
                    InboundEvent(kind=_PAYLOAD_TOO_LARGE, close_code=4413)
                )
                return
            try:
                parsed = json.loads(text_data)
            except (json.JSONDecodeError, TypeError):
                await event_queue.put(
                    InboundEvent(kind=_UNSUPPORTED_MESSAGE, close_code=4403)
                )
                return
            if (
                isinstance(parsed, dict)
                and parsed.get("type") in _HEARTBEAT_SCHEMA
            ):
                await event_queue.put(
                    InboundEvent(
                        kind=_HEARTBEAT,
                        client_activity_at=time.monotonic(),
                    )
                )
                continue
            # Under-limit but unsupported message
            await event_queue.put(
                InboundEvent(kind=_UNSUPPORTED_MESSAGE, close_code=4403)
            )
            return

        # ── binary frame ──────────────────────────────────────────────
        binary_data = msg.get("bytes")
        if binary_data is not None:
            if len(binary_data) > hardening_settings.payload_max_bytes:
                await event_queue.put(
                    InboundEvent(kind=_PAYLOAD_TOO_LARGE, close_code=4413)
                )
                return
            # Binary frames are not supported
            await event_queue.put(
                InboundEvent(kind=_UNSUPPORTED_MESSAGE, close_code=4403)
            )
            return


@router.get("/dashboard")
async def get_dashboard(_: CurrentUser = Depends(require_permissions(Permission.ADMIN_DASHBOARD))):
    """Serve dashboard HTML (requires ADMIN_DASHBOARD permission)."""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SintraPrime Admin Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .dashboard { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
            .metric { background: white; padding: 20px: border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .metric-value { font-size: 24px; font-weight: bold; color: #007bff; }
            .metric-label { font-size: 12px; color: #666; margin-top: 5px; }
            canvas { width: 100%; }
        </style>
    </head>
    <body>
        <h1>SintraPrime Admin Dashboard</h1>
        <div class="dashboard">
            <div class="metric">
                <div class="metric-value" id="requests">0</div>
                <div class="metric-label">Total Requests</div>
            </div>
            <div class="metric">
                <div class="metric-value" id="rps">0.0</div>
                <div class="metric-label">Requests/sec</div>
            </div>
            <div class="metric">
                <div class="metric-value" id="latency">0ms</div>
                <div class="metric-label">Avg Response Time</div>
            </div>
            <div class="metric">
                <div class="metric-value" id="errors">0%</div>
                <div class="metric-label">Error Rate</div>
            </div>
        </div>
        <script>
            const scheme = window.location.protocol === "https:" ? "wss" : "ws";
            const url = `${scheme}://${window.location.host}/api/v1/admin/ws`;
            const ws = new WebSocket(url);
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                document.getElementById("requests").textContent = data.requests_total;
                document.getElementById("rps").textContent = data.requests_per_sec.toFixed(1);
                document.getElementById("latency").textContent = data.avg_response_time_ms.toFixed(0) + "ms";
                document.getElementById("errors").textContent = data.error_rate.toFixed(1) + "%";
            };
        </script>
    </body>
    </html>
    """)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time metric streaming.

    Server-stream-only protocol with limited heartbeat inbound (Policy B).

    Inbound payload policy:
    - Only ``{"type": "ping"}`` heartbeat frames are accepted.
    - Oversized inbound text/binary frames are closed with code 4413.
    - Unsupported under-limit frames are closed with code 4403.
    - Inbound payload content is never written to logs or audit metadata.

    Outbound payload policy:
    - Payload size enforced at payload_max_bytes.
    - Oversized outbound payloads are skipped (metrics are non-critical).

    Task ownership:
    - receiver task exclusively calls websocket.receive()
    - sender/coordinator task exclusively calls websocket.send_text()
    - endpoint coordinator exclusively decides and performs close
    - child tasks must not independently close the WebSocket

    Security controls:
    - Authentication before accept (JWT validation)
    - Authorization (ADMIN_DASHBOARD permission)
    - Authentication-failure throttling
    - Capacity controls (global, per-actor, per-tenant, per-address)
    - Strict fixed-interval rate limiting on outbound sends
    - Idle timeout based on client activity (not server sends)
    - Maximum connection lifetime
    - Correlation context binding
    - Audit events for connect/disconnect/denials
    """
    client_address = get_effective_client_address(websocket)

    # Check authentication-failure throttle before attempting auth
    if await auth_throttle.is_throttled(client_address):
        await safe_close(websocket, 4429)
        return

    # Authenticate before accepting the connection.
    try:
        user = await authenticate_websocket(websocket)
    except WebSocketDisconnect:
        await auth_throttle.record_failure(client_address)
        return  # already rejected with 4401

    # Authorize: require ADMIN_DASHBOARD permission.
    try:
        await authorize_websocket_connection(user, Permission.ADMIN_DASHBOARD)
    except WebSocketDisconnect:
        await safe_close(websocket, 4403)
        with bind_context(bind_websocket_context(user, websocket)):
            await audit_websocket_event(
                db=None,
                action="websocket_authorization_denied",
                user=user,
                websocket=websocket,
                outcome=Outcome.DENIED,
                denial_reason="insufficient_permission",
            )
        return

    # Capacity control: try to register the connection
    registered = False
    connected = False

    registration_result, denial_reason = await ws_capacity.try_register(
        websocket, user.user_id, user.tenant_id, client_address
    )
    if not registration_result:
        close_code = 4429 if denial_reason and "limit" in denial_reason else 4400
        await safe_close(websocket, close_code)
        with bind_context(bind_websocket_context(user, websocket)):
            await audit_websocket_event(
                db=None,
                action="websocket_capacity_denied",
                user=user,
                websocket=websocket,
                outcome=Outcome.DENIED,
                denial_reason=denial_reason or "capacity_exceeded",
            )
        return

    registered = True

    # Bind correlation context for the WebSocket lifecycle.
    ctx = bind_websocket_context(user, websocket)

    # Event queue: receiver publishes typed events, coordinator consumes.
    event_queue: asyncio.Queue[InboundEvent] = asyncio.Queue()
    receiver_task: asyncio.Task | None = None
    last_client_activity = time.monotonic()
    closed = False

    try:
        # Register with the connection manager (accepts the connection).
        await ws_manager.connect(websocket, user.user_id, user.tenant_id)
        connected = True

        # Audit the connection acceptance.
        with bind_context(ctx):
            await audit_websocket_event(
                db=None,
                action="websocket_connect",
                user=user,
                websocket=websocket,
            )

        # Start receiver task — sole owner of websocket.receive()
        receiver_task = asyncio.create_task(
            _inbound_frame_handler(websocket, ws_hardening_settings, event_queue)
        )

        connection_start = time.monotonic()
        send_interval = ws_hardening_settings.min_send_interval_seconds
        last_send_time: float | None = None

        with bind_context(ctx):
            while True:
                now = time.monotonic()

                # Compute deadlines for idle timeout, max lifetime, and
                # the next scheduled outbound send.  The first send is
                # immediate (no interval wait); subsequent sends respect
                # min_send_interval_seconds.
                idle_deadline = last_client_activity + ws_hardening_settings.idle_timeout_seconds
                max_deadline = connection_start + ws_hardening_settings.max_connection_lifetime_seconds
                next_send = now if last_send_time is None else last_send_time + send_interval
                earliest_deadline = min(next_send, idle_deadline, max_deadline)
                timeout = max(0.0, earliest_deadline - now)

                # Wait for the earliest of: next scheduled outbound send,
                # receiver event, idle deadline, max lifetime deadline,
                # or endpoint cancellation.  The receiver publishes typed
                # events to the queue; we do not poll a shared dict.
                try:
                    event = await asyncio.wait_for(
                        event_queue.get(),
                        timeout=timeout if timeout > 0 else 0.0001,
                    )
                except TimeoutError:
                    event = None

                now = time.monotonic()

                # Process inbound event if one arrived
                if event is not None:
                    if event.kind == _HEARTBEAT:
                        if event.client_activity_at is not None:
                            last_client_activity = event.client_activity_at
                        # Sender sends pong response
                        if not closed:
                            try:
                                await websocket.send_text(json.dumps({"type": "pong"}))
                            except Exception:
                                break
                        continue

                    if event.kind == _CLIENT_DISCONNECT:
                        # Client disconnected — exit cleanly, no close needed.
                        break

                    if event.kind == _PAYLOAD_TOO_LARGE:
                        # Coordinator closes with suggested code
                        if not closed:
                            await safe_close(websocket, event.close_code or 4413)
                            closed = True
                        break

                    if event.kind == _UNSUPPORTED_MESSAGE:
                        if not closed:
                            await safe_close(websocket, event.close_code or 4403)
                            closed = True
                        break

                    if event.kind == _RECEIVE_FAILURE:
                        if not closed:
                            await safe_close(websocket, 4400)
                            closed = True
                        break

                # Check idle timeout (based on client activity, not server sends)
                if now - last_client_activity > ws_hardening_settings.idle_timeout_seconds:
                    if not closed:
                        await safe_close(websocket, 4408)
                        closed = True
                        await audit_websocket_event(
                            db=None,
                            action="websocket_idle_timeout",
                            user=user,
                            websocket=websocket,
                            outcome=Outcome.FAILURE,
                            denial_reason="idle_timeout",
                        )
                    break

                # Check max connection lifetime (independent of client activity)
                if now - connection_start > ws_hardening_settings.max_connection_lifetime_seconds:
                    if not closed:
                        await safe_close(websocket, 4408)
                        closed = True
                        await audit_websocket_event(
                            db=None,
                            action="websocket_lifetime_timeout",
                            user=user,
                            websocket=websocket,
                            outcome=Outcome.FAILURE,
                            denial_reason="max_lifetime",
                        )
                    break

                # Check if receiver task ended (disconnect or failure)
                if receiver_task.done():
                    break

                # Before every send: check whether termination was requested
                if closed:
                    break

                # Serialize and check outbound payload size
                payload = json.dumps(metrics_store, default=str).encode("utf-8")
                if len(payload) > ws_hardening_settings.payload_max_bytes:
                    if not closed:
                        await audit_websocket_event(
                            db=None,
                            action="websocket_payload_oversized",
                            user=user,
                            websocket=websocket,
                            outcome=Outcome.FAILURE,
                            denial_reason="payload_too_large",
                        )
                    # Skip this send rather than disconnect — metrics are non-critical
                    continue

                # Sender: exclusively calls send_text()
                if not closed:
                    try:
                        await websocket.send_text(payload.decode("utf-8"))
                        last_send_time = time.monotonic()
                    except Exception:
                        # Send failure — exit cleanly
                        break

    except asyncio.CancelledError:
        # Endpoint-level cancellation must not be swallowed.
        raise
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        # Cancel and await receiver task to prevent zombie receive task.
        if receiver_task is not None and not receiver_task.done():
            receiver_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await receiver_task

        # Cleanup: disconnect from manager, then unregister capacity.
        # Order matters: disconnect first (closes ws), then free capacity slot.
        # Both are idempotent — safe to call even if never connected/registered.
        if connected:
            await ws_manager.disconnect(websocket, user.user_id, user.tenant_id)
        if registered:
            await ws_capacity.unregister(websocket)

        with bind_context(ctx):
            await audit_websocket_event(
                db=None,
                action="websocket_disconnect",
                user=user,
                websocket=websocket,
            )


@router.get("/metrics")
async def get_metrics(_: CurrentUser = Depends(require_permissions(Permission.ADMIN_DASHBOARD))):
    """REST endpoint for metrics (requires ADMIN_DASHBOARD permission)."""
    return metrics_store

@router.post("/metrics/update")
async def update_metrics(
    data: dict,
    _: CurrentUser = Depends(require_permissions(Permission.ADMIN_DASHBOARD)),
):
    """Update metrics store (requires ADMIN_DASHBOARD permission)."""
    metrics_store.update(data)
    metrics_store["last_updated"] = datetime.now(UTC).isoformat()
    return {"status": "updated"}

"""
network_display.py — Twin-inspired Network-Transparent Display for SintraPrime

Based on twin's network socket layer (server/socket.cpp, libtw API).
Serves TUI state over WebSocket and REST for remote monitoring.
"""

import asyncio
import hashlib
import json
import logging
import os
import secrets
import time
import zlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# ─── Protocol helpers ─────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compress_payload(data: str) -> bytes:
    """Compress a JSON string payload with zlib for large screen updates."""
    return zlib.compress(data.encode("utf-8"), level=6)


def decompress_payload(data: bytes) -> str:
    """Decompress a zlib-compressed payload."""
    return zlib.decompress(data).decode("utf-8")


def make_token(length: int = 32) -> str:
    """Generate a cryptographically secure token."""
    return secrets.token_hex(length)


# ─── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class WindowState:
    """Serializable snapshot of a single window's state."""
    win_id: str
    title: str
    x: int
    y: int
    w: int
    h: int
    z_order: int
    state: str
    focused: bool
    content_preview: str = ""   # First line of content for quick display

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScreenState:
    """Full serializable snapshot of the TUI display."""
    timestamp: str
    term_width: int
    term_height: int
    windows: List[Dict[str, Any]]
    focused_id: Optional[str]
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    def to_compressed(self) -> bytes:
        return compress_payload(self.to_json())


@dataclass
class DisplayClientInfo:
    """Track a connected WebSocket client."""
    client_id: str
    connected_at: str
    remote_addr: str
    authenticated: bool
    last_ping: float
    websocket: Any  # actual websocket object


# ─── Authentication ───────────────────────────────────────────────────────────

class TwinAuth:
    """
    Token-based authentication for display connections.
    Inspired by twin's TwinAuth mechanism.
    """

    def __init__(self):
        self._tokens: Dict[str, Dict[str, Any]] = {}

    def issue_token(self, label: str = "", ttl: int = 86400) -> str:
        """
        Issue a new auth token.

        Args:
            label: Human-readable label for the token.
            ttl: Time-to-live in seconds.

        Returns:
            The token string.
        """
        token = make_token()
        self._tokens[token] = {
            "label": label,
            "issued_at": time.time(),
            "expires_at": time.time() + ttl,
            "use_count": 0,
        }
        return token

    def validate_token(self, token: str) -> bool:
        """
        Check if a token is valid and not expired.

        Args:
            token: Token to validate.

        Returns:
            True if valid.
        """
        info = self._tokens.get(token)
        if not info:
            return False
        if time.time() > info["expires_at"]:
            del self._tokens[token]
            return False
        info["use_count"] += 1
        return True

    def revoke_token(self, token: str):
        """Revoke a token immediately."""
        self._tokens.pop(token, None)

    def list_tokens(self) -> List[Dict[str, Any]]:
        """List all active tokens (without the token value)."""
        return [
            {**v, "valid": time.time() < v["expires_at"]}
            for v in self._tokens.values()
        ]


# ─── Reconnect logic ──────────────────────────────────────────────────────────

class ReconnectManager:
    """
    Manages reconnection attempts for display clients.
    Twin clients automatically reconnect after server restart.
    """

    def __init__(self, max_retries: int = 10, base_delay: float = 1.0,
                 max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self._attempts: Dict[str, int] = {}

    def next_delay(self, client_id: str) -> Optional[float]:
        """
        Calculate next reconnect delay (exponential backoff).

        Returns:
            Delay in seconds, or None if max retries exceeded.
        """
        attempts = self._attempts.get(client_id, 0)
        if attempts >= self.max_retries:
            return None
        delay = min(self.base_delay * (2 ** attempts), self.max_delay)
        self._attempts[client_id] = attempts + 1
        return delay

    def reset(self, client_id: str):
        """Reset retry counter after successful connection."""
        self._attempts.pop(client_id, None)

    def get_attempt_count(self, client_id: str) -> int:
        return self._attempts.get(client_id, 0)


# ─── DisplayServer ────────────────────────────────────────────────────────────

class DisplayServer:
    """
    Serves TUI state over WebSocket and REST.
    Inspired by twin's network-transparent display layer.

    The server broadcasts screen updates to all connected clients and
    accepts display commands from authorized clients.

    Usage:
        server = DisplayServer(host="0.0.0.0", port=8765)
        token = server.auth.issue_token("admin")
        await server.start()
        server.update_screen_state(window_manager)
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        """
        Initialize display server.

        Args:
            host: Bind address.
            port: WebSocket port.
        """
        self.host = host
        self.port = port
        self.auth = TwinAuth()
        self._clients: Dict[str, DisplayClientInfo] = {}
        self._current_state: Optional[ScreenState] = None
        self._state_version: int = 0
        self._update_callbacks: List[Callable[[ScreenState], None]] = []
        self._server = None
        self._running = False
        logger.info("DisplayServer configured on %s:%d", host, port)

    # ── State management ──────────────────────────────────────────────────────

    def build_screen_state(self, window_manager: Any) -> ScreenState:
        """
        Build a ScreenState from a TUIWindowManager.

        Args:
            window_manager: TUIWindowManager instance.

        Returns:
            ScreenState snapshot.
        """
        windows = []
        for w_info in window_manager.list_windows():
            win = window_manager.get_window(w_info["win_id"])
            content_preview = ""
            if win and win._content and win._content[0]:
                content_preview = "".join(
                    c[0] for c in win._content[0]
                ).strip()[:80]
            ws = WindowState(
                win_id=w_info["win_id"],
                title=w_info["title"],
                x=w_info["x"], y=w_info["y"],
                w=w_info["w"], h=w_info["h"],
                z_order=w_info["z_order"],
                state=w_info["state"],
                focused=w_info["focused"],
                content_preview=content_preview,
            )
            windows.append(ws.to_dict())

        self._state_version += 1
        state = ScreenState(
            timestamp=_now_iso(),
            term_width=window_manager.term_width,
            term_height=window_manager.term_height,
            windows=windows,
            focused_id=window_manager._focused_id,
            version=self._state_version,
        )
        self._current_state = state
        return state

    def set_screen_state(self, state: ScreenState):
        """Manually set the current screen state."""
        self._current_state = state
        self._state_version = state.version

    def get_current_state(self) -> Optional[ScreenState]:
        """Get the current screen state."""
        return self._current_state

    # ── REST endpoint simulation ───────────────────────────────────────────────

    async def handle_rest_state(self, request: Any) -> Dict[str, Any]:
        """
        Handler for GET /api/display/state.
        Returns current screen state as JSON.

        Args:
            request: HTTP request object (framework-agnostic).

        Returns:
            JSON-serializable dict.
        """
        if not self._current_state:
            return {"error": "No screen state available", "status": 404}
        return {
            "status": 200,
            "data": self._current_state.to_dict(),
        }

    # ── WebSocket broadcast ───────────────────────────────────────────────────

    async def broadcast_screen_state(self, state: Optional[ScreenState] = None):
        """
        Broadcast current TUI state to all connected authenticated clients.

        Args:
            state: ScreenState to broadcast. Uses current state if None.
        """
        if state is None:
            state = self._current_state
        if state is None:
            return

        payload = state.to_json()
        # Compress if payload is large (> 4KB)
        use_compression = len(payload) > 4096
        if use_compression:
            compressed = state.to_compressed()
            msg_type = "screen_update_compressed"
        else:
            msg_type = "screen_update"

        disconnected: List[str] = []
        for cid, client in list(self._clients.items()):
            if not client.authenticated:
                continue
            try:
                if use_compression:
                    await client.websocket.send(json.dumps({
                        "type": msg_type,
                        "compressed": True,
                        "size": len(compressed),
                        "version": state.version,
                    }))
                else:
                    await client.websocket.send(json.dumps({
                        "type": msg_type,
                        "data": state.to_dict(),
                    }))
            except Exception as exc:
                logger.warning("Client %s disconnected during broadcast: %s", cid, exc)
                disconnected.append(cid)

        for cid in disconnected:
            self._clients.pop(cid, None)

        logger.debug("Broadcasted state v%d to %d clients",
                     state.version, len(self._clients))

    async def handle_websocket(self, websocket: Any, path: str):
        """
        Handle a new WebSocket connection at /ws/display.

        Performs authentication handshake then streams updates.

        Args:
            websocket: WebSocket connection object.
            path: URL path.
        """
        import uuid
        client_id = str(uuid.uuid4())
        remote = getattr(websocket, "remote_address", ("unknown", 0))
        remote_str = f"{remote[0]}:{remote[1]}" if isinstance(remote, tuple) else str(remote)

        client = DisplayClientInfo(
            client_id=client_id,
            connected_at=_now_iso(),
            remote_addr=remote_str,
            authenticated=False,
            last_ping=time.time(),
            websocket=websocket,
        )
        self._clients[client_id] = client
        logger.info("WS client %s connected from %s", client_id, remote_str)

        try:
            # Auth handshake
            await websocket.send(json.dumps({
                "type": "auth_required",
                "client_id": client_id,
            }))

            auth_msg_raw = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            auth_msg = json.loads(auth_msg_raw)

            if auth_msg.get("type") == "auth" and self.auth.validate_token(
                    auth_msg.get("token", "")):
                client.authenticated = True
                await websocket.send(json.dumps({"type": "auth_ok", "client_id": client_id}))
                logger.info("Client %s authenticated", client_id)
            else:
                await websocket.send(json.dumps({"type": "auth_fail"}))
                logger.warning("Client %s authentication failed", client_id)
                return

            # Send initial state
            if self._current_state:
                await websocket.send(json.dumps({
                    "type": "initial_state",
                    "data": self._current_state.to_dict(),
                }))

            # Main message loop
            async for message_raw in websocket:
                try:
                    msg = json.loads(message_raw)
                    await self._handle_client_message(client, msg)
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON from client %s", client_id)
                except Exception as exc:
                    logger.error("Error handling message from %s: %s", client_id, exc)

        except asyncio.TimeoutError:
            logger.warning("Client %s auth timeout", client_id)
        except Exception as exc:
            logger.info("Client %s disconnected: %s", client_id, exc)
        finally:
            self._clients.pop(client_id, None)
            logger.info("WS client %s removed", client_id)

    async def _handle_client_message(self, client: DisplayClientInfo,
                                     msg: Dict[str, Any]):
        """Process an incoming message from an authenticated client."""
        msg_type = msg.get("type", "")
        if msg_type == "ping":
            client.last_ping = time.time()
            await client.websocket.send(json.dumps({"type": "pong"}))
        elif msg_type == "request_state":
            if self._current_state:
                await client.websocket.send(json.dumps({
                    "type": "screen_update",
                    "data": self._current_state.to_dict(),
                }))
        elif msg_type == "subscribe":
            logger.debug("Client %s subscribed to updates", client.client_id)
        else:
            logger.debug("Unknown message type '%s' from client %s",
                         msg_type, client.client_id)

    # ── Server lifecycle ──────────────────────────────────────────────────────

    async def start(self):
        """Start the WebSocket server."""
        try:
            import websockets
            self._server = await websockets.serve(
                self.handle_websocket,
                self.host,
                self.port,
            )
            self._running = True
            logger.info("DisplayServer started on ws://%s:%d", self.host, self.port)
        except ImportError:
            logger.warning("websockets package not available; DisplayServer running in mock mode")
            self._running = True
        except Exception as exc:
            logger.error("Failed to start DisplayServer: %s", exc)
            raise

    async def stop(self):
        """Stop the WebSocket server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        self._running = False
        logger.info("DisplayServer stopped")

    def client_count(self) -> int:
        """Return number of connected clients."""
        return len(self._clients)

    def authenticated_client_count(self) -> int:
        """Return number of authenticated connected clients."""
        return sum(1 for c in self._clients.values() if c.authenticated)


# ─── DisplayClient ────────────────────────────────────────────────────────────

class DisplayClient:
    """
    Connects to a remote DisplayServer to receive TUI state updates.
    Implements automatic reconnection like twin's display client.

    Usage:
        client = DisplayClient("ws://localhost:8765", token="your-token")
        await client.connect()
        state = client.get_latest_state()
        await client.disconnect()
    """

    def __init__(self, server_url: str, token: str,
                 on_state_update: Optional[Callable[[ScreenState], None]] = None):
        """
        Initialize display client.

        Args:
            server_url: WebSocket URL of the display server.
            token: Authentication token.
            on_state_update: Callback invoked when new state is received.
        """
        self.server_url = server_url
        self.token = token
        self.on_state_update = on_state_update
        self.reconnect_mgr = ReconnectManager()
        self._websocket = None
        self._connected = False
        self._latest_state: Optional[ScreenState] = None
        self.client_id: Optional[str] = None

    async def connect(self):
        """Connect and authenticate to the display server."""
        try:
            import websockets
            self._websocket = await websockets.connect(self.server_url)
            logger.info("Connected to display server at %s", self.server_url)

            # Wait for auth challenge
            challenge = json.loads(await self._websocket.recv())
            if challenge.get("type") == "auth_required":
                self.client_id = challenge.get("client_id")
                await self._websocket.send(json.dumps({
                    "type": "auth",
                    "token": self.token,
                }))
                result = json.loads(await self._websocket.recv())
                if result.get("type") == "auth_ok":
                    self._connected = True
                    self.reconnect_mgr.reset(self.server_url)
                    logger.info("Authenticated as client %s", self.client_id)
                    asyncio.ensure_future(self._receive_loop())
                else:
                    raise PermissionError("Authentication failed")
        except ImportError:
            logger.warning("websockets not available; running in mock mode")
            self._connected = True
        except Exception as exc:
            logger.error("Failed to connect to display server: %s", exc)
            raise

    async def _receive_loop(self):
        """Listen for screen state updates from the server."""
        try:
            async for message_raw in self._websocket:
                try:
                    msg = json.loads(message_raw)
                    await self._handle_message(msg)
                except Exception as exc:
                    logger.warning("Error processing server message: %s", exc)
        except Exception as exc:
            logger.info("Disconnected from display server: %s", exc)
            self._connected = False
            await self._attempt_reconnect()

    async def _handle_message(self, msg: Dict[str, Any]):
        """Process a message from the display server."""
        msg_type = msg.get("type", "")
        if msg_type in ("screen_update", "initial_state"):
            data = msg.get("data", {})
            state = ScreenState(
                timestamp=data.get("timestamp", _now_iso()),
                term_width=data.get("term_width", 80),
                term_height=data.get("term_height", 24),
                windows=data.get("windows", []),
                focused_id=data.get("focused_id"),
                version=data.get("version", 0),
            )
            self._latest_state = state
            if self.on_state_update:
                try:
                    self.on_state_update(state)
                except Exception as exc:
                    logger.warning("State update callback error: %s", exc)
        elif msg_type == "pong":
            pass
        else:
            logger.debug("Unknown message type from server: %s", msg_type)

    async def _attempt_reconnect(self):
        """Attempt reconnection with exponential backoff."""
        delay = self.reconnect_mgr.next_delay(self.server_url)
        if delay is None:
            logger.error("Max reconnect attempts reached for %s", self.server_url)
            return
        logger.info("Reconnecting in %.1fs (attempt %d)...", delay,
                    self.reconnect_mgr.get_attempt_count(self.server_url))
        await asyncio.sleep(delay)
        try:
            await self.connect()
        except Exception as exc:
            logger.warning("Reconnect failed: %s", exc)
            await self._attempt_reconnect()

    def get_latest_state(self) -> Optional[ScreenState]:
        """Return the most recently received screen state."""
        return self._latest_state

    async def request_state(self):
        """Ask the server to send the current state immediately."""
        if self._websocket and self._connected:
            await self._websocket.send(json.dumps({"type": "request_state"}))

    async def send_ping(self):
        """Send a ping to keep connection alive."""
        if self._websocket and self._connected:
            await self._websocket.send(json.dumps({"type": "ping"}))

    async def disconnect(self):
        """Disconnect from the display server."""
        self._connected = False
        if self._websocket:
            await self._websocket.close()
            self._websocket = None
        logger.info("Disconnected from display server")

    def is_connected(self) -> bool:
        return self._connected

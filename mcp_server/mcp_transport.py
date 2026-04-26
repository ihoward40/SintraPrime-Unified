"""
MCP Transport Layer — Stdio, HTTP/SSE, and WebSocket transports.

Implements message framing per the MCP specification:
  Content-Length: <bytes>\r\n\r\n<json-body>
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from abc import ABC, abstractmethod
from typing import AsyncIterator, Callable, Optional

logger = logging.getLogger(__name__)

MessageHandler = Callable[[dict], dict]


# ---------------------------------------------------------------------------
# Base transport
# ---------------------------------------------------------------------------

class BaseTransport(ABC):
    """Abstract base class for all MCP transports."""

    @abstractmethod
    async def start(self, handler: MessageHandler) -> None:
        """Start the transport and call *handler* for each incoming message."""

    @abstractmethod
    async def send(self, message: dict) -> None:
        """Send a message to the connected client."""

    @abstractmethod
    async def close(self) -> None:
        """Shut down the transport cleanly."""

    # ------------------------------------------------------------------
    # Shared framing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def frame_message(message: dict) -> bytes:
        body = json.dumps(message, separators=(",", ":")).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        return header + body

    @staticmethod
    async def read_message(reader: asyncio.StreamReader) -> Optional[dict]:
        """Read one length-framed JSON-RPC message from *reader*."""
        header_bytes = b""
        while True:
            chunk = await reader.read(1)
            if not chunk:
                return None
            header_bytes += chunk
            if header_bytes.endswith(b"\r\n\r\n"):
                break

        header_str = header_bytes.decode("ascii", errors="replace")
        content_length: Optional[int] = None
        for line in header_str.split("\r\n"):
            if line.lower().startswith("content-length:"):
                try:
                    content_length = int(line.split(":", 1)[1].strip())
                except ValueError:
                    pass

        if content_length is None:
            logger.error("Missing Content-Length header in message")
            return None

        body = await reader.readexactly(content_length)
        return json.loads(body.decode("utf-8"))


# ---------------------------------------------------------------------------
# Stdio transport (primary MCP transport)
# ---------------------------------------------------------------------------

class StdioTransport(BaseTransport):
    """
    Standard MCP stdio transport.

    Reads JSON-RPC messages from stdin and writes responses to stdout.
    This is the canonical transport for Claude Desktop and Cursor.
    """

    def __init__(self) -> None:
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._running = False

    async def start(self, handler: MessageHandler) -> None:
        loop = asyncio.get_event_loop()

        # Wrap stdin/stdout in asyncio streams
        self._reader = asyncio.StreamReader()
        read_protocol = asyncio.StreamReaderProtocol(self._reader)
        await loop.connect_read_pipe(lambda: read_protocol, sys.stdin.buffer)

        write_transport, write_protocol = await loop.connect_write_pipe(
            asyncio.BaseProtocol, sys.stdout.buffer
        )
        self._writer = asyncio.StreamWriter(write_transport, write_protocol, self._reader, loop)

        self._running = True
        logger.info("StdioTransport started — waiting for messages")

        while self._running:
            try:
                message = await self.read_message(self._reader)
                if message is None:
                    logger.info("EOF on stdin — shutting down")
                    break
                response = handler(message)
                if response is not None:
                    await self.send(response)
            except asyncio.IncompleteReadError:
                logger.info("Stdin closed")
                break
            except json.JSONDecodeError as exc:
                logger.error("JSON parse error: %s", exc)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Unexpected error: %s", exc)

    async def send(self, message: dict) -> None:
        if self._writer is None:
            raise RuntimeError("Transport not started")
        data = self.frame_message(message)
        self._writer.write(data)
        await self._writer.drain()

    async def close(self) -> None:
        self._running = False
        if self._writer:
            self._writer.close()


# ---------------------------------------------------------------------------
# HTTP / SSE transport (remote access)
# ---------------------------------------------------------------------------

class HTTPTransport(BaseTransport):
    """
    HTTP + Server-Sent Events transport for remote MCP access.

    POST /mcp    — send a JSON-RPC request, get a JSON response
    GET  /events — SSE stream for server-initiated notifications
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8765) -> None:
        self.host = host
        self.port = port
        self._handler: Optional[MessageHandler] = None
        self._server = None
        self._sse_queue: asyncio.Queue = asyncio.Queue()

    async def start(self, handler: MessageHandler) -> None:
        try:
            from aiohttp import web  # type: ignore[import]
        except ImportError:
            raise RuntimeError("aiohttp is required for HTTPTransport: pip install aiohttp")

        self._handler = handler
        app = web.Application()
        app.router.add_post("/mcp", self._handle_post)
        app.router.add_get("/events", self._handle_sse)
        app.router.add_get("/health", self._handle_health)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        self._server = runner
        logger.info("HTTPTransport listening on http://%s:%d", self.host, self.port)

    async def _handle_post(self, request):
        from aiohttp import web  # type: ignore[import]
        try:
            data = await request.json()
            response = self._handler(data)
            return web.json_response(response)
        except Exception as exc:
            return web.json_response(
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}},
                status=400,
            )

    async def _handle_sse(self, request):
        from aiohttp import web  # type: ignore[import]
        response = web.StreamResponse(
            headers={"Content-Type": "text/event-stream", "Cache-Control": "no-cache"}
        )
        await response.prepare(request)
        while True:
            msg = await self._sse_queue.get()
            await response.write(f"data: {json.dumps(msg)}\n\n".encode("utf-8"))
        return response

    async def _handle_health(self, request):
        from aiohttp import web  # type: ignore[import]
        return web.json_response({"status": "ok", "server": "SintraPrime MCP"})

    async def send(self, message: dict) -> None:
        await self._sse_queue.put(message)

    async def close(self) -> None:
        if self._server:
            await self._server.cleanup()


# ---------------------------------------------------------------------------
# WebSocket transport
# ---------------------------------------------------------------------------

class WebSocketTransport(BaseTransport):
    """
    WebSocket transport for bidirectional MCP communication.

    Useful for browser-based clients and tools that prefer WebSocket.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8766) -> None:
        self.host = host
        self.port = port
        self._handler: Optional[MessageHandler] = None
        self._server = None

    async def start(self, handler: MessageHandler) -> None:
        try:
            import websockets  # type: ignore[import]
        except ImportError:
            raise RuntimeError("websockets is required: pip install websockets")

        self._handler = handler

        async def _serve(websocket, path):
            async for raw in websocket:
                try:
                    message = json.loads(raw)
                    response = self._handler(message)
                    if response is not None:
                        await websocket.send(json.dumps(response))
                except json.JSONDecodeError as exc:
                    logger.error("WebSocket JSON error: %s", exc)
                except Exception as exc:
                    logger.exception("WebSocket handler error: %s", exc)

        self._server = await websockets.serve(_serve, self.host, self.port)  # type: ignore[attr-defined]
        logger.info("WebSocketTransport listening on ws://%s:%d", self.host, self.port)
        await self._server.wait_closed()

    async def send(self, message: dict) -> None:
        # Broadcast to all connected clients (simplified)
        if self._server:
            raw = json.dumps(message)
            for ws in list(getattr(self._server, "websockets", [])):
                try:
                    await ws.send(raw)
                except Exception:
                    pass

    async def close(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

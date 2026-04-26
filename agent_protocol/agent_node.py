"""A SintraPrime agent node that can join the network."""
from __future__ import annotations

import asyncio
import json
import logging
import socket
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .message_types import AgentCapabilities, AgentMessage, MessageType


class AgentNode:
    """
    A single SintraPrime instance that can:
    1. Announce itself on the local network (mDNS-style via UDP broadcast)
    2. Send/receive messages to/from other nodes
    3. Share knowledge and learn from peers
    4. Delegate tasks to specialized nodes
    5. Join/leave swarms

    Usage
    -----
    ::

        node = AgentNode("sintra-alpha", AgentCapabilities(trust_law=True))

        @node.on(MessageType.LEGAL_QUERY)
        async def handle_legal_query(msg: AgentMessage):
            response = await research(msg.payload["question"])
            await node.send(msg.make_reply(node.agent_id, {"answer": response},
                                           MessageType.LEGAL_RESPONSE))

        await node.start()
    """

    DEFAULT_PORT = 9876
    BROADCAST_ADDR = "255.255.255.255"
    _SEEN_TTL = 60  # seconds to remember a seen message_id

    def __init__(
        self,
        agent_id: str,
        capabilities: AgentCapabilities,
        port: int = DEFAULT_PORT,
        host: str = "0.0.0.0",
    ) -> None:
        self.agent_id = agent_id
        self.capabilities = capabilities
        self.port = port
        self.host = host

        # peer_id -> {addr, port, capabilities, last_seen}
        self.peers: dict[str, dict[str, Any]] = {}

        # message_type -> list of async handler callables
        self.handlers: dict[MessageType, list[Callable]] = {}

        self.running = False
        self.logger = logging.getLogger(f"AgentNode:{agent_id}")

        self.message_history: list[AgentMessage] = []
        self._seen_ids: dict[str, float] = {}   # message_id -> timestamp
        self._pending_replies: dict[str, asyncio.Future] = {}

        self._udp_transport: Optional[asyncio.DatagramTransport] = None
        self._udp_protocol: Optional[_UDPProtocol] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start listening for messages and announce presence."""
        if self.running:
            return
        self.running = True

        loop = asyncio.get_event_loop()

        # Create UDP socket (send + receive)
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: _UDPProtocol(self._on_datagram),
            local_addr=(self.host, self.port),
            allow_broadcast=True,
        )
        self._udp_transport = transport
        self._udp_protocol = protocol

        self.logger.info(
            "AgentNode %s listening on %s:%d", self.agent_id, self.host, self.port
        )

        # Register built-in handlers
        self._register_builtin_handlers()

        # Announce presence
        await self.announce()

        # Background task: periodic heartbeat
        asyncio.ensure_future(self._heartbeat_loop())

    async def stop(self) -> None:
        """Gracefully leave the network."""
        if not self.running:
            return
        self.running = False

        await self._broadcast(
            AgentMessage(
                type=MessageType.GOODBYE,
                sender_id=self.agent_id,
                payload={"reason": "shutdown"},
            )
        )

        if self._udp_transport:
            self._udp_transport.close()

        self.logger.info("AgentNode %s has left the network.", self.agent_id)

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------

    async def announce(self) -> None:
        """Broadcast HELLO to all nodes on the network."""
        msg = AgentMessage(
            type=MessageType.HELLO,
            sender_id=self.agent_id,
            payload={
                "port": self.port,
                "capabilities": self.capabilities.to_dict(),
            },
        )
        await self._broadcast(msg)
        self.logger.debug("Announced presence.")

    async def send(
        self,
        message: AgentMessage,
        target_addr: Optional[tuple[str, int]] = None,
    ) -> None:
        """Send message to a specific node or broadcast.

        Parameters
        ----------
        message:
            The message to send.
        target_addr:
            ``(host, port)`` tuple. If *None* the message is broadcast to the
            LAN and to every known peer individually if unicast is preferable.
        """
        if target_addr:
            await self._send_to(message, target_addr)
        else:
            if message.target_id and message.target_id in self.peers:
                peer = self.peers[message.target_id]
                await self._send_to(message, (peer["addr"], peer["port"]))
            else:
                await self._broadcast(message)

        self.message_history.append(message)

    async def ping(self, peer_id: str, timeout: int = 5) -> Optional[float]:
        """Ping a peer and return round-trip time in ms, or None on timeout."""
        if peer_id not in self.peers:
            return None

        msg = AgentMessage(
            type=MessageType.PING,
            sender_id=self.agent_id,
            payload={"ts": time.time()},
            target_id=peer_id,
        )
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_replies[msg.message_id] = future

        await self.send(msg)
        try:
            reply = await asyncio.wait_for(future, timeout=timeout)
            return (time.time() - reply.payload.get("ts", time.time())) * 1000
        except asyncio.TimeoutError:
            self._pending_replies.pop(msg.message_id, None)
            return None

    async def request_knowledge(
        self, topic: str, timeout: int = 5
    ) -> list[dict]:
        """Ask all peers for knowledge on a topic.

        Broadcasts a REQUEST_KNOWLEDGE message and collects KNOWLEDGE_RESPONSE
        messages from all peers within *timeout* seconds.
        """
        msg = AgentMessage(
            type=MessageType.REQUEST_KNOWLEDGE,
            sender_id=self.agent_id,
            payload={"topic": topic},
        )

        responses: list[dict] = []
        original_id = msg.message_id

        def _collect(reply: AgentMessage) -> None:
            if reply.reply_to == original_id:
                responses.append(reply.payload)

        # Temporarily register collector
        self.handlers.setdefault(MessageType.KNOWLEDGE_RESPONSE, []).append(_collect)

        await self._broadcast(msg)
        await asyncio.sleep(timeout)

        # Remove collector
        try:
            self.handlers[MessageType.KNOWLEDGE_RESPONSE].remove(_collect)
        except ValueError:
            pass

        return responses

    async def delegate_task(
        self, task: dict, required_capability: str
    ) -> Optional[dict]:
        """Delegate a task to the best available agent.

        Parameters
        ----------
        task:
            Task payload dict (must contain at least a ``"type"`` key).
        required_capability:
            Capability string (e.g. ``"trust_law"``).

        Returns
        -------
        dict | None
            The result payload from the accepting agent, or *None* on timeout.
        """
        peer_id = self.get_best_peer_for(required_capability)
        if not peer_id:
            self.logger.warning(
                "No peer found with capability '%s'.", required_capability
            )
            return None

        msg = AgentMessage(
            type=MessageType.DELEGATE_TASK,
            sender_id=self.agent_id,
            payload={"task": task, "required_capability": required_capability},
            target_id=peer_id,
        )

        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_replies[msg.message_id] = future

        await self.send(msg)

        try:
            reply = await asyncio.wait_for(future, timeout=30)
            return reply.payload
        except asyncio.TimeoutError:
            self._pending_replies.pop(msg.message_id, None)
            return None

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def on(self, message_type: MessageType) -> Callable:
        """Decorator to register a message handler.

        ::

            @node.on(MessageType.LEGAL_QUERY)
            async def handle(msg: AgentMessage):
                ...
        """

        def decorator(fn: Callable) -> Callable:
            self.handlers.setdefault(message_type, []).append(fn)
            return fn

        return decorator

    # ------------------------------------------------------------------
    # Peer helpers
    # ------------------------------------------------------------------

    def get_best_peer_for(self, capability: str) -> Optional[str]:
        """Find the best peer for a given capability (by last_seen recency)."""
        candidates = [
            (pid, info)
            for pid, info in self.peers.items()
            if info.get("capabilities", {}).get(capability, False)
        ]
        if not candidates:
            return None
        # Pick the most recently seen
        return max(candidates, key=lambda x: x[1].get("last_seen", 0))[0]

    def known_peers(self) -> list[str]:
        """Return list of known peer agent IDs."""
        return list(self.peers.keys())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _broadcast(self, message: AgentMessage) -> None:
        """Send via UDP broadcast."""
        await self._send_to(message, (self.BROADCAST_ADDR, self.port))

    async def _send_to(self, message: AgentMessage, addr: tuple[str, int]) -> None:
        """Serialize and send a single datagram."""
        if not self._udp_transport:
            return
        data = message.to_json().encode()
        self._udp_transport.sendto(data, addr)

    def _on_datagram(self, data: bytes, addr: tuple[str, int]) -> None:
        """Called by the UDP protocol when a datagram arrives."""
        try:
            msg = AgentMessage.from_json(data.decode())
        except Exception as exc:
            self.logger.debug("Could not parse datagram from %s: %s", addr, exc)
            return

        # Ignore our own messages
        if msg.sender_id == self.agent_id:
            return

        # Deduplicate
        now = time.time()
        self._seen_ids = {
            mid: ts
            for mid, ts in self._seen_ids.items()
            if now - ts < self._SEEN_TTL
        }
        if msg.message_id in self._seen_ids:
            return
        self._seen_ids[msg.message_id] = now

        # Ignore expired messages
        if msg.is_expired():
            return

        # Ignore messages targeted at someone else
        if msg.target_id and msg.target_id != self.agent_id:
            return

        self.logger.debug("Received %s from %s", msg.type.value, msg.sender_id)

        # Resolve pending futures (replies)
        if msg.reply_to and msg.reply_to in self._pending_replies:
            fut = self._pending_replies.pop(msg.reply_to)
            if not fut.done():
                fut.set_result(msg)

        # Dispatch to registered handlers
        asyncio.ensure_future(self._dispatch(msg, addr))

    async def _dispatch(self, msg: AgentMessage, addr: tuple[str, int]) -> None:
        handlers = self.handlers.get(msg.type, [])
        for handler in handlers:
            try:
                result = handler(msg)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:
                self.logger.error(
                    "Handler error for %s: %s", msg.type.value, exc, exc_info=True
                )

    def _register_builtin_handlers(self) -> None:
        """Register protocol-level handlers (HELLO, GOODBYE, PING, PONG)."""

        async def on_hello(msg: AgentMessage) -> None:
            caps = AgentCapabilities.from_dict(
                msg.payload.get("capabilities", {})
            )
            self.peers[msg.sender_id] = {
                "addr": msg.payload.get("addr", "unknown"),
                "port": msg.payload.get("port", self.DEFAULT_PORT),
                "capabilities": msg.payload.get("capabilities", {}),
                "caps_obj": caps,
                "last_seen": time.time(),
            }
            self.logger.info("Peer joined: %s (caps=%s)", msg.sender_id, caps.list_active())
            # Reply with our own HELLO so they know us
            reply = AgentMessage(
                type=MessageType.HELLO,
                sender_id=self.agent_id,
                payload={
                    "port": self.port,
                    "capabilities": self.capabilities.to_dict(),
                },
                target_id=msg.sender_id,
            )
            await self.send(reply)

        async def on_goodbye(msg: AgentMessage) -> None:
            self.peers.pop(msg.sender_id, None)
            self.logger.info("Peer left: %s", msg.sender_id)

        async def on_ping(msg: AgentMessage) -> None:
            pong = msg.make_reply(
                self.agent_id,
                {"ts": msg.payload.get("ts", time.time())},
                MessageType.PONG,
            )
            await self.send(pong)

        self.handlers.setdefault(MessageType.HELLO, []).insert(0, on_hello)
        self.handlers.setdefault(MessageType.GOODBYE, []).insert(0, on_goodbye)
        self.handlers.setdefault(MessageType.PING, []).insert(0, on_ping)

    async def _heartbeat_loop(self) -> None:
        """Periodically announce presence and prune stale peers."""
        while self.running:
            await asyncio.sleep(30)
            if not self.running:
                break
            await self.announce()
            # Prune peers not seen in 90 seconds
            now = time.time()
            stale = [
                pid
                for pid, info in self.peers.items()
                if now - info.get("last_seen", 0) > 90
            ]
            for pid in stale:
                self.logger.info("Pruning stale peer: %s", pid)
                del self.peers[pid]


class _UDPProtocol(asyncio.DatagramProtocol):
    """Asyncio UDP protocol adapter."""

    def __init__(self, callback: Callable[[bytes, tuple], None]) -> None:
        self._callback = callback
        self._transport: Optional[asyncio.DatagramTransport] = None

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        self._transport = transport

    def datagram_received(self, data: bytes, addr: tuple) -> None:
        self._callback(data, addr)

    def error_received(self, exc: Exception) -> None:
        logging.getLogger("_UDPProtocol").warning("UDP error: %s", exc)

"""
a2a_protocol.py
===============
Agent-to-Agent (A2A) Communication Protocol for SintraPrime-Unified.

Provides standardized message envelopes, an in-memory message bus with
pub/sub and priority queuing, agent registry, and capability advertisement.
"""

from __future__ import annotations

import asyncio
import heapq
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MessageType(str, Enum):
    REQUEST = "REQUEST"
    RESPONSE = "RESPONSE"
    BROADCAST = "BROADCAST"
    DELEGATION = "DELEGATION"
    RESULT = "RESULT"
    ERROR = "ERROR"
    HEARTBEAT = "HEARTBEAT"
    HANDSHAKE = "HANDSHAKE"
    CAPABILITY_ADV = "CAPABILITY_ADV"


class Priority(IntEnum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3

    @classmethod
    def from_str(cls, s: str) -> "Priority":
        mapping = {
            "low": cls.LOW,
            "normal": cls.NORMAL,
            "high": cls.HIGH,
            "critical": cls.CRITICAL,
        }
        return mapping.get(s.lower(), cls.NORMAL)


class AgentStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    IDLE = "idle"


# ---------------------------------------------------------------------------
# Message Envelope
# ---------------------------------------------------------------------------

@dataclass
class Message:
    """
    Standardized A2A message envelope.

    Fields
    ------
    from_agent     : sender agent ID
    to_agent       : recipient agent ID or '*' for broadcast
    message_type   : one of MessageType
    payload        : arbitrary dict payload
    correlation_id : links request/response pairs
    timestamp      : unix epoch float
    priority       : Priority enum value
    message_id     : globally unique ID for this message
    ttl            : time-to-live in seconds (None = no expiry)
    headers        : optional extensible metadata
    """
    from_agent: str
    to_agent: str
    message_type: MessageType
    payload: Dict[str, Any]
    correlation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: float = field(default_factory=time.time)
    priority: Priority = Priority.NORMAL
    message_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    ttl: Optional[float] = None
    headers: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        return (time.time() - self.timestamp) > self.ttl

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "message_type": self.message_type.value,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "priority": self.priority.value,
            "ttl": self.ttl,
            "headers": self.headers,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        return cls(
            message_id=data.get("message_id", uuid.uuid4().hex),
            from_agent=data["from_agent"],
            to_agent=data["to_agent"],
            message_type=MessageType(data["message_type"]),
            payload=data.get("payload", {}),
            correlation_id=data.get("correlation_id", uuid.uuid4().hex),
            timestamp=data.get("timestamp", time.time()),
            priority=Priority(data.get("priority", Priority.NORMAL)),
            ttl=data.get("ttl"),
            headers=data.get("headers", {}),
        )

    # Comparison for heap queue (higher priority = lower heap value)
    def __lt__(self, other: "Message") -> bool:
        if self.priority != other.priority:
            return self.priority > other.priority  # higher priority first
        return self.timestamp < other.timestamp  # earlier first if equal priority


# ---------------------------------------------------------------------------
# Priority Message Queue
# ---------------------------------------------------------------------------

class PriorityMessageQueue:
    """
    Thread-safe priority queue for A2A messages.
    Ordering: CRITICAL > HIGH > NORMAL > LOW; ties broken by timestamp.
    """

    def __init__(self, maxsize: int = 1000) -> None:
        self._heap: List[Message] = []
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Event()
        self.maxsize = maxsize

    async def put(self, msg: Message) -> None:
        async with self._lock:
            if len(self._heap) >= self.maxsize:
                raise RuntimeError("Message queue is full")
            heapq.heappush(self._heap, msg)
            self._not_empty.set()

    async def get(self, timeout: Optional[float] = None) -> Optional[Message]:
        deadline = time.time() + timeout if timeout else None
        while True:
            async with self._lock:
                while self._heap:
                    msg = heapq.heappop(self._heap)
                    if not msg.is_expired():
                        if not self._heap:
                            self._not_empty.clear()
                        return msg
                    logger.debug("Dropped expired message %s", msg.message_id)
                self._not_empty.clear()

            if deadline and time.time() >= deadline:
                return None
            try:
                remaining = deadline - time.time() if deadline else 5.0
                await asyncio.wait_for(self._not_empty.wait(), timeout=max(0.01, remaining))
            except asyncio.TimeoutError:
                return None

    def size(self) -> int:
        return len(self._heap)

    def empty(self) -> bool:
        return len(self._heap) == 0


# ---------------------------------------------------------------------------
# Agent Descriptor
# ---------------------------------------------------------------------------

@dataclass
class AgentDescriptor:
    """Describes an agent's identity and capabilities."""
    agent_id: str
    name: str
    capabilities: List[str]
    status: AgentStatus = AgentStatus.IDLE
    endpoint: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "capabilities": self.capabilities,
            "status": self.status.value,
            "endpoint": self.endpoint,
            "metadata": self.metadata,
            "registered_at": self.registered_at,
            "last_seen": self.last_seen,
        }

    def touch(self) -> None:
        self.last_seen = time.time()


# ---------------------------------------------------------------------------
# Agent Registry
# ---------------------------------------------------------------------------

class AgentRegistry:
    """Central registry for agent discovery and capability lookup."""

    def __init__(self) -> None:
        self._agents: Dict[str, AgentDescriptor] = {}
        self._capability_index: Dict[str, Set[str]] = {}  # cap -> set of agent_ids

    def register(self, descriptor: AgentDescriptor) -> None:
        self._agents[descriptor.agent_id] = descriptor
        for cap in descriptor.capabilities:
            self._capability_index.setdefault(cap, set()).add(descriptor.agent_id)
        logger.info("Agent registered: %s (%s)", descriptor.agent_id, descriptor.name)

    def deregister(self, agent_id: str) -> bool:
        desc = self._agents.pop(agent_id, None)
        if desc is None:
            return False
        for cap in desc.capabilities:
            self._capability_index.get(cap, set()).discard(agent_id)
        logger.info("Agent deregistered: %s", agent_id)
        return True

    def get(self, agent_id: str) -> Optional[AgentDescriptor]:
        return self._agents.get(agent_id)

    def find_by_capability(self, capability: str) -> List[AgentDescriptor]:
        ids = self._capability_index.get(capability, set())
        return [self._agents[aid] for aid in ids if aid in self._agents]

    def find_online(self) -> List[AgentDescriptor]:
        return [
            d for d in self._agents.values()
            if d.status in (AgentStatus.ONLINE, AgentStatus.IDLE)
        ]

    def all_agents(self) -> List[AgentDescriptor]:
        return list(self._agents.values())

    def update_status(self, agent_id: str, status: AgentStatus) -> bool:
        desc = self._agents.get(agent_id)
        if not desc:
            return False
        desc.status = status
        desc.touch()
        return True

    def heartbeat(self, agent_id: str) -> bool:
        desc = self._agents.get(agent_id)
        if not desc:
            return False
        desc.touch()
        return True


# ---------------------------------------------------------------------------
# Subscription Record
# ---------------------------------------------------------------------------

@dataclass
class Subscription:
    sub_id: str
    agent_id: str
    topic: str
    handler: Callable[[Message], Any]
    filter_types: Optional[List[MessageType]] = None

    def matches(self, msg: Message) -> bool:
        if self.filter_types and msg.message_type not in self.filter_types:
            return False
        return True


# ---------------------------------------------------------------------------
# Message Bus
# ---------------------------------------------------------------------------

class MessageBus:
    """
    In-memory message bus with pub/sub and direct messaging.

    - Direct messages are routed to the target agent's queue.
    - Broadcast messages are delivered to all subscribers of a topic.
    - Supports async handler callbacks via pub/sub subscriptions.
    """

    BROADCAST_TOPIC = "*"

    def __init__(self) -> None:
        self._queues: Dict[str, PriorityMessageQueue] = {}
        self._subscriptions: Dict[str, List[Subscription]] = {}  # topic -> subs
        self._message_log: List[Message] = []
        self._max_log_size = 10000
        self._lock = asyncio.Lock()

    def _agent_queue(self, agent_id: str) -> PriorityMessageQueue:
        if agent_id not in self._queues:
            self._queues[agent_id] = PriorityMessageQueue()
        return self._queues[agent_id]

    async def publish(self, msg: Message) -> None:
        """Publish a message to the bus."""
        async with self._lock:
            if len(self._message_log) >= self._max_log_size:
                self._message_log.pop(0)
            self._message_log.append(msg)

        if msg.message_type == MessageType.BROADCAST or msg.to_agent == self.BROADCAST_TOPIC:
            await self._broadcast(msg)
        else:
            await self._deliver(msg)

    async def _deliver(self, msg: Message) -> None:
        """Deliver a direct message to the target agent queue."""
        queue = self._agent_queue(msg.to_agent)
        await queue.put(msg)
        await self._notify_subscribers(msg.to_agent, msg)
        logger.debug("Delivered msg %s to agent %s", msg.message_id, msg.to_agent)

    async def _broadcast(self, msg: Message) -> None:
        """Deliver message to all agents (except sender)."""
        for agent_id, queue in self._queues.items():
            if agent_id != msg.from_agent:
                await queue.put(msg)
        await self._notify_subscribers(self.BROADCAST_TOPIC, msg)
        logger.debug("Broadcast msg %s from agent %s", msg.message_id, msg.from_agent)

    async def _notify_subscribers(self, topic: str, msg: Message) -> None:
        subs = self._subscriptions.get(topic, [])
        for sub in subs:
            if sub.matches(msg):
                try:
                    if asyncio.iscoroutinefunction(sub.handler):
                        asyncio.create_task(sub.handler(msg))
                    else:
                        sub.handler(msg)
                except Exception as exc:
                    logger.error("Subscriber %s handler error: %s", sub.sub_id, exc)

    async def receive(self, agent_id: str, timeout: Optional[float] = 5.0) -> Optional[Message]:
        """Receive the next message for agent_id (blocks up to timeout)."""
        queue = self._agent_queue(agent_id)
        return await queue.get(timeout=timeout)

    def subscribe(
        self,
        agent_id: str,
        topic: str,
        handler: Callable[[Message], Any],
        filter_types: Optional[List[MessageType]] = None,
    ) -> str:
        """Subscribe agent to a topic. Returns subscription ID."""
        sub_id = uuid.uuid4().hex
        sub = Subscription(sub_id=sub_id, agent_id=agent_id, topic=topic, handler=handler, filter_types=filter_types)
        self._subscriptions.setdefault(topic, []).append(sub)
        return sub_id

    def unsubscribe(self, sub_id: str) -> bool:
        for topic, subs in self._subscriptions.items():
            for sub in subs:
                if sub.sub_id == sub_id:
                    self._subscriptions[topic].remove(sub)
                    return True
        return False

    def pending_count(self, agent_id: str) -> int:
        q = self._queues.get(agent_id)
        return q.size() if q else 0

    def message_log(self, limit: int = 100) -> List[Message]:
        return self._message_log[-limit:]


# ---------------------------------------------------------------------------
# A2A Client (per-agent interface)
# ---------------------------------------------------------------------------

class A2AClient:
    """
    Per-agent interface to the A2A message bus.
    Handles handshake, messaging, and capability advertisement.
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        capabilities: List[str],
        bus: MessageBus,
        registry: AgentRegistry,
    ) -> None:
        self.agent_id = agent_id
        self.name = name
        self.capabilities = capabilities
        self._bus = bus
        self._registry = registry
        self._descriptor = AgentDescriptor(
            agent_id=agent_id,
            name=name,
            capabilities=capabilities,
        )
        self._registry.register(self._descriptor)
        # Pre-create queue so this agent receives broadcasts
        self._bus._agent_queue(agent_id)

    async def handshake(self, target_agent_id: str) -> Message:
        """Initiate a handshake with another agent."""
        msg = Message(
            from_agent=self.agent_id,
            to_agent=target_agent_id,
            message_type=MessageType.HANDSHAKE,
            payload={
                "agent_id": self.agent_id,
                "name": self.name,
                "capabilities": self.capabilities,
            },
            priority=Priority.HIGH,
        )
        await self._bus.publish(msg)
        logger.info("Handshake sent from %s to %s", self.agent_id, target_agent_id)
        return msg

    async def advertise_capabilities(self) -> Message:
        """Broadcast capability advertisement."""
        msg = Message(
            from_agent=self.agent_id,
            to_agent=MessageBus.BROADCAST_TOPIC,
            message_type=MessageType.CAPABILITY_ADV,
            payload={
                "agent_id": self.agent_id,
                "name": self.name,
                "capabilities": self.capabilities,
            },
            priority=Priority.NORMAL,
        )
        await self._bus.publish(msg)
        return msg

    async def send_request(
        self,
        to_agent: str,
        payload: Dict[str, Any],
        priority: Priority = Priority.NORMAL,
        ttl: Optional[float] = None,
    ) -> str:
        """Send a REQUEST message. Returns correlation_id."""
        msg = Message(
            from_agent=self.agent_id,
            to_agent=to_agent,
            message_type=MessageType.REQUEST,
            payload=payload,
            priority=priority,
            ttl=ttl,
        )
        await self._bus.publish(msg)
        return msg.correlation_id

    async def send_response(
        self,
        to_agent: str,
        payload: Dict[str, Any],
        correlation_id: str,
        priority: Priority = Priority.NORMAL,
    ) -> None:
        """Send a RESPONSE message linked to a correlation_id."""
        msg = Message(
            from_agent=self.agent_id,
            to_agent=to_agent,
            message_type=MessageType.RESPONSE,
            payload=payload,
            correlation_id=correlation_id,
            priority=priority,
        )
        await self._bus.publish(msg)

    async def delegate(
        self,
        to_agent: str,
        task: Dict[str, Any],
        priority: Priority = Priority.NORMAL,
    ) -> str:
        """Delegate a task to another agent. Returns correlation_id."""
        msg = Message(
            from_agent=self.agent_id,
            to_agent=to_agent,
            message_type=MessageType.DELEGATION,
            payload=task,
            priority=priority,
        )
        await self._bus.publish(msg)
        return msg.correlation_id

    async def broadcast(self, payload: Dict[str, Any]) -> None:
        """Broadcast a message to all agents."""
        msg = Message(
            from_agent=self.agent_id,
            to_agent=MessageBus.BROADCAST_TOPIC,
            message_type=MessageType.BROADCAST,
            payload=payload,
        )
        await self._bus.publish(msg)

    async def send_error(
        self,
        to_agent: str,
        error: str,
        correlation_id: Optional[str] = None,
        priority: Priority = Priority.HIGH,
    ) -> None:
        """Send an ERROR message."""
        msg = Message(
            from_agent=self.agent_id,
            to_agent=to_agent,
            message_type=MessageType.ERROR,
            payload={"error": error},
            correlation_id=correlation_id or uuid.uuid4().hex,
            priority=priority,
        )
        await self._bus.publish(msg)

    async def receive(self, timeout: float = 5.0) -> Optional[Message]:
        """Receive next message addressed to this agent."""
        return await self._bus.receive(self.agent_id, timeout=timeout)

    def pending_count(self) -> int:
        return self._bus.pending_count(self.agent_id)

    def go_online(self) -> None:
        self._registry.update_status(self.agent_id, AgentStatus.ONLINE)

    def go_offline(self) -> None:
        self._registry.update_status(self.agent_id, AgentStatus.OFFLINE)

    def set_busy(self) -> None:
        self._registry.update_status(self.agent_id, AgentStatus.BUSY)

    def set_idle(self) -> None:
        self._registry.update_status(self.agent_id, AgentStatus.IDLE)

    def find_agents_with_capability(self, capability: str) -> List[AgentDescriptor]:
        return self._registry.find_by_capability(capability)


# ---------------------------------------------------------------------------
# A2A Protocol factory
# ---------------------------------------------------------------------------

class A2AProtocol:
    """Top-level coordinator for the A2A ecosystem."""

    def __init__(self) -> None:
        self.bus = MessageBus()
        self.registry = AgentRegistry()

    def create_client(
        self,
        agent_id: str,
        name: str,
        capabilities: Optional[List[str]] = None,
    ) -> A2AClient:
        return A2AClient(
            agent_id=agent_id,
            name=name,
            capabilities=capabilities or [],
            bus=self.bus,
            registry=self.registry,
        )

    def get_all_agents(self) -> List[AgentDescriptor]:
        return self.registry.all_agents()

    def message_log(self, limit: int = 100) -> List[Message]:
        return self.bus.message_log(limit=limit)

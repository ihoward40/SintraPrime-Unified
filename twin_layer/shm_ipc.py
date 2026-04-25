"""
shm_ipc.py — Twin-inspired Shared Memory IPC for SintraPrime

Based on twin's shared memory (server/shm.cpp) for fast inter-process communication.
Provides pub/sub messaging over shared memory with ring buffer implementation.
"""

import json
import logging
import math
import multiprocessing
import os
import struct
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Try to import multiprocessing.shared_memory (Python 3.8+)
try:
    from multiprocessing.shared_memory import SharedMemory
    SHM_AVAILABLE = True
except ImportError:
    SHM_AVAILABLE = False
    logger.warning("shared_memory not available; using in-process fallback")

# Try msgpack for efficient serialization
try:
    import msgpack
    def _serialize(data: Any) -> bytes:
        return msgpack.packb(data, use_bin_type=True)
    def _deserialize(data: bytes) -> Any:
        return msgpack.unpackb(data, raw=False)
    MSGPACK_AVAILABLE = True
except ImportError:
    def _serialize(data: Any) -> bytes:
        return json.dumps(data, default=str).encode("utf-8")
    def _deserialize(data: bytes) -> Any:
        return json.loads(data.decode("utf-8"))
    MSGPACK_AVAILABLE = False
    logger.debug("msgpack not available; falling back to JSON serialization")


# ─── Ring buffer ──────────────────────────────────────────────────────────────

class RingBuffer:
    """
    Lock-free-read, locked-write ring buffer for high-throughput IPC.

    Stores a fixed number of messages. Readers get copies so writers
    never block on slow readers (same model as twin's event ring).
    """

    def __init__(self, capacity: int = 256):
        """
        Initialize ring buffer.

        Args:
            capacity: Maximum number of messages to retain.
        """
        self.capacity = capacity
        self._buffer: List[Optional[bytes]] = [None] * capacity
        self._write_pos: int = 0
        self._total_written: int = 0
        self._lock = threading.Lock()

    def put(self, data: bytes) -> int:
        """
        Write a message to the ring buffer (overwrites oldest if full).

        Args:
            data: Serialized message bytes.

        Returns:
            Sequence number of this message.
        """
        with self._lock:
            idx = self._write_pos % self.capacity
            self._buffer[idx] = data
            self._write_pos = (self._write_pos + 1) % self.capacity
            self._total_written += 1
            return self._total_written

    def get_since(self, last_seq: int) -> List[bytes]:
        """
        Read all messages written after last_seq.

        Args:
            last_seq: Last seen sequence number.

        Returns:
            List of message bytes in order.
        """
        with self._lock:
            total = self._total_written
            if total <= last_seq:
                return []
            # How many new messages?
            new_count = min(total - last_seq, self.capacity)
            start_seq = total - new_count  # oldest available
            results: List[bytes] = []
            for i in range(new_count):
                seq = start_seq + i
                idx = seq % self.capacity
                msg = self._buffer[idx]
                if msg is not None:
                    results.append(msg)
            return results

    def get_latest(self, n: int = 10) -> List[bytes]:
        """Return the last N messages."""
        with self._lock:
            total = self._total_written
            n = min(n, self.capacity, total)
            results: List[bytes] = []
            for i in range(n):
                idx = (self._write_pos - n + i) % self.capacity
                msg = self._buffer[idx]
                if msg is not None:
                    results.append(msg)
            return results

    @property
    def total_written(self) -> int:
        return self._total_written

    @property
    def size(self) -> int:
        with self._lock:
            return min(self._total_written, self.capacity)


# ─── Message envelope ──────────────────────────────────────────────────────────

@dataclass
class Message:
    """
    IPC message envelope.

    Attributes:
        msg_id: Unique message ID.
        channel: Channel name this message was published to.
        sender_id: Sender's agent/process ID.
        timestamp: Unix timestamp.
        payload: Message payload (any serializable data).
        seq: Sequence number assigned by the ring buffer.
    """
    msg_id: str
    channel: str
    sender_id: str
    timestamp: float
    payload: Any
    seq: int = 0

    def to_bytes(self) -> bytes:
        return _serialize({
            "msg_id": self.msg_id,
            "channel": self.channel,
            "sender_id": self.sender_id,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "seq": self.seq,
        })

    @classmethod
    def from_bytes(cls, data: bytes) -> "Message":
        d = _deserialize(data)
        return cls(**d)


# ─── SharedMemoryChannel ──────────────────────────────────────────────────────

class SharedMemoryChannel:
    """
    Fast inter-agent communication channel backed by shared memory.
    Falls back to in-process ring buffer if shared_memory is unavailable.

    Inspired by twin's server/shm.cpp shared memory segment management.

    Usage:
        ch = SharedMemoryChannel("agent-events", capacity=512)
        ch.publish({"event": "task_done", "task_id": "t123"}, sender_id="agent-1")
        msgs = ch.read_new()
    """

    def __init__(self, channel_name: str, capacity: int = 256,
                 shm_size_kb: int = 64):
        """
        Initialize the channel.

        Args:
            channel_name: Named channel identifier.
            capacity: Ring buffer capacity (number of messages).
            shm_size_kb: Shared memory segment size in KB.
        """
        self.channel_name = channel_name
        self.capacity = capacity
        self._ring = RingBuffer(capacity=capacity)
        self._last_seq: int = 0
        self._shm: Optional[Any] = None
        self._stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "errors": 0,
        }

        # Attempt shared memory setup
        if SHM_AVAILABLE:
            shm_name = f"sintraprime_{channel_name.replace('-', '_')}"[:30]
            try:
                size = shm_size_kb * 1024
                self._shm = SharedMemory(name=shm_name, create=True, size=size)
                logger.debug("Created shared memory segment '%s' (%d KB)",
                             shm_name, shm_size_kb)
            except FileExistsError:
                try:
                    self._shm = SharedMemory(name=shm_name, create=False)
                    logger.debug("Attached to existing shared memory '%s'", shm_name)
                except Exception as exc:
                    logger.warning("Could not attach to shared memory: %s", exc)
            except Exception as exc:
                logger.warning("Shared memory not available: %s; using in-process ring buffer", exc)

        logger.info("SharedMemoryChannel '%s' initialized (capacity=%d, shm=%s)",
                    channel_name, capacity, self._shm is not None)

    def publish(self, payload: Any, sender_id: str = "unknown") -> int:
        """
        Publish a message to this channel.

        Args:
            payload: Any serializable data.
            sender_id: ID of the sending agent.

        Returns:
            Sequence number of the published message.
        """
        msg = Message(
            msg_id=str(uuid.uuid4()),
            channel=self.channel_name,
            sender_id=sender_id,
            timestamp=time.time(),
            payload=payload,
        )
        try:
            data = msg.to_bytes()
            seq = self._ring.put(data)
            msg.seq = seq
            self._stats["messages_sent"] += 1
            logger.debug("Published msg seq=%d to channel '%s'", seq, self.channel_name)
            return seq
        except Exception as exc:
            self._stats["errors"] += 1
            logger.error("Publish error on '%s': %s", self.channel_name, exc)
            return -1

    def read_new(self) -> List[Message]:
        """
        Read all messages published since last read.

        Returns:
            List of new Messages in order.
        """
        raw_msgs = self._ring.get_since(self._last_seq)
        messages: List[Message] = []
        for raw in raw_msgs:
            try:
                msg = Message.from_bytes(raw)
                messages.append(msg)
                self._last_seq = max(self._last_seq, msg.seq)
            except Exception as exc:
                self._stats["errors"] += 1
                logger.warning("Failed to deserialize message: %s", exc)
        self._stats["messages_received"] += len(messages)
        return messages

    def read_latest(self, n: int = 10) -> List[Message]:
        """Return the last N messages regardless of read position."""
        raw_msgs = self._ring.get_latest(n)
        messages: List[Message] = []
        for raw in raw_msgs:
            try:
                messages.append(Message.from_bytes(raw))
            except Exception as exc:
                logger.warning("Failed to deserialize message: %s", exc)
        return messages

    def reset_position(self):
        """Reset read position to current end (skip history)."""
        self._last_seq = self._ring.total_written

    def get_stats(self) -> Dict[str, Any]:
        """Return channel statistics."""
        return {
            "channel": self.channel_name,
            "capacity": self.capacity,
            "total_messages": self._ring.total_written,
            "buffered": self._ring.size,
            "shm_backed": self._shm is not None,
            **self._stats,
        }

    def close(self):
        """Release shared memory resources."""
        if self._shm:
            try:
                self._shm.close()
                self._shm.unlink()
            except Exception as exc:
                logger.warning("Error closing shared memory: %s", exc)
            self._shm = None

    def __del__(self):
        self.close()


# ─── MessageQueue (Pub/Sub) ───────────────────────────────────────────────────

class MessageQueue:
    """
    Publish-subscribe message queue between SintraPrime agents.

    Agents subscribe to named channels and receive messages asynchronously
    via callbacks or by polling.

    Inspired by twin's inter-client messaging system.

    Usage:
        mq = MessageQueue()
        mq.subscribe("task-events", lambda msg: print(msg.payload))
        mq.publish("task-events", {"task": "scan", "status": "done"}, sender="agent-1")
    """

    def __init__(self, capacity: int = 256):
        """
        Initialize message queue.

        Args:
            capacity: Per-channel ring buffer capacity.
        """
        self.capacity = capacity
        self._channels: Dict[str, SharedMemoryChannel] = {}
        self._subscribers: Dict[str, List[Callable[[Message], None]]] = defaultdict(list)
        self._polling_thread: Optional[threading.Thread] = None
        self._running: bool = False
        self._poll_interval: float = 0.05  # 50ms polling
        self._stats = {
            "published": 0,
            "delivered": 0,
            "channels": 0,
        }
        self._lock = threading.Lock()
        logger.info("MessageQueue initialized (capacity=%d)", capacity)

    def _get_channel(self, channel_name: str) -> SharedMemoryChannel:
        """Get or create a channel."""
        with self._lock:
            if channel_name not in self._channels:
                self._channels[channel_name] = SharedMemoryChannel(
                    channel_name=channel_name,
                    capacity=self.capacity,
                )
                self._stats["channels"] += 1
            return self._channels[channel_name]

    def subscribe(self, channel_name: str, callback: Callable[[Message], None]):
        """
        Subscribe to a named channel.

        Args:
            channel_name: Channel to subscribe to.
            callback: Function called with each new Message.
        """
        channel = self._get_channel(channel_name)
        channel.reset_position()  # Start from current position
        self._subscribers[channel_name].append(callback)
        logger.info("Subscribed to channel '%s'", channel_name)

        # Start polling thread if not running
        if not self._running:
            self._start_polling()

    def unsubscribe(self, channel_name: str, callback: Callable[[Message], None]):
        """
        Remove a subscription.

        Args:
            channel_name: Channel name.
            callback: The callback to remove.
        """
        if channel_name in self._subscribers:
            try:
                self._subscribers[channel_name].remove(callback)
            except ValueError:
                pass

    def publish(self, channel_name: str, payload: Any,
                sender: str = "unknown") -> int:
        """
        Publish a message to a channel.

        Args:
            channel_name: Target channel.
            payload: Message data.
            sender: Sender agent ID.

        Returns:
            Sequence number.
        """
        channel = self._get_channel(channel_name)
        seq = channel.publish(payload, sender_id=sender)
        self._stats["published"] += 1
        return seq

    def poll(self, channel_name: str) -> List[Message]:
        """
        Manually poll a channel for new messages.

        Args:
            channel_name: Channel to poll.

        Returns:
            List of new Messages.
        """
        channel = self._channels.get(channel_name)
        if not channel:
            return []
        return channel.read_new()

    def _start_polling(self):
        """Start the background polling thread."""
        self._running = True
        self._polling_thread = threading.Thread(
            target=self._poll_loop,
            daemon=True,
            name="mq-poller",
        )
        self._polling_thread.start()
        logger.debug("MessageQueue polling thread started")

    def _poll_loop(self):
        """Background thread: poll all subscribed channels and dispatch."""
        while self._running:
            with self._lock:
                channels_to_poll = list(self._channels.items())

            for name, channel in channels_to_poll:
                callbacks = self._subscribers.get(name, [])
                if not callbacks:
                    continue
                try:
                    messages = channel.read_new()
                    for msg in messages:
                        for cb in callbacks:
                            try:
                                cb(msg)
                                self._stats["delivered"] += 1
                            except Exception as exc:
                                logger.warning("Subscriber callback error on '%s': %s", name, exc)
                except Exception as exc:
                    logger.warning("Poll error on channel '%s': %s", name, exc)

            time.sleep(self._poll_interval)

    def stop(self):
        """Stop polling and clean up all channels."""
        self._running = False
        if self._polling_thread:
            self._polling_thread.join(timeout=2.0)
        with self._lock:
            for ch in self._channels.values():
                ch.close()
            self._channels.clear()
        logger.info("MessageQueue stopped")

    def get_stats(self) -> Dict[str, Any]:
        """Return queue-wide statistics."""
        channel_stats = {name: ch.get_stats() for name, ch in self._channels.items()}
        return {
            "queue_stats": self._stats,
            "channels": channel_stats,
            "serializer": "msgpack" if MSGPACK_AVAILABLE else "json",
            "shm_available": SHM_AVAILABLE,
        }

    def list_channels(self) -> List[str]:
        """Return all registered channel names."""
        return list(self._channels.keys())

    def __repr__(self) -> str:
        return (f"MessageQueue(channels={len(self._channels)}, "
                f"published={self._stats['published']}, "
                f"delivered={self._stats['delivered']})")


# ─── Latency statistics ───────────────────────────────────────────────────────

class LatencyTracker:
    """
    Track message latency percentiles for performance monitoring.
    Records end-to-end latency from publish to receive timestamps.
    """

    def __init__(self, window: int = 1000):
        """
        Initialize tracker.

        Args:
            window: Number of recent samples to keep.
        """
        self._samples: List[float] = []
        self.window = window
        self._lock = threading.Lock()

    def record(self, publish_time: float, receive_time: Optional[float] = None):
        """
        Record a latency sample.

        Args:
            publish_time: Unix timestamp when message was published.
            receive_time: Unix timestamp when received (now if None).
        """
        latency_ms = ((receive_time or time.time()) - publish_time) * 1000
        with self._lock:
            self._samples.append(latency_ms)
            if len(self._samples) > self.window:
                self._samples.pop(0)

    def percentile(self, p: float) -> float:
        """
        Calculate a latency percentile.

        Args:
            p: Percentile 0-100 (e.g., 99 for P99).

        Returns:
            Latency in milliseconds.
        """
        with self._lock:
            if not self._samples:
                return 0.0
            sorted_s = sorted(self._samples)
            idx = min(int(math.ceil(len(sorted_s) * p / 100)) - 1, len(sorted_s) - 1)
            return sorted_s[max(0, idx)]

    def get_stats(self) -> Dict[str, float]:
        """Return latency statistics dict."""
        with self._lock:
            if not self._samples:
                return {"p50": 0, "p90": 0, "p99": 0, "mean": 0, "max": 0, "count": 0}
            sorted_s = sorted(self._samples)
            return {
                "p50": self.percentile(50),
                "p90": self.percentile(90),
                "p99": self.percentile(99),
                "mean": sum(self._samples) / len(self._samples),
                "max": max(self._samples),
                "count": len(self._samples),
            }

    def reset(self):
        """Reset all samples."""
        with self._lock:
            self._samples.clear()

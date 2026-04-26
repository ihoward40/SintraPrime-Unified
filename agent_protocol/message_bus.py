"""In-process message bus for local pub/sub between agent modules."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Optional

from .message_types import AgentMessage, MessageType


class MessageBus:
    """
    Local asynchronous message bus.

    Allows different parts of a SintraPrime instance to communicate via
    publish/subscribe without needing direct object references.

    Unlike :class:`AgentNode`, this bus is **local only** — it does not
    send messages over the network.  Use it to decouple modules within a
    single process.

    Usage
    -----
    ::

        bus = MessageBus()

        @bus.subscribe(MessageType.LEGAL_QUERY)
        async def handle_query(msg: AgentMessage):
            ...

        await bus.publish(AgentMessage(
            type=MessageType.LEGAL_QUERY,
            sender_id="trust_law",
            payload={"question": "Is this valid?"},
        ))
    """

    def __init__(self) -> None:
        self._subscribers: dict[MessageType, list[Callable]] = {}
        self._wildcard_subscribers: list[Callable] = []
        self._queue: asyncio.Queue[AgentMessage] = asyncio.Queue()
        self._running = False
        self.logger = logging.getLogger("MessageBus")

    # ------------------------------------------------------------------
    # Subscription
    # ------------------------------------------------------------------

    def subscribe(
        self,
        message_type: Optional[MessageType] = None,
    ) -> Callable:
        """
        Decorator to subscribe to a specific message type (or all types if
        *message_type* is None).

        ::

            @bus.subscribe(MessageType.TASK_RESULT)
            async def on_result(msg): ...

            @bus.subscribe()   # receives every message
            async def on_any(msg): ...
        """

        def decorator(fn: Callable) -> Callable:
            if message_type is None:
                self._wildcard_subscribers.append(fn)
            else:
                self._subscribers.setdefault(message_type, []).append(fn)
            return fn

        return decorator

    def unsubscribe(
        self,
        fn: Callable,
        message_type: Optional[MessageType] = None,
    ) -> None:
        """Remove a previously registered subscriber."""
        if message_type is None:
            try:
                self._wildcard_subscribers.remove(fn)
            except ValueError:
                pass
        else:
            handlers = self._subscribers.get(message_type, [])
            try:
                handlers.remove(fn)
            except ValueError:
                pass

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def publish(self, message: AgentMessage) -> None:
        """
        Publish a message to all matching subscribers.

        Delivers the message immediately (not queued) to all registered
        handlers for its type plus wildcard subscribers.
        """
        handlers = list(self._subscribers.get(message.type, []))
        handlers += self._wildcard_subscribers

        for handler in handlers:
            try:
                result = handler(message)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:
                self.logger.error(
                    "Subscriber error for %s: %s", message.type.value, exc,
                    exc_info=True,
                )

    async def enqueue(self, message: AgentMessage) -> None:
        """
        Queue a message for background processing.

        Use when you want fire-and-forget semantics (caller does not wait
        for handlers to complete).
        """
        await self._queue.put(message)

    # ------------------------------------------------------------------
    # Background worker
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start background queue processor."""
        self._running = True
        asyncio.ensure_future(self._process_queue())

    async def stop(self) -> None:
        """Stop background queue processor."""
        self._running = False
        # Unblock the queue
        await self._queue.put(
            AgentMessage(
                type=MessageType.GOODBYE,
                sender_id="__bus__",
                payload={},
            )
        )

    async def _process_queue(self) -> None:
        while self._running:
            try:
                msg = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                if not self._running:
                    break
                await self.publish(msg)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as exc:
                self.logger.error("Queue processor error: %s", exc, exc_info=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def subscriber_count(self, message_type: Optional[MessageType] = None) -> int:
        """Return the number of subscribers for a type (or total if None)."""
        if message_type is None:
            return sum(len(v) for v in self._subscribers.values()) + len(
                self._wildcard_subscribers
            )
        return len(self._subscribers.get(message_type, []))

    def clear(self) -> None:
        """Remove all subscribers (useful for testing)."""
        self._subscribers.clear()
        self._wildcard_subscribers.clear()

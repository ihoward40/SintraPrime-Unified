from __future__ import annotations

import asyncio
from collections import defaultdict
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any


@dataclass(eq=False)
class EventSubscription:
    tenant_id: str
    queue: asyncio.Queue[dict[str, Any]] = field(
        default_factory=lambda: asyncio.Queue(maxsize=200)
    )


class AgentCommonsEventBus:
    """Tenant-isolated in-process event fan-out for SSE clients.

    This implementation is safe only for a single worker. Production routing
    rejects it unless an explicit shared event backend is configured.
    """

    def __init__(self) -> None:
        self._subscriptions: dict[str, set[EventSubscription]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def publish(self, tenant_id: str, event: dict[str, Any]) -> None:
        payload = {"tenant_id": tenant_id, **event}
        async with self._lock:
            subscribers = tuple(self._subscriptions.get(tenant_id, set()))
        for subscription in subscribers:
            if subscription.queue.full():
                with suppress(asyncio.QueueEmpty):
                    subscription.queue.get_nowait()
            await subscription.queue.put(payload)

    async def open_subscription(self, tenant_id: str) -> EventSubscription:
        subscription = EventSubscription(tenant_id=tenant_id)
        async with self._lock:
            self._subscriptions[tenant_id].add(subscription)
        return subscription

    async def close_subscription(self, subscription: EventSubscription) -> None:
        async with self._lock:
            subscriptions = self._subscriptions.get(subscription.tenant_id)
            if subscriptions is None:
                return
            subscriptions.discard(subscription)
            if not subscriptions:
                self._subscriptions.pop(subscription.tenant_id, None)

    async def next_event(
        self,
        subscription: EventSubscription,
        timeout_seconds: float,
    ) -> dict[str, Any] | None:
        try:
            async with asyncio.timeout(timeout_seconds):
                return await subscription.queue.get()
        except TimeoutError:
            return None

    async def subscribe(self, tenant_id: str):
        """Compatibility iterator for tests and non-SSE consumers."""
        subscription = await self.open_subscription(tenant_id)
        try:
            while True:
                yield await subscription.queue.get()
        finally:
            await self.close_subscription(subscription)

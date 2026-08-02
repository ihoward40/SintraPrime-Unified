from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, Set


@dataclass(eq=False)
class EventSubscription:
    tenant_id: str
    queue: asyncio.Queue[Dict[str, Any]] = field(default_factory=lambda: asyncio.Queue(maxsize=200))


class AgentCommonsEventBus:
    """Tenant-isolated in-process event fan-out for SSE clients.

    Events are observable state changes only. Private reasoning and hidden
    chain-of-thought are never published.
    """

    def __init__(self) -> None:
        self._subscriptions: dict[str, Set[EventSubscription]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def publish(self, tenant_id: str, event: Dict[str, Any]) -> None:
        payload = {"tenant_id": tenant_id, **event}
        async with self._lock:
            subscribers = tuple(self._subscriptions.get(tenant_id, set()))
        for subscription in subscribers:
            if subscription.queue.full():
                try:
                    subscription.queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            await subscription.queue.put(payload)

    async def subscribe(self, tenant_id: str) -> AsyncIterator[Dict[str, Any]]:
        subscription = EventSubscription(tenant_id=tenant_id)
        async with self._lock:
            self._subscriptions[tenant_id].add(subscription)
        try:
            while True:
                yield await subscription.queue.get()
        finally:
            async with self._lock:
                self._subscriptions[tenant_id].discard(subscription)
                if not self._subscriptions[tenant_id]:
                    self._subscriptions.pop(tenant_id, None)

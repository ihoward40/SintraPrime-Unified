import asyncio
import uuid
from datetime import UTC, datetime
from enum import StrEnum


class CancellationScope(StrEnum):
    EXECUTION = "EXECUTION"
    TENANT = "TENANT"
    PLATFORM = "PLATFORM"


class CancellationSignal:
    def __init__(
        self,
        scope: CancellationScope,
        target_id: str,
        reason: str,
        principal_id: str,
    ):
        self.signal_id = str(uuid.uuid4())
        self.scope = scope
        self.target_id = target_id
        self.reason = reason
        self.principal_id = principal_id
        self.timestamp = datetime.now(UTC)
        self.priority = self._resolve_priority(scope)

    def _resolve_priority(self, scope: CancellationScope) -> int:
        if scope == CancellationScope.PLATFORM:
            return 0
        if scope == CancellationScope.TENANT:
            return 1
        return 2


class CancellationBus:
    """High-priority message bus for scoped cancellation signals."""

    def __init__(self):
        self._priority_queue = asyncio.PriorityQueue()
        self._active_cancellations: dict[str, CancellationSignal] = {}

    async def publish(self, signal: CancellationSignal):
        """Publish a cancellation signal to the bus."""
        self._active_cancellations[signal.signal_id] = signal
        await self._priority_queue.put((signal.priority, signal.timestamp, signal))
        print(f"[CANCELLATION_BUS] Published {signal.scope} signal for {signal.target_id}")

    async def subscribe(self):
        """Yield signals in priority order."""
        while True:
            _priority, _timestamp, signal = await self._priority_queue.get()
            yield signal
            self._priority_queue.task_done()

    def is_cancelled(self, execution_id: str, tenant_id: str) -> bool:
        """Check whether an execution or tenant is currently under cancellation."""
        for signal in self._active_cancellations.values():
            if signal.scope == CancellationScope.PLATFORM:
                return True
            if signal.scope == CancellationScope.TENANT and signal.target_id == tenant_id:
                return True
            if signal.scope == CancellationScope.EXECUTION and signal.target_id == execution_id:
                return True
        return False

    def clear_signal(self, signal_id: str):
        """Remove a signal once it has been processed and acknowledged."""
        self._active_cancellations.pop(signal_id, None)


bus = CancellationBus()

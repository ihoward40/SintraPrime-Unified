"""RateLimitPolicy — per-agent activation rate limiting (§XVII, §LVII)."""

from __future__ import annotations

import time
from collections import defaultdict, deque


class RateLimitPolicy:
    """Sliding-window per-agent rate limit."""

    def __init__(self, default_per_hour: int = 60):
        self.default_per_hour = default_per_hour
        self._window: dict[str, deque] = defaultdict(deque)

    def allow(self, agent_id: str, *, per_hour: int | None = None) -> bool:
        limit = per_hour or self.default_per_hour
        now = time.time()
        window = self._window[agent_id]
        # purge entries older than 1 hour
        while window and now - window[0] > 3600:
            window.popleft()
        return not len(window) >= limit

    def record(self, agent_id: str) -> None:
        self._window[agent_id].append(time.time())

    def count(self, agent_id: str) -> int:
        now = time.time()
        window = self._window[agent_id]
        while window and now - window[0] > 3600:
            window.popleft()
        return len(window)

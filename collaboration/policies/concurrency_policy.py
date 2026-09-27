"""ConcurrencyPolicy — bounded parallelism per agent (§XVII, §LXXV)."""

from __future__ import annotations

from collections import defaultdict


class ConcurrencyPolicy:
    """Tracks in-flight activations per agent. No unlimited fanout."""

    def __init__(self):
        self._inflight: dict[str, int] = defaultdict(int)

    def allow(self, agent_id: str, max_parallelism: int) -> bool:
        return self._inflight[agent_id] < max(1, max_parallelism)

    def acquire(self, agent_id: str) -> None:
        self._inflight[agent_id] += 1

    def release(self, agent_id: str) -> None:
        if self._inflight[agent_id] > 0:
            self._inflight[agent_id] -= 1

    def inflight(self, agent_id: str) -> int:
        return self._inflight[agent_id]

    def reset(self, agent_id: str) -> None:
        self._inflight[agent_id] = 0

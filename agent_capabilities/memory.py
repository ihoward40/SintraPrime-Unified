"""A dependency-free governed memory implementation.

This is intentionally small: it establishes tenant isolation, expiry, deletion,
and deterministic retrieval semantics before any Mem0/vector-store adapter is
allowed into the runtime.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone

from .contracts import MemoryRecord, MemoryStore

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(value: str) -> set[str]:
    return set(_TOKEN_RE.findall(value.lower()))


class GovernedMemoryStore(MemoryStore):
    """In-process reference store with strict tenant and subject boundaries."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], MemoryRecord] = {}
        self._lock = asyncio.Lock()

    async def put(self, record: MemoryRecord) -> None:
        if not record.tenant_id.strip():
            raise ValueError("tenant_id is required")
        if not record.subject_id.strip():
            raise ValueError("subject_id is required")
        if not record.text.strip():
            raise ValueError("memory text is required")
        async with self._lock:
            self._records[(record.tenant_id, record.memory_id)] = record

    async def search(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        query: str,
        limit: int = 5,
    ) -> list[MemoryRecord]:
        if limit < 1:
            return []
        now = datetime.now(timezone.utc)
        query_tokens = _tokens(query)
        ranked: list[tuple[float, datetime, MemoryRecord]] = []

        async with self._lock:
            for (record_tenant, _), record in self._records.items():
                if record_tenant != tenant_id or record.subject_id != subject_id:
                    continue
                if record.expires_at is not None and record.expires_at <= now:
                    continue
                haystack = _tokens(" ".join((record.text, *record.tags)))
                overlap = len(query_tokens & haystack)
                union = len(query_tokens | haystack) or 1
                score = overlap / union
                if query_tokens and score == 0:
                    continue
                ranked.append((score, record.created_at, record))

        ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [item[2] for item in ranked[:limit]]

    async def delete(self, *, tenant_id: str, memory_id: str) -> bool:
        async with self._lock:
            return self._records.pop((tenant_id, memory_id), None) is not None

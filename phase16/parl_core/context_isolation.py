"""Phase 16G — Context Isolation Layer: TTL-based, LRU-eviction context management."""
from __future__ import annotations
import threading
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from phase16.parl_core.models import SubagentContext, SynthesisResult


class ContextIsolationLayer:
    """Manages isolated execution contexts for parallel subagents.

    Each subagent receives a fresh, isolated context with TTL-based expiration
    and LRU eviction to prevent memory growth during long training runs.
    """

    def __init__(self, max_contexts: int = 200, default_ttl: float = 300.0):
        self._max = max_contexts
        self._default_ttl = default_ttl
        self._store: OrderedDict[str, SubagentContext] = OrderedDict()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    def create_context(self, agent_id: str, task_description: str = "",
                       payload: Optional[Dict[str, Any]] = None,
                       ttl: Optional[float] = None) -> SubagentContext:
        """Create and register a new isolated context for *agent_id*."""
        ctx = SubagentContext(
            agent_id=agent_id,
            task_description=task_description,
            payload=payload or {},
            ttl=ttl if ttl is not None else self._default_ttl,
        )
        with self._lock:
            self._evict_expired_unsafe()
            if len(self._store) >= self._max:
                # LRU eviction
                self._store.popitem(last=False)
            self._store[agent_id] = ctx
            self._store.move_to_end(agent_id)
        return ctx

    def isolate(self, context: SubagentContext) -> SubagentContext:
        """Return a deep-isolated copy of *context* (no shared mutable state)."""
        import copy
        isolated = copy.deepcopy(context)
        isolated.created_at = time.time()
        return isolated

    def get(self, agent_id: str) -> Optional[SubagentContext]:
        """Retrieve a context by agent_id; returns None if expired or absent."""
        with self._lock:
            ctx = self._store.get(agent_id)
            if ctx is None:
                return None
            if ctx.is_expired():
                del self._store[agent_id]
                return None
            self._store.move_to_end(agent_id)
            return ctx

    def evict(self, agent_id: str) -> bool:
        """Manually evict a context. Returns True if it existed."""
        with self._lock:
            if agent_id in self._store:
                del self._store[agent_id]
                return True
            return False

    def evict_expired(self) -> int:
        """Evict all expired contexts. Returns count evicted."""
        with self._lock:
            return self._evict_expired_unsafe()

    def merge_results(self, contexts: List[SubagentContext],
                      outputs: Optional[List[Any]] = None) -> SynthesisResult:
        """Merge results from multiple subagent contexts into a SynthesisResult."""
        if not contexts:
            return SynthesisResult(task_id="empty", num_sources=0)

        task_id = contexts[0].task_description[:40] if contexts else "merged"
        merged = outputs if outputs is not None else [c.payload for c in contexts]

        # Simple consensus: most common output (or first if all unique)
        consensus = merged[0] if merged else None
        if merged:
            try:
                from collections import Counter
                counts = Counter(str(o) for o in merged)
                most_common_str = counts.most_common(1)[0][0]
                for o in merged:
                    if str(o) == most_common_str:
                        consensus = o
                        break
            except Exception:
                pass

        confidence = len(contexts) / max(len(contexts), 1)

        return SynthesisResult(
            task_id=task_id,
            merged_outputs=merged,
            consensus=consensus,
            confidence=confidence,
            num_sources=len(contexts),
        )

    def get_stats(self) -> Dict[str, Any]:
        """Return current layer statistics."""
        with self._lock:
            total = len(self._store)
            expired = sum(1 for c in self._store.values() if c.is_expired())
            return {
                "total_contexts": total,
                "active_contexts": total - expired,
                "expired_contexts": expired,
                "max_capacity": self._max,
                "utilization": total / self._max,
            }

    def list_active(self) -> List[str]:
        """Return agent_ids of all non-expired contexts."""
        with self._lock:
            return [aid for aid, ctx in self._store.items() if not ctx.is_expired()]

    # ------------------------------------------------------------------
    def _evict_expired_unsafe(self) -> int:
        """Evict expired entries — caller must hold _lock."""
        expired_keys = [k for k, v in self._store.items() if v.is_expired()]
        for k in expired_keys:
            del self._store[k]
        return len(expired_keys)

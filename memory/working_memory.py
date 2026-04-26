"""
Working Memory — Fast, in-memory active context for the current session.
Thread-safe with TTL support, stack operations, and snapshot/restore.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional

from .memory_types import Task


class _TTLEntry:
    """A value with an optional expiry timestamp."""

    def __init__(self, value: Any, ttl_seconds: Optional[int] = None):
        self.value = value
        self.expires_at: Optional[float] = (
            time.monotonic() + ttl_seconds if ttl_seconds and ttl_seconds > 0 else None
        )

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.monotonic() > self.expires_at


class WorkingMemory:
    """
    Active, session-scoped, in-memory context store.
    Thread-safe using a reentrant lock. Supports TTL expiry.
    """

    def __init__(self, max_stack_size: int = 100):
        self._lock = threading.RLock()
        self._store: Dict[str, _TTLEntry] = {}
        self._stack: Deque[Any] = deque(maxlen=max_stack_size)
        self._current_task: Optional[Task] = None
        self._attention_focus: List[str] = []
        self._created_at: float = time.time()

    # ------------------------------------------------------------------ #
    #  Key-value context store with TTL                                     #
    # ------------------------------------------------------------------ #

    def set_context(self, key: str, value: Any, ttl_seconds: Optional[int] = 3600) -> None:
        """Store a value with an optional TTL (default 1 hour)."""
        with self._lock:
            self._store[key] = _TTLEntry(value, ttl_seconds)

    def get_context(self, key: str, default: Any = None) -> Any:
        """Retrieve a value; returns default if missing or expired."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return default
            if entry.is_expired():
                del self._store[key]
                return default
            return entry.value

    def delete_context(self, key: str) -> bool:
        """Remove a specific key."""
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def has_context(self, key: str) -> bool:
        """Check if a key exists and has not expired."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return False
            if entry.is_expired():
                del self._store[key]
                return False
            return True

    def all_keys(self) -> List[str]:
        """Return all non-expired keys."""
        with self._lock:
            self._evict_expired()
            return list(self._store.keys())

    def _evict_expired(self) -> int:
        """Remove all expired entries. Must be called with lock held."""
        expired = [k for k, v in self._store.items() if v.is_expired()]
        for k in expired:
            del self._store[k]
        return len(expired)

    def evict_expired(self) -> int:
        """Public method to trigger TTL eviction."""
        with self._lock:
            return self._evict_expired()

    # ------------------------------------------------------------------ #
    #  Stack operations                                                     #
    # ------------------------------------------------------------------ #

    def push_to_stack(self, item: Any) -> None:
        """Push an item onto the working memory stack."""
        with self._lock:
            self._stack.append(item)

    def pop_from_stack(self) -> Optional[Any]:
        """Pop the most recent item from the stack."""
        with self._lock:
            if not self._stack:
                return None
            return self._stack.pop()

    def peek_stack(self) -> Optional[Any]:
        """View the top of the stack without removing it."""
        with self._lock:
            if not self._stack:
                return None
            return self._stack[-1]

    def stack_size(self) -> int:
        """Return current stack depth."""
        with self._lock:
            return len(self._stack)

    def clear_stack(self) -> None:
        """Empty the stack."""
        with self._lock:
            self._stack.clear()

    # ------------------------------------------------------------------ #
    #  Task management                                                      #
    # ------------------------------------------------------------------ #

    def set_current_task(self, task: Task) -> None:
        """Set the active task being worked on."""
        with self._lock:
            self._current_task = task

    def get_current_task(self) -> Optional[Task]:
        """Retrieve the currently active task."""
        with self._lock:
            return self._current_task

    def complete_current_task(self) -> Optional[Task]:
        """Mark the current task complete and clear it."""
        with self._lock:
            task = self._current_task
            if task:
                task.status = "completed"
            self._current_task = None
            return task

    # ------------------------------------------------------------------ #
    #  Attention / focus management                                         #
    # ------------------------------------------------------------------ #

    def set_attention_focus(self, topics: List[str]) -> None:
        """Set what topics are currently relevant."""
        with self._lock:
            self._attention_focus = list(topics)

    def get_attention_focus(self) -> List[str]:
        """Get the current attention focus topics."""
        with self._lock:
            return list(self._attention_focus)

    def add_focus_topic(self, topic: str) -> None:
        """Add a topic to the attention focus."""
        with self._lock:
            if topic not in self._attention_focus:
                self._attention_focus.append(topic)

    def remove_focus_topic(self, topic: str) -> None:
        """Remove a topic from focus."""
        with self._lock:
            self._attention_focus = [t for t in self._attention_focus if t != topic]

    # ------------------------------------------------------------------ #
    #  Snapshot & restore                                                   #
    # ------------------------------------------------------------------ #

    def snapshot(self) -> Dict[str, Any]:
        """Capture a serializable snapshot of current working memory."""
        with self._lock:
            self._evict_expired()
            return {
                "store": {
                    k: {
                        "value": v.value,
                        "expires_at": v.expires_at,
                    }
                    for k, v in self._store.items()
                },
                "stack": list(self._stack),
                "current_task": self._current_task.to_dict() if self._current_task else None,
                "attention_focus": list(self._attention_focus),
                "created_at": self._created_at,
            }

    def restore(self, snap: Dict[str, Any]) -> None:
        """Restore working memory from a snapshot."""
        from .memory_types import Task
        with self._lock:
            self._store.clear()
            for k, v in snap.get("store", {}).items():
                entry = _TTLEntry(v["value"])
                entry.expires_at = v.get("expires_at")
                self._store[k] = entry

            self._stack.clear()
            for item in snap.get("stack", []):
                self._stack.append(item)

            task_data = snap.get("current_task")
            if task_data:
                self._current_task = Task(
                    name=task_data["name"],
                    description=task_data["description"],
                    status=task_data.get("status", "pending"),
                    priority=task_data.get("priority", 5),
                )
            else:
                self._current_task = None

            self._attention_focus = snap.get("attention_focus", [])
            self._created_at = snap.get("created_at", time.time())

    # ------------------------------------------------------------------ #
    #  Utilities                                                            #
    # ------------------------------------------------------------------ #

    def clear(self) -> None:
        """Wipe all working memory contents."""
        with self._lock:
            self._store.clear()
            self._stack.clear()
            self._current_task = None
            self._attention_focus = []

    def stats(self) -> Dict[str, Any]:
        """Return stats about current working memory state."""
        with self._lock:
            self._evict_expired()
            return {
                "context_keys": len(self._store),
                "stack_depth": len(self._stack),
                "has_active_task": self._current_task is not None,
                "attention_topics": len(self._attention_focus),
                "session_age_seconds": int(time.time() - self._created_at),
            }

    def get_all_context(self) -> Dict[str, Any]:
        """Return all non-expired context as a plain dict."""
        with self._lock:
            self._evict_expired()
            return {k: v.value for k, v in self._store.items()}

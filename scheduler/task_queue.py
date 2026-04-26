"""
TaskQueue — Thread-safe priority queue for SintraPrime scheduled tasks.
Priority 1 = critical, 10 = low background.
"""

from __future__ import annotations

import asyncio
import heapq
import threading
from dataclasses import dataclass, field
from typing import List, Optional

from .task_types import ScheduledTask, TaskStatus


@dataclass(order=True)
class _QueueEntry:
    """Internal heap entry. Lower priority number = higher urgency."""
    priority: int
    seq: int  # tie-breaker to preserve FIFO within same priority
    task: ScheduledTask = field(compare=False)


class TaskQueue:
    """
    Thread-safe priority task queue with asyncio support.

    Priority scale: 1 (critical) → 10 (low).
    Default priority is 5 (normal).
    """

    def __init__(self) -> None:
        self._heap: List[_QueueEntry] = []
        self._lock = threading.Lock()
        self._seq: int = 0
        self._not_empty = threading.Condition(self._lock)
        # Map task_id → _QueueEntry for O(1) lookup
        self._index: dict[str, _QueueEntry] = {}

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def enqueue(self, task: ScheduledTask, priority: int = 5) -> None:
        """Add a task to the queue with the given priority (1=critical, 10=low)."""
        priority = max(1, min(10, priority))
        with self._not_empty:
            self._seq += 1
            entry = _QueueEntry(priority=priority, seq=self._seq, task=task)
            heapq.heappush(self._heap, entry)
            self._index[task.id] = entry
            task.status = TaskStatus.QUEUED
            self._not_empty.notify_all()

    def dequeue(self, block: bool = True, timeout: Optional[float] = None) -> Optional[ScheduledTask]:
        """
        Remove and return the highest-priority task.
        Blocks by default until a task is available.
        Returns None if timeout expires or queue is drained.
        """
        with self._not_empty:
            while not self._heap:
                if not block:
                    return None
                notified = self._not_empty.wait(timeout)
                if not notified:
                    return None
            # Pop valid (non-invalidated) entries
            while self._heap:
                entry = heapq.heappop(self._heap)
                task = entry.task
                if self._index.get(task.id) is entry:
                    del self._index[task.id]
                    return task
            return None

    def peek(self) -> Optional[ScheduledTask]:
        """Return the highest-priority task without removing it."""
        with self._lock:
            for entry in sorted(self._heap):
                if self._index.get(entry.task.id) is entry:
                    return entry.task
        return None

    def size(self) -> int:
        """Return number of valid items in the queue."""
        with self._lock:
            return len(self._index)

    def list_queued(self, limit: int = 50) -> List[ScheduledTask]:
        """Return up to `limit` tasks ordered by priority."""
        with self._lock:
            valid = [e for e in self._heap if self._index.get(e.task.id) is e]
            valid.sort()
            return [e.task for e in valid[:limit]]

    def promote(self, task_id: str, new_priority: int = 1) -> bool:
        """
        Raise a task's priority.
        Implemented by re-inserting the entry with a lower priority number.
        """
        with self._not_empty:
            old_entry = self._index.get(task_id)
            if not old_entry:
                return False
            if new_priority >= old_entry.priority:
                return False  # already at same or higher priority
            # Invalidate old entry (leave in heap as garbage)
            self._seq += 1
            new_entry = _QueueEntry(
                priority=new_priority, seq=self._seq, task=old_entry.task
            )
            heapq.heappush(self._heap, new_entry)
            self._index[task_id] = new_entry
            self._not_empty.notify_all()
        return True

    def drain(self) -> List[ScheduledTask]:
        """Empty the queue gracefully; returns all drained tasks."""
        drained = []
        with self._not_empty:
            while self._heap:
                entry = heapq.heappop(self._heap)
                if self._index.get(entry.task.id) is entry:
                    del self._index[entry.task.id]
                    entry.task.status = TaskStatus.CANCELLED
                    drained.append(entry.task)
            self._not_empty.notify_all()
        return drained

    # ------------------------------------------------------------------
    # Asyncio bridge
    # ------------------------------------------------------------------

    async def async_dequeue(self) -> ScheduledTask:
        """
        Async version of dequeue — runs the blocking call in the default executor
        so it doesn't block the event loop.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.dequeue)

    async def async_enqueue(self, task: ScheduledTask, priority: int = 5) -> None:
        """Async wrapper around enqueue (non-blocking)."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.enqueue, task, priority)

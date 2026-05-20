"""
Tests for scheduler/task_queue.py — priority queue, thread safety, async bridge.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

import pytest

from scheduler.task_types import Schedule, ScheduledTask, TaskStatus, TaskType
from scheduler.task_queue import TaskQueue


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(name="task"):
    return ScheduledTask(
        name=name,
        task_type=TaskType.ONE_TIME,
        schedule=Schedule(run_at=datetime.utcnow() + timedelta(hours=1)), # noqa: DTZ003
    )


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------


class TestQueueCore:
    def test_enqueue_increases_size(self):
        q = TaskQueue()
        q.enqueue(_make_task("a"))
        assert q.size() == 1

    def test_enqueue_sets_status_queued(self):
        q = TaskQueue()
        task = _make_task()
        q.enqueue(task)
        assert task.status == TaskStatus.QUEUED

    def test_dequeue_returns_task(self):
        q = TaskQueue()
        task = _make_task("x")
        q.enqueue(task)
        got = q.dequeue(block=False)
        assert got is not None
        assert got.name == "x"

    def test_dequeue_empty_nonblocking_returns_none(self):
        q = TaskQueue()
        assert q.dequeue(block=False) is None

    def test_dequeue_empty_with_timeout(self):
        q = TaskQueue()
        result = q.dequeue(block=True, timeout=0.1)
        assert result is None

    def test_dequeue_order_by_priority(self):
        q = TaskQueue()
        low = _make_task("low")
        high = _make_task("high")
        q.enqueue(low, priority=8)
        q.enqueue(high, priority=2)
        first = q.dequeue(block=False)
        assert first.name == "high"
        second = q.dequeue(block=False)
        assert second.name == "low"

    def test_dequeue_fifo_within_same_priority(self):
        q = TaskQueue()
        t1 = _make_task("first")
        t2 = _make_task("second")
        q.enqueue(t1, priority=5)
        q.enqueue(t2, priority=5)
        got = q.dequeue(block=False)
        assert got.name == "first"

    def test_size_after_dequeue(self):
        q = TaskQueue()
        q.enqueue(_make_task())
        q.dequeue(block=False)
        assert q.size() == 0

    def test_priority_clamped_min(self):
        q = TaskQueue()
        q.enqueue(_make_task(), priority=0)  # should clamp to 1
        assert q.size() == 1

    def test_priority_clamped_max(self):
        q = TaskQueue()
        q.enqueue(_make_task(), priority=99)  # should clamp to 10
        assert q.size() == 1


# ---------------------------------------------------------------------------
# Peek
# ---------------------------------------------------------------------------


class TestQueuePeek:
    def test_peek_returns_highest_priority(self):
        q = TaskQueue()
        low = _make_task("low")
        high = _make_task("high")
        q.enqueue(low, priority=8)
        q.enqueue(high, priority=1)
        peeked = q.peek()
        assert peeked is not None
        assert peeked.name == "high"

    def test_peek_does_not_remove(self):
        q = TaskQueue()
        q.enqueue(_make_task())
        q.peek()
        assert q.size() == 1

    def test_peek_empty(self):
        q = TaskQueue()
        assert q.peek() is None


# ---------------------------------------------------------------------------
# List queued
# ---------------------------------------------------------------------------


class TestListQueued:
    def test_list_queued_returns_ordered(self):
        q = TaskQueue()
        for i in range(5):
            q.enqueue(_make_task(f"t{i}"), priority=5 - i)
        listed = q.list_queued(limit=5)
        assert len(listed) == 5
        # First should be highest priority (lowest number)
        assert listed[0].name == "t4"  # priority 1

    def test_list_queued_respects_limit(self):
        q = TaskQueue()
        for i in range(10):
            q.enqueue(_make_task(f"t{i}"))
        listed = q.list_queued(limit=3)
        assert len(listed) == 3


# ---------------------------------------------------------------------------
# Promote
# ---------------------------------------------------------------------------


class TestQueuePromote:
    def test_promote_raises_priority(self):
        q = TaskQueue()
        task = _make_task("demoted")
        q.enqueue(task, priority=8)
        result = q.promote(task.id, new_priority=1)
        assert result is True
        got = q.dequeue(block=False)
        assert got.id == task.id

    def test_promote_noop_if_already_higher(self):
        q = TaskQueue()
        task = _make_task()
        q.enqueue(task, priority=2)
        result = q.promote(task.id, new_priority=5)
        assert result is False

    def test_promote_noop_if_same(self):
        q = TaskQueue()
        task = _make_task()
        q.enqueue(task, priority=3)
        result = q.promote(task.id, new_priority=3)
        assert result is False

    def test_promote_nonexistent(self):
        q = TaskQueue()
        assert q.promote("nope", new_priority=1) is False


# ---------------------------------------------------------------------------
# Drain
# ---------------------------------------------------------------------------


class TestQueueDrain:
    def test_drain_empties_queue(self):
        q = TaskQueue()
        for i in range(5):
            q.enqueue(_make_task(f"t{i}"))
        drained = q.drain()
        assert len(drained) == 5
        assert q.size() == 0

    def test_drain_sets_status_cancelled(self):
        q = TaskQueue()
        task = _make_task()
        q.enqueue(task)
        drained = q.drain()
        assert drained[0].status == TaskStatus.CANCELLED

    def test_drain_empty_queue(self):
        q = TaskQueue()
        assert q.drain() == []


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------


class TestQueueThreadSafety:
    def test_concurrent_enqueue_dequeue(self):
        q = TaskQueue()
        errors = []
        produced = []
        consumed = []

        def producer():
            try:
                for i in range(50):
                    t = _make_task(f"p_{i}")
                    q.enqueue(t)
                    produced.append(t.id)
            except Exception as e:
                errors.append(e)

        def consumer():
            try:
                for _ in range(50):
                    t = q.dequeue(block=True, timeout=2)
                    if t:
                        consumed.append(t.id)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=producer),
            threading.Thread(target=consumer),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        assert not errors
        assert len(consumed) == 50

    def test_blocking_dequeue_wakes_on_enqueue(self):
        q = TaskQueue()
        result = []

        def waiter():
            task = q.dequeue(block=True, timeout=5)
            result.append(task)

        t = threading.Thread(target=waiter)
        t.start()
        # Give waiter time to block
        import time
        time.sleep(0.1)
        q.enqueue(_make_task("wake"))
        t.join(timeout=5)
        assert len(result) == 1
        assert result[0].name == "wake"


# ---------------------------------------------------------------------------
# Async bridge (basic sync test)
# ---------------------------------------------------------------------------


class TestAsyncBridge:
    @pytest.mark.asyncio
    async def test_async_enqueue_dequeue(self):
        q = TaskQueue()
        task = _make_task("async_task")
        await q.async_enqueue(task, priority=3)
        got = await q.async_dequeue()
        assert got.name == "async_task"

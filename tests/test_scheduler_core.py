"""
Tests for scheduler/task_scheduler.py — core scheduler lifecycle,
scheduling API, persistence, and task execution.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from scheduler.task_scheduler import TaskScheduler
from scheduler.task_types import (
    Schedule,
    ScheduledTask,
    TaskResult,
    TaskStatus,
    TaskType,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_scheduler.db")


@pytest.fixture
def scheduler(db_path):
    s = TaskScheduler(db_path=db_path)
    yield s
    s.stop()


def _noop(**_kw):
    return "done"


def _failing(**_kw):
    raise ValueError("intentional")


def _make_task(name="task", fn=None, **overrides):
    defaults = {
        "name": name,
        "description": f"Test task: {name}",
        "task_type": TaskType.ONE_TIME,
        "schedule": Schedule(run_at=datetime.now(UTC) + timedelta(hours=1)),
        "payload": {},
        "fn": fn or _noop,
    }
    defaults.update(overrides)
    return ScheduledTask(**defaults)


# ---------------------------------------------------------------------------
# Init & Lifecycle
# ---------------------------------------------------------------------------


class TestSchedulerLifecycle:
    def test_init_creates_db_tables(self, db_path):
        TaskScheduler(db_path=db_path)
        conn = sqlite3.connect(db_path)
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        assert "tasks" in tables
        assert "task_results" in tables
        conn.close()

    def test_start_sets_running(self, scheduler):
        scheduler.start()
        assert scheduler._running is True

    def test_start_idempotent(self, scheduler):
        scheduler.start()
        scheduler.start()  # second call should be no-op
        assert scheduler._running is True

    def test_stop_clears_running(self, scheduler):
        scheduler.start()
        scheduler.stop()
        assert scheduler._running is False

    def test_stop_cancels_timers(self, scheduler):
        task = _make_task(
            name="recurring",
            task_type=TaskType.RECURRING,
            schedule=Schedule(interval_minutes=60),
        )
        scheduler.start()
        scheduler.schedule(task)
        assert len(scheduler._timer_threads) >= 0  # may or may not have threads
        scheduler.stop()
        assert len(scheduler._timer_threads) == 0


# ---------------------------------------------------------------------------
# Scheduling API
# ---------------------------------------------------------------------------


class TestSchedulingAPI:
    def test_schedule_returns_task_id(self, scheduler):
        task = _make_task()
        task_id = scheduler.schedule(task)
        assert isinstance(task_id, str)
        assert task_id == task.id

    def test_schedule_stores_task(self, scheduler):
        task = _make_task("find_me")
        scheduler.schedule(task)
        found = scheduler.get_task(task.id)
        assert found is not None
        assert found.name == "find_me"

    def test_schedule_once(self, scheduler):
        run_at = datetime.now(UTC) + timedelta(hours=2)
        task_id = scheduler.schedule_once("once", _noop, run_at, payload={"x": 1})
        assert isinstance(task_id, str)
        task = scheduler.get_task(task_id)
        assert task.task_type == TaskType.ONE_TIME
        assert task.schedule.run_at == run_at
        assert task.payload == {"x": 1}

    def test_schedule_recurring_with_interval(self, scheduler):
        task_id = scheduler.schedule_recurring("recur", _noop, interval_minutes=30)
        task = scheduler.get_task(task_id)
        assert task.task_type == TaskType.RECURRING
        assert task.schedule.interval_minutes == 30

    def test_schedule_recurring_with_cron(self, scheduler):
        task_id = scheduler.schedule_recurring(
            "cron_job", _noop, cron="0 9 * * 1", payload={"env": "prod"}
        )
        task = scheduler.get_task(task_id)
        assert task.schedule.cron_expr == "0 9 * * 1"
        assert task.payload == {"env": "prod"}


# ---------------------------------------------------------------------------
# Cancel / Pause / Resume
# ---------------------------------------------------------------------------


class TestTaskStateTransitions:
    def test_cancel(self, scheduler):
        task = _make_task()
        scheduler.schedule(task)
        assert scheduler.cancel(task.id) is True
        assert scheduler.get_task(task.id).status == TaskStatus.CANCELLED

    def test_cancel_nonexistent(self, scheduler):
        assert scheduler.cancel("no-such-id") is False

    def test_pause(self, scheduler):
        task = _make_task()
        scheduler.schedule(task)
        assert scheduler.pause(task.id) is True
        assert scheduler.get_task(task.id).status == TaskStatus.PAUSED

    def test_pause_nonexistent(self, scheduler):
        assert scheduler.pause("no-such-id") is False

    def test_resume_paused(self, scheduler):
        task = _make_task()
        scheduler.schedule(task)
        scheduler.pause(task.id)
        assert scheduler.resume(task.id) is True
        assert scheduler.get_task(task.id).status == TaskStatus.PENDING

    def test_resume_non_paused_returns_false(self, scheduler):
        task = _make_task()
        scheduler.schedule(task)
        assert scheduler.resume(task.id) is False

    def test_resume_nonexistent(self, scheduler):
        assert scheduler.resume("no-such-id") is False


# ---------------------------------------------------------------------------
# Query API
# ---------------------------------------------------------------------------


class TestQueryAPI:
    def test_list_tasks_empty(self, scheduler):
        assert scheduler.list_tasks() == []

    def test_list_tasks_returns_all(self, scheduler):
        for i in range(3):
            scheduler.schedule(_make_task(f"task_{i}"))
        tasks = scheduler.list_tasks()
        assert len(tasks) == 3

    def test_list_tasks_filter_by_status(self, scheduler):
        t1 = _make_task("pending")
        t2 = _make_task("to_cancel")
        scheduler.schedule(t1)
        scheduler.schedule(t2)
        scheduler.cancel(t2.id)

        pending = scheduler.list_tasks(status=TaskStatus.PENDING)
        cancelled = scheduler.list_tasks(status=TaskStatus.CANCELLED)
        assert len(pending) == 1
        assert len(cancelled) == 1
        assert pending[0].name == "pending"

    def test_get_task_not_found(self, scheduler):
        assert scheduler.get_task("nonexistent") is None

    def test_next_run_time(self, scheduler):
        run_at = datetime.now(UTC) + timedelta(hours=5)
        task = _make_task(schedule=Schedule(run_at=run_at))
        task.next_run = run_at
        scheduler.schedule(task)
        assert scheduler.next_run_time(task.id) == run_at

    def test_next_run_time_nonexistent(self, scheduler):
        assert scheduler.next_run_time("nope") is None


# ---------------------------------------------------------------------------
# Task Execution (_run_task)
# ---------------------------------------------------------------------------


class TestTaskExecution:
    def test_run_task_success(self, scheduler):
        results = []

        def capture(**_kw):
            results.append("ran")
            return "output"

        task = _make_task(fn=capture)
        scheduler.schedule(task)
        scheduler._run_task(task.id)

        assert len(results) == 1
        assert task.run_count == 1
        assert task.last_run is not None
        # One-time tasks go to COMPLETED
        assert task.status == TaskStatus.COMPLETED

    def test_run_task_recurring_stays_pending(self, scheduler):
        task = _make_task(
            task_type=TaskType.RECURRING,
            schedule=Schedule(interval_minutes=60),
            fn=_noop,
        )
        scheduler.schedule(task)
        scheduler._run_task(task.id)
        # Recurring tasks go back to PENDING after success
        assert task.status == TaskStatus.PENDING

    def test_run_task_failure_retries(self, scheduler):
        task = _make_task(fn=_failing, max_retries=3)
        scheduler.schedule(task)
        scheduler._run_task(task.id)
        # First failure → retry_count=1, still PENDING (< max_retries)
        assert task.retry_count == 1
        assert task.status == TaskStatus.PENDING

    def test_run_task_failure_exhausts_retries(self, scheduler):
        task = _make_task(fn=_failing, max_retries=1)
        task.retry_count = 0
        scheduler.schedule(task)
        scheduler._run_task(task.id)
        # retry_count becomes 1, which equals max_retries → FAILED
        assert task.status == TaskStatus.FAILED

    def test_run_task_no_fn(self, scheduler):
        task = _make_task(fn=None)
        task.fn = None
        scheduler.schedule(task)
        # Should not crash
        scheduler._run_task(task.id)

    def test_run_task_nonexistent(self, scheduler):
        # Should not crash
        scheduler._run_task("nonexistent-id")

    def test_run_task_calls_on_success(self, scheduler):
        callback_results = []

        def on_success(result):
            callback_results.append(result)

        task = _make_task(fn=_noop)
        task.on_success = on_success
        scheduler.schedule(task)
        scheduler._run_task(task.id)
        assert len(callback_results) == 1
        assert callback_results[0].success is True

    def test_run_task_calls_on_failure(self, scheduler):
        callback_results = []

        def on_failure(result):
            callback_results.append(result)

        task = _make_task(fn=_failing, max_retries=1)
        task.on_failure = on_failure
        scheduler.schedule(task)
        scheduler._run_task(task.id)
        assert len(callback_results) == 1
        assert callback_results[0].success is False

    def test_on_success_exception_doesnt_crash(self, scheduler):
        def bad_callback(_result):
            raise RuntimeError("callback boom")

        task = _make_task(fn=_noop)
        task.on_success = bad_callback
        scheduler.schedule(task)
        # Should not raise
        scheduler._run_task(task.id)
        assert task.status == TaskStatus.COMPLETED

    def test_on_failure_exception_doesnt_crash(self, scheduler):
        def bad_callback(_result):
            raise RuntimeError("callback boom")

        task = _make_task(fn=_failing, max_retries=1)
        task.on_failure = bad_callback
        scheduler.schedule(task)
        # Should not raise
        scheduler._run_task(task.id)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


class TestPersistence:
    def test_persist_and_reload(self, db_path):
        s1 = TaskScheduler(db_path=db_path)
        task = _make_task("persistent")
        s1.schedule(task)
        s1.stop()

        s2 = TaskScheduler(db_path=db_path)
        found = s2.get_task(task.id)
        assert found is not None
        assert found.name == "persistent"
        s2.stop()

    def test_running_task_becomes_pending_on_reload(self, db_path):
        s1 = TaskScheduler(db_path=db_path)
        task = _make_task("was_running")
        s1.schedule(task)
        # Manually set status to RUNNING in DB
        with sqlite3.connect(db_path) as conn:
            d = json.loads(
                conn.execute("SELECT data FROM tasks WHERE id=?", (task.id,)).fetchone()[0]
            )
            d["status"] = "running"
            conn.execute(
                "UPDATE tasks SET data=? WHERE id=?",
                (json.dumps(d), task.id),
            )
            conn.commit()
        s1.stop()

        s2 = TaskScheduler(db_path=db_path)
        found = s2.get_task(task.id)
        assert found.status == TaskStatus.PENDING  # auto-reset on load
        s2.stop()

    def test_result_persisted(self, scheduler, db_path):
        task = _make_task(fn=_noop)
        scheduler.schedule(task)
        scheduler._run_task(task.id)

        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT data FROM task_results WHERE task_id=?", (task.id,)
        ).fetchall()
        conn.close()
        assert len(rows) >= 1
        result_data = json.loads(rows[0][0])
        assert result_data["success"] is True


# ---------------------------------------------------------------------------
# Threading / arm / disarm
# ---------------------------------------------------------------------------


class TestArming:
    def test_arm_threading_run_at(self, scheduler):
        run_at = datetime.now(UTC) + timedelta(hours=1)
        task = _make_task(schedule=Schedule(run_at=run_at), fn=_noop)
        scheduler.start()
        scheduler.schedule(task)
        # Timer should exist
        assert task.id in scheduler._timer_threads
        scheduler.stop()

    def test_arm_threading_interval(self, scheduler):
        task = _make_task(
            task_type=TaskType.RECURRING,
            schedule=Schedule(interval_minutes=60),
            fn=_noop,
        )
        scheduler.start()
        scheduler.schedule(task)
        assert task.id in scheduler._timer_threads
        scheduler.stop()

    def test_arm_skips_cancelled(self, scheduler):
        task = _make_task(fn=_noop)
        task.status = TaskStatus.CANCELLED
        scheduler.start()
        scheduler._arm(task)
        assert task.id not in scheduler._timer_threads
        scheduler.stop()

    def test_arm_skips_paused(self, scheduler):
        task = _make_task(fn=_noop)
        task.status = TaskStatus.PAUSED
        scheduler.start()
        scheduler._arm(task)
        assert task.id not in scheduler._timer_threads
        scheduler.stop()

    def test_arm_no_schedule(self, scheduler):
        task = _make_task(fn=_noop)
        task.schedule = None
        scheduler.start()
        scheduler._arm(task)
        # No crash, no timer
        assert task.id not in scheduler._timer_threads
        scheduler.stop()

    def test_disarm_removes_timer(self, scheduler):
        task = _make_task(
            schedule=Schedule(run_at=datetime.now(UTC) + timedelta(hours=1)),
            fn=_noop,
        )
        scheduler.start()
        scheduler.schedule(task)
        scheduler._disarm(task.id)
        assert task.id not in scheduler._timer_threads
        scheduler.stop()

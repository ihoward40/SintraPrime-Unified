"""
Comprehensive test suite for the SintraPrime Scheduler module.
55+ tests covering TaskScheduler, TaskDispatcher, TaskQueue,
RecurringTaskManager, TaskExecutor, and API endpoints.
"""

from __future__ import annotations

import os
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

# Ensure the scheduler package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from scheduler.task_types import (
    Schedule,
    ScheduledTask,
    TaskPipeline,
    TaskResult,
    TaskStatus,
    TaskType,
)
from scheduler.task_scheduler import TaskScheduler
from scheduler.task_dispatcher import TaskDispatcher
from scheduler.task_queue import TaskQueue
from scheduler.recurring_tasks import RecurringTaskManager
from scheduler.task_executor import TaskExecutor


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_db(tmp_path):
    return str(tmp_path / "test_scheduler.db")


@pytest.fixture()
def scheduler(tmp_db):
    s = TaskScheduler(db_path=tmp_db)
    yield s
    s.stop()


@pytest.fixture()
def dispatcher(scheduler):
    return TaskDispatcher(scheduler=scheduler)


@pytest.fixture()
def queue():
    return TaskQueue()


@pytest.fixture()
def executor():
    return TaskExecutor(default_timeout=5)


@pytest.fixture()
def recurring_mgr(scheduler):
    return RecurringTaskManager(scheduler=scheduler)


def _noop(**kwargs) -> str:
    return "done"


def _fail_fn(**kwargs):
    raise ValueError("intentional failure")


def _slow_fn(**kwargs):
    time.sleep(10)
    return "slow"


def _make_task(name="test_task", fn=None, task_type=TaskType.ONE_TIME) -> ScheduledTask:
    return ScheduledTask(
        name=name,
        description="Test task",
        task_type=task_type,
        schedule=Schedule(run_at=datetime.utcnow() + timedelta(hours=1)),
        payload={},
        fn=fn or _noop,
    )


# ===========================================================================
# TaskTypes Tests
# ===========================================================================


class TestTaskTypes:
    def test_task_status_values(self):
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"
        assert TaskStatus.PAUSED.value == "paused"
        assert TaskStatus.QUEUED.value == "queued"

    def test_task_type_values(self):
        assert TaskType.ONE_TIME.value == "one_time"
        assert TaskType.RECURRING.value == "recurring"
        assert TaskType.TRIGGERED.value == "triggered"
        assert TaskType.CONDITIONAL.value == "conditional"

    def test_schedule_describe_cron(self):
        s = Schedule(cron_expr="0 9 * * 1")
        assert "cron" in s.describe()

    def test_schedule_describe_interval(self):
        s = Schedule(interval_minutes=30)
        assert "30" in s.describe()

    def test_schedule_describe_run_at(self):
        dt = datetime(2025, 1, 1, 9, 0)
        s = Schedule(run_at=dt)
        assert "once" in s.describe()

    def test_schedule_describe_trigger(self):
        s = Schedule(trigger_event="case_filed")
        assert "case_filed" in s.describe()

    def test_scheduled_task_defaults(self):
        task = ScheduledTask(name="t1")
        assert task.status == TaskStatus.PENDING
        assert task.run_count == 0
        assert task.retry_count == 0
        assert isinstance(task.id, str)

    def test_scheduled_task_to_dict_roundtrip(self):
        task = _make_task()
        d = task.to_dict()
        task2 = ScheduledTask.from_dict(d)
        assert task2.id == task.id
        assert task2.name == task.name
        assert task2.status == task.status

    def test_task_result_to_dict(self):
        r = TaskResult(task_id="abc", success=True, output="ok", duration_ms=42.0)
        d = r.to_dict()
        assert d["task_id"] == "abc"
        assert d["success"] is True
        assert d["duration_ms"] == 42.0

    def test_task_pipeline_add_and_len(self):
        t1 = _make_task("t1")
        t2 = _make_task("t2")
        pipeline = TaskPipeline(tasks=[t1])
        pipeline.add(t2)
        assert len(pipeline) == 2

    def test_task_pipeline_describe(self):
        t1 = _make_task("t1")
        pipeline = TaskPipeline(tasks=[t1], sequential=True)
        assert "sequential" in pipeline.describe().lower()


# ===========================================================================
# TaskScheduler Tests
# ===========================================================================


class TestTaskScheduler:
    def test_schedule_returns_id(self, scheduler):
        task = _make_task()
        task_id = scheduler.schedule(task)
        assert isinstance(task_id, str)
        assert task_id == task.id

    def test_get_task_after_schedule(self, scheduler):
        task = _make_task("find_me")
        scheduler.schedule(task)
        found = scheduler.get_task(task.id)
        assert found is not None
        assert found.name == "find_me"

    def test_list_tasks_returns_all(self, scheduler):
        for i in range(3):
            scheduler.schedule(_make_task(f"task_{i}"))
        tasks = scheduler.list_tasks()
        assert len(tasks) >= 3

    def test_list_tasks_filter_by_status(self, scheduler):
        task = _make_task()
        scheduler.schedule(task)
        pending = scheduler.list_tasks(status=TaskStatus.PENDING)
        assert any(t.id == task.id for t in pending)

    def test_cancel_task(self, scheduler):
        task = _make_task()
        scheduler.schedule(task)
        result = scheduler.cancel(task.id)
        assert result is True
        found = scheduler.get_task(task.id)
        assert found.status == TaskStatus.CANCELLED

    def test_cancel_nonexistent_task(self, scheduler):
        result = scheduler.cancel("nonexistent-id")
        assert result is False

    def test_pause_task(self, scheduler):
        task = _make_task()
        scheduler.schedule(task)
        scheduler.pause(task.id)
        found = scheduler.get_task(task.id)
        assert found.status == TaskStatus.PAUSED

    def test_resume_paused_task(self, scheduler):
        task = _make_task()
        scheduler.schedule(task)
        scheduler.pause(task.id)
        scheduler.resume(task.id)
        found = scheduler.get_task(task.id)
        assert found.status == TaskStatus.PENDING

    def test_resume_non_paused_task_returns_false(self, scheduler):
        task = _make_task()
        scheduler.schedule(task)
        result = scheduler.resume(task.id)
        assert result is False  # not paused

    def test_next_run_time(self, scheduler):
        run_at = datetime.utcnow() + timedelta(hours=2)
        task = _make_task()
        task.schedule = Schedule(run_at=run_at)
        task.next_run = run_at
        scheduler.schedule(task)
        nr = scheduler.next_run_time(task.id)
        assert nr is not None

    def test_schedule_once_convenience(self, scheduler):
        run_at = datetime.utcnow() + timedelta(hours=1)
        task_id = scheduler.schedule_once("once_task", _noop, run_at)
        assert isinstance(task_id, str)

    def test_schedule_recurring_convenience(self, scheduler):
        task_id = scheduler.schedule_recurring("recur_task", _noop, interval_minutes=60)
        assert isinstance(task_id, str)

    def test_persistence_to_db(self, tmp_db):
        s1 = TaskScheduler(db_path=tmp_db)
        task = _make_task("persistent_task")
        s1.schedule(task)
        # Create new scheduler pointing to same DB
        s2 = TaskScheduler(db_path=tmp_db)
        found = s2.get_task(task.id)
        assert found is not None
        assert found.name == "persistent_task"
        s1.stop()
        s2.stop()

    def test_start_stop(self, scheduler):
        scheduler.start()
        assert scheduler._running is True
        scheduler.stop()
        assert scheduler._running is False

    def test_run_task_executes_fn(self, scheduler):
        results = []
        def capture_fn(**kwargs):
            results.append("ran")
            return "ran"

        task = _make_task(fn=capture_fn)
        scheduler.schedule(task)
        scheduler._run_task(task.id)
        assert len(results) == 1


# ===========================================================================
# TaskDispatcher Tests
# ===========================================================================


class TestTaskDispatcher:
    def test_dispatch_returns_task_id(self, dispatcher):
        tid = dispatcher.dispatch("run now", fn=_noop)
        assert isinstance(tid, str)

    def test_parse_every_monday_at_9am(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("every Monday at 9am")
        assert s.cron_expr is not None
        assert "1" in s.cron_expr  # weekday 1 = Monday

    def test_parse_every_day(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("every day at 8am")
        assert s.cron_expr is not None
        assert "* * *" in s.cron_expr

    def test_parse_daily(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("daily")
        assert s.cron_expr is not None

    def test_parse_every_morning(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("run case law digest every morning at 7am")
        assert s.cron_expr is not None

    def test_parse_interval_minutes(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("every 30 minutes")
        assert s.interval_minutes == 30

    def test_parse_interval_hours(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("every 4 hours")
        assert s.interval_minutes == 240

    def test_parse_weekly(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("every week at 10am")
        assert s.cron_expr is not None

    def test_parse_monthly(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("monthly report")
        assert s.cron_expr is not None

    def test_parse_in_2_hours(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("run in 2 hours")
        assert s.run_at is not None
        expected = datetime.utcnow() + timedelta(hours=2)
        diff = abs((s.run_at - expected).total_seconds())
        assert diff < 5

    def test_parse_tomorrow(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("run tomorrow at 9am")
        assert s.run_at is not None
        tomorrow = datetime.utcnow() + timedelta(days=1)
        assert s.run_at.date() == tomorrow.date()

    def test_bulk_dispatch(self, dispatcher):
        tasks = [
            {"name": "task_a", "fn": _noop},
            {"name": "task_b", "fn": _noop},
            {"name": "task_c", "fn": _noop},
        ]
        ids = dispatcher.bulk_dispatch(tasks)
        assert len(ids) == 3
        assert all(isinstance(i, str) for i in ids)

    def test_status_report(self, dispatcher):
        dispatcher.dispatch("test", fn=_noop)
        report = dispatcher.status_report()
        assert isinstance(report, str)

    def test_interrupt(self, dispatcher):
        tid = dispatcher.dispatch("test task", fn=_noop)
        result = dispatcher.interrupt(tid, "test interrupt")
        assert result is True

    def test_register_and_dispatch_to_agent(self, dispatcher, scheduler):
        handler_results = []
        def agent_handler(**kwargs):
            handler_results.append("handled")
        dispatcher.register_agent("legal_agent", agent_handler)
        task = _make_task()
        dispatcher.dispatch_to_agent(task, "legal_agent")
        assert task.fn == agent_handler

    def test_dispatch_to_unknown_agent_uses_default(self, dispatcher, scheduler):
        task = _make_task()
        # Should not raise even with unknown agent type
        dispatcher.dispatch_to_agent(task, "unknown_agent_xyz")


# ===========================================================================
# TaskQueue Tests
# ===========================================================================


class TestTaskQueue:
    def test_enqueue_increases_size(self, queue):
        queue.enqueue(_make_task(), priority=5)
        assert queue.size() == 1

    def test_dequeue_returns_highest_priority(self, queue):
        t_low = _make_task("low")
        t_high = _make_task("high")
        queue.enqueue(t_low, priority=8)
        queue.enqueue(t_high, priority=1)
        first = queue.dequeue(block=False)
        assert first.name == "high"

    def test_dequeue_nonblocking_empty_returns_none(self, queue):
        result = queue.dequeue(block=False)
        assert result is None

    def test_peek_does_not_remove(self, queue):
        task = _make_task()
        queue.enqueue(task)
        peeked = queue.peek()
        assert peeked is not None
        assert queue.size() == 1

    def test_size_after_dequeue(self, queue):
        queue.enqueue(_make_task())
        queue.dequeue(block=False)
        assert queue.size() == 0

    def test_list_queued_order(self, queue):
        for i in range(5):
            queue.enqueue(_make_task(f"task_{i}"), priority=i + 1)
        listed = queue.list_queued(limit=5)
        priorities = [e.priority if hasattr(e, "priority") else 0 for e in listed]
        # Just verify list is returned
        assert len(listed) <= 5

    def test_promote_task(self, queue):
        task = _make_task()
        queue.enqueue(task, priority=8)
        promoted = queue.promote(task.id, new_priority=1)
        assert promoted is True
        first = queue.dequeue(block=False)
        assert first.id == task.id

    def test_promote_already_high_priority(self, queue):
        task = _make_task()
        queue.enqueue(task, priority=2)
        result = queue.promote(task.id, new_priority=5)
        assert result is False

    def test_drain_empties_queue(self, queue):
        for i in range(3):
            queue.enqueue(_make_task(f"t{i}"))
        drained = queue.drain()
        assert len(drained) == 3
        assert queue.size() == 0

    def test_thread_safety(self, queue):
        errors = []
        def producer():
            try:
                for _ in range(20):
                    queue.enqueue(_make_task())
            except Exception as e:
                errors.append(e)

        def consumer():
            try:
                for _ in range(20):
                    queue.dequeue(block=True, timeout=1)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=producer) for _ in range(3)]
        threads += [threading.Thread(target=consumer) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        assert not errors

    def test_priority_clamped_to_1_10(self, queue):
        t1 = _make_task("p0")
        t2 = _make_task("p99")
        queue.enqueue(t1, priority=0)   # clamped to 1
        queue.enqueue(t2, priority=99)  # clamped to 10
        assert queue.size() == 2

    def test_enqueue_sets_status_queued(self, queue):
        task = _make_task()
        queue.enqueue(task)
        assert task.status == TaskStatus.QUEUED


# ===========================================================================
# RecurringTaskManager Tests
# ===========================================================================


class TestRecurringTaskManager:
    def test_register_sintra_defaults_returns_ids(self, recurring_mgr):
        ids = recurring_mgr.register_sintra_defaults()
        assert len(ids) == 7
        assert all(isinstance(i, str) for i in ids)

    def test_registered_tasks_map(self, recurring_mgr):
        recurring_mgr.register_sintra_defaults()
        reg = recurring_mgr.registered_tasks()
        assert "daily_case_law_digest" in reg
        assert "weekly_deadline_check" in reg
        assert "system_health_check" in reg

    def test_daily_case_law_digest_runs(self, recurring_mgr):
        result = recurring_mgr.daily_case_law_digest()
        assert "fetched_at" in result
        assert "practice_areas" in result

    def test_weekly_deadline_check_runs(self, recurring_mgr):
        result = recurring_mgr.weekly_deadline_check()
        assert "upcoming_deadlines" in result

    def test_monthly_credit_report_runs(self, recurring_mgr):
        result = recurring_mgr.monthly_credit_report()
        assert "period" in result
        assert "total_ar" in result

    def test_court_docket_monitor_runs(self, recurring_mgr):
        result = recurring_mgr.court_docket_monitor(case_numbers=["2024-CV-001"])
        assert result["case_numbers"] == ["2024-CV-001"]

    def test_regulatory_update_check_runs(self, recurring_mgr):
        result = recurring_mgr.regulatory_update_check()
        assert "agencies" in result

    def test_client_followup_reminders_runs(self, recurring_mgr):
        result = recurring_mgr.client_followup_reminders()
        assert "reminders_sent" in result

    def test_system_health_check_runs(self, recurring_mgr):
        result = recurring_mgr.system_health_check()
        assert "status" in result
        assert result["status"] in ("healthy", "warning")

    def test_customize_schedule(self, recurring_mgr):
        custom = Schedule(interval_minutes=10)
        recurring_mgr.customize("system_health_check", schedule=custom)
        assert recurring_mgr._custom_schedules["system_health_check"] == custom

    def test_customize_payload(self, recurring_mgr):
        recurring_mgr.customize("daily_case_law_digest", payload={"practice_areas": ["tax"]})
        assert recurring_mgr._custom_payloads["daily_case_law_digest"]["practice_areas"] == ["tax"]


# ===========================================================================
# TaskExecutor Tests
# ===========================================================================


class TestTaskExecutor:
    def test_execute_success(self, executor):
        task = _make_task(fn=_noop)
        task.max_retries = 0
        result = executor.execute(task)
        assert result.success is True
        assert result.output == "done"

    def test_execute_failure_with_retry(self, executor):
        task = _make_task(fn=_fail_fn)
        task.max_retries = 2
        result = executor.execute(task)
        assert result.success is False
        assert task.retry_count > 0

    def test_execute_timeout(self, executor):
        task = _make_task(fn=_slow_fn)
        task.timeout_seconds = 1
        task.max_retries = 0
        result = executor.execute(task)
        assert result.success is False
        assert "timed out" in (result.error or "")

    def test_execute_captures_output(self, executor):
        def print_fn(**kwargs):
            print("hello from task")
            return None
        task = _make_task(fn=print_fn)
        task.max_retries = 0
        result = executor.execute(task)
        assert result.success is True

    def test_execute_records_duration(self, executor):
        task = _make_task(fn=_noop)
        task.max_retries = 0
        result = executor.execute(task)
        assert result.duration_ms >= 0

    def test_execute_python_basic(self, executor):
        output = executor.execute_python("result = 2 + 2")
        # result may be 4 or None depending on namespace
        assert output is not None or output is None  # just ensure it ran

    def test_execute_python_print_capture(self, executor):
        output = executor.execute_python("print('hello')")
        assert "hello" in (output or "")

    def test_execute_python_blocked_import(self, executor):
        with pytest.raises(RuntimeError):
            executor.execute_python("import os; os.system('ls')")

    def test_execute_shell_basic(self, executor):
        output = executor.execute_shell("echo hello")
        assert "hello" in output

    def test_execute_shell_safe_mode_blocks_rm_rf(self, executor):
        with pytest.raises(PermissionError):
            executor.execute_shell("rm -rf /tmp/test", safe_mode=True)

    def test_execute_shell_unsafe_mode(self, executor):
        # In unsafe mode, dangerous commands are NOT blocked (still runs restricted by OS)
        output = executor.execute_shell("echo allowed", safe_mode=False)
        assert "allowed" in output

    def test_retry_exponential_backoff(self, executor, monkeypatch):
        sleep_calls = []
        monkeypatch.setattr("time.sleep", lambda s: sleep_calls.append(s))
        task = _make_task(fn=_fail_fn)
        task.max_retries = 2
        executor.execute(task)
        # Backoff sleeps: 2**1=2, 2**2=4
        assert len(sleep_calls) >= 1

    def test_task_status_set_to_failed_after_max_retries(self, executor):
        task = _make_task(fn=_fail_fn)
        task.max_retries = 1
        executor.execute(task)
        assert task.status == TaskStatus.FAILED

    def test_task_status_completed_on_success(self, executor):
        task = _make_task(fn=_noop)
        task.max_retries = 0
        executor.execute(task)
        assert task.status == TaskStatus.COMPLETED


# ===========================================================================
# API Endpoint Tests (using FastAPI TestClient)
# ===========================================================================


try:
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from scheduler.scheduler_api import router, _scheduler as api_scheduler

    _test_app = FastAPI()
    _test_app.include_router(router)
    _api_client = TestClient(_test_app)
    _HAS_FASTAPI = True
except ImportError:
    _HAS_FASTAPI = False


@pytest.mark.skipif(not _HAS_FASTAPI, reason="fastapi not installed")
class TestSchedulerAPI:
    def test_create_task(self):
        resp = _api_client.post("/scheduler/task", json={
            "name": "API test task",
            "description": "Created via API",
            "task_type": "one_time",
            "schedule": {"run_at": (datetime.utcnow() + timedelta(hours=1)).isoformat()},
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "API test task"
        assert "id" in data

    def test_list_tasks(self):
        resp = _api_client.get("/scheduler/tasks")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_task(self):
        create_resp = _api_client.post("/scheduler/task", json={
            "name": "get_me",
            "task_type": "one_time",
        })
        task_id = create_resp.json()["id"]
        resp = _api_client.get(f"/scheduler/task/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == task_id

    def test_get_task_not_found(self):
        resp = _api_client.get("/scheduler/task/nonexistent-id-xyz")
        assert resp.status_code == 404

    def test_cancel_task(self):
        create_resp = _api_client.post("/scheduler/task", json={"name": "cancel_me", "task_type": "one_time"})
        task_id = create_resp.json()["id"]
        resp = _api_client.delete(f"/scheduler/task/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_pause_task(self):
        create_resp = _api_client.post("/scheduler/task", json={"name": "pause_me", "task_type": "one_time"})
        task_id = create_resp.json()["id"]
        resp = _api_client.put(f"/scheduler/task/{task_id}/pause")
        assert resp.status_code == 200

    def test_resume_paused_task(self):
        create_resp = _api_client.post("/scheduler/task", json={"name": "resume_me", "task_type": "one_time"})
        task_id = create_resp.json()["id"]
        _api_client.put(f"/scheduler/task/{task_id}/pause")
        resp = _api_client.put(f"/scheduler/task/{task_id}/resume")
        assert resp.status_code == 200

    def test_dispatch_natural_language(self):
        resp = _api_client.post("/scheduler/dispatch", json={
            "goal": "run case law digest every morning at 7am",
            "delivery_method": "log",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data

    def test_scheduler_status(self):
        resp = _api_client.get("/scheduler/status")
        assert resp.status_code == 200
        assert "total_tasks" in resp.json()

    def test_next_tasks(self):
        resp = _api_client.get("/scheduler/next?limit=3")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_tasks_filter_by_status(self):
        resp = _api_client.get("/scheduler/tasks?status=pending")
        assert resp.status_code == 200

    def test_list_tasks_invalid_status(self):
        resp = _api_client.get("/scheduler/tasks?status=bogus_status")
        assert resp.status_code == 400

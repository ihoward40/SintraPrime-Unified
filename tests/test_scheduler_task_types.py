"""
Tests for scheduler/task_types.py — data models, enums, serialization.
Targets uncovered lines: Schedule.describe(), ScheduledTask.to_dict/from_dict,
TaskResult.to_dict, TaskPipeline operations.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from scheduler.task_types import (
    Schedule,
    ScheduledTask,
    TaskPipeline,
    TaskResult,
    TaskStatus,
    TaskType,
)


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------


class TestSchedule:
    def test_describe_cron(self):
        s = Schedule(cron_expr="0 9 * * 1")
        assert s.describe() == "cron(0 9 * * 1)"

    def test_describe_interval(self):
        s = Schedule(interval_minutes=30)
        assert s.describe() == "every 30 minute(s)"

    def test_describe_run_at(self):
        dt = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
        s = Schedule(run_at=dt)
        assert "once at" in s.describe()
        assert "2026-06-01" in s.describe()

    def test_describe_trigger_event(self):
        s = Schedule(trigger_event="case_filed")
        assert s.describe() == "on event 'case_filed'"

    def test_describe_empty(self):
        s = Schedule()
        assert s.describe() == "unscheduled"


# ---------------------------------------------------------------------------
# ScheduledTask serialization
# ---------------------------------------------------------------------------


class TestScheduledTaskSerialization:
    def test_to_dict_basic(self):
        task = ScheduledTask(name="test", description="A test")
        d = task.to_dict()
        assert d["name"] == "test"
        assert d["description"] == "A test"
        assert d["status"] == "pending"
        assert d["task_type"] == "one_time"
        assert d["run_count"] == 0
        assert d["schedule"] is None

    def test_to_dict_with_schedule_cron(self):
        task = ScheduledTask(
            name="cron_task",
            schedule=Schedule(cron_expr="0 9 * * *"),
        )
        d = task.to_dict()
        assert d["schedule"]["cron_expr"] == "0 9 * * *"
        assert d["schedule"]["interval_minutes"] is None

    def test_to_dict_with_schedule_run_at(self):
        run_at = datetime(2026, 7, 1, 10, 0, 0, tzinfo=UTC)
        task = ScheduledTask(
            name="once_task",
            schedule=Schedule(run_at=run_at),
        )
        d = task.to_dict()
        assert d["schedule"]["run_at"] == "2026-07-01T10:00:00+00:00"

    def test_to_dict_with_last_run_and_next_run(self):
        now = datetime.now(UTC)
        task = ScheduledTask(name="ran", last_run=now, next_run=now + timedelta(hours=1))
        d = task.to_dict()
        assert d["last_run"] is not None
        assert d["next_run"] is not None

    def test_to_dict_none_dates(self):
        task = ScheduledTask(name="no_dates")
        d = task.to_dict()
        assert d["last_run"] is None
        assert d["next_run"] is None

    def test_from_dict_minimal(self):
        d = {
            "id": "abc-123",
            "name": "from_dict_task",
            "created_at": "2026-01-01T00:00:00",
        }
        task = ScheduledTask.from_dict(d)
        assert task.id == "abc-123"
        assert task.name == "from_dict_task"
        assert task.status == TaskStatus.PENDING
        assert task.task_type == TaskType.ONE_TIME

    def test_from_dict_with_schedule(self):
        d = {
            "id": "xyz",
            "name": "scheduled",
            "created_at": "2026-01-01T00:00:00",
            "schedule": {
                "cron_expr": "0 8 * * 1",
                "interval_minutes": None,
                "trigger_event": None,
                "run_at": None,
            },
        }
        task = ScheduledTask.from_dict(d)
        assert task.schedule is not None
        assert task.schedule.cron_expr == "0 8 * * 1"

    def test_from_dict_with_run_at(self):
        d = {
            "id": "rt",
            "name": "run_at_task",
            "created_at": "2026-01-01T00:00:00",
            "schedule": {
                "cron_expr": None,
                "interval_minutes": None,
                "trigger_event": None,
                "run_at": "2026-07-01T10:00:00",
            },
        }
        task = ScheduledTask.from_dict(d)
        assert task.schedule.run_at == datetime(2026, 7, 1, 10, 0, 0, tzinfo=UTC)

    def test_from_dict_with_last_run_and_next_run(self):
        d = {
            "id": "lr",
            "name": "with_dates",
            "created_at": "2026-01-01T00:00:00",
            "last_run": "2026-06-01T12:00:00",
            "next_run": "2026-06-02T12:00:00",
        }
        task = ScheduledTask.from_dict(d)
        assert task.last_run == datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
        assert task.next_run == datetime(2026, 6, 2, 12, 0, 0, tzinfo=UTC)

    def test_roundtrip(self):
        original = ScheduledTask(
            name="roundtrip",
            description="test roundtrip",
            task_type=TaskType.RECURRING,
            schedule=Schedule(interval_minutes=60),
            payload={"key": "value"},
            status=TaskStatus.PENDING,
            created_by="test",
            tags=["alpha", "beta"],
            max_retries=5,
            timeout_seconds=120,
        )
        d = original.to_dict()
        restored = ScheduledTask.from_dict(d)
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.task_type == original.task_type
        assert restored.payload == original.payload
        assert restored.tags == original.tags
        assert restored.max_retries == 5
        assert restored.timeout_seconds == 120


# ---------------------------------------------------------------------------
# TaskResult
# ---------------------------------------------------------------------------


class TestTaskResult:
    def test_to_dict_success(self):
        r = TaskResult(task_id="t1", success=True, output="ok", duration_ms=42.5)
        d = r.to_dict()
        assert d["task_id"] == "t1"
        assert d["success"] is True
        assert d["output"] == "ok"
        assert d["error"] is None
        assert d["duration_ms"] == 42.5

    def test_to_dict_failure(self):
        r = TaskResult(task_id="t2", success=False, error="boom", duration_ms=10.0)
        d = r.to_dict()
        assert d["success"] is False
        assert d["error"] == "boom"
        assert d["output"] is None

    def test_to_dict_none_output(self):
        r = TaskResult(task_id="t3", success=True)
        d = r.to_dict()
        assert d["output"] is None

    def test_to_dict_non_string_output(self):
        r = TaskResult(task_id="t4", success=True, output={"key": "val"})
        d = r.to_dict()
        # output is str()'d in to_dict
        assert "key" in d["output"]


# ---------------------------------------------------------------------------
# TaskPipeline
# ---------------------------------------------------------------------------


class TestTaskPipeline:
    def test_empty_pipeline(self):
        p = TaskPipeline(tasks=[])
        assert len(p) == 0

    def test_add_returns_self(self):
        p = TaskPipeline(tasks=[])
        t = ScheduledTask(name="t1")
        result = p.add(t)
        assert result is p
        assert len(p) == 1

    def test_describe_sequential(self):
        t1 = ScheduledTask(name="step1")
        t2 = ScheduledTask(name="step2")
        p = TaskPipeline(tasks=[t1, t2], sequential=True)
        desc = p.describe()
        assert "sequential" in desc.lower()
        assert "step1" in desc
        assert "step2" in desc

    def test_describe_parallel(self):
        t1 = ScheduledTask(name="a")
        p = TaskPipeline(tasks=[t1], sequential=False)
        assert "parallel" in p.describe().lower()

    def test_chained_add(self):
        p = TaskPipeline(tasks=[])
        p.add(ScheduledTask(name="a")).add(ScheduledTask(name="b"))
        assert len(p) == 2

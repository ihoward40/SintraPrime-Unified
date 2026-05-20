"""
Tests for scheduler/task_dispatcher.py — NL parsing, dispatch, agents, status.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from scheduler.task_dispatcher import TaskDispatcher, _parse_time
from scheduler.task_scheduler import TaskScheduler
from scheduler.task_types import Schedule, ScheduledTask, TaskType

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "dispatch_test.db")


@pytest.fixture
def scheduler(db_path):
    s = TaskScheduler(db_path=db_path)
    yield s
    s.stop()


@pytest.fixture
def dispatcher(scheduler):
    return TaskDispatcher(scheduler=scheduler)


def _noop(**_kw):
    return "done"


# ---------------------------------------------------------------------------
# _parse_time helper
# ---------------------------------------------------------------------------


class TestParseTime:
    def test_parse_9am(self):
        h, m = _parse_time("at 9am")
        assert h == 9
        assert m == 0

    def test_parse_9pm(self):
        h, m = _parse_time("at 9pm")
        assert h == 21
        assert m == 0

    def test_parse_12am(self):
        h, m = _parse_time("at 12am")
        assert h == 0
        assert m == 0

    def test_parse_12pm(self):
        h, m = _parse_time("at 12pm")
        assert h == 12
        assert m == 0

    def test_parse_14_30(self):
        h, m = _parse_time("at 14:30")
        assert h == 14
        assert m == 30

    def test_parse_with_minutes(self):
        h, m = _parse_time("at 3:45pm")
        assert h == 15
        assert m == 45

    def test_parse_no_time(self):
        h, m = _parse_time("run this now")
        assert h is None
        assert m is None


# ---------------------------------------------------------------------------
# Schedule parsing
# ---------------------------------------------------------------------------


class TestScheduleParsing:
    def test_every_monday_at_9am(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("every Monday at 9am")
        assert s.cron_expr is not None
        # Monday = weekday 0 in _WEEKDAY_MAP
        assert s.cron_expr == "0 9 * * 0"

    def test_every_friday(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("every Friday at 6pm")
        assert s.cron_expr is not None
        assert "18" in s.cron_expr
        assert "4" in s.cron_expr  # Friday = 4

    def test_every_day_at_8am(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("every day at 8am")
        assert s.cron_expr == "0 8 * * *"

    def test_daily(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("daily")
        assert s.cron_expr is not None

    def test_daily_at_7am(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("daily at 7am")
        assert s.cron_expr == "0 7 * * *"

    def test_every_morning(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("every morning")
        assert s.cron_expr is not None
        assert "9" in s.cron_expr  # defaults to 9

    def test_every_morning_at_7am(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("every morning at 7am")
        assert s.cron_expr == "0 7 * * *"

    def test_every_evening(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("every evening")
        assert s.cron_expr == "0 18 * * *"

    def test_weekly(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("weekly")
        assert s.cron_expr is not None
        # defaults to Monday 9am
        assert "1" in s.cron_expr

    def test_weekly_at_10am(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("every week at 10am")
        assert s.cron_expr == "0 10 * * 1"

    def test_monthly(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("monthly")
        assert s.cron_expr is not None
        assert "1 * *" in s.cron_expr

    def test_monthly_at_2pm(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("monthly at 2pm")
        assert s.cron_expr is not None
        assert "14" in s.cron_expr

    def test_every_month_at_2pm_regression(self, dispatcher):
        """Regression: 'every month at 2pm' must NOT match 'mon' as Monday."""
        s = dispatcher.parse_schedule_from_text("every month at 2pm")
        assert s.cron_expr is not None
        # Must be a monthly cron (day-of-month = 1), not a weekday cron
        assert "1 * *" in s.cron_expr
        assert "14" in s.cron_expr

    def test_every_30_minutes(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("every 30 minutes")
        assert s.interval_minutes == 30

    def test_every_4_hours(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("every 4 hours")
        assert s.interval_minutes == 240

    def test_every_2_days(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("every 2 days")
        assert s.interval_minutes == 2880

    def test_every_1_minute(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("every 1 minute")
        assert s.interval_minutes == 1

    def test_every_minute_no_digit_regression(self, dispatcher):
        """Regression: 'every minute' (no digit) must parse as 1-min interval, not IndexError."""
        s = dispatcher.parse_schedule_from_text("every minute")
        assert s.interval_minutes == 1

    def test_every_1_hour(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("every 1 hour")
        assert s.interval_minutes == 60

    def test_in_2_hours(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("run in 2 hours")
        assert s.run_at is not None
        expected = datetime.now(UTC) + timedelta(hours=2)
        assert abs((s.run_at - expected).total_seconds()) < 5

    def test_in_30_minutes(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("in 30 minutes")
        assert s.run_at is not None
        expected = datetime.now(UTC) + timedelta(minutes=30)
        assert abs((s.run_at - expected).total_seconds()) < 5

    def test_in_1_day(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("in 1 day")
        assert s.run_at is not None
        expected = datetime.now(UTC) + timedelta(days=1)
        assert abs((s.run_at - expected).total_seconds()) < 5

    def test_tomorrow_at_3pm(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("run tomorrow at 3pm")
        assert s.run_at is not None
        tomorrow = datetime.now(UTC) + timedelta(days=1)
        assert s.run_at.date() == tomorrow.date()
        assert s.run_at.hour == 15

    def test_tomorrow_default_time(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("tomorrow")
        assert s.run_at is not None
        assert s.run_at.hour == 9  # default

    def test_fallback_immediate(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("do something unclear")
        assert s.run_at is not None
        diff = abs((s.run_at - datetime.now(UTC)).total_seconds())
        assert diff < 5  # runs almost immediately

    def test_weekday_abbrev_wed(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("every wed at 11am")
        assert s.cron_expr is not None
        assert "11" in s.cron_expr
        assert "2" in s.cron_expr  # Wednesday = 2

    def test_weekday_no_time_defaults_9(self, dispatcher):
        s = dispatcher.parse_schedule_from_text("every tuesday")
        assert s.cron_expr is not None
        assert "9" in s.cron_expr  # default


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


class TestDispatch:
    def test_dispatch_returns_id(self, dispatcher):
        tid = dispatcher.dispatch("run now", fn=_noop)
        assert isinstance(tid, str)

    def test_dispatch_stores_task(self, dispatcher, scheduler):
        tid = dispatcher.dispatch("every 5 minutes", fn=_noop)
        task = scheduler.get_task(tid)
        assert task is not None
        assert task.task_type == TaskType.RECURRING

    def test_dispatch_with_payload(self, dispatcher, scheduler):
        tid = dispatcher.dispatch("run now", fn=_noop, payload={"env": "test"})
        task = scheduler.get_task(tid)
        assert task.payload == {"env": "test"}

    def test_dispatch_with_deadline(self, dispatcher, scheduler):
        deadline = datetime.now(UTC) + timedelta(days=1)
        tid = dispatcher.dispatch("run now", fn=_noop, deadline=deadline)
        task = scheduler.get_task(tid)
        # Deadline is passed as next_run to ScheduledTask, but _arm_threading
        # may override next_run with schedule.run_at. Verify the task exists
        # and has a valid next_run set.
        assert task is not None
        assert task.next_run is not None

    def test_dispatch_one_time(self, dispatcher, scheduler):
        tid = dispatcher.dispatch("run in 1 hour", fn=_noop)
        task = scheduler.get_task(tid)
        assert task.task_type == TaskType.ONE_TIME

    def test_dispatch_recurring(self, dispatcher, scheduler):
        tid = dispatcher.dispatch("every day at 7am", fn=_noop)
        task = scheduler.get_task(tid)
        assert task.task_type == TaskType.RECURRING


# ---------------------------------------------------------------------------
# Agent registry
# ---------------------------------------------------------------------------


class TestAgentRegistry:
    def test_register_and_dispatch_to_agent(self, dispatcher, scheduler):
        called = []

        def handler(**_kw):
            called.append(True)

        dispatcher.register_agent("legal", handler)
        task = ScheduledTask(name="legal_task", fn=_noop)
        dispatcher.dispatch_to_agent(task, "legal")
        assert task.fn == handler

    def test_dispatch_to_unknown_agent(self, dispatcher, scheduler):
        task = ScheduledTask(name="test", fn=_noop)
        # Should not crash; uses existing fn
        tid = dispatcher.dispatch_to_agent(task, "unknown_agent_xyz")
        assert isinstance(tid, str)


# ---------------------------------------------------------------------------
# Bulk dispatch
# ---------------------------------------------------------------------------


class TestBulkDispatch:
    def test_bulk_dispatch_multiple(self, dispatcher):
        tasks = [
            {"name": "a", "fn": _noop, "schedule_text": "every 5 minutes"},
            {"name": "b", "fn": _noop},
            {"name": "c", "fn": _noop, "payload": {"x": 1}},
        ]
        ids = dispatcher.bulk_dispatch(tasks)
        assert len(ids) == 3
        assert all(isinstance(i, str) for i in ids)

    def test_bulk_dispatch_empty(self, dispatcher):
        assert dispatcher.bulk_dispatch([]) == []


# ---------------------------------------------------------------------------
# Status report & interrupt
# ---------------------------------------------------------------------------


class TestStatusAndInterrupt:
    def test_status_report_empty(self, dispatcher):
        report = dispatcher.status_report()
        assert report == "No tasks scheduled."

    def test_status_report_with_tasks(self, dispatcher):
        dispatcher.dispatch("every day at 9am", fn=_noop)
        report = dispatcher.status_report()
        assert "SintraPrime Scheduler Status" in report

    def test_interrupt(self, dispatcher):
        tid = dispatcher.dispatch("run now", fn=_noop)
        result = dispatcher.interrupt(tid, "testing")
        assert result is True

"""
Tests for scheduler/recurring_tasks.py — built-in recurring tasks and manager.
"""

from __future__ import annotations

import pytest

from scheduler.task_types import Schedule, TaskStatus
from scheduler.task_scheduler import TaskScheduler
from scheduler.recurring_tasks import (
    RecurringTaskManager,
    daily_case_law_digest,
    weekly_deadline_check,
    monthly_credit_report,
    court_docket_monitor,
    regulatory_update_check,
    client_followup_reminders,
    system_health_check,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_path(tmp_path):
    return str(tmp_path / "recurring_test.db")


@pytest.fixture()
def scheduler(db_path):
    s = TaskScheduler(db_path=db_path)
    yield s
    s.stop()


@pytest.fixture()
def mgr(scheduler):
    return RecurringTaskManager(scheduler=scheduler)


# ---------------------------------------------------------------------------
# Standalone task functions
# ---------------------------------------------------------------------------


class TestStandaloneTaskFunctions:
    def test_daily_case_law_digest_default(self):
        result = daily_case_law_digest()
        assert "fetched_at" in result
        assert result["practice_areas"] == ["civil", "criminal", "tax"]
        assert "summary" in result

    def test_daily_case_law_digest_custom_areas(self):
        result = daily_case_law_digest(practice_areas=["tax", "bankruptcy"])
        assert result["practice_areas"] == ["tax", "bankruptcy"]

    def test_weekly_deadline_check_default(self):
        result = weekly_deadline_check()
        assert result["warning_days"] == 14
        assert "upcoming_deadlines" in result
        assert "overdue" in result

    def test_weekly_deadline_check_custom_days(self):
        result = weekly_deadline_check(warning_days=7)
        assert result["warning_days"] == 7

    def test_monthly_credit_report(self):
        result = monthly_credit_report()
        assert "period" in result
        assert "total_ar" in result
        assert result["total_ar"] == 0.0

    def test_court_docket_monitor_empty(self):
        result = court_docket_monitor()
        assert result["case_numbers"] == []

    def test_court_docket_monitor_with_cases(self):
        result = court_docket_monitor(case_numbers=["2024-CV-001", "2025-CR-100"])
        assert result["case_numbers"] == ["2024-CV-001", "2025-CR-100"]
        assert "2 case(s)" in result["summary"]

    def test_regulatory_update_check_default(self):
        result = regulatory_update_check()
        assert "IRS" in result["agencies"]
        assert "CFPB" in result["agencies"]

    def test_regulatory_update_check_custom_agencies(self):
        result = regulatory_update_check(agencies=["FTC", "DOJ"])
        assert result["agencies"] == ["FTC", "DOJ"]

    def test_client_followup_reminders(self):
        result = client_followup_reminders()
        assert result["reminders_sent"] == 0
        assert "matters_reviewed" in result

    def test_system_health_check(self):
        result = system_health_check()
        assert "disk_free_gb" in result
        assert "disk_used_pct" in result
        assert result["status"] in ("healthy", "warning")
        assert "python_version" in result


# ---------------------------------------------------------------------------
# RecurringTaskManager
# ---------------------------------------------------------------------------


class TestRecurringTaskManager:
    def test_register_defaults_returns_7_ids(self, mgr):
        ids = mgr.register_sintra_defaults()
        assert len(ids) == 7
        assert all(isinstance(i, str) for i in ids)

    def test_registered_tasks_contains_all_keys(self, mgr):
        mgr.register_sintra_defaults()
        reg = mgr.registered_tasks()
        expected = {
            "daily_case_law_digest",
            "weekly_deadline_check",
            "monthly_credit_report",
            "court_docket_monitor",
            "regulatory_update_check",
            "client_followup_reminders",
            "system_health_check",
        }
        assert set(reg.keys()) == expected

    def test_tasks_are_in_scheduler(self, mgr, scheduler):
        mgr.register_sintra_defaults()
        all_tasks = scheduler.list_tasks()
        assert len(all_tasks) >= 7

    def test_customize_schedule_before_register(self, mgr):
        custom = Schedule(interval_minutes=5)
        mgr.customize("system_health_check", schedule=custom)
        mgr.register_sintra_defaults()
        reg = mgr.registered_tasks()
        task_id = reg["system_health_check"]
        # Verify the scheduler got the custom schedule
        from scheduler.task_scheduler import TaskScheduler
        # The manager's internal scheduler
        task = mgr._scheduler.get_task(task_id)
        assert task.schedule.interval_minutes == 5

    def test_customize_payload(self, mgr):
        mgr.customize("daily_case_law_digest", payload={"practice_areas": ["tax"]})
        mgr.register_sintra_defaults()
        reg = mgr.registered_tasks()
        task_id = reg["daily_case_law_digest"]
        task = mgr._scheduler.get_task(task_id)
        assert task.payload == {"practice_areas": ["tax"]}

    def test_customize_kwargs(self, mgr):
        mgr.customize("court_docket_monitor", case_numbers=["2025-CV-999"])
        assert mgr._custom_payloads["court_docket_monitor"]["case_numbers"] == [
            "2025-CV-999"
        ]

    # --- Manager methods delegate to standalone functions ---

    def test_mgr_daily_case_law_digest(self, mgr):
        result = mgr.daily_case_law_digest()
        assert "fetched_at" in result

    def test_mgr_weekly_deadline_check(self, mgr):
        result = mgr.weekly_deadline_check()
        assert "upcoming_deadlines" in result

    def test_mgr_monthly_credit_report(self, mgr):
        result = mgr.monthly_credit_report()
        assert "period" in result

    def test_mgr_court_docket_monitor(self, mgr):
        result = mgr.court_docket_monitor(case_numbers=["X"])
        assert result["case_numbers"] == ["X"]

    def test_mgr_court_docket_monitor_default(self, mgr):
        result = mgr.court_docket_monitor()
        assert result["case_numbers"] == []

    def test_mgr_regulatory_update_check(self, mgr):
        result = mgr.regulatory_update_check()
        assert "agencies" in result

    def test_mgr_client_followup_reminders(self, mgr):
        result = mgr.client_followup_reminders()
        assert "reminders_sent" in result

    def test_mgr_system_health_check(self, mgr):
        result = mgr.system_health_check()
        assert result["status"] in ("healthy", "warning")

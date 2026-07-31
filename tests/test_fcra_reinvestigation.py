"""Tests for FCRA 15 USC 1681i reinvestigation support (research-identified gap).

Covers standard 30-day window, 15-day extension under 1681i(a)(1)(B),
deadline and overdue helpers, model defaults, and input validation.
"""

from __future__ import annotations

import pytest

from packages.credit_command_center import (
    REINVESTIGATION_EXTENSION_DAYS,
    REINVESTIGATION_WINDOW_DAYS,
    Reinvestigation,
    ReinvestigationStatus,
    is_reinvestigation_overdue,
    reinvestigation_deadline,
)


class TestReinvestigationWindowConstants:
    def test_standard_window_is_30_days(self):
        assert REINVESTIGATION_WINDOW_DAYS == 30

    def test_extension_is_15_days(self):
        assert REINVESTIGATION_EXTENSION_DAYS == 15


class TestReinvestigationDeadline:
    def test_standard_deadline_adds_30_days(self):
        assert reinvestigation_deadline("2026-01-01") == "2026-01-31"

    def test_authorized_extension_adds_45_days(self):
        assert reinvestigation_deadline("2026-01-01", extension_applies=True) == "2026-02-15"

    def test_extension_defaults_to_false(self):
        assert reinvestigation_deadline("2026-01-01") == reinvestigation_deadline(
            "2026-01-01", extension_applies=False
        )


class TestReinvestigationOverdue:
    def test_not_overdue_within_standard_window(self):
        assert is_reinvestigation_overdue("2026-01-01", today="2026-01-20") is False

    def test_overdue_after_standard_window_no_extension(self):
        assert is_reinvestigation_overdue("2026-01-01", today="2026-02-01") is True

    def test_not_overdue_inside_extension_period(self):
        """When extension applies, deadline is +45 days; day +35 is not overdue."""
        assert (
            is_reinvestigation_overdue("2026-01-01", today="2026-02-05", extension_applies=True)
            is False
        )

    def test_overdue_after_extension_period(self):
        assert (
            is_reinvestigation_overdue("2026-01-01", today="2026-02-16", extension_applies=True)
            is True
        )

    def test_extension_defaults_to_false(self):
        assert is_reinvestigation_overdue(
            "2026-01-01", today="2026-02-05"
        ) is is_reinvestigation_overdue("2026-01-01", today="2026-02-05", extension_applies=False)


class TestReinvestigationModel:
    def test_default_status_is_not_started(self):
        r = Reinvestigation(case_id="C-0001", account_ref="****1234", opened_date="2026-01-01")
        assert r.status == ReinvestigationStatus.NOT_STARTED
        assert r.completed_date is None


class TestInvalidDateInput:
    def test_invalid_date_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid date format"):
            reinvestigation_deadline("not-a-date")

    def test_invalid_overdue_date_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid date format"):
            is_reinvestigation_overdue("01/01/2026", today="2026-01-20")

"""Tests for FCRA 15 USC 1681i reinvestigation support (research-identified gap)."""

from __future__ import annotations

from packages.credit_command_center import (
    REINVESTIGATION_WINDOW_DAYS,
    Reinvestigation,
    ReinvestigationStatus,
    is_reinvestigation_overdue,
    reinvestigation_deadline,
)


def test_window_is_30_days():
    assert REINVESTIGATION_WINDOW_DAYS == 30


def test_deadline_adds_30_days():
    assert reinvestigation_deadline("2026-01-01") == "2026-01-31"


def test_not_overdue_within_window():
    assert is_reinvestigation_overdue("2026-01-01", today="2026-01-20") is False


def test_overdue_after_window():
    assert is_reinvestigation_overdue("2026-01-01", today="2026-02-01") is True


def test_reinvestigation_model_defaults():
    r = Reinvestigation(case_id="C-0001", account_ref="****1234", opened_date="2026-01-01")
    assert r.status == ReinvestigationStatus.NOT_STARTED
    assert r.completed_date is None

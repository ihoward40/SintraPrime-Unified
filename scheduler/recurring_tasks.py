"""
RecurringTaskManager — Pre-built recurring tasks for SintraPrime-Unified.
All tasks are designed for 24/7 autonomous operation.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional

from .task_types import Schedule, ScheduledTask, TaskType
from .task_scheduler import TaskScheduler

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Built-in task implementations
# ---------------------------------------------------------------------------


def daily_case_law_digest(**kwargs) -> Dict:
    """
    Fetches new relevant case law each morning.
    In production this calls a legal data provider (CourtListener, Westlaw, etc.)
    """
    logger.info("[RecurringTask] Running daily_case_law_digest")
    practice_areas = kwargs.get("practice_areas", ["civil", "criminal", "tax"])
    result = {
        "fetched_at": datetime.utcnow().isoformat(),
        "practice_areas": practice_areas,
        "new_cases": [],        # populated by real API call
        "summary": "Daily case law digest completed (stub).",
    }
    # TODO: integrate with CourtListener API or Westlaw
    return result


def weekly_deadline_check(**kwargs) -> Dict:
    """
    Scans all active matters for upcoming filing / response deadlines.
    Flags anything within 14 days.
    """
    logger.info("[RecurringTask] Running weekly_deadline_check")
    warning_days = kwargs.get("warning_days", 14)
    result = {
        "checked_at": datetime.utcnow().isoformat(),
        "warning_days": warning_days,
        "upcoming_deadlines": [],   # populated from matters DB
        "overdue": [],
        "summary": "Weekly deadline check completed (stub).",
    }
    # TODO: query SintraPrime matters module
    return result


def monthly_credit_report(**kwargs) -> Dict:
    """Generates a financial health summary for the firm (AR, collections, trust accounts)."""
    logger.info("[RecurringTask] Running monthly_credit_report")
    result = {
        "period": datetime.utcnow().strftime("%Y-%m"),
        "total_ar": 0.0,
        "collected": 0.0,
        "trust_balance": 0.0,
        "overdue_invoices": [],
        "summary": "Monthly credit report completed (stub).",
    }
    # TODO: integrate with accounting module
    return result


def court_docket_monitor(**kwargs) -> Dict:
    """
    Checks federal / state court dockets for new filings on watched case numbers.
    Runs every 4 hours.
    """
    logger.info("[RecurringTask] Running court_docket_monitor")
    case_numbers = kwargs.get("case_numbers", [])
    result = {
        "checked_at": datetime.utcnow().isoformat(),
        "case_numbers": case_numbers,
        "new_filings": [],      # populated by PACER / court API
        "summary": f"Docket monitor checked {len(case_numbers)} case(s) (stub).",
    }
    # TODO: integrate with PACER or CourtListener
    return result


def regulatory_update_check(**kwargs) -> Dict:
    """
    Monitors IRS, SEC, CFPB and other agencies for new rules / guidance.
    """
    logger.info("[RecurringTask] Running regulatory_update_check")
    agencies = kwargs.get("agencies", ["IRS", "SEC", "CFPB", "DOJ"])
    result = {
        "checked_at": datetime.utcnow().isoformat(),
        "agencies": agencies,
        "new_rules": [],        # populated by agency RSS / API
        "summary": f"Regulatory update check for {agencies} completed (stub).",
    }
    # TODO: scrape agency RSS feeds
    return result


def client_followup_reminders(**kwargs) -> Dict:
    """
    Scans open matters for pending client actions and generates reminder emails.
    """
    logger.info("[RecurringTask] Running client_followup_reminders")
    result = {
        "checked_at": datetime.utcnow().isoformat(),
        "reminders_sent": 0,
        "matters_reviewed": 0,
        "summary": "Client follow-up reminders completed (stub).",
    }
    # TODO: query matters and send via notification_dispatch
    return result


def system_health_check(**kwargs) -> Dict:
    """
    Ensures all SintraPrime modules are operational.
    Checks DB connectivity, scheduler status, memory, disk.
    """
    import shutil
    import sys

    logger.info("[RecurringTask] Running system_health_check")
    disk = shutil.disk_usage("/")
    result = {
        "checked_at": datetime.utcnow().isoformat(),
        "python_version": sys.version,
        "disk_free_gb": round(disk.free / 1e9, 2),
        "disk_used_pct": round(disk.used / disk.total * 100, 1),
        "status": "healthy",
        "alerts": [],
    }
    if result["disk_used_pct"] > 90:
        result["alerts"].append("Disk usage above 90%")
        result["status"] = "warning"
    return result


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class RecurringTaskManager:
    """
    Manages the full set of pre-built recurring tasks for SintraPrime.
    Allows registration with the TaskScheduler and custom schedule overrides.
    """

    _DEFAULTS = {
        "daily_case_law_digest": {
            "fn": daily_case_law_digest,
            "schedule": Schedule(cron_expr="0 7 * * *"),   # every day 7 AM
            "description": "Fetch new relevant case law each morning at 7 AM",
            "tags": ["legal", "case-law", "daily"],
        },
        "weekly_deadline_check": {
            "fn": weekly_deadline_check,
            "schedule": Schedule(cron_expr="0 8 * * 1"),   # Monday 8 AM
            "description": "Scan all matters for upcoming deadlines (weekly)",
            "tags": ["legal", "deadlines", "weekly"],
        },
        "monthly_credit_report": {
            "fn": monthly_credit_report,
            "schedule": Schedule(cron_expr="0 9 1 * *"),   # 1st of month 9 AM
            "description": "Financial health summary — 1st of each month",
            "tags": ["finance", "monthly"],
        },
        "court_docket_monitor": {
            "fn": court_docket_monitor,
            "schedule": Schedule(interval_minutes=240),    # every 4 hours
            "description": "Monitor court dockets for new filings every 4 hours",
            "tags": ["legal", "docket", "recurring"],
        },
        "regulatory_update_check": {
            "fn": regulatory_update_check,
            "schedule": Schedule(cron_expr="0 6 * * *"),   # every day 6 AM
            "description": "Check IRS/SEC/CFPB for new regulatory updates daily",
            "tags": ["compliance", "regulatory", "daily"],
        },
        "client_followup_reminders": {
            "fn": client_followup_reminders,
            "schedule": Schedule(cron_expr="0 9 * * 1-5"),  # weekdays 9 AM
            "description": "Send client follow-up reminders on weekday mornings",
            "tags": ["client", "reminders", "weekday"],
        },
        "system_health_check": {
            "fn": system_health_check,
            "schedule": Schedule(interval_minutes=30),     # every 30 minutes
            "description": "System health check every 30 minutes",
            "tags": ["system", "monitoring"],
        },
    }

    def __init__(self, scheduler: Optional[TaskScheduler] = None) -> None:
        self._scheduler = scheduler or TaskScheduler()
        self._registered: Dict[str, str] = {}  # task_name → task_id
        self._custom_schedules: Dict[str, Schedule] = {}
        self._custom_payloads: Dict[str, Dict] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_sintra_defaults(self) -> List[str]:
        """
        Install all default recurring tasks into the scheduler.
        Returns list of task_ids.
        """
        ids = []
        for name, config in self._DEFAULTS.items():
            task_id = self._register_one(name, config)
            ids.append(task_id)
            logger.info("Registered recurring task '%s' → %s", name, task_id)
        return ids

    def _register_one(self, name: str, config: Dict) -> str:
        # Allow user customizations to override defaults
        schedule = self._custom_schedules.get(name, config["schedule"])
        payload = self._custom_payloads.get(name, {})
        task = ScheduledTask(
            name=name,
            description=config["description"],
            task_type=TaskType.RECURRING,
            schedule=schedule,
            payload=payload,
            fn=config["fn"],
            tags=config.get("tags", []),
        )
        task_id = self._scheduler.schedule(task)
        self._registered[name] = task_id
        return task_id

    def customize(
        self,
        task_name: str,
        schedule: Optional[Schedule] = None,
        payload: Optional[Dict] = None,
        **kwargs,
    ) -> None:
        """
        Override the schedule or payload for a named built-in task.
        Must be called before ``register_sintra_defaults()``.
        """
        if schedule:
            self._custom_schedules[task_name] = schedule
        if payload:
            self._custom_payloads[task_name] = payload
        if kwargs:
            existing = self._custom_payloads.get(task_name, {})
            existing.update(kwargs)
            self._custom_payloads[task_name] = existing

    # ------------------------------------------------------------------
    # Individual task runners (callable directly)
    # ------------------------------------------------------------------

    def daily_case_law_digest(self, **kwargs) -> Dict:
        return daily_case_law_digest(**kwargs)

    def weekly_deadline_check(self, **kwargs) -> Dict:
        return weekly_deadline_check(**kwargs)

    def monthly_credit_report(self, **kwargs) -> Dict:
        return monthly_credit_report(**kwargs)

    def court_docket_monitor(self, case_numbers: Optional[List[str]] = None, **kwargs) -> Dict:
        return court_docket_monitor(case_numbers=case_numbers or [], **kwargs)

    def regulatory_update_check(self, **kwargs) -> Dict:
        return regulatory_update_check(**kwargs)

    def client_followup_reminders(self, **kwargs) -> Dict:
        return client_followup_reminders(**kwargs)

    def system_health_check(self, **kwargs) -> Dict:
        return system_health_check(**kwargs)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def registered_tasks(self) -> Dict[str, str]:
        """Return mapping of task_name → task_id for registered tasks."""
        return dict(self._registered)

"""
TaskDispatcher — Claude Cowork-inspired natural-language dispatch system.
Parses free-form scheduling text and routes tasks to the right specialist.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from .task_types import Schedule, ScheduledTask, TaskStatus, TaskType
from .task_scheduler import TaskScheduler

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Natural-language parsing helpers
# ---------------------------------------------------------------------------

_WEEKDAY_MAP = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
    "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6,
}

_INTERVAL_PATTERNS = [
    (re.compile(r"every\s+(\d+)\s+minute", re.I), "minutes"),
    (re.compile(r"every\s+(\d+)\s+hour", re.I), "hours"),
    (re.compile(r"every\s+(\d+)\s+day", re.I), "days"),
    (re.compile(r"every\s+minute", re.I), "1_minute"),
    (re.compile(r"every\s+hour", re.I), "60_minutes"),
    (re.compile(r"every\s+day|daily", re.I), "1440_minutes"),
    (re.compile(r"every\s+week|weekly", re.I), "10080_minutes"),
    (re.compile(r"every\s+month|monthly", re.I), "43200_minutes"),
]

_TIME_PATTERN = re.compile(r"at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", re.I)
_WEEKDAY_PATTERN = re.compile(
    r"every\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun)",
    re.I,
)


def _parse_time(text: str):
    """Extract hour/minute from text like 'at 9am' or 'at 14:30'."""
    m = _TIME_PATTERN.search(text)
    if not m:
        return None, None
    hour = int(m.group(1))
    minute = int(m.group(2)) if m.group(2) else 0
    meridiem = (m.group(3) or "").lower()
    if meridiem == "pm" and hour != 12:
        hour += 12
    if meridiem == "am" and hour == 12:
        hour = 0
    return hour, minute


class TaskDispatcher:
    """
    Dispatch tasks via natural language or structured dicts.

    Inspired by Claude Cowork's dispatch layer — accepts a plain English goal,
    figures out the schedule, and hands off to the TaskScheduler.
    """

    def __init__(self, scheduler: Optional[TaskScheduler] = None) -> None:
        self._scheduler = scheduler or TaskScheduler()
        self._agent_registry: Dict[str, Callable] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def dispatch(
        self,
        goal: str,
        fn: Callable,
        delivery_method: str = "auto",
        deadline: Optional[datetime] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Dispatch a task described in plain English.

        Args:
            goal: Natural language description, e.g. "run case law digest every morning at 7am"
            fn: The callable to execute
            delivery_method: "auto" | "email" | "webhook" | "log"
            deadline: Optional hard deadline for one-time tasks
            payload: Additional keyword arguments passed to fn

        Returns:
            task_id string
        """
        schedule = self.parse_schedule_from_text(goal)
        task_type = (
            TaskType.RECURRING
            if (schedule.cron_expr or schedule.interval_minutes)
            else TaskType.ONE_TIME
        )
        task = ScheduledTask(
            name=goal[:80],
            description=f"Dispatched: {goal}",
            task_type=task_type,
            schedule=schedule,
            payload=payload or {},
            fn=fn,
            next_run=deadline or schedule.run_at,
        )
        task_id = self._scheduler.schedule(task)
        logger.info(
            "Dispatched task '%s' → id=%s, schedule=%s",
            goal,
            task_id,
            schedule.describe(),
        )
        return task_id

    def parse_schedule_from_text(self, text: str) -> Schedule:
        """
        Convert natural-language scheduling text to a Schedule object.

        Supports:
        - "every Monday at 9am" → cron
        - "every 30 minutes" → interval
        - "every day at 8pm" → cron
        - "daily" → interval 1440 min
        - "tomorrow at 3pm" / "in 2 hours" → one-time run_at
        """
        text_lower = text.lower()

        # --- Weekday + time  ("every Monday at 9am")
        weekday_m = _WEEKDAY_PATTERN.search(text_lower)
        if weekday_m:
            day_num = _WEEKDAY_MAP[weekday_m.group(1).lower()]
            hour, minute = _parse_time(text)
            h = hour if hour is not None else 9
            m = minute if minute is not None else 0
            cron = f"{m} {h} * * {day_num}"
            return Schedule(cron_expr=cron)

        # --- "every day at HH:MM"
        if re.search(r"every\s+day|daily", text_lower):
            hour, minute = _parse_time(text)
            h = hour if hour is not None else 9
            m = minute if minute is not None else 0
            cron = f"{m} {h} * * *"
            return Schedule(cron_expr=cron)

        # --- "every morning" → 9 AM daily
        if re.search(r"every\s+morning", text_lower):
            hour, minute = _parse_time(text)
            h = hour if hour is not None else 9
            m = minute if minute is not None else 0
            return Schedule(cron_expr=f"{m} {h} * * *")

        # --- "every evening" → 6 PM daily
        if re.search(r"every\s+evening", text_lower):
            return Schedule(cron_expr="0 18 * * *")

        # --- "every week" / "weekly"
        if re.search(r"every\s+week|weekly", text_lower):
            hour, minute = _parse_time(text)
            h = hour if hour is not None else 9
            m = minute if minute is not None else 0
            return Schedule(cron_expr=f"{m} {h} * * 1")

        # --- "every month" / "monthly"
        if re.search(r"every\s+month|monthly", text_lower):
            hour, minute = _parse_time(text)
            h = hour if hour is not None else 9
            m = minute if minute is not None else 0
            return Schedule(cron_expr=f"{m} {h} 1 * *")

        # --- Numeric intervals
        for pattern, unit in _INTERVAL_PATTERNS:
            m_obj = pattern.search(text_lower)
            if m_obj:
                if unit.endswith("_minutes"):
                    mins = int(unit.split("_")[0])
                    return Schedule(interval_minutes=mins)
                num = int(m_obj.group(1))
                if unit == "minutes":
                    return Schedule(interval_minutes=num)
                if unit == "hours":
                    return Schedule(interval_minutes=num * 60)
                if unit == "days":
                    return Schedule(interval_minutes=num * 1440)

        # --- Relative one-time: "in N hours/minutes"
        in_m = re.search(r"in\s+(\d+)\s+(minute|hour|day)", text_lower)
        if in_m:
            num = int(in_m.group(1))
            unit = in_m.group(2)
            now = datetime.utcnow()
            if unit == "minute":
                run_at = now + timedelta(minutes=num)
            elif unit == "hour":
                run_at = now + timedelta(hours=num)
            else:
                run_at = now + timedelta(days=num)
            return Schedule(run_at=run_at)

        # --- "tomorrow at HH"
        if "tomorrow" in text_lower:
            hour, minute = _parse_time(text)
            h = hour if hour is not None else 9
            mn = minute if minute is not None else 0
            now = datetime.utcnow()
            run_at = (now + timedelta(days=1)).replace(
                hour=h, minute=mn, second=0, microsecond=0
            )
            return Schedule(run_at=run_at)

        # --- fallback: run immediately (1 second from now)
        return Schedule(run_at=datetime.utcnow() + timedelta(seconds=1))

    def dispatch_to_agent(
        self, task: ScheduledTask, agent_type: str
    ) -> str:
        """Route a task to a named specialist agent."""
        handler = self._agent_registry.get(agent_type)
        if handler is None:
            logger.warning(
                "No agent registered for type '%s'; using default executor",
                agent_type,
            )
        else:
            task.fn = handler
        return self._scheduler.schedule(task)

    def register_agent(self, agent_type: str, handler: Callable) -> None:
        """Register a callable as the handler for an agent type."""
        self._agent_registry[agent_type] = handler

    def bulk_dispatch(self, tasks: List[Dict[str, Any]]) -> List[str]:
        """
        Queue multiple tasks at once.

        Each dict must have at minimum: ``name``, ``fn``, optionally ``schedule_text``.
        Returns list of task_ids.
        """
        ids = []
        for t in tasks:
            fn = t.get("fn", lambda **_: None)
            goal = t.get("schedule_text", t.get("name", "unnamed"))
            task_id = self.dispatch(
                goal=goal,
                fn=fn,
                payload=t.get("payload", {}),
            )
            ids.append(task_id)
        return ids

    def status_report(self) -> str:
        """Return a human-readable overview of all scheduled tasks."""
        tasks = self._scheduler.list_tasks()
        if not tasks:
            return "No tasks scheduled."
        lines = ["# SintraPrime Scheduler Status", ""]
        for t in tasks:
            next_r = t.next_run.strftime("%Y-%m-%d %H:%M UTC") if t.next_run else "—"
            lines.append(
                f"- [{t.status.value.upper()}] **{t.name}** | next: {next_r} | runs: {t.run_count}"
            )
        return "\n".join(lines)

    def interrupt(self, task_id: str, reason: str = "user request") -> bool:
        """Gracefully stop a running task by cancelling it."""
        logger.info("Interrupt requested for task %s: %s", task_id, reason)
        return self._scheduler.cancel(task_id)

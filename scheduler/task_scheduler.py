"""
TaskScheduler — Core APScheduler-backed (with threading fallback) scheduler.
Persists tasks to SQLite so they survive process restarts.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional

from .task_types import Schedule, ScheduledTask, TaskResult, TaskStatus, TaskType

logger = logging.getLogger(__name__)

_DB_DEFAULT = "sintra_scheduler.db"


class TaskScheduler:
    """
    Central scheduler for SintraPrime-Unified.

    Tries to use APScheduler when available; falls back to a lightweight
    threading-based timer loop so the module always works without optional
    dependencies.

    All task metadata is persisted in SQLite, meaning:
      - tasks survive process restarts
      - run history is kept per task
    """

    def __init__(self, db_path: str = _DB_DEFAULT) -> None:
        self._db_path = db_path
        self._tasks: Dict[str, ScheduledTask] = {}
        self._lock = threading.Lock()
        self._running = False
        self._timer_threads: Dict[str, threading.Timer] = {}
        self._apscheduler = None
        self._init_db()
        self._load_from_db()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the scheduler daemon."""
        if self._running:
            return
        self._running = True
        try:
            from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore

            self._apscheduler = BackgroundScheduler()
            self._apscheduler.start()
            logger.info("TaskScheduler started (APScheduler backend)")
        except ImportError:
            logger.info("TaskScheduler started (threading fallback backend)")

    def stop(self) -> None:
        """Stop the scheduler daemon gracefully."""
        self._running = False
        for timer in self._timer_threads.values():
            timer.cancel()
        self._timer_threads.clear()
        if self._apscheduler:
            self._apscheduler.shutdown(wait=False)
            self._apscheduler = None
        logger.info("TaskScheduler stopped")

    # ------------------------------------------------------------------
    # Scheduling API
    # ------------------------------------------------------------------

    def schedule(self, task: ScheduledTask) -> str:
        """Register and schedule a task. Returns the task_id."""
        with self._lock:
            self._tasks[task.id] = task
        self._persist_task(task)
        self._arm(task)
        logger.info("Scheduled task '%s' (id=%s)", task.name, task.id)
        return task.id

    def schedule_once(
        self,
        name: str,
        fn: Callable,
        run_at: datetime,
        payload: Optional[Dict] = None,
    ) -> str:
        """Convenience: schedule a one-time task."""
        task = ScheduledTask(
            name=name,
            task_type=TaskType.ONE_TIME,
            schedule=Schedule(run_at=run_at),
            payload=payload or {},
            fn=fn,
        )
        return self.schedule(task)

    def schedule_recurring(
        self,
        name: str,
        fn: Callable,
        interval_minutes: Optional[int] = None,
        cron: Optional[str] = None,
        payload: Optional[Dict] = None,
    ) -> str:
        """Convenience: schedule a recurring task."""
        task = ScheduledTask(
            name=name,
            task_type=TaskType.RECURRING,
            schedule=Schedule(cron_expr=cron, interval_minutes=interval_minutes),
            payload=payload or {},
            fn=fn,
        )
        return self.schedule(task)

    def cancel(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            task.status = TaskStatus.CANCELLED
        self._disarm(task_id)
        self._persist_task(task)
        logger.info("Cancelled task id=%s", task_id)
        return True

    def pause(self, task_id: str) -> bool:
        """Pause a running/scheduled task."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            task.status = TaskStatus.PAUSED
        self._disarm(task_id)
        self._persist_task(task)
        logger.info("Paused task id=%s", task_id)
        return True

    def resume(self, task_id: str) -> bool:
        """Resume a paused task."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.status != TaskStatus.PAUSED:
                return False
            task.status = TaskStatus.PENDING
        self._persist_task(task)
        self._arm(task)
        logger.info("Resumed task id=%s", task_id)
        return True

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------

    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[ScheduledTask]:
        """Return all tasks, optionally filtered by status."""
        with self._lock:
            tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Return a single task by id."""
        with self._lock:
            return self._tasks.get(task_id)

    def next_run_time(self, task_id: str) -> Optional[datetime]:
        """Return when a task is next scheduled to run."""
        with self._lock:
            task = self._tasks.get(task_id)
        return task.next_run if task else None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _arm(self, task: ScheduledTask) -> None:
        """Set up the actual timer/scheduler job for a task."""
        if task.status in (TaskStatus.CANCELLED, TaskStatus.PAUSED):
            return

        if self._apscheduler:
            self._arm_apscheduler(task)
        else:
            self._arm_threading(task)

    def _arm_apscheduler(self, task: ScheduledTask) -> None:
        """Use APScheduler to arm the task."""
        try:
            from apscheduler.triggers.cron import CronTrigger  # type: ignore
            from apscheduler.triggers.interval import IntervalTrigger  # type: ignore

            sched = task.schedule
            if sched is None:
                return

            job_kwargs = dict(
                func=self._run_task,
                args=[task.id],
                id=task.id,
                replace_existing=True,
            )

            if sched.cron_expr:
                trigger = CronTrigger.from_crontab(sched.cron_expr)
            elif sched.interval_minutes:
                trigger = IntervalTrigger(minutes=sched.interval_minutes)
            elif sched.run_at:
                trigger = sched.run_at
                task.next_run = sched.run_at
            else:
                return

            self._apscheduler.add_job(trigger=trigger, **job_kwargs)
        except Exception as exc:
            logger.error("APScheduler arm failed for task %s: %s", task.id, exc)

    def _arm_threading(self, task: ScheduledTask) -> None:
        """Fallback: use threading.Timer for one-shot and polling for recurring."""
        sched = task.schedule
        if sched is None:
            return

        now = datetime.utcnow()

        if sched.run_at:
            delay = max(0.0, (sched.run_at - now).total_seconds())
            task.next_run = sched.run_at
            timer = threading.Timer(delay, self._run_task, args=[task.id])
            timer.daemon = True
            timer.start()
            self._timer_threads[task.id] = timer

        elif sched.interval_minutes:
            delay = sched.interval_minutes * 60
            task.next_run = now + timedelta(minutes=sched.interval_minutes)
            self._schedule_recurring_thread(task.id, delay)

    def _schedule_recurring_thread(self, task_id: str, interval_seconds: float) -> None:
        def _fire():
            if not self._running:
                return
            with self._lock:
                task = self._tasks.get(task_id)
            if task and task.status not in (TaskStatus.CANCELLED, TaskStatus.PAUSED):
                self._run_task(task_id)
                task.next_run = datetime.utcnow() + timedelta(seconds=interval_seconds)
                self._persist_task(task)
                timer = threading.Timer(interval_seconds, _fire)
                timer.daemon = True
                timer.start()
                self._timer_threads[task_id] = timer

        timer = threading.Timer(interval_seconds, _fire)
        timer.daemon = True
        timer.start()
        self._timer_threads[task_id] = timer

    def _disarm(self, task_id: str) -> None:
        timer = self._timer_threads.pop(task_id, None)
        if timer:
            timer.cancel()
        if self._apscheduler:
            try:
                self._apscheduler.remove_job(task_id)
            except Exception:
                pass

    def _run_task(self, task_id: str) -> None:
        """Execute the task's callable and record the result."""
        with self._lock:
            task = self._tasks.get(task_id)
        if not task or task.fn is None:
            return

        start = datetime.utcnow()
        task.status = TaskStatus.RUNNING
        task.last_run = start
        task.run_count += 1
        self._persist_task(task)

        try:
            output = task.fn(**task.payload)
            duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
            result = TaskResult(
                task_id=task_id,
                success=True,
                output=output,
                duration_ms=duration_ms,
            )
            task.status = (
                TaskStatus.COMPLETED
                if task.task_type == TaskType.ONE_TIME
                else TaskStatus.PENDING
            )
            if task.on_success:
                try:
                    task.on_success(result)
                except Exception:
                    pass
        except Exception as exc:  # noqa: BLE001
            duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
            import traceback

            result = TaskResult(
                task_id=task_id,
                success=False,
                error=traceback.format_exc(),
                duration_ms=duration_ms,
            )
            task.retry_count += 1
            if task.retry_count < task.max_retries:
                task.status = TaskStatus.PENDING
            else:
                task.status = TaskStatus.FAILED
            if task.on_failure:
                try:
                    task.on_failure(result)
                except Exception:
                    pass
            logger.error("Task %s failed: %s", task_id, exc)

        self._persist_task(task)
        self._persist_result(result)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS task_results (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _persist_task(self, task: ScheduledTask) -> None:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO tasks (id, data, updated_at) VALUES (?, ?, ?)",
                    (task.id, json.dumps(task.to_dict()), datetime.utcnow().isoformat()),
                )
                conn.commit()
        except Exception as exc:
            logger.warning("Failed to persist task %s: %s", task.id, exc)

    def _persist_result(self, result: TaskResult) -> None:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO task_results (id, task_id, data, timestamp) VALUES (?, ?, ?, ?)",
                    (
                        str(uuid.uuid4()),
                        result.task_id,
                        json.dumps(result.to_dict()),
                        result.timestamp.isoformat(),
                    ),
                )
                conn.commit()
        except Exception as exc:
            logger.warning("Failed to persist result for task %s: %s", result.task_id, exc)

    def _load_from_db(self) -> None:
        try:
            with sqlite3.connect(self._db_path) as conn:
                rows = conn.execute("SELECT data FROM tasks").fetchall()
            for (data_str,) in rows:
                data = json.loads(data_str)
                task = ScheduledTask.from_dict(data)
                # Don't auto-resume cancelled / failed tasks on reload
                if task.status in (TaskStatus.RUNNING,):
                    task.status = TaskStatus.PENDING
                with self._lock:
                    self._tasks[task.id] = task
            logger.info("Loaded %d tasks from SQLite", len(rows))
        except Exception as exc:
            logger.warning("Could not load tasks from DB: %s", exc)

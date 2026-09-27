from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

# Intentionally long hold while a job is in RUNNING to prevent it from being
# re-claimed as ready before the worker reports completion/failure.
RUNNING_LEASE_DURATION = timedelta(days=36500)


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class RetryPolicy:
    max_attempts: int = 5
    base_delay_seconds: int = 1
    max_delay_seconds: int = 60

    def delay_for_attempt(self, attempt: int) -> int:
        return min(self.max_delay_seconds, self.base_delay_seconds * (2 ** max(0, attempt - 1)))


@dataclass(slots=True)
class AsyncJob:
    task_id: str
    payload: dict[str, Any]
    status: JobStatus
    attempts: int
    last_error: str | None
    callback_url: str | None
    run_after: datetime
    created_at: datetime
    updated_at: datetime


class AsyncJobQueue:
    """Durable queue with retry tracking and webhook callback hooks."""

    def __init__(
        self,
        *,
        db_path: Path,
        retry_policy: RetryPolicy | None = None,
        webhook_sender: Callable[[str, str, dict[str, Any]], None] | None = None,
    ) -> None:
        self._db_path = Path(db_path)
        self._retry_policy = retry_policy or RetryPolicy()
        self._webhook_sender = webhook_sender
        self._ensure_schema()

    def submit(self, payload: dict[str, Any], callback_url: str | None = None) -> AsyncJob:
        now = datetime.now(UTC)
        task_id = f"job-{uuid4().hex}"
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO async_jobs(task_id, status, payload, attempts, last_error, callback_url, run_after, created_at, updated_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    JobStatus.PENDING.value,
                    json.dumps(payload, sort_keys=True),
                    0,
                    None,
                    callback_url,
                    now.isoformat(),
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
        return self.get(task_id)

    def claim_next_ready(self, *, as_of: datetime | None = None) -> AsyncJob | None:
        current = as_of or datetime.now(UTC)
        running_hold_until = current + RUNNING_LEASE_DURATION
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                UPDATE async_jobs
                SET status = :status_running,
                    attempts = attempts + 1,
                    run_after = :run_after,
                    updated_at = :updated_at
                WHERE task_id = (
                    SELECT task_id
                    FROM async_jobs
                    WHERE status IN (:status_pending, :status_retrying) AND run_after <= :ready_at
                    ORDER BY created_at ASC
                    LIMIT 1
                )
                RETURNING task_id
                """,
                {
                    "status_running": JobStatus.RUNNING.value,
                    "run_after": running_hold_until.isoformat(),
                    "updated_at": current.isoformat(),
                    "status_pending": JobStatus.PENDING.value,
                    "status_retrying": JobStatus.RETRYING.value,
                    "ready_at": current.isoformat(),
                },
            ).fetchone()
            if row is None:
                conn.commit()
                return None
            conn.commit()
        return self.get(row[0])

    def mark_completed(self, task_id: str, *, result: dict[str, Any]) -> AsyncJob:
        now = datetime.now(UTC)
        with sqlite3.connect(self._db_path) as conn:
            updated = conn.execute(
                """
                UPDATE async_jobs SET status = ?, last_error = NULL, updated_at = ?
                WHERE task_id = ? AND status = ?
                """,
                (JobStatus.COMPLETED.value, now.isoformat(), task_id, JobStatus.RUNNING.value),
            ).rowcount
        if updated == 0:
            raise KeyError(task_id)
        self._emit_webhook(task_id, "completed", result)
        return self.get(task_id)

    def mark_failed(self, task_id: str, *, error: str) -> AsyncJob:
        now = datetime.now(UTC)
        status = JobStatus.FAILED
        run_after = now
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT attempts, status FROM async_jobs WHERE task_id = ?
                """,
                (task_id,),
            ).fetchone()
            if row is None:
                conn.commit()
                raise KeyError(task_id)
            attempts, current_status = row
            if JobStatus(current_status) is not JobStatus.RUNNING:
                conn.commit()
                raise ValueError("job must be running before it can fail")
            if attempts >= self._retry_policy.max_attempts:
                status = JobStatus.FAILED
            else:
                status = JobStatus.RETRYING
                delay = self._retry_policy.delay_for_attempt(attempts)
                run_after = now + timedelta(seconds=delay)
            updated = conn.execute(
                """
                UPDATE async_jobs
                SET status = ?, last_error = ?, run_after = ?, updated_at = ?
                WHERE task_id = ? AND status = ?
                """,
                (
                    status.value,
                    error,
                    run_after.isoformat(),
                    now.isoformat(),
                    task_id,
                    JobStatus.RUNNING.value,
                ),
            ).rowcount
            conn.commit()
        if updated == 0:
            raise ValueError("job must be running before it can fail")
        if status is JobStatus.FAILED:
            self._emit_webhook(task_id, "failed", {"error": error})
        return self.get(task_id)

    def get(self, task_id: str) -> AsyncJob | None:
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                """
                SELECT task_id, payload, status, attempts, last_error, callback_url, run_after, created_at, updated_at
                FROM async_jobs WHERE task_id = ?
                """,
                (task_id,),
            ).fetchone()
        if row is None:
            return None
        return AsyncJob(
            task_id=row[0],
            payload=json.loads(row[1]),
            status=JobStatus(row[2]),
            attempts=row[3],
            last_error=row[4],
            callback_url=row[5],
            run_after=datetime.fromisoformat(row[6]),
            created_at=datetime.fromisoformat(row[7]),
            updated_at=datetime.fromisoformat(row[8]),
        )

    def _emit_webhook(self, task_id: str, event: str, payload: dict[str, Any]) -> None:
        job = self.get(task_id)
        if job and job.callback_url and self._webhook_sender:
            self._webhook_sender(job.callback_url, event, payload)

    def _ensure_schema(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS async_jobs(
                    task_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    payload JSON NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    callback_url TEXT,
                    run_after TIMESTAMPTZ NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL
                )
                """
            )

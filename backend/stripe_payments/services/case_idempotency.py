"""SQLite-backed idempotency for monetization case starts."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .case_security import CaseSecurityError

CLAIMED = "CLAIMED"
PROCESSING = "PROCESSING"
SUCCEEDED = "SUCCEEDED"
FAILED_RETRYABLE = "FAILED_RETRYABLE"
FAILED_FINAL = "FAILED_FINAL"
ALLOWED_STATUSES = {CLAIMED, PROCESSING, SUCCEEDED, FAILED_RETRYABLE, FAILED_FINAL}


class IdempotencyConflictError(ValueError):
    """Raised when an event id is reused unsafely or is already in progress."""


@dataclass(frozen=True)
class IdempotencyClaim:
    action: str
    status: str
    response_json: dict[str, Any] | None = None
    attempt_count: int = 0


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class SQLiteIdempotencyStore:
    def __init__(self, db_path: Path, *, stale_after_seconds: int = 900) -> None:
        self.db_path = db_path
        self.stale_after_seconds = stale_after_seconds
        self._ensure_path_contained()
        self._init_db()

    def _ensure_path_contained(self) -> None:
        root = self.db_path.parent.resolve()
        target = self.db_path.resolve() if self.db_path.exists() else (root / self.db_path.name).resolve()
        if target.parent != root:
            raise CaseSecurityError("idempotency database path escaped its directory")

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(str(self.db_path), timeout=30, isolation_level=None)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA foreign_keys=ON")
        return con

    def _init_db(self) -> None:
        with self._connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS case_start_events (
                    event_id TEXT PRIMARY KEY,
                    body_digest TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    payment_session_id TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('CLAIMED','PROCESSING','SUCCEEDED','FAILED_RETRYABLE','FAILED_FINAL')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    response_json TEXT,
                    error_code TEXT,
                    attempt_count INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            con.execute("CREATE INDEX IF NOT EXISTS idx_case_start_events_case_id ON case_start_events(case_id)")

    def claim(self, *, event_id: str, body_digest: str, case_id: str, payment_session_id: str) -> IdempotencyClaim:
        now = utc_now_iso()
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM case_start_events WHERE event_id = ?", (event_id,)).fetchone()
            if row is None:
                con.execute(
                    """
                    INSERT INTO case_start_events(event_id, body_digest, case_id, payment_session_id, status, created_at, updated_at, attempt_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (event_id, body_digest, case_id, payment_session_id, CLAIMED, now, now),
                )
                con.commit()
                return IdempotencyClaim(action="claimed", status=CLAIMED, attempt_count=1)

            if row["body_digest"] != body_digest or row["case_id"] != case_id or row["payment_session_id"] != payment_session_id:
                con.rollback()
                raise IdempotencyConflictError("event_id was reused with a different payload, case, or payment session")

            status = row["status"]
            if status == SUCCEEDED:
                payload = json.loads(row["response_json"] or "{}")
                con.commit()
                return IdempotencyClaim(action="replay", status=SUCCEEDED, response_json=payload, attempt_count=row["attempt_count"])
            if status == FAILED_FINAL:
                con.rollback()
                raise IdempotencyConflictError("event_id previously failed permanently")
            if status in {CLAIMED, PROCESSING} and not self._is_stale(row["updated_at"]):
                con.rollback()
                raise IdempotencyConflictError("event_id is already being processed")

            con.execute(
                "UPDATE case_start_events SET status = ?, updated_at = ?, attempt_count = attempt_count + 1 WHERE event_id = ?",
                (CLAIMED, now, event_id),
            )
            row2 = con.execute("SELECT attempt_count FROM case_start_events WHERE event_id = ?", (event_id,)).fetchone()
            con.commit()
            return IdempotencyClaim(action="reclaimed", status=CLAIMED, attempt_count=int(row2["attempt_count"]))

    def _is_stale(self, updated_at: str) -> bool:
        try:
            parsed = datetime.fromisoformat(updated_at).astimezone(UTC)
        except ValueError:
            return True
        return parsed < datetime.now(UTC) - timedelta(seconds=self.stale_after_seconds)

    def set_status(self, event_id: str, status: str, *, error_code: str | None = None) -> None:
        if status not in ALLOWED_STATUSES:
            raise ValueError(f"unsupported idempotency status: {status}")
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                "UPDATE case_start_events SET status = ?, updated_at = ?, error_code = COALESCE(?, error_code) WHERE event_id = ?",
                (status, utc_now_iso(), error_code, event_id),
            )
            con.commit()

    def mark_succeeded(self, event_id: str, response_json: dict[str, Any]) -> None:
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                """
                UPDATE case_start_events
                   SET status = ?, updated_at = ?, response_json = ?, error_code = NULL
                 WHERE event_id = ? AND status != ?
                """,
                (SUCCEEDED, utc_now_iso(), json.dumps(response_json, sort_keys=True), event_id, SUCCEEDED),
            )
            con.commit()

    def get(self, event_id: str) -> dict[str, Any] | None:
        with self._connect() as con:
            row = con.execute("SELECT * FROM case_start_events WHERE event_id = ?", (event_id,)).fetchone()
            return dict(row) if row else None

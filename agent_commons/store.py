from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from .models import MessageRecord, RunStatus, SupervisorRun


class AgentCommonsStore:
    """Tenant-scoped SQLite persistence for local development and tests."""

    def __init__(self, database_path: str = ":memory:") -> None:
        if database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._migrate()

    def _migrate(self) -> None:
        with self._lock, self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS commons_messages (
                    message_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL, channel_id TEXT NOT NULL,
                    thread_id TEXT NOT NULL, task_id TEXT NOT NULL,
                    from_agent TEXT NOT NULL, to_agents_json TEXT NOT NULL,
                    status TEXT NOT NULL, payload_json TEXT NOT NULL,
                    evidence_json TEXT NOT NULL, correlation_id TEXT NOT NULL,
                    owner_decision_required INTEGER NOT NULL,
                    timestamp REAL NOT NULL, trace_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_commons_thread
                    ON commons_messages(tenant_id, workspace_id, channel_id, thread_id, timestamp);

                CREATE TABLE IF NOT EXISTS owner_approvals (
                    approval_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
                    run_id TEXT NOT NULL, reason TEXT NOT NULL,
                    status TEXT NOT NULL, decision_note TEXT,
                    created_at REAL NOT NULL, decided_at REAL
                );
                """
            )
            self._ensure_tenant_scoped_runs_table()

    def _ensure_tenant_scoped_runs_table(self) -> None:
        row = self._connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='supervisor_runs'"
        ).fetchone()
        if row is None:
            self._create_runs_table()
            return
        schema = (row["sql"] or "").replace("\n", " ").lower()
        legacy_global_unique = (
            "task_id text not null unique" in schema
            or "idempotency_key text unique" in schema
        )
        if not legacy_global_unique:
            return
        self._connection.execute("ALTER TABLE supervisor_runs RENAME TO supervisor_runs_legacy")
        self._create_runs_table()
        self._connection.execute(
            """INSERT INTO supervisor_runs (
                run_id, tenant_id, workspace_id, channel_id, thread_id, task_id,
                objective, owner_agent, builder_agent, reviewer_agent,
                acceptance_criteria_json, status, builder_result_json,
                review_result_json, reconciliation_json, approval_id,
                idempotency_key, created_at, updated_at
            ) SELECT
                run_id, tenant_id, workspace_id, channel_id, thread_id, task_id,
                objective, owner_agent, builder_agent, reviewer_agent,
                acceptance_criteria_json, status, builder_result_json,
                review_result_json, reconciliation_json, approval_id,
                idempotency_key, created_at, updated_at
            FROM supervisor_runs_legacy"""
        )
        self._connection.execute("DROP TABLE supervisor_runs_legacy")

    def _create_runs_table(self) -> None:
        self._connection.execute(
            """CREATE TABLE supervisor_runs (
                run_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL, channel_id TEXT NOT NULL,
                thread_id TEXT NOT NULL, task_id TEXT NOT NULL,
                objective TEXT NOT NULL, owner_agent TEXT NOT NULL,
                builder_agent TEXT NOT NULL, reviewer_agent TEXT NOT NULL,
                acceptance_criteria_json TEXT NOT NULL, status TEXT NOT NULL,
                builder_result_json TEXT, review_result_json TEXT,
                reconciliation_json TEXT, approval_id TEXT,
                idempotency_key TEXT, created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                UNIQUE (tenant_id, task_id),
                UNIQUE (tenant_id, idempotency_key)
            )"""
        )

    def append_message(self, message: MessageRecord) -> None:
        values = (
            message.message_id, message.tenant_id, message.workspace_id,
            message.channel_id, message.thread_id, message.task_id,
            message.from_agent, json.dumps(message.to_agents), message.status.value,
            json.dumps(message.payload), json.dumps(message.evidence),
            message.correlation_id, int(message.owner_decision_required),
            message.timestamp, json.dumps(message.trace),
        )
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT INTO commons_messages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                values,
            )

    def get_thread(
        self,
        tenant_id: str,
        workspace_id: str,
        channel_id: str,
        thread_id: str,
    ) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                """SELECT * FROM commons_messages
                   WHERE tenant_id=? AND workspace_id=? AND channel_id=? AND thread_id=?
                   ORDER BY timestamp ASC""",
                (tenant_id, workspace_id, channel_id, thread_id),
            ).fetchall()
            return [self._decode_message(row) for row in rows]

    def save_run(
        self,
        run: SupervisorRun,
        idempotency_key: str | None = None,
    ) -> SupervisorRun:
        with self._lock, self._connection:
            if idempotency_key:
                existing = self._connection.execute(
                    "SELECT run_id FROM supervisor_runs WHERE tenant_id=? AND idempotency_key=?",
                    (run.tenant_id, idempotency_key),
                ).fetchone()
                if existing:
                    return self.get_run(run.tenant_id, existing["run_id"])
            values = (
                run.run_id, run.tenant_id, run.workspace_id, run.channel_id,
                run.thread_id, run.task_id, run.objective, run.owner_agent,
                run.builder_agent, run.reviewer_agent,
                json.dumps(run.acceptance_criteria), run.status.value,
                self._json_or_none(run.builder_result),
                self._json_or_none(run.review_result),
                self._json_or_none(run.reconciliation), run.approval_id,
                idempotency_key, run.created_at, run.updated_at,
            )
            self._connection.execute(
                "INSERT INTO supervisor_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                values,
            )
        return run

    def update_run(self, run: SupervisorRun) -> None:
        run.updated_at = time.time()
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """UPDATE supervisor_runs SET status=?, builder_result_json=?,
                   review_result_json=?, reconciliation_json=?, approval_id=?, updated_at=?
                   WHERE tenant_id=? AND run_id=?""",
                (
                    run.status.value,
                    self._json_or_none(run.builder_result),
                    self._json_or_none(run.review_result),
                    self._json_or_none(run.reconciliation),
                    run.approval_id, run.updated_at, run.tenant_id, run.run_id,
                ),
            )
            if cursor.rowcount != 1:
                raise KeyError(f"run not found: {run.run_id}")

    def get_run(self, tenant_id: str, run_id: str) -> SupervisorRun:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM supervisor_runs WHERE tenant_id=? AND run_id=?",
                (tenant_id, run_id),
            ).fetchone()
            if row is None:
                raise KeyError(f"run not found: {run_id}")
            return self._decode_run(row)

    def list_runs(self, tenant_id: str, limit: int = 50) -> list[SupervisorRun]:
        bounded_limit = max(1, min(limit, 200))
        with self._lock:
            rows = self._connection.execute(
                """SELECT * FROM supervisor_runs
                   WHERE tenant_id=? ORDER BY updated_at DESC LIMIT ?""",
                (tenant_id, bounded_limit),
            ).fetchall()
            return [self._decode_run(row) for row in rows]

    def create_approval(self, tenant_id: str, run_id: str, reason: str) -> str:
        approval_id = uuid.uuid4().hex
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT INTO owner_approvals VALUES (?, ?, ?, ?, 'pending', NULL, ?, NULL)",
                (approval_id, tenant_id, run_id, reason, time.time()),
            )
        return approval_id

    def decide_approval(
        self,
        tenant_id: str,
        approval_id: str,
        approved: bool,
        note: str = "",
    ) -> None:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """UPDATE owner_approvals SET status=?, decision_note=?, decided_at=?
                   WHERE tenant_id=? AND approval_id=? AND status='pending'""",
                (
                    "approved" if approved else "rejected", note, time.time(),
                    tenant_id, approval_id,
                ),
            )
            if cursor.rowcount != 1:
                raise KeyError(f"pending approval not found: {approval_id}")

    @staticmethod
    def _json_or_none(value: Any) -> str | None:
        return None if value is None else json.dumps(value)

    @staticmethod
    def _decode_message(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        for key in ("to_agents_json", "payload_json", "evidence_json", "trace_json"):
            result[key.removesuffix("_json")] = json.loads(result.pop(key))
        result["owner_decision_required"] = bool(result["owner_decision_required"])
        return result

    @staticmethod
    def _decode_run(row: sqlite3.Row) -> SupervisorRun:
        def decode(key: str) -> Any:
            return json.loads(row[key]) if row[key] else None

        return SupervisorRun(
            run_id=row["run_id"], tenant_id=row["tenant_id"],
            workspace_id=row["workspace_id"], channel_id=row["channel_id"],
            thread_id=row["thread_id"], task_id=row["task_id"],
            objective=row["objective"], owner_agent=row["owner_agent"],
            builder_agent=row["builder_agent"], reviewer_agent=row["reviewer_agent"],
            acceptance_criteria=json.loads(row["acceptance_criteria_json"]),
            status=RunStatus(row["status"]),
            builder_result=decode("builder_result_json"),
            review_result=decode("review_result_json"),
            reconciliation=decode("reconciliation_json"),
            approval_id=row["approval_id"], created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

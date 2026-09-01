"""
durable_execution.py
====================
Temporal-inspired Durable Execution for SintraPrime-Unified.

Features:
- SQLite-backed workflow checkpoints (survives process restarts)
- Resume interrupted workflows (legal cases can span weeks)
- Activity retries with exponential backoff and jitter
- Full workflow history / audit log
- Saga compensation pattern for rollbacks
- Durable dispatch claim + recovery worker for exactly-once dispatch
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class WorkflowStatus(str, Enum):
    CLAIMED = "claimed"          # durable dispatch claim persisted; not yet dispatched
    DISPATCHING = "dispatching"  # a scheduler owns the dispatch handoff
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING = "waiting"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"


class ActivityStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    COMPENSATED = "compensated"


class SideEffectStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class HistoryEventType(str, Enum):
    WORKFLOW_CLAIMED = "WORKFLOW_CLAIMED"
    WORKFLOW_DISPATCHING = "WORKFLOW_DISPATCHING"
    WORKFLOW_RECOVERED = "WORKFLOW_RECOVERED"
    WORKFLOW_STARTED = "WORKFLOW_STARTED"
    WORKFLOW_COMPLETED = "WORKFLOW_COMPLETED"
    WORKFLOW_FAILED = "WORKFLOW_FAILED"
    WORKFLOW_CANCELLED = "WORKFLOW_CANCELLED"
    ACTIVITY_SCHEDULED = "ACTIVITY_SCHEDULED"
    ACTIVITY_STARTED = "ACTIVITY_STARTED"
    ACTIVITY_COMPLETED = "ACTIVITY_COMPLETED"
    ACTIVITY_FAILED = "ACTIVITY_FAILED"
    ACTIVITY_RETRIED = "ACTIVITY_RETRIED"
    COMPENSATION_STARTED = "COMPENSATION_STARTED"
    COMPENSATION_COMPLETED = "COMPENSATION_COMPLETED"
    CHECKPOINT_SAVED = "CHECKPOINT_SAVED"
    WORKFLOW_RESUMED = "WORKFLOW_RESUMED"
    SIGNAL_RECEIVED = "SIGNAL_RECEIVED"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class HistoryEvent:
    workflow_id: str
    event_type: HistoryEventType
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: float = field(default_factory=time.time)
    activity_name: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    attempt: int = 0
    error: Optional[str] = None


@dataclass
class ActivityRecord:
    activity_id: str
    workflow_id: str
    name: str
    status: ActivityStatus
    attempt: int = 0
    max_attempts: int = 3
    result: Optional[Any] = None
    error: Optional[str] = None
    scheduled_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    compensation_func_name: Optional[str] = None


@dataclass
class WorkflowRecord:
    workflow_id: str
    workflow_type: str
    status: WorkflowStatus
    state: Dict[str, Any]
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    error: Optional[str] = None
    parent_workflow_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    dispatch_request_hash: Optional[str] = None
    dispatch_attempt_count: int = 0
    dispatch_owner_id: Optional[str] = None
    dispatch_lease_expires_at: Optional[float] = None


@dataclass
class SideEffectRecord:
    """Durable identity and receipt for one logical external mutation."""

    side_effect_id: str
    tenant_id: str
    workflow_id: str
    activity_id: str
    idempotency_key: str
    target_type: str
    target_identifier: str
    normalized_request_hash: str
    provider_name: str
    status: SideEffectStatus = SideEffectStatus.PENDING
    provider_request_id: Optional[str] = None
    result_reference: Optional[Any] = None
    receipt_hash: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    lease_owner_id: Optional[str] = None
    lease_expires_at: Optional[float] = None
    last_error: Optional[str] = None


@dataclass
class ProviderExecutionResult:
    """Normalized result returned by a consequential side-effect provider."""

    provider_request_id: str
    result_reference: Any


class SideEffectConflictError(ValueError):
    """An idempotency identity was reused for a conflicting mutation."""


class SideEffectProvider:
    """Interface required of consequential external-mutation adapters."""

    name = "provider"
    supports_native_idempotency = False

    async def execute(
        self,
        request: Dict[str, Any],
        *,
        idempotency_key: str,
    ) -> ProviderExecutionResult:
        raise NotImplementedError

    async def verify_or_reconcile(
        self,
        *,
        idempotency_key: str,
        provider_request_id: Optional[str],
    ) -> Optional[ProviderExecutionResult]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# SQLite Persistence Layer
# ---------------------------------------------------------------------------

class DurableStore:
    """SQLite-backed persistence for workflow state, activities, and history."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._persistent_conn: Optional[sqlite3.Connection] = None
        # Keep one long-lived connection per store instance. For file-backed
        # stores this ensures the database can be closed deterministically.
        self._persistent_conn = sqlite3.connect(db_path, check_same_thread=False)
        self._persistent_conn.row_factory = sqlite3.Row
        self._persistent_conn.execute("PRAGMA foreign_keys=ON")
        if db_path != ":memory:":
            self._persistent_conn.execute("PRAGMA journal_mode=WAL")
        self._init_db()

    def close(self) -> None:
        """Close this store's long-lived SQLite connection."""
        if self._persistent_conn is not None:
            self._persistent_conn.close()
            self._persistent_conn = None

    def _connect(self) -> sqlite3.Connection:
        if self._persistent_conn is None:
            raise RuntimeError("DURABLE_STORE_CLOSED")
        self._persistent_conn.row_factory = sqlite3.Row
        return self._persistent_conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS workflows (
                    workflow_id TEXT PRIMARY KEY,
                    workflow_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT '{}',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    completed_at REAL,
                    error TEXT,
                    parent_workflow_id TEXT,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    dispatch_request_hash TEXT,
                    dispatch_attempt_count INTEGER NOT NULL DEFAULT 0,
                    dispatch_owner_id TEXT,
                    dispatch_lease_expires_at REAL
                );

                CREATE TABLE IF NOT EXISTS activities (
                    activity_id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempt INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    result TEXT,
                    error TEXT,
                    scheduled_at REAL NOT NULL,
                    started_at REAL,
                    completed_at REAL,
                    compensation_func_name TEXT,
                    FOREIGN KEY (workflow_id) REFERENCES workflows(workflow_id)
                );

                CREATE TABLE IF NOT EXISTS history (
                    event_id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    activity_name TEXT,
                    payload TEXT NOT NULL DEFAULT '{}',
                    attempt INTEGER NOT NULL DEFAULT 0,
                    error TEXT,
                    FOREIGN KEY (workflow_id) REFERENCES workflows(workflow_id)
                );

                CREATE TABLE IF NOT EXISTS side_effects (
                    side_effect_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    workflow_id TEXT NOT NULL,
                    activity_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    target_type TEXT NOT NULL,
                    target_identifier TEXT NOT NULL,
                    normalized_request_hash TEXT NOT NULL,
                    provider_name TEXT NOT NULL,
                    provider_request_id TEXT,
                    status TEXT NOT NULL,
                    result_reference TEXT,
                    receipt_hash TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    completed_at REAL,
                    lease_owner_id TEXT,
                    lease_expires_at REAL,
                    last_error TEXT,
                    FOREIGN KEY (workflow_id) REFERENCES workflows(workflow_id)
                );

                CREATE INDEX IF NOT EXISTS idx_activities_workflow ON activities(workflow_id);
                CREATE INDEX IF NOT EXISTS idx_history_workflow ON history(workflow_id);
                CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows(status);
            """)
            self._ensure_dispatch_claim_columns(conn)

    def _ensure_dispatch_claim_columns(self, conn: sqlite3.Connection) -> None:
        """Idempotent migration for durable dispatch claim columns."""
        for column, ddl in (
            ("dispatch_request_hash", "TEXT"),
            ("dispatch_attempt_count", "INTEGER NOT NULL DEFAULT 0"),
            ("dispatch_owner_id", "TEXT"),
            ("dispatch_lease_expires_at", "REAL"),
        ):
            try:
                conn.execute(f"ALTER TABLE workflows ADD COLUMN {column} {ddl}")
            except sqlite3.OperationalError:
                pass

    def _row_to_side_effect(self, row: sqlite3.Row) -> SideEffectRecord:
        raw_result = row["result_reference"]
        return SideEffectRecord(
            side_effect_id=row["side_effect_id"],
            tenant_id=row["tenant_id"],
            workflow_id=row["workflow_id"],
            activity_id=row["activity_id"],
            idempotency_key=row["idempotency_key"],
            target_type=row["target_type"],
            target_identifier=row["target_identifier"],
            normalized_request_hash=row["normalized_request_hash"],
            provider_name=row["provider_name"],
            provider_request_id=row["provider_request_id"],
            status=SideEffectStatus(row["status"]),
            result_reference=json.loads(raw_result) if raw_result is not None else None,
            receipt_hash=row["receipt_hash"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            completed_at=row["completed_at"],
            lease_owner_id=row["lease_owner_id"],
            lease_expires_at=row["lease_expires_at"],
            last_error=row["last_error"],
        )

    def get_side_effect(self, idempotency_key: str) -> Optional[SideEffectRecord]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM side_effects WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
        return self._row_to_side_effect(row) if row else None

    def claim_side_effect(self, record: SideEffectRecord) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("""
                INSERT OR IGNORE INTO side_effects
                (side_effect_id, tenant_id, workflow_id, activity_id,
                 idempotency_key, target_type, target_identifier,
                 normalized_request_hash, provider_name, provider_request_id,
                 status, result_reference, receipt_hash, created_at, updated_at,
                 completed_at, lease_owner_id, lease_expires_at, last_error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.side_effect_id, record.tenant_id, record.workflow_id,
                record.activity_id, record.idempotency_key, record.target_type,
                record.target_identifier, record.normalized_request_hash,
                record.provider_name, record.provider_request_id,
                record.status.value,
                json.dumps(record.result_reference, sort_keys=True)
                if record.result_reference is not None else None,
                record.receipt_hash, record.created_at, record.updated_at,
                record.completed_at, record.lease_owner_id,
                record.lease_expires_at, record.last_error,
            ))
            return cursor.rowcount == 1

    def claim_side_effect_execution(
        self,
        idempotency_key: str,
        owner_id: str,
        lease_expires_at: float,
        now: float,
    ) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("""
                UPDATE side_effects
                SET status = ?, lease_owner_id = ?, lease_expires_at = ?,
                    updated_at = ?
                WHERE idempotency_key = ?
                  AND (
                    status IN (?, ?)
                    OR (status = ? AND lease_expires_at < ?)
                  )
            """, (
                SideEffectStatus.IN_PROGRESS.value, owner_id, lease_expires_at,
                now, idempotency_key, SideEffectStatus.PENDING.value,
                SideEffectStatus.UNKNOWN.value,
                SideEffectStatus.IN_PROGRESS.value, now,
            ))
            return cursor.rowcount == 1

    def mark_side_effect_unknown(
        self,
        idempotency_key: str,
        owner_id: str,
        *,
        provider_request_id: Optional[str],
        error: str,
    ) -> None:
        now = time.time()
        with self._connect() as conn:
            conn.execute("""
                UPDATE side_effects
                SET status = ?, provider_request_id = COALESCE(?, provider_request_id),
                    last_error = ?, updated_at = ?, lease_owner_id = NULL,
                    lease_expires_at = NULL
                WHERE idempotency_key = ? AND lease_owner_id = ?
            """, (
                SideEffectStatus.UNKNOWN.value, provider_request_id, error, now,
                idempotency_key, owner_id,
            ))

    def complete_side_effect(
        self,
        idempotency_key: str,
        owner_id: str,
        execution: ProviderExecutionResult,
        receipt_hash: str,
    ) -> None:
        now = time.time()
        encoded_result = json.dumps(execution.result_reference, sort_keys=True)
        with self._connect() as conn:
            cursor = conn.execute("""
                UPDATE side_effects
                SET status = ?, provider_request_id = ?, result_reference = ?,
                    receipt_hash = ?, completed_at = ?, updated_at = ?,
                    lease_owner_id = NULL, lease_expires_at = NULL,
                    last_error = NULL
                WHERE idempotency_key = ? AND lease_owner_id = ?
            """, (
                SideEffectStatus.SUCCEEDED.value,
                execution.provider_request_id, encoded_result, receipt_hash,
                now, now, idempotency_key, owner_id,
            ))
            if cursor.rowcount != 1:
                raise RuntimeError("SIDE_EFFECT_RECEIPT_WRITE_CONFLICT")

    def claim_workflow(self, wf: WorkflowRecord) -> bool:
        """Insert a workflow record exactly once. Return True if newly claimed."""
        with self._connect() as conn:
            cursor = conn.execute("""
                INSERT OR IGNORE INTO workflows
                (workflow_id, workflow_type, status, state, created_at, updated_at,
                 completed_at, error, parent_workflow_id, metadata, dispatch_request_hash,
                 dispatch_attempt_count, dispatch_owner_id, dispatch_lease_expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                wf.workflow_id, wf.workflow_type, wf.status.value,
                json.dumps(wf.state), wf.created_at, wf.updated_at,
                wf.completed_at, wf.error, wf.parent_workflow_id,
                json.dumps(wf.metadata),
                wf.dispatch_request_hash,
                wf.dispatch_attempt_count,
                wf.dispatch_owner_id,
                wf.dispatch_lease_expires_at,
            ))
            return cursor.rowcount == 1

    def try_claim_dispatch(
        self,
        workflow_id: str,
        owner_id: str,
        lease_expires_at: float,
        now: float,
    ) -> bool:
        """
        Atomically claim a workflow for dispatch.
        Accepts CLAIMED rows or DISPATCHING rows with expired leases.
        Returns True if this owner won the claim.
        """
        with self._connect() as conn:
            cursor = conn.execute("""
                UPDATE workflows
                SET status = ?,
                    dispatch_owner_id = ?,
                    dispatch_lease_expires_at = ?,
                    dispatch_attempt_count = dispatch_attempt_count + 1,
                    updated_at = ?
                WHERE workflow_id = ?
                  AND (status = ? OR (status = ? AND dispatch_lease_expires_at < ?))
            """, (
                WorkflowStatus.DISPATCHING.value,
                owner_id,
                lease_expires_at,
                now,
                workflow_id,
                WorkflowStatus.CLAIMED.value,
                WorkflowStatus.DISPATCHING.value,
                now,
            ))
            return cursor.rowcount == 1

    def release_dispatch_claim(
        self,
        workflow_id: str,
        owner_id: str,
        status: WorkflowStatus,
        now: float,
    ) -> bool:
        """
        Release a dispatch ownership claim and set the truthful execution status.
        Only succeeds if the current owner matches and the workflow is DISPATCHING.
        """
        with self._connect() as conn:
            cursor = conn.execute("""
                UPDATE workflows
                SET status = ?,
                    dispatch_owner_id = NULL,
                    dispatch_lease_expires_at = NULL,
                    updated_at = ?
                WHERE workflow_id = ?
                  AND status = ?
                  AND dispatch_owner_id = ?
            """, (
                status.value,
                now,
                workflow_id,
                WorkflowStatus.DISPATCHING.value,
                owner_id,
            ))
            return cursor.rowcount == 1

    def find_claimed_workflows(
        self,
        now: float,
        limit: int = 100,
    ) -> List[WorkflowRecord]:
        """Find workflows that need dispatch: CLAIMED or DISPATCHING with expired lease."""
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT * FROM workflows
                WHERE status = ?
                   OR (status = ? AND dispatch_lease_expires_at < ?)
                ORDER BY created_at ASC
                LIMIT ?
            """, (
                WorkflowStatus.CLAIMED.value,
                WorkflowStatus.DISPATCHING.value,
                now,
                limit,
            )).fetchall()
        return [self._row_to_workflow(row) for row in rows]

    # --- Workflow CRUD ---

    def save_workflow(self, wf: WorkflowRecord) -> None:
        """General-purpose save/update. Tests and internal state transitions may use this."""
        wf.updated_at = time.time()
        with self._connect() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO workflows
                (workflow_id, workflow_type, status, state, created_at, updated_at,
                 completed_at, error, parent_workflow_id, metadata, dispatch_request_hash,
                 dispatch_attempt_count, dispatch_owner_id, dispatch_lease_expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                wf.workflow_id, wf.workflow_type, wf.status.value,
                json.dumps(wf.state), wf.created_at, wf.updated_at,
                wf.completed_at, wf.error, wf.parent_workflow_id,
                json.dumps(wf.metadata),
                wf.dispatch_request_hash,
                wf.dispatch_attempt_count,
                wf.dispatch_owner_id,
                wf.dispatch_lease_expires_at,
            ))

    def load_workflow(self, workflow_id: str) -> Optional[WorkflowRecord]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM workflows WHERE workflow_id = ?", (workflow_id,)
            ).fetchone()
        if not row:
            return None
        return self._row_to_workflow(row)

    def _row_to_workflow(self, row: sqlite3.Row) -> WorkflowRecord:
        return WorkflowRecord(
            workflow_id=row["workflow_id"],
            workflow_type=row["workflow_type"],
            status=WorkflowStatus(row["status"]),
            state=json.loads(row["state"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            completed_at=row["completed_at"],
            error=row["error"],
            parent_workflow_id=row["parent_workflow_id"],
            metadata=json.loads(row["metadata"]),
            dispatch_request_hash=row["dispatch_request_hash"],
            dispatch_attempt_count=row["dispatch_attempt_count"] or 0,
            dispatch_owner_id=row["dispatch_owner_id"],
            dispatch_lease_expires_at=row["dispatch_lease_expires_at"],
        )

    def list_workflows(
        self,
        status: Optional[WorkflowStatus] = None,
        limit: int = 100,
    ) -> List[WorkflowRecord]:
        with self._connect() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM workflows WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status.value, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM workflows ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
        return [self._row_to_workflow(row) for row in rows]

    # --- Activity CRUD ---

    def save_activity(self, act: ActivityRecord) -> None:
        with self._connect() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO activities
                (activity_id, workflow_id, name, status, attempt, max_attempts,
                 result, error, scheduled_at, started_at, completed_at, compensation_func_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                act.activity_id, act.workflow_id, act.name, act.status.value,
                act.attempt, act.max_attempts,
                json.dumps(act.result) if act.result is not None else None,
                act.error, act.scheduled_at, act.started_at, act.completed_at,
                act.compensation_func_name,
            ))

    def load_activities(self, workflow_id: str) -> List[ActivityRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM activities WHERE workflow_id = ? ORDER BY scheduled_at",
                (workflow_id,),
            ).fetchall()
        result = []
        for row in rows:
            result.append(ActivityRecord(
                activity_id=row["activity_id"],
                workflow_id=row["workflow_id"],
                name=row["name"],
                status=ActivityStatus(row["status"]),
                attempt=row["attempt"],
                max_attempts=row["max_attempts"],
                result=json.loads(row["result"]) if row["result"] else None,
                error=row["error"],
                scheduled_at=row["scheduled_at"],
                started_at=row["started_at"],
                completed_at=row["completed_at"],
                compensation_func_name=row["compensation_func_name"],
            ))
        return result

    # --- History ---

    def append_history(self, event: HistoryEvent) -> None:
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO history
                (event_id, workflow_id, event_type, timestamp, activity_name, payload, attempt, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id, event.workflow_id, event.event_type.value,
                event.timestamp, event.activity_name,
                json.dumps(event.payload), event.attempt, event.error,
            ))

    def load_history(self, workflow_id: str) -> List[HistoryEvent]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM history WHERE workflow_id = ? ORDER BY timestamp",
                (workflow_id,),
            ).fetchall()
        result = []
        for row in rows:
            result.append(HistoryEvent(
                workflow_id=row["workflow_id"],
                event_type=HistoryEventType(row["event_type"]),
                event_id=row["event_id"],
                timestamp=row["timestamp"],
                activity_name=row["activity_name"],
                payload=json.loads(row["payload"]),
                attempt=row["attempt"],
                error=row["error"],
            ))
        return result


# ---------------------------------------------------------------------------
# Retry Policy
# ---------------------------------------------------------------------------

@dataclass
class RetryPolicy:
    max_attempts: int = 3
    initial_interval: float = 1.0
    backoff_coefficient: float = 2.0
    max_interval: float = 60.0
    jitter: bool = True

    def next_delay(self, attempt: int) -> float:
        delay = min(
            self.initial_interval * (self.backoff_coefficient ** attempt),
            self.max_interval,
        )
        if self.jitter:
            delay *= (0.75 + random.random() * 0.5)
        return delay


# ---------------------------------------------------------------------------
# Activity Executor
# ---------------------------------------------------------------------------

class ActivityExecutor:
    """Executes activities with retries and records results."""

    def __init__(self, store: DurableStore) -> None:
        self._store = store

    async def run(
        self,
        workflow_id: str,
        name: str,
        func: Callable,
        args: Tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        retry_policy: Optional[RetryPolicy] = None,
        compensation_func: Optional[Callable] = None,
    ) -> Any:
        kwargs = kwargs or {}
        policy = retry_policy or RetryPolicy()
        activity_id = uuid.uuid4().hex
        comp_name = compensation_func.__name__ if compensation_func else None

        act = ActivityRecord(
            activity_id=activity_id,
            workflow_id=workflow_id,
            name=name,
            status=ActivityStatus.PENDING,
            max_attempts=policy.max_attempts,
            compensation_func_name=comp_name,
        )
        self._store.save_activity(act)
        self._store.append_history(HistoryEvent(
            workflow_id=workflow_id,
            event_type=HistoryEventType.ACTIVITY_SCHEDULED,
            activity_name=name,
        ))

        last_exc: Optional[Exception] = None
        for attempt in range(policy.max_attempts):
            act.attempt = attempt
            act.status = ActivityStatus.RUNNING
            act.started_at = time.time()
            self._store.save_activity(act)
            self._store.append_history(HistoryEvent(
                workflow_id=workflow_id,
                event_type=HistoryEventType.ACTIVITY_STARTED,
                activity_name=name,
                attempt=attempt,
            ))

            try:
                is_async = asyncio.iscoroutinefunction(func)
                if is_async:
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                act.result = result
                act.status = ActivityStatus.COMPLETED
                act.completed_at = time.time()
                self._store.save_activity(act)
                self._store.append_history(HistoryEvent(
                    workflow_id=workflow_id,
                    event_type=HistoryEventType.ACTIVITY_COMPLETED,
                    activity_name=name,
                    attempt=attempt,
                    payload={"result": str(result)[:500] if result else None},
                ))
                return result

            except Exception as exc:
                last_exc = exc
                act.error = str(exc)
                self._store.append_history(HistoryEvent(
                    workflow_id=workflow_id,
                    event_type=HistoryEventType.ACTIVITY_FAILED,
                    activity_name=name,
                    attempt=attempt,
                    error=str(exc),
                ))
                if attempt < policy.max_attempts - 1:
                    delay = policy.next_delay(attempt)
                    act.status = ActivityStatus.RETRYING
                    self._store.save_activity(act)
                    self._store.append_history(HistoryEvent(
                        workflow_id=workflow_id,
                        event_type=HistoryEventType.ACTIVITY_RETRIED,
                        activity_name=name,
                        attempt=attempt,
                        payload={"delay": delay},
                    ))
                    logger.warning("Activity %s attempt %d failed, retrying in %.1fs: %s", name, attempt + 1, delay, exc)
                    await asyncio.sleep(delay)

        act.status = ActivityStatus.FAILED
        self._store.save_activity(act)
        raise RuntimeError(f"Activity '{name}' failed after {policy.max_attempts} attempts") from last_exc


# ---------------------------------------------------------------------------
# Saga Compensator
# ---------------------------------------------------------------------------

class SagaCompensator:
    """
    Saga pattern: tracks completed activities and their compensations.
    On failure, executes compensations in reverse order (rollback).
    """

    def __init__(self) -> None:
        self._steps: List[Tuple[str, Callable, Tuple, Dict[str, Any]]] = []

    def register_compensation(
        self,
        name: str,
        func: Callable,
        args: Tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._steps.append((name, func, args, kwargs or {}))

    async def compensate(self) -> List[str]:
        """Execute compensations in reverse order. Returns names executed."""
        executed: List[str] = []
        for name, func, args, kwargs in reversed(self._steps):
            try:
                if asyncio.iscoroutinefunction(func):
                    await func(*args, **kwargs)
                else:
                    func(*args, **kwargs)
                executed.append(name)
                logger.info("Compensation executed: %s", name)
            except Exception as exc:
                logger.error("Compensation %s failed: %s", name, exc)
        return executed

    def step_count(self) -> int:
        return len(self._steps)


# ---------------------------------------------------------------------------
# Workflow Context
# ---------------------------------------------------------------------------

class WorkflowContext:
    """Runtime context passed to workflow functions."""

    def __init__(
        self,
        workflow_id: str,
        workflow_type: str,
        store: DurableStore,
        executor: ActivityExecutor,
    ) -> None:
        self.workflow_id = workflow_id
        self.workflow_type = workflow_type
        self._store = store
        self._executor = executor
        self._compensator = SagaCompensator()

    async def execute_activity(
        self,
        name: str,
        func: Callable,
        args: Tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        retry_policy: Optional[RetryPolicy] = None,
        compensation_func: Optional[Callable] = None,
    ) -> Any:
        """Execute an activity within this workflow."""
        result = await self._executor.run(
            workflow_id=self.workflow_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            retry_policy=retry_policy,
            compensation_func=compensation_func,
        )
        if compensation_func:
            self._compensator.register_compensation(name, compensation_func)
        return result

    async def compensate(self) -> List[str]:
        """Trigger saga compensation (rollback)."""
        self._store.append_history(HistoryEvent(
            workflow_id=self.workflow_id,
            event_type=HistoryEventType.COMPENSATION_STARTED,
        ))
        executed = await self._compensator.compensate()
        self._store.append_history(HistoryEvent(
            workflow_id=self.workflow_id,
            event_type=HistoryEventType.COMPENSATION_COMPLETED,
            payload={"compensated_steps": executed},
        ))
        return executed

    def record_signal(self, signal_name: str, payload: Dict[str, Any]) -> None:
        self._store.append_history(HistoryEvent(
            workflow_id=self.workflow_id,
            event_type=HistoryEventType.SIGNAL_RECEIVED,
            payload={"signal": signal_name, **payload},
        ))

    def get_history(self) -> List[HistoryEvent]:
        return self._store.load_history(self.workflow_id)

    def get_activities(self) -> List[ActivityRecord]:
        return self._store.load_activities(self.workflow_id)


# ---------------------------------------------------------------------------
# Durable Workflow Engine
# ---------------------------------------------------------------------------

WorkflowFunc = Callable[["WorkflowContext", Dict[str, Any]], Any]


class DurableWorkflowEngine:
    """
    Temporal-inspired durable workflow engine.

    - Start, resume, and cancel workflows
    - SQLite-backed persistence for crash recovery
    - Workflow history and audit trail
    - Saga compensation
    - Durable dispatch claim + recovery worker for exactly-once dispatch
    """

    def __init__(
        self,
        db_path: str = ":memory:",
        dispatch_lease_seconds: float = 30.0,
    ) -> None:
        self._store = DurableStore(db_path=db_path)
        self._executor = ActivityExecutor(self._store)
        self._registered: Dict[str, WorkflowFunc] = {}
        self._instance_id = uuid.uuid4().hex
        self._dispatch_lease_seconds = dispatch_lease_seconds
        self._shutdown_event: asyncio.Event = asyncio.Event()
        self._recovery_task: Optional[asyncio.Task] = None
        self._running_tasks: set[asyncio.Task] = set()

    def register_workflow(self, workflow_type: str, func: WorkflowFunc) -> None:
        self._registered[workflow_type] = func
        logger.info("Registered workflow type: %s", workflow_type)

    async def start_workflow(
        self,
        workflow_type: str,
        input_data: Dict[str, Any],
        workflow_id: Optional[str] = None,
        parent_workflow_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Start a new workflow idempotently. Returns workflow_id."""
        if workflow_type not in self._registered:
            raise ValueError(f"Unknown workflow type: '{workflow_type}'")

        wf_id = workflow_id or uuid.uuid4().hex
        metadata = metadata or {}
        dispatch_request_hash = self._compute_dispatch_hash(
            workflow_type=workflow_type,
            input_data=input_data,
            metadata=metadata,
        )

        # Fast path: existing durable claim with same identity.
        existing = self._store.load_workflow(wf_id)
        if existing is not None:
            if existing.dispatch_request_hash != dispatch_request_hash:
                raise ValueError(
                    f"Workflow {wf_id} already exists with conflicting request"
                )
            if existing.status == WorkflowStatus.CLAIMED:
                # A previous dispatch handoff never completed. Try to finish it now.
                await self._dispatch_workflow(existing, from_recovery=False)
            # Idempotent replay: return existing identity without scheduling a duplicate.
            return wf_id

        now = time.time()
        wf = WorkflowRecord(
            workflow_id=wf_id,
            workflow_type=workflow_type,
            status=WorkflowStatus.CLAIMED,
            state=input_data,
            created_at=now,
            updated_at=now,
            parent_workflow_id=parent_workflow_id,
            metadata=metadata,
            dispatch_request_hash=dispatch_request_hash,
        )
        claimed = self._store.claim_workflow(wf)
        if not claimed:
            # Lost race: another caller claimed the workflow concurrently.
            # Verify the existing claim matches this request and, if it is still
            # CLAIMED, attempt to dispatch it ourselves before returning.
            existing = self._store.load_workflow(wf_id)
            if existing is None or existing.dispatch_request_hash != dispatch_request_hash:
                raise ValueError(
                    f"Workflow {wf_id} already exists with conflicting request"
                )
            if existing.status == WorkflowStatus.CLAIMED:
                await self._dispatch_workflow(existing, from_recovery=False)
            return wf_id

        self._store.append_history(HistoryEvent(
            workflow_id=wf_id,
            event_type=HistoryEventType.WORKFLOW_CLAIMED,
            payload={"workflow_type": workflow_type, "input": input_data},
        ))

        await self._dispatch_workflow(wf, from_recovery=False)
        return wf_id

    def _compute_dispatch_hash(
        self,
        workflow_type: str,
        input_data: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> str:
        """Stable hash of the immutable dispatch request. No timestamps."""
        fingerprint = {
            "workflow_type": workflow_type,
            "input_data": input_data,
            "metadata": metadata,
        }
        canonical = json.dumps(fingerprint, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    async def _dispatch_workflow(
        self,
        wf: WorkflowRecord,
        from_recovery: bool,
    ) -> bool:
        """
        Acquire dispatch ownership and launch the workflow task.
        Returns True if this engine scheduled the task.
        """
        workflow_id = wf.workflow_id
        workflow_type = wf.workflow_type
        input_data = wf.state

        now = time.time()
        owner_id = self._instance_id
        lease_expires_at = now + self._dispatch_lease_seconds

        claimed = self._store.try_claim_dispatch(
            workflow_id=workflow_id,
            owner_id=owner_id,
            lease_expires_at=lease_expires_at,
            now=now,
        )
        if not claimed:
            return False

        event_type = (
            HistoryEventType.WORKFLOW_RECOVERED
            if from_recovery
            else HistoryEventType.WORKFLOW_DISPATCHING
        )
        self._store.append_history(HistoryEvent(
            workflow_id=workflow_id,
            event_type=event_type,
            payload={"workflow_type": workflow_type, "owner": owner_id},
        ))

        task = asyncio.create_task(
            self._run_workflow(workflow_id, workflow_type, input_data, owner_id)
        )
        self._running_tasks.add(task)
        task.add_done_callback(self._running_tasks.discard)
        return True

    async def _run_workflow(
        self,
        workflow_id: str,
        workflow_type: str,
        input_data: Dict[str, Any],
        owner_id: str,
    ) -> None:
        """Execute a workflow body after confirming the durable dispatch handoff."""
        now = time.time()

        # Confirm the task has actually begun. This durable compare-and-swap is
        # the boundary between "dispatch scheduled" and "execution started".
        released = self._store.release_dispatch_claim(
            workflow_id=workflow_id,
            owner_id=owner_id,
            status=WorkflowStatus.RUNNING,
            now=now,
        )
        if not released:
            # Workflow was cancelled, another worker owns it, or it was already
            # recovered. Do not execute the body.
            logger.info("Workflow %s dispatch claim was released by another owner; aborting", workflow_id)
            return

        self._store.append_history(HistoryEvent(
            workflow_id=workflow_id,
            event_type=HistoryEventType.WORKFLOW_STARTED,
            payload={"workflow_type": workflow_type, "input": input_data},
        ))

        func = self._registered[workflow_type]
        ctx = WorkflowContext(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            store=self._store,
            executor=self._executor,
        )
        wf = self._store.load_workflow(workflow_id)
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(ctx, input_data)
            else:
                result = func(ctx, input_data)

            wf.status = WorkflowStatus.COMPLETED
            wf.state["_result"] = result
            wf.completed_at = time.time()
            self._store.save_workflow(wf)
            self._store.append_history(HistoryEvent(
                workflow_id=workflow_id,
                event_type=HistoryEventType.WORKFLOW_COMPLETED,
                payload={"result": str(result)[:500] if result else None},
            ))
        except Exception as exc:
            logger.exception("Workflow %s failed: %s", workflow_id, exc)
            wf.status = WorkflowStatus.FAILED
            wf.error = str(exc)
            self._store.save_workflow(wf)
            self._store.append_history(HistoryEvent(
                workflow_id=workflow_id,
                event_type=HistoryEventType.WORKFLOW_FAILED,
                error=str(exc),
            ))
            # Trigger compensation
            try:
                await ctx.compensate()
                wf.status = WorkflowStatus.COMPENSATED
                self._store.save_workflow(wf)
            except Exception as comp_exc:
                logger.error("Compensation for %s also failed: %s", workflow_id, comp_exc)

    async def recover_dispatches(self, batch_size: int = 10) -> int:
        """
        Discover and dispatch workflows that were claimed but never handed off.
        Returns the number of workflows dispatched by this call.
        """
        now = time.time()
        eligible = self._store.find_claimed_workflows(now=now, limit=batch_size)
        dispatched = 0
        for wf in eligible:
            if self._shutdown_event.is_set():
                break
            if await self._dispatch_workflow(wf, from_recovery=True):
                dispatched += 1
        return dispatched

    def start_recovery_worker(
        self,
        interval_seconds: float = 5.0,
        batch_size: int = 10,
    ) -> None:
        """Start a background task that periodically recovers stranded dispatches."""
        async def _worker() -> None:
            while not self._shutdown_event.is_set():
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=interval_seconds,
                    )
                except asyncio.TimeoutError:
                    pass
                if self._shutdown_event.is_set():
                    break
                try:
                    await self.recover_dispatches(batch_size=batch_size)
                except Exception:
                    logger.exception("Recovery worker iteration failed")

        self._recovery_task = asyncio.create_task(_worker())

    async def shutdown(self, timeout_seconds: float = 10.0) -> None:
        """Stop the recovery worker and wait for running workflow tasks."""
        self._shutdown_event.set()
        if self._recovery_task is not None:
            self._recovery_task.cancel()
            try:
                await self._recovery_task
            except asyncio.CancelledError:
                pass
        if self._running_tasks:
            done, pending = await asyncio.wait(
                self._running_tasks,
                timeout=timeout_seconds,
                return_when=asyncio.ALL_COMPLETED,
            )
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    async def resume_workflow(self, workflow_id: str, signal: Dict[str, Any]) -> bool:
        """Signal / resume a waiting workflow."""
        wf = self._store.load_workflow(workflow_id)
        if not wf:
            return False
        if wf.status not in (WorkflowStatus.WAITING, WorkflowStatus.RUNNING):
            return False
        wf.state.update(signal)
        wf.status = WorkflowStatus.RUNNING
        self._store.save_workflow(wf)
        self._store.append_history(HistoryEvent(
            workflow_id=workflow_id,
            event_type=HistoryEventType.WORKFLOW_RESUMED,
            payload=signal,
        ))
        return True

    @staticmethod
    def _normalize_side_effect_value(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    @classmethod
    def derive_side_effect_identity(
        cls,
        *,
        workflow_id: str,
        activity_id: str,
        target_type: str,
        target_identifier: str,
        request: Dict[str, Any],
    ) -> Tuple[str, str]:
        normalized_target = cls._normalize_side_effect_value({
            "target_type": target_type,
            "target_identifier": target_identifier,
        })
        normalized_request = cls._normalize_side_effect_value(request)
        request_hash = hashlib.sha256(normalized_request.encode("utf-8")).hexdigest()
        identity = cls._normalize_side_effect_value({
            "workflow_id": workflow_id,
            "activity_id": activity_id,
            "target": normalized_target,
            "request_hash": request_hash,
        })
        return hashlib.sha256(identity.encode("utf-8")).hexdigest(), request_hash

    async def execute_idempotent_side_effect(
        self,
        *,
        tenant_id: str,
        workflow_id: str,
        activity_id: str,
        target_type: str,
        target_identifier: str,
        request: Dict[str, Any],
        provider: SideEffectProvider,
        idempotency_key: Optional[str] = None,
        lease_seconds: float = 30.0,
    ) -> Any:
        """Execute or reconcile one consequential external mutation.

        Timeouts and acknowledgement loss become UNKNOWN and are reconciled;
        they are never treated as permission for an automatic blind retry.
        """
        derived_key, request_hash = self.derive_side_effect_identity(
            workflow_id=workflow_id,
            activity_id=activity_id,
            target_type=target_type,
            target_identifier=target_identifier,
            request=request,
        )
        key = idempotency_key or derived_key
        record = SideEffectRecord(
            side_effect_id=hashlib.sha256(f"side-effect:{key}".encode("utf-8")).hexdigest(),
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            activity_id=activity_id,
            idempotency_key=key,
            target_type=target_type,
            target_identifier=target_identifier,
            normalized_request_hash=request_hash,
            provider_name=provider.name,
            status=SideEffectStatus.PENDING,
        )
        self._store.claim_side_effect(record)

        while True:
            current = self._store.get_side_effect(key)
            if current is None:
                raise RuntimeError("SIDE_EFFECT_CLAIM_MISSING")
            if (
                current.normalized_request_hash != request_hash
                or current.workflow_id != workflow_id
                or current.activity_id != activity_id
                or current.target_type != target_type
                or current.target_identifier != target_identifier
                or current.provider_name != provider.name
            ):
                raise SideEffectConflictError("SIDE_EFFECT_IDEMPOTENCY_CONFLICT")
            if current.status == SideEffectStatus.SUCCEEDED:
                return current.result_reference

            owner_id = f"side-effect-{uuid.uuid4()}"
            now = time.time()
            if not self._store.claim_side_effect_execution(
                key, owner_id, now + lease_seconds, now,
            ):
                await asyncio.sleep(0.01)
                continue

            current = self._store.get_side_effect(key)
            try:
                if current is not None and current.status == SideEffectStatus.IN_PROGRESS:
                    reconciled = await provider.verify_or_reconcile(
                        idempotency_key=key,
                        provider_request_id=current.provider_request_id,
                    )
                    if reconciled is not None:
                        execution = reconciled
                    else:
                        execution = await provider.execute(
                            request,
                            idempotency_key=key,
                        )
                else:
                    raise RuntimeError("SIDE_EFFECT_CLAIM_STATE_INVALID")
            except TimeoutError as exc:
                provider_request_id = getattr(exc, "provider_request_id", None)
                self._store.mark_side_effect_unknown(
                    key,
                    owner_id,
                    provider_request_id=provider_request_id,
                    error=str(exc),
                )
                reconciled = await provider.verify_or_reconcile(
                    idempotency_key=key,
                    provider_request_id=provider_request_id,
                )
                if reconciled is None:
                    raise
                owner_id = f"side-effect-{uuid.uuid4()}"
                now = time.time()
                if not self._store.claim_side_effect_execution(
                    key, owner_id, now + lease_seconds, now,
                ):
                    continue
                execution = reconciled

            receipt_payload = self._normalize_side_effect_value({
                "idempotency_key": key,
                "provider_name": provider.name,
                "provider_request_id": execution.provider_request_id,
                "request_hash": request_hash,
                "result_reference": execution.result_reference,
            })
            receipt_hash = hashlib.sha256(receipt_payload.encode("utf-8")).hexdigest()
            if getattr(provider, "fail_receipt_once", False):
                provider.fail_receipt_once = False
                self._store.mark_side_effect_unknown(
                    key,
                    owner_id,
                    provider_request_id=execution.provider_request_id,
                    error="simulated local receipt loss",
                )
                raise RuntimeError("simulated local receipt loss")
            self._store.complete_side_effect(key, owner_id, execution, receipt_hash)
            return execution.result_reference

    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a workflow. Prevents later recovery dispatch."""
        wf = self._store.load_workflow(workflow_id)
        if not wf:
            return False
        # Allowed at any pre-terminal state.
        if wf.status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED, WorkflowStatus.COMPENSATED):
            return False
        wf.status = WorkflowStatus.CANCELLED
        wf.dispatch_owner_id = None
        wf.dispatch_lease_expires_at = None
        self._store.save_workflow(wf)
        self._store.append_history(HistoryEvent(
            workflow_id=workflow_id,
            event_type=HistoryEventType.WORKFLOW_CANCELLED,
        ))
        return True

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowRecord]:
        return self._store.load_workflow(workflow_id)

    def close(self) -> None:
        """Close the engine's durable store connection."""
        self._store.close()

    def get_history(self, workflow_id: str) -> List[HistoryEvent]:
        return self._store.load_history(workflow_id)

    def get_activities(self, workflow_id: str) -> List[ActivityRecord]:
        return self._store.load_activities(workflow_id)

    def list_workflows(
        self,
        status: Optional[WorkflowStatus] = None,
        limit: int = 100,
    ) -> List[WorkflowRecord]:
        return self._store.list_workflows(status=status, limit=limit)

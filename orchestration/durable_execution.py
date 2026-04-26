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
"""

from __future__ import annotations

import asyncio
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


class HistoryEventType(str, Enum):
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


# ---------------------------------------------------------------------------
# SQLite Persistence Layer
# ---------------------------------------------------------------------------

class DurableStore:
    """SQLite-backed persistence for workflow state, activities, and history."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._persistent_conn: Optional[sqlite3.Connection] = None
        if db_path == ":memory:":
            # For in-memory databases, reuse a single connection so tables persist
            self._persistent_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._persistent_conn.row_factory = sqlite3.Row
            self._persistent_conn.execute("PRAGMA foreign_keys=ON")
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        if self._persistent_conn is not None:
            return self._persistent_conn
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

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
                    metadata TEXT NOT NULL DEFAULT '{}'
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

                CREATE INDEX IF NOT EXISTS idx_activities_workflow ON activities(workflow_id);
                CREATE INDEX IF NOT EXISTS idx_history_workflow ON history(workflow_id);
                CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows(status);
            """)

    # --- Workflow CRUD ---

    def save_workflow(self, wf: WorkflowRecord) -> None:
        wf.updated_at = time.time()
        with self._connect() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO workflows
                (workflow_id, workflow_type, status, state, created_at, updated_at,
                 completed_at, error, parent_workflow_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                wf.workflow_id, wf.workflow_type, wf.status.value,
                json.dumps(wf.state), wf.created_at, wf.updated_at,
                wf.completed_at, wf.error, wf.parent_workflow_id,
                json.dumps(wf.metadata),
            ))

    def load_workflow(self, workflow_id: str) -> Optional[WorkflowRecord]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM workflows WHERE workflow_id = ?", (workflow_id,)
            ).fetchone()
        if not row:
            return None
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
        result = []
        for row in rows:
            result.append(WorkflowRecord(
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
            ))
        return result

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
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self._store = DurableStore(db_path=db_path)
        self._executor = ActivityExecutor(self._store)
        self._registered: Dict[str, WorkflowFunc] = {}

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
        """Start a new workflow. Returns workflow_id."""
        if workflow_type not in self._registered:
            raise ValueError(f"Unknown workflow type: '{workflow_type}'")

        wf_id = workflow_id or uuid.uuid4().hex
        now = time.time()
        wf = WorkflowRecord(
            workflow_id=wf_id,
            workflow_type=workflow_type,
            status=WorkflowStatus.RUNNING,
            state=input_data,
            created_at=now,
            updated_at=now,
            parent_workflow_id=parent_workflow_id,
            metadata=metadata or {},
        )
        self._store.save_workflow(wf)
        self._store.append_history(HistoryEvent(
            workflow_id=wf_id,
            event_type=HistoryEventType.WORKFLOW_STARTED,
            payload={"workflow_type": workflow_type, "input": input_data},
        ))

        asyncio.create_task(self._run_workflow(wf_id, workflow_type, input_data))
        return wf_id

    async def _run_workflow(
        self,
        workflow_id: str,
        workflow_type: str,
        input_data: Dict[str, Any],
    ) -> None:
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

    async def cancel_workflow(self, workflow_id: str) -> bool:
        wf = self._store.load_workflow(workflow_id)
        if not wf:
            return False
        wf.status = WorkflowStatus.CANCELLED
        self._store.save_workflow(wf)
        self._store.append_history(HistoryEvent(
            workflow_id=workflow_id,
            event_type=HistoryEventType.WORKFLOW_CANCELLED,
        ))
        return True

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowRecord]:
        return self._store.load_workflow(workflow_id)

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

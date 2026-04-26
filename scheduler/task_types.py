"""
Task Types — Data models for the SintraPrime Scheduler
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class TaskStatus(str, Enum):
    """Lifecycle states for a scheduled task."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskType(str, Enum):
    """Classification of how a task is triggered."""
    ONE_TIME = "one_time"
    RECURRING = "recurring"
    TRIGGERED = "triggered"
    CONDITIONAL = "conditional"


# ---------------------------------------------------------------------------
# Core data models
# ---------------------------------------------------------------------------


@dataclass
class Schedule:
    """Defines *when* a task should fire.

    Exactly one scheduling mechanism should be supplied:
    - ``cron_expr``  — standard cron string, e.g. ``"0 9 * * 1"`` (Mon 9 AM)
    - ``interval_minutes`` — repeat every N minutes
    - ``run_at``     — one-time UTC datetime
    - ``trigger_event`` — event name that causes the task to fire
    """
    cron_expr: Optional[str] = None
    interval_minutes: Optional[int] = None
    trigger_event: Optional[str] = None
    run_at: Optional[datetime] = None

    def describe(self) -> str:
        if self.cron_expr:
            return f"cron({self.cron_expr})"
        if self.interval_minutes:
            return f"every {self.interval_minutes} minute(s)"
        if self.run_at:
            return f"once at {self.run_at.isoformat()}"
        if self.trigger_event:
            return f"on event '{self.trigger_event}'"
        return "unscheduled"


@dataclass
class ScheduledTask:
    """Full representation of a task managed by the scheduler."""
    name: str
    description: str = ""
    task_type: TaskType = TaskType.ONE_TIME
    schedule: Optional[Schedule] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    created_by: str = "system"
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    max_retries: int = 3
    retry_count: int = 0
    on_success: Optional[Callable] = None
    on_failure: Optional[Callable] = None
    tags: List[str] = field(default_factory=list)
    timeout_seconds: int = 300
    # Assigned at scheduling time
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    # Internal: the callable to execute
    fn: Optional[Callable] = field(default=None, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type.value,
            "schedule": (
                {
                    "cron_expr": self.schedule.cron_expr,
                    "interval_minutes": self.schedule.interval_minutes,
                    "trigger_event": self.schedule.trigger_event,
                    "run_at": (
                        self.schedule.run_at.isoformat()
                        if self.schedule and self.schedule.run_at
                        else None
                    ),
                }
                if self.schedule
                else None
            ),
            "payload": self.payload,
            "status": self.status.value,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "run_count": self.run_count,
            "max_retries": self.max_retries,
            "retry_count": self.retry_count,
            "tags": self.tags,
            "timeout_seconds": self.timeout_seconds,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduledTask":
        schedule_data = data.get("schedule")
        schedule = None
        if schedule_data:
            run_at = schedule_data.get("run_at")
            schedule = Schedule(
                cron_expr=schedule_data.get("cron_expr"),
                interval_minutes=schedule_data.get("interval_minutes"),
                trigger_event=schedule_data.get("trigger_event"),
                run_at=datetime.fromisoformat(run_at) if run_at else None,
            )
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            task_type=TaskType(data.get("task_type", "one_time")),
            schedule=schedule,
            payload=data.get("payload", {}),
            status=TaskStatus(data.get("status", "pending")),
            created_by=data.get("created_by", "system"),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_run=(
                datetime.fromisoformat(data["last_run"])
                if data.get("last_run")
                else None
            ),
            next_run=(
                datetime.fromisoformat(data["next_run"])
                if data.get("next_run")
                else None
            ),
            run_count=data.get("run_count", 0),
            max_retries=data.get("max_retries", 3),
            retry_count=data.get("retry_count", 0),
            tags=data.get("tags", []),
            timeout_seconds=data.get("timeout_seconds", 300),
        )


@dataclass
class TaskResult:
    """Output record from a single task execution."""
    task_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "success": self.success,
            "output": str(self.output) if self.output is not None else None,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class TaskPipeline:
    """A chain of tasks that are executed in order (or in parallel)."""
    tasks: List[ScheduledTask]
    sequential: bool = True
    name: str = "pipeline"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __len__(self) -> int:
        return len(self.tasks)

    def add(self, task: ScheduledTask) -> "TaskPipeline":
        self.tasks.append(task)
        return self

    def describe(self) -> str:
        mode = "sequential" if self.sequential else "parallel"
        names = " → ".join(t.name for t in self.tasks)
        return f"Pipeline({mode}): {names}"

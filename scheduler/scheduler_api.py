"""
scheduler_api.py — FastAPI router for the SintraPrime Scheduler.

Mount in your main FastAPI app:
    from scheduler.scheduler_api import router as scheduler_router
    app.include_router(scheduler_router)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from fastapi import APIRouter, HTTPException, Query
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover
    raise ImportError("fastapi and pydantic are required for scheduler_api. pip install fastapi pydantic")

from .task_dispatcher import TaskDispatcher
from .task_scheduler import TaskScheduler
from .task_types import Schedule, ScheduledTask, TaskStatus, TaskType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])

# --- Singleton instances (replaced by DI in production) ------------------
_scheduler = TaskScheduler()
_dispatcher = TaskDispatcher(scheduler=_scheduler)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ScheduleModel(BaseModel):
    cron_expr: Optional[str] = None
    interval_minutes: Optional[int] = None
    trigger_event: Optional[str] = None
    run_at: Optional[datetime] = None


class CreateTaskRequest(BaseModel):
    name: str
    description: str = ""
    task_type: str = "one_time"
    schedule: Optional[ScheduleModel] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_by: str = "api"
    max_retries: int = 3
    timeout_seconds: int = 300
    tags: List[str] = Field(default_factory=list)


class DispatchRequest(BaseModel):
    goal: str
    delivery_method: str = "log"
    deadline: Optional[datetime] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class TaskResponse(BaseModel):
    id: str
    name: str
    description: str
    task_type: str
    status: str
    created_by: str
    created_at: str
    last_run: Optional[str]
    next_run: Optional[str]
    run_count: int
    retry_count: int
    max_retries: int
    tags: List[str]


def _task_to_response(task: ScheduledTask) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        name=task.name,
        description=task.description,
        task_type=task.task_type.value,
        status=task.status.value,
        created_by=task.created_by,
        created_at=task.created_at.isoformat(),
        last_run=task.last_run.isoformat() if task.last_run else None,
        next_run=task.next_run.isoformat() if task.next_run else None,
        run_count=task.run_count,
        retry_count=task.retry_count,
        max_retries=task.max_retries,
        tags=task.tags,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/task", response_model=TaskResponse, status_code=201)
def create_task(body: CreateTaskRequest):
    """Create and schedule a new task."""
    schedule: Optional[Schedule] = None
    if body.schedule:
        schedule = Schedule(
            cron_expr=body.schedule.cron_expr,
            interval_minutes=body.schedule.interval_minutes,
            trigger_event=body.schedule.trigger_event,
            run_at=body.schedule.run_at,
        )
    task = ScheduledTask(
        name=body.name,
        description=body.description,
        task_type=TaskType(body.task_type),
        schedule=schedule,
        payload=body.payload,
        created_by=body.created_by,
        max_retries=body.max_retries,
        timeout_seconds=body.timeout_seconds,
        tags=body.tags,
    )
    _scheduler.schedule(task)
    logger.info("API: created task '%s' id=%s", task.name, task.id)
    return _task_to_response(task)


@router.get("/tasks", response_model=List[TaskResponse])
def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """List all scheduled tasks, optionally filtered by status."""
    status_enum: Optional[TaskStatus] = None
    if status:
        try:
            status_enum = TaskStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    tasks = _scheduler.list_tasks(status=status_enum)
    return [_task_to_response(t) for t in tasks]


@router.get("/task/{task_id}", response_model=TaskResponse)
def get_task(task_id: str):
    """Get details for a specific task."""
    task = _scheduler.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return _task_to_response(task)


@router.delete("/task/{task_id}")
def cancel_task(task_id: str):
    """Cancel a scheduled task."""
    success = _scheduler.cancel(task_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return {"ok": True, "message": f"Task {task_id} cancelled"}


@router.put("/task/{task_id}/pause")
def pause_task(task_id: str):
    """Pause a task."""
    success = _scheduler.pause(task_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found or cannot be paused")
    return {"ok": True, "message": f"Task {task_id} paused"}


@router.put("/task/{task_id}/resume")
def resume_task(task_id: str):
    """Resume a paused task."""
    success = _scheduler.resume(task_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Task {task_id} not found or is not paused",
        )
    return {"ok": True, "message": f"Task {task_id} resumed"}


@router.post("/dispatch")
def dispatch_task(body: DispatchRequest):
    """
    Natural-language task dispatch.
    Parse a plain English goal and schedule accordingly.
    """
    task_id = _dispatcher.dispatch(
        goal=body.goal,
        fn=lambda **kw: {"dispatched": True, "goal": body.goal, **kw},
        delivery_method=body.delivery_method,
        deadline=body.deadline,
        payload=body.payload,
    )
    task = _scheduler.get_task(task_id)
    return {
        "task_id": task_id,
        "schedule": task.schedule.describe() if task and task.schedule else "immediate",
        "status": task.status.value if task else "unknown",
    }


@router.get("/status")
def scheduler_status():
    """System-wide scheduler overview."""
    all_tasks = _scheduler.list_tasks()
    by_status: Dict[str, int] = {}
    for t in all_tasks:
        by_status[t.status.value] = by_status.get(t.status.value, 0) + 1
    return {
        "total_tasks": len(all_tasks),
        "by_status": by_status,
        "report": _dispatcher.status_report(),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/next")
def next_tasks(limit: int = Query(5, ge=1, le=50)):
    """Return the next N tasks scheduled to run, ordered by next_run time."""
    all_tasks = _scheduler.list_tasks()
    upcoming = [t for t in all_tasks if t.next_run and t.status == TaskStatus.PENDING]
    upcoming.sort(key=lambda t: t.next_run)  # type: ignore[arg-type]
    return [
        {
            "id": t.id,
            "name": t.name,
            "next_run": t.next_run.isoformat() if t.next_run else None,
            "task_type": t.task_type.value,
        }
        for t in upcoming[:limit]
    ]

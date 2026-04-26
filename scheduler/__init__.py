"""
SintraPrime-Unified Scheduler Module
24/7 Autonomous Scheduled Task Engine
Inspired by Claude Cowork, Hermes Agent, OpenAI Workspace Agents, and Manus AI
"""

from .task_types import (
    ScheduledTask,
    TaskStatus,
    TaskType,
    Schedule,
    TaskResult,
    TaskPipeline,
)
from .task_scheduler import TaskScheduler
from .task_queue import TaskQueue
from .task_dispatcher import TaskDispatcher
from .recurring_tasks import RecurringTaskManager

__all__ = [
    "TaskScheduler",
    "ScheduledTask",
    "TaskQueue",
    "TaskDispatcher",
    "RecurringTaskManager",
    "TaskStatus",
    "TaskType",
    "Schedule",
    "TaskResult",
    "TaskPipeline",
]

__version__ = "1.0.0"
__author__ = "SintraPrime-Unified"

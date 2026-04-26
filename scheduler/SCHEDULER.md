# SintraPrime Scheduler — 24/7 Autonomous Task Engine

> Inspired by **Claude Cowork Scheduled Tasks**, **Hermes Agent** (cloud-native 24/7), **OpenAI Workspace Agents** (long-running execution), and **Manus AI** (deliver results while you're away).

---

## Overview

The SintraPrime Scheduler is a production-ready, 24/7 autonomous background task engine built for legal AI workloads. It runs continuously, persists state across restarts, supports natural-language scheduling, and notifies you of results through any channel.

```
scheduler/
├── __init__.py              # Public exports
├── task_types.py            # Data models (ScheduledTask, Schedule, TaskResult, …)
├── task_scheduler.py        # Core scheduler (APScheduler + threading fallback)
├── task_dispatcher.py       # NL dispatch ("every Monday at 9am")
├── task_queue.py            # Priority queue (thread-safe + asyncio)
├── recurring_tasks.py       # Pre-built SintraPrime recurring tasks
├── task_executor.py         # Sandboxed execution, retry, timeout
├── notification_dispatch.py # Multi-channel notifications (email/Slack/Discord/…)
├── scheduler_api.py         # FastAPI REST router
├── tests/
│   └── test_scheduler.py    # 55+ pytest tests
└── SCHEDULER.md             # This file
```

---

## Quick Start

### Installation

```bash
pip install apscheduler fastapi pydantic uvicorn
```

APScheduler is optional — the scheduler falls back to Python threading if it's not available.

### Mount the API

```python
from fastapi import FastAPI
from scheduler.scheduler_api import router as scheduler_router

app = FastAPI()
app.include_router(scheduler_router)
```

### Start the daemon

```python
from scheduler import TaskScheduler

scheduler = TaskScheduler(db_path="sintra_scheduler.db")
scheduler.start()  # starts background thread / APScheduler
```

---

## Scheduling Tasks

### One-Time Task

```python
from datetime import datetime, timedelta
from scheduler import TaskScheduler

scheduler = TaskScheduler()
scheduler.start()

def generate_brief(**kwargs):
    return "Brief generated for " + kwargs.get("matter_id", "unknown")

task_id = scheduler.schedule_once(
    name="generate_brief_123",
    fn=generate_brief,
    run_at=datetime.utcnow() + timedelta(hours=2),
    payload={"matter_id": "123"},
)
print(f"Scheduled: {task_id}")
```

### Recurring Task (interval)

```python
task_id = scheduler.schedule_recurring(
    name="court_docket_check",
    fn=check_dockets,
    interval_minutes=240,          # every 4 hours
    payload={"case_numbers": ["2024-CV-001"]},
)
```

### Recurring Task (cron)

```python
from scheduler.task_types import ScheduledTask, Schedule, TaskType

task = ScheduledTask(
    name="weekly_deadline_check",
    task_type=TaskType.RECURRING,
    schedule=Schedule(cron_expr="0 8 * * 1"),   # Monday 8 AM
    fn=check_deadlines,
    payload={"warning_days": 14},
)
scheduler.schedule(task)
```

---

## Natural-Language Dispatch

The `TaskDispatcher` understands plain English scheduling instructions, exactly like Claude Cowork's task dispatch interface.

```python
from scheduler import TaskDispatcher, TaskScheduler

scheduler = TaskScheduler()
scheduler.start()
dispatcher = TaskDispatcher(scheduler=scheduler)

# Schedule from plain English
task_id = dispatcher.dispatch(
    goal="run case law digest every morning at 7am",
    fn=fetch_case_law,
)

task_id = dispatcher.dispatch(
    goal="check court dockets every 4 hours",
    fn=monitor_dockets,
    payload={"case_numbers": ["2024-CV-001"]},
)

task_id = dispatcher.dispatch(
    goal="send financial report tomorrow at 9am",
    fn=generate_report,
)
```

### Supported Natural-Language Patterns

| Text | Parsed Schedule |
|---|---|
| `"every morning at 7am"` | `cron: 0 7 * * *` |
| `"every Monday at 9am"` | `cron: 0 9 * * 1` |
| `"daily"` | `cron: 0 9 * * *` |
| `"every 30 minutes"` | `interval: 30 min` |
| `"every 4 hours"` | `interval: 240 min` |
| `"every week at 10am"` | `cron: 0 10 * * 1` |
| `"monthly report"` | `cron: 0 9 1 * *` |
| `"in 2 hours"` | `run_at: now + 2h` |
| `"tomorrow at 3pm"` | `run_at: tomorrow 15:00` |

---

## Built-in SintraPrime Recurring Tasks

Register all defaults in one call:

```python
from scheduler import RecurringTaskManager, TaskScheduler

scheduler = TaskScheduler()
scheduler.start()

mgr = RecurringTaskManager(scheduler=scheduler)
mgr.register_sintra_defaults()
```

| Task Name | Default Schedule | Description |
|---|---|---|
| `daily_case_law_digest` | Daily 7 AM | Fetch new relevant case law |
| `weekly_deadline_check` | Monday 8 AM | Scan matters for upcoming deadlines |
| `monthly_credit_report` | 1st of month 9 AM | Financial health summary |
| `court_docket_monitor` | Every 4 hours | Monitor PACER / court dockets |
| `regulatory_update_check` | Daily 6 AM | IRS/SEC/CFPB rule changes |
| `client_followup_reminders` | Weekdays 9 AM | Pending client action reminders |
| `system_health_check` | Every 30 minutes | Module health + disk/memory |

### Customizing Schedules

```python
from scheduler.task_types import Schedule

mgr.customize(
    "system_health_check",
    schedule=Schedule(interval_minutes=15),   # override: every 15 min
)
mgr.customize(
    "daily_case_law_digest",
    payload={"practice_areas": ["tax", "securities"]},
)
mgr.register_sintra_defaults()  # call after customization
```

---

## Task Queue

```python
from scheduler import TaskQueue

queue = TaskQueue()

queue.enqueue(high_priority_task, priority=1)    # critical
queue.enqueue(normal_task, priority=5)           # normal
queue.enqueue(background_task, priority=10)      # low

# Blocking dequeue (waits for item)
task = queue.dequeue()

# Non-blocking
task = queue.dequeue(block=False)

# Async
task = await queue.async_dequeue()

# Raise a task's priority
queue.promote(task_id, new_priority=1)

# Drain everything (e.g. on shutdown)
cancelled_tasks = queue.drain()
```

---

## Notifications

```python
from scheduler.notification_dispatch import NotificationDispatch

notify = NotificationDispatch(config={
    "smtp_host": "smtp.example.com",
    "smtp_from": "sintra@example.com",
    "email_recipients": ["lawyer@firm.com"],
    "slack_webhook_url": "https://hooks.slack.com/...",
    "discord_webhook_url": "https://discord.com/api/webhooks/...",
    "telegram_bot_token": "BOT_TOKEN",
    "telegram_chat_id": "CHAT_ID",
})

# On task completion
notify.notify_on_complete(task_result, channels=["email", "slack"])

# Urgent failure alert
notify.alert_on_failure(task_result, recipients=["oncall@firm.com"])

# Format results
markdown = notify.format_result(task_result, format="markdown")
json_str = notify.format_result(task_result, format="json")

# Digest
notify.schedule_digest(channel="email", frequency="daily")
```

---

## REST API Reference

| Method | Path | Description |
|---|---|---|
| `POST` | `/scheduler/task` | Create a new scheduled task |
| `GET` | `/scheduler/tasks` | List all tasks (optional `?status=pending`) |
| `GET` | `/scheduler/task/{id}` | Task details |
| `DELETE` | `/scheduler/task/{id}` | Cancel a task |
| `PUT` | `/scheduler/task/{id}/pause` | Pause a task |
| `PUT` | `/scheduler/task/{id}/resume` | Resume a paused task |
| `POST` | `/scheduler/dispatch` | Natural-language dispatch |
| `GET` | `/scheduler/status` | System overview |
| `GET` | `/scheduler/next` | Next N tasks to run |

### Example: Natural-Language Dispatch via API

```bash
curl -X POST http://localhost:8000/scheduler/dispatch \
  -H "Content-Type: application/json" \
  -d '{"goal": "run case law digest every morning at 7am", "delivery_method": "email"}'
```

---

## Comparison: Claude Cowork vs SintraPrime Scheduler

| Feature | Claude Cowork | SintraPrime Scheduler |
|---|---|---|
| Natural language scheduling | ✅ | ✅ |
| Recurring tasks (cron) | ✅ | ✅ |
| One-time tasks | ✅ | ✅ |
| Persistent across restarts | ✅ | ✅ (SQLite) |
| Priority queue | ❌ | ✅ |
| Domain-specific tasks (legal) | ❌ | ✅ |
| Multi-channel notifications | Partial | ✅ (email/Slack/Discord/Telegram/webhook) |
| Sandboxed execution | ❌ | ✅ |
| REST API | ✅ | ✅ (FastAPI) |
| Retry with backoff | ✅ | ✅ |
| Timeout per task | ✅ | ✅ |
| Open source | ❌ | ✅ |

---

## Running Tests

```bash
cd SintraPrime-Unified
pip install pytest fastapi httpx pydantic
pytest scheduler/tests/test_scheduler.py -v
```

---

## Architecture Notes

- **APScheduler** is used when available (pip install apscheduler) for production-grade cron support.
- **Threading fallback**: without APScheduler, interval tasks use `threading.Timer` chains, and cron support is limited to the parsed cron expression being converted to the next `run_at` datetime.
- **SQLite persistence**: all task metadata is written synchronously after every state change. A new `TaskScheduler` instance pointed at the same DB file will pick up all previously registered tasks.
- **Thread safety**: `TaskQueue` uses `threading.Condition` for the heap; `TaskScheduler` uses `threading.Lock` for the tasks dict.

---

*SintraPrime-Unified — Built for 24/7 autonomous legal intelligence.*

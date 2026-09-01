"""Subprocess helpers for durable recovery acceptance tests.

Kept in a real importable module so Windows multiprocessing can spawn it.
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestration.durable_execution import (  # noqa: E402
    DurableWorkflowEngine,
    HistoryEvent,
    HistoryEventType,
    WorkflowRecord,
    WorkflowStatus,
)


def seed_claimed_workflow(db_path: str, workflow_id: str = "runtime-wf") -> None:
    """Persist a stranded claim as process A would leave it."""
    engine = DurableWorkflowEngine(db_path=db_path, dispatch_lease_seconds=0.05)
    try:
        record = WorkflowRecord(
            workflow_id=workflow_id,
            workflow_type="runtime.acceptance",
            status=WorkflowStatus.CLAIMED,
            state={"input": {}},
            dispatch_request_hash="acceptance-hash",
        )
        engine._store.save_workflow(record)
        engine._store.append_history(
            HistoryEvent(
                workflow_id=workflow_id,
                event_type=HistoryEventType.WORKFLOW_CLAIMED,
                payload={"workflow_type": "runtime.acceptance"},
            )
        )
    finally:
        engine.close()


def boot_runtime(
    db_path: str,
    started_path: str,
    completed_path: str,
    stop_path: str,
) -> None:
    """Boot the normal runtime, whose recovery worker autostarts."""
    os.environ["DURABLE_WORKFLOW_STORE_PATH"] = db_path
    os.environ["DURABLE_WORKFLOW_RECOVERY_INTERVAL_SECONDS"] = "0.05"
    os.environ["DURABLE_WORKFLOW_RECOVERY_BATCH_SIZE"] = "10"
    os.environ["DURABLE_WORKFLOW_DISPATCH_LEASE_SECONDS"] = "0.1"

    from portal.config import get_settings
    from portal.services.orchestration_runtime import (
        get_canonical_durable_engine,
        reset_canonical_durable_engine_for_tests,
    )

    async def workflow(ctx, data):
        Path(started_path).write_text("started", encoding="utf-8")
        return {"recovered": True}

    async def main() -> None:
        get_settings.cache_clear()
        reset_canonical_durable_engine_for_tests()
        engine = get_canonical_durable_engine()
        engine.register_workflow("runtime.acceptance", workflow)
        settings = get_settings()
        engine.start_recovery_worker(
            interval_seconds=settings.DURABLE_WORKFLOW_RECOVERY_INTERVAL_SECONDS,
            batch_size=settings.DURABLE_WORKFLOW_RECOVERY_BATCH_SIZE,
        )
        deadline = time.time() + 8.0
        try:
            while time.time() < deadline:
                record = engine.get_workflow("runtime-wf")
                if record and record.status == WorkflowStatus.COMPLETED:
                    Path(completed_path).write_text("completed", encoding="utf-8")
                    break
                await asyncio.sleep(0.05)
            while not Path(stop_path).exists() and time.time() < deadline:
                await asyncio.sleep(0.05)
        finally:
            await engine.shutdown(timeout_seconds=2.0)
            engine.close()
            reset_canonical_durable_engine_for_tests()
            get_settings.cache_clear()

    asyncio.run(main())


def race_claim(
    db_path: str,
    ready_path: str,
    result_path: str,
    sibling_ready_path: str,
) -> None:
    """Race one cross-process durable dispatch claim and report its result."""
    ready = Path(ready_path)
    sibling_ready = Path(sibling_ready_path)
    result = Path(result_path)
    engine = DurableWorkflowEngine(db_path=db_path, dispatch_lease_seconds=30.0)
    try:
        ready.write_text("ready", encoding="utf-8")
        deadline = time.time() + 8.0
        while not sibling_ready.exists() and time.time() < deadline:
            time.sleep(0.01)
        if not sibling_ready.exists():
            raise RuntimeError("other process did not become ready")

        now = time.time()
        claimed = engine._store.try_claim_dispatch(
            "race-wf",
            owner_id=f"worker-{os.getpid()}",
            lease_expires_at=now + 30.0,
            now=now,
        )
        result.write_text("claimed" if claimed else "not-claimed", encoding="utf-8")
    finally:
        engine.close()

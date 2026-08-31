"""Process-level acceptance tests for canonical durable recovery wiring."""
from __future__ import annotations

import multiprocessing
import tempfile
import time
from pathlib import Path

import pytest

from orchestration.durable_execution import DurableWorkflowEngine, WorkflowStatus
from portal.tests._orchestration_runtime_subprocess import (
    boot_runtime,
    race_claim,
    seed_claimed_workflow,
)


def _wait_for(path: Path, timeout: float = 10.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if path.exists():
            return True
        time.sleep(0.05)
    return False


def _join(process: multiprocessing.Process, timeout: float = 15.0) -> None:
    process.join(timeout=timeout)
    if process.is_alive():
        process.terminate()
        process.join(timeout=5.0)
    assert process.exitcode == 0


@pytest.mark.asyncio
async def test_automatic_process_restart_recovery():
    """Normal runtime boot recovers a prior process's CLAIMED workflow."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "durable.db"
        seed_claimed_workflow(str(db_path), "runtime-wf")

        started = Path(tmpdir) / "started"
        completed = Path(tmpdir) / "completed"
        stop = Path(tmpdir) / "stop"
        process = multiprocessing.Process(
            target=boot_runtime,
            args=(str(db_path), str(started), str(completed), str(stop)),
        )
        process.start()
        try:
            assert _wait_for(started), "recovery worker did not execute stranded claim"
            assert _wait_for(completed), "recovered workflow did not complete"
        finally:
            stop.write_text("stop", encoding="utf-8")
            _join(process)

        engine = DurableWorkflowEngine(db_path=str(db_path))
        try:
            record = engine.get_workflow("runtime-wf")
            assert record is not None
            assert record.status == WorkflowStatus.COMPLETED
        finally:
            engine.close()


@pytest.mark.asyncio
async def test_multi_process_recovery_race_single_dispatch_owner():
    """Two OS processes racing one durable claim produce one lease owner."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "durable.db"
        seed_claimed_workflow(str(db_path), "race-wf")

        ready_a = Path(tmpdir) / "ready-a"
        ready_b = Path(tmpdir) / "ready-b"
        result_a = Path(tmpdir) / "result-a"
        result_b = Path(tmpdir) / "result-b"
        process_a = multiprocessing.Process(
            target=race_claim,
            args=(str(db_path), str(ready_a), str(result_a), str(ready_b)),
        )
        process_b = multiprocessing.Process(
            target=race_claim,
            args=(str(db_path), str(ready_b), str(result_b), str(ready_a)),
        )
        process_a.start()
        process_b.start()
        _join(process_a)
        _join(process_b)

        results = [
            result_a.read_text(encoding="utf-8"),
            result_b.read_text(encoding="utf-8"),
        ]
        assert results.count("claimed") == 1
        assert results.count("not-claimed") == 1

        engine = DurableWorkflowEngine(db_path=str(db_path))
        try:
            record = engine.get_workflow("race-wf")
            assert record is not None
            assert record.status == WorkflowStatus.DISPATCHING
            assert record.dispatch_owner_id is not None
            assert record.dispatch_attempt_count == 1
        finally:
            engine.close()

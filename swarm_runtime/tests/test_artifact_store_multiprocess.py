from __future__ import annotations

import json
import multiprocessing as mp
from pathlib import Path

import pytest

from swarm_runtime.artifact_store import ArtifactStore
from swarm_runtime.worker import SwarmEvent, WorkerState, WorkerStatus


def _state(worker_id: str, status: WorkerStatus) -> WorkerState:
    return WorkerState(swarm_id="probe", worker_id=worker_id, role="probe", status=status)


def _status_writer(run_dir: str, worker_id: str, status: str, gate, result) -> None:
    store = ArtifactStore(run_dir)
    gate.wait()
    result.put(store.write_status(worker_id, _state(worker_id, WorkerStatus(status))))


def _event_writer(run_dir: str, worker_id: str, count: int, gate, result) -> None:
    store = ArtifactStore(run_dir)
    gate.wait()
    errors = 0
    for i in range(count):
        try:
            store.record_event(SwarmEvent(float(i), "probe", worker_id, "probe", {"i": i}))
        except Exception:
            errors += 1
    result.put(errors)


def test_multiprocess_status_writes_are_atomic_and_error_free(tmp_path: Path) -> None:
    ctx = mp.get_context("spawn")
    gate = ctx.Barrier(2)
    result = ctx.Queue()
    processes = [
        ctx.Process(target=_status_writer, args=(str(tmp_path), "one", "running", gate, result))
        for _ in range(2)
    ]
    for process in processes:
        process.start()
    writes = [result.get() for _ in processes]
    for process in processes:
        process.join()
    path = tmp_path / "worker-one" / "status.json"
    assert all(writes)
    assert json.loads(path.read_text(encoding="utf-8"))
    assert not list(tmp_path.rglob("*.tmp"))


@pytest.mark.parametrize("iteration", range(20))
def test_terminal_timeout_rejects_stale_running(tmp_path: Path, iteration: int) -> None:
    store = ArtifactStore(tmp_path / str(iteration))
    worker_id = "same"
    assert store.write_status(worker_id, _state(worker_id, WorkerStatus.TIMED_OUT)) is True
    assert store.write_status(worker_id, _state(worker_id, WorkerStatus.RUNNING)) is False
    assert store.read_status(worker_id)["status"] == WorkerStatus.TIMED_OUT.value


@pytest.mark.parametrize("iteration", range(20))
def test_completed_rejects_stale_running(tmp_path: Path, iteration: int) -> None:
    store = ArtifactStore(tmp_path / str(iteration))
    worker_id = "same"
    assert store.write_status(worker_id, _state(worker_id, WorkerStatus.COMPLETED)) is True
    assert store.write_status(worker_id, _state(worker_id, WorkerStatus.RUNNING)) is False
    assert store.read_status(worker_id)["status"] == WorkerStatus.COMPLETED.value



def test_multiprocess_status_writer_processes_complete(tmp_path: Path) -> None:
    ctx = mp.get_context("spawn")
    gate = ctx.Barrier(2)
    result = ctx.Queue()
    processes = [ctx.Process(target=_status_writer, args=(str(tmp_path), "two", "running", gate, result)) for _ in range(2)]
    for process in processes:
        process.start()
    results = [result.get() for _ in processes]
    for process in processes:
        process.join()
    assert results == [True, True]
    assert all(process.exitcode == 0 for process in processes)
    assert json.loads((tmp_path / "worker-two" / "status.json").read_text(encoding="utf-8"))
    assert not list(tmp_path.rglob("*.tmp"))



@pytest.mark.parametrize("iteration", range(20))
def test_terminal_status_rejects_late_stale_process_write(tmp_path: Path, iteration: int) -> None:
    run_dir = tmp_path / str(iteration)
    store = ArtifactStore(run_dir)
    worker_id = "race"
    assert store.write_status(worker_id, _state(worker_id, WorkerStatus.TIMED_OUT)) is True

    ctx = mp.get_context("spawn")
    gate = ctx.Barrier(1)
    result = ctx.Queue()
    process = ctx.Process(target=_status_writer, args=(str(run_dir), worker_id, "running", gate, result))
    process.start()
    outcome = result.get()
    process.join()

    assert outcome is False
    assert process.exitcode == 0
    assert json.loads((run_dir / "worker-race" / "status.json").read_text(encoding="utf-8"))["status"] == "timed_out"
    assert not list(run_dir.rglob("*.tmp"))


@pytest.mark.parametrize("iteration", range(20))
def test_completed_status_rejects_late_stale_process_write(tmp_path: Path, iteration: int) -> None:
    run_dir = tmp_path / str(iteration)
    store = ArtifactStore(run_dir)
    worker_id = "completed"
    assert store.write_status(worker_id, _state(worker_id, WorkerStatus.COMPLETED)) is True

    ctx = mp.get_context("spawn")
    gate = ctx.Barrier(1)
    result = ctx.Queue()
    process = ctx.Process(target=_status_writer, args=(str(run_dir), worker_id, "running", gate, result))
    process.start()
    outcome = result.get()
    process.join()

    assert outcome is False
    assert process.exitcode == 0
    assert json.loads((run_dir / "worker-completed" / "status.json").read_text(encoding="utf-8"))["status"] == "completed"
    assert not list(run_dir.rglob("*.tmp"))


def test_terminal_state_wins_over_later_stale_worker_write(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    worker_id = "same"
    assert store.write_status(worker_id, _state(worker_id, WorkerStatus.TIMED_OUT)) is True
    assert store.write_status(worker_id, _state(worker_id, WorkerStatus.RUNNING)) is False
    assert store.read_status(worker_id)["status"] == WorkerStatus.TIMED_OUT.value


def test_completed_state_wins_over_later_stale_controller_write(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    worker_id = "same"
    assert store.write_status(worker_id, _state(worker_id, WorkerStatus.COMPLETED)) is True
    assert store.write_status(worker_id, _state(worker_id, WorkerStatus.RUNNING)) is False
    assert store.read_status(worker_id)["status"] == WorkerStatus.COMPLETED.value


def test_multiprocess_event_log_is_serialized(tmp_path: Path) -> None:
    ctx = mp.get_context("spawn")
    count = 200
    gate = ctx.Barrier(2)
    result = ctx.Queue()
    processes = [ctx.Process(target=_event_writer, args=(str(tmp_path), f"worker-{i}", count, gate, result)) for i in range(2)]
    for process in processes:
        process.start()
    errors = [result.get() for _ in processes]
    for process in processes:
        process.join()
    lines = (tmp_path / "event_log.jsonl").read_text(encoding="utf-8").splitlines()
    assert errors == [0, 0]
    assert len(lines) == 2 * count
    assert all(json.loads(line) for line in lines)

from __future__ import annotations

import json
import multiprocessing as mp
import time
from pathlib import Path
from unittest import mock

import pytest

from swarm_runtime.artifact_store import (
    ArtifactStore,
    LockAcquisitionTimeoutError,
    _CrossProcessLock,
)
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


def _lock_holder(lock_path: str, held, release, result) -> None:
    lock = _CrossProcessLock(Path(lock_path))
    acquired = False
    released_signal = False
    try:
        lock.__enter__()
        acquired = True
        held.set()
        released_signal = release.wait(10)
    finally:
        lock.__exit__(None, None, None)
        result.put({
            "acquired": acquired,
            "released": released_signal,
            "handle_cleared": lock._handle is None,
        })




def _lock_contender(lock_path: str, result) -> None:
    lock = _CrossProcessLock(Path(lock_path), lock_timeout_seconds=0.2)
    started = time.monotonic()
    try:
        lock.__enter__()
    except LockAcquisitionTimeoutError as exc:
        result.put({
            "timeout": True,
            "exception": type(exc).__name__,
            "elapsed": time.monotonic() - started,
            "handle_closed": lock._handle is None,
            "lock_not_held": lock._handle is None,
        })
        return
    else:
        lock.__exit__(None, None, None)
        result.put({"timeout": False})


def test_independent_process_contention_timeout_and_reacquisition(tmp_path: Path) -> None:
    ctx = mp.get_context("spawn")
    lock_path = tmp_path / "lock"
    held = ctx.Event()
    release = ctx.Event()
    holder_result = ctx.Queue()
    contender_result = ctx.Queue()
    holder = ctx.Process(target=_lock_holder, args=(str(lock_path), held, release, holder_result))
    contender = ctx.Process(target=_lock_contender, args=(str(lock_path), contender_result))
    holder.start()
    assert held.wait(10)
    contender.start()
    contender_outcome = contender_result.get(timeout=10)
    contender.join(10)
    assert contender_outcome["timeout"] is True
    assert contender_outcome["exception"] == "LockAcquisitionTimeoutError"
    assert contender_outcome["elapsed"] >= 0.15
    assert contender_outcome["elapsed"] < 2.0
    assert contender_outcome["handle_closed"] is True
    assert contender_outcome["lock_not_held"] is True
    release.set()
    holder_outcome = holder_result.get(timeout=10)
    holder.join(10)
    assert holder_outcome["acquired"] is True
    assert holder_outcome["released"] is True
    assert holder_outcome["handle_cleared"] is True
    assert holder.exitcode == 0
    assert contender.exitcode == 0
    with _CrossProcessLock(lock_path, lock_timeout_seconds=0.2):
        pass


@pytest.mark.parametrize("iteration", range(5))
def test_independent_process_contention_repeatable(tmp_path: Path, iteration: int) -> None:
    test_independent_process_contention_timeout_and_reacquisition(tmp_path / str(iteration))




def test_lock_acquisition_failure_closes_handle(tmp_path: Path) -> None:
    lock = _CrossProcessLock(tmp_path / "lock")
    with (
        mock.patch("msvcrt.locking", side_effect=RuntimeError("forced acquisition failure")),
        pytest.raises(RuntimeError, match="forced acquisition failure"),
    ):
        lock.__enter__()
    assert lock._handle is None


def test_lock_timeout_closes_handle_and_allows_reacquisition(tmp_path: Path) -> None:
    lock = _CrossProcessLock(tmp_path / "lock", lock_timeout_seconds=0.01)
    with _CrossProcessLock(tmp_path / "lock"), pytest.raises(LockAcquisitionTimeoutError):
        lock.__enter__()
    assert lock._handle is None
    with _CrossProcessLock(tmp_path / "lock", lock_timeout_seconds=0.1):
        pass


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
    observed = {(event["worker_id"], event["details"]["i"]) for event in map(json.loads, lines)}
    expected = {(f"worker-{worker}", i) for worker in range(2) for i in range(count)}
    assert errors == [0, 0]
    assert all(process.exitcode == 0 for process in processes)
    assert len(observed) == len(expected) == 2 * count
    assert observed == expected
    assert len(lines) == len(observed)
    assert all(json.loads(line) for line in lines)
    assert not list(tmp_path.rglob("*.tmp"))


def test_lock_body_exception_releases_handle(tmp_path: Path) -> None:
    lock = _CrossProcessLock(tmp_path / "lock")
    with pytest.raises(RuntimeError, match="body failure"), lock:
        raise RuntimeError("body failure")
    assert lock._handle is None

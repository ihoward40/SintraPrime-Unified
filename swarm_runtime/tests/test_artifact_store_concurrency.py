from __future__ import annotations

import json
import threading
from pathlib import Path

from swarm_runtime.artifact_store import ArtifactStore
from swarm_runtime.worker import WorkerState, WorkerStatus


def test_concurrent_status_writes_are_atomic(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    errors: list[BaseException] = []
    writers = 4
    iterations = 100

    def writer(index: int) -> None:
        try:
            for iteration in range(iterations):
                state = WorkerState(
                    swarm_id="stress",
                    worker_id="worker-1",
                    role="breaker",
                    status=WorkerStatus.RUNNING,
                    phase=f"writer-{index}-{iteration}",
                )
                store.write_status("worker-1", state)
        except BaseException as exc:  # pragma: no cover - diagnostic collection
            errors.append(exc)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(writers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    status_path = tmp_path / "worker-worker-1" / "status.json"
    assert json.loads(status_path.read_text(encoding="utf-8"))
    assert not list(status_path.parent.glob("*.tmp"))

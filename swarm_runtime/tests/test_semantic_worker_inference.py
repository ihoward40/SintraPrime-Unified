"""S1 semantic worker acceptance tests."""
from __future__ import annotations

import tempfile
from pathlib import Path

from swarm_runtime import DelegateTask, HermesSwarmAdapter

REPO = Path(__file__).resolve().parents[2]


def _run(task_params: dict) -> dict:
    run_dir = tempfile.mkdtemp(prefix="semantic-worker-")
    task = DelegateTask(
        task_id="semantic-1",
        description="Perform one bounded semantic inference",
        role="breaker",
        worker_class="ModelReasoningWorker",
        timeout_seconds=30,
        run_context={"swarm_id": "SWARM-SEMANTIC-ACCEPTANCE-001"},
        task_params=task_params,
        artifact_filename="artifacts/result.json",
    )
    result = HermesSwarmAdapter(
        repo_path=str(REPO), run_dir=run_dir, max_concurrent=1
    ).delegate([task])
    return {"result": result.to_dict(), "run_dir": run_dir}


def test_semantic_worker_calls_governed_router_and_writes_one_artifact() -> None:
    outcome = _run(
        {
            "prompt": "Return a bounded deterministic summary.",
            "task_type": "summarization",
            "capability": "summarization",
            "provider_fixtures": [{"name": "fallback", "fail_times": 0}],
        }
    )
    result = outcome["result"]
    assert result["status"] == "SUCCESS"
    assert result["workers_completed"] == 1
    assert len(result["artifacts"]) == 1
    artifact = result["artifacts"][0]["artifact"]
    assert artifact["state"] == "completed"
    assert artifact["findings"]["provider"] == "fallback"
    assert artifact["findings"]["attempt_log"]


def test_semantic_worker_fails_over_to_second_governed_provider() -> None:
    outcome = _run(
        {
            "prompt": "Return a bounded deterministic summary after failover.",
            "task_type": "summarization",
            "capability": "summarization",
            "provider_fixtures": [
                        {"name": "primary", "fail_times": 1, "quality": "premium", "model": "model-a"},
                        {"name": "fallback", "fail_times": 0, "quality": "standard", "model": "model-b"},
                    ],
            "governed_provider_priority": {"primary": 0, "fallback": 1},
        }
    )
    result = outcome["result"]
    assert result["status"] == "SUCCESS"
    assert result["workers_completed"] == 1
    artifact = result["artifacts"][0]["artifact"]
    assert artifact["state"] == "completed"
    assert artifact["findings"]["provider"] == "fallback"
    assert artifact["findings"]["providers_attempted"] == ["primary", "fallback"]
    assert artifact["findings"]["failover_count"] == 1
    assert len(result["artifacts"]) == 1

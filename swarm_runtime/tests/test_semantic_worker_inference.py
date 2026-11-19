"""S1 semantic worker acceptance tests."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from swarm_runtime import DelegateTask, HermesSwarmAdapter

REPO = Path(__file__).resolve().parents[2]


def _run(task_params: dict, *, run_dir: str | None = None) -> dict:
    run_dir = run_dir or tempfile.mkdtemp(prefix="semantic-worker-")
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


def _artifact(outcome: dict) -> dict:
    return outcome["result"]["artifacts"][0]["artifact"]


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
    artifact = _artifact(outcome)
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
    artifact = _artifact(outcome)
    assert artifact["state"] == "completed"
    assert artifact["findings"]["provider"] == "fallback"
    assert artifact["findings"]["providers_attempted"] == ["primary", "fallback"]
    assert artifact["findings"]["failover_count"] == 1
    assert len(result["artifacts"]) == 1


def test_semantic_worker_records_timeout_health_and_preserves_identity() -> None:
    with tempfile.TemporaryDirectory(prefix="semantic-worker-health-") as run_dir:
        outcome = _run(
            {
                "prompt": "Return a bounded deterministic summary after timeout failover.",
                "task_type": "summarization",
                "capability": "summarization",
                "timeout_seconds": 29,
                "governed_providers": [
                    {
                        "kind": "mock",
                        "name": "primary",
                        "model": "model-a",
                        "quality": "premium",
                        "fail_times": 1,
                        "error_kind": "timeout_progress",
                    },
                    {
                        "kind": "mock",
                        "name": "fallback",
                        "model": "model-b",
                        "quality": "standard",
                    },
                ],
                "governed_provider_priority": {"primary": 0, "fallback": 1},
                "provider_health_store_dir": run_dir,
            },
            run_dir=run_dir,
        )

        result = outcome["result"]
        artifact = _artifact(outcome)
        findings = artifact["findings"]
        health_file = Path(findings["provider_health_store_path"])
        health_data = json.loads(health_file.read_text(encoding="utf-8"))

        assert result["status"] == "SUCCESS"
        assert len(result["artifacts"]) == 1
        assert findings["provider"] == "fallback"
        assert findings["providers_attempted"] == ["primary", "fallback"]
        assert findings["configured_provider_timeout_seconds"] < findings["worker_timeout_seconds"]
        assert all(entry["worker_id"] == "semantic-1" for entry in findings["attempt_log"])
        assert all(entry["task_id"] == "semantic-1" for entry in findings["attempt_log"])
        assert health_data["primary"]["timeout_count"] == 1
        assert health_data["fallback"]["success_count"] == 1


def test_semantic_worker_persists_cooldown_across_controller_restart() -> None:
    with tempfile.TemporaryDirectory(prefix="semantic-worker-restart-") as run_dir:
        first = _run(
            {
                "prompt": "Drive primary into cooldown, then succeed on fallback.",
                "task_type": "summarization",
                "capability": "summarization",
                "timeout_seconds": 29,
                "max_attempts": 3,
                "max_attempts_per_provider": 3,
                "governed_providers": [
                    {
                        "kind": "mock",
                        "name": "primary",
                        "model": "model-a",
                        "quality": "premium",
                        "fail_times": 3,
                        "error_kind": "timeout_progress",
                    },
                    {
                        "kind": "mock",
                        "name": "fallback",
                        "model": "model-b",
                        "quality": "standard",
                    },
                ],
                "governed_provider_priority": {"primary": 0, "fallback": 1},
                "provider_health_store_dir": run_dir,
            },
            run_dir=run_dir,
        )
        first_artifact = _artifact(first)
        first_findings = first_artifact["findings"]
        first_health = json.loads(
            Path(first_findings["provider_health_store_path"]).read_text(encoding="utf-8")
        )

        assert first["result"]["status"] == "SUCCESS"
        assert len(first["result"]["artifacts"]) == 1
        assert first_findings["providers_attempted"] == [
            "primary",
            "primary",
            "primary",
            "fallback",
        ]
        assert first_health["primary"]["state"] == "cooldown"
        assert first_health["primary"]["timeout_count"] == 3

        second = _run(
            {
                "prompt": "Reuse persisted cooldown and route directly to fallback.",
                "task_type": "summarization",
                "capability": "summarization",
                "timeout_seconds": 29,
                "governed_providers": [
                    {
                        "kind": "mock",
                        "name": "primary",
                        "model": "model-a",
                        "quality": "premium",
                    },
                    {
                        "kind": "mock",
                        "name": "fallback",
                        "model": "model-b",
                        "quality": "standard",
                    },
                ],
                "governed_provider_priority": {"primary": 0, "fallback": 1},
                "provider_health_store_dir": run_dir,
            },
            run_dir=run_dir,
        )

        second_artifact = _artifact(second)
        second_findings = second_artifact["findings"]

        assert second["result"]["status"] == "SUCCESS"
        assert len(second["result"]["artifacts"]) == 1
        assert second_findings["provider"] == "fallback"
        assert second_findings["providers_attempted"] == ["fallback"]
        assert second_findings["provider_health"]["primary"]["state"] == "cooldown"

from __future__ import annotations

import json
from pathlib import Path

import pytest

from swarm_runtime.artifact_store import ArtifactStore
from swarm_runtime.worker import WorkerState, WorkerStatus

TERMINAL_CASES = [
    "success",
    "timeout_first_byte",
    "timeout_progress",
    "rate_limited",
    "provider_5xx",
    "malformed_response",
    "schema_invalid",
    "auth_failure",
    "provider_unavailable",
    "policy_denied",
    "cancelled",
    "provider_exhaustion",
    "successful_failover",
]


@pytest.mark.parametrize("case", TERMINAL_CASES)
def test_exactly_one_terminal_artifact(case: str, tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    state = WorkerState(swarm_id="matrix", worker_id=case, role="breaker", status=WorkerStatus.COMPLETED)
    artifact = {
        "outcome": "success" if case in {"success", "successful_failover"} else "failure",
        "failure_class": None if case in {"success", "successful_failover"} else case,
        "provider_attempts": 2 if case in {"successful_failover", "provider_exhaustion"} else 1,
        "providers_attempted": ["primary", "fallback"] if case in {"successful_failover", "provider_exhaustion"} else ["primary"],
        "failover_count": 1 if case in {"successful_failover", "provider_exhaustion"} else 0,
        "final_provider": "fallback" if case == "successful_failover" else None,
        "final_model": "model-fallback" if case == "successful_failover" else None,
        "errors": [] if case in {"success", "successful_failover"} else [case],
    }
    store.write_findings(case, artifact, state)
    assert len(list((tmp_path / f"worker-{case}").glob("findings.json"))) == 1
    assert json.loads((tmp_path / f"worker-{case}" / "findings.json").read_text())

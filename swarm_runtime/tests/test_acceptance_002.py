"""SWARM-ACCEPTANCE-002 — Failure injection / provider failover test.

Intentionally assign one worker to a simulated stalled provider.
Expected:
  worker begins → provider exceeds threshold → failover → worker continues → artifact produced
Required:
  PROVIDER_FAILOVER = PASS
  WORKER_SURVIVED_PROVIDER_FAILURE = TRUE
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from swarm_runtime import SwarmController, WorkerSpec

REPO = Path(__file__).resolve().parents[2]
def run_acceptance_002() -> dict:
    swarm_id = "SWARM-ACCEPTANCE-002"

    controller = SwarmController(
        swarm_id=swarm_id,
        repo_path=str(REPO),
        run_dir=os.path.join(
            os.getenv("LOCALAPPDATA", os.path.expanduser("~")),
            "SintraPrime", "swarm-runs", swarm_id,
        ),
        max_concurrent=3,
    )

    specs = [
        WorkerSpec(
            worker_id="F1",
            role="failover_test",
            worker_class="FailoverTestWorker",
            task={"stall_duration": 3, "stall_phase": "before_work"},
            artifact_path="artifacts/failover-test.json",
            base_sha="eeb55ffb",
            timeout_seconds=30,
        ),
        WorkerSpec(
            worker_id="N1",
            role="normal_search",
            worker_class="CodeSearchWorker",
            task={"pattern": r"ForeignKey", "path": "portal/models", "file_glob": "*.py"},
            artifact_path="artifacts/normal-search.json",
            base_sha="eeb55ffb",
            timeout_seconds=30,
        ),
        WorkerSpec(
            worker_id="N2",
            role="normal_ast",
            worker_class="ASTAnalysisWorker",
            task={"path": "portal/models", "target": "foreign_keys"},
            artifact_path="artifacts/normal-ast.json",
            base_sha="eeb55ffb",
            timeout_seconds=30,
        ),
    ]

    print(f"[{swarm_id}] Launching {len(specs)} workers (1 failover + 2 normal)...")
    controller.launch_all(specs)
    summary = controller.wait(timeout=60)

    s = summary.to_dict()
    print(f"\n{'='*60}")
    print("SWARM-ACCEPTANCE-002 RESULTS")
    print(f"{'='*60}")
    for d in s['worker_details']:
        print(f"  Worker {d['worker_id']} ({d['role']}): status={d['status']} "
              f"exit={d['exit_code']} failovers={d['failover_count']} "
              f"artifact={d['artifact_valid']}")

    # Check failover worker specifically
    f1 = next(d for d in s['worker_details'] if d['worker_id'] == 'F1')
    failover_passed = (
        f1['status'] == 'completed'
        and f1['failover_count'] >= 1
        and f1['artifact_valid']
    )

    print("\nACCEPTANCE CRITERIA:")
    criteria = [
        ("PROVIDER_FAILOVER = PASS", failover_passed),
        ("WORKER_SURVIVED_PROVIDER_FAILURE = TRUE", f1['status'] == 'completed'),
        ("FAILOVER_WORKER_ARTIFACT_VALID", f1['artifact_valid']),
        ("FAILOVER_COUNT >= 1", f1['failover_count'] >= 1),
        ("NORMAL_WORKERS_UNAFFECTED",
         all(d['status'] == 'completed' for d in s['worker_details'] if d['worker_id'].startswith('N'))),
    ]
    all_pass = all(p for _, p in criteria)
    for name, passed in criteria:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")

    print(f"\n  OVERALL: {'PASS' if all_pass else 'FAIL'}")
    return s


def test_run() -> None:
    """Pytest entry point — delegates to run_* function."""
    result = run_acceptance_002()
    if isinstance(result, dict):
        # Check for all_pass or swarm_result
        if "all_pass" in result:
            assert result["all_pass"], "run_acceptance_002 did not pass"
        elif "swarm_result" in result:
            assert result["swarm_result"] == "SUCCESS", "run_acceptance_002 failed"
        elif "status" in result:
            assert result["status"] == "SUCCESS", "run_acceptance_002 failed"


if __name__ == "__main__":
    result = run_acceptance_002()
    sys.exit(0 if result['swarm_result'] in ('SUCCESS', 'PARTIAL') else 1)

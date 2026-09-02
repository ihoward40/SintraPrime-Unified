"""SWARM-ACCEPTANCE-001 — 5 independent read-only deterministic workers.

Required:
  WORKERS_REQUESTED = 5
  WORKERS_STARTED = 5
  WORKERS_COMPLETED = 5
  WORKERS_TIMED_OUT = 0
  WORKERS_MISSING_ARTIFACT = 0
  MAX_SIMULTANEOUS_WORKERS >= 3
  VALID_ARTIFACTS = 5/5
  CONTROLLER_FALLBACK_REQUIRED = FALSE

Workers:
  A — inventory Tenant FK references (CodeSearchWorker)
  B — inventory User FK references (CodeSearchWorker)
  C — inventory PortableUUID usage (CodeSearchWorker)
  D — inventory RLS identity casts (DatabaseSchemaWorker)
  E — inventory identity-related API schemas (ASTAnalysisWorker)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from swarm_runtime import SwarmController, WorkerSpec

REPO = Path(__file__).resolve().parents[2]


def run_acceptance_001() -> dict:
    swarm_id = "SWARM-ACCEPTANCE-001"
    repo_path = str(REPO)

    controller = SwarmController(
        swarm_id=swarm_id,
        repo_path=repo_path,
        run_dir=os.path.join(
            os.getenv("LOCALAPPDATA", os.path.expanduser("~")),
            "SintraPrime", "swarm-runs", swarm_id,
        ),
        max_concurrent=5,
    )

    # Define 5 independent read-only deterministic workers
    specs = [
        WorkerSpec(
            worker_id="A",
            role="tenant_fk_inventory",
            worker_class="CodeSearchWorker",
            task={
                "pattern": r"ForeignKey.*tenants\.id",
                "path": "portal/",
                "file_glob": "*.py",
                "context_lines": 0,
            },
            artifact_path="artifacts/lane-a-tenant-fk.json",
            base_sha="eeb55ffb4d6bf8b71cabc9554ec8119927efada4",
            timeout_seconds=60,
        ),
        WorkerSpec(
            worker_id="B",
            role="user_fk_inventory",
            worker_class="CodeSearchWorker",
            task={
                "pattern": r"ForeignKey.*users\.id",
                "path": "portal/",
                "file_glob": "*.py",
                "context_lines": 0,
            },
            artifact_path="artifacts/lane-b-user-fk.json",
            base_sha="eeb55ffb4d6bf8b71cabc9554ec8119927efada4",
            timeout_seconds=60,
        ),
        WorkerSpec(
            worker_id="C",
            role="portable_uuid_usage",
            worker_class="CodeSearchWorker",
            task={
                "pattern": r"PortableUUID",
                "path": "portal/",
                "file_glob": "*.py",
                "context_lines": 1,
            },
            artifact_path="artifacts/lane-c-portable-uuid.json",
            base_sha="eeb55ffb4d6bf8b71cabc9554ec8119927efada4",
            timeout_seconds=60,
        ),
        WorkerSpec(
            worker_id="D",
            role="rls_identity_casts",
            worker_class="DatabaseSchemaWorker",
            task={
                "path": "portal/migrations",
                "extract": "rls_policies",
            },
            artifact_path="artifacts/lane-d-rls-casts.json",
            base_sha="eeb55ffb4d6bf8b71cabc9554ec8119927efada4",
            timeout_seconds=60,
        ),
        WorkerSpec(
            worker_id="E",
            role="api_schema_identity_types",
            worker_class="ASTAnalysisWorker",
            task={
                "path": "portal/routers",
                "target": "class_defs",
            },
            artifact_path="artifacts/lane-e-api-schemas.json",
            base_sha="eeb55ffb4d6bf8b71cabc9554ec8119927efada4",
            timeout_seconds=60,
        ),
    ]

    # Launch all 5 workers
    print(f"[{swarm_id}] Launching {len(specs)} workers...")
    controller.launch_all(specs)

    # Wait for completion
    print(f"[{swarm_id}] Waiting for workers to complete...")
    summary = controller.wait(timeout=120)

    # Print results
    s = summary.to_dict()
    print(f"\n{'='*60}")
    print("SWARM-ACCEPTANCE-001 RESULTS")
    print(f"{'='*60}")
    print(f"  workers_requested:     {s['workers_requested']}")
    print(f"  workers_started:       {s['workers_started']}")
    print(f"  workers_completed:     {s['workers_completed']}")
    print(f"  workers_failed:        {s['workers_failed']}")
    print(f"  workers_timed_out:     {s['workers_timed_out']}")
    print(f"  workers_missing_artifact: {s['workers_missing_artifact']}")
    print(f"  max_simultaneous_workers: {s['max_simultaneous_workers']}")
    print(f"  valid_artifacts:       {s['valid_artifacts']}")
    print(f"  invalid_artifacts:     {s['invalid_artifacts']}")
    print(f"  swarm_result:          {s['swarm_result']}")
    print(f"  duration_seconds:      {s['duration_seconds']:.1f}s")
    print()
    for detail in s['worker_details']:
        print(f"  Worker {detail['worker_id']} ({detail['role']}):")
        print(f"    status={detail['status']}  exit_code={detail['exit_code']}"
              f"  elapsed={detail['elapsed_seconds']:.1f}s"
              f"  artifact_valid={detail['artifact_valid']}")
        if detail.get('errors'):
            print(f"    errors: {detail['errors']}")

    # Validation
    print(f"\n{'='*60}")
    print("ACCEPTANCE CRITERIA")
    print(f"{'='*60}")
    criteria = [
        ("WORKERS_REQUESTED == 5", s['workers_requested'] == 5),
        ("WORKERS_STARTED == 5", s['workers_started'] == 5),
        ("WORKERS_COMPLETED == 5", s['workers_completed'] == 5),
        ("WORKERS_TIMED_OUT == 0", s['workers_timed_out'] == 0),
        ("WORKERS_MISSING_ARTIFACT == 0", s['workers_missing_artifact'] == 0),
        ("MAX_SIMULTANEOUS_WORKERS >= 3", s['max_simultaneous_workers'] >= 3),
        ("VALID_ARTIFACTS == 5", s['valid_artifacts'] == 5),
        ("CONTROLLER_FALLBACK_REQUIRED == FALSE", not s['controller_fallback_required']),
        ("SWARM_RESULT == SUCCESS", s['swarm_result'] == "SUCCESS"),
    ]
    all_pass = True
    for name, passed in criteria:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  [{status}] {name}")

    print(f"\n  OVERALL: {'PASS' if all_pass else 'FAIL'}")
    print(f"  SWARM_RUNTIME_CERTIFICATION = {'LOCALLY_CERTIFIED' if all_pass else 'FAILED'}")

    return s


def test_run() -> None:
    """Pytest entry point — delegates to run_* function."""
    result = run_acceptance_001()
    if isinstance(result, dict):
        # Check for all_pass or swarm_result
        if "all_pass" in result:
            assert result["all_pass"], "run_acceptance_001 did not pass"
        elif "swarm_result" in result:
            assert result["swarm_result"] == "SUCCESS", "run_acceptance_001 failed"
        elif "status" in result:
            assert result["status"] == "SUCCESS", "run_acceptance_001 failed"


if __name__ == "__main__":
    result = run_acceptance_001()
    sys.exit(0 if result['swarm_result'] == 'SUCCESS' else 1)

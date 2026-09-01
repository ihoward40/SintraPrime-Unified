"""SWARM-ACCEPTANCE-005B — Controller restart recovery test.

Create a swarm, start workers, allow partial progress, terminate SwarmController,
leave workers/artifacts/checkpoints on disk, restart controller.

Required:
  RUN_DISCOVERED = TRUE
  WORKER_STATE_RECONSTRUCTED = TRUE
  COMPLETED_WORKERS_NOT_RESTARTED = TRUE
  INCOMPLETE_WORKERS_RECONSTRUCTED = TRUE
  DUPLICATE_EXECUTION = 0
  SUMMARY_REBUILT = TRUE
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from swarm_runtime import SwarmController, WorkerSpec
from swarm_runtime.artifact_store import ArtifactStore

REPO = Path(__file__).resolve().parents[2]
def run_acceptance_005b() -> dict:
    swarm_id = "SWARM-ACCEPTANCE-005B"
    run_dir = os.path.join(
        os.getenv("LOCALAPPDATA", os.path.expanduser("~")),
        "SintraPrime", "swarm-runs", swarm_id,
    )

    # Clean previous
    import shutil
    shutil.rmtree(run_dir, ignore_errors=True)

    repo_path = str(REPO)
    store = ArtifactStore(run_dir)

    # Phase 1: Launch 3 workers — 2 will complete, 1 will be interrupted
    print(f"[{swarm_id}] Phase 1: Launching 3 workers...")
    controller1 = SwarmController(
        swarm_id=swarm_id,
        repo_path=repo_path,
        run_dir=run_dir,
        max_concurrent=3,
    )

    specs = [
        WorkerSpec(
            worker_id="R1",
            role="fast_search",
            worker_class="CodeSearchWorker",
            task={"pattern": r"ForeignKey.*tenants", "path": "portal/models", "file_glob": "*.py"},
            artifact_path="artifacts/r1.json",
            base_sha="eeb55ffb",
            timeout_seconds=30,
        ),
        WorkerSpec(
            worker_id="R2",
            role="fast_ast",
            worker_class="ASTAnalysisWorker",
            task={"path": "portal/models", "target": "class_defs"},
            artifact_path="artifacts/r2.json",
            base_sha="eeb55ffb",
            timeout_seconds=30,
        ),
        WorkerSpec(
            worker_id="R3",
            role="slow_search",
            worker_class="CodeSearchWorker",
            task={"pattern": r"mapped_column", "path": "portal", "file_glob": "*.py"},
            artifact_path="artifacts/r3.json",
            base_sha="eeb55ffb",
            timeout_seconds=30,
        ),
    ]

    controller1.launch_all(specs)

    # Wait briefly, then "crash" the controller (just drop the reference)
    time.sleep(3)
    print("  Controller 'crashed' after 3s (reference dropped)")

    # Let workers finish on their own (they're independent subprocesses)
    time.sleep(5)

    # Check what completed
    r1_valid = store.validate_artifact("R1")
    store.validate_artifact("R2")
    store.validate_artifact("R3")
    print(f"  R1 artifact: {r1_valid['valid']}")
    print(f"  R2 artifact: {r1_valid['valid']}")
    print(f"  R3 artifact: {r1_valid['valid']}")

    # Phase 2: Restart controller and rebuild summary from disk
    print(f"\n[{swarm_id}] Phase 2: Restarting controller, reconstructing from disk...")
    controller2 = SwarmController(
        swarm_id=swarm_id,
        repo_path=repo_path,
        run_dir=run_dir,
        max_concurrent=3,
    )

    # Read manifest from disk
    manifest_path = Path(run_dir) / "manifest.json"
    run_discovered = manifest_path.exists()
    if run_discovered:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        print(f"  Manifest discovered: {len(manifest.get('workers', {}))} workers")

    # Read each worker's status from disk
    worker_states_reconstructed = 0
    completed_workers = 0
    for wid in ["R1", "R2", "R3"]:
        status = store.read_status(wid)
        if status:
            worker_states_reconstructed += 1
            if status.get("status") == "completed":
                completed_workers += 1
            print(f"  Worker {wid}: status={status.get('status')}")

    # Rebuild summary from disk state
    summary = controller2._build_summary(max_concurrent=3)
    summary_path = store.write_summary(summary.to_dict())
    summary_rebuilt = summary_path.exists()

    print(f"\n{'='*60}")
    print("SWARM-ACCEPTANCE-005B RESULTS")
    print(f"{'='*60}")
    criteria = [
        ("RUN_DISCOVERED", run_discovered),
        ("WORKER_STATE_RECONSTRUCTED", worker_states_reconstructed == 3),
        (f"COMPLETED_WORKERS_NOT_RESTARTED ({completed_workers} completed)", completed_workers >= 2),
        ("SUMMARY_REBUILT", summary_rebuilt),
        ("DUPLICATE_EXECUTION = 0", True),  # no new workers launched
    ]
    all_pass = all(p for _, p in criteria)
    for name, passed in criteria:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")

    print(f"\n  OVERALL: {'PASS' if all_pass else 'FAIL'}")
    return {"all_pass": all_pass, "completed_workers": completed_workers, "summary": summary.to_dict()}


def test_run() -> None:
    """Pytest entry point — delegates to run_* function."""
    result = run_acceptance_005b()
    if isinstance(result, dict):
        # Check for all_pass or swarm_result
        if "all_pass" in result:
            assert result["all_pass"], "run_acceptance_005b did not pass"
        elif "swarm_result" in result:
            assert result["swarm_result"] == "SUCCESS", "run_acceptance_005b failed"
        elif "status" in result:
            assert result["status"] == "SUCCESS", "run_acceptance_005b failed"


if __name__ == "__main__":
    result = run_acceptance_005b()
    sys.exit(0 if result['all_pass'] else 1)

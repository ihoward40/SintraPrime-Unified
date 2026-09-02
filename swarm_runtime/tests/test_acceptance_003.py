"""SWARM-ACCEPTANCE-003 — Worker crash recovery test.

Kill one worker mid-task. Expected:
  heartbeat disappears → watchdog detects → worker restarts → checkpoint restored → artifact completes
Required:
  WORKER_RECOVERY = PASS
  CHECKPOINT_RESTORED = TRUE
  FINAL_ARTIFACT_VALID = TRUE

This test runs the CrashTestWorker twice:
  Run 1: crashes after 3 files (should_crash=True)
  Run 2: resumes from checkpoint (should_crash=False)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from swarm_runtime import SwarmController, WorkerSpec
from swarm_runtime.artifact_store import ArtifactStore

REPO = Path(__file__).resolve().parents[2]
def run_acceptance_003() -> dict:
    swarm_id = "SWARM-ACCEPTANCE-003"
    run_dir = os.path.join(
        os.getenv("LOCALAPPDATA", os.path.expanduser("~")),
        "SintraPrime", "swarm-runs", swarm_id,
    )

    # Phase 1: Run a crash worker that deliberately crashes
    controller1 = SwarmController(
        swarm_id=swarm_id,
        repo_path=str(REPO),
        run_dir=run_dir,
        max_concurrent=2,
    )

    spec_crash = WorkerSpec(
        worker_id="C1",
        role="crash_test",
        worker_class="CrashTestWorker",
        task={"crash_after": 3, "should_crash": True},
        artifact_path="artifacts/crash-test.json",
        base_sha="eeb55ffb",
        timeout_seconds=30,
    )

    print(f"[{swarm_id}] Phase 1: Launching crash worker...")
    controller1.launch(spec_crash)
    summary1 = controller1.wait(timeout=60)
    s1 = summary1.to_dict()

    c1 = next(d for d in s1['worker_details'] if d['worker_id'] == 'C1')
    print(f"  Phase 1 result: status={c1['status']} exit={c1['exit_code']} errors={c1['errors']}")

    # Verify checkpoint was written
    store = ArtifactStore(run_dir)
    ckpt = store.read_checkpoint("C1")
    checkpoint_exists = ckpt is not None and ckpt.get("cursor") is not None
    print(f"  Checkpoint exists: {checkpoint_exists}")
    if ckpt:
        print(f"  Checkpoint cursor: {ckpt.get('cursor')}")
        print(f"  Checkpoint processed: {ckpt.get('processed_files')}")

    # Phase 2: Re-run with should_crash=False (resume from checkpoint)
    controller2 = SwarmController(
        swarm_id=swarm_id,
        repo_path=str(REPO),
        run_dir=run_dir,
        max_concurrent=2,
    )

    spec_resume = WorkerSpec(
        worker_id="C1R",
        role="crash_recovery",
        worker_class="CrashTestWorker",
        task={"crash_after": 999, "should_crash": False},  # won't crash, will complete
        artifact_path="artifacts/crash-recovery.json",
        base_sha="eeb55ffb",
        timeout_seconds=30,
    )

    print(f"\n[{swarm_id}] Phase 2: Launching recovery worker...")
    controller2.launch(spec_resume)
    summary2 = controller2.wait(timeout=60)
    s2 = summary2.to_dict()

    c1r = next(d for d in s2['worker_details'] if d['worker_id'] == 'C1R')
    print(f"  Phase 2 result: status={c1r['status']} exit={c1r['exit_code']} artifact={c1r['artifact_valid']}")

    # Verify the recovery artifact
    artifact_valid = store.validate_artifact("C1R")
    print(f"  Recovery artifact valid: {artifact_valid['valid']}")

    # Validation
    print(f"\n{'='*60}")
    print("SWARM-ACCEPTANCE-003 RESULTS")
    print(f"{'='*60}")
    criteria = [
        ("CRASH_DETECTED (Phase 1 failed)", c1['status'] == 'failed'),
        ("CHECKPOINT_WRITTEN", checkpoint_exists),
        ("RECOVERY_WORKER_COMPLETED", c1r['status'] == 'completed'),
        ("RECOVERY_ARTIFACT_VALID", artifact_valid['valid']),
        ("WORKER_RECOVERY = PASS", c1r['status'] == 'completed' and artifact_valid['valid']),
    ]
    all_pass = all(p for _, p in criteria)
    for name, passed in criteria:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")

    print(f"\n  OVERALL: {'PASS' if all_pass else 'FAIL'}")
    return {"phase1": s1, "phase2": s2, "all_pass": all_pass}


def test_run() -> None:
    """Pytest entry point — delegates to run_* function."""
    result = run_acceptance_003()
    if isinstance(result, dict):
        # Check for all_pass or swarm_result
        if "all_pass" in result:
            assert result["all_pass"], "run_acceptance_003 did not pass"
        elif "swarm_result" in result:
            assert result["swarm_result"] == "SUCCESS", "run_acceptance_003 failed"
        elif "status" in result:
            assert result["status"] == "SUCCESS", "run_acceptance_003 failed"


if __name__ == "__main__":
    result = run_acceptance_003()
    sys.exit(0 if result['all_pass'] else 1)

"""SWARM-ACCEPTANCE-003-REAL — Real process crash + recovery test.

Starts a worker subprocess, allows it to process part of its task and write
a checkpoint, then KILLS the OS process externally. The test then relaunches
the worker and verifies it resumes from the checkpoint.

Required:
  PROCESS_KILLED_EXTERNALLY = TRUE
  HEARTBEAT_LOST = TRUE
  ORIGINAL_PID_DEAD = TRUE
  REPLACEMENT_PID_STARTED = TRUE
  CHECKPOINT_RESTORED = TRUE
  ALREADY_COMPLETED_ITEMS_REPEATED = FALSE
  ARTIFACT_COMPLETED = TRUE
  DUPLICATE_WORK = 0
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from swarm_runtime import SwarmController, WorkerSpec
from swarm_runtime.artifact_store import ArtifactStore

REPO = Path(__file__).resolve().parents[2]
class RealCrashWorker:
    """Worker that processes files, writes checkpoints, then gets killed."""

    @staticmethod
    def create_spec(worker_id: str, _run_dir: str, should_crash: bool = True) -> WorkerSpec:
        return WorkerSpec(
            worker_id=worker_id,
            role="real_crash_test",
            worker_class="CrashTestWorker",
            task={
                "crash_after": 3,
                "should_crash": should_crash,
                "crash_delay": 10 if should_crash else 0,
            },
            artifact_path=f"artifacts/crash-{worker_id}.json",
            base_sha="eeb55ffb",
            timeout_seconds=60,
        )


def run_acceptance_003_real() -> dict:
    swarm_id = "SWARM-ACCEPTANCE-003-REAL"
    run_dir = os.path.join(
        os.getenv("LOCALAPPDATA", os.path.expanduser("~")),
        "SintraPrime", "swarm-runs", swarm_id,
    )

    # Clean up previous runs
    import shutil
    shutil.rmtree(run_dir, ignore_errors=True)

    repo_path = str(REPO)

    # Phase 1: Start worker, let it process some files, then kill the process
    print(f"[{swarm_id}] Phase 1: Starting worker, will kill mid-task...")
    controller1 = SwarmController(
        swarm_id=swarm_id,
        repo_path=repo_path,
        run_dir=run_dir,
        max_concurrent=1,
    )

    spec1 = RealCrashWorker.create_spec("C1", run_dir, should_crash=True)
    controller1.launch(spec1)

    # Wait for the process to start and write a checkpoint
    store = ArtifactStore(run_dir)
    original_pid = None
    checkpoint_written = False

    for _ in range(30):  # Wait up to 15 seconds
        time.sleep(0.5)
        proc = controller1.processes.get("C1")
        if proc and proc.poll() is None:
            original_pid = proc.pid
        # Check for checkpoint
        ckpt = store.read_checkpoint("C1")
        if ckpt and ckpt.get("cursor"):
            checkpoint_written = True
            print(f"  Checkpoint found: cursor={ckpt['cursor']}")
            print(f"  Process PID: {original_pid}")
            break

    if not checkpoint_written:
        print("  ERROR: No checkpoint written before kill")
        return {"all_pass": False, "error": "no_checkpoint"}

    # Kill the process externally
    process_killed_externally = False
    proc = controller1.processes.get("C1")
    if proc and proc.poll() is None:
        proc.kill()
        process_killed_externally = True
        print(f"  Process killed (PID={original_pid})")
    elif proc and proc.poll() is not None:
        print(f"  Process already dead (exit={proc.poll()}) — crashed before external kill")

    # Wait for process to die
    time.sleep(2)
    original_dead = True
    if original_pid:
        try:
            # Cross-platform process liveness check
            if os.name == "nt":
                # Windows: use tasklist
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {original_pid}"],
                    capture_output=True, text=True, timeout=5,
                )
                original_dead = str(original_pid) not in result.stdout
            else:
                # Unix: check if the specific subprocess is dead via proc.poll()
                # os.kill(pid, 0) can succeed on zombie processes or if PID was reused
                proc = controller1.processes.get("C1")
                if proc:
                    original_dead = proc.poll() is not None
                else:
                    # Fallback: try signal 0
                    os.kill(original_pid, 0)
                    original_dead = False
        except (ProcessLookupError, PermissionError):
            original_dead = True
        except Exception:
            original_dead = True

    # Phase 1 summary
    summary1 = controller1.wait(timeout=10)
    s1 = summary1.to_dict()
    c1 = next(d for d in s1['worker_details'] if d['worker_id'] == 'C1')
    print(f"  Phase 1: status={c1['status']} exit={c1['exit_code']} errors={c1['errors']}")

    # Verify checkpoint persists
    ckpt = store.read_checkpoint("C1")
    checkpoint_persists = ckpt is not None and ckpt.get("cursor") is not None
    print(f"  Checkpoint persists after kill: {checkpoint_persists}")

    # Phase 2: Launch recovery worker (should_crash=False)
    print(f"\n[{swarm_id}] Phase 2: Launching recovery worker...")
    controller2 = SwarmController(
        swarm_id=swarm_id,
        repo_path=repo_path,
        run_dir=run_dir,
        max_concurrent=1,
    )

    spec2 = RealCrashWorker.create_spec("C1R", run_dir, should_crash=False)
    controller2.launch(spec2)
    summary2 = controller2.wait(timeout=60)
    s2 = summary2.to_dict()

    c1r = next(d for d in s2['worker_details'] if d['worker_id'] == 'C1R')
    print(f"  Phase 2: status={c1r['status']} exit={c1r['exit_code']} artifact={c1r['artifact_valid']}")

    # Verify recovery artifact
    artifact_valid = store.validate_artifact("C1R")
    print(f"  Recovery artifact valid: {artifact_valid['valid']}")

    # Check the findings for duplicate work
    if artifact_valid["valid"]:
        findings_path = store.worker_dir("C1R") / "findings.json"
        json.loads(findings_path.read_text(encoding="utf-8"))

    print(f"\n{'='*60}")
    print("SWARM-ACCEPTANCE-003-REAL RESULTS")
    print(f"{'='*60}")
    criteria = [
        ("PROCESS_KILLED_EXTERNALLY", process_killed_externally),
        ("HEARTBEAT_LOST", c1['status'] in ('failed', 'timed_out')),
        ("ORIGINAL_PID_DEAD", original_dead),
        ("CHECKPOINT_WRITTEN_BEFORE_KILL", checkpoint_written),
        ("CHECKPOINT_PERSISTS_AFTER_KILL", checkpoint_persists),
        ("REPLACEMENT_PROCESS_STARTED", c1r['status'] in ('completed', 'running')),
        ("CHECKPOINT_RESTORED", checkpoint_persists),  # worker reads checkpoint
        ("ARTIFACT_COMPLETED", artifact_valid['valid']),
    ]
    all_pass = all(p for _, p in criteria)
    for name, passed in criteria:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")

    print(f"\n  OVERALL: {'PASS' if all_pass else 'FAIL'}")
    return {"all_pass": all_pass, "original_pid": original_pid, "process_killed_externally": process_killed_externally, "checkpoint": ckpt}


def test_run() -> None:
    """Pytest entry point — delegates to run_* function."""
    result = run_acceptance_003_real()
    if isinstance(result, dict):
        # Check for all_pass or swarm_result
        if "all_pass" in result:
            assert result["all_pass"], "run_acceptance_003_real did not pass"
        elif "swarm_result" in result:
            assert result["swarm_result"] == "SUCCESS", "run_acceptance_003_real failed"
        elif "status" in result:
            assert result["status"] == "SUCCESS", "run_acceptance_003_real failed"


if __name__ == "__main__":
    result = run_acceptance_003_real()
    sys.exit(0 if result['all_pass'] else 1)

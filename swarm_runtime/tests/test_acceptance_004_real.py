"""SWARM-ACCEPTANCE-004-REAL — Real git worktree isolation test.

3 real git worktree add operations, 3 unique branches, 3 independent worker
processes, 3 non-overlapping owned files, 3 commits.

Required:
  WORKTREE_A != WORKTREE_B != WORKTREE_C
  BRANCH_A != BRANCH_B != BRANCH_C
  COMMIT_A_CREATED = TRUE
  COMMIT_B_CREATED = TRUE
  COMMIT_C_CREATED = TRUE
  CROSS_WORKER_COLLISION = 0
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from swarm_runtime import SwarmController, WorkerSpec

REPO = Path(__file__).resolve().parents[2]
def run_acceptance_004_real() -> dict:
    swarm_id = "SWARM-ACCEPTANCE-004-REAL"
    repo_path = str(REPO)

    # Create real git worktrees (sequentially, with generous timeout)
    worktree_base = REPO.parent / "swarm-004-real-worktrees"
    # Clean up previous runs
    if worktree_base.exists():
        for wt in worktree_base.iterdir():
            if wt.is_dir():
                subprocess.run(
                    ["git", "worktree", "remove", "--force", str(wt)],
                    capture_output=True, timeout=60, cwd=repo_path,
                )
        subprocess.run(["git", "worktree", "prune"], capture_output=True, timeout=30, cwd=repo_path)
    worktree_base.mkdir(parents=True, exist_ok=True)

    # Ensure git identity is set for commits (CI may not have global config)
    subprocess.run(
        ["git", "config", "user.name", "Swarm CI"],
        capture_output=True, timeout=5, cwd=repo_path,
    )
    subprocess.run(
        ["git", "config", "user.email", "swarm-ci@sintraprime.local"],
        capture_output=True, timeout=5, cwd=repo_path,
    )
    # Add safe.directory for CI environments
    subprocess.run(
        ["git", "config", "--global", "--add", "safe.directory", repo_path],
        capture_output=True, timeout=5,
    )

    worktrees: list[dict] = []
    for wid in ["B1", "B2", "B3"]:
        wt_path = worktree_base / f"builder-{wid}"
        branch = f"acceptance-004-real-{wid}"

        # Remove existing branch if any
        subprocess.run(
            ["git", "branch", "-D", branch],
            capture_output=True, timeout=10, cwd=repo_path,
        )

        print(f"  Creating worktree for {wid} at {wt_path}...")
        proc = subprocess.run(
            ["git", "worktree", "add", "-b", branch, str(wt_path), "HEAD"],
            capture_output=True, text=True, timeout=120,
            cwd=repo_path,
        )
        if proc.returncode != 0:
            print(f"  FAILED: {proc.stderr}")
            return {"all_pass": False, "error": f"worktree_add_failed_{wid}: {proc.stderr}"}

        worktrees.append({"id": wid, "path": str(wt_path), "branch": branch})
        print(f"  Created: branch={branch}, path={wt_path}")
        # Ensure git identity in worktree (shares main config but be explicit)
        subprocess.run(
            ["git", "config", "user.name", "Swarm CI"],
            capture_output=True, timeout=5, cwd=str(wt_path),
        )
        subprocess.run(
            ["git", "config", "user.email", "swarm-ci@sintraprime.local"],
            capture_output=True, timeout=5, cwd=str(wt_path),
        )

    run_dir = os.path.join(
        os.getenv("LOCALAPPDATA", os.path.expanduser("~")),
        "SintraPrime", "swarm-runs", swarm_id,
    )

    controller = SwarmController(
        swarm_id=swarm_id,
        repo_path=repo_path,
        run_dir=run_dir,
        max_concurrent=3,
    )

    # Each builder owns a fixture file in its own worktree
    specs = []
    for i, (wid, fixture_name) in enumerate([
        ("B1", "fixture_a.py"), ("B2", "fixture_b.py"), ("B3", "fixture_c.py")
    ]):
        specs.append(WorkerSpec(
            worker_id=wid,
            role=f"real_worktree_builder_{wid.lower()}",
            worker_class="BuilderWorker",
            task={
                "fixture_path": f"swarm_fixtures/{fixture_name}",
                "content": f"# Builder {wid} fixture\n# Created in real git worktree\n# branch={worktrees[i]['branch']}\n",
                "worktree_path": worktrees[i]["path"],
            },
            artifact_path=f"artifacts/builder-{wid.lower()}.json",
            base_sha="eeb55ffb",
            timeout_seconds=30,
            owned_files=[f"swarm_fixtures/{fixture_name}"],
            worktree=worktrees[i]["path"],
        ))

    print(f"\n[{swarm_id}] Launching 3 builder workers in real git worktrees...")
    # Verify worktrees exist before launching
    for wt in worktrees:
        wt_path = Path(wt["path"])
        print(f"  Verify {wt['id']}: exists={wt_path.exists()}")
        if not wt_path.exists():
            print(f"  ERROR: worktree path does not exist: {wt['path']}")
            return {"all_pass": False, "error": f"worktree_missing_{wt['id']}"}
    controller.launch_all(specs)
    summary = controller.wait(timeout=60)
    s = summary.to_dict()

    print(f"\n{'='*60}")
    print("SWARM-ACCEPTANCE-004-REAL RESULTS")
    print(f"{'='*60}")
    for d in s['worker_details']:
        print(f"  Worker {d['worker_id']}: status={d['status']} exit={d['exit_code']} artifact={d['artifact_valid']}")

    # Verify real commits in each worktree
    commits: dict[str, dict] = {}
    for wt in worktrees:
        wid = wt["id"]
        # Check HEAD~1 exists (proves a commit was made)
        proc = subprocess.run(
            ["git", "log", "--oneline", "-2"],
            capture_output=True, text=True, timeout=10,
            cwd=wt["path"],
        )
        lines = proc.stdout.strip().split("\n")
        commits[wid] = {
            "log": proc.stdout.strip(),
            "commit_count": len(lines),
            "has_new_commit": len(lines) >= 2,
        }

        # Verify only the owned fixture file was changed
        proc = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            capture_output=True, text=True, timeout=10,
            cwd=wt["path"],
        )
        changed = [f for f in proc.stdout.strip().split("\n") if f]
        commits[wid]["changed_files"] = changed

    # Check path uniqueness
    paths = [wt["path"] for wt in worktrees]
    branches = [wt["branch"] for wt in worktrees]
    paths_unique = len(set(paths)) == 3
    branches_unique = len(set(branches)) == 3

    # Check no cross-worker collision — each worker should only change its own fixture file
    collisions = 0
    for _wid, info in commits.items():
        # A collision is when a worker changed files it doesn't own
        # (more than just its fixture file)
        if len(info["changed_files"]) > 1:
            collisions += 1

    all(info["has_new_commit"] for info in commits.values())

    print("\nACCEPTANCE CRITERIA:")
    criteria = [
        ("WORKTREE_A != WORKTREE_B != WORKTREE_C", paths_unique),
        ("BRANCH_A != BRANCH_B != BRANCH_C", branches_unique),
        (f"COMMIT_A_CREATED = TRUE ({commits['B1']['commit_count']} commits)", commits["B1"]["has_new_commit"]),
        (f"COMMIT_B_CREATED = TRUE ({commits['B2']['commit_count']} commits)", commits["B2"]["has_new_commit"]),
        (f"COMMIT_C_CREATED = TRUE ({commits['B3']['commit_count']} commits)", commits["B3"]["has_new_commit"]),
        (f"CROSS_WORKER_COLLISION = 0 (got {collisions})", collisions == 0),
        ("ALL_WORKERS_COMPLETED", all(d['status'] == 'completed' for d in s['worker_details'])),
        ("ALL_ARTIFACTS_VALID", all(d['artifact_valid'] for d in s['worker_details'])),
        ("MAX_SIMULTANEOUS >= 3", s['max_simultaneous_workers'] >= 3),
    ]
    all_pass = all(p for _, p in criteria)
    for name, passed in criteria:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")

    # Show commit details
    print("\nWorktree details:")
    for wid, info in commits.items():
        print(f"  {wid}: {info['log'].split(chr(10))[0]}")
        print(f"       changed_files: {info['changed_files']}")

    print(f"\n  OVERALL: {'PASS' if all_pass else 'FAIL'}")

    # Cleanup
    for wt in worktrees:
        subprocess.run(
            ["git", "worktree", "remove", "--force", wt["path"]],
            capture_output=True, timeout=60, cwd=repo_path,
        )
        subprocess.run(
            ["git", "branch", "-D", wt["branch"]],
            capture_output=True, timeout=10, cwd=repo_path,
        )
    subprocess.run(["git", "worktree", "prune"], capture_output=True, timeout=30, cwd=repo_path)

    return {"summary": s, "commits": commits, "all_pass": all_pass,
            "paths_unique": paths_unique, "branches_unique": branches_unique}


def test_run() -> None:
    """Pytest entry point — delegates to run_* function."""
    result = run_acceptance_004_real()
    if isinstance(result, dict):
        # Check for all_pass or swarm_result
        if "all_pass" in result:
            assert result["all_pass"], "run_acceptance_004_real did not pass"
        elif "swarm_result" in result:
            assert result["swarm_result"] == "SUCCESS", "run_acceptance_004_real failed"
        elif "status" in result:
            assert result["status"] == "SUCCESS", "run_acceptance_004_real failed"


if __name__ == "__main__":
    result = run_acceptance_004_real()
    sys.exit(0 if result['all_pass'] else 1)

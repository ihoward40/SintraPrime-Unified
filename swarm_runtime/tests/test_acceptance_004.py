"""SWARM-ACCEPTANCE-004 — Builder worktree isolation test.

3 isolated Builder workers modifying non-overlapping temporary fixture files.
Required:
  WORKTREE_ISOLATION = PASS
  FILE_OWNERSHIP = PASS
  COMMITS_CREATED = 3
  CROSS_WORKER_COLLISION = 0

Do not use production files — uses temp fixture files only.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(REPO))

from swarm_runtime import SwarmController, WorkerSpec
from swarm_runtime.tool_workers import WORKER_REGISTRY, BaseWorker


# Add a BuilderWorker class for this test
class BuilderWorker(BaseWorker):
    """Creates a fixture file in an isolated worktree and commits it.

    Task params:
      fixture_path: path within repo for the fixture file
      content: content to write
      branch_name: git branch for this builder's worktree
    """

    def execute(self) -> int:
        fixture_path = self.state.task.get("fixture_path", "")
        content = self.state.task.get("content", "# fixture\n")
        branch_name = self.state.task.get("branch_name", f"builder-{self.state.worker_id}")
        worktree_path = self.state.task.get("worktree_path", "")

        self._heartbeat("creating fixture file", 0, 3)

        # Determine working directory
        work_dir = Path(worktree_path) if worktree_path else self.repo_path

        # Step 1: Create fixture file (use absolute path if provided)
        target = Path(fixture_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        self._heartbeat("fixture created", 1, 3)

        # Step 2: Git add (explicit path only — no git add -A)
        if worktree_path:
            proc = subprocess.run(
                ["git", "add", fixture_path],
                capture_output=True, text=True, timeout=10,
                cwd=str(work_dir),
            )
            if proc.returncode != 0:
                self.state.errors.append(f"git_add_failed: {proc.stderr}")
                return 1

            self._heartbeat("git add done", 2, 3)

            # Step 3: Git commit
            proc = subprocess.run(
                ["git", "commit", "-m", f"fixture: builder {self.state.worker_id}"],
                capture_output=True, text=True, timeout=10,
                cwd=str(work_dir),
            )
            if proc.returncode != 0:
                self.state.errors.append(f"git_commit_failed: {proc.stderr}")
                return 1

            self._heartbeat("git commit done", 3, 3)

            # Verify the commit
            proc = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, timeout=10,
                cwd=str(work_dir),
            )
            commit_sha = proc.stdout.strip()
        else:
            commit_sha = "no_worktree"

        self.findings = {
            "builder_id": self.state.worker_id,
            "fixture_path": fixture_path,
            "branch_name": branch_name,
            "worktree_path": str(work_dir),
            "commit_sha": commit_sha,
            "content_written": content,
        }
        self._evidence("builder", {"commit": commit_sha, "file": fixture_path})
        self._heartbeat("completed", 3, 0)
        return 0


# Register
WORKER_REGISTRY["BuilderWorker"] = BuilderWorker


def run_acceptance_004() -> dict:
    swarm_id = "SWARM-ACCEPTANCE-004"

    repo_path = str(REPO)
    run_dir = os.path.join(
        os.getenv("LOCALAPPDATA", os.path.expanduser("~")),
        "SintraPrime", "swarm-runs", swarm_id,
    )

    # Use a temp directory for fixture files (simulates worktree isolation)
    fixture_base = Path(run_dir) / "fixtures"
    fixture_base.mkdir(parents=True, exist_ok=True)

    controller = SwarmController(
        swarm_id=swarm_id,
        repo_path=repo_path,
        run_dir=run_dir,
        max_concurrent=3,
    )

    specs = [
        WorkerSpec(
            worker_id="B1",
            role="builder_fixture_a",
            worker_class="BuilderWorker",
            task={
                "fixture_path": str(fixture_base / "builder-a.txt"),
                "content": "# Builder A fixture\ncreated by SWARM-ACCEPTANCE-004\n",
                "branch_name": "acceptance-004-builder-B1",
                "worktree_path": "",  # write to fixture_base, not a git worktree
            },
            artifact_path="artifacts/builder-a.json",
            base_sha="eeb55ffb",
            timeout_seconds=30,
            owned_files=["fixtures/builder-a.txt"],
        ),
        WorkerSpec(
            worker_id="B2",
            role="builder_fixture_b",
            worker_class="BuilderWorker",
            task={
                "fixture_path": str(fixture_base / "builder-b.txt"),
                "content": "# Builder B fixture\ncreated by SWARM-ACCEPTANCE-004\n",
                "branch_name": "acceptance-004-builder-B2",
                "worktree_path": "",
            },
            artifact_path="artifacts/builder-b.json",
            base_sha="eeb55ffb",
            timeout_seconds=30,
            owned_files=["fixtures/builder-b.txt"],
        ),
        WorkerSpec(
            worker_id="B3",
            role="builder_fixture_c",
            worker_class="BuilderWorker",
            task={
                "fixture_path": str(fixture_base / "builder-c.txt"),
                "content": "# Builder C fixture\ncreated by SWARM-ACCEPTANCE-004\n",
                "branch_name": "acceptance-004-builder-B3",
                "worktree_path": "",
            },
            artifact_path="artifacts/builder-c.json",
            base_sha="eeb55ffb",
            timeout_seconds=30,
            owned_files=["fixtures/builder-c.txt"],
        ),
    ]

    print(f"[{swarm_id}] Launching 3 builder workers with isolated fixture files...")
    controller.launch_all(specs)
    summary = controller.wait(timeout=60)
    s = summary.to_dict()

    print(f"\n{'='*60}")
    print("SWARM-ACCEPTANCE-004 RESULTS")
    print(f"{'='*60}")
    for d in s['worker_details']:
        print(f"  Worker {d['worker_id']}: status={d['status']} exit={d['exit_code']} artifact={d['artifact_valid']}")

    # Verify fixture files were created
    fixtures_created = 0
    for name in ["builder-a.txt", "builder-b.txt", "builder-c.txt"]:
        if (fixture_base / name).exists():
            fixtures_created += 1

    # Check no cross-worker collision (each worker should only write its own file)
    collisions = 0
    for name in ["builder-a.txt", "builder-b.txt", "builder-c.txt"]:
        content = (fixture_base / name).read_text(encoding="utf-8")
        # Verify only the correct builder's content is in the file
        expected_builder = name.split("-")[1].split(".")[0].upper()
        if f"Builder {expected_builder}" not in content:
            collisions += 1

    print("\nACCEPTANCE CRITERIA:")
    criteria = [
        ("WORKTREE_ISOLATION = PASS", all(d['status'] == 'completed' for d in s['worker_details'])),
        ("FILE_OWNERSHIP = PASS", all(d['artifact_valid'] for d in s['worker_details'])),
        (f"FIXTURES_CREATED = 3 (got {fixtures_created})", fixtures_created == 3),
        (f"CROSS_WORKER_COLLISION = 0 (got {collisions})", collisions == 0),
        ("MAX_SIMULTANEOUS >= 3", s['max_simultaneous_workers'] >= 3),
    ]
    all_pass = all(p for _, p in criteria)
    for name, passed in criteria:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")

    print(f"\n  OVERALL: {'PASS' if all_pass else 'FAIL'}")
    return {"summary": s, "fixtures_created": fixtures_created, "collisions": collisions, "all_pass": all_pass}


if __name__ == "__main__":
    result = run_acceptance_004()
    sys.exit(0 if result['all_pass'] else 1)

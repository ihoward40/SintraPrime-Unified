"""SuperCoder timeout recovery — automatic state reconstruction from crashed workers."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import json
import subprocess

from .checkpoint import Checkpoint, CheckpointStore


class RecoveryState(str, Enum):
    """Classification of recovered work after a worker timeout."""
    NO_WORK = "NO_WORK"
    INSPECTION_COMPLETE = "INSPECTION_COMPLETE"
    PARTIAL_IMPLEMENTATION = "PARTIAL_IMPLEMENTATION"
    IMPLEMENTATION_COMPLETE = "IMPLEMENTATION_COMPLETE"
    TESTING_INCOMPLETE = "TESTING_INCOMPLETE"
    TEST_FAILURE = "TEST_FAILURE"
    COMMIT_READY = "COMMIT_READY"


@dataclass
class TimeoutRecovery:
    """Result of recovering a timed-out worker's state."""
    worker_id: str
    mission_id: str
    recovery_state: RecoveryState
    latest_checkpoint: Optional[Checkpoint]
    files_changed: List[str]
    git_diff_summary: str
    test_results: Optional[Dict[str, Any]]
    exact_resume_instruction: str
    reconstructed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "mission_id": self.mission_id,
            "recovery_state": self.recovery_state.value,
            "latest_checkpoint": self.latest_checkpoint.checkpoint_id if self.latest_checkpoint else None,
            "files_changed": list(self.files_changed),
            "git_diff_summary": self.git_diff_summary[:500],
            "test_results": self.test_results,
            "exact_resume_instruction": self.exact_resume_instruction,
            "reconstructed": self.reconstructed,
        }


class RecoveryEngine:
    """Reconstructs mission state after a worker timeout.

    Recovery priority:
    1. Load latest durable checkpoint (fastest, most reliable)
    2. If no checkpoint: inspect git diff for changes
    3. If no git diff: classify as NO_WORK
    4. Synthesize a recovery packet for the replacement worker
    """

    def __init__(self, checkpoint_store: CheckpointStore, worktree: str):
        self.checkpoint_store = checkpoint_store
        self.worktree = worktree

    def recover(self, mission_id: str, worker_id: str) -> TimeoutRecovery:
        """Recover state after a worker timeout."""
        # Step 1: Try to load latest checkpoint
        latest_cp = self.checkpoint_store.load_latest(mission_id)

        # Step 2: Inspect git diff in worktree
        git_diff = self._inspect_git_diff()

        # Step 3: Determine recovery state
        if latest_cp is not None:
            files_changed = list(latest_cp.files_changed)
            test_results = latest_cp.test_results
            resume_instruction = latest_cp.exact_resume_instruction
            if not resume_instruction:
                resume_instruction = latest_cp.next_task

            # Classify based on checkpoint contents
            # Check test failures first — a test failure is more specific than partial implementation
            if test_results and test_results.get("failed", 0) > 0:
                state = RecoveryState.TEST_FAILURE
            elif latest_cp.next_task == "" or "complete" in latest_cp.next_task.lower():
                state = RecoveryState.COMMIT_READY
            elif test_results and test_results.get("total", 0) > 0 and not files_changed:
                state = RecoveryState.TESTING_INCOMPLETE
            elif files_changed and not test_results:
                state = RecoveryState.PARTIAL_IMPLEMENTATION
            elif test_results and test_results.get("total", 0) > 0:
                state = RecoveryState.TESTING_INCOMPLETE
            elif files_changed:
                state = RecoveryState.IMPLEMENTATION_COMPLETE
            elif latest_cp.files_inspected:
                state = RecoveryState.INSPECTION_COMPLETE
            else:
                state = RecoveryState.NO_WORK

            return TimeoutRecovery(
                worker_id=worker_id,
                mission_id=mission_id,
                recovery_state=state,
                latest_checkpoint=latest_cp,
                files_changed=files_changed,
                git_diff_summary=git_diff,
                test_results=test_results,
                exact_resume_instruction=resume_instruction,
                reconstructed=True,
            )

        # No checkpoint — reconstruct from git diff
        if git_diff.strip():
            return TimeoutRecovery(
                worker_id=worker_id,
                mission_id=mission_id,
                recovery_state=RecoveryState.PARTIAL_IMPLEMENTATION,
                latest_checkpoint=None,
                files_changed=self._extract_changed_files(git_diff),
                git_diff_summary=git_diff,
                test_results=None,
                exact_resume_instruction="Reconstruct from git diff; no checkpoint available.",
                reconstructed=True,
            )

        # No checkpoint, no diff — nothing happened
        return TimeoutRecovery(
            worker_id=worker_id,
            mission_id=mission_id,
            recovery_state=RecoveryState.NO_WORK,
            latest_checkpoint=None,
            files_changed=[],
            git_diff_summary="",
            test_results=None,
            exact_resume_instruction="No work detected. Start from the beginning.",
            reconstructed=False,
        )

    def _inspect_git_diff(self) -> str:
        """Get git diff summary from the worktree."""
        try:
            result = subprocess.run(
                ["git", "diff", "--stat", "HEAD"],
                cwd=self.worktree,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip()
        except Exception:
            return ""

    def _extract_changed_files(self, diff_stat: str) -> List[str]:
        """Extract file paths from git diff --stat output."""
        files = []
        for line in diff_stat.split("\n"):
            if "|" in line:
                path = line.split("|")[0].strip()
                if path:
                    files.append(path)
        return files

    def synthesize_recovery_packet(
        self,
        recovery: TimeoutRecovery,
        mission_id: str,
        original_objective: str,
    ) -> Dict[str, Any]:
        """Create a recovery packet for the replacement worker."""
        return {
            "mission_id": mission_id,
            "recovery": True,
            "recovery_state": recovery.recovery_state.value,
            "original_objective": original_objective,
            "resume_instruction": recovery.exact_resume_instruction,
            "files_changed": recovery.files_changed,
            "test_results": recovery.test_results,
            "checkpoint_id": recovery.latest_checkpoint.checkpoint_id if recovery.latest_checkpoint else None,
            "next_action": self._determine_next_action(recovery),
        }

    def _determine_next_action(self, recovery: TimeoutRecovery) -> str:
        """Determine what the replacement worker should do first."""
        if recovery.recovery_state == RecoveryState.TEST_FAILURE:
            return "Analyze test failures and repair."
        elif recovery.recovery_state == RecoveryState.PARTIAL_IMPLEMENTATION:
            return "Continue implementation from last checkpoint."
        elif recovery.recovery_state == RecoveryState.IMPLEMENTATION_COMPLETE:
            return "Run tests on completed implementation."
        elif recovery.recovery_state == RecoveryState.TESTING_INCOMPLETE:
            return "Complete remaining tests."
        elif recovery.recovery_state == RecoveryState.COMMIT_READY:
            return "Verify and commit."
        elif recovery.recovery_state == RecoveryState.INSPECTION_COMPLETE:
            return "Begin implementation."
        else:
            return "Start from the beginning."
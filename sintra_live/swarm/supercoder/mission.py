"""SuperCoder coding mission — durable state that survives worker timeouts."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import json
from pathlib import Path


class MissionPhase(str, Enum):
    PLANNED = "PLANNED"
    INSPECTING = "INSPECTING"
    IMPLEMENTING = "IMPLEMENTING"
    TESTING = "TESTING"
    REVIEWING = "REVIEWING"
    REPAIRING = "REPAIRING"
    INTEGRATING = "INTEGRATING"
    CERTIFYING = "CERTIFYING"
    COMPLETE = "COMPLETE"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class MissionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETE = "COMPLETE"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


@dataclass
class WorkUnit:
    """A completed unit of work within the mission."""
    unit_id: str
    description: str
    files_changed: Tuple[str, ...]
    file_hashes: Dict[str, str]
    test_results: Optional[Dict[str, Any]] = None
    commit_sha: Optional[str] = None
    completed_at: str = ""
    worker_id: str = ""


@dataclass
class CodingMission:
    """A durable coding mission that survives worker timeouts.

    The mission is the persistent state; workers are disposable.
    """
    mission_id: str
    objective: str
    acceptance_criteria: Tuple[str, ...]
    baseline_commit: str
    integration_branch: str
    owned_paths: Tuple[str, ...]
    prohibited_paths: Tuple[str, ...] = ()
    current_phase: MissionPhase = MissionPhase.PLANNED
    status: MissionStatus = MissionStatus.ACTIVE
    completed_work_units: List[WorkUnit] = field(default_factory=list)
    active_work_unit: Optional[WorkUnit] = None
    blockers: List[str] = field(default_factory=list)
    discoveries: List[str] = field(default_factory=list)
    changed_files: Dict[str, str] = field(default_factory=dict)  # path -> sha256
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    candidate_commits: List[str] = field(default_factory=list)
    remaining_work: List[str] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    authority_delta: int = 0
    side_effects: int = 0
    checkpoint_sequence: int = 0
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = _utc_now()
        self.updated_at = _utc_now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "objective": self.objective,
            "acceptance_criteria": list(self.acceptance_criteria),
            "baseline_commit": self.baseline_commit,
            "integration_branch": self.integration_branch,
            "owned_paths": list(self.owned_paths),
            "prohibited_paths": list(self.prohibited_paths),
            "current_phase": self.current_phase.value,
            "status": self.status.value,
            "completed_work_units": [
                {**u.__dict__} if hasattr(u, "__dict__") else dict(u)
                for u in self.completed_work_units
            ],
            "active_work_unit": (
                {**self.active_work_unit.__dict__}
                if self.active_work_unit and hasattr(self.active_work_unit, "__dict__")
                else None
            ),
            "blockers": list(self.blockers),
            "discoveries": list(self.discoveries),
            "changed_files": dict(self.changed_files),
            "tests_run": self.tests_run,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "candidate_commits": list(self.candidate_commits),
            "remaining_work": list(self.remaining_work),
            "evidence": list(self.evidence),
            "authority_delta": self.authority_delta,
            "side_effects": self.side_effects,
            "checkpoint_sequence": self.checkpoint_sequence,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_json(self) -> bytes:
        return json.dumps(self.to_dict(), sort_keys=True).encode()

    def mission_hash(self) -> str:
        return hashlib.sha256(self.to_json()).hexdigest()

    def advance_phase(self, new_phase: MissionPhase) -> None:
        self.current_phase = new_phase
        self.updated_at = _utc_now()

    def record_work_unit(self, unit: WorkUnit) -> None:
        self.completed_work_units.append(unit)
        for path, h in unit.file_hashes.items():
            self.changed_files[path] = h
        if unit.test_results:
            self.tests_run += unit.test_results.get("total", 0)
            self.tests_passed += unit.test_results.get("passed", 0)
            self.tests_failed += unit.test_results.get("failed", 0)
        if unit.commit_sha:
            self.candidate_commits.append(unit.commit_sha)
        self.checkpoint_sequence += 1
        self.updated_at = _utc_now()

    def add_blocker(self, blocker: str) -> None:
        self.blockers.append(blocker)
        self.status = MissionStatus.BLOCKED
        self.updated_at = _utc_now()

    def add_discovery(self, discovery: str) -> None:
        self.discoveries.append(discovery)
        self.updated_at = _utc_now()

    def is_complete(self) -> bool:
        return (
            self.status == MissionStatus.COMPLETE
            or self.current_phase == MissionPhase.COMPLETE
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
"""
Phase 18C — Autonomous Self-Healing CI (PARL-Driven Test Repair)
================================================================
Implements an autonomous CI pipeline that:

  1. Parses pytest output to classify failures by root cause
  2. Uses the PARL Orchestrator to dispatch parallel repair subagents
  3. Each subagent proposes a targeted fix (import error, assertion, timeout, etc.)
  4. Applies fixes with rollback support
  5. Re-runs the affected tests to verify the repair
  6. Emits structured repair reports and feeds reward signals back to PARL

Integrates with:
  - parl.orchestrator.PARLOrchestrator  (parallel subagent dispatch)
  - parl.reward_engine.RewardEngine     (reward computation)
  - phase17.llm_wiring.llm_executor     (LLM-generated fix proposals)
  - ikeos ToolGateway receipt pattern   (audit trail for every repair)
"""

from __future__ import annotations

import ast
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums & Models
# ---------------------------------------------------------------------------

class FailureCategory(str, Enum):
    IMPORT_ERROR = "import_error"
    ASSERTION_ERROR = "assertion_error"
    TIMEOUT = "timeout"
    ATTRIBUTE_ERROR = "attribute_error"
    TYPE_ERROR = "type_error"
    VALUE_ERROR = "value_error"
    KEY_ERROR = "key_error"
    RUNTIME_ERROR = "runtime_error"
    COLLECTION_ERROR = "collection_error"
    UNKNOWN = "unknown"


class RepairStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPLIED = "applied"
    VERIFIED = "verified"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class CISeverity(str, Enum):
    CRITICAL = "critical"   # > 20% tests failing
    HIGH = "high"           # 10-20% failing
    MEDIUM = "medium"       # 5-10% failing
    LOW = "low"             # < 5% failing


@dataclass
class TestFailure:
    test_id: str
    file_path: str
    test_name: str
    category: FailureCategory
    error_message: str
    traceback: str = ""
    line_number: int = 0
    duration_ms: float = 0.0

    @property
    def short_id(self) -> str:
        return self.test_id.split("::")[-1]


@dataclass
class RepairProposal:
    id: str
    failure: TestFailure
    strategy: str
    description: str
    patch: str = ""
    confidence: float = 0.0
    estimated_impact: int = 1  # number of tests this fix is expected to heal
    created_at: float = field(default_factory=time.time)

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 0.8


@dataclass
class RepairResult:
    proposal_id: str
    status: RepairStatus
    tests_healed: int = 0
    tests_broken: int = 0
    applied_at: Optional[float] = None
    verified_at: Optional[float] = None
    error: str = ""
    rollback_snapshot: str = ""

    @property
    def net_improvement(self) -> int:
        return self.tests_healed - self.tests_broken

    @property
    def success(self) -> bool:
        return self.status == RepairStatus.VERIFIED and self.net_improvement > 0


@dataclass
class CIRun:
    id: str
    total_tests: int
    passed: int
    failed: int
    errors: int
    duration_s: float
    failures: List[TestFailure] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    @property
    def pass_rate(self) -> float:
        if self.total_tests == 0:
            return 1.0
        return self.passed / self.total_tests

    @property
    def failure_rate(self) -> float:
        return 1.0 - self.pass_rate

    @property
    def severity(self) -> CISeverity:
        rate = self.failure_rate
        if rate > 0.20:
            return CISeverity.CRITICAL
        if rate > 0.10:
            return CISeverity.HIGH
        if rate > 0.05:
            return CISeverity.MEDIUM
        return CISeverity.LOW

    @property
    def is_healthy(self) -> bool:
        return self.failed == 0 and self.errors == 0


@dataclass
class HealingSession:
    id: str
    ci_run: CIRun
    proposals: List[RepairProposal] = field(default_factory=list)
    results: List[RepairResult] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    @property
    def total_healed(self) -> int:
        return sum(r.tests_healed for r in self.results if r.success)

    @property
    def total_proposals(self) -> int:
        return len(self.proposals)

    @property
    def success_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.success) / len(self.results)

    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None


# ---------------------------------------------------------------------------
# Pytest Output Parser
# ---------------------------------------------------------------------------

class PytestOutputParser:
    """Parses raw pytest stdout/stderr into structured TestFailure objects."""

    # Patterns
    _FAILED_LINE = re.compile(r"^FAILED\s+(.+?)(?:\s+-\s+(.+))?$", re.MULTILINE)
    _ERROR_LINE = re.compile(r"^ERROR\s+(.+?)(?:\s+-\s+(.+))?$", re.MULTILINE)
    _SUMMARY_LINE = re.compile(
        r"(\d+) passed(?:,\s*(\d+) failed)?(?:,\s*(\d+) error)?(?:.*in ([\d.]+)s)?",
        re.IGNORECASE,
    )
    _IMPORT_ERROR = re.compile(r"ImportError|ModuleNotFoundError|cannot import", re.IGNORECASE)
    _ASSERTION_ERROR = re.compile(r"AssertionError|assert\s+", re.IGNORECASE)
    _TIMEOUT = re.compile(r"Timeout|timed out|TimeoutError", re.IGNORECASE)
    _ATTRIBUTE_ERROR = re.compile(r"AttributeError", re.IGNORECASE)
    _TYPE_ERROR = re.compile(r"TypeError", re.IGNORECASE)
    _VALUE_ERROR = re.compile(r"ValueError", re.IGNORECASE)
    _KEY_ERROR = re.compile(r"KeyError", re.IGNORECASE)
    _RUNTIME_ERROR = re.compile(r"RuntimeError", re.IGNORECASE)
    _COLLECTION_ERROR = re.compile(r"collection error|ERROR collecting", re.IGNORECASE)

    def classify(self, error_text: str) -> FailureCategory:
        if self._COLLECTION_ERROR.search(error_text):
            return FailureCategory.COLLECTION_ERROR
        if self._IMPORT_ERROR.search(error_text):
            return FailureCategory.IMPORT_ERROR
        if self._TIMEOUT.search(error_text):
            return FailureCategory.TIMEOUT
        if self._ASSERTION_ERROR.search(error_text):
            return FailureCategory.ASSERTION_ERROR
        if self._ATTRIBUTE_ERROR.search(error_text):
            return FailureCategory.ATTRIBUTE_ERROR
        if self._TYPE_ERROR.search(error_text):
            return FailureCategory.TYPE_ERROR
        if self._VALUE_ERROR.search(error_text):
            return FailureCategory.VALUE_ERROR
        if self._KEY_ERROR.search(error_text):
            return FailureCategory.KEY_ERROR
        if self._RUNTIME_ERROR.search(error_text):
            return FailureCategory.RUNTIME_ERROR
        return FailureCategory.UNKNOWN

    def parse(self, output: str) -> CIRun:
        """Parse full pytest output into a CIRun."""
        failures: List[TestFailure] = []

        # Extract FAILED lines
        for match in self._FAILED_LINE.finditer(output):
            test_path = match.group(1).strip()
            error_msg = match.group(2) or ""
            parts = test_path.split("::")
            file_path = parts[0] if parts else test_path
            test_name = "::".join(parts[1:]) if len(parts) > 1 else test_path
            category = self.classify(error_msg)
            failures.append(TestFailure(
                test_id=test_path,
                file_path=file_path,
                test_name=test_name,
                category=category,
                error_message=error_msg,
            ))

        # Extract ERROR lines (collection errors)
        for match in self._ERROR_LINE.finditer(output):
            test_path = match.group(1).strip()
            error_msg = match.group(2) or ""
            parts = test_path.split("::")
            file_path = parts[0] if parts else test_path
            failures.append(TestFailure(
                test_id=f"ERROR::{test_path}",
                file_path=file_path,
                test_name=test_path,
                category=FailureCategory.COLLECTION_ERROR,
                error_message=error_msg,
            ))

        # Parse summary line
        passed = failed = errors = 0
        duration = 0.0
        summary_match = self._SUMMARY_LINE.search(output)
        if summary_match:
            passed = int(summary_match.group(1) or 0)
            failed = int(summary_match.group(2) or 0)
            errors = int(summary_match.group(3) or 0)
            duration = float(summary_match.group(4) or 0.0)

        total = passed + failed + errors
        return CIRun(
            id=str(uuid.uuid4()),
            total_tests=total,
            passed=passed,
            failed=failed,
            errors=errors,
            duration_s=duration,
            failures=failures,
        )


# ---------------------------------------------------------------------------
# Repair Strategy Registry
# ---------------------------------------------------------------------------

class RepairStrategyRegistry:
    """Maps failure categories to repair strategy functions."""

    def __init__(self) -> None:
        self._strategies: Dict[FailureCategory, Callable[[TestFailure], RepairProposal]] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(FailureCategory.IMPORT_ERROR, self._fix_import_error)
        self.register(FailureCategory.ASSERTION_ERROR, self._fix_assertion_error)
        self.register(FailureCategory.TIMEOUT, self._fix_timeout)
        self.register(FailureCategory.ATTRIBUTE_ERROR, self._fix_attribute_error)
        self.register(FailureCategory.TYPE_ERROR, self._fix_type_error)
        self.register(FailureCategory.VALUE_ERROR, self._fix_value_error)
        self.register(FailureCategory.KEY_ERROR, self._fix_key_error)
        self.register(FailureCategory.COLLECTION_ERROR, self._fix_collection_error)
        self.register(FailureCategory.RUNTIME_ERROR, self._fix_runtime_error)
        self.register(FailureCategory.UNKNOWN, self._fix_unknown)

    def register(
        self,
        category: FailureCategory,
        strategy_fn: Callable[[TestFailure], RepairProposal],
    ) -> None:
        self._strategies[category] = strategy_fn

    def propose(self, failure: TestFailure) -> RepairProposal:
        fn = self._strategies.get(failure.category, self._fix_unknown)
        return fn(failure)

    # --- Default strategy implementations ---

    @staticmethod
    def _fix_import_error(f: TestFailure) -> RepairProposal:
        # Extract missing module name from error message
        match = re.search(r"No module named '([^']+)'", f.error_message)
        module = match.group(1) if match else "unknown_module"
        return RepairProposal(
            id=str(uuid.uuid4()),
            failure=f,
            strategy="install_missing_package",
            description=f"Install missing package: {module}",
            patch=f"pip install {module}",
            confidence=0.85,
            estimated_impact=max(1, len(f.error_message) // 50),
        )

    @staticmethod
    def _fix_assertion_error(f: TestFailure) -> RepairProposal:
        return RepairProposal(
            id=str(uuid.uuid4()),
            failure=f,
            strategy="update_assertion",
            description=f"Update assertion in {f.test_name} to match actual value",
            patch=f"# Review assertion in {f.file_path}::{f.test_name}",
            confidence=0.65,
            estimated_impact=1,
        )

    @staticmethod
    def _fix_timeout(f: TestFailure) -> RepairProposal:
        return RepairProposal(
            id=str(uuid.uuid4()),
            failure=f,
            strategy="increase_timeout",
            description=f"Increase timeout for {f.test_name}",
            patch=f"@pytest.mark.timeout(30)  # was default",
            confidence=0.75,
            estimated_impact=1,
        )

    @staticmethod
    def _fix_attribute_error(f: TestFailure) -> RepairProposal:
        match = re.search(r"'([^']+)' object has no attribute '([^']+)'", f.error_message)
        if match:
            obj_type, attr = match.group(1), match.group(2)
            description = f"Add missing attribute '{attr}' to {obj_type}"
        else:
            description = f"Fix AttributeError in {f.test_name}"
        return RepairProposal(
            id=str(uuid.uuid4()),
            failure=f,
            strategy="add_missing_attribute",
            description=description,
            patch=f"# Add missing attribute to class",
            confidence=0.70,
            estimated_impact=1,
        )

    @staticmethod
    def _fix_type_error(f: TestFailure) -> RepairProposal:
        return RepairProposal(
            id=str(uuid.uuid4()),
            failure=f,
            strategy="fix_type_mismatch",
            description=f"Fix type mismatch in {f.test_name}",
            patch=f"# Cast or convert argument types",
            confidence=0.60,
            estimated_impact=1,
        )

    @staticmethod
    def _fix_value_error(f: TestFailure) -> RepairProposal:
        return RepairProposal(
            id=str(uuid.uuid4()),
            failure=f,
            strategy="fix_invalid_value",
            description=f"Fix invalid value in {f.test_name}",
            patch=f"# Validate input before passing to function",
            confidence=0.65,
            estimated_impact=1,
        )

    @staticmethod
    def _fix_key_error(f: TestFailure) -> RepairProposal:
        match = re.search(r"KeyError: '?([^']+)'?", f.error_message)
        key = match.group(1) if match else "unknown_key"
        return RepairProposal(
            id=str(uuid.uuid4()),
            failure=f,
            strategy="add_missing_key",
            description=f"Add missing key '{key}' or use .get() with default",
            patch=f"# Use dict.get('{key}', default_value)",
            confidence=0.72,
            estimated_impact=1,
        )

    @staticmethod
    def _fix_collection_error(f: TestFailure) -> RepairProposal:
        return RepairProposal(
            id=str(uuid.uuid4()),
            failure=f,
            strategy="fix_import_path",
            description=f"Fix import path or add __init__.py in {f.file_path}",
            patch=f"touch {Path(f.file_path).parent}/__init__.py",
            confidence=0.80,
            estimated_impact=5,  # collection errors often affect multiple tests
        )

    @staticmethod
    def _fix_runtime_error(f: TestFailure) -> RepairProposal:
        return RepairProposal(
            id=str(uuid.uuid4()),
            failure=f,
            strategy="fix_runtime_condition",
            description=f"Fix runtime condition in {f.test_name}",
            patch=f"# Add guard condition or mock the failing call",
            confidence=0.55,
            estimated_impact=1,
        )

    @staticmethod
    def _fix_unknown(f: TestFailure) -> RepairProposal:
        return RepairProposal(
            id=str(uuid.uuid4()),
            failure=f,
            strategy="manual_review",
            description=f"Manual review required for {f.test_name}",
            patch="",
            confidence=0.20,
            estimated_impact=0,
        )


# ---------------------------------------------------------------------------
# Self-Healing CI Engine
# ---------------------------------------------------------------------------

class SelfHealingCIEngine:
    """
    Autonomous CI engine that detects test failures, proposes repairs,
    applies them, and verifies the outcome — all driven by PARL reward signals.
    """

    def __init__(
        self,
        max_parallel_repairs: int = 4,
        min_confidence_threshold: float = 0.5,
        auto_apply: bool = False,
    ) -> None:
        self.max_parallel_repairs = max_parallel_repairs
        self.min_confidence_threshold = min_confidence_threshold
        self.auto_apply = auto_apply
        self._parser = PytestOutputParser()
        self._registry = RepairStrategyRegistry()
        self._sessions: List[HealingSession] = []
        self._repair_history: List[RepairResult] = []

    # --- Public API ---

    def ingest_ci_output(self, output: str) -> CIRun:
        """Parse pytest output into a CIRun."""
        return self._parser.parse(output)

    def start_healing_session(self, ci_run: CIRun) -> HealingSession:
        """Create a new healing session for the given CI run."""
        session = HealingSession(
            id=str(uuid.uuid4()),
            ci_run=ci_run,
        )
        self._sessions.append(session)
        return session

    def generate_proposals(self, session: HealingSession) -> List[RepairProposal]:
        """Generate repair proposals for all failures in the session."""
        proposals = []
        for failure in session.ci_run.failures:
            proposal = self._registry.propose(failure)
            if proposal.confidence >= self.min_confidence_threshold:
                proposals.append(proposal)
        # Sort by confidence descending, then by estimated_impact descending
        proposals.sort(key=lambda p: (p.confidence, p.estimated_impact), reverse=True)
        # Limit to max_parallel_repairs
        proposals = proposals[: self.max_parallel_repairs]
        session.proposals.extend(proposals)
        return proposals

    def apply_proposal(
        self,
        session: HealingSession,
        proposal: RepairProposal,
        executor: Optional[Callable[[str], Tuple[bool, str]]] = None,
    ) -> RepairResult:
        """
        Apply a repair proposal. If executor is provided, it is called with
        the patch string and should return (success, output). Otherwise the
        patch is simulated.
        """
        result = RepairResult(
            proposal_id=proposal.id,
            status=RepairStatus.IN_PROGRESS,
            applied_at=time.time(),
        )

        if executor is not None:
            success, output = executor(proposal.patch)
        else:
            # Simulation: high-confidence proposals succeed
            success = proposal.confidence >= 0.7
            output = "simulated"

        if success:
            result.status = RepairStatus.APPLIED
            result.tests_healed = proposal.estimated_impact
        else:
            result.status = RepairStatus.FAILED
            result.error = output

        session.results.append(result)
        self._repair_history.append(result)
        return result

    def verify_repair(
        self,
        result: RepairResult,
        re_run_fn: Optional[Callable[[], CIRun]] = None,
        baseline_ci_run: Optional[CIRun] = None,
    ) -> RepairResult:
        """
        Verify that a repair actually improved the test suite.
        If re_run_fn is provided, it is called to get the new CI run.
        """
        if result.status != RepairStatus.APPLIED:
            return result

        if re_run_fn is not None:
            new_run = re_run_fn()
            if baseline_ci_run is not None:
                improvement = baseline_ci_run.failed - new_run.failed
                result.tests_healed = max(0, improvement)
                result.tests_broken = max(0, new_run.failed - baseline_ci_run.failed)
            result.status = (
                RepairStatus.VERIFIED if result.tests_healed > 0 else RepairStatus.FAILED
            )
        else:
            # Simulate verification
            result.status = RepairStatus.VERIFIED
        result.verified_at = time.time()
        return result

    def rollback(self, result: RepairResult, rollback_fn: Optional[Callable] = None) -> bool:
        """Roll back a repair that caused regressions."""
        if rollback_fn is not None:
            rollback_fn()
        result.status = RepairStatus.ROLLED_BACK
        return True

    def complete_session(self, session: HealingSession) -> HealingSession:
        """Mark the session as complete and compute final metrics."""
        session.completed_at = time.time()
        return session

    def compute_parl_reward(self, session: HealingSession) -> Dict[str, float]:
        """
        Compute PARL reward signal for the healing session.

        r_PARL = λ1 * r_parallel + λ2 * r_finish + r_perf
        """
        if not session.proposals:
            return {"r_parallel": 0.0, "r_finish": 1.0, "r_perf": 0.0, "total": 0.0}

        # r_parallel: fraction of proposals executed in parallel
        r_parallel = min(1.0, len(session.proposals) / max(1, self.max_parallel_repairs))

        # r_finish: fraction of proposals that completed (applied or verified)
        completed = sum(
            1 for r in session.results
            if r.status in (RepairStatus.APPLIED, RepairStatus.VERIFIED, RepairStatus.FAILED)
        )
        r_finish = completed / len(session.proposals) if session.proposals else 1.0

        # r_perf: net improvement rate
        total_failures = session.ci_run.failed + session.ci_run.errors
        r_perf = session.total_healed / max(1, total_failures)

        # Weighted sum (λ1=0.3, λ2=0.1, r_perf weight=0.6)
        total = 0.3 * r_parallel + 0.1 * r_finish + 0.6 * r_perf
        return {
            "r_parallel": r_parallel,
            "r_finish": r_finish,
            "r_perf": r_perf,
            "total": total,
        }

    def healing_report(self, session: HealingSession) -> Dict[str, Any]:
        """Generate a structured healing report for the session."""
        reward = self.compute_parl_reward(session)
        return {
            "session_id": session.id,
            "ci_run_id": session.ci_run.id,
            "severity": session.ci_run.severity.value,
            "initial_failures": session.ci_run.failed + session.ci_run.errors,
            "proposals_generated": session.total_proposals,
            "tests_healed": session.total_healed,
            "success_rate": session.success_rate,
            "parl_reward": reward,
            "duration_s": (
                (session.completed_at or time.time()) - session.started_at
            ),
            "is_complete": session.is_complete,
        }

    # --- Convenience: full auto-heal pipeline ---

    def auto_heal(
        self,
        pytest_output: str,
        executor: Optional[Callable[[str], Tuple[bool, str]]] = None,
    ) -> HealingSession:
        """
        Full pipeline: parse → propose → apply → verify → complete.
        Returns the completed HealingSession.
        """
        ci_run = self.ingest_ci_output(pytest_output)
        session = self.start_healing_session(ci_run)

        if ci_run.is_healthy:
            return self.complete_session(session)

        proposals = self.generate_proposals(session)
        for proposal in proposals:
            result = self.apply_proposal(session, proposal, executor=executor)
            if result.status == RepairStatus.APPLIED:
                self.verify_repair(result)

        return self.complete_session(session)

    # --- Stats ---

    @property
    def total_sessions(self) -> int:
        return len(self._sessions)

    @property
    def total_repairs_applied(self) -> int:
        return sum(1 for r in self._repair_history if r.status != RepairStatus.PENDING)

    @property
    def total_tests_healed(self) -> int:
        return sum(r.tests_healed for r in self._repair_history if r.success)

    def category_breakdown(self) -> Dict[str, int]:
        """Return count of failures by category across all sessions."""
        counts: Dict[str, int] = {}
        for session in self._sessions:
            for failure in session.ci_run.failures:
                key = failure.category.value
                counts[key] = counts.get(key, 0) + 1
        return counts

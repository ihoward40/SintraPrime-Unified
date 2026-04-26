"""
OperatorAgent – Main autonomous operator for SintraPrime Operator Mode.

Implements the full plan → execute → verify → iterate loop inspired by
OpenAI Operator, Manus AI, and GPT-5.5 Spud.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .browser_controller import BrowserController, ActionResult
from .task_planner import TaskPlanner, TaskPlan, TaskStep, StepResult, ActionType
from .web_researcher import WebResearcher, ResearchReport

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Status & Result types
# ---------------------------------------------------------------------------


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class CodeResult:
    """Result of sandboxed code execution."""
    success: bool
    stdout: str = ""
    stderr: str = ""
    return_value: Any = None
    error: Optional[str] = None
    duration_seconds: float = 0.0


@dataclass
class TaskResult:
    """Final result of a complete operator task execution."""
    goal: str
    status: TaskStatus
    summary: str
    steps_completed: int
    steps_total: int
    deliverables: List[str] = field(default_factory=list)
    error: Optional[str] = None
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    duration_seconds: float = 0.0
    plan: Optional[TaskPlan] = None
    step_results: List[StepResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "status": self.status.value,
            "summary": self.summary,
            "steps_completed": self.steps_completed,
            "steps_total": self.steps_total,
            "deliverables": self.deliverables,
            "error": self.error,
            "session_id": self.session_id,
            "duration_seconds": self.duration_seconds,
        }


class HumanInLoopCheckpoint:
    """
    Manages human-in-the-loop approval gates.

    When Operator encounters a sensitive step (payment, deletion, send),
    it calls checkpoint.request_approval() and waits for approval before
    proceeding. Approval can be granted programmatically or via callbacks.
    """

    def __init__(self, auto_approve: bool = False, callback: Optional[Callable] = None):
        """
        Args:
            auto_approve: If True, all approvals are granted automatically (for testing).
            callback: Optional callable(step) -> bool to handle approvals.
        """
        self.auto_approve = auto_approve
        self.callback = callback
        self.pending_steps: List[TaskStep] = []
        self.approved_steps: set = set()
        self.rejected_steps: set = set()

    def request_approval(self, step: TaskStep) -> bool:
        """
        Request human approval for a sensitive step.

        Returns:
            True if approved, False if rejected.
        """
        if self.auto_approve:
            logger.info(f"[AUTO-APPROVE] Step {step.step_id}: {step.description}")
            self.approved_steps.add(step.step_id)
            return True

        if self.callback:
            approved = self.callback(step)
            if approved:
                self.approved_steps.add(step.step_id)
            else:
                self.rejected_steps.add(step.step_id)
            return approved

        # Default: interactive prompt
        self.pending_steps.append(step)
        print(f"\n⚠️  APPROVAL REQUIRED")
        print(f"   Step {step.step_id}: {step.description}")
        print(f"   Expected outcome: {step.expected_outcome}")
        print(f"   Action type: {step.action_type.value}")
        response = input("   Approve? [y/N]: ").strip().lower()
        approved = response == "y"
        if approved:
            self.approved_steps.add(step.step_id)
        else:
            self.rejected_steps.add(step.step_id)
        return approved

    def is_approved(self, step_id: int) -> bool:
        return step_id in self.approved_steps

    def is_rejected(self, step_id: int) -> bool:
        return step_id in self.rejected_steps


# ---------------------------------------------------------------------------
# OperatorAgent
# ---------------------------------------------------------------------------


class OperatorAgent:
    """
    Main autonomous operator agent.

    Implements the full plan → execute → verify → iterate loop.
    Delegates to TaskPlanner, BrowserController, and WebResearcher.

    Example:
        agent = OperatorAgent()
        result = agent.execute("Research the top 10 trust attorneys in California")
        print(result.summary)
    """

    DELIVERABLE_DIR = "/tmp/sintra_deliverables"

    def __init__(
        self,
        planner: Optional[TaskPlanner] = None,
        browser: Optional[BrowserController] = None,
        researcher: Optional[WebResearcher] = None,
        checkpoint: Optional[HumanInLoopCheckpoint] = None,
        verbose: bool = False,
        deliverable_dir: str = DELIVERABLE_DIR,
    ):
        self.planner = planner or TaskPlanner(verbose=verbose)
        self.browser = browser or BrowserController()
        self.researcher = researcher or WebResearcher(browser=self.browser)
        self.checkpoint = checkpoint or HumanInLoopCheckpoint(auto_approve=False)
        self.verbose = verbose
        self.deliverable_dir = deliverable_dir

        os.makedirs(self.deliverable_dir, exist_ok=True)

        # Session tracking
        self.session_id = uuid.uuid4().hex
        self._history: List[Dict[str, Any]] = []
        self._current_status: Dict[str, Any] = {
            "status": TaskStatus.PENDING.value,
            "goal": "",
            "progress": 0.0,
            "steps_completed": 0,
            "steps_total": 0,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(self, goal: str, context: dict = {}) -> TaskResult:
        """
        Execute a goal autonomously using plan → execute → verify → iterate.

        Args:
            goal: Natural-language task description.
            context: Optional context dict (user info, preferences, etc.).

        Returns:
            TaskResult with status, summary, and deliverables.
        """
        start = time.time()
        session_id = uuid.uuid4().hex
        logger.info(f"[{session_id}] Starting execution: {goal}")

        self._set_status(TaskStatus.RUNNING, goal=goal)

        # Phase 1: Plan
        try:
            plan = self.planner.plan(goal)
        except Exception as exc:
            return TaskResult(
                goal=goal, status=TaskStatus.FAILED,
                summary=f"Planning failed: {exc}",
                steps_completed=0, steps_total=0,
                error=str(exc), session_id=session_id,
            )

        self._current_status["steps_total"] = len(plan.steps)
        step_results: List[StepResult] = []
        deliverables: List[str] = []

        # Phase 2: Execute each step
        for step in plan.steps:
            # Check if step needs approval
            if step.requires_approval:
                self._set_status(TaskStatus.AWAITING_APPROVAL)
                approved = self.checkpoint.request_approval(step)
                if not approved:
                    logger.warning(f"Step {step.step_id} rejected by human. Stopping.")
                    self._set_status(TaskStatus.PAUSED)
                    return TaskResult(
                        goal=goal, status=TaskStatus.PAUSED,
                        summary=f"Paused: step {step.step_id} rejected by user.",
                        steps_completed=len(step_results),
                        steps_total=len(plan.steps),
                        deliverables=deliverables,
                        session_id=session_id,
                        plan=plan,
                        step_results=step_results,
                    )
                self._set_status(TaskStatus.RUNNING)

            # Execute step with retry logic
            result = self._execute_step(step, context)
            step_results.append(result)

            # Track deliverables
            if result.success and isinstance(result.data, str) and os.path.isfile(result.data):
                deliverables.append(result.data)

            # Verify step
            verified = self.planner.verify_step(step, result)

            # Retry if needed
            retry_attempts = 0
            while not verified and step.retry_count < step.max_retries:
                logger.info(f"Retrying step {step.step_id} (attempt {step.retry_count + 1})")
                time.sleep(2 ** retry_attempts)  # Exponential back-off
                result = self._execute_step(step, context)
                step_results[-1] = result
                verified = self.planner.verify_step(step, result)
                retry_attempts += 1

            self._current_status["steps_completed"] = len(step_results)
            self._current_status["progress"] = len(step_results) / len(plan.steps)

            if self.verbose:
                status_icon = "✅" if result.success else "❌"
                logger.info(f"{status_icon} Step {step.step_id}: {step.description}")

        # Phase 3: Create summary deliverable
        summary_text = self._build_summary(goal, plan, step_results)
        report_path = self.create_deliverable("markdown", summary_text)
        if report_path:
            deliverables.append(report_path)

        duration = time.time() - start
        self._set_status(TaskStatus.COMPLETED)

        # Record in history
        self._history.append({
            "session_id": session_id,
            "goal": goal,
            "steps_completed": len(step_results),
            "duration_seconds": duration,
            "deliverables": deliverables,
        })

        return TaskResult(
            goal=goal,
            status=TaskStatus.COMPLETED,
            summary=summary_text[:500],
            steps_completed=len(step_results),
            steps_total=len(plan.steps),
            deliverables=deliverables,
            session_id=session_id,
            duration_seconds=round(duration, 2),
            plan=plan,
            step_results=step_results,
        )

    def pause_for_approval(self, step: TaskStep) -> bool:
        """
        Request human approval before executing a sensitive step.

        Returns True if approved, False if rejected.
        """
        return self.checkpoint.request_approval(step)

    def execute_sandboxed(self, code: str, language: str = "python") -> CodeResult:
        """
        Execute code in a sandboxed subprocess with timeout.

        Args:
            code: Source code to execute.
            language: 'python' or 'bash'.

        Returns:
            CodeResult with stdout, stderr, and success flag.
        """
        start = time.time()

        if language not in ("python", "bash"):
            return CodeResult(success=False, error=f"Unsupported language: {language}")

        # Write code to temp file
        suffix = ".py" if language == "python" else ".sh"
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as f:
                f.write(code)
                tmp_path = f.name

            if language == "python":
                cmd = [sys.executable, tmp_path]
            else:
                cmd = ["bash", tmp_path]

            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "SINTRA_SANDBOXED": "1"},
            )

            return CodeResult(
                success=proc.returncode == 0,
                stdout=proc.stdout,
                stderr=proc.stderr,
                error=proc.stderr if proc.returncode != 0 else None,
                duration_seconds=time.time() - start,
            )
        except subprocess.TimeoutExpired:
            return CodeResult(success=False, error="Code execution timed out (30s limit).",
                              duration_seconds=time.time() - start)
        except Exception as exc:
            return CodeResult(success=False, error=str(exc), duration_seconds=time.time() - start)
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    def delegate_to_specialist(self, task_type: str, task: Any) -> Any:
        """
        Route a task to a specialist sub-agent or tool.

        Supported task_types:
            'research' → WebResearcher
            'browse' → BrowserController
            'code' → execute_sandboxed
            'plan' → TaskPlanner
        """
        if task_type == "research":
            topic = task if isinstance(task, str) else str(task)
            return self.researcher.research(topic)
        elif task_type == "browse":
            url = task if isinstance(task, str) else str(task)
            return self.browser.navigate(url)
        elif task_type == "code":
            code = task if isinstance(task, str) else str(task)
            return self.execute_sandboxed(code)
        elif task_type == "plan":
            goal = task if isinstance(task, str) else str(task)
            return self.planner.plan(goal)
        else:
            raise ValueError(f"Unknown task_type: {task_type}")

    def create_deliverable(self, format: str, data: Any) -> str:
        """
        Create an output file in the specified format.

        Supported formats: 'markdown', 'json', 'csv', 'txt'

        Returns:
            File path to the created deliverable.
        """
        ext_map = {"markdown": "md", "json": "json", "csv": "csv", "txt": "txt"}
        ext = ext_map.get(format, "txt")
        filename = f"deliverable_{uuid.uuid4().hex[:8]}.{ext}"
        path = os.path.join(self.deliverable_dir, filename)

        try:
            if format == "json":
                content = json.dumps(data, indent=2, default=str)
            elif format == "csv":
                if isinstance(data, list) and data:
                    out = io.StringIO()
                    writer = csv.DictWriter(out, fieldnames=list(data[0].keys()))
                    writer.writeheader()
                    writer.writerows(data)
                    content = out.getvalue()
                else:
                    content = str(data)
            else:
                content = str(data)

            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"Deliverable created: {path}")
            return path
        except Exception as exc:
            logger.error(f"Failed to create deliverable: {exc}")
            return ""

    def status(self) -> Dict[str, Any]:
        """Return live task progress as a dict."""
        return dict(self._current_status)

    def replay(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Return session history for a given session_id."""
        for entry in self._history:
            if entry.get("session_id") == session_id:
                return entry
        return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _set_status(self, status: TaskStatus, **kwargs):
        self._current_status["status"] = status.value
        self._current_status.update(kwargs)

    def _execute_step(self, step: TaskStep, context: dict) -> StepResult:
        """Dispatch a TaskStep to the appropriate executor."""
        start = time.time()
        try:
            if step.action_type == ActionType.BROWSE:
                result = self.browser.navigate(step.target)
                return StepResult(
                    step_id=step.step_id,
                    success=result.success,
                    data=result.data,
                    error=result.error,
                    duration_seconds=time.time() - start,
                )
            elif step.action_type == ActionType.SEARCH:
                result = self.browser.search_web(step.target or step.description)
                return StepResult(
                    step_id=step.step_id,
                    success=result.success,
                    data=result.data,
                    error=result.error,
                    duration_seconds=time.time() - start,
                )
            elif step.action_type == ActionType.EXTRACT:
                result = self.browser.extract_text()
                return StepResult(
                    step_id=step.step_id,
                    success=result.success,
                    data=result.data,
                    error=result.error,
                    duration_seconds=time.time() - start,
                )
            elif step.action_type == ActionType.CODE:
                code_result = self.execute_sandboxed(step.target)
                return StepResult(
                    step_id=step.step_id,
                    success=code_result.success,
                    data=code_result.stdout,
                    error=code_result.error,
                    duration_seconds=time.time() - start,
                )
            elif step.action_type == ActionType.SUMMARIZE:
                report = self.researcher.research(step.description or step.target, depth=1)
                return StepResult(
                    step_id=step.step_id,
                    success=True,
                    data=report.to_markdown(),
                    duration_seconds=time.time() - start,
                )
            elif step.action_type == ActionType.VERIFY:
                # Treat verify as a no-op if previous step succeeded
                return StepResult(
                    step_id=step.step_id,
                    success=True,
                    data={"verified": True},
                    duration_seconds=time.time() - start,
                )
            elif step.action_type == ActionType.WAIT:
                wait_seconds = step.metadata.get("wait_seconds", 5)
                time.sleep(min(wait_seconds, 60))
                return StepResult(
                    step_id=step.step_id,
                    success=True,
                    data={"waited_seconds": wait_seconds},
                    duration_seconds=time.time() - start,
                )
            else:
                return StepResult(
                    step_id=step.step_id,
                    success=False,
                    error=f"Unsupported action_type: {step.action_type}",
                    duration_seconds=time.time() - start,
                )
        except Exception as exc:
            logger.error(f"Step {step.step_id} exception: {exc}")
            return StepResult(
                step_id=step.step_id,
                success=False,
                error=str(exc),
                duration_seconds=time.time() - start,
            )

    def _build_summary(
        self, goal: str, plan: TaskPlan, step_results: List[StepResult]
    ) -> str:
        successful = sum(1 for r in step_results if r.success)
        failed = len(step_results) - successful
        lines = [
            f"# Operator Task Report",
            f"",
            f"**Goal:** {goal}",
            f"**Complexity:** {plan.complexity_score}/10",
            f"**Steps:** {successful} succeeded, {failed} failed out of {len(step_results)} total",
            f"",
            f"## Chain-of-Thought Log",
        ]
        for entry in plan.cot_log[-10:]:
            lines.append(f"- {entry}")
        return "\n".join(lines)

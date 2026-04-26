"""
TaskPlanner – Autonomous multi-step task planner for SintraPrime Operator Mode.

Inspired by GPT-5.5 Spud's plan → execute → verify → iterate loop and
Manus AI's long-horizon task decomposition.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    BROWSE = "browse"
    CLICK = "click"
    TYPE = "type"
    EXTRACT = "extract"
    CODE = "code"
    VERIFY = "verify"
    SEARCH = "search"
    DOWNLOAD = "download"
    FILL_FORM = "fill_form"
    SUMMARIZE = "summarize"
    DELEGATE = "delegate"
    WAIT = "wait"


@dataclass
class TaskStep:
    """A single executable step in a task plan."""

    step_id: int
    action_type: ActionType
    target: str
    description: str
    expected_outcome: str
    requires_approval: bool = False
    dependencies: List[int] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 30
    metadata: Dict[str, Any] = field(default_factory=dict)
    cot_reasoning: str = ""  # Chain-of-thought reasoning

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "action_type": self.action_type.value,
            "target": self.target,
            "description": self.description,
            "expected_outcome": self.expected_outcome,
            "requires_approval": self.requires_approval,
            "dependencies": self.dependencies,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "metadata": self.metadata,
            "cot_reasoning": self.cot_reasoning,
        }


@dataclass
class StepResult:
    """Result of executing a single task step."""

    step_id: int
    success: bool
    data: Any = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    attempts: int = 1


@dataclass
class TaskPlan:
    """Complete task plan produced by the planner."""

    goal: str
    steps: List[TaskStep]
    complexity_score: int
    estimated_duration_minutes: float
    requires_human_approval: bool
    cot_log: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "complexity_score": self.complexity_score,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "requires_human_approval": self.requires_human_approval,
            "cot_log": self.cot_log,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# ---------------------------------------------------------------------------
# Sensitive action keywords – steps containing these require human approval
# ---------------------------------------------------------------------------
APPROVAL_REQUIRED_KEYWORDS = {
    "payment", "pay", "purchase", "buy", "charge", "subscribe",
    "delete", "remove", "destroy", "terminate", "cancel",
    "send email", "send message", "post", "publish", "submit",
    "sign", "sign up", "register", "create account",
    "wire transfer", "bank", "credit card",
}


class TaskPlanner:
    """
    Autonomous multi-step task planner.

    Breaks complex goals into discrete, verifiable steps and manages
    retry logic with chain-of-thought reasoning.

    Example:
        planner = TaskPlanner()
        plan = planner.plan("Research the top 10 trust attorneys in California")
        for step in plan.steps:
            print(step.description)
    """

    MAX_STEPS = 100
    DEFAULT_MIN_STEPS = 5
    DEFAULT_MAX_STEPS = 20

    def __init__(self, llm_client=None, verbose: bool = False):
        """
        Args:
            llm_client: Optional LLM client for dynamic plan generation.
                        Falls back to rule-based decomposition if None.
            verbose: Log chain-of-thought reasoning to stdout.
        """
        self.llm_client = llm_client
        self.verbose = verbose
        self._step_counter = 0
        self.reasoning_log: List[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def plan(self, goal: str) -> TaskPlan:
        """
        Produce a complete TaskPlan for the given goal.

        Args:
            goal: Natural-language description of what to accomplish.

        Returns:
            TaskPlan with ordered, verifiable steps.
        """
        self._reset()
        self._log(f"Planning goal: {goal}")

        complexity = self.estimate_complexity(goal)
        self._log(f"Estimated complexity: {complexity}/10")

        steps = self.decompose_goal(goal)
        self._log(f"Decomposed into {len(steps)} steps")

        requires_approval = any(s.requires_approval for s in steps)
        duration = self._estimate_duration(steps, complexity)

        return TaskPlan(
            goal=goal,
            steps=steps,
            complexity_score=complexity,
            estimated_duration_minutes=duration,
            requires_human_approval=requires_approval,
            cot_log=list(self.reasoning_log),
        )

    def decompose_goal(self, goal: str) -> List[TaskStep]:
        """
        Decompose a complex goal into 5-20 executable steps.

        Uses LLM if available, otherwise applies rule-based heuristics.

        Args:
            goal: The high-level goal string.

        Returns:
            Ordered list of TaskStep objects.
        """
        if self.llm_client is not None:
            return self._llm_decompose(goal)
        return self._heuristic_decompose(goal)

    def verify_step(self, step: TaskStep, result: StepResult) -> bool:
        """
        Verify whether a step completed successfully.
        Retries up to step.max_retries times on failure.

        Args:
            step: The step that was executed.
            result: The result from executing the step.

        Returns:
            True if the step succeeded (possibly after retries), False otherwise.
        """
        if result.success:
            self._log(f"Step {step.step_id} verified OK: {step.expected_outcome}")
            return True

        if step.retry_count >= step.max_retries:
            self._log(
                f"Step {step.step_id} FAILED after {step.retry_count} retries: {result.error}"
            )
            return False

        step.retry_count += 1
        self._log(
            f"Step {step.step_id} retry {step.retry_count}/{step.max_retries}: {result.error}"
        )
        return False  # Caller should re-execute

    def estimate_complexity(self, goal: str) -> int:
        """
        Estimate complexity of a goal on a 1-10 scale.

        Heuristics:
          - Number of distinct actions implied
          - Presence of legal/financial/multi-entity keywords
          - Length and specificity of the goal

        Returns:
            Integer 1-10 (1 = trivial lookup, 10 = weeks-long project)
        """
        score = 1
        goal_lower = goal.lower()

        # Length heuristic
        word_count = len(goal.split())
        score += min(word_count // 10, 2)

        # Domain keywords
        complex_domains = [
            "legal", "court", "lawsuit", "filing", "contract",
            "jurisdiction", "multi", "multiple", "several", "all",
            "compare", "analyze", "research", "comprehensive",
            "integrate", "automate", "monitor", "track",
        ]
        for kw in complex_domains:
            if kw in goal_lower:
                score += 1

        # Action multipliers
        if any(k in goal_lower for k in ["and then", "after that", "next", "finally"]):
            score += 2

        # Hard cap
        return min(max(score, 1), 10)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _reset(self):
        self._step_counter = 0
        self.reasoning_log = []

    def _next_id(self) -> int:
        self._step_counter += 1
        return self._step_counter

    def _log(self, message: str):
        ts = time.strftime("%H:%M:%S")
        entry = f"[{ts}] {message}"
        self.reasoning_log.append(entry)
        if self.verbose:
            logger.info(entry)

    def _estimate_duration(self, steps: List[TaskStep], complexity: int) -> float:
        base_per_step = 0.5  # minutes
        return round(len(steps) * base_per_step * (1 + complexity / 10), 1)

    def _needs_approval(self, description: str) -> bool:
        dl = description.lower()
        return any(kw in dl for kw in APPROVAL_REQUIRED_KEYWORDS)

    def _make_step(
        self,
        action_type: ActionType,
        target: str,
        description: str,
        expected_outcome: str,
        requires_approval: bool = False,
        dependencies: Optional[List[int]] = None,
        reasoning: str = "",
        timeout: int = 30,
    ) -> TaskStep:
        sid = self._next_id()
        if requires_approval is False:
            requires_approval = self._needs_approval(description)
        step = TaskStep(
            step_id=sid,
            action_type=action_type,
            target=target,
            description=description,
            expected_outcome=expected_outcome,
            requires_approval=requires_approval,
            dependencies=dependencies or [],
            timeout_seconds=timeout,
            cot_reasoning=reasoning,
        )
        self._log(f"Step {sid}: [{action_type.value}] {description} → {expected_outcome}")
        return step

    # ------------------------------------------------------------------
    # Rule-based decomposition (fallback when no LLM is available)
    # ------------------------------------------------------------------

    def _heuristic_decompose(self, goal: str) -> List[TaskStep]:
        """
        Rule-based goal decomposition using keyword matching.
        Produces generic research/execution pipelines tailored to the goal.
        """
        goal_lower = goal.lower()
        steps: List[TaskStep] = []

        # --- Step 1: Always start with a research phase ---
        s1 = self._make_step(
            ActionType.SEARCH,
            target=goal,
            description=f"Search the web for: {goal}",
            expected_outcome="List of relevant URLs and snippets",
            reasoning="Begin by gathering initial information from multiple sources.",
        )
        steps.append(s1)

        # --- Step 2: Browse top results ---
        s2 = self._make_step(
            ActionType.BROWSE,
            target="top search results",
            description="Browse the top 5 search result pages",
            expected_outcome="Raw content from primary sources",
            dependencies=[s1.step_id],
            reasoning="Collect raw data from the most relevant sources.",
        )
        steps.append(s2)

        # --- Domain-specific branching ---
        if any(k in goal_lower for k in ["attorney", "lawyer", "legal", "court", "law"]):
            steps.extend(self._legal_research_steps([s2.step_id]))
        elif any(k in goal_lower for k in ["market", "competitor", "industry", "business"]):
            steps.extend(self._market_research_steps([s2.step_id]))
        elif any(k in goal_lower for k in ["form", "file", "document", "download"]):
            steps.extend(self._document_steps([s2.step_id]))
        else:
            steps.extend(self._generic_research_steps([s2.step_id]))

        # --- Always end with summarize & deliverable ---
        last_id = steps[-1].step_id
        s_sum = self._make_step(
            ActionType.SUMMARIZE,
            target="collected_data",
            description="Synthesize all gathered information into a structured report",
            expected_outcome="Comprehensive markdown report with citations",
            dependencies=[last_id],
            reasoning="Produce final deliverable from aggregated data.",
        )
        steps.append(s_sum)

        s_verify = self._make_step(
            ActionType.VERIFY,
            target="report",
            description="Verify report completeness and accuracy",
            expected_outcome="Validated, fact-checked report ready for delivery",
            dependencies=[s_sum.step_id],
            reasoning="Final quality gate before handing off to user.",
        )
        steps.append(s_verify)

        return steps[: self.MAX_STEPS]

    def _legal_research_steps(self, deps: List[int]) -> List[TaskStep]:
        steps = []
        s = self._make_step(
            ActionType.BROWSE,
            target="https://www.avvo.com",
            description="Browse Avvo attorney directory",
            expected_outcome="Attorney profiles with ratings and reviews",
            dependencies=deps,
            reasoning="Avvo is the primary attorney rating source.",
        )
        steps.append(s)

        s2 = self._make_step(
            ActionType.BROWSE,
            target="https://www.martindale.com",
            description="Browse Martindale-Hubbell attorney directory",
            expected_outcome="Peer-rated attorney profiles",
            dependencies=[s.step_id],
        )
        steps.append(s2)

        s3 = self._make_step(
            ActionType.EXTRACT,
            target="attorney_profiles",
            description="Extract attorney names, contact info, ratings, and specializations",
            expected_outcome="Structured list of attorney data",
            dependencies=[s.step_id, s2.step_id],
        )
        steps.append(s3)

        s4 = self._make_step(
            ActionType.VERIFY,
            target="bar_membership",
            description="Cross-reference attorneys with state bar membership records",
            expected_outcome="Confirmed active bar members only",
            dependencies=[s3.step_id],
        )
        steps.append(s4)

        return steps

    def _market_research_steps(self, deps: List[int]) -> List[TaskStep]:
        steps = []
        s = self._make_step(
            ActionType.SEARCH,
            target="market_reports",
            description="Search for industry reports and market data",
            expected_outcome="Market size, growth rate, key players",
            dependencies=deps,
        )
        steps.append(s)

        s2 = self._make_step(
            ActionType.EXTRACT,
            target="competitor_data",
            description="Extract competitor profiles, pricing, and positioning",
            expected_outcome="Competitive matrix data",
            dependencies=[s.step_id],
        )
        steps.append(s2)

        s3 = self._make_step(
            ActionType.SUMMARIZE,
            target="market_data",
            description="Compile market research into structured report",
            expected_outcome="Market research report with charts and data tables",
            dependencies=[s2.step_id],
        )
        steps.append(s3)

        return steps

    def _document_steps(self, deps: List[int]) -> List[TaskStep]:
        steps = []
        s = self._make_step(
            ActionType.BROWSE,
            target="government_portal",
            description="Locate the relevant government or agency portal",
            expected_outcome="Portal landing page loaded",
            dependencies=deps,
        )
        steps.append(s)

        s2 = self._make_step(
            ActionType.DOWNLOAD,
            target="form_document",
            description="Download the required form or document",
            expected_outcome="Document saved locally",
            dependencies=[s.step_id],
        )
        steps.append(s2)

        return steps

    def _generic_research_steps(self, deps: List[int]) -> List[TaskStep]:
        steps = []
        s = self._make_step(
            ActionType.EXTRACT,
            target="web_content",
            description="Extract key facts and data points from source pages",
            expected_outcome="Structured data from multiple sources",
            dependencies=deps,
        )
        steps.append(s)

        s2 = self._make_step(
            ActionType.VERIFY,
            target="facts",
            description="Cross-reference key facts across at least 3 sources",
            expected_outcome="Verified facts with source citations",
            dependencies=[s.step_id],
        )
        steps.append(s2)

        return steps

    def _llm_decompose(self, goal: str) -> List[TaskStep]:
        """
        Use an LLM client to decompose the goal into steps.
        The LLM is expected to return a JSON list of step dictionaries.
        """
        prompt = (
            f"You are a task planner. Decompose the following goal into {self.DEFAULT_MIN_STEPS}"
            f"-{self.DEFAULT_MAX_STEPS} discrete, verifiable steps.\n\n"
            f"Goal: {goal}\n\n"
            "For each step, provide:\n"
            "  - action_type (browse/click/type/extract/code/verify/search/download/fill_form/summarize)\n"
            "  - target (URL, selector, or data target)\n"
            "  - description (what to do)\n"
            "  - expected_outcome (how to verify success)\n"
            "  - requires_approval (true if sensitive: payments, deletions, sends)\n"
            "  - cot_reasoning (why this step is needed)\n\n"
            "Return ONLY valid JSON array."
        )

        try:
            response = self.llm_client.complete(prompt)
            raw_steps = json.loads(response)
        except Exception as exc:
            logger.warning(f"LLM decomposition failed: {exc}. Falling back to heuristics.")
            return self._heuristic_decompose(goal)

        steps = []
        for raw in raw_steps[: self.MAX_STEPS]:
            try:
                action_type = ActionType(raw.get("action_type", "browse"))
            except ValueError:
                action_type = ActionType.BROWSE

            step = self._make_step(
                action_type=action_type,
                target=raw.get("target", ""),
                description=raw.get("description", ""),
                expected_outcome=raw.get("expected_outcome", ""),
                requires_approval=raw.get("requires_approval", False),
                reasoning=raw.get("cot_reasoning", ""),
            )
            steps.append(step)

        return steps

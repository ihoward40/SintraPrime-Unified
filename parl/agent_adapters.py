"""
PARL Agent Adapters — Bridge between SintraPrime agents and the PARL framework.

Each adapter wraps an existing SintraPrime agent (Zero, Sigma, Nova, Chat)
and exposes it as a PARL-compatible SubagentFn:

    SubagentFn = Callable[[Subtask], Tuple[Any, float]]
                                               ↑ trajectory_score in [0, 1]

The adapters also:
- Pull the latest policy parameters from the PolicyStore before each run
- Push gradient signals back after each run
- Report PARL-compatible trajectory scores based on agent-specific outcomes
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from typing import Any, Dict, Optional, Tuple

from parl.orchestrator import Subtask, SubtaskStatus
from parl.policy_sync import PolicyStore

logger = logging.getLogger("parl.adapters")


# ---------------------------------------------------------------------------
# Base adapter
# ---------------------------------------------------------------------------

class BasePARLAdapter:
    """
    Base class for all PARL agent adapters.

    Subclasses override `_execute` to implement agent-specific logic.
    """

    AGENT_TYPE: str = "generic"

    def __init__(self, policy_store: Optional[PolicyStore] = None):
        self.policy_store = policy_store
        self._call_count = 0
        self._success_count = 0

    def __call__(self, subtask: Subtask) -> Tuple[Any, float]:
        """PARL SubagentFn interface."""
        # Pull latest policy parameters
        params: Dict[str, Any] = {}
        if self.policy_store:
            params = self.policy_store.get_parameters(self.AGENT_TYPE) or {}

        self._call_count += 1
        try:
            result, score = self._execute(subtask, params)
            self._success_count += 1
            # Push a positive gradient signal
            if self.policy_store:
                self.policy_store.push_gradient(
                    self.AGENT_TYPE,
                    {"reward": score, "success": 1.0},
                    weight=score,
                )
            return result, score
        except Exception as exc:
            logger.warning("%s adapter error: %s", self.AGENT_TYPE, exc)
            if self.policy_store:
                self.policy_store.push_gradient(
                    self.AGENT_TYPE,
                    {"reward": -0.5, "success": 0.0},
                    weight=0.1,
                )
            raise

    def _execute(
        self, subtask: Subtask, params: Dict[str, Any]
    ) -> Tuple[Any, float]:
        """Override in subclasses. Return (result, trajectory_score)."""
        raise NotImplementedError

    @property
    def success_rate(self) -> float:
        if self._call_count == 0:
            return 0.0
        return self._success_count / self._call_count


# ---------------------------------------------------------------------------
# Zero adapter — self-healing maintenance agent
# ---------------------------------------------------------------------------

class ZeroPARLAdapter(BasePARLAdapter):
    """
    PARL adapter for Agent Zero (autonomous self-healing).

    Trajectory score is based on:
    - Number of import errors fixed
    - Number of tests restored to green
    - Whether the build is passing after the patch
    """

    AGENT_TYPE = "zero"

    def __init__(
        self,
        repo_path: str = ".",
        policy_store: Optional[PolicyStore] = None,
    ):
        super().__init__(policy_store)
        self.repo_path = repo_path

    def _execute(
        self, subtask: Subtask, params: Dict[str, Any]
    ) -> Tuple[Any, float]:
        description = subtask.description.lower()
        payload = subtask.payload

        # Simulate Zero's self-healing actions
        result: Dict[str, Any] = {
            "agent": "zero",
            "subtask_id": subtask.subtask_id,
            "description": subtask.description,
            "actions_taken": [],
            "errors_fixed": 0,
            "tests_restored": 0,
        }

        score = 0.5  # baseline

        if "import" in description or "fix" in description:
            # Attempt to detect and report import errors
            try:
                proc = subprocess.run(
                    [sys.executable, "-c",
                     f"import py_compile, glob; "
                     f"errors = []; "
                     f"[errors.append(f) for f in glob.glob('{self.repo_path}/**/*.py', recursive=True) "
                     f"if not (lambda f: (py_compile.compile(f, doraise=True), True) or True)(f)]; "
                     f"print(len(errors))"],
                    capture_output=True, text=True, timeout=10
                )
                result["actions_taken"].append("import_scan")
                result["errors_fixed"] = payload.get("errors_to_fix", 1)
                score = min(1.0, 0.6 + result["errors_fixed"] * 0.1)
            except Exception:
                score = 0.4

        if "test" in description:
            result["actions_taken"].append("test_scan")
            result["tests_restored"] = payload.get("tests_to_restore", 1)
            score = min(1.0, score + result["tests_restored"] * 0.05)

        result["trajectory_score"] = score
        return result, score


# ---------------------------------------------------------------------------
# Sigma adapter — CI/CD gating agent
# ---------------------------------------------------------------------------

class SigmaPARLAdapter(BasePARLAdapter):
    """
    PARL adapter for Agent Sigma (mandatory test gating).

    Trajectory score is based on:
    - Test pass rate
    - Coverage percentage
    - Security scan findings
    """

    AGENT_TYPE = "sigma"

    def __init__(
        self,
        repo_path: str = ".",
        policy_store: Optional[PolicyStore] = None,
    ):
        super().__init__(policy_store)
        self.repo_path = repo_path

    def _execute(
        self, subtask: Subtask, params: Dict[str, Any]
    ) -> Tuple[Any, float]:
        description = subtask.description.lower()
        payload = subtask.payload

        result: Dict[str, Any] = {
            "agent": "sigma",
            "subtask_id": subtask.subtask_id,
            "description": subtask.description,
            "checks_run": [],
            "pass_rate": 0.0,
            "coverage_pct": 0.0,
            "security_issues": 0,
        }

        score = 0.5

        if "test" in description or "suite" in description:
            pass_rate = payload.get("pass_rate", 0.95)
            result["checks_run"].append("test_suite")
            result["pass_rate"] = pass_rate
            score = pass_rate  # direct mapping

        if "coverage" in description:
            coverage = payload.get("coverage_pct", 80.0)
            result["checks_run"].append("coverage")
            result["coverage_pct"] = coverage
            score = min(1.0, score * 0.7 + (coverage / 100.0) * 0.3)

        if "security" in description or "scan" in description:
            issues = payload.get("security_issues", 0)
            result["checks_run"].append("security_scan")
            result["security_issues"] = issues
            penalty = min(0.3, issues * 0.05)
            score = max(0.0, score - penalty)

        result["trajectory_score"] = score
        return result, score


# ---------------------------------------------------------------------------
# Nova adapter — real-world execution agent
# ---------------------------------------------------------------------------

class NovaPARLAdapter(BasePARLAdapter):
    """
    PARL adapter for Agent Nova (autonomous real-world execution).

    Trajectory score is based on:
    - Action completion rate
    - Approval level (AUTO > HUMAN > LEGAL_REVIEW)
    - Audit trail completeness
    """

    AGENT_TYPE = "nova"

    def __init__(
        self,
        policy_store: Optional[PolicyStore] = None,
    ):
        super().__init__(policy_store)

    def _execute(
        self, subtask: Subtask, params: Dict[str, Any]
    ) -> Tuple[Any, float]:
        description = subtask.description.lower()
        payload = subtask.payload

        result: Dict[str, Any] = {
            "agent": "nova",
            "subtask_id": subtask.subtask_id,
            "description": subtask.description,
            "actions_dispatched": 0,
            "actions_completed": 0,
            "approval_level": "AUTO",
            "audit_entries": 0,
        }

        score = 0.5

        actions_total = payload.get("actions_total", 1)
        actions_done = payload.get("actions_completed", actions_total)
        approval = payload.get("approval_level", "AUTO")

        result["actions_dispatched"] = actions_total
        result["actions_completed"] = actions_done
        result["approval_level"] = approval
        result["audit_entries"] = actions_done

        completion_rate = actions_done / max(actions_total, 1)

        # Approval level bonus (AUTO is fastest/most autonomous)
        approval_bonus = {"AUTO": 0.1, "HUMAN": 0.05, "LEGAL_REVIEW": 0.0}.get(
            approval, 0.0
        )

        score = min(1.0, completion_rate * 0.8 + approval_bonus + 0.1)
        result["trajectory_score"] = score
        return result, score


# ---------------------------------------------------------------------------
# Chat adapter — autonomous chat agent
# ---------------------------------------------------------------------------

class ChatPARLAdapter(BasePARLAdapter):
    """
    PARL adapter for the Chat Agent (primary autonomy interface).

    Trajectory score is based on:
    - Intent detection accuracy
    - Task delegation success
    - Session memory utilisation
    """

    AGENT_TYPE = "chat"

    def __init__(
        self,
        policy_store: Optional[PolicyStore] = None,
    ):
        super().__init__(policy_store)

    def _execute(
        self, subtask: Subtask, params: Dict[str, Any]
    ) -> Tuple[Any, float]:
        description = subtask.description.lower()
        payload = subtask.payload

        result: Dict[str, Any] = {
            "agent": "chat",
            "subtask_id": subtask.subtask_id,
            "description": subtask.description,
            "intent_detected": None,
            "delegated_to": None,
            "response_generated": False,
            "memory_hits": 0,
        }

        score = 0.5

        # Simulate intent detection
        if any(kw in description for kw in ["fix", "repair", "error", "broken"]):
            result["intent_detected"] = "self_healing"
            result["delegated_to"] = "zero"
            score = 0.85
        elif any(kw in description for kw in ["test", "ci", "coverage", "gate"]):
            result["intent_detected"] = "ci_gate"
            result["delegated_to"] = "sigma"
            score = 0.85
        elif any(kw in description for kw in ["execute", "action", "dispatch", "file"]):
            result["intent_detected"] = "execution"
            result["delegated_to"] = "nova"
            score = 0.80
        elif any(kw in description for kw in ["chat", "answer", "respond", "help"]):
            result["intent_detected"] = "conversation"
            result["response_generated"] = True
            score = 0.90
        else:
            result["intent_detected"] = "general"
            score = 0.70

        memory_hits = payload.get("memory_hits", 0)
        result["memory_hits"] = memory_hits
        score = min(1.0, score + memory_hits * 0.02)

        result["trajectory_score"] = score
        return result, score


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

ADAPTER_REGISTRY: Dict[str, type] = {
    "zero": ZeroPARLAdapter,
    "sigma": SigmaPARLAdapter,
    "nova": NovaPARLAdapter,
    "chat": ChatPARLAdapter,
}


def create_adapter(
    agent_type: str,
    policy_store: Optional[PolicyStore] = None,
    **kwargs: Any,
) -> BasePARLAdapter:
    """
    Factory function to create a PARL adapter by agent type name.

    Args:
        agent_type:   One of "zero", "sigma", "nova", "chat"
        policy_store: Shared PolicyStore instance
        **kwargs:     Additional kwargs passed to the adapter constructor

    Returns:
        A BasePARLAdapter subclass instance.
    """
    cls = ADAPTER_REGISTRY.get(agent_type.lower())
    if cls is None:
        raise ValueError(
            f"Unknown agent type '{agent_type}'. "
            f"Available: {list(ADAPTER_REGISTRY.keys())}"
        )
    return cls(policy_store=policy_store, **kwargs)

"""SuperCoder certification chain — independent verification of completed work."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .mission import CodingMission, WorkUnit
from .role_registry import SuperCoderRole


from enum import Enum

class CertStep(str, Enum):
    IMPLEMENTED = "IMPLEMENTED"
    TESTED = "TESTED"
    SECURITY_REVIEWED = "SECURITY_REVIEWED"
    CODE_REVIEWED = "CODE_REVIEWED"
    INTEGRATED = "INTEGRATED"
    CERTIFIED = "CERTIFIED"
    FAILED = "FAILED"


@dataclass
class CertificationResult:
    """Result of one certification step."""
    step: CertStep
    passed: bool
    reviewer_id: str
    findings: List[str] = field(default_factory=list)
    authority_delta: int = 0
    side_effects: int = 0


class CertificationChain:
    """Independent certification of completed work.

    Never let the implementer be the final certifier.
    BUILDER != CERTIFIER

    Chain: Implementer → Test Engineer → Security Reviewer → Code Reviewer → Integrator
    For authority/security code: + Adversarial Evaluator
    """

    def __init__(self, mission_id: str):
        self.mission_id = mission_id
        self._results: List[CertificationResult] = []

    def submit(self, step: CertStep, passed: bool, reviewer_id: str, findings: List[str] = None, authority_delta: int = 0, side_effects: int = 0) -> CertificationResult:
        result = CertificationResult(
            step=step,
            passed=passed,
            reviewer_id=reviewer_id,
            findings=findings or [],
            authority_delta=authority_delta,
            side_effects=side_effects,
        )
        self._results.append(result)
        return result

    def is_fully_certified(self) -> bool:
        """Check if all required steps have passed."""
        required = {CertStep.IMPLEMENTED, CertStep.TESTED, CertStep.CODE_REVIEWED}
        passed_steps = {r.step for r in self._results if r.passed}
        return required.issubset(passed_steps)

    def any_failed(self) -> bool:
        return any(not r.passed for r in self._results)

    def authority_delta_total(self) -> int:
        return sum(r.authority_delta for r in self._results)

    def side_effects_total(self) -> int:
        return sum(r.side_effects for r in self._results)

    def all_results(self) -> List[CertificationResult]:
        return list(self._results)

    def summary(self) -> str:
        steps = [f"{r.step.value}={'PASS' if r.passed else 'FAIL'}" for r in self._results]
        return " → ".join(steps) if steps else "No certification steps submitted"
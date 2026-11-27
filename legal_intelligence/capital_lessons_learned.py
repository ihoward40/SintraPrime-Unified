"""Governance learning loop for the SintraPrime private-capital stack.

SP-CAPITAL-LESSONS-LEARNED-001 converts ineffective or partially effective outcomes
into reusable lessons, policy-change candidates, underwriting adjustments, servicing
changes, and future early-warning rules. It is an internal governance mechanism and
does not itself change policy or authorize transactions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class CapitalLesson:
    lesson_id: str
    decision_id: str
    outcome_classification: str
    problem_statement: str
    root_cause: str
    lesson: str
    policy_change_candidates: tuple[str, ...]
    underwriting_adjustments: tuple[str, ...]
    early_warning_candidates: tuple[str, ...]
    servicing_adjustments: tuple[str, ...]
    governance_actions: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    status: str
    beneficial_suggestions: tuple[str, ...]


class CapitalLessonsLearnedEngine:
    MODULE_ID = "SP-CAPITAL-LESSONS-LEARNED-001"
    ACTIONABLE_OUTCOMES = {"INEFFECTIVE", "PARTIALLY_EFFECTIVE"}

    def derive(self, context: Mapping[str, object]) -> CapitalLesson:
        lesson_id = str(context.get("lesson_id") or "").strip()
        decision_id = str(context.get("decision_id") or "").strip()
        outcome = str(context.get("outcome_classification") or "").strip().upper()
        problem = str(context.get("problem_statement") or "").strip()
        root_cause = str(context.get("root_cause") or "").strip()
        lesson_text = str(context.get("lesson") or "").strip()
        evidence_refs = tuple(str(x).strip() for x in (context.get("evidence_refs") or []) if str(x).strip())

        findings: list[str] = []
        if not lesson_id:
            findings.append("LESSON_ID_REQUIRED")
        if not decision_id:
            findings.append("DECISION_ID_REQUIRED")
        if not outcome:
            findings.append("OUTCOME_CLASSIFICATION_REQUIRED")
        if not problem:
            findings.append("PROBLEM_STATEMENT_REQUIRED")
        if not root_cause:
            findings.append("ROOT_CAUSE_REQUIRED")
        if not lesson_text:
            findings.append("LESSON_REQUIRED")
        if not evidence_refs:
            findings.append("EVIDENCE_REFS_REQUIRED")

        policy = list(context.get("policy_change_candidates") or [])
        underwriting = list(context.get("underwriting_adjustments") or [])
        early_warning = list(context.get("early_warning_candidates") or [])
        servicing = list(context.get("servicing_adjustments") or [])
        governance = list(context.get("governance_actions") or [])

        if outcome in self.ACTIONABLE_OUTCOMES:
            if not policy and "POLICY" in str(context.get("failure_domain") or "").upper():
                policy.append("Review governing threshold or policy design through SP-POLICY-CHANGE-CONTROL-001.")
            if not underwriting and "UNDERWRIT" in str(context.get("failure_domain") or "").upper():
                underwriting.append("Revisit underwriting assumptions and approval criteria for similar future facilities.")
            if not early_warning:
                early_warning.append("Evaluate whether a leading indicator could have detected this deterioration earlier.")
            if not governance:
                governance.append("Present the lesson in the next committee pack and assign an owner for disposition.")

        if outcome == "EFFECTIVE":
            status = "CAPTURE_FOR_REUSE"
        elif outcome in self.ACTIONABLE_OUTCOMES:
            status = "ACTION_REQUIRED"
        elif outcome == "TOO_EARLY_TO_TELL":
            status = "DEFER_PENDING_OUTCOME_REVIEW"
        else:
            status = "REVIEW_REQUIRED"

        if findings:
            status = "INCOMPLETE"

        suggestions = [
            "Require evidence-backed root-cause analysis before changing policy or underwriting rules.",
            "Use SP-POLICY-CHANGE-CONTROL-001 for any policy change candidate; lessons do not directly mutate active policy.",
            "Promote repeat lessons into early-warning rules only after checking for false positives and source-data quality.",
            "Track whether adopted lessons later improve outcomes so the learning loop itself can be audited.",
        ]
        if findings:
            suggestions.append("Resolve required lesson fields before treating the item as an institutional learning record.")

        return CapitalLesson(
            lesson_id=lesson_id,
            decision_id=decision_id,
            outcome_classification=outcome,
            problem_statement=problem,
            root_cause=root_cause,
            lesson=lesson_text,
            policy_change_candidates=tuple(str(x) for x in policy),
            underwriting_adjustments=tuple(str(x) for x in underwriting),
            early_warning_candidates=tuple(str(x) for x in early_warning),
            servicing_adjustments=tuple(str(x) for x in servicing),
            governance_actions=tuple(str(x) for x in governance),
            evidence_refs=evidence_refs,
            status=status,
            beneficial_suggestions=tuple(suggestions),
        )

    def adoption_payload(self, lesson: CapitalLesson) -> dict[str, object]:
        """Return controlled downstream candidates without auto-applying them."""
        return {
            "module_id": self.MODULE_ID,
            "lesson_id": lesson.lesson_id,
            "decision_id": lesson.decision_id,
            "status": lesson.status,
            "policy_change_candidates": list(lesson.policy_change_candidates),
            "underwriting_adjustments": list(lesson.underwriting_adjustments),
            "early_warning_candidates": list(lesson.early_warning_candidates),
            "servicing_adjustments": list(lesson.servicing_adjustments),
            "governance_actions": list(lesson.governance_actions),
            "requires_separate_approval": True,
            "beneficial_suggestions": [
                "Route policy candidates through policy-change governance, underwriting changes through credit governance, and surveillance candidates through controlled rule testing.",
                "Never auto-deploy a lesson-derived rule solely because a prior decision was ineffective.",
            ],
        }

"""Decision-to-execution action tracking for the SintraPrime private-capital stack.

SP-CAPITAL-ACTION-TRACKER-001 tracks committee decisions through assigned action,
evidence of completion, aging, overdue escalation, and independent closure certification.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Iterable


@dataclass
class CapitalAction:
    action_id: str
    decision_id: str
    owner: str
    action: str
    due_date: date
    status: str = "OPEN"
    evidence_refs: list[str] = field(default_factory=list)
    completed_date: date | None = None
    closure_certifier: str | None = None
    closure_authority: str | None = None
    closure_certified_date: date | None = None
    reopen_trigger: str | None = None
    journal_entry_ref: str | None = None


@dataclass(frozen=True)
class ActionStatusReport:
    module_id: str
    action_id: str
    status: str
    findings: tuple[str, ...]
    beneficial_suggestions: tuple[str, ...]


class CapitalActionTrackerEngine:
    MODULE_ID = "SP-CAPITAL-ACTION-TRACKER-001"

    def evaluate(self, action: CapitalAction, as_of: date) -> ActionStatusReport:
        findings: list[str] = []
        status = action.status.upper()

        if not action.action_id.strip():
            findings.append("ACTION_ID_REQUIRED")
        if not action.decision_id.strip():
            findings.append("DECISION_ID_REQUIRED")
        if not action.owner.strip():
            findings.append("OWNER_REQUIRED")
        if not action.action.strip():
            findings.append("ACTION_DESCRIPTION_REQUIRED")

        if status in {"OPEN", "IN_PROGRESS"} and as_of > action.due_date:
            status = "OVERDUE"
            findings.append("ACTION_OVERDUE")

        if status in {"COMPLETE", "CLOSED"} and not action.evidence_refs:
            findings.append("COMPLETION_EVIDENCE_REQUIRED")
            status = "EVIDENCE_DEFICIENT"

        if status == "CLOSED":
            if not action.closure_certifier:
                findings.append("CLOSURE_CERTIFIER_REQUIRED")
            if not action.closure_authority:
                findings.append("CLOSURE_AUTHORITY_REQUIRED")
            if not action.closure_certified_date:
                findings.append("CLOSURE_CERTIFICATION_DATE_REQUIRED")
            if action.closure_certifier == action.owner:
                findings.append("INDEPENDENT_CLOSURE_CERTIFICATION_REQUIRED")

        if action.reopen_trigger:
            status = "REOPENED"
            findings.append(f"REOPEN_TRIGGER:{action.reopen_trigger}")

        suggestions = (
            "Attach source evidence proving the action occurred; approval or narrative alone is not execution evidence.",
            "Route overdue actions to Principal and audit review and include them in the monthly risk-trend report.",
            "Use an independent closure certifier for material actions and funding-freeze releases.",
            "Journal closure, reopening, extension, and reassignment events instead of overwriting prior history.",
        )
        return ActionStatusReport(
            module_id=self.MODULE_ID,
            action_id=action.action_id,
            status=status,
            findings=tuple(findings),
            beneficial_suggestions=suggestions,
        )

    def certify_closure(
        self,
        action: CapitalAction,
        *,
        certifier: str,
        authority: str,
        certified_date: date,
        evidence_refs: Iterable[str],
    ) -> ActionStatusReport:
        refs = [ref for ref in evidence_refs if str(ref).strip()]
        if not refs:
            return ActionStatusReport(
                module_id=self.MODULE_ID,
                action_id=action.action_id,
                status="BLOCK_CLOSURE",
                findings=("COMPLETION_EVIDENCE_REQUIRED",),
                beneficial_suggestions=("Collect execution evidence before closure certification.",),
            )
        if certifier == action.owner:
            return ActionStatusReport(
                module_id=self.MODULE_ID,
                action_id=action.action_id,
                status="BLOCK_CLOSURE",
                findings=("INDEPENDENT_CLOSURE_CERTIFICATION_REQUIRED",),
                beneficial_suggestions=("Assign closure certification to an independent authorized reviewer.",),
            )

        action.evidence_refs = refs
        action.completed_date = certified_date
        action.closure_certifier = certifier
        action.closure_authority = authority
        action.closure_certified_date = certified_date
        action.status = "CLOSED"
        return self.evaluate(action, certified_date)

    def portfolio_summary(self, actions: Iterable[CapitalAction], as_of: date) -> dict[str, object]:
        records = list(actions)
        reports = [self.evaluate(action, as_of) for action in records]
        overdue = [report.action_id for report in reports if report.status == "OVERDUE"]
        reopened = [report.action_id for report in reports if report.status == "REOPENED"]
        evidence_deficient = [report.action_id for report in reports if report.status == "EVIDENCE_DEFICIENT"]
        return {
            "module_id": self.MODULE_ID,
            "action_count": len(records),
            "overdue_action_ids": overdue,
            "reopened_action_ids": reopened,
            "evidence_deficient_action_ids": evidence_deficient,
            "beneficial_suggestions": [
                "Feed overdue/reopened/evidence-deficient counts into SP-CAPITAL-RISK-TRENDS-001.",
                "Include unresolved actions in the next SP-CAPITAL-COMMITTEE-PACK-001 decision-required queue.",
            ],
        }

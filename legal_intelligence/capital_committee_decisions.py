"""Formal committee disposition control for the SintraPrime private-capital stack.

SP-CAPITAL-COMMITTEE-DECISIONS-001 records committee decisions as governed,
traceable dispositions. Committee approval does not itself create legal authority,
perfect collateral, cure documentation defects, or authorize enforcement.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Iterable


@dataclass(frozen=True)
class CommitteeDecision:
    decision_id: str
    meeting_period: str
    decision_type: str
    responsible_owner: str
    approval_authority: str
    effective_date: date
    required_actions: tuple[str, ...]
    action_deadline: date
    evidence_refs: tuple[str, ...]
    journal_entry_ref: str
    conditions: tuple[str, ...] = ()
    dissent: tuple[str, ...] = ()
    policy_id: str | None = None
    policy_version: str | None = None
    status: str = "APPROVED"


@dataclass(frozen=True)
class CommitteeDecisionValidation:
    module_id: str
    valid: bool
    findings: tuple[str, ...]
    beneficial_suggestions: tuple[str, ...]


class CapitalCommitteeDecisionsEngine:
    MODULE_ID = "SP-CAPITAL-COMMITTEE-DECISIONS-001"

    def validate(self, decision: CommitteeDecision) -> CommitteeDecisionValidation:
        findings: list[str] = []
        if not decision.decision_id.strip():
            findings.append("DECISION_ID_REQUIRED")
        if not decision.meeting_period.strip():
            findings.append("MEETING_PERIOD_REQUIRED")
        if not decision.decision_type.strip():
            findings.append("DECISION_TYPE_REQUIRED")
        if not decision.responsible_owner.strip():
            findings.append("RESPONSIBLE_OWNER_REQUIRED")
        if not decision.approval_authority.strip():
            findings.append("APPROVAL_AUTHORITY_REQUIRED")
        if not decision.required_actions:
            findings.append("REQUIRED_ACTION_REQUIRED")
        if decision.action_deadline < decision.effective_date:
            findings.append("ACTION_DEADLINE_BEFORE_EFFECTIVE_DATE")
        if not decision.evidence_refs:
            findings.append("EVIDENCE_REFERENCE_REQUIRED")
        if not decision.journal_entry_ref.strip():
            findings.append("JOURNAL_ENTRY_REQUIRED")
        if bool(decision.policy_id) ^ bool(decision.policy_version):
            findings.append("POLICY_ID_VERSION_MUST_BE_PAIRED")

        suggestions = (
            "Link each required action to SP-CAPITAL-ACTION-TRACKER-001 before treating the disposition as operationally complete.",
            "Record material dissent and conditions rather than collapsing committee discussion into a binary approval flag.",
            "Journal amendments, rescissions, or superseding decisions as new entries instead of editing the original disposition.",
            "Do not treat committee approval as a substitute for legal, fiduciary, licensing, perfection, or contractual authority.",
        )
        return CommitteeDecisionValidation(
            module_id=self.MODULE_ID,
            valid=not findings,
            findings=tuple(findings),
            beneficial_suggestions=suggestions,
        )

    def open_action_payloads(self, decision: CommitteeDecision) -> list[dict[str, object]]:
        validation = self.validate(decision)
        if not validation.valid:
            return []
        payloads: list[dict[str, object]] = []
        for index, action in enumerate(decision.required_actions, start=1):
            payloads.append(
                {
                    "action_id": f"{decision.decision_id}-A{index:02d}",
                    "decision_id": decision.decision_id,
                    "owner": decision.responsible_owner,
                    "action": action,
                    "due_date": decision.action_deadline.isoformat(),
                    "evidence_required": True,
                    "status": "OPEN",
                    "journal_entry_ref": decision.journal_entry_ref,
                    "policy_id": decision.policy_id,
                    "policy_version": decision.policy_version,
                }
            )
        return payloads

    def decision_register(self, decisions: Iterable[CommitteeDecision]) -> dict[str, object]:
        records = list(decisions)
        validations = {d.decision_id: self.validate(d) for d in records}
        invalid = [key for key, value in validations.items() if not value.valid]
        return {
            "module_id": self.MODULE_ID,
            "count": len(records),
            "invalid_decision_ids": invalid,
            "open_action_count": sum(len(d.required_actions) for d in records),
            "beneficial_suggestions": [
                "Reconcile the register to monthly committee minutes and the decision journal head hash.",
                "Escalate aged unexecuted decisions into the monthly risk-trend and committee-pack layers.",
            ],
        }

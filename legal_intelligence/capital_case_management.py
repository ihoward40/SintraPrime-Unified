"""SP-CAPITAL-CASE-MANAGEMENT-001 — escalation case ownership and SLA enforcement."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


SEVERITY_SLA_HOURS = {
    "CRITICAL": 4,
    "HIGH": 24,
    "WATCH": 72,
    "NORMAL": 168,
}


@dataclass
class CapitalCase:
    case_id: str
    source_signal_id: str
    facility_id: str
    severity: str
    owner: str
    opened_at: str
    due_at: str
    status: str
    evidence_checklist: list[str] = field(default_factory=list)
    remediation_plan: list[str] = field(default_factory=list)
    closure_authority: str = ""
    reopen_triggers: list[str] = field(default_factory=list)
    satisfied_evidence: list[str] = field(default_factory=list)
    beneficial_suggestions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class CapitalCaseManagementEngine:
    MODULE_ID = "SP-CAPITAL-CASE-MANAGEMENT-001"

    def open_case(self, context: dict[str, Any]) -> CapitalCase:
        severity = str(context.get("severity") or "WATCH").upper()
        if severity not in SEVERITY_SLA_HOURS:
            severity = "WATCH"
        now_raw = context.get("opened_at")
        if now_raw:
            opened = datetime.fromisoformat(str(now_raw).replace("Z", "+00:00"))
            if opened.tzinfo is None:
                opened = opened.replace(tzinfo=timezone.utc)
        else:
            opened = datetime.now(timezone.utc)
        due = opened + timedelta(hours=SEVERITY_SLA_HOURS[severity])
        owner = str(context.get("owner") or "")
        if not owner:
            raise ValueError("CASE_OWNER_REQUIRED")
        closure_authority = str(context.get("closure_authority") or "")
        if not closure_authority:
            raise ValueError("CASE_CLOSURE_AUTHORITY_REQUIRED")
        checklist = list(context.get("evidence_checklist") or [])
        remediation = list(context.get("remediation_plan") or [])
        reopen_triggers = list(context.get("reopen_triggers") or [])
        suggestions = [
            "Use an owner who is accountable for resolution but is not the sole closure authority for HIGH/CRITICAL cases.",
            "Reopen closed cases automatically if the triggering condition recurs or previously accepted evidence is later invalidated.",
        ]
        return CapitalCase(
            case_id=str(context.get("case_id") or ""),
            source_signal_id=str(context.get("source_signal_id") or ""),
            facility_id=str(context.get("facility_id") or ""),
            severity=severity,
            owner=owner,
            opened_at=opened.isoformat(),
            due_at=due.isoformat(),
            status="OPEN",
            evidence_checklist=checklist,
            remediation_plan=remediation,
            closure_authority=closure_authority,
            reopen_triggers=reopen_triggers,
            beneficial_suggestions=suggestions,
        )

    def evaluate(self, case: CapitalCase, *, now: str | None = None) -> dict[str, Any]:
        current = datetime.fromisoformat((now or datetime.now(timezone.utc).isoformat()).replace("Z", "+00:00"))
        due = datetime.fromisoformat(case.due_at.replace("Z", "+00:00"))
        missing = [x for x in case.evidence_checklist if x not in set(case.satisfied_evidence)]
        overdue = current > due and case.status not in {"CLOSED", "CANCELLED"}
        status = "SLA_BREACH" if overdue else case.status
        return {
            "module_id": self.MODULE_ID,
            "case_id": case.case_id,
            "status": status,
            "overdue": overdue,
            "missing_evidence": missing,
            "hours_remaining": max(0, int((due - current).total_seconds() // 3600)),
            "beneficial_suggestions": [
                "Escalate overdue HIGH/CRITICAL cases to Principal review and capital-audit exception handling.",
                "Do not close while required evidence or remediation items remain incomplete.",
            ],
        }

    def can_close(self, case: CapitalCase, *, actor: str, trigger_active: bool = False) -> dict[str, Any]:
        missing = [x for x in case.evidence_checklist if x not in set(case.satisfied_evidence)]
        issues: list[str] = []
        if actor != case.closure_authority:
            issues.append("CLOSURE_AUTHORITY_MISMATCH")
        if missing:
            issues.append("REQUIRED_EVIDENCE_INCOMPLETE")
        if trigger_active:
            issues.append("TRIGGER_CONDITION_STILL_ACTIVE")
        if not case.remediation_plan:
            issues.append("REMEDIATION_PLAN_REQUIRED")
        return {
            "module_id": self.MODULE_ID,
            "can_close": not issues,
            "issues": issues,
            "missing_evidence": missing,
        }

    def should_reopen(self, *, trigger_returned: bool = False, evidence_invalidated: bool = False, override_expired: bool = False) -> dict[str, Any]:
        reasons: list[str] = []
        if trigger_returned:
            reasons.append("TRIGGER_RETURNED")
        if evidence_invalidated:
            reasons.append("EVIDENCE_INVALIDATED")
        if override_expired:
            reasons.append("OVERRIDE_EXPIRED")
        return {"module_id": self.MODULE_ID, "reopen": bool(reasons), "reasons": reasons}

"""SP-CAPITAL-AUDIT-001 — monthly private-capital certification package.

Reconciles the private-capital ledger, dashboard, bank evidence, approvals, collateral
records, servicing exceptions, and journal/anchor evidence into one monthly review.
This is an internal certification control, not an external audit opinion.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class CapitalAuditReport:
    module_id: str
    period: str
    status: str
    reconciliations: dict[str, bool]
    exceptions: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    beneficial_suggestions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class CapitalAuditEngine:
    MODULE_ID = "SP-CAPITAL-AUDIT-001"

    def certify(self, context: dict[str, Any]) -> CapitalAuditReport:
        required = {
            "ledger_to_bank": bool(context.get("ledger_to_bank_reconciled")),
            "ledger_to_dashboard": bool(context.get("ledger_to_dashboard_reconciled")),
            "approvals_complete": bool(context.get("approvals_complete")),
            "collateral_records_current": bool(context.get("collateral_records_current")),
            "servicing_exceptions_reviewed": bool(context.get("servicing_exceptions_reviewed")),
            "journal_chain_valid": bool(context.get("journal_chain_valid")),
            "journal_head_anchored": bool(context.get("journal_head_anchored")),
        }
        exceptions = [f"AUDIT_FAIL:{name}" for name, passed in required.items() if not passed]

        if context.get("unexplained_cash_variance"):
            exceptions.append("UNEXPLAINED_CASH_VARIANCE")
        if context.get("unapproved_override"):
            exceptions.append("UNAPPROVED_OVERRIDE")
        if context.get("stale_collateral_exception"):
            exceptions.append("STALE_COLLATERAL_EXCEPTION")
        if context.get("unresolved_default_notice_issue"):
            exceptions.append("UNRESOLVED_DEFAULT_NOTICE_ISSUE")

        evidence = list(dict.fromkeys(context.get("evidence_refs") or []))
        status = "CERTIFIED" if not exceptions else "EXCEPTION"
        return CapitalAuditReport(
            module_id=self.MODULE_ID,
            period=str(context.get("period") or ""),
            status=status,
            reconciliations=required,
            exceptions=exceptions,
            evidence_refs=evidence,
            beneficial_suggestions=[
                "Require the monthly packet to include bank statements, reconciliation workpapers, facility snapshots, exception aging, collateral-monitor reports, and the journal anchor receipt.",
                "Separate preparer and reviewer roles for material reconciliations whenever staffing permits.",
                "Carry unresolved exceptions forward month-to-month until closed with evidence rather than resetting them at period end.",
                "Hash the completed audit packet and include that hash in the next external journal anchor payload.",
                "Maintain a Principal-approved materiality policy defining which variances require escalation, re-underwriting, or funding suspension.",
            ],
        )

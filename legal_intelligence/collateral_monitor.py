"""SP-COLLATERAL-MONITOR-001 — scheduled collateral integrity monitoring.

Monitors valuation freshness, insurance, title/ownership, lien/perfection evidence,
continuation deadlines, custody/control, and deterioration flags. It does not create
or perfect a security interest by itself.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass
class CollateralMonitorReport:
    module_id: str
    collateral_id: str
    status: str
    findings: list[str] = field(default_factory=list)
    deadlines: list[str] = field(default_factory=list)
    required_actions: list[str] = field(default_factory=list)
    beneficial_suggestions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class CollateralMonitorEngine:
    MODULE_ID = "SP-COLLATERAL-MONITOR-001"

    @staticmethod
    def _days_since(value: str | None) -> int | None:
        if not value:
            return None
        try:
            d = datetime.fromisoformat(value).date()
        except ValueError:
            try:
                d = date.fromisoformat(value)
            except ValueError:
                return None
        return (date.today() - d).days

    def evaluate(self, context: dict[str, Any]) -> CollateralMonitorReport:
        cid = str(context.get("collateral_id") or "")
        findings: list[str] = []
        deadlines: list[str] = []
        actions: list[str] = []

        if not cid:
            findings.append("COLLATERAL_ID_REQUIRED")

        valuation_age = self._days_since(context.get("valuation_date"))
        max_age = int(context.get("max_valuation_age_days") or 180)
        if valuation_age is None:
            findings.append("VALUATION_DATE_MISSING_OR_INVALID")
            actions.append("Obtain current valuation evidence.")
        elif valuation_age > max_age:
            findings.append("VALUATION_STALE")
            actions.append("Revalue collateral before relying on coverage metrics or workout recovery assumptions.")

        if context.get("insurance_required"):
            if not context.get("insurance_verified"):
                findings.append("INSURANCE_NOT_VERIFIED")
                actions.append("Verify policy, named insured/loss payee status, limits, and expiration.")
            expiration = context.get("insurance_expiration")
            if expiration:
                deadlines.append(f"INSURANCE_EXPIRATION:{expiration}")

        if context.get("title_or_ownership_required") and not context.get("title_or_ownership_verified"):
            findings.append("TITLE_OR_OWNERSHIP_NOT_VERIFIED")
            actions.append("Verify ownership/title and reconcile it to the debtor/collateral description.")

        if context.get("secured"):
            if not context.get("security_agreement_verified"):
                findings.append("SECURITY_AGREEMENT_NOT_VERIFIED")
            if not context.get("perfection_status_verified"):
                findings.append("PERFECTION_STATUS_NOT_VERIFIED")
                actions.append("Perform current-law filing/control/possession/perfection review.")
            continuation = context.get("continuation_window_start")
            lapse = context.get("filing_lapse_date")
            if continuation:
                deadlines.append(f"CONTINUATION_WINDOW_START:{continuation}")
            if lapse:
                deadlines.append(f"FILING_LAPSE_DATE:{lapse}")

        if context.get("control_or_custody_required") and not context.get("control_or_custody_verified"):
            findings.append("CONTROL_OR_CUSTODY_NOT_VERIFIED")
            actions.append("Verify possession/control/custody evidence and responsible custodian.")

        if context.get("deterioration_detected"):
            findings.append("COLLATERAL_DETERIORATION")
            actions.append("Revalue, review insurance, test covenant/default implications, and update workout scenarios.")

        status = "EXCEPTION" if findings else "CURRENT"
        return CollateralMonitorReport(
            module_id=self.MODULE_ID,
            collateral_id=cid,
            status=status,
            findings=list(dict.fromkeys(findings)),
            deadlines=list(dict.fromkeys(deadlines)),
            required_actions=list(dict.fromkeys(actions)),
            beneficial_suggestions=[
                "Set review frequency by collateral volatility rather than using one calendar interval for every asset class.",
                "Store valuation source, methodology, appraiser/vendor identity, date, and hash/reference so later changes are explainable.",
                "Track insurance, title, UCC continuation, possession/control, and valuation as separate controls; one cannot substitute for another.",
                "Journal every material collateral revaluation or exception override in the decision hash chain.",
            ],
        )

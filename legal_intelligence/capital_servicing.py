"""SP-CAPITAL-SERVICING-001 — private-capital servicing and workout controls."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ServicingReport:
    module_id: str
    facility_id: str
    status: str
    covenant_breaches: list[str] = field(default_factory=list)
    notice_actions: list[str] = field(default_factory=list)
    workout_options: list[str] = field(default_factory=list)
    collateral_actions: list[str] = field(default_factory=list)
    beneficial_suggestions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class CapitalServicingEngine:
    MODULE_ID = "SP-CAPITAL-SERVICING-001"

    def review(self, context: dict[str, Any]) -> ServicingReport:
        facility_id = str(context.get("facility_id") or "")
        days_past_due = int(context.get("days_past_due") or 0)
        missed_payments = int(context.get("missed_payments") or 0)
        covenant_tests = context.get("covenant_tests") or {}
        collateral_value = float(context.get("collateral_value") or 0)
        principal = float(context.get("principal_outstanding") or 0)
        maturity_passed = bool(context.get("maturity_passed"))
        restructure_requested = bool(context.get("restructure_requested"))

        breaches = [name for name, passed in covenant_tests.items() if passed is False]
        notice_actions: list[str] = []
        workout_options: list[str] = []
        collateral_actions: list[str] = []
        suggestions = [
            "Reconcile payment history to the capital ledger before declaring delinquency or default.",
            "Verify contract notice, cure, governing-law, and service requirements before sending any default notice.",
            "Record every servicing override or restructuring decision in the decision journal hash chain.",
        ]

        if days_past_due > 0 or missed_payments > 0:
            notice_actions.append("Prepare contractual delinquency/cure review; do not send until notice requirements are verified.")
        if days_past_due >= 30:
            notice_actions.append("Escalate to formal workout review and collateral verification.")
        if maturity_passed:
            notice_actions.append("Review maturity/default provisions and any applicable cure or acceleration requirements.")
        if breaches:
            notice_actions.append("Map each covenant breach to the agreement's cure, waiver, reservation, and default provisions.")
        if principal > 0 and collateral_value > 0 and collateral_value / principal < 1.0:
            collateral_actions.append("Obtain a current collateral valuation and test any margin/cure rights before further advances.")
        if context.get("collateral_revaluation_due"):
            collateral_actions.append("Order or document a fresh collateral revaluation using an independent or policy-approved source.")

        if restructure_requested or days_past_due >= 30 or breaches:
            workout_options.extend([
                "temporary payment modification subject to affordability/cash-flow evidence",
                "maturity extension with documented consideration and updated approvals",
                "additional collateral or guaranty if lawful and independently supportable",
                "cash-sweep or enhanced reporting covenant",
                "standstill/forbearance with explicit milestones and expiration",
            ])
            suggestions.append("Compare expected recovery under workout versus enforcement before choosing a path.")
            suggestions.append("Re-underwrite the facility after any material restructure rather than carrying forward the original approval blindly.")

        if days_past_due >= 90 or maturity_passed:
            status = "DEFAULT_REVIEW"
        elif days_past_due >= 30 or breaches:
            status = "WORKOUT_REVIEW"
        elif days_past_due > 0 or missed_payments > 0:
            status = "DELINQUENT"
        else:
            status = "CURRENT"

        return ServicingReport(
            module_id=self.MODULE_ID,
            facility_id=facility_id,
            status=status,
            covenant_breaches=breaches,
            notice_actions=notice_actions,
            workout_options=workout_options,
            collateral_actions=collateral_actions,
            beneficial_suggestions=suggestions,
        )

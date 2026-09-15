"""SP-CREDIT-COMMITTEE-001 — internal underwriting and approval engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class CreditDecision:
    module_id: str
    score: int
    grade: str
    decision: str
    reasons: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    beneficial_suggestions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class CreditCommitteeEngine:
    MODULE_ID = "SP-CREDIT-COMMITTEE-001"

    def evaluate(self, context: dict[str, Any]) -> CreditDecision:
        score = 100
        reasons: list[str] = []
        conditions: list[str] = []
        suggestions: list[str] = []

        dscr = float(context.get("debt_service_coverage_ratio") or 0)
        liquidity_months = float(context.get("liquidity_months") or 0)
        collateral_coverage = float(context.get("collateral_coverage_ratio") or 0)
        borrower_concentration = float(context.get("borrower_concentration_pct") or 0)
        arrears_days = int(context.get("days_past_due") or 0)
        policy_limit = float(context.get("policy_limit") or 0)
        requested = float(context.get("requested_amount") or 0)
        approval_authority = float(context.get("approver_limit") or 0)
        covenant_package = bool(context.get("covenant_package"))
        current_law_verified = bool(context.get("current_law_verified"))
        related_party = bool(context.get("related_party"))
        independent_benefit = bool(context.get("independent_benefit_documented"))

        if dscr < 1.0:
            score -= 35
            reasons.append("Cash flow does not currently cover modeled debt service.")
        elif dscr < 1.25:
            score -= 15
            conditions.append("Require tighter reporting, amortization, or additional support because DSCR is below 1.25x.")

        if liquidity_months < 1:
            score -= 20
            reasons.append("Liquidity is below one month of modeled obligations.")
        elif liquidity_months < 3:
            score -= 8
            conditions.append("Maintain a minimum liquidity covenant or reserve sweep.")

        if context.get("secured") and collateral_coverage < 1.0:
            score -= 25
            reasons.append("Collateral coverage is below funded exposure.")
        elif context.get("secured") and collateral_coverage < 1.25:
            score -= 10
            conditions.append("Require valuation refresh or lower advance amount to restore collateral cushion.")

        if borrower_concentration > 35:
            score -= 15
            reasons.append("Single-borrower concentration exceeds 35% of modeled private-capital exposure.")
            conditions.append("Reduce requested amount or document Principal-approved concentration exception.")

        if arrears_days >= 30:
            score -= 25
            reasons.append("Existing obligation is at least 30 days past due.")
        elif arrears_days > 0:
            score -= 8
            conditions.append("Cure arrears before additional discretionary funding.")

        if policy_limit and requested > policy_limit:
            score -= 30
            reasons.append("Requested amount exceeds transaction policy limit.")
        if approval_authority and requested > approval_authority:
            score -= 30
            reasons.append("Proposed approver lacks delegated authority for the requested amount.")

        if not covenant_package and requested > 0:
            score -= 5
            conditions.append("Add affirmative, negative, reporting, reserve, and default covenants proportionate to the risk.")

        if related_party and not independent_benefit:
            score -= 25
            reasons.append("Related-party transaction lacks documented independent benefit/fair-dealing analysis.")
            conditions.append("Complete SP-RELATED-PARTY-001 before approval.")

        if context.get("interest_bearing") and not current_law_verified:
            score -= 40
            reasons.append("Current governing-law interest/usury/licensing review is incomplete.")

        score = max(0, min(100, score))
        if score >= 80:
            grade, decision = "A", "APPROVE_WITH_DOCUMENTATION"
        elif score >= 65:
            grade, decision = "B", "CONDITIONAL_APPROVAL"
        elif score >= 50:
            grade, decision = "C", "HOLD_FOR_RESTRUCTURE"
        else:
            grade, decision = "D", "DECLINE_OR_PRINCIPAL_EXCEPTION"

        suggestions.extend([
            "Re-run underwriting whenever cash flow, collateral value, repayment status, or concentration changes materially.",
            "Store the score inputs and source documents so a later reviewer can reproduce the decision.",
            "Do not let a high score override licensing, fiduciary, conflict, or current-law compliance gates.",
        ])

        return CreditDecision(self.MODULE_ID, score, grade, decision, reasons, conditions, suggestions)

"""SP-PRIVATE-CAPITAL-001 — Internal Capital & Lawful Credit Engine.

Purpose:
- structure owner/trust/affiliate capital lawfully;
- document internal loans, secured advances, receivables financing, and repayment waterfalls;
- force current-law review for interest/usury, licensing, securities, tax, fiduciary, and consumer-credit boundaries;
- block public-facing lending or customer-money activity until licensing/partner review is complete.

This module does not treat a trust, UCC filing, note, or internal treasury policy as a banking charter.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class CapitalDecision(str, Enum):
    PASS = "PASS"
    PASS_WITH_CONDITIONS = "PASS_WITH_CONDITIONS"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class CapitalFinding:
    code: str
    message: str
    blocking: bool = False


@dataclass
class CapitalReport:
    module_id: str
    decision: CapitalDecision
    transaction_class: str
    required_documents: list[str] = field(default_factory=list)
    legal_reviews: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    repayment_waterfall: list[str] = field(default_factory=list)
    beneficial_suggestions: list[str] = field(default_factory=list)
    findings: list[CapitalFinding] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "module_id": self.module_id,
            "decision": self.decision.value,
            "transaction_class": self.transaction_class,
            "required_documents": self.required_documents,
            "legal_reviews": self.legal_reviews,
            "risk_flags": self.risk_flags,
            "repayment_waterfall": self.repayment_waterfall,
            "beneficial_suggestions": self.beneficial_suggestions,
            "findings": [asdict(x) for x in self.findings],
        }


class PrivateCapitalEngine:
    """Classify and control internal capital before funds move."""

    MODULE_ID = "SP-PRIVATE-CAPITAL-001"

    INTERNAL_CLASSES = {
        "owner_capital_contribution",
        "owner_loan",
        "trust_to_affiliate_loan",
        "affiliate_to_affiliate_loan",
        "secured_internal_advance",
        "receivables_financing_internal",
    }

    PUBLIC_OR_REGULATED_CLASSES = {
        "consumer_lending",
        "public_business_lending",
        "deposit_taking",
        "customer_fund_custody",
        "money_transmission",
        "stored_value",
        "bill_pay_for_customers",
        "debt_adjustment",
    }

    def evaluate(self, context: dict[str, Any]) -> CapitalReport:
        tx = self._text(context.get("transaction_class")).lower()
        parties = context.get("parties") or []
        amount = context.get("amount")
        interest_rate = context.get("interest_rate")
        collateral = context.get("collateral") or []
        related = bool(context.get("related_parties"))
        public_facing = bool(context.get("public_facing"))
        consumer = bool(context.get("consumer_borrower"))
        holds_customer_funds = bool(context.get("holds_customer_funds"))
        verified_current_law = bool(context.get("current_law_verified"))
        licensed_or_partnered = bool(context.get("licensed_or_regulated_partner"))

        findings: list[CapitalFinding] = []
        required_documents: list[str] = []
        legal_reviews: list[str] = []
        risk_flags: list[str] = []
        suggestions: list[str] = []

        if not tx:
            findings.append(CapitalFinding("PC001_CLASS_REQUIRED", "transaction_class is required", True))
            tx = "unclassified"

        if not parties:
            findings.append(CapitalFinding("PC002_PARTIES_REQUIRED", "actual legal parties and capacities must be identified", True))

        if amount in {None, ""}:
            findings.append(CapitalFinding("PC003_AMOUNT_REQUIRED", "funded amount or maximum facility amount must be identified", True))

        if tx in self.PUBLIC_OR_REGULATED_CLASSES or public_facing or consumer or holds_customer_funds:
            risk_flags.append("REGULATED_ACTIVITY_REVIEW_REQUIRED")
            legal_reviews.extend([
                "state lending/license review",
                "interest/usury and fee review",
                "federal consumer-credit applicability review",
                "money-transmission/customer-funds review if funds flow through IKE",
            ])
            if not licensed_or_partnered:
                findings.append(
                    CapitalFinding(
                        "PC010_LICENSE_FIREWALL",
                        "Public-facing or customer-money activity is blocked until required licensing or regulated-partner authority is verified",
                        True,
                    )
                )

        if interest_rate not in {None, ""}:
            legal_reviews.append("current jurisdiction-specific interest/usury/fee-cap review")
            if not verified_current_law:
                findings.append(
                    CapitalFinding(
                        "PC011_RATE_VERIFICATION",
                        "Interest-bearing credit may not be approved until current governing-law rate, fee, exemption, and licensing rules are verified",
                        True,
                    )
                )

        if tx == "owner_capital_contribution":
            required_documents.extend([
                "capital contribution memo",
                "ownership/equity ledger entry",
                "funding proof",
                "tax/accounting classification",
            ])
        elif tx in self.INTERNAL_CLASSES:
            required_documents.extend([
                "written promissory note or facility agreement",
                "purpose and use-of-proceeds memo",
                "authorization/resolution or trustee approval",
                "funding proof",
                "repayment ledger",
                "tax/accounting treatment memo",
            ])

        if related:
            legal_reviews.extend([
                "related-party fair-dealing and fiduciary-duty review",
                "tax/accounting treatment and imputed-interest review where applicable",
            ])
            required_documents.append("related-party approval/conflict record")

        if collateral:
            required_documents.extend([
                "security agreement with specific collateral description",
                "debtor rights/ownership evidence",
                "perfection/priority analysis",
            ])
            legal_reviews.append("Article 9 attachment, perfection, priority, and filing-location review")

        if "receivables_financing" in tx:
            required_documents.extend([
                "receivables schedule",
                "eligibility criteria",
                "aging report",
                "advance-rate formula",
                "dilution/chargeback policy",
                "collection-control agreement if used",
            ])
            suggestions.append("Use a borrowing-base certificate so advances never exceed the approved percentage of eligible receivables.")

        repayment_waterfall = [
            "1. transaction taxes/mandatory pass-through amounts",
            "2. ordinary operating obligations needed to preserve the financed asset or receivable pool",
            "3. accrued permitted interest/fees, if lawfully documented",
            "4. scheduled principal",
            "5. reserve replenishment",
            "6. subordinate affiliate/owner balances",
            "7. discretionary distributions only after covenant/reserve tests pass",
        ]

        suggestions.extend([
            "Create a written capital-allocation policy with per-transaction and aggregate exposure limits.",
            "Require dual approval for related-party advances above a Principal-set threshold.",
            "Maintain a 13-week liquidity forecast and minimum reserve floor before approving new advances.",
            "Add covenant tests for delinquency, concentration, collateral value, and reserve breaches.",
            "Generate a monthly private-capital certificate showing balances, arrears, collateral status, and exceptions.",
            "For any transaction touching consumers or the public, route through licensing review before marketing, funding, or collecting.",
        ])

        blockers = [x for x in findings if x.blocking]
        if blockers:
            decision = CapitalDecision.BLOCK
        elif legal_reviews:
            decision = CapitalDecision.PASS_WITH_CONDITIONS
        else:
            decision = CapitalDecision.PASS

        return CapitalReport(
            module_id=self.MODULE_ID,
            decision=decision,
            transaction_class=tx,
            required_documents=self._dedupe(required_documents),
            legal_reviews=self._dedupe(legal_reviews),
            risk_flags=self._dedupe(risk_flags),
            repayment_waterfall=repayment_waterfall,
            beneficial_suggestions=self._dedupe(suggestions),
            findings=findings,
        )

    @staticmethod
    def reserve_requirement(context: dict[str, Any]) -> dict[str, Any]:
        """Return a policy-oriented reserve calculation; not a legal minimum."""
        monthly_fixed = float(context.get("monthly_fixed_obligations") or 0)
        target_months = float(context.get("target_reserve_months") or 3)
        committed_undrawn = float(context.get("committed_undrawn_advances") or 0)
        tax_reserve = float(context.get("tax_reserve_required") or 0)
        minimum = (monthly_fixed * target_months) + committed_undrawn + tax_reserve
        return {
            "policy_reserve_floor": round(minimum, 2),
            "components": {
                "operating_reserve": round(monthly_fixed * target_months, 2),
                "committed_undrawn": round(committed_undrawn, 2),
                "tax_reserve": round(tax_reserve, 2),
            },
            "caveat": "This is an internal policy calculation, not a statutory capital or bank reserve requirement.",
        }

    @staticmethod
    def _text(value: Any) -> str:
        return value.strip() if isinstance(value, str) else ""

    @staticmethod
    def _dedupe(items: list[str]) -> list[str]:
        return list(dict.fromkeys(items))

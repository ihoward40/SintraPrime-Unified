"""SP-RECEIVABLES-001 — receivables eligibility and borrowing-base engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Receivable:
    receivable_id: str
    customer: str
    amount: float
    days_outstanding: int
    disputed: bool = False
    affiliate: bool = False
    contra_or_setoff_risk: bool = False


@dataclass
class BorrowingBaseReport:
    module_id: str
    gross_receivables: float
    eligible_receivables: float
    borrowing_base: float
    current_advance: float
    overadvance: float
    concentration_pct: float
    dilution_pct: float
    ineligible: list[dict[str, Any]] = field(default_factory=list)
    beneficial_suggestions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class ReceivablesEngine:
    MODULE_ID = "SP-RECEIVABLES-001"

    def calculate(self, context: dict[str, Any]) -> BorrowingBaseReport:
        raw = context.get("receivables") or []
        advance_rate = float(context.get("advance_rate") or 0.80)
        max_age = int(context.get("max_eligible_days") or 90)
        concentration_limit = float(context.get("customer_concentration_limit_pct") or 25)
        current_advance = float(context.get("current_advance") or 0)
        trailing_sales = float(context.get("trailing_credit_sales") or 0)
        dilution_amount = float(context.get("trailing_dilution") or 0)

        receivables = [
            Receivable(
                receivable_id=str(x.get("receivable_id") or ""),
                customer=str(x.get("customer") or ""),
                amount=float(x.get("amount") or 0),
                days_outstanding=int(x.get("days_outstanding") or 0),
                disputed=bool(x.get("disputed")),
                affiliate=bool(x.get("affiliate")),
                contra_or_setoff_risk=bool(x.get("contra_or_setoff_risk")),
            )
            for x in raw if isinstance(x, dict)
        ]

        gross = sum(x.amount for x in receivables)
        eligible: list[Receivable] = []
        ineligible: list[dict[str, Any]] = []
        for item in receivables:
            reason = None
            if item.days_outstanding > max_age:
                reason = "AGED_OVER_LIMIT"
            elif item.disputed:
                reason = "DISPUTED"
            elif item.affiliate:
                reason = "AFFILIATE_RECEIVABLE"
            elif item.contra_or_setoff_risk:
                reason = "SETOFF_OR_CONTRA_RISK"
            if reason:
                ineligible.append({"receivable_id": item.receivable_id, "reason": reason, "amount": item.amount})
            else:
                eligible.append(item)

        by_customer: dict[str, float] = {}
        for item in eligible:
            by_customer[item.customer] = by_customer.get(item.customer, 0) + item.amount
        eligible_total = sum(x.amount for x in eligible)
        largest = max(by_customer.values(), default=0)
        concentration_pct = (largest / eligible_total * 100) if eligible_total else 0

        concentration_haircut = 0.0
        if eligible_total and concentration_pct > concentration_limit:
            allowed_largest = eligible_total * concentration_limit / 100
            concentration_haircut = max(0.0, largest - allowed_largest)

        adjusted_eligible = max(0.0, eligible_total - concentration_haircut)
        borrowing_base = adjusted_eligible * advance_rate
        overadvance = max(0.0, current_advance - borrowing_base)
        dilution_pct = (dilution_amount / trailing_sales * 100) if trailing_sales else 0

        suggestions = [
            "Refresh the borrowing base at least monthly and more frequently when collections deteriorate.",
            "Require source invoices, proof of performance/delivery, and cash-application reconciliation for large receivables.",
        ]
        if concentration_pct > concentration_limit:
            suggestions.append("Reduce advance availability for customer concentration or obtain Principal-approved concentration treatment.")
        if dilution_pct > 5:
            suggestions.append("Investigate returns, credits, disputes, write-offs, and billing errors driving dilution before increasing the advance rate.")
        if overadvance > 0:
            suggestions.append("Freeze discretionary new advances and require cure, additional eligible collateral, or a documented restructuring.")

        return BorrowingBaseReport(
            module_id=self.MODULE_ID,
            gross_receivables=round(gross, 2),
            eligible_receivables=round(adjusted_eligible, 2),
            borrowing_base=round(borrowing_base, 2),
            current_advance=round(current_advance, 2),
            overadvance=round(overadvance, 2),
            concentration_pct=round(concentration_pct, 2),
            dilution_pct=round(dilution_pct, 2),
            ineligible=ineligible,
            beneficial_suggestions=suggestions,
        )

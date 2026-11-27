"""SP-CAPITAL-RISK-001 — private-capital portfolio risk and concentration controls."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class CapitalRiskReport:
    module_id: str
    decision: str
    total_exposure: float
    limit_breaches: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    beneficial_suggestions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class CapitalRiskEngine:
    MODULE_ID = "SP-CAPITAL-RISK-001"

    def evaluate(self, context: dict[str, Any]) -> CapitalRiskReport:
        exposures = context.get("exposures") or []
        total = sum(float(x.get("amount") or 0) for x in exposures if isinstance(x, dict))
        max_single = float(context.get("max_single_borrower_pct") or 25)
        max_affiliate = float(context.get("max_affiliate_group_pct") or 40)
        max_collateral_class = float(context.get("max_collateral_class_pct") or 50)
        max_receivable_customer = float(context.get("max_receivable_customer_pct") or 25)
        reserve_available = float(context.get("reserve_available") or 0)
        reserve_required = float(context.get("reserve_required") or 0)

        breaches: list[str] = []
        warnings: list[str] = []
        suggestions: list[str] = []

        by_borrower: dict[str, float] = {}
        by_group: dict[str, float] = {}
        by_collateral: dict[str, float] = {}
        by_customer: dict[str, float] = {}

        for row in exposures:
            if not isinstance(row, dict):
                continue
            amount = float(row.get("amount") or 0)
            borrower = str(row.get("borrower") or "UNSPECIFIED")
            group = str(row.get("affiliate_group") or borrower)
            collateral = str(row.get("collateral_class") or "UNSECURED")
            customer = str(row.get("receivable_customer") or "")
            by_borrower[borrower] = by_borrower.get(borrower, 0) + amount
            by_group[group] = by_group.get(group, 0) + amount
            by_collateral[collateral] = by_collateral.get(collateral, 0) + amount
            if customer:
                by_customer[customer] = by_customer.get(customer, 0) + amount

        def pct(amount: float) -> float:
            return (amount / total * 100) if total else 0.0

        for borrower, amount in by_borrower.items():
            if pct(amount) > max_single:
                breaches.append(f"SINGLE_BORROWER_LIMIT:{borrower}:{pct(amount):.2f}%")
        for group, amount in by_group.items():
            if pct(amount) > max_affiliate:
                breaches.append(f"AFFILIATE_GROUP_LIMIT:{group}:{pct(amount):.2f}%")
        for cls, amount in by_collateral.items():
            if pct(amount) > max_collateral_class:
                breaches.append(f"COLLATERAL_CLASS_LIMIT:{cls}:{pct(amount):.2f}%")
        for customer, amount in by_customer.items():
            if pct(amount) > max_receivable_customer:
                breaches.append(f"RECEIVABLE_CUSTOMER_LIMIT:{customer}:{pct(amount):.2f}%")

        if reserve_available < reserve_required:
            breaches.append("RESERVE_FLOOR_BREACH")
        elif reserve_required and reserve_available < reserve_required * 1.25:
            warnings.append("RESERVE_HEADROOM_BELOW_25_PERCENT")

        if total == 0:
            warnings.append("NO_EXPOSURE_DATA")

        decision = "BLOCK_NEW_ADVANCES" if breaches else "PASS_WITH_WARNINGS" if warnings else "PASS"
        suggestions.extend([
            "Run concentration testing before every new advance and after every material repayment, write-down, or collateral revaluation.",
            "Set Principal-approved hard limits and lower warning thresholds so the system escalates before a breach occurs.",
            "Track committed-but-undrawn facilities separately from funded balances and include them in liquidity stress tests.",
        ])
        if breaches:
            suggestions.append("Do not cure concentration breaches with bookkeeping reclassification; reduce exposure, add capital/reserves, diversify, or approve a documented exception with exit plan.")

        return CapitalRiskReport(
            module_id=self.MODULE_ID,
            decision=decision,
            total_exposure=round(total, 2),
            limit_breaches=breaches,
            warnings=warnings,
            beneficial_suggestions=suggestions,
        )

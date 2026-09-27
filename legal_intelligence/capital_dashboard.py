"""SP-CAPITAL-DASHBOARD-001 — monthly private-capital command dashboard."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class CapitalDashboardReport:
    module_id: str
    as_of: str
    total_exposure: float
    available_liquidity: float
    reserve_available: float
    reserve_required: float
    reserve_shortfall: float
    delinquent_exposure: float
    weighted_collateral_coverage: float | None
    borrowing_base_available: float
    concentration_flags: list[str] = field(default_factory=list)
    covenant_breaches: list[str] = field(default_factory=list)
    aged_exceptions: list[str] = field(default_factory=list)
    beneficial_suggestions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class CapitalDashboardEngine:
    MODULE_ID = "SP-CAPITAL-DASHBOARD-001"

    def build(self, context: dict[str, Any]) -> CapitalDashboardReport:
        facilities = context.get("facilities") or []
        total_exposure = sum(float(x.get("principal_outstanding") or 0) for x in facilities)
        delinquent_exposure = sum(
            float(x.get("principal_outstanding") or 0)
            for x in facilities
            if int(x.get("days_past_due") or 0) > 0
        )
        collateral_total = sum(float(x.get("collateral_value") or 0) for x in facilities)
        coverage = None if total_exposure <= 0 else round(collateral_total / total_exposure, 4)
        reserve_available = float(context.get("reserve_available") or 0)
        reserve_required = float(context.get("reserve_required") or 0)
        reserve_shortfall = max(0.0, reserve_required - reserve_available)
        liquidity = float(context.get("available_liquidity") or 0)
        borrowing_base_available = float(context.get("borrowing_base_available") or 0)

        concentration_flags = list(dict.fromkeys(context.get("concentration_flags") or []))
        covenant_breaches: list[str] = []
        aged_exceptions: list[str] = []
        for facility in facilities:
            fid = str(facility.get("facility_id") or "UNKNOWN")
            for covenant in facility.get("covenant_breaches") or []:
                covenant_breaches.append(f"{fid}: {covenant}")
            for exc in facility.get("exceptions") or []:
                age = int(exc.get("age_days") or 0) if isinstance(exc, dict) else 0
                code = exc.get("code") if isinstance(exc, dict) else str(exc)
                if age >= 30:
                    aged_exceptions.append(f"{fid}: {code} ({age}d)")

        suggestions = [
            "Certify dashboard inputs back to the capital ledger, bank statements, receivables report, and latest collateral valuations before Principal review.",
            "Track month-over-month movement for exposure, liquidity, reserve coverage, delinquency, and concentration rather than relying on one-period snapshots.",
        ]
        if reserve_shortfall > 0:
            suggestions.append("Freeze discretionary new advances until the reserve shortfall is cured or a documented Principal override is approved.")
        if delinquent_exposure > 0:
            suggestions.append("Route delinquent facilities through SP-CAPITAL-SERVICING-001 and age workout actions to closure.")
        if concentration_flags:
            suggestions.append("Reduce or hedge concentration before approving new exposure to the flagged borrower, affiliate group, customer, or collateral class.")
        if aged_exceptions:
            suggestions.append("Escalate exceptions older than 30 days to a named owner with a cure date and decision-journal entry.")

        return CapitalDashboardReport(
            module_id=self.MODULE_ID,
            as_of=str(context.get("as_of") or ""),
            total_exposure=round(total_exposure, 2),
            available_liquidity=round(liquidity, 2),
            reserve_available=round(reserve_available, 2),
            reserve_required=round(reserve_required, 2),
            reserve_shortfall=round(reserve_shortfall, 2),
            delinquent_exposure=round(delinquent_exposure, 2),
            weighted_collateral_coverage=coverage,
            borrowing_base_available=round(borrowing_base_available, 2),
            concentration_flags=concentration_flags,
            covenant_breaches=list(dict.fromkeys(covenant_breaches)),
            aged_exceptions=aged_exceptions,
            beneficial_suggestions=suggestions,
        )

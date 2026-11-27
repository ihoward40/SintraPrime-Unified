"""SP-CAPITAL-STRESS-001 — private-capital stress testing engine.

Applies scenario shocks to collateral, collections, delinquency, liquidity, reserves,
and customer concentration to estimate remaining deployable-capital headroom.
Policy outputs are internal risk controls, not regulatory bank-capital calculations.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class StressResult:
    module_id: str
    scenario_name: str
    stressed_collateral_value: float
    stressed_collections: float
    stressed_liquidity: float
    stressed_reserves: float
    stressed_delinquent_exposure: float
    stressed_top_customer_concentration: float
    reserve_headroom: float
    liquidity_headroom: float
    concentration_headroom: float
    safe_deployable_capital: float
    breaches: list[str] = field(default_factory=list)
    beneficial_suggestions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class CapitalStressEngine:
    MODULE_ID = "SP-CAPITAL-STRESS-001"

    def evaluate(self, context: dict[str, Any]) -> StressResult:
        scenario = str(context.get("scenario_name") or "custom")
        collateral = float(context.get("collateral_value") or 0)
        collections = float(context.get("expected_collections") or 0)
        liquidity = float(context.get("available_liquidity") or 0)
        reserves = float(context.get("available_reserves") or 0)
        delinquent = float(context.get("delinquent_exposure") or 0)
        top_customer = float(context.get("top_customer_exposure") or 0)
        total_exposure = float(context.get("total_exposure") or 0)

        collateral_shock = float(context.get("collateral_value_shock_pct") or 0) / 100
        collection_shock = float(context.get("collection_rate_shock_pct") or 0) / 100
        liquidity_shock = float(context.get("liquidity_shock_pct") or 0) / 100
        delinquency_shock = float(context.get("delinquency_increase_pct") or 0) / 100
        concentration_shock = float(context.get("top_customer_exposure_increase_pct") or 0) / 100

        reserve_floor = float(context.get("reserve_floor") or 0)
        minimum_liquidity = float(context.get("minimum_liquidity") or 0)
        max_top_customer_pct = float(context.get("max_top_customer_pct") or 100)

        stressed_collateral = max(0.0, collateral * (1 - collateral_shock))
        stressed_collections = max(0.0, collections * (1 - collection_shock))
        stressed_liquidity = max(0.0, liquidity * (1 - liquidity_shock))
        stressed_delinquent = max(0.0, delinquent * (1 + delinquency_shock))
        stressed_top_customer = max(0.0, top_customer * (1 + concentration_shock))

        stressed_reserves = max(0.0, reserves + stressed_collections - stressed_delinquent)
        reserve_headroom = stressed_reserves - reserve_floor
        liquidity_headroom = stressed_liquidity - minimum_liquidity

        stressed_total = max(total_exposure, stressed_top_customer)
        allowed_top_customer = stressed_total * (max_top_customer_pct / 100)
        concentration_headroom = allowed_top_customer - stressed_top_customer

        safe_deployable = max(0.0, min(reserve_headroom, liquidity_headroom, concentration_headroom))

        breaches: list[str] = []
        if reserve_headroom < 0:
            breaches.append("RESERVE_FLOOR_BREACH")
        if liquidity_headroom < 0:
            breaches.append("LIQUIDITY_MINIMUM_BREACH")
        if concentration_headroom < 0:
            breaches.append("CUSTOMER_CONCENTRATION_BREACH")
        if total_exposure > 0 and stressed_collateral < total_exposure:
            breaches.append("COLLATERAL_COVERAGE_BREACH")

        suggestions = [
            "Run base, moderate, severe, and reverse-stress scenarios monthly and before large new advances.",
            "Set Principal-approved response triggers for each breach rather than relying on ad hoc reactions.",
            "Use the lowest headroom across reserve, liquidity, and concentration constraints as the deployable-capital ceiling.",
        ]
        if breaches:
            suggestions.append("Suspend discretionary new deployment until breached limits are cured or a documented exception is independently approved.")

        return StressResult(
            module_id=self.MODULE_ID,
            scenario_name=scenario,
            stressed_collateral_value=round(stressed_collateral, 2),
            stressed_collections=round(stressed_collections, 2),
            stressed_liquidity=round(stressed_liquidity, 2),
            stressed_reserves=round(stressed_reserves, 2),
            stressed_delinquent_exposure=round(stressed_delinquent, 2),
            stressed_top_customer_concentration=round(stressed_top_customer, 2),
            reserve_headroom=round(reserve_headroom, 2),
            liquidity_headroom=round(liquidity_headroom, 2),
            concentration_headroom=round(concentration_headroom, 2),
            safe_deployable_capital=round(safe_deployable, 2),
            breaches=breaches,
            beneficial_suggestions=suggestions,
        )

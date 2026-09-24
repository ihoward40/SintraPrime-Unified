"""SP-WORKOUT-RECOVERY-001 — compare restructure vs enforcement recovery.

Provides scenario analysis for internal/private-capital workouts. It does not authorize
repossession, collection, acceleration, foreclosure, or other enforcement action.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class RecoveryScenario:
    name: str
    gross_recovery: float
    direct_costs: float
    delay_months: float
    probability: float
    collateral_loss: float = 0.0
    tax_or_fee_cost: float = 0.0
    legal_review_required: bool = False

    @property
    def expected_net_recovery(self) -> float:
        net = self.gross_recovery - self.direct_costs - self.collateral_loss - self.tax_or_fee_cost
        return round(max(0.0, net) * max(0.0, min(1.0, self.probability)), 2)

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["expected_net_recovery"] = self.expected_net_recovery
        return data


class WorkoutRecoveryEngine:
    MODULE_ID = "SP-WORKOUT-RECOVERY-001"

    def compare(self, context: dict[str, Any]) -> dict[str, Any]:
        scenarios: list[RecoveryScenario] = []
        for raw in context.get("scenarios") or []:
            scenarios.append(RecoveryScenario(
                name=str(raw.get("name") or "unnamed"),
                gross_recovery=float(raw.get("gross_recovery") or 0),
                direct_costs=float(raw.get("direct_costs") or 0),
                delay_months=float(raw.get("delay_months") or 0),
                probability=float(raw.get("probability") or 0),
                collateral_loss=float(raw.get("collateral_loss") or 0),
                tax_or_fee_cost=float(raw.get("tax_or_fee_cost") or 0),
                legal_review_required=bool(raw.get("legal_review_required")),
            ))

        ranked = sorted(scenarios, key=lambda x: (-x.expected_net_recovery, x.delay_months, x.name))
        findings: list[str] = []
        if not ranked:
            findings.append("NO_RECOVERY_SCENARIOS")
        if not context.get("current_balance_verified"):
            findings.append("CURRENT_BALANCE_NOT_VERIFIED")
        if context.get("secured") and not context.get("collateral_value_verified"):
            findings.append("COLLATERAL_VALUE_NOT_VERIFIED")
        if any(s.legal_review_required for s in ranked) and not context.get("current_law_verified"):
            findings.append("ENFORCEMENT_CURRENT_LAW_REVIEW_REQUIRED")

        recommended = ranked[0].name if ranked and not findings else None
        return {
            "module_id": self.MODULE_ID,
            "decision": "COMPARE_ONLY" if ranked else "BLOCK",
            "recommended_scenario": recommended,
            "scenarios": [x.as_dict() for x in ranked],
            "findings": findings,
            "beneficial_suggestions": [
                "Include a do-nothing/baseline scenario so the committee can compare action against expected natural recovery.",
                "Stress-test recovery assumptions at lower collateral values, longer timelines, and lower collection probabilities.",
                "Require Principal approval before selecting a workout path that changes maturity, interest, collateral, guarantees, or enforcement posture.",
                "Re-run underwriting and related-party review after any material restructure.",
                "Track actual workout cash flows against the approved scenario so future recovery assumptions improve over time.",
            ],
            "caveat": "Highest modeled recovery is not automatic authority to enforce. Contract, fiduciary, notice, licensing, bankruptcy, and current-law constraints remain controlling.",
        }

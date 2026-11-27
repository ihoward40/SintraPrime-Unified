"""Management-information trend engine for private-capital governance.

Tracks whether risk indicators are improving, deteriorating, or being deferred through
repeated waivers and overrides. Internal management control only; not a bank regulatory
report or external audit opinion.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any


def _d(value: Any) -> Decimal:
    return Decimal(str(value or 0))


@dataclass(frozen=True)
class RiskTrendPoint:
    period: str
    sla_breaches: int = 0
    reopened_cases: int = 0
    overrides: int = 0
    waivers: int = 0
    aged_waivers: int = 0
    collateral_coverage: Decimal = Decimal("0")
    reserve_headroom: Decimal = Decimal("0")
    policy_exceptions: int = 0
    top_concentration_pct: Decimal = Decimal("0")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RiskTrendReport:
    module_id: str
    direction: str
    deterioration_flags: tuple[str, ...]
    improvement_flags: tuple[str, ...]
    waiver_dependency_score: int
    current_period: dict[str, Any]
    deltas: dict[str, Any]
    beneficial_suggestions: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class CapitalRiskTrendsEngine:
    MODULE_ID = "SP-CAPITAL-RISK-TRENDS-001"

    def analyze(self, history: list[dict[str, Any]]) -> RiskTrendReport:
        if not history:
            return RiskTrendReport(
                module_id=self.MODULE_ID,
                direction="NO_DATA",
                deterioration_flags=("NO_HISTORY",),
                improvement_flags=(),
                waiver_dependency_score=0,
                current_period={},
                deltas={},
                beneficial_suggestions=(
                    "Load at least two monthly snapshots before drawing trend conclusions.",
                    "Preserve source references for each metric so the trend report can be reconstructed.",
                ),
            )

        rows = [self._normalize(row) for row in history]
        current = rows[-1]
        previous = rows[-2] if len(rows) > 1 else rows[-1]

        deltas = {
            "sla_breaches": current["sla_breaches"] - previous["sla_breaches"],
            "reopened_cases": current["reopened_cases"] - previous["reopened_cases"],
            "overrides": current["overrides"] - previous["overrides"],
            "waivers": current["waivers"] - previous["waivers"],
            "aged_waivers": current["aged_waivers"] - previous["aged_waivers"],
            "collateral_coverage": current["collateral_coverage"] - previous["collateral_coverage"],
            "reserve_headroom": current["reserve_headroom"] - previous["reserve_headroom"],
            "policy_exceptions": current["policy_exceptions"] - previous["policy_exceptions"],
            "top_concentration_pct": current["top_concentration_pct"] - previous["top_concentration_pct"],
        }

        deterioration: list[str] = []
        improvement: list[str] = []

        for key in ("sla_breaches", "reopened_cases", "overrides", "waivers", "aged_waivers", "policy_exceptions", "top_concentration_pct"):
            if deltas[key] > 0:
                deterioration.append(f"{key.upper()}_WORSENING")
            elif deltas[key] < 0:
                improvement.append(f"{key.upper()}_IMPROVING")

        for key in ("collateral_coverage", "reserve_headroom"):
            if deltas[key] < 0:
                deterioration.append(f"{key.upper()}_ERODING")
            elif deltas[key] > 0:
                improvement.append(f"{key.upper()}_IMPROVING")

        waiver_dependency = min(
            100,
            int(current["overrides"] * 8 + current["waivers"] * 8 + current["aged_waivers"] * 12 + current["policy_exceptions"] * 5),
        )
        if waiver_dependency >= 60:
            deterioration.append("WAIVER_DEPENDENCY_HIGH")
        elif waiver_dependency >= 30:
            deterioration.append("WAIVER_DEPENDENCY_ELEVATED")

        if len(deterioration) > len(improvement):
            direction = "DETERIORATING"
        elif len(improvement) > len(deterioration):
            direction = "IMPROVING"
        else:
            direction = "MIXED_OR_STABLE"

        suggestions = [
            "Review recurring overrides and waivers as a portfolio-level risk theme, not only case-by-case exceptions.",
            "Require management commentary for every month classified as DETERIORATING.",
            "Link trend movements to source dashboard, case, collateral, override, and audit records.",
        ]
        if waiver_dependency >= 30:
            suggestions.append("Test whether policy thresholds are unrealistic or whether risk is being deferred through repeated exceptions.")
        if current["sla_breaches"] > 0 or current["reopened_cases"] > 0:
            suggestions.append("Escalate persistent SLA breaches and reopened cases to committee with named owners and cure dates.")

        return RiskTrendReport(
            module_id=self.MODULE_ID,
            direction=direction,
            deterioration_flags=tuple(deterioration),
            improvement_flags=tuple(improvement),
            waiver_dependency_score=waiver_dependency,
            current_period=self._serialize(current),
            deltas=self._serialize(deltas),
            beneficial_suggestions=tuple(suggestions),
        )

    @staticmethod
    def _normalize(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "period": str(row.get("period", "")),
            "sla_breaches": int(row.get("sla_breaches", 0)),
            "reopened_cases": int(row.get("reopened_cases", 0)),
            "overrides": int(row.get("overrides", 0)),
            "waivers": int(row.get("waivers", 0)),
            "aged_waivers": int(row.get("aged_waivers", 0)),
            "collateral_coverage": _d(row.get("collateral_coverage")),
            "reserve_headroom": _d(row.get("reserve_headroom")),
            "policy_exceptions": int(row.get("policy_exceptions", 0)),
            "top_concentration_pct": _d(row.get("top_concentration_pct")),
        }

    @staticmethod
    def _serialize(value: dict[str, Any]) -> dict[str, Any]:
        return {k: float(v) if isinstance(v, Decimal) else v for k, v in value.items()}

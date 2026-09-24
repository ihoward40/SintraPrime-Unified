"""Champion/challenger shadow testing for governed capital rules.

SP-CAPITAL-CHAMPION-CHALLENGER-001 compares an active champion rule with a
proposed challenger in shadow mode. Shadow performance never confers production
authority; promotion requires separate governed approval and dependency review.
"""

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class RuleTestObservation:
    observation_id: str
    bad_outcome_observed: bool
    champion_triggered: bool
    challenger_triggered: bool
    champion_latency_ms: int | None = None
    challenger_latency_ms: int | None = None
    champion_operational_cost: float = 0.0
    challenger_operational_cost: float = 0.0
    observation_complete: bool = True


@dataclass(frozen=True)
class RulePerformance:
    sample_size: int
    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int
    precision: float | None
    recall: float | None
    false_positive_rate: float | None
    false_negative_rate: float | None
    average_latency_ms: float | None
    average_operational_cost: float


@dataclass(frozen=True)
class ChampionChallengerReport:
    module_id: str
    champion_rule_id: str
    champion_version: str
    challenger_rule_id: str
    challenger_version: str
    champion: RulePerformance
    challenger: RulePerformance
    recommendation: str
    production_authority: bool
    findings: tuple[str, ...]
    beneficial_suggestions: tuple[str, ...]


class CapitalChampionChallengerEngine:
    MODULE_ID = "SP-CAPITAL-CHAMPION-CHALLENGER-001"

    def compare(
        self,
        *,
        champion_rule_id: str,
        champion_version: str,
        challenger_rule_id: str,
        challenger_version: str,
        observations: Iterable[RuleTestObservation],
        minimum_complete_observations: int = 20,
        max_false_negative_regression: float = 0.0,
        max_false_positive_regression: float = 0.05,
    ) -> ChampionChallengerReport:
        complete = [row for row in observations if row.observation_complete]
        findings: list[str] = []

        required = {
            "CHAMPION_RULE_ID_REQUIRED": champion_rule_id,
            "CHAMPION_VERSION_REQUIRED": champion_version,
            "CHALLENGER_RULE_ID_REQUIRED": challenger_rule_id,
            "CHALLENGER_VERSION_REQUIRED": challenger_version,
        }
        for code, value in required.items():
            if not str(value).strip():
                findings.append(code)

        champion = self._performance(complete, use_challenger=False)
        challenger = self._performance(complete, use_challenger=True)

        if len(complete) < minimum_complete_observations:
            findings.append("INSUFFICIENT_SHADOW_OBSERVATIONS")
            recommendation = "CONTINUE_SHADOW_TEST"
        else:
            champion_fnr = champion.false_negative_rate or 0.0
            challenger_fnr = challenger.false_negative_rate or 0.0
            champion_fpr = champion.false_positive_rate or 0.0
            challenger_fpr = challenger.false_positive_rate or 0.0

            if challenger_fnr > champion_fnr + max_false_negative_regression:
                findings.append("CHALLENGER_FALSE_NEGATIVE_REGRESSION")
            if challenger_fpr > champion_fpr + max_false_positive_regression:
                findings.append("CHALLENGER_FALSE_POSITIVE_REGRESSION")

            recall_better = self._better(challenger.recall, champion.recall, higher=True)
            precision_better = self._better(challenger.precision, champion.precision, higher=True)
            latency_better = self._better(challenger.average_latency_ms, champion.average_latency_ms, higher=False)
            cost_better = challenger.average_operational_cost <= champion.average_operational_cost

            regressions = {
                "CHALLENGER_FALSE_NEGATIVE_REGRESSION",
                "CHALLENGER_FALSE_POSITIVE_REGRESSION",
            }.intersection(findings)
            if regressions:
                recommendation = "RETAIN_CHAMPION"
            elif recall_better and (precision_better or latency_better or cost_better):
                recommendation = "CHALLENGER_ELIGIBLE_FOR_GOVERNED_PROMOTION"
            else:
                recommendation = "RETAIN_CHAMPION_OR_CONTINUE_TEST"

        # Shadow testing never grants production authority by itself.
        production_authority = False
        suggestions = [
            "Keep challenger execution shadow-only until formal promotion approval, dependency impact review, and registry versioning are complete.",
            "Compare performance on the same observation population and preserve source evidence for reproducibility.",
            "Treat false-negative regressions as a promotion blocker unless an authorized governance decision explicitly accepts the risk with compensating controls.",
            "Run SP-CAPITAL-RULE-DEPENDENCY-001 before promotion or champion retirement to identify downstream migration obligations.",
            "Persist champion and challenger versions in the validation record so results remain historically reproducible.",
        ]

        return ChampionChallengerReport(
            module_id=self.MODULE_ID,
            champion_rule_id=champion_rule_id,
            champion_version=champion_version,
            challenger_rule_id=challenger_rule_id,
            challenger_version=challenger_version,
            champion=champion,
            challenger=challenger,
            recommendation=recommendation,
            production_authority=production_authority,
            findings=tuple(findings),
            beneficial_suggestions=tuple(suggestions),
        )

    def promotion_ready(
        self,
        report: ChampionChallengerReport,
        *,
        dependency_review_passed: bool,
        registry_entry_ready: bool,
        governance_approval_ref: str | None,
    ) -> tuple[bool, tuple[str, ...]]:
        findings: list[str] = []
        if report.recommendation != "CHALLENGER_ELIGIBLE_FOR_GOVERNED_PROMOTION":
            findings.append("CHALLENGER_NOT_PERFORMANCE_ELIGIBLE")
        if not dependency_review_passed:
            findings.append("DEPENDENCY_REVIEW_REQUIRED")
        if not registry_entry_ready:
            findings.append("RULE_REGISTRY_ENTRY_REQUIRED")
        if not governance_approval_ref or not governance_approval_ref.strip():
            findings.append("GOVERNANCE_APPROVAL_REQUIRED")
        return (not findings, tuple(findings))

    @classmethod
    def _performance(cls, rows: list[RuleTestObservation], *, use_challenger: bool) -> RulePerformance:
        def triggered(row: RuleTestObservation) -> bool:
            return row.challenger_triggered if use_challenger else row.champion_triggered

        tp = sum(1 for row in rows if triggered(row) and row.bad_outcome_observed)
        tn = sum(1 for row in rows if not triggered(row) and not row.bad_outcome_observed)
        fp = sum(1 for row in rows if triggered(row) and not row.bad_outcome_observed)
        fn = sum(1 for row in rows if not triggered(row) and row.bad_outcome_observed)
        latencies = [
            row.challenger_latency_ms if use_challenger else row.champion_latency_ms
            for row in rows
        ]
        usable_latencies = [float(value) for value in latencies if value is not None]
        costs = [
            row.challenger_operational_cost if use_challenger else row.champion_operational_cost
            for row in rows
        ]
        return RulePerformance(
            sample_size=len(rows),
            true_positives=tp,
            true_negatives=tn,
            false_positives=fp,
            false_negatives=fn,
            precision=cls._ratio(tp, tp + fp),
            recall=cls._ratio(tp, tp + fn),
            false_positive_rate=cls._ratio(fp, fp + tn),
            false_negative_rate=cls._ratio(fn, fn + tp),
            average_latency_ms=(round(sum(usable_latencies) / len(usable_latencies), 3) if usable_latencies else None),
            average_operational_cost=round(sum(costs) / len(costs), 6) if costs else 0.0,
        )

    @staticmethod
    def _ratio(numerator: int, denominator: int) -> float | None:
        if denominator == 0:
            return None
        return round(numerator / denominator, 6)

    @staticmethod
    def _better(challenger: float | None, champion: float | None, *, higher: bool) -> bool:
        if challenger is None or champion is None:
            return False
        return challenger > champion if higher else challenger < champion

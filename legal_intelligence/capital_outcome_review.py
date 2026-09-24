"""Decision-effectiveness review for the SintraPrime private-capital stack.

SP-CAPITAL-OUTCOME-REVIEW-001 answers a different question from action completion:
Did an executed committee decision actually improve the underlying risk condition?

The engine compares pre-decision and post-decision metrics and classifies the outcome
as EFFECTIVE, PARTIALLY_EFFECTIVE, INEFFECTIVE, or TOO_EARLY_TO_TELL. These are
internal governance assessments, not legal, accounting, or regulatory conclusions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Mapping


METRIC_DIRECTIONS: dict[str, str] = {
    "reserve_headroom": "HIGHER_IS_BETTER",
    "delinquency": "LOWER_IS_BETTER",
    "concentration": "LOWER_IS_BETTER",
    "collateral_coverage": "HIGHER_IS_BETTER",
    "sla_breaches": "LOWER_IS_BETTER",
    "waiver_dependency": "LOWER_IS_BETTER",
    "stress_headroom": "HIGHER_IS_BETTER",
}


@dataclass(frozen=True)
class MetricOutcome:
    metric: str
    before: Decimal
    after: Decimal
    delta: Decimal
    direction: str
    result: str


@dataclass(frozen=True)
class OutcomeReview:
    module_id: str
    decision_id: str
    review_date: date
    classification: str
    improved_count: int
    worsened_count: int
    unchanged_count: int
    metric_outcomes: tuple[MetricOutcome, ...]
    findings: tuple[str, ...]
    beneficial_suggestions: tuple[str, ...]


class CapitalOutcomeReviewEngine:
    MODULE_ID = "SP-CAPITAL-OUTCOME-REVIEW-001"
    CLASSIFICATIONS = {
        "EFFECTIVE",
        "PARTIALLY_EFFECTIVE",
        "INEFFECTIVE",
        "TOO_EARLY_TO_TELL",
    }

    def review(self, context: Mapping[str, object]) -> OutcomeReview:
        findings: list[str] = []
        decision_id = str(context.get("decision_id") or "").strip()
        if not decision_id:
            findings.append("DECISION_ID_REQUIRED")

        review_date = context.get("review_date")
        if not isinstance(review_date, date):
            raise ValueError("review_date must be a datetime.date")

        effective_date = context.get("effective_date")
        minimum_observation_days = int(context.get("minimum_observation_days", 30))
        if isinstance(effective_date, date):
            observation_days = (review_date - effective_date).days
        else:
            observation_days = None
            findings.append("EFFECTIVE_DATE_REQUIRED_FOR_MATURITY_TEST")

        pre = context.get("pre_metrics") or {}
        post = context.get("post_metrics") or {}
        if not isinstance(pre, Mapping) or not isinstance(post, Mapping):
            raise ValueError("pre_metrics and post_metrics must be mappings")

        outcomes: list[MetricOutcome] = []
        missing: list[str] = []
        for metric, direction in METRIC_DIRECTIONS.items():
            if metric not in pre or metric not in post:
                missing.append(metric)
                continue
            before = Decimal(str(pre[metric]))
            after = Decimal(str(post[metric]))
            delta = after - before
            if delta == 0:
                result = "UNCHANGED"
            elif direction == "HIGHER_IS_BETTER":
                result = "IMPROVED" if delta > 0 else "WORSENED"
            else:
                result = "IMPROVED" if delta < 0 else "WORSENED"
            outcomes.append(MetricOutcome(metric, before, after, delta, direction, result))

        if missing:
            findings.append("MISSING_METRICS:" + ",".join(sorted(missing)))

        improved = sum(item.result == "IMPROVED" for item in outcomes)
        worsened = sum(item.result == "WORSENED" for item in outcomes)
        unchanged = sum(item.result == "UNCHANGED" for item in outcomes)

        if observation_days is None or observation_days < minimum_observation_days:
            classification = "TOO_EARLY_TO_TELL"
        elif not outcomes:
            classification = "TOO_EARLY_TO_TELL"
            findings.append("NO_COMPARABLE_METRICS")
        elif worsened == 0 and improved >= max(1, len(outcomes) // 2):
            classification = "EFFECTIVE"
        elif improved > worsened and improved > 0:
            classification = "PARTIALLY_EFFECTIVE"
        elif improved == 0 and worsened > 0:
            classification = "INEFFECTIVE"
        else:
            classification = "PARTIALLY_EFFECTIVE"

        expected_result = str(context.get("expected_result") or "").strip()
        if not expected_result:
            findings.append("EXPECTED_RESULT_NOT_DOCUMENTED")

        completed = bool(context.get("action_completed", False))
        if not completed:
            findings.append("ACTION_NOT_CONFIRMED_COMPLETE")

        suggestions = [
            "Keep execution completion separate from outcome effectiveness; a completed action can still be ineffective.",
            "Use the same metric definitions and source systems before and after the decision to avoid false trend signals.",
            "Route INEFFECTIVE and PARTIALLY_EFFECTIVE results into SP-CAPITAL-LESSONS-LEARNED-001 and the next committee pack.",
            "Do not treat correlation after a committee action as proof that the action caused the observed change.",
        ]
        if classification == "INEFFECTIVE":
            suggestions.append("Reopen the underlying risk case or require a replacement remediation plan with Principal/committee review.")
        if classification == "TOO_EARLY_TO_TELL":
            suggestions.append("Schedule a later review date rather than prematurely classifying the intervention as successful or failed.")

        return OutcomeReview(
            module_id=self.MODULE_ID,
            decision_id=decision_id,
            review_date=review_date,
            classification=classification,
            improved_count=improved,
            worsened_count=worsened,
            unchanged_count=unchanged,
            metric_outcomes=tuple(outcomes),
            findings=tuple(findings),
            beneficial_suggestions=tuple(suggestions),
        )

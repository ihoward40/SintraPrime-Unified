"""Control-performance validation for the SintraPrime private-capital stack.

SP-CAPITAL-CONTROL-VALIDATION-001 measures whether operational controls are
predictive and proportionate. It distinguishes hit rate, false positives,
false negatives, and insufficient evidence. This is an internal governance
control, not a regulatory model-risk opinion or legal conclusion.
"""

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ControlObservation:
    control_id: str
    triggered: bool
    bad_outcome_observed: bool
    observation_complete: bool = True


@dataclass(frozen=True)
class ControlValidationReport:
    module_id: str
    control_id: str
    sample_size: int
    complete_observations: int
    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int
    precision: float | None
    recall: float | None
    false_positive_rate: float | None
    false_negative_rate: float | None
    classification: str
    findings: tuple[str, ...]
    beneficial_suggestions: tuple[str, ...]


class CapitalControlValidationEngine:
    MODULE_ID = "SP-CAPITAL-CONTROL-VALIDATION-001"

    def validate(
        self,
        control_id: str,
        observations: Iterable[ControlObservation],
        *,
        minimum_complete_observations: int = 20,
        max_false_positive_rate: float = 0.35,
        max_false_negative_rate: float = 0.20,
    ) -> ControlValidationReport:
        rows = [row for row in observations if row.control_id == control_id]
        complete = [row for row in rows if row.observation_complete]
        findings: list[str] = []

        tp = sum(1 for row in complete if row.triggered and row.bad_outcome_observed)
        tn = sum(1 for row in complete if not row.triggered and not row.bad_outcome_observed)
        fp = sum(1 for row in complete if row.triggered and not row.bad_outcome_observed)
        fn = sum(1 for row in complete if not row.triggered and row.bad_outcome_observed)

        precision = self._ratio(tp, tp + fp)
        recall = self._ratio(tp, tp + fn)
        fpr = self._ratio(fp, fp + tn)
        fnr = self._ratio(fn, fn + tp)

        if not control_id.strip():
            findings.append("CONTROL_ID_REQUIRED")
        if len(complete) < minimum_complete_observations:
            findings.append("INSUFFICIENT_COMPLETE_OBSERVATIONS")
            classification = "INSUFFICIENT_EVIDENCE"
        else:
            if fpr is not None and fpr > max_false_positive_rate:
                findings.append("FALSE_POSITIVE_RATE_EXCESSIVE")
            if fnr is not None and fnr > max_false_negative_rate:
                findings.append("FALSE_NEGATIVE_RATE_EXCESSIVE")
            if "FALSE_NEGATIVE_RATE_EXCESSIVE" in findings:
                classification = "REVALIDATE_OR_REDESIGN"
            elif "FALSE_POSITIVE_RATE_EXCESSIVE" in findings:
                classification = "TUNE"
            else:
                classification = "VALIDATED_FOR_CONTINUED_USE"

        suggestions = [
            "Retain the observation population and source evidence so validation can be independently reproduced.",
            "Review controls on a fixed cadence and after material policy, portfolio, or data changes.",
            "Treat false negatives as higher-severity governance failures than nuisance false positives when the missed outcome is material.",
            "Route threshold or rule changes through SP-CAPITAL-RULE-REGISTRY-001 and SP-POLICY-CHANGE-CONTROL-001 rather than editing production logic silently.",
        ]
        if classification == "INSUFFICIENT_EVIDENCE":
            suggestions.append("Do not retire or materially loosen a control solely because current samples are too small to validate it.")
        if classification in {"TUNE", "REVALIDATE_OR_REDESIGN"}:
            suggestions.append("Create a controlled remediation candidate and preserve the prior rule version for rollback/comparison.")

        return ControlValidationReport(
            module_id=self.MODULE_ID,
            control_id=control_id,
            sample_size=len(rows),
            complete_observations=len(complete),
            true_positives=tp,
            true_negatives=tn,
            false_positives=fp,
            false_negatives=fn,
            precision=precision,
            recall=recall,
            false_positive_rate=fpr,
            false_negative_rate=fnr,
            classification=classification,
            findings=tuple(findings),
            beneficial_suggestions=tuple(suggestions),
        )

    @staticmethod
    def _ratio(numerator: int, denominator: int) -> float | None:
        if denominator == 0:
            return None
        return round(numerator / denominator, 6)

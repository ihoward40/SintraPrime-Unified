"""Portfolio/input drift monitoring for the SintraPrime private-capital stack.

SP-CAPITAL-DRIFT-MONITOR-001 detects material changes between the validation
baseline and the current operating population. A historically validated rule can
become temporarily untrusted when the data environment materially changes.

This is an internal governance control, not a statistical or regulatory opinion.
"""

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class DriftFeatureObservation:
    feature_name: str
    baseline_mean: float
    current_mean: float
    baseline_std: float | None = None
    baseline_missing_rate: float = 0.0
    current_missing_rate: float = 0.0
    population_stability_index: float | None = None


@dataclass(frozen=True)
class DriftFeatureResult:
    feature_name: str
    standardized_mean_shift: float | None
    missing_rate_shift: float
    population_stability_index: float | None
    severity: str
    findings: tuple[str, ...]


@dataclass(frozen=True)
class DriftMonitorReport:
    module_id: str
    rule_id: str
    rule_version: str
    baseline_id: str
    data_quality_status: str
    status: str
    revalidation_required: bool
    feature_results: tuple[DriftFeatureResult, ...]
    findings: tuple[str, ...]
    beneficial_suggestions: tuple[str, ...]


class CapitalDriftMonitorEngine:
    MODULE_ID = "SP-CAPITAL-DRIFT-MONITOR-001"

    def evaluate(
        self,
        *,
        rule_id: str,
        rule_version: str,
        baseline_id: str,
        observations: Iterable[DriftFeatureObservation],
        data_quality_status: str,
        watch_standardized_shift: float = 0.50,
        material_standardized_shift: float = 1.00,
        watch_psi: float = 0.10,
        material_psi: float = 0.25,
        watch_missing_rate_shift: float = 0.05,
        material_missing_rate_shift: float = 0.10,
    ) -> DriftMonitorReport:
        findings: list[str] = []
        rows = list(observations)

        if not rule_id.strip():
            findings.append("RULE_ID_REQUIRED")
        if not rule_version.strip():
            findings.append("RULE_VERSION_REQUIRED")
        if not baseline_id.strip():
            findings.append("BASELINE_ID_REQUIRED")
        if not rows:
            findings.append("DRIFT_OBSERVATIONS_REQUIRED")

        if data_quality_status == "BLOCK_DOWNSTREAM_RELIANCE":
            findings.append("DATA_QUALITY_BLOCKS_DRIFT_CONCLUSION")

        results: list[DriftFeatureResult] = []
        critical_or_material = 0
        watch_count = 0

        for row in rows:
            row_findings: list[str] = []
            standardized_shift = None
            if row.baseline_std is not None:
                if row.baseline_std < 0:
                    row_findings.append("BASELINE_STD_INVALID")
                elif row.baseline_std == 0:
                    if row.current_mean != row.baseline_mean:
                        row_findings.append("ZERO_VARIANCE_BASELINE_CHANGED")
                else:
                    standardized_shift = round(abs(row.current_mean - row.baseline_mean) / row.baseline_std, 6)

            if not 0 <= row.baseline_missing_rate <= 1 or not 0 <= row.current_missing_rate <= 1:
                row_findings.append("MISSING_RATE_OUT_OF_RANGE")
            missing_shift = round(abs(row.current_missing_rate - row.baseline_missing_rate), 6)

            if row.population_stability_index is not None and row.population_stability_index < 0:
                row_findings.append("PSI_INVALID")

            material = False
            watch = False
            if standardized_shift is not None:
                material = material or standardized_shift >= material_standardized_shift
                watch = watch or standardized_shift >= watch_standardized_shift
            if row.population_stability_index is not None:
                material = material or row.population_stability_index >= material_psi
                watch = watch or row.population_stability_index >= watch_psi
            material = material or missing_shift >= material_missing_rate_shift
            watch = watch or missing_shift >= watch_missing_rate_shift

            if any(code in {"BASELINE_STD_INVALID", "MISSING_RATE_OUT_OF_RANGE", "PSI_INVALID"} for code in row_findings):
                severity = "INVALID"
                critical_or_material += 1
            elif material:
                severity = "MATERIAL"
                critical_or_material += 1
                row_findings.append("MATERIAL_DRIFT_DETECTED")
            elif watch:
                severity = "WATCH"
                watch_count += 1
                row_findings.append("DRIFT_WATCH_THRESHOLD_REACHED")
            else:
                severity = "STABLE"

            results.append(
                DriftFeatureResult(
                    feature_name=row.feature_name,
                    standardized_mean_shift=standardized_shift,
                    missing_rate_shift=missing_shift,
                    population_stability_index=row.population_stability_index,
                    severity=severity,
                    findings=tuple(row_findings),
                )
            )

        if data_quality_status == "BLOCK_DOWNSTREAM_RELIANCE":
            status = "DATA_QUALITY_BLOCK"
            revalidation_required = True
        elif critical_or_material >= 1:
            status = "REVALIDATION_REQUIRED"
            revalidation_required = True
            findings.append("MATERIAL_POPULATION_DRIFT")
        elif watch_count >= 2:
            status = "WATCH"
            revalidation_required = False
            findings.append("MULTI_FEATURE_DRIFT_WATCH")
        elif watch_count == 1:
            status = "WATCH"
            revalidation_required = False
        else:
            status = "STABLE"
            revalidation_required = False

        suggestions = [
            "Persist the exact validation baseline, feature definitions, rule version, and observation window so drift comparisons remain reproducible.",
            "Trigger SP-CAPITAL-CONTROL-VALIDATION-001 when material drift changes the population on which the rule was validated.",
            "Do not promote a challenger or loosen a champion solely because drift makes historical validation performance look stale.",
            "Feed material drift into the committee pack, rule registry review, and dependency review before production rule changes are approved.",
        ]
        if revalidation_required:
            suggestions.append("Treat the affected rule as temporarily untrusted for material decisions until data quality and revalidation are complete or Principal-approved compensating controls are documented.")

        return DriftMonitorReport(
            module_id=self.MODULE_ID,
            rule_id=rule_id,
            rule_version=rule_version,
            baseline_id=baseline_id,
            data_quality_status=data_quality_status,
            status=status,
            revalidation_required=revalidation_required,
            feature_results=tuple(results),
            findings=tuple(findings),
            beneficial_suggestions=tuple(suggestions),
        )

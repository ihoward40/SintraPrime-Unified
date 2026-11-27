"""Data-quality governance for the SintraPrime private-capital stack.

SP-CAPITAL-DATA-QUALITY-001 validates whether operational data is sufficiently
complete, timely, reconciled, non-duplicative, provenance-backed, and internally
consistent before downstream risk analytics rely on it.

Thresholds in this module are internal governance defaults, not legal or
regulatory requirements.
"""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DataQualitySnapshot:
    dataset_id: str
    as_of: date
    total_records: int
    complete_records: int
    duplicate_records: int
    stale_records: int
    provenance_complete_records: int
    reconciled_records: int
    inconsistent_metric_count: int = 0
    expected_record_count: int | None = None
    source_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class DataQualityReport:
    module_id: str
    dataset_id: str
    status: str
    completeness_rate: float | None
    duplicate_rate: float | None
    stale_rate: float | None
    provenance_rate: float | None
    reconciliation_rate: float | None
    population_coverage_rate: float | None
    findings: tuple[str, ...]
    beneficial_suggestions: tuple[str, ...]


class CapitalDataQualityEngine:
    MODULE_ID = "SP-CAPITAL-DATA-QUALITY-001"

    def evaluate(
        self,
        snapshot: DataQualitySnapshot,
        *,
        minimum_completeness_rate: float = 0.95,
        maximum_duplicate_rate: float = 0.02,
        maximum_stale_rate: float = 0.10,
        minimum_provenance_rate: float = 0.95,
        minimum_reconciliation_rate: float = 0.98,
        minimum_population_coverage_rate: float = 0.95,
    ) -> DataQualityReport:
        findings: list[str] = []

        if not snapshot.dataset_id.strip():
            findings.append("DATASET_ID_REQUIRED")
        if snapshot.total_records < 0:
            findings.append("TOTAL_RECORDS_INVALID")
        if snapshot.total_records == 0:
            findings.append("NO_RECORDS_AVAILABLE")

        numeric_counts = {
            "COMPLETE_RECORDS_INVALID": snapshot.complete_records,
            "DUPLICATE_RECORDS_INVALID": snapshot.duplicate_records,
            "STALE_RECORDS_INVALID": snapshot.stale_records,
            "PROVENANCE_RECORDS_INVALID": snapshot.provenance_complete_records,
            "RECONCILED_RECORDS_INVALID": snapshot.reconciled_records,
            "INCONSISTENT_METRIC_COUNT_INVALID": snapshot.inconsistent_metric_count,
        }
        for code, value in numeric_counts.items():
            if value < 0:
                findings.append(code)

        if snapshot.total_records > 0:
            bounded_counts = {
                "COMPLETE_RECORDS_EXCEED_TOTAL": snapshot.complete_records,
                "DUPLICATE_RECORDS_EXCEED_TOTAL": snapshot.duplicate_records,
                "STALE_RECORDS_EXCEED_TOTAL": snapshot.stale_records,
                "PROVENANCE_RECORDS_EXCEED_TOTAL": snapshot.provenance_complete_records,
                "RECONCILED_RECORDS_EXCEED_TOTAL": snapshot.reconciled_records,
            }
            for code, value in bounded_counts.items():
                if value > snapshot.total_records:
                    findings.append(code)

        completeness = self._rate(snapshot.complete_records, snapshot.total_records)
        duplicate_rate = self._rate(snapshot.duplicate_records, snapshot.total_records)
        stale_rate = self._rate(snapshot.stale_records, snapshot.total_records)
        provenance = self._rate(snapshot.provenance_complete_records, snapshot.total_records)
        reconciliation = self._rate(snapshot.reconciled_records, snapshot.total_records)
        coverage = None
        if snapshot.expected_record_count is not None:
            if snapshot.expected_record_count <= 0:
                findings.append("EXPECTED_RECORD_COUNT_INVALID")
            else:
                coverage = round(snapshot.total_records / snapshot.expected_record_count, 6)

        self._below(findings, completeness, minimum_completeness_rate, "COMPLETENESS_BELOW_MINIMUM")
        self._above(findings, duplicate_rate, maximum_duplicate_rate, "DUPLICATE_RATE_EXCESSIVE")
        self._above(findings, stale_rate, maximum_stale_rate, "STALE_DATA_RATE_EXCESSIVE")
        self._below(findings, provenance, minimum_provenance_rate, "PROVENANCE_BELOW_MINIMUM")
        self._below(findings, reconciliation, minimum_reconciliation_rate, "RECONCILIATION_BELOW_MINIMUM")
        if coverage is not None and coverage < minimum_population_coverage_rate:
            findings.append("POPULATION_COVERAGE_BELOW_MINIMUM")
        if snapshot.inconsistent_metric_count > 0:
            findings.append("CROSS_METRIC_INCONSISTENCY_PRESENT")
        if not snapshot.source_refs:
            findings.append("SOURCE_REFERENCES_MISSING")

        hard_block_codes = {
            "DATASET_ID_REQUIRED",
            "TOTAL_RECORDS_INVALID",
            "NO_RECORDS_AVAILABLE",
            "COMPLETE_RECORDS_INVALID",
            "DUPLICATE_RECORDS_INVALID",
            "STALE_RECORDS_INVALID",
            "PROVENANCE_RECORDS_INVALID",
            "RECONCILED_RECORDS_INVALID",
            "INCONSISTENT_METRIC_COUNT_INVALID",
            "COMPLETE_RECORDS_EXCEED_TOTAL",
            "DUPLICATE_RECORDS_EXCEED_TOTAL",
            "STALE_RECORDS_EXCEED_TOTAL",
            "PROVENANCE_RECORDS_EXCEED_TOTAL",
            "RECONCILED_RECORDS_EXCEED_TOTAL",
            "COMPLETENESS_BELOW_MINIMUM",
            "PROVENANCE_BELOW_MINIMUM",
            "RECONCILIATION_BELOW_MINIMUM",
            "CROSS_METRIC_INCONSISTENCY_PRESENT",
        }
        watch_codes = {
            "DUPLICATE_RATE_EXCESSIVE",
            "STALE_DATA_RATE_EXCESSIVE",
            "POPULATION_COVERAGE_BELOW_MINIMUM",
            "SOURCE_REFERENCES_MISSING",
            "EXPECTED_RECORD_COUNT_INVALID",
        }

        if any(code in hard_block_codes for code in findings):
            status = "BLOCK_DOWNSTREAM_RELIANCE"
        elif any(code in watch_codes for code in findings):
            status = "WATCH"
        else:
            status = "PASS"

        suggestions = [
            "Persist source-system identifiers and extraction timestamps with every dataset used for underwriting, monitoring, stress, or committee reporting.",
            "Reconcile aggregate balances and counts back to independently retained source records before certifying monthly management information.",
            "Route stale collateral values to SP-COLLATERAL-MONITOR-001 and material reconciliation breaks to case management rather than suppressing them.",
            "Block rule validation and challenger promotion when the underlying observation dataset is not reliable enough to support the conclusion.",
        ]
        if status == "BLOCK_DOWNSTREAM_RELIANCE":
            suggestions.append("Repair and re-certify the dataset before relying on it for a material capital, policy, or rule decision.")

        return DataQualityReport(
            module_id=self.MODULE_ID,
            dataset_id=snapshot.dataset_id,
            status=status,
            completeness_rate=completeness,
            duplicate_rate=duplicate_rate,
            stale_rate=stale_rate,
            provenance_rate=provenance,
            reconciliation_rate=reconciliation,
            population_coverage_rate=coverage,
            findings=tuple(findings),
            beneficial_suggestions=tuple(suggestions),
        )

    @staticmethod
    def _rate(numerator: int, denominator: int) -> float | None:
        if denominator <= 0:
            return None
        return round(numerator / denominator, 6)

    @staticmethod
    def _below(findings: list[str], value: float | None, threshold: float, code: str) -> None:
        if value is not None and value < threshold:
            findings.append(code)

    @staticmethod
    def _above(findings: list[str], value: float | None, threshold: float, code: str) -> None:
        if value is not None and value > threshold:
            findings.append(code)

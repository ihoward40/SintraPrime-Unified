from datetime import date

from legal_intelligence.capital_data_quality import CapitalDataQualityEngine, DataQualitySnapshot
from legal_intelligence.capital_drift_monitor import CapitalDriftMonitorEngine, DriftFeatureObservation


def test_data_quality_blocks_material_reliance_when_completeness_or_reconciliation_fails():
    snapshot = DataQualitySnapshot(
        dataset_id="portfolio-2026-09",
        as_of=date(2026, 9, 15),
        total_records=100,
        complete_records=90,
        duplicate_records=1,
        stale_records=2,
        provenance_complete_records=99,
        reconciled_records=90,
        inconsistent_metric_count=0,
        expected_record_count=100,
        source_refs=("bank-recon-1", "ledger-export-1"),
    )

    report = CapitalDataQualityEngine().evaluate(snapshot)

    assert report.status == "BLOCK_DOWNSTREAM_RELIANCE"
    assert "COMPLETENESS_BELOW_MINIMUM" in report.findings
    assert "RECONCILIATION_BELOW_MINIMUM" in report.findings


def test_data_quality_passes_clean_dataset():
    snapshot = DataQualitySnapshot(
        dataset_id="portfolio-2026-09",
        as_of=date(2026, 9, 15),
        total_records=100,
        complete_records=100,
        duplicate_records=0,
        stale_records=0,
        provenance_complete_records=100,
        reconciled_records=100,
        inconsistent_metric_count=0,
        expected_record_count=100,
        source_refs=("bank-recon-1", "ledger-export-1"),
    )

    report = CapitalDataQualityEngine().evaluate(snapshot)

    assert report.status == "PASS"
    assert report.completeness_rate == 1.0
    assert report.reconciliation_rate == 1.0


def test_drift_requires_revalidation_for_material_shift():
    report = CapitalDriftMonitorEngine().evaluate(
        rule_id="EWS-COLLATERAL-001",
        rule_version="1.2.0",
        baseline_id="baseline-2026-q2",
        data_quality_status="PASS",
        observations=(
            DriftFeatureObservation(
                feature_name="collateral_coverage_ratio",
                baseline_mean=1.50,
                current_mean=1.10,
                baseline_std=0.25,
                baseline_missing_rate=0.0,
                current_missing_rate=0.0,
                population_stability_index=0.30,
            ),
        ),
    )

    assert report.status == "REVALIDATION_REQUIRED"
    assert report.revalidation_required is True
    assert report.feature_results[0].severity == "MATERIAL"
    assert "MATERIAL_POPULATION_DRIFT" in report.findings


def test_drift_does_not_trust_conclusion_when_data_quality_is_blocked():
    report = CapitalDriftMonitorEngine().evaluate(
        rule_id="UW-DSCR-001",
        rule_version="2.0.0",
        baseline_id="baseline-2026-q2",
        data_quality_status="BLOCK_DOWNSTREAM_RELIANCE",
        observations=(
            DriftFeatureObservation(
                feature_name="dscr",
                baseline_mean=1.40,
                current_mean=1.39,
                baseline_std=0.20,
            ),
        ),
    )

    assert report.status == "DATA_QUALITY_BLOCK"
    assert report.revalidation_required is True
    assert "DATA_QUALITY_BLOCKS_DRIFT_CONCLUSION" in report.findings


def test_drift_watch_for_multiple_moderate_features():
    report = CapitalDriftMonitorEngine().evaluate(
        rule_id="PORTFOLIO-001",
        rule_version="1.0.0",
        baseline_id="baseline-2026-q2",
        data_quality_status="PASS",
        observations=(
            DriftFeatureObservation(
                feature_name="top_customer_concentration",
                baseline_mean=0.20,
                current_mean=0.31,
                baseline_std=0.20,
            ),
            DriftFeatureObservation(
                feature_name="days_past_due",
                baseline_mean=5.0,
                current_mean=8.0,
                baseline_std=5.0,
            ),
        ),
    )

    assert report.status == "WATCH"
    assert report.revalidation_required is False
    assert "MULTI_FEATURE_DRIFT_WATCH" in report.findings

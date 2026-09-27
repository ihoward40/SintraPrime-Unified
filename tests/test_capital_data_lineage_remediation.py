from datetime import date, datetime, timezone

from legal_intelligence.capital_data_lineage import (
    CapitalDataLineageEngine,
    DataLineageRecord,
    LineageStep,
)
from legal_intelligence.capital_data_remediation import (
    CapitalDataRemediationEngine,
    DataRemediationCase,
)


def _lineage() -> DataLineageRecord:
    extracted = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
    return DataLineageRecord(
        lineage_id="LIN-001",
        dataset_id="portfolio-2026-09",
        metric_or_field="reserve_headroom",
        source_system="capital-ledger",
        source_record_ref="ledger-snapshot-2026-09",
        extracted_at=extracted,
        extraction_actor="svc-capital-reporting",
        transformations=[
            LineageStep("S1", "TRANSFORM", "Normalize balances", "svc-etl", extracted, "ev-transform-1"),
            LineageStep("S2", "RECONCILE", "Tie to bank evidence", "svc-recon", extracted, "ev-recon-1"),
        ],
        reconciliation_ref="recon-2026-09",
        evidence_refs=["ledger-export", "bank-statement"],
        downstream_consumers=["SP-CAPITAL-DASHBOARD-001", "SP-CAPITAL-COMMITTEE-PACK-001"],
        policy_id="CAP-POL",
        policy_version="3.2.0",
    )


def test_complete_lineage_and_impact_map():
    engine = CapitalDataLineageEngine()
    record = _lineage()
    report = engine.validate(record)
    assert report.status == "COMPLETE"
    consumers = engine.impacted_consumers([record], record.dataset_id)
    assert "SP-CAPITAL-DASHBOARD-001" in consumers
    assert "SP-CAPITAL-COMMITTEE-PACK-001" in consumers


def test_lineage_missing_reconciliation_blocks_completeness():
    engine = CapitalDataLineageEngine()
    record = _lineage()
    record.reconciliation_ref = None
    report = engine.validate(record)
    assert report.status == "INCOMPLETE"
    assert "RECONCILIATION_REFERENCE_REQUIRED" in report.findings


def _remediation() -> DataRemediationCase:
    return DataRemediationCase(
        case_id="DQ-CASE-001",
        dataset_id="portfolio-2026-09",
        severity="HIGH",
        owner="data-owner",
        opened_date=date(2026, 9, 1),
        source_quality_status="BLOCK_DOWNSTREAM_RELIANCE",
        failed_findings=["RECONCILIATION_BELOW_MINIMUM"],
        remediation_plan=["Repair reconciliation and rerun quality checks"],
    )


def test_remediation_case_gets_sla_and_blocks_reliance_until_recertified():
    engine = CapitalDataRemediationEngine()
    case = _remediation()
    opened = engine.open_case(case)
    assert opened.status == "OPEN"
    assert case.due_date == date(2026, 9, 4)
    current = engine.evaluate(case, as_of=date(2026, 9, 2))
    assert current.downstream_reliance_restored is False


def test_recertification_requires_independent_reviewer_and_downstream_rerun():
    engine = CapitalDataRemediationEngine()
    case = _remediation()
    engine.open_case(case)
    case.status = "RECERTIFIED"
    case.corrected_dataset_ref = "dataset-v2"
    case.corrected_lineage_ref = "LIN-002"
    case.recertifier = case.owner
    case.recertification_evidence_refs = ["dq-pass-v2"]
    case.downstream_consumers = ["SP-CAPITAL-DASHBOARD-001"]
    case.closure_authority = "principal"
    blocked = engine.evaluate(case, as_of=date(2026, 9, 3))
    assert blocked.downstream_reliance_restored is False
    assert "RECERTIFIER_MUST_BE_INDEPENDENT" in blocked.findings

    case.recertifier = "independent-reviewer"
    case.downstream_rerun_refs = ["dashboard-rerun-v2"]
    passed = engine.evaluate(case, as_of=date(2026, 9, 3))
    assert passed.downstream_reliance_restored is True

from datetime import datetime, timedelta, timezone

from legal_intelligence.capital_data_contracts import (
    CapitalDataContractsEngine,
    DataContract,
    DataContractField,
)
from legal_intelligence.capital_replay_certification import (
    CapitalReplayCertificationEngine,
    ReplayCertificationRequest,
    ReplayInputRef,
)


def _contract() -> DataContract:
    return DataContract(
        contract_id="DC-001",
        version="1.0.0",
        dataset_id="portfolio-monthly",
        owner="data-governance",
        source_system="capital-ledger",
        fields=[
            DataContractField("facility_id", "STRING", required=True, nullable=False),
            DataContractField("principal", "DECIMAL", required=True, unit="USD", nullable=False),
        ],
        freshness_sla_hours=24,
        reconciliation_rule="Tie principal to ledger and bank evidence",
        allowed_transformations=["normalize_currency", "aggregate_by_facility"],
        breaking_change_protocol="Create new contract version and complete downstream dependency review",
        effective_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )


def test_contract_is_valid_and_dataset_conforms():
    engine = CapitalDataContractsEngine()
    contract = _contract()
    assert engine.validate_contract(contract).valid is True
    now = datetime(2026, 9, 15, 8, 0, tzinfo=timezone.utc)
    report = engine.check_dataset(
        contract,
        observed_fields=["facility_id", "principal"],
        observed_types={"facility_id": "STRING", "principal": "DECIMAL"},
        observed_units={"principal": "USD"},
        extracted_at=now - timedelta(hours=2),
        reconciled=True,
        transformations_used=["normalize_currency"],
        as_of=now,
    )
    assert report.status == "PASS"
    assert report.breaking_change_detected is False


def test_breaking_schema_or_unit_change_blocks_use():
    engine = CapitalDataContractsEngine()
    contract = _contract()
    now = datetime(2026, 9, 15, 8, 0, tzinfo=timezone.utc)
    report = engine.check_dataset(
        contract,
        observed_fields=["facility_id", "principal"],
        observed_types={"facility_id": "STRING", "principal": "STRING"},
        observed_units={"principal": "EUR"},
        extracted_at=now,
        reconciled=True,
        transformations_used=["normalize_currency"],
        as_of=now,
    )
    assert report.status == "BLOCK_USE"
    assert report.breaking_change_detected is True
    assert "FIELD_TYPE_MISMATCH:principal" in report.findings
    assert "FIELD_UNIT_MISMATCH:principal" in report.findings


def _replay_request(replayed_value=125000.00, replay_actor="independent-reviewer"):
    return ReplayCertificationRequest(
        replay_id="RP-001",
        subject_id="committee-metric-reserve-headroom",
        result_type="COMMITTEE_METRIC",
        certified_value=125000.00,
        replayed_value=replayed_value,
        inputs=[
            ReplayInputRef(
                source_ref="ledger-export-2026-09",
                contract_id="DC-001",
                contract_version="1.0.0",
                lineage_ref="LIN-001",
                transformation_spec_ref="transform-v4",
                evidence_ref="hash-ledger-export",
            )
        ],
        replayed_at=datetime(2026, 9, 15, 8, 30, tzinfo=timezone.utc),
        replay_actor=replay_actor,
        original_actor="svc-capital-reporting",
        tolerance=0.01,
        policy_id="CAP-POL",
        policy_version="3.2.0",
        rule_id="RESERVE-HEADROOM",
        rule_version="2.0.0",
        execution_environment_ref="env-hash-001",
        code_or_formula_ref="formula-hash-001",
        evidence_refs=["replay-log-001"],
    )


def test_replay_certifies_exact_reproduction():
    report = CapitalReplayCertificationEngine().certify(_replay_request())
    assert report.status == "CERTIFIED_REPRODUCIBLE"
    assert report.reproducible is True
    assert report.variance == 0.0


def test_replay_mismatch_fails_certification():
    report = CapitalReplayCertificationEngine().certify(_replay_request(replayed_value=124000.0))
    assert report.status == "REPLAY_FAILED"
    assert report.reproducible is False
    assert "REPLAY_RESULT_MISMATCH" in report.findings


def test_replay_requires_independent_actor():
    request = _replay_request(replay_actor="svc-capital-reporting")
    request.original_actor = "svc-capital-reporting"
    report = CapitalReplayCertificationEngine().certify(request)
    assert report.reproducible is False
    assert "INDEPENDENT_REPLAY_ACTOR_REQUIRED" in report.findings

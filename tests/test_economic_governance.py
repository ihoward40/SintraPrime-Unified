from decimal import Decimal

import pytest
from pydantic import ValidationError

from packages.economic_governance import (
    AssetProvenanceRecord,
    CapitalReservePolicy,
    EvidenceReference,
    EvidenceType,
    LegalEffectStatus,
    ScenarioConfidence,
    ScenarioRecord,
    SpendCategory,
    SpendPolicy,
    SpendRequest,
    assess_provenance,
    evaluate_spend,
)


def test_public_filing_does_not_promote_legal_effects() -> None:
    record = AssetProvenanceRecord(
        asset_id="ASSET-001",
        asset_type="intellectual_property",
        asset_name="Example governed asset",
        public_filing_reference="FILING-001",
        evidence=[
            EvidenceReference(
                evidence_id="E-001",
                evidence_type=EvidenceType.GOVERNMENT_ACKNOWLEDGMENT,
                reference="FILING-001",
                description="Government acknowledgment that a filing was recorded",
                verified=True,
                supports={"filing_occurred"},
            )
        ],
    )

    assessment = assess_provenance(record)

    assert assessment.public_filing_present is True
    assert assessment.complete is False
    assert record.ownership_status == LegalEffectStatus.NOT_ASSESSED
    assert record.attachment_status == LegalEffectStatus.NOT_ASSESSED
    assert record.perfection_status == LegalEffectStatus.NOT_ASSESSED
    assert record.priority_status == LegalEffectStatus.NOT_ASSESSED
    assert record.enforceability_status == LegalEffectStatus.NOT_ASSESSED
    assert "does not auto-establish" in assessment.warnings[0]


def test_complete_provenance_chain_can_be_assessed_without_legal_inference() -> None:
    record = AssetProvenanceRecord(
        asset_id="ASSET-002",
        asset_type="software_ip",
        asset_name="Example software asset",
        origin="Created internally",
        claimed_owner="Example Trust",
        transfer_document="ASSIGNMENT-001",
        consideration="Documented consideration",
        trust_acceptance_record="MINUTES-001",
        schedule_a_reference="SCHEDULE-A-001",
        accounting_record="LEDGER-001",
        control_or_possession="Repository and credential control",
        legal_classification="intellectual property",
    )

    assessment = assess_provenance(record)

    assert assessment.complete is True
    assert assessment.missing_elements == []
    assert record.ownership_status == LegalEffectStatus.NOT_ASSESSED


def test_authorized_research_spend_inside_budget_is_allowed() -> None:
    policy = SpendPolicy(
        mission_id="MISSION-1",
        agent_id="researcher-04",
        per_transaction_limit=Decimal("10"),
        mission_budget=Decimal("25"),
        spent_to_date=Decimal("5"),
    )
    request = SpendRequest(
        request_id="REQ-1",
        mission_id="MISSION-1",
        agent_id="researcher-04",
        category=SpendCategory.RESEARCH,
        amount=Decimal("4.50"),
        purpose="Purchase a mission-scoped research record",
    )

    decision = evaluate_spend(request, policy)

    assert decision.allowed is True
    assert decision.requires_principal_approval is False
    assert decision.remaining_budget == Decimal("15.50")


@pytest.mark.parametrize(
    "category",
    [
        SpendCategory.TRANSFER_TO_HUMAN,
        SpendCategory.BORROWING,
        SpendCategory.OPEN_ACCOUNT,
        SpendCategory.SECURITIES,
        SpendCategory.TRUST_ASSET_MOVEMENT,
    ],
)
def test_high_risk_financial_actions_are_hard_denied(category: SpendCategory) -> None:
    policy = SpendPolicy(
        mission_id="MISSION-1",
        agent_id="agent-1",
        per_transaction_limit=Decimal("1000"),
        mission_budget=Decimal("10000"),
    )
    request = SpendRequest(
        request_id="REQ-2",
        mission_id="MISSION-1",
        agent_id="agent-1",
        category=category,
        amount=Decimal("1"),
        purpose="Attempt prohibited autonomous action",
    )

    decision = evaluate_spend(request, policy)

    assert decision.allowed is False
    assert "hard-denied" in decision.reason


def test_software_spend_requires_principal_approval() -> None:
    policy = SpendPolicy(
        mission_id="MISSION-1",
        agent_id="agent-1",
        per_transaction_limit=Decimal("50"),
        mission_budget=Decimal("100"),
    )
    request = SpendRequest(
        request_id="REQ-3",
        mission_id="MISSION-1",
        agent_id="agent-1",
        category=SpendCategory.SOFTWARE,
        amount=Decimal("10"),
        purpose="Purchase software subscription",
    )

    decision = evaluate_spend(request, policy)

    assert decision.allowed is False
    assert decision.requires_principal_approval is True


def test_scenario_requires_assumptions_and_failure_conditions() -> None:
    with pytest.raises(ValidationError):
        ScenarioRecord(
            scenario_id="SCENARIO-1",
            thesis="A future market outcome",
            assumptions=[],
            confidence=ScenarioConfidence.MEDIUM,
            failure_conditions=["Demand does not develop"],
            time_horizon="10 years",
        )


def test_default_capital_stack_has_six_unique_layers() -> None:
    policy = CapitalReservePolicy.default_stack()

    assert [layer.layer for layer in policy.layers] == [1, 2, 3, 4, 5, 6]
    assert policy.layers[0].name == "Daily liquidity"
    assert policy.layers[-1].name == "Long-duration family/trust capital"

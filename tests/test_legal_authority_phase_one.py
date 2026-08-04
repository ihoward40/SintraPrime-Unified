from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from legal_authority.constants import AUTHORITY_HIERARCHY
from legal_authority.engine import RuleEvaluationEngine
from legal_authority.models import JurisdictionRule, LegalAuthority
from legal_authority.repository import LegalAuthorityRepository


def _authority(**overrides):
    data = {
        "id": "A1",
        "jurisdiction": "NJ",
        "authority_type": "NEW_JERSEY_STATUTE",
        "source_classification": "PRIMARY_LEGAL_AUTHORITY",
        "citation": "N.J.S.A. 3B:31-1",
        "title": "Authority",
        "court_or_agency": "New Jersey Legislature",
        "docket_or_bill_number": None,
        "source_url": "https://example.test",
        "source_document_id": None,
        "publication_date": "2020-01-01",
        "effective_date": "2020-01-01",
        "repeal_date": None,
        "last_verified_at": "2026-08-03T00:00:00Z",
        "verified_by": "test",
        "verification_status": "PRIMARY_SOURCE_VERIFIED",
        "authority_weight": AUTHORITY_HIERARCHY["NEW_JERSEY_STATUTE"],
        "summary": "Summary",
        "quoted_text": None,
        "limitations": [],
        "tags": [],
        "content_hash": None,
        "created_at": "2026-08-03T00:00:00Z",
        "updated_at": "2026-08-03T00:00:00Z",
    }
    data.update(overrides)
    return LegalAuthority.model_validate(data)


def _rule(**overrides):
    data = {
        "id": "R1",
        "jurisdiction": "NJ",
        "domain": "trust_law",
        "topic": "topic",
        "rule_statement": "Statement",
        "rule_logic": {"conditions": [], "conclusion": "OK"},
        "authority_ids": ["A1"],
        "status": "ACTIVE",
        "confidence": 0.5,
        "requires_human_review": True,
        "effective_from": "2020-01-01",
        "effective_to": None,
        "exceptions": [],
        "conflicting_rule_ids": [],
        "supersedes_rule_ids": [],
        "superseded_by_rule_ids": [],
        "version": "1.0.0",
        "created_at": "2026-08-03T00:00:00Z",
        "updated_at": "2026-08-03T00:00:00Z",
    }
    data.update(overrides)
    return JurisdictionRule.model_validate(data)


def test_valid_authority_model():
    authority = _authority()
    assert authority.source_classification == "PRIMARY_LEGAL_AUTHORITY"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_classification", "BLOG"),
        ("jurisdiction", "XX"),
        ("verification_status", "LEGAL_APPROVED"),
        ("citation", ""),
    ],
)
def test_invalid_authority_fields(field, value):
    with pytest.raises(ValidationError):
        _authority(**{field: value})


def test_unsupported_private_claim_cannot_be_verified():
    with pytest.raises(ValidationError):
        _authority(
            authority_type="UNSUPPORTED_PRIVATE_CLAIM",
            source_classification="UNVERIFIED_PRIVATE_LAW_CLAIM",
            verification_status="PRIMARY_SOURCE_VERIFIED",
            authority_weight=0,
        )


def test_rule_schema_validation_errors():
    with pytest.raises(ValidationError):
        _rule(authority_ids=[])
    with pytest.raises(ValidationError):
        _rule(confidence=1.5)
    with pytest.raises(ValidationError):
        _rule(rule_logic={"conditions": "bad", "conclusion": "OK"})
    with pytest.raises(ValidationError):
        _rule(effective_from="2021-01-01", effective_to="2020-01-01")


def test_repository_has_no_orphan_rules():
    repo = LegalAuthorityRepository()
    assert repo.rules
    for rule in repo.rules.values():
        assert rule.authority_ids
        for authority_id in rule.authority_ids:
            assert authority_id in repo.authorities


def test_current_rule_selection_requires_human_review_with_provenance():
    result = RuleEvaluationEngine().select_rule(
        "NJ", "trust_law", "certification of trust", date(2026, 8, 3)
    )
    assert result.selected_rule.id == "NJ-TRUST-CERTIFICATION"
    assert result.authorities[0].id == "NJ-UTC-LIABILITY-3B31-70-81"
    assert result.human_review_required is True
    assert "not a legal opinion" in " ".join(result.limitations).lower()


def test_future_rule_is_not_applied_early():
    result = RuleEvaluationEngine().select_rule(
        "NJ", "engine_fixture", "future rule selection fixture", date(2026, 8, 3)
    )
    assert result.selected_rule is None
    assert result.candidate_rule_ids == []


def test_repealed_historical_rule_available_only_historically():
    engine = RuleEvaluationEngine()
    historical = engine.select_rule(
        "NJ", "ucc_article9", "historical trust debtor naming pre 2013", date(2012, 1, 1)
    )
    current = engine.select_rule(
        "NJ", "ucc_article9", "historical trust debtor naming pre 2013", date(2026, 8, 3)
    )
    assert historical.selected_rule.id == "NJ-UCC-DEBTOR-NAMING-TRUSTS-PRE-2013"
    assert current.selected_rule is None


def test_superseded_rule_does_not_apply_currently():
    result = RuleEvaluationEngine().select_rule(
        "NJ", "ucc_article9", "historical trust debtor naming pre 2013", date(2014, 1, 1)
    )
    assert result.selected_rule is None


def test_missing_effective_date_requires_review():
    result = RuleEvaluationEngine().select_rule(
        "NJ", "engine_fixture", "missing date fixture", date(2026, 8, 3)
    )
    assert result.selected_rule is None
    assert result.verification_status == "HUMAN_REVIEW_REQUIRED"
    assert result.human_review_required is True


def test_overlapping_rules_trigger_conflict():
    result = RuleEvaluationEngine().select_rule(
        "NJ", "engine_fixture", "overlapping conflict fixture", date(2026, 8, 3)
    )
    assert result.selected_rule is None
    assert result.verification_status == "CONFLICTING_AUTHORITY"
    assert result.conflicts


@pytest.mark.parametrize(
    ("topic", "expected_rule", "expected_authority"),
    [
        (
            "revocable trust exposure",
            "NJ-TRUST-REVOCABLE-CREDITOR-EXPOSURE",
            "NJ-UTC-CREDITORS-3B31-35-41",
        ),
        (
            "irrevocable trust settlor benefit",
            "NJ-TRUST-IRREVOCABLE-SETTLOR-BENEFIT",
            "NJ-UTC-CREDITORS-3B31-35-41",
        ),
        (
            "spendthrift provisions",
            "NJ-TRUST-SPENDTHRIFT-DISCRETIONARY-MANDATORY",
            "NJ-UTC-CREDITORS-3B31-35-41",
        ),
        (
            "discretionary trusts",
            "NJ-TRUST-SPENDTHRIFT-DISCRETIONARY-MANDATORY",
            "NJ-UTC-CREDITORS-3B31-35-41",
        ),
        (
            "overdue distributions",
            "NJ-TRUST-SPENDTHRIFT-DISCRETIONARY-MANDATORY",
            "NJ-UTC-CREDITORS-3B31-35-41",
        ),
        ("trustee powers duties", "NJ-TRUST-TRUSTEE-DUTIES", "NJ-UTC-DUTIES-3B31-54-69"),
        (
            "modification reformation",
            "NJ-TRUST-MODIFICATION-TERMINATION",
            "NJ-UTC-NJSA-3B31-11-26-34",
        ),
        (
            "uniform voidable transactions act",
            "NJ-CREDITOR-UVTA-ACTUAL-CONSTRUCTIVE",
            "NJ-UVTA-2021-92",
        ),
        (
            "financing statements amendments",
            "NJ-UCC-FINANCING-STATEMENTS-AMENDMENTS",
            "NJ-UCC9-2001-117",
        ),
        (
            "debtor naming organization",
            "NJ-UCC-DEBTOR-NAMING-TRUSTS",
            "NJ-UCC9-2013-65-DEBTOR-NAME",
        ),
        ("filing office rejection", "NJ-UCC-FILING-REJECTION-SEARCH", "NJ-NJAC-17-33-UCC-RULES"),
    ],
)
def test_new_jersey_representative_rules_select_with_authorities(
    topic, expected_rule, expected_authority
):
    domain = "ucc_article9" if expected_rule.startswith("NJ-UCC") else "trust_law"
    if expected_rule.startswith("NJ-CREDITOR"):
        domain = "creditor_protection"
    result = RuleEvaluationEngine().select_rule("NJ", domain, topic, date(2026, 8, 3))
    assert result.selected_rule.id == expected_rule
    assert expected_authority in [authority.id for authority in result.authorities]


def test_unsupported_private_claim_is_quarantined_and_not_active():
    repo = LegalAuthorityRepository()
    authority = repo.get_authority("NJ-PRIVATE-UNSUPPORTED-BANK-SIGNATURE-CARD")
    assert authority.source_classification == "UNVERIFIED_PRIVATE_LAW_CLAIM"
    assert authority.verification_status == "UNVERIFIED"
    active_rules = repo.query_rules(topic="bank signature card", status="ACTIVE")
    assert active_rules == []
    quarantined = repo.query_rules(topic="bank signature card")
    assert quarantined[0].status == "QUARANTINED"

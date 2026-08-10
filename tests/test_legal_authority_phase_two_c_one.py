from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from legal_authority.constants import AUTHORITY_HIERARCHY
from legal_authority.repository import LegalAuthorityRepository
from portal.auth.jwt_handler import create_access_token
from portal.auth.rbac import Role


def test_federal_package_validates_and_preserves_provenance():
    repo = LegalAuthorityRepository()
    result = repo.validate_jurisdiction_packages()
    assert result["federal_package_validated"] is True
    assert result["errors"] == []
    assert result["authority_count"] >= 106
    assert result["rule_count"] >= 135

    rule = repo.get_rule("FED-RULE-FCRA-REINVESTIGATION")
    assert rule is not None
    assert rule.jurisdiction == "FED"
    assert rule.rule_category == "FEDERAL_OVERLAY"
    assert rule.requires_human_review is True
    assert set(rule.authority_ids) == {"FED-FCRA-15-1681", "FED-REG-FCRA-12-CFR-1022"}
    assert any("locator-only" in str(item).lower() for item in rule.exceptions)


def test_federal_authority_hierarchy_preserves_statute_and_regulation_types():
    repo = LegalAuthorityRepository()
    statute = repo.get_authority("FED-FDCPA-15-1692")
    regulation = repo.get_authority("FED-REG-FCRA-12-CFR-1022")
    assert statute is not None
    assert regulation is not None
    assert statute.authority_type == "FEDERAL_STATUTE"
    assert statute.authority_weight == AUTHORITY_HIERARCHY["FEDERAL_STATUTE"]
    assert regulation.authority_type == "FEDERAL_REGULATION"
    assert regulation.authority_weight == AUTHORITY_HIERARCHY["FEDERAL_REGULATION"]
    assert regulation.verification_status == "PRIMARY_SOURCE_LOCATED"
    assert regulation.source_availability_status == "LOCATOR_ONLY"


def test_federal_rules_cover_required_overlay_domains_without_production_gate_bypass():
    repo = LegalAuthorityRepository()
    rules = [rule for rule in repo.rules.values() if rule.jurisdiction == "FED"]
    domains = {rule.domain for rule in rules}
    assert {
        "consumer_debt_collection",
        "credit_reporting",
        "consumer_credit",
        "electronic_transfers",
        "bankruptcy",
        "creditor_protection",
        "federal_tax",
        "servicemember_protection",
        "procedure",
        "ucc_intersection",
    } <= domains
    assert all(rule.requires_human_review for rule in rules)
    assert all(rule.review_status == "NOT_SUBMITTED" for rule in rules)
    assert all(rule.status != "QUARANTINED" for rule in rules)


def test_federal_coverage_is_partial_and_other_jurisdictions_remain_unchanged():
    repo = LegalAuthorityRepository()
    assert repo.get_coverage("FED")["support_status"] == "NOT_STARTED"
    assert repo.get_coverage("FED")["human_reviewed"] is False
    assert repo.get_coverage("FED")["production_eligible"] is False
    # Phase 3A advanced CT and DE to TESTED.
    for code in ("CT", "DE"):
        coverage = repo.get_coverage(code)
        assert coverage["support_status"] == "TESTED"
        assert coverage["production_eligible"] is False
    # Remaining non-pilot states remain NOT_STARTED.
    remaining = (
        "AL",
        "AK",
        "AZ",
        "AR",
        "CA",
        "CO",
        "FL",
        "GA",
        "HI",
        "ID",
        "IL",
        "IN",
        "IA",
        "KS",
        "KY",
        "LA",
        "ME",
        "MD",
        "MA",
        "MI",
        "MN",
        "MS",
        "MO",
        "MT",
        "NE",
        "NV",
        "NH",
        "NM",
        "NC",
        "ND",
        "OH",
        "OK",
        "OR",
        "RI",
        "SC",
        "SD",
        "TN",
        "TX",
        "UT",
        "VT",
        "VA",
        "WA",
        "WV",
        "WI",
        "WY",
        "DC",
    )
    for code in remaining:
        coverage = repo.get_coverage(code)
        assert coverage["support_status"] == "NOT_STARTED"
        assert coverage["production_eligible"] is False


def test_federal_benefit_rules_include_social_security_va_and_railroad_retirement():
    repo = LegalAuthorityRepository()
    social = repo.get_rule("FED-RULE-BENEFITS-SOCIAL-SECURITY")
    va_railroad = repo.get_rule("FED-RULE-VA-RAILROAD-BENEFITS")
    assert social is not None
    assert va_railroad is not None
    assert {"FED-VA-38-5301", "FED-RRA-45-231M"} == set(va_railroad.authority_ids)
    assert va_railroad.requires_human_review is True


def test_federal_rules_keep_explicit_non_advice_limitations():
    repo = LegalAuthorityRepository()
    bankruptcy = repo.get_rule("FED-RULE-BANKRUPTCY-ESTATE")
    tax = repo.get_rule("FED-RULE-TAX-LIEN-LEVY")
    ucc = repo.get_rule("FED-RULE-UCC-FEDERAL-INTERSECTION")
    assert bankruptcy is not None
    assert tax is not None
    assert ucc is not None
    assert any(
        "FEDERAL_BANKRUPTCY_REVIEW_REQUIRED" in item["rule"] for item in bankruptcy.exceptions
    )
    assert any("CPA" in item["rule"] or "tax-attorney" in item["rule"] for item in tax.exceptions)
    assert any("No federal UCC" in item["rule"] for item in ucc.exceptions)


def test_federal_read_only_api_endpoints():
    from portal.main import create_app

    token = create_access_token(
        user_id=str(uuid4()),
        tenant_id=str(uuid4()),
        role=Role.SUPER_ADMIN.value,
        permissions=[],
    )
    headers = {"Authorization": f"Bearer {token}"}
    client = TestClient(create_app())
    domains = client.get("/federal/domains", headers=headers)
    rules = client.get("/federal/rules", params={"domain": "bankruptcy"}, headers=headers)
    authorities = client.get("/federal/authorities", headers=headers)
    conflicts = client.get("/federal/conflicts", headers=headers)
    detail = client.get("/federal/rules/FED-RULE-FDCPA-VALIDATION", headers=headers)
    missing = client.get("/federal/rules/does-not-exist", headers=headers)

    assert domains.status_code == 200
    assert any(item["domain"] == "bankruptcy" for item in domains.json())
    assert rules.status_code == 200
    assert all(item["jurisdiction"] == "FED" for item in rules.json())
    assert authorities.status_code == 200
    assert all(item["jurisdiction"] == "FED" for item in authorities.json())
    assert conflicts.status_code == 200
    assert detail.status_code == 200
    assert detail.json()["authority_ids"]
    assert detail.json()["production_gate"]["production_eligible"] is False
    assert missing.status_code == 404

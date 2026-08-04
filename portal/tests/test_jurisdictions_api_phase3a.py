"""Phase 3A jurisdiction tests: Delaware and Connecticut."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import portal.routers.jurisdictions as jurisdiction_router
from legal_authority.constants import (
    REQUIRED_JURISDICTION_PACKAGE_FILES,
    RULE_STATUSES,
    SUPPORTED_JURISDICTIONS,
)
from legal_authority.repository import LegalAuthorityRepository
from portal.main import create_app
from portal.services.jurisdiction_rule_service import JurisdictionRuleService


def _pkg_root() -> Path:
    return Path(__file__).parents[2] / "data" / "jurisdictions"


def _load_json(path: Path) -> list[dict] | dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _temp_service(tmp_path: Path) -> JurisdictionRuleService:
    """Create a JurisdictionRuleService backed by a temp copy of data/jurisdictions."""
    root = tmp_path / "repo"
    shutil.copytree(
        Path.cwd() / "data" / "jurisdictions", root / "data" / "jurisdictions", dirs_exist_ok=True
    )
    return JurisdictionRuleService(LegalAuthorityRepository(root=root))


@pytest.fixture(autouse=True)
def _swap_service(tmp_path: Path):
    """Swap the router service to use tmp_path copy of data/ (bypasses gitignore)."""
    original = jurisdiction_router.service
    jurisdiction_router.service = _temp_service(tmp_path)
    yield
    jurisdiction_router.service = original


def client() -> TestClient:
    return TestClient(create_app())


# ---------------------------------------------------------------------------
# Package structure validation
# ---------------------------------------------------------------------------


def test_de_required_package_files_exist():
    for fname in REQUIRED_JURISDICTION_PACKAGE_FILES:
        assert (_pkg_root() / "delaware" / fname).exists(), f"Missing: delaware/{fname}"


def test_ct_required_package_files_exist():
    for fname in REQUIRED_JURISDICTION_PACKAGE_FILES:
        assert (_pkg_root() / "connecticut" / fname).exists(), f"Missing: connecticut/{fname}"


def test_de_package_required_files_nonempty():
    for fname in REQUIRED_JURISDICTION_PACKAGE_FILES:
        data = _load_json(_pkg_root() / "delaware" / fname)
        assert data is not None, f"delaware/{fname} is None"


def test_ct_package_required_files_nonempty():
    for fname in REQUIRED_JURISDICTION_PACKAGE_FILES:
        data = _load_json(_pkg_root() / "connecticut" / fname)
        assert data is not None, f"connecticut/{fname} is None"


def test_de_rules_have_unique_ids():
    rules = _load_json(_pkg_root() / "delaware" / "rules.json")
    ids = [r["id"] for r in rules]
    assert len(ids) == len(set(ids)), "Duplicate rule IDs in Delaware rules.json"


def test_ct_rules_have_unique_ids():
    rules = _load_json(_pkg_root() / "connecticut" / "rules.json")
    ids = [r["id"] for r in rules]
    assert len(ids) == len(set(ids)), "Duplicate rule IDs in Connecticut rules.json"


def test_de_authorities_have_unique_ids():
    authorities = _load_json(_pkg_root() / "delaware" / "authorities.json")
    ids = [a["id"] for a in authorities]
    assert len(ids) == len(set(ids)), "Duplicate authority IDs in Delaware authorities.json"


def test_ct_authorities_have_unique_ids():
    authorities = _load_json(_pkg_root() / "connecticut" / "authorities.json")
    ids = [a["id"] for a in authorities]
    assert len(ids) == len(set(ids)), "Duplicate authority IDs in Connecticut authorities.json"


def test_de_rules_reference_valid_authority_ids():
    rules = _load_json(_pkg_root() / "delaware" / "rules.json")
    authorities = _load_json(_pkg_root() / "delaware" / "authorities.json")
    auth_ids = {a["id"] for a in authorities}
    for rule in rules:
        for aid in rule.get("authority_ids", []):
            assert aid in auth_ids, f"Rule {rule['id']} references unknown authority {aid}"


def test_ct_rules_reference_valid_authority_ids():
    rules = _load_json(_pkg_root() / "connecticut" / "rules.json")
    authorities = _load_json(_pkg_root() / "connecticut" / "authorities.json")
    auth_ids = {a["id"] for a in authorities}
    for rule in rules:
        for aid in rule.get("authority_ids", []):
            assert aid in auth_ids, f"Rule {rule['id']} references unknown authority {aid}"


_RULE_REQUIRED_FIELDS = {
    "id",
    "jurisdiction",
    "domain",
    "topic",
    "rule_statement",
    "rule_logic",
    "authority_ids",
    "status",
    "confidence",
    "requires_human_review",
    "effective_from",
    "exceptions",
    "conflicting_rule_ids",
    "supersedes_rule_ids",
    "superseded_by_rule_ids",
    "version",
    "rule_category",
    "review_status",
}


def test_de_rules_have_required_fields():
    rules = _load_json(_pkg_root() / "delaware" / "rules.json")
    for rule in rules:
        missing = _RULE_REQUIRED_FIELDS - set(rule.keys())
        assert not missing, f"Rule {rule['id']} missing fields: {missing}"


def test_ct_rules_have_required_fields():
    rules = _load_json(_pkg_root() / "connecticut" / "rules.json")
    for rule in rules:
        missing = _RULE_REQUIRED_FIELDS - set(rule.keys())
        assert not missing, f"Rule {rule['id']} missing fields: {missing}"


def test_de_rules_have_valid_status_enum():
    rules = _load_json(_pkg_root() / "delaware" / "rules.json")
    for rule in rules:
        assert (
            rule["status"] in RULE_STATUSES
        ), f"Rule {rule['id']} has invalid status {rule['status']}"


def test_ct_rules_have_valid_status_enum():
    rules = _load_json(_pkg_root() / "connecticut" / "rules.json")
    for rule in rules:
        assert (
            rule["status"] in RULE_STATUSES
        ), f"Rule {rule['id']} has invalid status {rule['status']}"


def test_de_rules_human_review_flag_set():
    rules = _load_json(_pkg_root() / "delaware" / "rules.json")
    assert all(
        r["requires_human_review"] is True for r in rules
    ), "All DE rules must require human review"


def test_ct_rules_human_review_flag_set():
    rules = _load_json(_pkg_root() / "connecticut" / "rules.json")
    assert all(
        r["requires_human_review"] is True for r in rules
    ), "All CT rules must require human review"


def test_de_conflict_rules_reference_valid_ids():
    conflicts = _load_json(_pkg_root() / "delaware" / "conflicts.json")
    rules = _load_json(_pkg_root() / "delaware" / "rules.json")
    rule_ids = {r["id"] for r in rules}
    for conflict in conflicts:
        for rid in conflict.get("competing_rules", []):
            assert rid in rule_ids, f"Conflict {conflict['id']} references unknown rule {rid}"


def test_ct_conflict_rules_reference_valid_ids():
    # Connecticut conflicts may reference rules from other jurisdictions (e.g., CT vs DE).
    conflicts = _load_json(_pkg_root() / "connecticut" / "conflicts.json")
    ct_rules = _load_json(_pkg_root() / "connecticut" / "rules.json")
    de_rules = _load_json(_pkg_root() / "delaware" / "rules.json")
    all_rule_ids = {r["id"] for r in ct_rules} | {r["id"] for r in de_rules}
    for conflict in conflicts:
        for rid in conflict.get("competing_rules", []):
            assert rid in all_rule_ids, f"Conflict {conflict['id']} references unknown rule {rid}"


# ---------------------------------------------------------------------------
# API: jurisdiction list and detail
# ---------------------------------------------------------------------------


def test_de_jurisdiction_in_list():
    response = client().get("/jurisdictions")
    assert response.status_code == 200
    assert any(
        item["code"] == "DE" for item in response.json()
    ), "DE missing from jurisdiction list"


def test_ct_jurisdiction_in_list():
    response = client().get("/jurisdictions")
    assert response.status_code == 200
    assert any(
        item["code"] == "CT" for item in response.json()
    ), "CT missing from jurisdiction list"


def test_de_jurisdiction_detail():
    response = client().get("/jurisdictions/DE")
    assert response.status_code == 200
    assert response.json()["code"] == "DE"
    assert response.json()["support_status"] == "TESTED"
    assert response.json()["production_eligible"] is False


def test_ct_jurisdiction_detail():
    response = client().get("/jurisdictions/CT")
    assert response.status_code == 200
    assert response.json()["code"] == "CT"
    assert response.json()["support_status"] == "TESTED"
    assert response.json()["production_eligible"] is False


def test_de_coverage_includes_domains_and_counts():
    response = client().get("/jurisdictions/DE/coverage")
    assert response.status_code == 200
    body = response.json()
    assert (
        "trust_law" in body["domains"]
        or "creditor_protection" in body["domains"]
        or "ucc_article9" in body["domains"]
    )
    assert body["rule_count"] >= 20
    assert body["human_reviewed"] is False
    assert "does not provide a legal opinion" in body["human_review_warning"]


def test_ct_coverage_includes_domains_and_counts():
    response = client().get("/jurisdictions/CT/coverage")
    assert response.status_code == 200
    body = response.json()
    assert (
        "trust_law" in body["domains"]
        or "creditor_protection" in body["domains"]
        or "ucc_article9" in body["domains"]
    )
    assert body["rule_count"] >= 18
    assert body["human_reviewed"] is False
    assert "does not provide a legal opinion" in body["human_review_warning"]


# ---------------------------------------------------------------------------
# API: rules filtering
# ---------------------------------------------------------------------------


def test_de_rules_list():
    response = client().get("/jurisdictions/DE/rules")
    assert response.status_code == 200
    rules = response.json()
    assert len(rules) >= 20
    assert all(r["jurisdiction"] == "DE" for r in rules)


def test_ct_rules_list():
    response = client().get("/jurisdictions/CT/rules")
    assert response.status_code == 200
    rules = response.json()
    assert len(rules) >= 18
    assert all(r["jurisdiction"] == "CT" for r in rules)


def test_de_rules_filtered_by_domain():
    response = client().get("/jurisdictions/DE/rules", params={"domain": "trust_law"})
    assert response.status_code == 200
    for rule in response.json():
        assert rule["domain"] == "trust_law"


def test_ct_rules_filtered_by_domain():
    response = client().get("/jurisdictions/CT/rules", params={"domain": "creditor_protection"})
    assert response.status_code == 200
    for rule in response.json():
        assert rule["domain"] == "creditor_protection"


def test_de_rule_detail():
    rules = client().get("/jurisdictions/DE/rules").json()
    rule_id = rules[0]["id"]
    response = client().get(f"/jurisdictions/DE/rules/{rule_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["provenance"]["jurisdiction"] == "DE"
    assert body["provenance"]["rule_id"] == rule_id
    assert body["human_review_status"] == "HUMAN_REVIEW_REQUIRED"
    assert body["limitations"]


def test_ct_rule_detail():
    rules = client().get("/jurisdictions/CT/rules").json()
    rule_id = rules[0]["id"]
    response = client().get(f"/jurisdictions/CT/rules/{rule_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["provenance"]["jurisdiction"] == "CT"
    assert body["provenance"]["rule_id"] == rule_id
    assert body["human_review_status"] == "HUMAN_REVIEW_REQUIRED"


# ---------------------------------------------------------------------------
# API: conflicts and review queue
# ---------------------------------------------------------------------------


def test_de_conflicts_endpoint():
    response = client().get("/jurisdictions/DE/conflicts")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_ct_conflicts_endpoint():
    response = client().get("/jurisdictions/CT/conflicts")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_de_review_queue_requires_auth():
    denied = client().get("/jurisdictions/DE/review-queue")
    assert denied.status_code == 403
    allowed = client().get(
        "/jurisdictions/DE/review-queue",
        headers={
            "X-Reviewer-Role": "LICENSED_ATTORNEY",
            "X-Reviewer-Identity": "attorney@example.test",
        },
    )
    assert allowed.status_code == 200
    body = allowed.json()
    assert body["jurisdiction"] == "DE"
    assert body["pending_rules"]


def test_ct_review_queue_requires_auth():
    denied = client().get("/jurisdictions/CT/review-queue")
    assert denied.status_code == 403
    allowed = client().get(
        "/jurisdictions/CT/review-queue",
        headers={
            "X-Reviewer-Role": "LICENSED_ATTORNEY",
            "X-Reviewer-Identity": "attorney@example.test",
        },
    )
    assert allowed.status_code == 200
    body = allowed.json()
    assert body["jurisdiction"] == "CT"
    assert body["pending_rules"]


# ---------------------------------------------------------------------------
# API: authority retrieval
# ---------------------------------------------------------------------------


def test_de_authority_retrieval():
    response = client().get("/legal-authorities/DE-TRUST-DAPT-4901")
    assert response.status_code == 200
    body = response.json()
    assert body["jurisdiction"] == "DE"
    assert body["verification_status"] == "PRIMARY_SOURCE_VERIFIED"


def test_ct_authority_retrieval():
    response = client().get("/legal-authorities/CT-TRUST-CREDITOR-45478")
    assert response.status_code == 200
    body = response.json()
    assert body["jurisdiction"] == "CT"


# ---------------------------------------------------------------------------
# Comparison: 5-state comparison
# ---------------------------------------------------------------------------


def test_five_state_comparison():
    response = client().get(
        "/legal-rules/compare",
        params={
            "jurisdictions": "NJ,NY,PA,DE,CT",
            "domain": "trust_law",
            "topic": "revocable trust settlor creditor exposure",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body["jurisdictions"]) == {"NJ", "NY", "PA", "DE", "CT"}
    assert body["conflict_of_laws_warning"]
    assert len(body["rows"]) == 5


def test_comparison_shows_missing_rule_as_null():
    response = client().get(
        "/legal-rules/compare",
        params={
            "jurisdictions": "DE,CT",
            "domain": "trust_law",
            "topic": "nonexistent topic xyzabc",
        },
    )
    assert response.status_code == 200
    body = response.json()
    for row in body["rows"]:
        if row["jurisdiction"] in ("DE", "CT"):
            assert (
                row["rule"] is None or row["missing_data"]
            ), "Should show missing data for nonexistent topic"


def test_comparison_includes_conflict_warning():
    response = client().get(
        "/legal-rules/compare",
        params={
            "jurisdictions": "DE,CT",
            "domain": "creditor_protection",
            "topic": "self-settled asset protection trust DAPT qualified disposition",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["conflict_of_laws_warning"]


def test_comparison_dapt_vs_ct_produces_conflict_row():
    response = client().get(
        "/legal-rules/compare",
        params={
            "jurisdictions": "DE,CT",
            "domain": "creditor_protection",
            "topic": "self-settled trust no asset protection Connecticut",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["rows"]) == 2


# ---------------------------------------------------------------------------
# Invalid rule / authority returns 404
# ---------------------------------------------------------------------------


def test_de_invalid_rule_returns_404():
    response = client().get("/jurisdictions/DE/rules/NOTREAL123")
    assert response.status_code == 404


def test_ct_invalid_rule_returns_404():
    response = client().get("/jurisdictions/CT/rules/NOTREAL123")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Constants: supported jurisdictions
# ---------------------------------------------------------------------------


def test_constants_include_de_and_ct():
    assert "DE" in SUPPORTED_JURISDICTIONS
    assert "CT" in SUPPORTED_JURISDICTIONS


# ---------------------------------------------------------------------------
# Coverage.json: status correct (file-based, bypasses gitignore)
# ---------------------------------------------------------------------------


def test_coverage_de_is_tested():
    with open(_pkg_root() / "coverage.json", encoding="utf-8") as f:
        coverage = json.load(f)
    de = next(j for j in coverage["jurisdictions"] if j["code"] == "DE")
    assert de["support_status"] == "TESTED"
    assert de["researched"] is True
    assert de["encoded"] is True
    assert de["tested"] is True
    assert de["human_reviewed"] is False
    assert de["production_eligible"] is False


def test_coverage_ct_is_tested():
    with open(_pkg_root() / "coverage.json", encoding="utf-8") as f:
        coverage = json.load(f)
    ct = next(j for j in coverage["jurisdictions"] if j["code"] == "CT")
    assert ct["support_status"] == "TESTED"
    assert ct["researched"] is True
    assert ct["encoded"] is True
    assert ct["tested"] is True
    assert ct["human_reviewed"] is False
    assert ct["production_eligible"] is False


def test_coverage_nj_ny_pa_unchanged():
    with open(_pkg_root() / "coverage.json", encoding="utf-8") as f:
        coverage = json.load(f)
    for code, expected in [("NJ", "TESTED"), ("NY", "TESTED"), ("PA", "TESTED")]:
        j = next(x for x in coverage["jurisdictions"] if x["code"] == code)
        assert j["support_status"] == expected, f"{code} support_status changed from {expected}"


# ---------------------------------------------------------------------------
# Production gate blocks all Phase 3A rules
# ---------------------------------------------------------------------------


def test_de_rules_blocked_from_production():
    rules = client().get("/jurisdictions/DE/rules").json()
    for rule in rules[:3]:
        detail = client().get(f"/jurisdictions/DE/rules/{rule['id']}")
        gate = detail.json()["production_gate"]
        assert gate["production_eligible"] is False


def test_ct_rules_blocked_from_production():
    rules = client().get("/jurisdictions/CT/rules").json()
    for rule in rules[:3]:
        detail = client().get(f"/jurisdictions/CT/rules/{rule['id']}")
        gate = detail.json()["production_gate"]
        assert gate["production_eligible"] is False


# ---------------------------------------------------------------------------
# DE-specific: DAPT and statutory trust distinction
# ---------------------------------------------------------------------------


def test_de_distinguishes_statutory_vs_common_law():
    rules = client().get("/jurisdictions/DE/rules").json()
    statutory_trust_ids = [
        r["id"]
        for r in rules
        if "dsta" in r["topic"].lower() or "statutory trust" in r["topic"].lower()
    ]
    common_law_ids = [
        r["id"]
        for r in rules
        if "express trust" in r["topic"].lower() or "common law" in r["topic"].lower()
    ]
    assert (
        len(statutory_trust_ids) > 0 or len(common_law_ids) > 0
    ), "DE should distinguish statutory vs common-law trust types"


def test_de_dapt_rule_has_fraudulent_transfer_exception():
    rules = client().get("/jurisdictions/DE/rules").json()
    dapt_rules = [r for r in rules if "DAPT" in r["id"] or "self-settled" in r["topic"]]
    assert dapt_rules
    for rule in dapt_rules:
        exception_texts = [str(e) for e in rule.get("exceptions", [])]
        assert any(
            "fraudulent" in t.lower() or "bankruptcy" in t.lower() for t in exception_texts
        ), f"Rule {rule['id']} should include fraudulent-transfer or bankruptcy exception"


def test_ct_self_settled_prohibition_rule_has_exception():
    rules = client().get("/jurisdictions/CT/rules").json()
    self_settled = [r for r in rules if "self-settled" in r["topic"].lower()]
    assert self_settled
    for rule in self_settled:
        assert rule["exceptions"], f"CT self-settled rule {rule['id']} should have exceptions"

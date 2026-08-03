from __future__ import annotations

from fastapi.testclient import TestClient

from portal.main import create_app


def client():
    return TestClient(create_app())


def test_jurisdiction_list_and_detail():
    c = client()
    response = c.get("/jurisdictions")
    assert response.status_code == 200
    assert any(item["code"] == "NJ" for item in response.json())

    detail = c.get("/jurisdictions/NJ")
    assert detail.status_code == 200
    assert detail.json()["support_status"] == "TESTED"
    assert detail.json()["production_eligible"] is False


def test_unsupported_jurisdiction():
    response = client().get("/jurisdictions/ZZ")
    assert response.status_code == 404


def test_coverage_includes_warning_and_counts():
    response = client().get("/jurisdictions/NJ/coverage")
    assert response.status_code == 200
    body = response.json()
    assert body["rule_count"] > 10
    assert "trust_law" in body["domains"]
    assert body["human_reviewed"] is False
    assert "Not a legal opinion" in body["human_review_warning"]


def test_rules_filtering_and_as_of_date_query():
    c = client()
    response = c.get(
        "/jurisdictions/NJ/rules", params={"domain": "ucc_article9", "topic": "debtor naming"}
    )
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert "NJ-UCC-DEBTOR-NAMING-TRUSTS" in ids

    historical = c.get(
        "/jurisdictions/NJ/rules",
        params={"domain": "ucc_article9", "effective_date": "2012-01-01"},
    )
    assert historical.status_code == 200
    assert any(item["id"] == "NJ-UCC-DEBTOR-NAMING-TRUSTS-PRE-2013" for item in historical.json())


def test_rule_detail_provenance_and_limitations():
    response = client().get("/jurisdictions/NJ/rules/NJ-TRUST-CERTIFICATION")
    assert response.status_code == 200
    body = response.json()
    assert body["provenance"]["rule_id"] == "NJ-TRUST-CERTIFICATION"
    assert body["provenance"]["authority_ids"] == ["NJ-UTC-LIABILITY-3B31-70-81"]
    assert body["provenance"]["jurisdiction"] == "NJ"
    assert body["human_review_status"] == "HUMAN_REVIEW_REQUIRED"
    assert body["limitations"]


def test_invalid_rule_id():
    response = client().get("/jurisdictions/NJ/rules/NOPE")
    assert response.status_code == 404


def test_authority_retrieval():
    response = client().get("/legal-authorities/NJ-UTC-2015-276")
    assert response.status_code == 200
    body = response.json()
    assert body["citation"].startswith("P.L.2015")
    assert body["verification_status"] == "PRIMARY_SOURCE_VERIFIED"


def test_compare_endpoint_conflict_and_provenance():
    response = client().get(
        "/legal-rules/compare",
        params={
            "jurisdiction": "NJ",
            "domain": "engine_fixture",
            "topic": "overlapping conflict fixture",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["verification_status"] == "CONFLICTING_AUTHORITY"
    assert body["conflicts"]


def test_containment_not_returned_as_verified_authority_or_active_rule():
    c = client()
    authority = c.get("/legal-authorities/NJ-PRIVATE-UNSUPPORTED-BANK-SIGNATURE-CARD")
    assert authority.status_code == 200
    assert authority.json()["source_classification"] == "UNVERIFIED_PRIVATE_LAW_CLAIM"
    assert authority.json()["verification_status"] == "UNVERIFIED"

    active = c.get(
        "/jurisdictions/NJ/rules",
        params={"topic": "bank signature card", "status": "ACTIVE"},
    )
    assert active.status_code == 200
    assert active.json() == []

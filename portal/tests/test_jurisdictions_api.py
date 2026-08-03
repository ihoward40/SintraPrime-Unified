from __future__ import annotations

import shutil
from pathlib import Path

from fastapi.testclient import TestClient

import portal.routers.jurisdictions as jurisdiction_router
from legal_authority.repository import LegalAuthorityRepository
from portal.main import create_app
from portal.services.jurisdiction_rule_service import JurisdictionRuleService


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
    assert "does not provide a legal opinion" in body["human_review_warning"]


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


def _temp_service(tmp_path):
    root = tmp_path / "repo"
    shutil.copytree(Path.cwd() / "data" / "jurisdictions", root / "data" / "jurisdictions")
    return JurisdictionRuleService(LegalAuthorityRepository(root=root))


def test_phase_2a_review_queue_requires_authorization(tmp_path):
    original = jurisdiction_router.service
    jurisdiction_router.service = _temp_service(tmp_path)
    try:
        c = client()
        denied = c.get("/jurisdictions/NJ/review-queue")
        assert denied.status_code == 403

        allowed = c.get(
            "/jurisdictions/NJ/review-queue",
            headers={
                "X-Reviewer-Role": "LICENSED_ATTORNEY",
                "X-Reviewer-Identity": "attorney@example.test",
            },
        )
        assert allowed.status_code == 200
        body = allowed.json()
        assert body["pending_rules"]
        assert "stale_authorities" in body
    finally:
        jurisdiction_router.service = original


def test_phase_2a_review_and_challenge_write_endpoints_are_controlled(tmp_path):
    original = jurisdiction_router.service
    jurisdiction_router.service = _temp_service(tmp_path)
    try:
        c = client()
        no_auth = c.post(
            "/legal-rules/NJ-TRUST-CERTIFICATION/submit-review",
            json={"findings": "submit"},
        )
        assert no_auth.status_code == 403

        submit = c.post(
            "/legal-rules/NJ-TRUST-CERTIFICATION/submit-review",
            headers={
                "X-Reviewer-Role": "LEGAL_RESEARCHER",
                "X-Reviewer-Identity": "researcher@example.test",
            },
            json={"findings": "ready for attorney review"},
        )
        assert submit.status_code == 200
        assert submit.json()["review_status"] == "SUBMITTED"

        non_attorney = c.post(
            "/legal-rules/NJ-TRUST-CERTIFICATION/reviews",
            headers={
                "X-Reviewer-Role": "LEGAL_RESEARCHER",
                "X-Reviewer-Identity": "researcher@example.test",
            },
            json={"review_status": "APPROVED", "findings": "approve", "digital_signature": "sig"},
        )
        assert non_attorney.status_code == 400

        challenge = c.post(
            "/legal-rules/NJ-UCC-DEBTOR-NAMING-TRUSTS/challenges",
            headers={
                "X-Reviewer-Role": "LICENSED_ATTORNEY",
                "X-Reviewer-Identity": "attorney@example.test",
            },
            json={
                "challenge_type": "EFFECTIVE_DATE",
                "issue": "Confirm current transition rule dates.",
                "challenged_version": {"effective_from": "2013-07-01"},
                "evidence_submitted": [],
            },
        )
        assert challenge.status_code == 200
        assert challenge.json()["challenge_state"] == "OPEN"
    finally:
        jurisdiction_router.service = original


def test_phase_2a_stale_authority_and_refresh_endpoint(tmp_path):
    original = jurisdiction_router.service
    jurisdiction_router.service = _temp_service(tmp_path)
    try:
        c = client()
        stale = c.get("/jurisdictions/NJ/stale-authorities")
        assert stale.status_code == 200
        assert any(item["source_availability_status"] == "LOCATOR_ONLY" for item in stale.json())

        refreshed = c.post(
            "/legal-authorities/NJ-UTC-2015-276/refresh-metadata",
            headers={
                "X-Reviewer-Role": "LEGAL_RESEARCHER",
                "X-Reviewer-Identity": "researcher@example.test",
            },
            json={"supplied_hash": "phase2a-test-hash", "source_available": True},
        )
        assert refreshed.status_code == 200
        assert refreshed.json()["authority_id"] == "NJ-UTC-2015-276"
        assert "audit_event" in refreshed.json()
    finally:
        jurisdiction_router.service = original


def test_phase_2a_conflicts_endpoint_and_production_gate_payload():
    c = client()
    conflicts = c.get("/jurisdictions/NJ/conflicts")
    assert conflicts.status_code == 200
    assert conflicts.json()

    detail = c.get("/jurisdictions/NJ/rules/NJ-TRUST-CERTIFICATION")
    assert detail.status_code == 200
    gate = detail.json()["production_gate"]
    assert gate["production_eligible"] is False
    assert "licensed-attorney approval is missing" in gate["blockers"]

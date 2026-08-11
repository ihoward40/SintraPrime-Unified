"""Phase 2C — Legal-reference auth boundary certification.

Governs the security contract for AuthMiddleware's legal-reference prefix rules:

  PUBLIC_GET_PREFIXES  — GET requests bypass JWT, all other methods do not.
  _is_route_authority_write_exception  — individually enumerated POST routes that
      bypass JWT and use _authorized_actor() (reviewer headers) instead.

Security matrix required for Phase 2C certification:

  GET  /federal/domains                          -> 200
  GET  /jurisdictions/NY                        -> 200
  GET  /jurisdictions/NY/review-queue           -> 403  (no reviewer headers)

  POST /ucc-filings/evaluate                    -> 403  (no reviewer headers)
  POST /legal-rules/{id}/reviews                -> 403  (no reviewer headers)
  POST /legal-authorities/{id}/refresh-metadata -> 403  (no reviewer headers)

  GET  /api/v1/cases                            -> 401  (no JWT, behind main auth wall)

Regression contract: the three protected POSTs must return 403 even with a
missing or malformed request body.  If any returns 422, the authorization gate
fires too late (after request-body validation).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from portal.main import create_app
from portal.middleware.auth_middleware import (
    PUBLIC_GET_PREFIXES,
    PUBLIC_PATHS,
    _is_route_authority_write_exception,
)


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Security matrix — GET public access
# ---------------------------------------------------------------------------


def test_federal_domains_public_get(client: TestClient):
    """GET /federal/domains is on a PUBLIC_GET_PREFIXES path — must be 200."""
    response = client.get("/federal/domains")
    assert response.status_code == 200


def test_jurisdictions_detail_public_get(client: TestClient):
    """GET /jurisdictions/NY — prefix is public for GET requests."""
    response = client.get("/jurisdictions/NY")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Security matrix — review-queue (GET but route-level auth gate)
# ---------------------------------------------------------------------------


def test_review_queue_requires_reviewer_headers(client: TestClient):
    """GET /jurisdictions/NY/review-queue passes the middleware GET check but
    the route calls _authorized_actor() — must return 403 without headers."""
    response = client.get("/jurisdictions/NY/review-queue")
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Security matrix — protected POST routes, well-formed bodies
# ---------------------------------------------------------------------------


def test_ucc_evaluate_requires_reviewer_headers(client: TestClient):
    """POST /ucc-filings/evaluate — middleware exemption, route gate returns 403."""
    response = client.post(
        "/ucc-filings/evaluate",
        json={"debtor_name": "Test Corp", "jurisdiction": "NY", "collateral_description": "equipment"},
    )
    assert response.status_code == 403


def test_legal_rules_reviews_requires_reviewer_headers(client: TestClient):
    """POST /legal-rules/{id}/reviews — middleware exemption, route gate returns 403."""
    response = client.post(
        "/legal-rules/NJ-UCC-DEBTOR-NAMING-TRUSTS/reviews",
        json={"outcome": "APPROVED", "notes": "looks good"},
    )
    assert response.status_code == 403


def test_legal_authorities_refresh_requires_reviewer_headers(client: TestClient):
    """POST /legal-authorities/{id}/refresh-metadata — middleware exemption, route gate returns 403."""
    response = client.post(
        "/legal-authorities/AUTH-001/refresh-metadata",
        json={"force": True},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Regression: 403 BEFORE 422 — missing/malformed body must not leak past auth
# ---------------------------------------------------------------------------


def test_ucc_evaluate_missing_body_returns_403_not_422(client: TestClient):
    """Auth gate fires before request-body validation — missing body still 403."""
    response = client.post("/ucc-filings/evaluate")
    assert response.status_code == 403, (
        f"Expected 403 (auth before validation), got {response.status_code}. "
        "If 422, the authorization gate is too late."
    )


def test_ucc_evaluate_malformed_body_returns_403_not_422(client: TestClient):
    """Malformed body must not reach request validation before auth check."""
    response = client.post(
        "/ucc-filings/evaluate",
        content=b"not-json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 403, (
        f"Expected 403 (auth before validation), got {response.status_code}. "
        "If 422, the authorization gate is too late."
    )


def test_legal_rules_reviews_missing_body_returns_403_not_422(client: TestClient):
    """POST /legal-rules/{id}/reviews: missing body must return 403, not 422."""
    response = client.post("/legal-rules/NJ-UCC-DEBTOR-NAMING-TRUSTS/reviews")
    assert response.status_code == 403, (
        f"Expected 403 (auth before validation), got {response.status_code}. "
        "If 422, the authorization gate is too late."
    )


def test_legal_authorities_refresh_missing_body_returns_403_not_422(client: TestClient):
    """POST /legal-authorities/{id}/refresh-metadata: missing body must return 403."""
    response = client.post("/legal-authorities/AUTH-001/refresh-metadata")
    assert response.status_code == 403, (
        f"Expected 403 (auth before validation), got {response.status_code}. "
        "If 422, the authorization gate is too late."
    )


# ---------------------------------------------------------------------------
# Security matrix — main API requires JWT
# ---------------------------------------------------------------------------


def test_cases_api_requires_auth(client: TestClient):
    """GET /api/v1/cases — behind the main JWT wall, no token -> 401."""
    response = client.get("/api/v1/cases")
    assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Unit tests — middleware helper functions
# ---------------------------------------------------------------------------


def test_public_get_prefix_is_recognised():
    """/federal/, /jurisdictions, /legal-rules/, etc. are in PUBLIC_GET_PREFIXES."""
    assert "/federal/" in PUBLIC_GET_PREFIXES
    assert "/jurisdictions" in PUBLIC_GET_PREFIXES
    assert "/legal-rules/" in PUBLIC_GET_PREFIXES
    assert "/legal-authorities/" in PUBLIC_GET_PREFIXES
    assert "/ucc-filings/" in PUBLIC_GET_PREFIXES


def test_write_exception_ucc_evaluate():
    """POST /ucc-filings/evaluate is an individually enumerated write exception."""
    assert _is_route_authority_write_exception("POST", "/ucc-filings/evaluate") is True


def test_write_exception_legal_rules_reviews():
    """POST /legal-rules/{id}/reviews is enumerated."""
    assert _is_route_authority_write_exception("POST", "/legal-rules/ABC-123/reviews") is True


def test_write_exception_legal_rules_submit_review():
    """POST /legal-rules/{id}/submit-review is enumerated."""
    assert _is_route_authority_write_exception("POST", "/legal-rules/ABC-123/submit-review") is True


def test_write_exception_legal_rules_challenges():
    """POST /legal-rules/{id}/challenges is enumerated."""
    assert _is_route_authority_write_exception("POST", "/legal-rules/ABC-123/challenges") is True


def test_write_exception_refresh_metadata():
    """POST /legal-authorities/{id}/refresh-metadata is enumerated."""
    assert _is_route_authority_write_exception("POST", "/legal-authorities/AUTH-001/refresh-metadata") is True


def test_non_enumerated_post_is_not_exempt():
    """A POST route under a public prefix that is NOT in the enumeration is not exempt."""
    assert _is_route_authority_write_exception("POST", "/legal-rules/ABC/unknown-action") is False
    assert _is_route_authority_write_exception("POST", "/ucc-filings/some-other-action") is False


def test_get_is_never_a_write_exception():
    """_is_route_authority_write_exception only applies to POST — GET always returns False."""
    assert _is_route_authority_write_exception("GET", "/ucc-filings/evaluate") is False
    assert _is_route_authority_write_exception("GET", "/legal-rules/X/reviews") is False


def test_unrelated_protected_path_requires_jwt(client: TestClient):
    """/api/v1/cases is not reachable without auth — must return 401 or 403."""
    response = client.get("/api/v1/cases")
    assert response.status_code in (401, 403)


def test_unrelated_protected_path_is_not_in_public_get_prefixes():
    """/api/v1/cases does not start with any PUBLIC_GET_PREFIXES entry."""
    assert not any("/api/v1/cases".startswith(p) for p in PUBLIC_GET_PREFIXES)


def test_review_queue_is_a_get_prefix_match():
    """/jurisdictions/NY/review-queue starts with /jurisdictions — passes middleware GET check."""
    assert any("/jurisdictions/NY/review-queue".startswith(p) for p in PUBLIC_GET_PREFIXES)


def test_post_on_public_prefix_is_not_get_exempt():
    """A POST on a PUBLIC_GET_PREFIXES path that is not write-excepted is NOT exempt."""
    # POST to /federal/ is not a write exception and is not a GET
    assert _is_route_authority_write_exception("POST", "/federal/domains") is False

"""Regression checks for the public-route method boundary.

These tests intentionally make no network calls and do not modify application data.
"""
from fastapi.testclient import TestClient

from portal.main import create_app
from portal.middleware.auth_middleware import is_public_path


def test_get_only_reference_exemptions_do_not_apply_to_writes():
    for path in (
        "/jurisdictions",
        "/jurisdictions/123",
        "/federal/statutes",
        "/ucc-filings/123",
        "/federal/rules",
    ):
        assert is_public_path(path, "GET"), path
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            assert not is_public_path(path, method), (method, path)


def test_intentional_public_post_exception_is_not_broader_than_post():
    path = "/ucc-filings/evaluate"
    assert is_public_path(path, "POST")
    assert not is_public_path(path, "PUT")
    assert not is_public_path(path, "PATCH")
    assert not is_public_path(path, "DELETE")


def test_protected_write_request_cannot_bypass_auth_via_get_only_path():
    client = TestClient(create_app())
    # Even if a particular write handler is absent, the middleware must
    # reject the unauthenticated request before invoking a protected handler.
    for method, path in (
        ("POST", "/jurisdictions"),
        ("DELETE", "/jurisdictions/123"),
        ("POST", "/federal/rules"),
        ("PUT", "/federal/statutes"),
    ):
        response = client.request(method, path)
        if response.status_code != 404:  # A genuine unmatched route may return 404.
            assert response.status_code == 401, (method, path, response.text)

"""Tests for the SP-TKM-001 consumer evidence preview router.

Tests require the SP_TKM_001_PREVIEW_ENABLED flag to be set explicitly.
By default the flag is disabled and the routes are not registered.
"""
import os

import pytest
from fastapi.testclient import TestClient

from portal.config import get_settings
from portal.main import create_app


@pytest.fixture
def preview_enabled_app(monkeypatch):
    """Create app with the SP-TKM-001 preview router enabled."""
    # Use monkeypatch to set env var, then clear cached settings
    monkeypatch.setenv("SP_TKM_001_PREVIEW_ENABLED", "true")
    # Reset cached settings
    get_settings.cache_clear()
    app = create_app()
    # Restore default after fixture teardown happens automatically with monkeypatch
    get_settings.cache_clear()
    return app


@pytest.fixture
def preview_disabled_app(monkeypatch):
    """Create app with the SP-TKM-001 preview router explicitly disabled."""
    monkeypatch.setenv("SP_TKM_001_PREVIEW_ENABLED", "false")
    get_settings.cache_clear()
    app = create_app()
    get_settings.cache_clear()
    return app


def test_flag_disabled_route_unavailable(preview_disabled_app):
    client = TestClient(preview_disabled_app)
    response = client.get("/consumer-evidence")
    assert response.status_code == 404


def test_flag_enabled_route_available(preview_enabled_app):
    client = TestClient(preview_enabled_app)
    response = client.get("/consumer-evidence")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_disclaimer_present(preview_enabled_app):
    client = TestClient(preview_enabled_app)
    response = client.get("/consumer-evidence")
    assert response.status_code == 200
    text = response.text
    assert "Educational use only" in text or "educational" in text.lower()
    assert "Not a law firm" in text


def test_no_payment_controls(preview_enabled_app):
    client = TestClient(preview_enabled_app)
    response = client.get("/consumer-evidence")
    assert response.status_code == 200
    text = response.text.lower()
    assert "stripe" not in text
    assert "credit card" not in text
    # "checkout" appears only in the disclaimer "no active checkout"; that is acceptable
    assert "buy now" not in text
    assert "pay now" not in text
    assert "add to cart" not in text
    assert "paypal" not in text
    assert "apple pay" not in text


def test_no_payment_forms(preview_enabled_app):
    client = TestClient(preview_enabled_app)
    response = client.get("/consumer-evidence")
    assert response.status_code == 200
    text = response.text.lower()
    # No input for card, account number, ssn
    assert 'type="number"' not in text
    assert 'name="card_number"' not in text
    assert "expiration" not in text
    assert "cvv" not in text
    assert 'name="account_number"' not in text
    assert 'name="ssn"' not in text
    assert 'name="social_security"' not in text
    # Legitimate email/name/topic/hidden inputs exist
    assert text.count('<input') >= 4


def test_price_displayed(preview_enabled_app):
    client = TestClient(preview_enabled_app)
    response = client.get("/consumer-evidence")
    assert response.status_code == 200
    assert "$9" in response.text


def test_utm_parameters_accepted_safely(preview_enabled_app):
    client = TestClient(preview_enabled_app)
    response = client.get(
        "/consumer-evidence?utm_source=tiktok&utm_medium=organic&utm_campaign=consumer_evidence&utm_content=UCC001"
    )
    assert response.status_code == 200


def test_unexpected_query_values_do_not_crash(preview_enabled_app):
    client = TestClient(preview_enabled_app)
    response = client.get(
        "/consumer-evidence?utm_source=%3Cscript%3Ealert(1)%3C/script%3E&utm_medium=x"
    )
    assert response.status_code == 200
    # Ensure the malicious value is not rendered literally in the HTML body
    assert "<script>alert(1)</script>" not in response.text


def test_interest_endpoint_placeholder(preview_enabled_app):
    client = TestClient(preview_enabled_app)
    payload = {
        "first_name": "Jordan",
        "email": "jordan@example.com",
        "topic": "debt",
        "utm_source": "tiktok",
        "utm_medium": "organic",
        "utm_campaign": "consumer_evidence",
        "utm_content": "UCC001",
    }
    response = client.post("/api/v1/consumer-evidence/interest", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["email"] == payload["email"]


def test_interest_endpoint_rejects_pii(preview_enabled_app):
    client = TestClient(preview_enabled_app)
    # The form does not accept SSN or account numbers; extra fields are ignored by Pydantic
    payload = {
        "first_name": "Jordan",
        "email": "jordan@example.com",
        "ssn": "123-45-6789",
        "account_number": "1234567890",
    }
    response = client.post("/api/v1/consumer-evidence/interest", json=payload)
    # Pydantic drops extra fields by default; verify they are not echoed back
    assert response.status_code == 200
    data = response.json()
    assert "ssn" not in data
    assert "account_number" not in data
    # Sanity check that the legitimate fields are accepted
    assert data["email"] == "jordan@example.com"


def test_event_endpoint_accepts_valid_event(preview_enabled_app):
    client = TestClient(preview_enabled_app)
    response = client.post(
        "/api/v1/consumer-evidence/event",
        json={"event_name": "starter_sheet_view", "url": "https://example.com/test"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_event_endpoint_rejects_invalid_event_name(preview_enabled_app):
    client = TestClient(preview_enabled_app)
    response = client.post(
        "/api/v1/consumer-evidence/event",
        json={"event_name": "bad event name!", "url": "https://example.com/test"}
    )
    assert response.status_code == 422

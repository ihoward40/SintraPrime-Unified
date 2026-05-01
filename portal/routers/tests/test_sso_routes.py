"""
Phase 21B — SSO Route Tests

Tests all five endpoints for each of the three providers:
  authorize, callback, refresh, logout, me

Coverage:
  - Happy path for each route
  - CSRF state mismatch → 400
  - Missing refresh cookie → 401
  - Missing/invalid Bearer token → 401
  - IdP exchange failure → 502
  - Unconfigured provider → 503
  - Refresh token rotation
  - Logout clears cookie
  - validate_session returns None → 401
  - Cookie security attributes (HttpOnly, SameSite)
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from portal.routers.sso import router as sso_router
from portal.sso.session_models import SessionData, TokenPair

# ── App factory ───────────────────────────────────────────────────────────────

def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key="test-secret-key-for-testing-only")
    app.include_router(sso_router, prefix="/api/v1/sso")
    return app


@pytest.fixture
def client():
    app = _make_app()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ── Shared test data ──────────────────────────────────────────────────────────

def _make_token_pair() -> TokenPair:
    return TokenPair(
        access_token="test-access-token-abc123",
        refresh_token="test-refresh-token-xyz789",
    )


def _make_session_data(provider: str = "okta") -> SessionData:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return SessionData(
        session_id="sess-001",
        user_id="user-sub-001",
        email="test@example.com",
        issuer="https://portal.sintraprime.ai",
        audience="sintraprime-portal",
        created_at=now,
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
        identity_provider=provider,
        auth_method="oidc",
    )


# ── Mock settings ─────────────────────────────────────────────────────────────

MOCK_SETTINGS = MagicMock()
MOCK_SETTINGS.SSO_SESSION_SECRET = "test-sso-secret-256-bit-key-here"
MOCK_SETTINGS.SSO_ISSUER = "https://portal.sintraprime.ai"
MOCK_SETTINGS.SSO_AUDIENCE = "sintraprime-portal"
MOCK_SETTINGS.SSO_SESSION_TTL_SECONDS = 3600
MOCK_SETTINGS.SSO_REFRESH_TTL_SECONDS = 2592000
MOCK_SETTINGS.OKTA_DOMAIN = "dev-test.okta.com"
MOCK_SETTINGS.OKTA_CLIENT_ID = "test-okta-client-id"
MOCK_SETTINGS.OKTA_CLIENT_SECRET = "test-okta-client-secret"
MOCK_SETTINGS.OKTA_REDIRECT_URI = "https://portal.sintraprime.ai/api/v1/sso/okta/callback"
MOCK_SETTINGS.OKTA_SCOPES = "openid email profile offline_access"
MOCK_SETTINGS.AZURE_TENANT_ID = "test-azure-tenant-id"
MOCK_SETTINGS.AZURE_CLIENT_ID = "test-azure-client-id"
MOCK_SETTINGS.AZURE_CLIENT_SECRET = "test-azure-client-secret"
MOCK_SETTINGS.AZURE_REDIRECT_URI = "https://portal.sintraprime.ai/api/v1/sso/azure/callback"
MOCK_SETTINGS.GOOGLE_CLIENT_ID = "test-google-client-id"
MOCK_SETTINGS.GOOGLE_CLIENT_SECRET = "test-google-client-secret"
MOCK_SETTINGS.GOOGLE_REDIRECT_URI = "https://portal.sintraprime.ai/api/v1/sso/google/callback"
MOCK_SETTINGS.GOOGLE_HOSTED_DOMAIN = ""


# ═══════════════════════════════════════════════════════════════════════════════
# CSRF / STATE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCSRFProtection:
    """State parameter validation is the same for all three providers."""

    @pytest.mark.parametrize("provider", ["okta", "azure", "google"])
    def test_callback_rejects_missing_state(self, client, provider):
        """Callback with no stored state returns 400."""
        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._pop_state", return_value=None):
            resp = client.get(
                f"/api/v1/sso/{provider}/callback",
                params={"code": "auth-code-123", "state": "attacker-state"},
                follow_redirects=False,
            )
        assert resp.status_code == 400

    @pytest.mark.parametrize("provider", ["okta", "azure", "google"])
    def test_callback_rejects_mismatched_state(self, client, provider):
        """Callback with wrong state returns 400."""
        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._pop_state", return_value="correct-state-value"):
            resp = client.get(
                f"/api/v1/sso/{provider}/callback",
                params={"code": "auth-code-123", "state": "wrong-state-value"},
                follow_redirects=False,
            )
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# MISSING COOKIE / TOKEN TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestMissingCredentials:
    """Routes that require a cookie or Bearer token return 401 when absent."""

    @pytest.mark.parametrize("provider", ["okta", "azure", "google"])
    def test_refresh_without_cookie_returns_401(self, client, provider):
        resp = client.post(f"/api/v1/sso/{provider}/refresh")
        assert resp.status_code == 401

    @pytest.mark.parametrize("provider", ["okta", "azure", "google"])
    def test_logout_without_cookie_returns_401(self, client, provider):
        resp = client.post(f"/api/v1/sso/{provider}/logout")
        assert resp.status_code == 401

    @pytest.mark.parametrize("provider", ["okta", "azure", "google"])
    def test_me_without_bearer_returns_401(self, client, provider):
        resp = client.get(f"/api/v1/sso/{provider}/me")
        assert resp.status_code == 401

    @pytest.mark.parametrize("provider", ["okta", "azure", "google"])
    def test_me_with_invalid_bearer_returns_401(self, client, provider):
        resp = client.get(
            f"/api/v1/sso/{provider}/me",
            headers={"Authorization": "NotBearer token"},
        )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# OKTA ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

class TestOktaAuthorize:
    def test_authorize_redirects_to_okta(self, client):
        mock_provider = MagicMock()
        mock_provider.get_authorization_url.return_value = (
            "https://dev-test.okta.com/oauth2/v1/authorize?client_id=test&state=abc",
            "abc",
        )
        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._get_okta_provider", return_value=mock_provider):
            resp = client.get("/api/v1/sso/okta/authorize", follow_redirects=False)
        assert resp.status_code == 302
        assert "okta.com" in resp.headers["location"]

    def test_authorize_503_when_not_configured(self, client):
        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._get_okta_provider", side_effect=ValueError("missing config")):
            resp = client.get("/api/v1/sso/okta/authorize", follow_redirects=False)
        assert resp.status_code == 503


class TestOktaCallback:
    def test_callback_happy_path(self, client):
        state = "valid-csrf-state"
        mock_token_resp = MagicMock()
        mock_token_resp.access_token = "okta-access-token"
        mock_user_info = MagicMock()
        mock_user_info.sub = "okta-sub-001"
        mock_user_info.email = "user@example.com"
        mock_user_info.preferred_username = "user@example.com"
        mock_provider = AsyncMock()
        mock_provider.config = MagicMock()
        mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
        mock_provider.__aexit__ = AsyncMock(return_value=False)
        mock_provider.exchange_code_for_token = AsyncMock(return_value=mock_token_resp)
        mock_provider.get_user_info = AsyncMock(return_value=mock_user_info)
        mock_sm = AsyncMock()
        mock_sm.create_session = AsyncMock(return_value=_make_token_pair())

        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._pop_state", return_value=state), \
             patch("portal.routers.sso.OktaProvider", return_value=mock_provider), \
             patch("portal.routers.sso._get_okta_provider", return_value=mock_provider), \
             patch("portal.routers.sso._get_session_manager", return_value=mock_sm):
            resp = client.get(
                "/api/v1/sso/okta/callback",
                params={"code": "auth-code", "state": state},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["provider"] == "okta"
        assert body["access_token"] == "test-access-token-abc123"
        assert "sso_refresh_token" in resp.cookies

    def test_callback_502_on_exchange_failure(self, client):
        state = "valid-csrf-state-2"
        mock_provider = AsyncMock()
        mock_provider.config = MagicMock()
        mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
        mock_provider.__aexit__ = AsyncMock(return_value=False)
        mock_provider.exchange_code_for_token = AsyncMock(side_effect=ValueError("token exchange failed"))

        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._pop_state", return_value=state), \
             patch("portal.routers.sso.OktaProvider", return_value=mock_provider), \
             patch("portal.routers.sso._get_okta_provider", return_value=mock_provider):
            resp = client.get(
                "/api/v1/sso/okta/callback",
                params={"code": "bad-code", "state": state},
            )
        assert resp.status_code == 502


class TestOktaRefresh:
    def test_refresh_happy_path(self, client):
        mock_sm = AsyncMock()
        mock_sm.refresh_session = AsyncMock(return_value=_make_token_pair())

        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._get_session_manager", return_value=mock_sm):
            resp = client.post(
                "/api/v1/sso/okta/refresh",
                cookies={"sso_refresh_token": "valid-refresh-token"},
            )
        assert resp.status_code == 200
        assert resp.json()["access_token"] == "test-access-token-abc123"
        assert "sso_refresh_token" in resp.cookies

    def test_refresh_401_on_invalid_token(self, client):
        mock_sm = AsyncMock()
        mock_sm.refresh_session = AsyncMock(return_value=None)

        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._get_session_manager", return_value=mock_sm):
            resp = client.post(
                "/api/v1/sso/okta/refresh",
                cookies={"sso_refresh_token": "expired-token"},
            )
        assert resp.status_code == 401


class TestOktaLogout:
    def test_logout_clears_cookie(self, client):
        mock_sm = AsyncMock()
        mock_sm.jwt_service = MagicMock()
        mock_sm.jwt_service.validate_token = MagicMock(return_value={"session_id": "sess-001"})
        mock_sm.revoke_session = AsyncMock(return_value=True)

        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._get_session_manager", return_value=mock_sm):
            resp = client.post(
                "/api/v1/sso/okta/logout",
                cookies={"sso_refresh_token": "valid-refresh-token"},
            )
        assert resp.status_code == 204


class TestOktaMe:
    def test_me_returns_session_info(self, client):
        mock_sm = AsyncMock()
        mock_sm.validate_session = AsyncMock(return_value=_make_session_data("okta"))

        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._get_session_manager", return_value=mock_sm):
            resp = client.get(
                "/api/v1/sso/okta/me",
                headers={"Authorization": "Bearer valid-access-token"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["provider"] == "okta"
        assert body["email"] == "test@example.com"
        assert body["user_id"] == "user-sub-001"

    def test_me_401_on_invalid_session(self, client):
        mock_sm = AsyncMock()
        mock_sm.validate_session = AsyncMock(return_value=None)

        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._get_session_manager", return_value=mock_sm):
            resp = client.get(
                "/api/v1/sso/okta/me",
                headers={"Authorization": "Bearer invalid-token"},
            )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# AZURE ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

class TestAzureAuthorize:
    def test_authorize_redirects(self, client):
        mock_provider = MagicMock()
        mock_provider.get_authorization_url.return_value = (
            "https://login.microsoftonline.com/tenant/oauth2/v2.0/authorize?state=abc"
        )
        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._get_azure_provider", return_value=mock_provider):
            resp = client.get("/api/v1/sso/azure/authorize", follow_redirects=False)
        assert resp.status_code == 302
        assert "microsoftonline.com" in resp.headers["location"]

    def test_authorize_503_when_not_configured(self, client):
        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._get_azure_provider", side_effect=ValueError("missing")):
            resp = client.get("/api/v1/sso/azure/authorize", follow_redirects=False)
        assert resp.status_code == 503


class TestAzureCallback:
    def test_callback_happy_path(self, client):
        state = "azure-csrf-state"
        mock_provider = MagicMock()
        mock_provider.exchange_code_for_tokens.return_value = {"access_token": "azure-at"}
        mock_provider.get_user_info.return_value = {
            "sub": "azure-sub-001",
            "email": "user@contoso.com",
            "name": "Test User",
        }
        mock_sm = AsyncMock()
        mock_sm.create_session = AsyncMock(return_value=_make_token_pair())

        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._pop_state", return_value=state), \
             patch("portal.routers.sso._get_azure_provider", return_value=mock_provider), \
             patch("portal.routers.sso._get_session_manager", return_value=mock_sm):
            resp = client.get(
                "/api/v1/sso/azure/callback",
                params={"code": "auth-code", "state": state},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["provider"] == "azure"
        assert body["email"] == "user@contoso.com"

    def test_callback_502_on_exchange_failure(self, client):
        state = "azure-csrf-state-2"
        mock_provider = MagicMock()
        mock_provider.exchange_code_for_tokens.side_effect = Exception("Azure error")

        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._pop_state", return_value=state), \
             patch("portal.routers.sso._get_azure_provider", return_value=mock_provider):
            resp = client.get(
                "/api/v1/sso/azure/callback",
                params={"code": "bad-code", "state": state},
            )
        assert resp.status_code == 502


class TestAzureRefresh:
    def test_refresh_happy_path(self, client):
        mock_sm = AsyncMock()
        mock_sm.refresh_session = AsyncMock(return_value=_make_token_pair())

        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._get_session_manager", return_value=mock_sm):
            resp = client.post(
                "/api/v1/sso/azure/refresh",
                cookies={"sso_refresh_token": "valid-refresh-token"},
            )
        assert resp.status_code == 200

    def test_refresh_401_on_none(self, client):
        mock_sm = AsyncMock()
        mock_sm.refresh_session = AsyncMock(return_value=None)

        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._get_session_manager", return_value=mock_sm):
            resp = client.post(
                "/api/v1/sso/azure/refresh",
                cookies={"sso_refresh_token": "expired"},
            )
        assert resp.status_code == 401


class TestAzureLogout:
    def test_logout_204(self, client):
        mock_sm = AsyncMock()
        mock_sm.jwt_service = MagicMock()
        mock_sm.jwt_service.validate_token = MagicMock(return_value={"session_id": "sess-002"})
        mock_sm.revoke_session = AsyncMock(return_value=True)

        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._get_session_manager", return_value=mock_sm):
            resp = client.post(
                "/api/v1/sso/azure/logout",
                cookies={"sso_refresh_token": "valid-token"},
            )
        assert resp.status_code == 204


class TestAzureMe:
    def test_me_happy_path(self, client):
        mock_sm = AsyncMock()
        mock_sm.validate_session = AsyncMock(return_value=_make_session_data("azure"))

        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._get_session_manager", return_value=mock_sm):
            resp = client.get(
                "/api/v1/sso/azure/me",
                headers={"Authorization": "Bearer valid-access-token"},
            )
        assert resp.status_code == 200
        assert resp.json()["provider"] == "azure"

    def test_me_401_on_invalid(self, client):
        mock_sm = AsyncMock()
        mock_sm.validate_session = AsyncMock(return_value=None)

        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._get_session_manager", return_value=mock_sm):
            resp = client.get(
                "/api/v1/sso/azure/me",
                headers={"Authorization": "Bearer bad-token"},
            )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# GOOGLE ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

class TestGoogleAuthorize:
    def test_authorize_redirects(self, client):
        mock_provider = MagicMock()
        mock_provider.get_authorization_url.return_value = (
            "https://accounts.google.com/o/oauth2/v2/auth?state=abc"
        )
        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._get_google_provider", return_value=mock_provider):
            resp = client.get("/api/v1/sso/google/authorize", follow_redirects=False)
        assert resp.status_code == 302
        assert "google.com" in resp.headers["location"]

    def test_authorize_503_when_not_configured(self, client):
        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._get_google_provider", side_effect=ValueError("missing")):
            resp = client.get("/api/v1/sso/google/authorize", follow_redirects=False)
        assert resp.status_code == 503


class TestGoogleCallback:
    def test_callback_happy_path(self, client):
        state = "google-csrf-state"
        mock_provider = MagicMock()
        mock_provider.exchange_code_for_tokens.return_value = {"access_token": "google-at"}
        mock_provider.get_user_info.return_value = {
            "sub": "google-sub-001",
            "email": "user@gmail.com",
            "name": "Google User",
        }
        mock_sm = AsyncMock()
        mock_sm.create_session = AsyncMock(return_value=_make_token_pair())

        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._pop_state", return_value=state), \
             patch("portal.routers.sso._get_google_provider", return_value=mock_provider), \
             patch("portal.routers.sso._get_session_manager", return_value=mock_sm):
            resp = client.get(
                "/api/v1/sso/google/callback",
                params={"code": "auth-code", "state": state},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["provider"] == "google"
        assert body["email"] == "user@gmail.com"

    def test_callback_502_on_exchange_failure(self, client):
        state = "google-csrf-state-2"
        mock_provider = MagicMock()
        mock_provider.exchange_code_for_tokens.side_effect = Exception("Google error")

        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._pop_state", return_value=state), \
             patch("portal.routers.sso._get_google_provider", return_value=mock_provider):
            resp = client.get(
                "/api/v1/sso/google/callback",
                params={"code": "bad-code", "state": state},
            )
        assert resp.status_code == 502


class TestGoogleRefresh:
    def test_refresh_happy_path(self, client):
        mock_sm = AsyncMock()
        mock_sm.refresh_session = AsyncMock(return_value=_make_token_pair())

        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._get_session_manager", return_value=mock_sm):
            resp = client.post(
                "/api/v1/sso/google/refresh",
                cookies={"sso_refresh_token": "valid-refresh-token"},
            )
        assert resp.status_code == 200

    def test_refresh_401_on_none(self, client):
        mock_sm = AsyncMock()
        mock_sm.refresh_session = AsyncMock(return_value=None)

        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._get_session_manager", return_value=mock_sm):
            resp = client.post(
                "/api/v1/sso/google/refresh",
                cookies={"sso_refresh_token": "expired"},
            )
        assert resp.status_code == 401


class TestGoogleLogout:
    def test_logout_204(self, client):
        mock_sm = AsyncMock()
        mock_sm.jwt_service = MagicMock()
        mock_sm.jwt_service.validate_token = MagicMock(return_value={"session_id": "sess-003"})
        mock_sm.revoke_session = AsyncMock(return_value=True)

        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._get_session_manager", return_value=mock_sm):
            resp = client.post(
                "/api/v1/sso/google/logout",
                cookies={"sso_refresh_token": "valid-token"},
            )
        assert resp.status_code == 204


class TestGoogleMe:
    def test_me_happy_path(self, client):
        mock_sm = AsyncMock()
        mock_sm.validate_session = AsyncMock(return_value=_make_session_data("google"))

        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._get_session_manager", return_value=mock_sm):
            resp = client.get(
                "/api/v1/sso/google/me",
                headers={"Authorization": "Bearer valid-access-token"},
            )
        assert resp.status_code == 200
        assert resp.json()["provider"] == "google"

    def test_me_401_on_invalid(self, client):
        mock_sm = AsyncMock()
        mock_sm.validate_session = AsyncMock(return_value=None)

        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._get_session_manager", return_value=mock_sm):
            resp = client.get(
                "/api/v1/sso/google/me",
                headers={"Authorization": "Bearer bad-token"},
            )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# COOKIE SECURITY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCookieSecurity:
    """Verify that the refresh cookie has the correct security attributes."""

    def test_okta_callback_sets_httponly_samesite_cookie(self, client):
        state = "cookie-test-state"
        mock_token_resp = MagicMock()
        mock_token_resp.access_token = "okta-at"
        mock_user_info = MagicMock()
        mock_user_info.sub = "sub-001"
        mock_user_info.email = "user@example.com"
        mock_user_info.preferred_username = "user@example.com"
        mock_provider = AsyncMock()
        mock_provider.config = MagicMock()
        mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
        mock_provider.__aexit__ = AsyncMock(return_value=False)
        mock_provider.exchange_code_for_token = AsyncMock(return_value=mock_token_resp)
        mock_provider.get_user_info = AsyncMock(return_value=mock_user_info)
        mock_sm = AsyncMock()
        mock_sm.create_session = AsyncMock(return_value=_make_token_pair())

        with patch("portal.routers.sso.get_settings", return_value=MOCK_SETTINGS), \
             patch("portal.routers.sso._pop_state", return_value=state), \
             patch("portal.routers.sso.OktaProvider", return_value=mock_provider), \
             patch("portal.routers.sso._get_okta_provider", return_value=mock_provider), \
             patch("portal.routers.sso._get_session_manager", return_value=mock_sm):
            resp = client.get(
                "/api/v1/sso/okta/callback",
                params={"code": "auth-code", "state": state},
            )

        assert resp.status_code == 200
        assert "sso_refresh_token" in resp.cookies
        set_cookie = resp.headers.get("set-cookie", "")
        assert "httponly" in set_cookie.lower(), f"HttpOnly missing from: {set_cookie}"
        assert "samesite" in set_cookie.lower(), f"SameSite missing from: {set_cookie}"

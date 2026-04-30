"""
Okta SSO provider tests (16 tests).
Tests use dependency injection to mock httpx.AsyncClient — no real network calls.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from portal.sso.okta_config import OktaConfig
from portal.sso.okta_models import OktaTokenResponse, OktaUserInfo
from portal.sso.okta_provider import OktaProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**kwargs):
    defaults = dict(
        okta_domain="https://dev-12345.okta.com",
        client_id="test_client_id",
        client_secret="test_client_secret",
        redirect_uri="http://localhost:8000/callback",
    )
    defaults.update(kwargs)
    return OktaConfig(**defaults)


def _mock_response(json_data: dict, status_code: int = 200):
    """Create a mock httpx Response-like object."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()  # no-op for 2xx
    return resp


def _mock_client(post_resp=None, get_resp=None):
    """Create a mock AsyncClient with configurable post/get responses."""
    client = AsyncMock()
    if post_resp is not None:
        client.post = AsyncMock(return_value=post_resp)
    if get_resp is not None:
        client.get = AsyncMock(return_value=get_resp)
    return client


# ---------------------------------------------------------------------------
# OktaConfig tests (7)
# ---------------------------------------------------------------------------

class TestOktaConfig:
    """Okta configuration validation tests."""

    def test_valid_config(self):
        config = _make_config()
        assert config.okta_domain == "https://dev-12345.okta.com"
        assert config.client_id == "test_client_id"
        assert config.scopes == ["openid", "profile", "email"]

    def test_missing_domain_raises(self):
        with pytest.raises(ValueError, match="okta_domain must be absolute HTTPS URL"):
            _make_config(okta_domain="")

    def test_http_domain_raises(self):
        with pytest.raises(ValueError, match="okta_domain must be absolute HTTPS URL"):
            _make_config(okta_domain="http://dev-12345.okta.com")

    def test_missing_client_id_raises(self):
        with pytest.raises(ValueError, match="client_id is required"):
            _make_config(client_id="")

    def test_missing_client_secret_raises(self):
        with pytest.raises(ValueError, match="client_secret is required"):
            _make_config(client_secret="")

    def test_missing_redirect_uri_raises(self):
        with pytest.raises(ValueError, match="redirect_uri is required"):
            _make_config(redirect_uri="")

    def test_custom_scopes(self):
        config = _make_config(scopes=["openid", "groups"])
        assert config.scopes == ["openid", "groups"]


# ---------------------------------------------------------------------------
# OktaProvider tests (9)
# ---------------------------------------------------------------------------

class TestOktaProvider:
    """Okta OAuth 2.0 provider tests — all async HTTP calls use injected mocks."""

    @pytest.fixture
    def config(self):
        return _make_config()

    # --- get_authorization_url (sync) ---

    def test_get_authorization_url_contains_required_params(self, config):
        provider = OktaProvider(config)
        url, state = provider.get_authorization_url()
        assert "oauth2/v1/authorize" in url
        assert "client_id=test_client_id" in url
        assert "response_type=code" in url
        assert f"state={state}" in url
        assert len(state) > 20  # urlsafe token

    def test_get_authorization_url_with_custom_state(self, config):
        provider = OktaProvider(config)
        url, state = provider.get_authorization_url(state="custom_state_xyz")
        assert state == "custom_state_xyz"
        assert "state=custom_state_xyz" in url

    # --- exchange_code_for_token (async, mocked) ---

    @pytest.mark.asyncio
    async def test_exchange_code_returns_token_response(self, config):
        token_data = {
            "access_token": "at_abc123",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "openid profile email",
            "id_token": "id_xyz",
        }
        client = _mock_client(post_resp=_mock_response(token_data))
        provider = OktaProvider(config, client=client)

        result = await provider.exchange_code_for_token("auth_code_123")

        assert result.access_token == "at_abc123"
        assert result.token_type == "Bearer"
        assert result.id_token == "id_xyz"
        client.post.assert_called_once()
        call_args = client.post.call_args
        assert "oauth2/v1/token" in call_args[0][0]
        assert call_args[1]["timeout"] == config.timeout_seconds

    @pytest.mark.asyncio
    async def test_exchange_empty_code_raises(self, config):
        provider = OktaProvider(config)
        with pytest.raises(ValueError, match="code is required"):
            await provider.exchange_code_for_token("")

    @pytest.mark.asyncio
    async def test_exchange_http_error_raises_value_error(self, config):
        import httpx
        error_resp = MagicMock()
        error_resp.status_code = 401
        error_resp.text = "Unauthorized"
        http_error = httpx.HTTPStatusError("401", request=MagicMock(), response=error_resp)
        client = AsyncMock()
        client.post = AsyncMock(side_effect=http_error)
        provider = OktaProvider(config, client=client)

        with pytest.raises(ValueError, match="Okta token exchange failed: 401"):
            await provider.exchange_code_for_token("bad_code")

    # --- get_user_info (async, mocked) ---

    @pytest.mark.asyncio
    async def test_get_user_info_returns_user_info(self, config):
        user_data = {
            "sub": "okta_user_001",
            "email": "alice@example.com",
            "email_verified": True,
            "name": "Alice Smith",
            "given_name": "Alice",
            "family_name": "Smith",
        }
        client = _mock_client(get_resp=_mock_response(user_data))
        provider = OktaProvider(config, client=client)

        result = await provider.get_user_info("valid_access_token")

        assert result.sub == "okta_user_001"
        assert result.email == "alice@example.com"
        assert result.email_verified is True
        client.get.assert_called_once()
        call_args = client.get.call_args
        assert "oauth2/v1/userinfo" in call_args[0][0]
        assert "Bearer valid_access_token" in call_args[1]["headers"]["Authorization"]

    @pytest.mark.asyncio
    async def test_get_user_info_empty_token_raises(self, config):
        provider = OktaProvider(config)
        with pytest.raises(ValueError, match="access_token is required"):
            await provider.get_user_info("")

    @pytest.mark.asyncio
    async def test_get_user_info_http_error_raises_value_error(self, config):
        import httpx
        error_resp = MagicMock()
        error_resp.status_code = 403
        error_resp.text = "Forbidden"
        http_error = httpx.HTTPStatusError("403", request=MagicMock(), response=error_resp)
        client = AsyncMock()
        client.get = AsyncMock(side_effect=http_error)
        provider = OktaProvider(config, client=client)

        with pytest.raises(ValueError, match="Okta userinfo request failed: 403"):
            await provider.get_user_info("expired_token")

    # --- validate_state ---

    def test_validate_state_matching(self, config):
        provider = OktaProvider(config)
        assert provider.validate_state("abc123", "abc123") is True

    def test_validate_state_mismatch(self, config):
        provider = OktaProvider(config)
        assert provider.validate_state("abc123", "xyz789") is False

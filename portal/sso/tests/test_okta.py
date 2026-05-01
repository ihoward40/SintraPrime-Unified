"""
Tests for Okta OAuth 2.0 provider.

Coverage:
  - OktaConfig: validation, from_env() with valid env vars, missing vars
  - OktaProvider: authorization URL, token exchange (success + HTTP errors),
    userinfo (success + HTTP errors), refresh with revocation, state validation
  - OktaTokenResponse / OktaUserInfo: model fields including new fields
"""
import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from portal.sso.okta_config import OktaConfig
from portal.sso.okta_models import OktaTokenResponse, OktaUserInfo
from portal.sso.okta_provider import OktaProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_ENV = {
    "OKTA_DOMAIN": "https://dev-12345.okta.com",
    "OKTA_CLIENT_ID": "env_client_id",
    "OKTA_CLIENT_SECRET": "env_client_secret",
    "OKTA_REDIRECT_URI": "https://app.example.com/callback",
    "OKTA_SCOPES": "openid,profile,email",
    "OKTA_TIMEOUT_SECONDS": "15",
}


def _make_http_status_error(status_code: int) -> httpx.HTTPStatusError:
    """Build a realistic HTTPStatusError for testing."""
    request = httpx.Request("GET", "https://dev-12345.okta.com/oauth2/v1/token")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError(
        f"HTTP {status_code}", request=request, response=response
    )


# ---------------------------------------------------------------------------
# OktaConfig tests
# ---------------------------------------------------------------------------


class TestOktaConfig:
    def test_init_valid(self):
        cfg = OktaConfig(
            okta_domain="https://dev-12345.okta.com",
            client_id="cid",
            client_secret="csec",
            redirect_uri="https://app.example.com/cb",
        )
        assert cfg.okta_domain == "https://dev-12345.okta.com"
        assert cfg.scopes == ["openid", "profile", "email"]
        assert cfg.timeout_seconds == 30

    def test_missing_domain(self):
        with pytest.raises(ValueError, match="okta_domain"):
            OktaConfig(
                okta_domain="",
                client_id="cid",
                client_secret="csec",
                redirect_uri="https://app.example.com/cb",
            )

    def test_invalid_protocol(self):
        with pytest.raises(ValueError, match="HTTPS"):
            OktaConfig(
                okta_domain="http://dev-12345.okta.com",
                client_id="cid",
                client_secret="csec",
                redirect_uri="https://app.example.com/cb",
            )

    def test_missing_client_id(self):
        with pytest.raises(ValueError, match="client_id"):
            OktaConfig(
                okta_domain="https://dev-12345.okta.com",
                client_id="",
                client_secret="csec",
                redirect_uri="https://app.example.com/cb",
            )

    def test_missing_redirect_uri(self):
        with pytest.raises(ValueError, match="redirect_uri"):
            OktaConfig(
                okta_domain="https://dev-12345.okta.com",
                client_id="cid",
                client_secret="csec",
                redirect_uri="",
            )

    def test_from_env_success(self):
        """from_env() must construct a valid OktaConfig from environment variables."""
        with patch.dict(os.environ, VALID_ENV, clear=False):
            cfg = OktaConfig.from_env()
        assert cfg.okta_domain == "https://dev-12345.okta.com"
        assert cfg.client_id == "env_client_id"
        assert cfg.client_secret == "env_client_secret"
        assert cfg.redirect_uri == "https://app.example.com/callback"
        assert cfg.scopes == ["openid", "profile", "email"]
        assert cfg.timeout_seconds == 15

    def test_from_env_missing_var(self):
        """from_env() must raise ValueError when a required env var is absent."""
        env_without_secret = {k: v for k, v in VALID_ENV.items() if k != "OKTA_CLIENT_SECRET"}
        with patch.dict(os.environ, env_without_secret, clear=False):
            # Ensure the variable is actually absent
            os.environ.pop("OKTA_CLIENT_SECRET", None)
            with pytest.raises(ValueError, match="OKTA_CLIENT_SECRET"):
                OktaConfig.from_env()


# ---------------------------------------------------------------------------
# OktaProvider tests
# ---------------------------------------------------------------------------


class TestOktaProvider:
    @pytest.fixture
    def config(self):
        return OktaConfig(
            okta_domain="https://dev-12345.okta.com",
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost:8000/callback",
            timeout_seconds=10,
        )

    @pytest.fixture
    def mock_client(self):
        return AsyncMock(spec=httpx.AsyncClient)

    # --- Authorization URL ---

    def test_get_authorization_url_with_state(self, config):
        provider = OktaProvider(config)
        url, state = provider.get_authorization_url(state="csrf_abc")
        assert "https://dev-12345.okta.com/oauth2/v1/authorize?" in url
        assert "client_id=test_client_id" in url
        assert "response_type=code" in url
        assert state == "csrf_abc"

    def test_get_authorization_url_auto_state(self, config):
        provider = OktaProvider(config)
        url, state = provider.get_authorization_url()
        assert state is not None and len(state) > 0
        assert "state=" + state in url

    # --- Timeout is sourced from config ---

    def test_timeout_applied_from_config(self, config):
        """OktaProvider must use config.timeout_seconds, not a hardcoded value."""
        provider = OktaProvider(config)
        assert provider._timeout.connect == float(config.timeout_seconds)

    # --- Token exchange success ---

    @pytest.mark.asyncio
    async def test_exchange_code_for_token(self, config, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "at_xyz",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "openid profile email",
            "id_token": "id_abc",
            "refresh_token": "rt_123",
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        provider = OktaProvider(config, client=mock_client)
        token = await provider.exchange_code_for_token("auth_code_123")

        assert token.access_token == "at_xyz"
        assert token.id_token == "id_abc"
        assert token.refresh_token == "rt_123"
        mock_client.post.assert_called_once()
        mock_response.raise_for_status.assert_called_once()

    # --- Token exchange empty code ---

    @pytest.mark.asyncio
    async def test_exchange_code_empty_code(self, config):
        provider = OktaProvider(config)
        with pytest.raises(ValueError, match="code is required"):
            await provider.exchange_code_for_token("")

    # --- Token exchange HTTP error → ValueError ---

    @pytest.mark.asyncio
    async def test_exchange_code_http_error_raises_value_error(self, config, mock_client):
        """HTTP 401 from Okta token endpoint must raise ValueError, not HTTPStatusError."""
        mock_client.post.side_effect = _make_http_status_error(401)

        provider = OktaProvider(config, client=mock_client)
        with pytest.raises(ValueError, match="401"):
            await provider.exchange_code_for_token("bad_code")

    # --- Userinfo success ---

    @pytest.mark.asyncio
    async def test_get_user_info(self, config, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "sub": "00u123xyz",
            "email": "user@example.com",
            "email_verified": True,
            "name": "Test User",
            "preferred_username": "user@example.com",
            "groups": ["Everyone", "Admins"],
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        provider = OktaProvider(config, client=mock_client)
        info = await provider.get_user_info("access_token_xyz")

        assert info.sub == "00u123xyz"
        assert info.email == "user@example.com"
        assert info.email_verified is True
        assert info.preferred_username == "user@example.com"
        assert info.groups == ["Everyone", "Admins"]
        mock_client.get.assert_called_once()
        mock_response.raise_for_status.assert_called_once()

    # --- Userinfo empty token ---

    @pytest.mark.asyncio
    async def test_get_user_info_empty_token(self, config):
        provider = OktaProvider(config)
        with pytest.raises(ValueError, match="access_token is required"):
            await provider.get_user_info("")

    # --- Userinfo HTTP error → ValueError ---

    @pytest.mark.asyncio
    async def test_get_user_info_http_error_raises_value_error(self, config, mock_client):
        """HTTP 403 from Okta userinfo endpoint must raise ValueError."""
        mock_client.get.side_effect = _make_http_status_error(403)

        provider = OktaProvider(config, client=mock_client)
        with pytest.raises(ValueError, match="403"):
            await provider.get_user_info("bad_token")

    # --- Refresh with revocation ---

    @pytest.mark.asyncio
    async def test_refresh_access_token_revokes_old_token(self, config, mock_client):
        """refresh_access_token must call /revoke before /token."""
        revoke_response = MagicMock()
        revoke_response.raise_for_status = MagicMock()

        new_token_response = MagicMock()
        new_token_response.json.return_value = {
            "access_token": "new_at",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "openid profile email",
            "refresh_token": "new_rt",
        }
        new_token_response.raise_for_status = MagicMock()

        # post is called twice: first revoke, then token exchange
        mock_client.post.side_effect = [revoke_response, new_token_response]

        provider = OktaProvider(config, client=mock_client)
        token = await provider.refresh_access_token("old_rt")

        assert token.access_token == "new_at"
        assert token.refresh_token == "new_rt"
        assert mock_client.post.call_count == 2
        # First call must be to the revoke endpoint
        first_call_url = mock_client.post.call_args_list[0][0][0]
        assert "/oauth2/v1/revoke" in first_call_url

    @pytest.mark.asyncio
    async def test_refresh_access_token_empty_raises(self, config):
        provider = OktaProvider(config)
        with pytest.raises(ValueError, match="refresh_token is required"):
            await provider.refresh_access_token("")

    # --- State validation ---

    def test_validate_state_valid(self, config):
        provider = OktaProvider(config)
        assert provider.validate_state("abc", "abc") is True

    def test_validate_state_invalid(self, config):
        provider = OktaProvider(config)
        assert provider.validate_state("abc", "xyz") is False

    # --- Model fields ---

    def test_response_models_new_fields(self, config):
        token = OktaTokenResponse(
            access_token="at",
            token_type="Bearer",
            expires_in=3600,
            scope="openid",
            id_token="id",
            refresh_token="rt",
        )
        assert token.refresh_token == "rt"

        user = OktaUserInfo(
            sub="00u1",
            email="u@example.com",
            email_verified=True,
            name="U",
            preferred_username="u@example.com",
            groups=["Admins"],
        )
        assert user.preferred_username == "u@example.com"
        assert user.groups == ["Admins"]

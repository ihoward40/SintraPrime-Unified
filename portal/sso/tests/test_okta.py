"""
Tests for Okta OAuth 2.0 provider and configuration.

All tests are mocked; no real network calls.
"""

import os
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from portal.sso.okta_config import OktaConfig
from portal.sso.okta_models import OktaTokenResponse, OktaUserInfo
from portal.sso.okta_provider import OktaProvider


class TestOktaConfig:
    """Test OktaConfig validation and initialization."""

    def test_init_valid(self):
        """Test valid OktaConfig initialization."""
        config = OktaConfig(
            okta_domain="https://dev-12345.okta.com",
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost:8000/callback",
        )
        assert config.okta_domain == "https://dev-12345.okta.com"
        assert config.client_id == "test_client_id"
        assert config.scopes == ["openid", "profile", "email"]

    def test_missing_domain(self):
        """Test missing okta_domain raises ValueError."""
        with pytest.raises(ValueError, match="okta_domain"):
            OktaConfig(
                okta_domain="",
                client_id="test",
                client_secret="test",
                redirect_uri="http://localhost:8000/callback",
            )

    def test_invalid_protocol(self):
        """Test invalid protocol in okta_domain raises ValueError."""
        with pytest.raises(ValueError, match="HTTPS URL"):
            OktaConfig(
                okta_domain="http://dev-12345.okta.com",
                client_id="test",
                client_secret="test",
                redirect_uri="http://localhost:8000/callback",
            )

    def test_missing_client_id(self):
        """Test missing client_id raises ValueError."""
        with pytest.raises(ValueError, match="client_id"):
            OktaConfig(
                okta_domain="https://dev-12345.okta.com",
                client_id="",
                client_secret="test",
                redirect_uri="http://localhost:8000/callback",
            )

    def test_missing_redirect_uri(self):
        """Test missing redirect_uri raises ValueError."""
        with pytest.raises(ValueError, match="redirect_uri"):
            OktaConfig(
                okta_domain="https://dev-12345.okta.com",
                client_id="test",
                client_secret="test",
                redirect_uri="",
            )

    def test_from_env_success(self):
        """Test OktaConfig.from_env() with valid environment variables."""
        # Set up environment
        os.environ["OKTA_DOMAIN"] = "https://dev-12345.okta.com"
        os.environ["OKTA_CLIENT_ID"] = "env_client_id"
        os.environ["OKTA_CLIENT_SECRET"] = "env_client_secret"
        os.environ["OKTA_REDIRECT_URI"] = "http://localhost:8000/callback"

        try:
            config = OktaConfig.from_env()
            assert config.okta_domain == "https://dev-12345.okta.com"
            assert config.client_id == "env_client_id"
            assert config.client_secret == "env_client_secret"
            assert config.redirect_uri == "http://localhost:8000/callback"
        finally:
            # Clean up
            os.environ.pop("OKTA_DOMAIN", None)
            os.environ.pop("OKTA_CLIENT_ID", None)
            os.environ.pop("OKTA_CLIENT_SECRET", None)
            os.environ.pop("OKTA_REDIRECT_URI", None)

    def test_from_env_missing_var(self):
        """Test OktaConfig.from_env() with missing environment variable."""
        # Ensure variable is missing
        os.environ.pop("OKTA_DOMAIN", None)

        with pytest.raises((KeyError, ValueError)):
            OktaConfig.from_env()


class TestOktaProvider:
    """Test OktaProvider OAuth 2.0 flow."""

    @pytest.fixture
    def config(self):
        """Fixture providing test OktaConfig."""
        return OktaConfig(
            okta_domain="https://dev-12345.okta.com",
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost:8000/callback",
        )

    @pytest.fixture
    def mock_client(self):
        """Fixture providing mocked httpx.AsyncClient."""
        return AsyncMock(spec=httpx.AsyncClient)

    def test_get_authorization_url_with_state(self, config):
        """Test authorization URL generation with provided state."""
        provider = OktaProvider(config)
        auth_url, returned_state = provider.get_authorization_url(
            state="test_state_123"
        )

        assert "https://dev-12345.okta.com/oauth2/v1/authorize?" in auth_url
        assert "client_id=test_client_id" in auth_url
        assert "response_type=code" in auth_url
        assert "scope=openid+profile+email" in auth_url
        assert returned_state == "test_state_123"

    def test_get_authorization_url_auto_state(self, config):
        """Test authorization URL generation with auto-generated state."""
        provider = OktaProvider(config)
        auth_url, returned_state = provider.get_authorization_url()

        assert "https://dev-12345.okta.com/oauth2/v1/authorize?" in auth_url
        assert returned_state is not None
        assert len(returned_state) > 0

    @pytest.mark.asyncio
    async def test_exchange_code_for_token(self, config, mock_client):
        """Test authorization code exchange with real HTTP boundary."""
        provider = OktaProvider(config, client=mock_client)

        # Mock successful token response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "real_okta_access_token_xyz",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "openid profile email",
            "id_token": "real_okta_id_token_abc",
        }
        mock_client.post.return_value = mock_response

        token = await provider.exchange_code_for_token("auth_code_123")

        assert token.access_token == "real_okta_access_token_xyz"
        assert token.id_token == "real_okta_id_token_abc"
        assert token.token_type == "Bearer"
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_exchange_code_empty_code(self, config):
        """Test exchange_code_for_token with empty code raises ValueError."""
        provider = OktaProvider(config)

        with pytest.raises(ValueError, match="code is required"):
            await provider.exchange_code_for_token("")

    @pytest.mark.asyncio
    async def test_get_user_info(self, config, mock_client):
        """Test user info retrieval with real HTTP boundary."""
        provider = OktaProvider(config, client=mock_client)

        # Mock successful userinfo response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "sub": "00u123xyz",
            "email": "user@example.com",
            "email_verified": True,
            "name": "Test User",
        }
        mock_client.get.return_value = mock_response

        user_info = await provider.get_user_info("real_access_token_xyz")

        assert user_info.sub == "00u123xyz"
        assert user_info.email == "user@example.com"
        assert user_info.email_verified is True
        assert user_info.name == "Test User"
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_info_empty_token(self, config):
        """Test get_user_info with empty token raises ValueError."""
        provider = OktaProvider(config)

        with pytest.raises(ValueError, match="access_token is required"):
            await provider.get_user_info("")

    def test_validate_state_valid(self, config):
        """Test state validation with matching state."""
        provider = OktaProvider(config)
        assert provider.validate_state("test_state", "test_state") is True

    def test_validate_state_invalid(self, config):
        """Test state validation with non-matching state."""
        provider = OktaProvider(config)
        assert provider.validate_state("test_state", "different_state") is False

    def test_response_models(self, config):
        """Test OktaTokenResponse and OktaUserInfo model parsing."""
        token = OktaTokenResponse(
            access_token="token_xyz",
            token_type="Bearer",
            expires_in=3600,
            scope="openid",
            id_token="id_token_abc",
        )
        assert token.access_token == "token_xyz"
        assert token.id_token == "id_token_abc"

        user = OktaUserInfo(
            sub="00u123",
            email="user@example.com",
            email_verified=True,
            name="Test User",
        )
        assert user.email == "user@example.com"

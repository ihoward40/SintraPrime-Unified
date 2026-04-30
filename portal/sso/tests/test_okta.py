"""
Okta SSO provider tests (12 tests).
"""

import pytest

from portal.sso.okta_config import OktaConfig
from portal.sso.okta_models import OktaTokenResponse, OktaUserInfo
from portal.sso.okta_provider import OktaProvider


class TestOktaConfig:
    """Okta configuration tests."""

    def test_okta_config_init_valid(self):
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

    def test_okta_config_missing_domain(self):
        """Test OktaConfig raises ValueError if domain is missing."""
        with pytest.raises(ValueError, match="okta_domain must be absolute HTTPS URL"):
            OktaConfig(
                okta_domain="",
                client_id="test_client_id",
                client_secret="test_client_secret",
                redirect_uri="http://localhost:8000/callback",
            )

    def test_okta_config_invalid_domain_protocol(self):
        """Test OktaConfig raises ValueError if domain is not HTTPS."""
        with pytest.raises(ValueError, match="okta_domain must be absolute HTTPS URL"):
            OktaConfig(
                okta_domain="http://dev-12345.okta.com",
                client_id="test_client_id",
                client_secret="test_client_secret",
                redirect_uri="http://localhost:8000/callback",
            )

    def test_okta_config_missing_client_id(self):
        """Test OktaConfig raises ValueError if client_id is missing."""
        with pytest.raises(ValueError, match="client_id is required"):
            OktaConfig(
                okta_domain="https://dev-12345.okta.com",
                client_id="",
                client_secret="test_client_secret",
                redirect_uri="http://localhost:8000/callback",
            )

    def test_okta_config_missing_redirect_uri(self):
        """Test OktaConfig raises ValueError if redirect_uri is missing."""
        with pytest.raises(ValueError, match="redirect_uri is required"):
            OktaConfig(
                okta_domain="https://dev-12345.okta.com",
                client_id="test_client_id",
                client_secret="test_client_secret",
                redirect_uri="",
            )


class TestOktaProvider:
    """Okta OAuth 2.0 provider tests."""

    @pytest.fixture
    def config(self):
        """Create test OktaConfig."""
        return OktaConfig(
            okta_domain="https://dev-12345.okta.com",
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost:8000/callback",
        )

    @pytest.fixture
    def provider(self, config):
        """Create test OktaProvider."""
        return OktaProvider(config)

    def test_get_authorization_url(self, provider):
        """Test authorization URL generation."""
        auth_url, state = provider.get_authorization_url()
        assert "oauth2/v1/authorize" in auth_url
        assert "client_id=test_client_id" in auth_url
        assert "response_type=code" in auth_url
        assert state is not None
        assert len(state) > 0

    def test_get_authorization_url_with_custom_state(self, provider):
        """Test authorization URL with custom state."""
        custom_state = "my_custom_state_123"
        auth_url, state = provider.get_authorization_url(state=custom_state)
        assert state == custom_state
        assert f"state={custom_state}" in auth_url

    def test_exchange_code_for_token(self, provider):
        """Test authorization code exchange."""
        token_response = provider.exchange_code_for_token(code="auth_code_123")
        assert token_response.access_token is not None
        assert token_response.token_type == "Bearer"
        assert token_response.expires_in > 0
        assert token_response.id_token is not None

    def test_exchange_code_empty_fails(self, provider):
        """Test exchange with empty code raises ValueError."""
        with pytest.raises(ValueError, match="code is required"):
            provider.exchange_code_for_token(code="")

    def test_get_user_info(self, provider):
        """Test userinfo endpoint."""
        user_info = provider.get_user_info(access_token="test_token_123")
        assert user_info.sub is not None
        assert user_info.email is not None
        assert user_info.email_verified is True
        assert user_info.name is not None

    def test_get_user_info_empty_token_fails(self, provider):
        """Test userinfo with empty token raises ValueError."""
        with pytest.raises(ValueError, match="access_token is required"):
            provider.get_user_info(access_token="")

    def test_validate_state_valid(self, provider):
        """Test state validation passes for matching state."""
        state = "test_state_123"
        assert provider.validate_state(state, state) is True

    def test_validate_state_invalid(self, provider):
        """Test state validation fails for non-matching state."""
        assert provider.validate_state("state1", "state2") is False

    def test_okta_token_response_from_dict(self):
        """Test OktaTokenResponse from dict."""
        data = {
            "access_token": "test_access",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "openid profile email",
            "id_token": "test_id_token",
        }
        token = OktaTokenResponse.from_dict(data)
        assert token.access_token == "test_access"
        assert token.expires_in == 3600

    def test_okta_user_info_from_dict(self):
        """Test OktaUserInfo from dict."""
        data = {
            "sub": "okta_user_123",
            "email": "user@example.com",
            "email_verified": True,
            "name": "Test User",
        }
        user = OktaUserInfo.from_dict(data)
        assert user.sub == "okta_user_123"
        assert user.email == "user@example.com"
        assert user.email_verified is True
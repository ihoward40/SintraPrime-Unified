<<<<<<< HEAD
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
=======
import unittest
from unittest.mock import patch, MagicMock
import requests
import hashlib
import base64
from urllib.parse import urlparse, parse_qs, quote_plus

from portal.sso.providers.okta import OktaConfig, OktaProvider, generate_pkce_pair

class TestOktaConfig(unittest.TestCase):

    def test_config_initialization_success(self):
        config = OktaConfig("client_id", "client_secret", "example.okta.com", "https://redirect.uri")
        self.assertEqual(config.client_id, "client_id")
        self.assertEqual(config.client_secret, "client_secret")
        self.assertEqual(config.domain, "example.okta.com")
        self.assertEqual(config.redirect_uri, "https://redirect.uri")
        self.assertEqual(config.scopes, ["openid", "email", "profile"])
        self.assertIn("example.okta.com", config.authorize_url)
        self.assertIn("example.okta.com", config.token_url)
        self.assertIn("example.okta.com", config.userinfo_url)
        self.assertIn("example.okta.com", config.revoke_url)
        self.assertIn("example.okta.com", config.jwks_url)

    def test_config_initialization_with_custom_scopes(self):
        config = OktaConfig("client_id", "client_secret", "example.okta.com", "https://redirect.uri", scopes=["custom_scope"])
        self.assertEqual(config.scopes, ["custom_scope"])

    def test_config_initialization_missing_client_id(self):
        with self.assertRaisesRegex(ValueError, "client_id"):
            OktaConfig(None, "client_secret", "example.okta.com", "https://redirect.uri")

    def test_config_initialization_missing_client_secret(self):
        with self.assertRaisesRegex(ValueError, "client_secret"):
            OktaConfig("client_id", None, "example.okta.com", "https://redirect.uri")

    def test_config_initialization_missing_domain(self):
        with self.assertRaisesRegex(ValueError, "domain"):
            OktaConfig("client_id", "client_secret", None, "https://redirect.uri")

    def test_config_initialization_missing_redirect_uri(self):
        with self.assertRaisesRegex(ValueError, "redirect_uri"):
            OktaConfig("client_id", "client_secret", "example.okta.com", None)

class TestOktaProvider(unittest.TestCase):

    def setUp(self):
        self.config = OktaConfig("test_client_id", "test_client_secret", "test.okta.com", "https://test.redirect.uri")
        self.provider = OktaProvider(self.config)
        self.code_verifier = "test_code_verifier"
        self.code_challenge = base64.urlsafe_b64encode(hashlib.sha256(self.code_verifier.encode("ascii")).digest()).decode().rstrip("=")

    def test_get_authorization_url(self):
        state = "test_state"
        auth_url = self.provider.get_authorization_url(state, self.code_challenge)

        parsed_url = urlparse(auth_url)
        query_params = parse_qs(parsed_url.query)

        self.assertEqual(parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path, self.config.authorize_url)
        self.assertEqual(query_params["client_id"][0], self.config.client_id)
        self.assertEqual(query_params["response_type"][0], "code")
        self.assertEqual(query_params["scope"][0], " ".join(self.config.scopes))
        self.assertEqual(query_params["redirect_uri"][0], self.config.redirect_uri)
        self.assertEqual(query_params["state"][0], state)
        self.assertEqual(query_params["code_challenge"][0], self.code_challenge)
        self.assertEqual(query_params["code_challenge_method"][0], "S256")

    @patch("requests.post")
    def test_exchange_code_for_tokens_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "mock_access_token",
            "id_token": "mock_id_token",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        mock_post.return_value = mock_response

        code = "test_code"
        tokens = self.provider.exchange_code_for_tokens(code, self.code_verifier)

        mock_post.assert_called_once_with(
            self.config.token_url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "authorization_code",
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "redirect_uri": self.config.redirect_uri,
                "code": code,
                "code_verifier": self.code_verifier,
            },
            timeout=10,
        )
        self.assertEqual(tokens["access_token"], "mock_access_token")

    @patch("requests.post")
    def test_exchange_code_for_tokens_failure(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = requests.exceptions.RequestException("Bad Request")
        mock_post.return_value = mock_response

        with self.assertRaises(requests.exceptions.RequestException):
            self.provider.exchange_code_for_tokens("invalid_code", self.code_verifier)

    @patch("requests.get")
    def test_get_user_info_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"sub": "user123", "name": "Test User"}
        mock_get.return_value = mock_response

        access_token = "mock_access_token"
        user_info = self.provider.get_user_info(access_token)

        mock_get.assert_called_once_with(
            self.config.userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        self.assertEqual(user_info["sub"], "user123")

    @patch("requests.get")
    def test_get_user_info_failure(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.exceptions.RequestException("Unauthorized")
        mock_get.return_value = mock_response

        with self.assertRaises(requests.exceptions.RequestException):
            self.provider.get_user_info("invalid_access_token")

    @patch("requests.get")
    @patch("jwt.decode")
    def test_validate_id_token_success(self, mock_jwt_decode, mock_requests_get):
        mock_jwks_response = MagicMock()
        mock_jwks_response.status_code = 200
        mock_jwks_response.json.return_value = {"keys": [{"kid": "abc", "kty": "RSA"}]}
        mock_requests_get.return_value = mock_jwks_response

        mock_jwt_decode.return_value = {"sub": "user123", "iss": f"https://{self.config.domain}/oauth2/default", "aud": self.config.client_id}

        id_token = "mock_id_token"
        claims = self.provider.validate_id_token(id_token)

        mock_requests_get.assert_called_once_with(self.config.jwks_url, timeout=10)
        mock_jwt_decode.assert_called_once()
        self.assertEqual(claims["sub"], "user123")

    @patch("requests.get")
    def test_validate_id_token_jwks_failure(self, mock_requests_get):
        mock_jwks_response = MagicMock()
        mock_jwks_response.status_code = 500
        mock_jwks_response.raise_for_status.side_effect = requests.exceptions.RequestException("Internal Server Error")
        mock_requests_get.return_value = mock_jwks_response

        with self.assertRaisesRegex(ValueError, "Failed to retrieve JWKS"):
            self.provider.validate_id_token("mock_id_token")

    @patch("requests.get")
    @patch("jwt.decode")
    def test_validate_id_token_invalid_token(self, mock_jwt_decode, mock_requests_get):
        mock_jwks_response = MagicMock()
        mock_jwks_response.status_code = 200
        mock_jwks_response.json.return_value = {"keys": [{"kid": "abc", "kty": "RSA"}]}
        mock_requests_get.return_value = mock_jwks_response

        from jwt.exceptions import InvalidTokenError
        mock_jwt_decode.side_effect = InvalidTokenError("Invalid signature")

        with self.assertRaisesRegex(ValueError, "Invalid ID token"):
            self.provider.validate_id_token("invalid_id_token")

    @patch("requests.post")
    def test_revoke_token_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        token = "test_token_to_revoke"
        result = self.provider.revoke_token(token)

        mock_post.assert_called_once_with(
            self.config.revoke_url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "token": token,
            },
            timeout=10,
        )
        self.assertTrue(result)

    @patch("requests.post")
    def test_revoke_token_failure(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = requests.exceptions.RequestException("Bad Request")
        mock_post.return_value = mock_response

        with self.assertRaises(requests.exceptions.RequestException):
            self.provider.revoke_token("invalid_token")

    def test_generate_pkce_pair(self):
        pkce_pair = generate_pkce_pair()
        self.assertIn("code_verifier", pkce_pair)
        self.assertIn("code_challenge", pkce_pair)
        self.assertIsInstance(pkce_pair["code_verifier"], str)
        self.assertIsInstance(pkce_pair["code_challenge"], str)
        self.assertGreater(len(pkce_pair["code_verifier"]), 0)
        self.assertGreater(len(pkce_pair["code_challenge"]), 0)

        # Verify code_challenge is derived correctly from code_verifier
        calculated_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(pkce_pair["code_verifier"].encode("ascii")).digest()
        ).decode().rstrip("=")
        self.assertEqual(pkce_pair["code_challenge"], calculated_challenge)

if __name__ == "__main__":
    unittest.main()
>>>>>>> 322a69b (feat(phase-21a): implement Okta, Azure AD, Google SSO providers — 79/79 tests, 0 bandit issues)

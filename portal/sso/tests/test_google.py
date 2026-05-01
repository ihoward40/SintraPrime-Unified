
import time
import unittest
from unittest.mock import MagicMock, patch

import jwt
import pytest
import requests

from portal.sso.providers.google import GoogleConfig, GoogleWorkspaceProvider


class TestGoogleWorkspaceProvider(unittest.TestCase):

    def setUp(self):
        self.config = GoogleConfig(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="https://test.com/redirect",
            hosted_domain="test.com"
        )
        self.provider = GoogleWorkspaceProvider(self.config)

    def test_google_config_init_success(self):
        """Test GoogleConfig initialization with valid parameters."""
        config = GoogleConfig(
            client_id="valid_client_id",
            client_secret="valid_client_secret",
            redirect_uri="https://valid.com/redirect"
        )
        assert isinstance(config, GoogleConfig)
        assert config.client_id == "valid_client_id"

    def test_google_config_init_missing_client_id(self):
        """Test GoogleConfig initialization raises ValueError for missing client_id."""
        with pytest.raises(ValueError, match=r".") as cm:
            GoogleConfig(client_id="", client_secret="secret", redirect_uri="uri")
        assert "client_id is required" in str(cm.value)

    def test_google_config_init_missing_client_secret(self):
        """Test GoogleConfig initialization raises ValueError for missing client_secret."""
        with pytest.raises(ValueError, match=r".") as cm:
            GoogleConfig(client_id="id", client_secret="", redirect_uri="uri")
        assert "client_secret is required" in str(cm.value)

    def test_google_config_init_missing_redirect_uri(self):
        """Test GoogleConfig initialization raises ValueError for missing redirect_uri."""
        with pytest.raises(ValueError, match=r".") as cm:
            GoogleConfig(client_id="id", client_secret="secret", redirect_uri="")
        assert "redirect_uri is required" in str(cm.value)

    def test_get_authorization_url_no_hosted_domain(self):
        """Test get_authorization_url without hosted_domain."""
        self.config.hosted_domain = None
        url = self.provider.get_authorization_url("test_state")
        assert "client_id=test_client_id" in url
        assert "redirect_uri=https%3A%2F%2Ftest.com%2Fredirect" in url
        assert "response_type=code" in url
        assert "scope=openid+email+profile" in url
        assert "state=test_state" in url
        assert "hd=" not in url

    def test_get_authorization_url_with_hosted_domain(self):
        """Test get_authorization_url with hosted_domain."""
        url = self.provider.get_authorization_url("test_state")
        assert "client_id=test_client_id" in url
        assert "redirect_uri=https%3A%2F%2Ftest.com%2Fredirect" in url
        assert "response_type=code" in url
        assert "scope=openid+email+profile" in url
        assert "state=test_state" in url
        assert "hd=test.com" in url

    @patch("requests.post")
    def test_exchange_code_for_tokens_success(self, mock_post):
        """Test exchange_code_for_tokens successfully retrieves tokens."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "id_token": "test_id_token",
            "expires_in": 3600
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        tokens = self.provider.exchange_code_for_tokens("test_code")
        assert tokens["access_token"] == "test_access_token"
        mock_post.assert_called_once()

    @patch("requests.post")
    def test_exchange_code_for_tokens_http_error(self, mock_post):
        """Test exchange_code_for_tokens handles HTTP errors."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError
        mock_post.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            self.provider.exchange_code_for_tokens("test_code")

    @patch("requests.get")
    def test_get_user_info_success(self, mock_get):
        """Test get_user_info successfully retrieves user information."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"email": "test@test.com", "name": "Test User"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        user_info = self.provider.get_user_info("test_access_token")
        assert user_info["email"] == "test@test.com"
        mock_get.assert_called_once()

    @patch("requests.get")
    def test_get_user_info_http_error(self, mock_get):
        """Test get_user_info handles HTTP errors."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError
        mock_get.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            self.provider.get_user_info("test_access_token")

    @patch("jwt.PyJWKClient")
    @patch("jwt.decode")
    def test_validate_id_token_success(self, mock_jwt_decode, mock_pyjwk_client):
        """Test validate_id_token successfully validates and decodes the token."""
        mock_signing_key = MagicMock()
        mock_signing_key.key = "test_key"
        mock_pyjwk_client.return_value.get_signing_key_from_jwt.return_value = mock_signing_key

        mock_jwt_decode.return_value = {
            "iss": "https://accounts.google.com",
            "aud": "test_client_id",
            "exp": time.time() + 3600,
            "iat": time.time(),
            "nbf": time.time(),
            "hd": "test.com"
        }

        claims = self.provider.validate_id_token("test_id_token")
        assert "iss" in claims
        mock_jwt_decode.assert_called_once()

    @patch("jwt.PyJWKClient")
    @patch("jwt.decode")
    def test_validate_id_token_invalid_signature(self, mock_jwt_decode, mock_pyjwk_client):
        """Test validate_id_token handles invalid signature."""
        mock_signing_key = MagicMock()
        mock_signing_key.key = "test_key"
        mock_pyjwk_client.return_value.get_signing_key_from_jwt.return_value = mock_signing_key

        mock_jwt_decode.side_effect = jwt.exceptions.InvalidSignatureError

        with pytest.raises(jwt.exceptions.InvalidSignatureError):
            self.provider.validate_id_token("invalid_id_token")

    @patch("jwt.PyJWKClient")
    @patch("jwt.decode")
    def test_validate_id_token_invalid_audience(self, mock_jwt_decode, mock_pyjwk_client):
        """Test validate_id_token handles invalid audience."""
        mock_signing_key = MagicMock()
        mock_signing_key.key = "test_key"
        mock_pyjwk_client.return_value.get_signing_key_from_jwt.return_value = mock_signing_key

        mock_jwt_decode.side_effect = jwt.exceptions.InvalidAudienceError

        with pytest.raises(jwt.exceptions.InvalidAudienceError):
            self.provider.validate_id_token("invalid_id_token")

    @patch("jwt.PyJWKClient")
    @patch("jwt.decode")
    def test_validate_id_token_invalid_issuer(self, mock_jwt_decode, mock_pyjwk_client):
        """Test validate_id_token handles invalid issuer."""
        mock_signing_key = MagicMock()
        mock_signing_key.key = "test_key"
        mock_pyjwk_client.return_value.get_signing_key_from_jwt.return_value = mock_signing_key

        mock_jwt_decode.side_effect = jwt.exceptions.InvalidIssuerError

        with pytest.raises(jwt.exceptions.InvalidIssuerError):
            self.provider.validate_id_token("invalid_id_token")

    def test_verify_hosted_domain_match(self):
        """Test verify_hosted_domain when hosted_domain matches."""
        claims = {"hd": "test.com"}
        assert self.provider.verify_hosted_domain(claims)

    def test_verify_hosted_domain_no_match(self):
        """Test verify_hosted_domain when hosted_domain does not match."""
        claims = {"hd": "other.com"}
        assert not self.provider.verify_hosted_domain(claims)

    def test_verify_hosted_domain_no_config_hosted_domain(self):
        """Test verify_hosted_domain when no hosted_domain is configured."""
        self.config.hosted_domain = None
        claims = {"hd": "test.com"}
        assert self.provider.verify_hosted_domain(claims)

    def test_verify_hosted_domain_no_hd_claim(self):
        """Test verify_hosted_domain when 'hd' claim is missing."""
        claims = {}
        assert not self.provider.verify_hosted_domain(claims)

    def test_google_config_default_scopes(self):
        """Test that default scopes are correctly set if not provided."""
        config = GoogleConfig(
            client_id="id",
            client_secret="secret",
            redirect_uri="uri"
        )
        assert config.scopes == ["openid", "email", "profile"]

    def test_google_config_custom_scopes(self):
        """Test that custom scopes are correctly set."""
        config = GoogleConfig(
            client_id="id",
            client_secret="secret",
            redirect_uri="uri",
            scopes=["custom_scope"]
        )
        assert config.scopes == ["custom_scope"]

    @patch("requests.post")
    def test_exchange_code_for_tokens_data_sent_correctly(self, mock_post):
        """Test that correct data is sent in exchange_code_for_tokens request."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "token"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        self.provider.exchange_code_for_tokens("test_code")
        mock_post.assert_called_with(
            self.provider.token_url,
            data={
                "code": "test_code",
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "redirect_uri": "https://test.com/redirect",
                "grant_type": "authorization_code",
            },
            timeout=10,
        )

    @patch("requests.get")
    def test_get_user_info_headers_sent_correctly(self, mock_get):
        """Test that correct headers are sent in get_user_info request."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"email": "test@test.com"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        self.provider.get_user_info("test_access_token")
        mock_get.assert_called_with(
            self.provider.userinfo_url,
            headers={
                "Authorization": "Bearer test_access_token"
            },
            timeout=10,
        )

    @patch("jwt.PyJWKClient")
    @patch("jwt.decode")
    def test_validate_id_token_jwt_decode_params(self, mock_jwt_decode, mock_pyjwk_client):
        """Test that jwt.decode is called with correct parameters."""
        mock_signing_key = MagicMock()
        mock_signing_key.key = "test_key"
        mock_pyjwk_client.return_value.get_signing_key_from_jwt.return_value = mock_signing_key

        mock_jwt_decode.return_value = {
            "iss": "https://accounts.google.com",
            "aud": "test_client_id",
            "exp": time.time() + 3600,
            "iat": time.time(),
            "nbf": time.time(),
            "hd": "test.com"
        }

        self.provider.validate_id_token("test_id_token")
        mock_jwt_decode.assert_called_once_with(
            "test_id_token",
            "test_key",
            algorithms=["RS256"],
            audience="test_client_id",
            issuer="https://accounts.google.com",
            options={
                "verify_signature": True,
                "verify_aud": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_nbf": True,
                "verify_iss": True,
                "require_aud": True,
                "require_exp": True,
                "require_iat": True,
                "require_nbf": True,
                "require_iss": True,
            }
        )

    def test_google_config_scopes_default_value(self):
        """Test that scopes default to [\'openid\', \'email\', \'profile\'] if not provided."""
        config = GoogleConfig(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="https://test.com/redirect"
        )
        assert config.scopes == ["openid", "email", "profile"]

    def test_google_config_scopes_custom_value(self):
        """Test that scopes can be overridden with custom values."""
        custom_scopes = ["custom_scope1", "custom_scope2"]
        config = GoogleConfig(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="https://test.com/redirect",
            scopes=custom_scopes
        )
        assert config.scopes == custom_scopes

    def test_google_config_hosted_domain_default_value(self):
        """Test that hosted_domain defaults to None if not provided."""
        config = GoogleConfig(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="https://test.com/redirect"
        )
        assert config.hosted_domain is None

    def test_google_config_hosted_domain_custom_value(self):
        """Test that hosted_domain can be overridden with a custom value."""
        config = GoogleConfig(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="https://test.com/redirect",
            hosted_domain="custom.com"
        )
        assert config.hosted_domain == "custom.com"

    def test_verify_hosted_domain_with_none_config_hosted_domain(self):
        """Test verify_hosted_domain returns True when config.hosted_domain is None."""
        self.config.hosted_domain = None
        claims = {"hd": "any.com"}
        assert self.provider.verify_hosted_domain(claims)

    def test_verify_hosted_domain_with_empty_config_hosted_domain(self):
        """Test verify_hosted_domain returns True when config.hosted_domain is an empty string."""
        self.config.hosted_domain = ""
        claims = {"hd": "any.com"}
        assert self.provider.verify_hosted_domain(claims)

    def test_verify_hosted_domain_with_matching_hd_claim(self):
        """Test verify_hosted_domain returns True when config.hosted_domain matches 'hd' claim."""
        self.config.hosted_domain = "example.com"
        claims = {"hd": "example.com"}
        assert self.provider.verify_hosted_domain(claims)

    def test_verify_hosted_domain_with_mismatching_hd_claim(self):
        """Test verify_hosted_domain returns False when config.hosted_domain mismatches 'hd' claim."""
        self.config.hosted_domain = "example.com"
        claims = {"hd": "wrong.com"}
        assert not self.provider.verify_hosted_domain(claims)

    def test_verify_hosted_domain_with_missing_hd_claim(self):
        """Test verify_hosted_domain returns False when 'hd' claim is missing and hosted_domain is configured."""
        self.config.hosted_domain = "example.com"
        claims = {}
        assert not self.provider.verify_hosted_domain(claims)

    def test_get_authorization_url_scopes_format(self):
        """Test that scopes are correctly formatted in the authorization URL."""
        self.config.scopes = ["scope1", "scope2"]
        url = self.provider.get_authorization_url("test_state")
        assert "scope=scope1+scope2" in url

    def test_get_authorization_url_prompt_select_account(self):
        """Test that 'prompt=select_account' is included in the authorization URL."""
        url = self.provider.get_authorization_url("test_state")
        assert "prompt=select_account" in url

    def test_get_authorization_url_access_type_offline(self):
        """Test that 'access_type=offline' is included in the authorization URL."""
        url = self.provider.get_authorization_url("test_state")
        assert "access_type=offline" in url




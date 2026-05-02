import base64
import hashlib
import unittest
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, quote, urlparse

import pytest
import requests

from portal.sso.providers.azure import AzureADProvider, AzureConfig


class TestAzureADProvider(unittest.TestCase):

    def setUp(self):
        self.mock_config = AzureConfig(
            tenant_id="test_tenant_id",
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="https://test.com/redirect",
            scopes=["openid", "email", "profile"]
        )
        self.provider = AzureADProvider(self.mock_config)
        self.mock_openid_config = {
            "authorization_endpoint": "https://login.microsoftonline.com/test_tenant_id/oauth2/v2.0/authorize",
            "token_endpoint": "https://login.microsoftonline.com/test_tenant_id/oauth2/v2.0/token",
            "userinfo_endpoint": "https://graph.microsoft.com/oidc/userinfo",
            "jwks_uri": "https://login.microsoftonline.com/test_tenant_id/discovery/v2.0/keys",
            "issuer": "https://login.microsoftonline.com/test_tenant_id/v2.0"
        }
        self.mock_jwks = {
            "keys": [
                {
                    "kty": "RSA",
                    "use": "sig",
                    "kid": "test_kid",
                    "x5t": "test_x5t",
                    "n": "test_n",
                    "e": "AQAB",
                    "x5c": ["test_x5c"],
                    "issuer": "test_issuer"
                }
            ]
        }

    def test_azure_config_validation(self):
        with pytest.raises(ValueError):
            AzureConfig(tenant_id="", client_id="cid", client_secret="cs", redirect_uri="ru")
        with pytest.raises(ValueError):
            AzureConfig(tenant_id="tid", client_id="", client_secret="cs", redirect_uri="ru")
        with pytest.raises(ValueError):
            AzureConfig(tenant_id="tid", client_id="cid", client_secret="", redirect_uri="ru")
        with pytest.raises(ValueError):
            AzureConfig(tenant_id="tid", client_id="cid", client_secret="cs", redirect_uri="")
        # Should not raise error
        AzureConfig(tenant_id="tid", client_id="cid", client_secret="cs", redirect_uri="ru")

    @patch("requests.get")
    def test_get_openid_config(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = self.mock_openid_config
        mock_requests_get.return_value = mock_response

        config = self.provider._get_openid_config()
        assert config == self.mock_openid_config
        mock_requests_get.assert_called_once_with(self.provider.openid_config_url, timeout=10)

        # Test caching
        mock_requests_get.reset_mock()
        config = self.provider._get_openid_config()
        assert config == self.mock_openid_config
        mock_requests_get.assert_not_called()

    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    def test_get_authorization_url(self, mock_get_openid_config):
        mock_get_openid_config.return_value = self.mock_openid_config
        state = "test_state"
        auth_url = self.provider.get_authorization_url(state)

        assert self.mock_openid_config["authorization_endpoint"] in auth_url
        assert f"client_id={self.mock_config.client_id}" in auth_url
        assert "response_type=code" in auth_url
        quoted_redirect_uri = quote(self.mock_config.redirect_uri, safe="")
        quoted_scopes = quote(" ".join(self.mock_config.scopes), safe="").replace("%20", "+")
        assert f"redirect_uri={quoted_redirect_uri}" in auth_url
        assert f"scope={quoted_scopes}" in auth_url
        assert f"state={state}" in auth_url
        assert "code_challenge=" in auth_url
        assert "code_challenge_method=S256" in auth_url

        parsed_url = urlparse(auth_url)
        query_params = parse_qs(parsed_url.query)
        assert "code_challenge" in query_params
        assert query_params["code_challenge_method"][0] == "S256"

        code_verifier = base64.urlsafe_b64encode(hashlib.sha256(self.mock_config.client_secret.encode()).digest()).decode().rstrip("=")
        expected_code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).decode().rstrip("=")
        assert query_params["code_challenge"][0] == expected_code_challenge

    @patch("requests.post")
    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    def test_exchange_code_for_tokens(self, mock_get_openid_config, mock_requests_post):
        mock_get_openid_config.return_value = self.mock_openid_config
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"access_token": "at", "id_token": "idt", "expires_in": 3600}
        mock_requests_post.return_value = mock_response

        code = "test_code"
        tokens = self.provider.exchange_code_for_tokens(code)

        assert tokens["access_token"] == "at"
        mock_requests_post.assert_called_once()
        args, kwargs = mock_requests_post.call_args
        assert args[0] == self.mock_openid_config["token_endpoint"]
        assert "client_id" in kwargs["data"]
        assert "client_secret" in kwargs["data"]
        assert "code" in kwargs["data"]
        assert "redirect_uri" in kwargs["data"]
        assert "grant_type" in kwargs["data"]
        assert "code_verifier" in kwargs["data"]

        code_verifier = base64.urlsafe_b64encode(hashlib.sha256(self.mock_config.client_secret.encode()).digest()).decode().rstrip("=")
        assert kwargs["data"]["code_verifier"] == code_verifier

    @patch("requests.get")
    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    def test_get_user_info(self, mock_get_openid_config, mock_requests_get):
        mock_get_openid_config.return_value = self.mock_openid_config
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"sub": "123", "name": "Test User"}
        mock_requests_get.return_value = mock_response

        access_token = "test_access_token"
        user_info = self.provider.get_user_info(access_token)

        assert user_info["name"] == "Test User"
        mock_requests_get.assert_called_once_with(
            self.mock_openid_config["userinfo_endpoint"],
            headers={
                "Authorization": f"Bearer {access_token}"
            },
            timeout=10,
        )

    @patch("requests.get")
    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    def test_get_jwks(self, mock_get_openid_config, mock_requests_get):
        mock_get_openid_config.return_value = self.mock_openid_config
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = self.mock_jwks
        mock_requests_get.return_value = mock_response

        jwks = self.provider.get_jwks()
        assert jwks == self.mock_jwks
        mock_requests_get.assert_called_once_with(self.mock_openid_config["jwks_uri"], timeout=10)

        # Test caching
        mock_requests_get.reset_mock()
        jwks = self.provider.get_jwks()
        assert jwks == self.mock_jwks
        mock_requests_get.assert_not_called()

    @patch("portal.sso.providers.azure.AzureADProvider.get_jwks")
    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    @patch("jose.jwt.decode")
    @patch("jose.jwt.get_unverified_header")
    def test_validate_id_token_success(self, mock_get_unverified_header, mock_jwt_decode, mock_get_openid_config, mock_get_jwks):
        mock_get_openid_config.return_value = self.mock_openid_config
        mock_get_jwks.return_value = self.mock_jwks
        mock_get_unverified_header.return_value = {"kid": "test_kid"}
        mock_jwt_decode.return_value = {"sub": "123", "aud": "test_client_id", "iss": self.mock_openid_config["issuer"]}

        id_token = "mock_id_token"
        decoded_token = self.provider.validate_id_token(id_token)

        assert decoded_token["sub"] == "123"
        mock_get_unverified_header.assert_called_once_with(id_token)
        mock_get_jwks.assert_called_once()
        mock_jwt_decode.assert_called_once()
        args, kwargs = mock_jwt_decode.call_args
        assert args[0] == id_token
        assert kwargs["audience"] == self.mock_config.client_id
        assert kwargs["issuer"] == self.mock_openid_config["issuer"]

    @patch("portal.sso.providers.azure.AzureADProvider.get_jwks")
    @patch("jose.jwt.get_unverified_header")
    def test_validate_id_token_no_matching_jwk(self, mock_get_unverified_header, mock_get_jwks):
        mock_get_jwks.return_value = self.mock_jwks
        mock_get_unverified_header.return_value = {"kid": "unknown_kid"}

        id_token = "mock_id_token"
        with pytest.raises(ValueError, match="No matching JWK found for the ID token."):
            self.provider.validate_id_token(id_token)

    @patch("portal.sso.providers.azure.AzureADProvider.get_jwks")
    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    @patch("jose.jwt.decode")
    @patch("jose.jwt.get_unverified_header")
    def test_validate_id_token_jwt_error(self, mock_get_unverified_header, mock_jwt_decode, mock_get_openid_config, mock_get_jwks):
        from jose.exceptions import JWTError
        mock_get_openid_config.return_value = self.mock_openid_config
        mock_get_jwks.return_value = self.mock_jwks
        mock_get_unverified_header.return_value = {"kid": "test_kid"}
        mock_jwt_decode.side_effect = JWTError("Invalid token")

        id_token = "mock_id_token"
        with pytest.raises(ValueError, match="ID token validation failed: Invalid token"):
            self.provider.validate_id_token(id_token)

    @patch("requests.get")
    def test_get_openid_config_http_error(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_requests_get.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            self.provider._get_openid_config()

    @patch("requests.post")
    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    def test_exchange_code_for_tokens_http_error(self, mock_get_openid_config, mock_requests_post):
        mock_get_openid_config.return_value = self.mock_openid_config
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("400 Bad Request")
        mock_requests_post.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            self.provider.exchange_code_for_tokens("test_code")

    @patch("requests.get")
    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    def test_get_user_info_http_error(self, mock_get_openid_config, mock_requests_get):
        mock_get_openid_config.return_value = self.mock_openid_config
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
        mock_requests_get.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            self.provider.get_user_info("test_access_token")

    @patch("requests.get")
    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    def test_get_jwks_http_error(self, mock_get_openid_config, mock_requests_get):
        mock_get_openid_config.return_value = self.mock_openid_config
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Internal Server Error")
        mock_requests_get.return_value = mock_response

        self.provider._jwks = None # Clear cache to force API call
        with pytest.raises(requests.exceptions.HTTPError):
            self.provider.get_jwks()

    @patch("portal.sso.providers.azure.AzureADProvider.get_jwks")
    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    @patch("jose.jwt.decode")
    @patch("jose.jwt.get_unverified_header")
    def test_validate_id_token_general_exception(self, mock_get_unverified_header, mock_jwt_decode, mock_get_openid_config, mock_get_jwks):
        mock_get_openid_config.return_value = self.mock_openid_config
        mock_get_jwks.return_value = self.mock_jwks
        mock_get_unverified_header.side_effect = Exception("Something unexpected")

        id_token = "mock_id_token"
        with pytest.raises(ValueError, match="An unexpected error occurred during ID token validation: Something unexpected"):
            self.provider.validate_id_token(id_token)

    def test_azure_config_default_scopes(self):
        config = AzureConfig(
            tenant_id="tid",
            client_id="cid",
            client_secret="cs",
            redirect_uri="ru"
        )
        assert config.scopes == ["openid", "email", "profile"]

    def test_azure_config_custom_scopes(self):
        custom_scopes = ["profile", "offline_access"]
        config = AzureConfig(
            tenant_id="tid",
            client_id="cid",
            client_secret="cs",
            redirect_uri="ru",
            scopes=custom_scopes
        )
        assert config.scopes == custom_scopes

    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    def test_get_authorization_url_custom_scopes(self, mock_get_openid_config):
        mock_get_openid_config.return_value = self.mock_openid_config
        custom_scopes = ["profile", "offline_access"]
        self.mock_config.scopes = custom_scopes
        provider = AzureADProvider(self.mock_config)
        auth_url = provider.get_authorization_url("state")
        quoted_custom_scopes = quote(" ".join(custom_scopes), safe="").replace("%20", "+")
        assert f"scope={quoted_custom_scopes}" in auth_url

    @patch("requests.post")
    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    def test_exchange_code_for_tokens_invalid_code(self, mock_get_openid_config, mock_requests_post):
        mock_get_openid_config.return_value = self.mock_openid_config
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("400 Invalid Grant")
        mock_requests_post.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            self.provider.exchange_code_for_tokens("invalid_code")

    @patch("portal.sso.providers.azure.AzureADProvider.get_jwks")
    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    @patch("jose.jwt.decode")
    @patch("jose.jwt.get_unverified_header")
    def test_validate_id_token_invalid_audience(self, mock_get_unverified_header, mock_jwt_decode, mock_get_openid_config, mock_get_jwks):
        from jose.exceptions import JWTError
        mock_get_openid_config.return_value = self.mock_openid_config
        mock_get_jwks.return_value = self.mock_jwks
        mock_get_unverified_header.return_value = {"kid": "test_kid"}
        mock_jwt_decode.side_effect = JWTError("Invalid audience")

        id_token = "mock_id_token"
        with pytest.raises(ValueError, match="ID token validation failed: Invalid audience"):
            self.provider.validate_id_token(id_token)

    @patch("portal.sso.providers.azure.AzureADProvider.get_jwks")
    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    @patch("jose.jwt.decode")
    @patch("jose.jwt.get_unverified_header")
    def test_validate_id_token_invalid_issuer(self, mock_get_unverified_header, mock_jwt_decode, mock_get_openid_config, mock_get_jwks):
        from jose.exceptions import JWTError
        mock_get_openid_config.return_value = self.mock_openid_config
        mock_get_jwks.return_value = self.mock_jwks
        mock_get_unverified_header.return_value = {"kid": "test_kid"}
        mock_jwt_decode.side_effect = JWTError("Invalid issuer")

        id_token = "mock_id_token"
        with pytest.raises(ValueError, match="ID token validation failed: Invalid issuer"):
            self.provider.validate_id_token(id_token)

    @patch("portal.sso.providers.azure.AzureADProvider.get_jwks")
    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    @patch("jose.jwt.decode")
    @patch("jose.jwt.get_unverified_header")
    def test_validate_id_token_expired(self, mock_get_unverified_header, mock_jwt_decode, mock_get_openid_config, mock_get_jwks):
        from jose.exceptions import ExpiredSignatureError
        mock_get_openid_config.return_value = self.mock_openid_config
        mock_get_jwks.return_value = self.mock_jwks
        mock_get_unverified_header.return_value = {"kid": "test_kid"}
        mock_jwt_decode.side_effect = ExpiredSignatureError("Token expired")

        id_token = "mock_id_token"
        with pytest.raises(ValueError, match="ID token validation failed: Token expired"):
            self.provider.validate_id_token(id_token)

    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    def test_authority_url_construction(self, mock_get_openid_config):
        mock_get_openid_config.return_value = self.mock_openid_config
        expected_authority = f"https://login.microsoftonline.com/{self.mock_config.tenant_id}/v2.0"
        assert self.provider.authority == expected_authority

    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    def test_openid_config_url_construction(self, mock_get_openid_config):
        mock_get_openid_config.return_value = self.mock_openid_config
        expected_openid_config_url = f"https://login.microsoftonline.com/{self.mock_config.tenant_id}/v2.0/.well-known/openid-configuration"
        assert self.provider.openid_config_url == expected_openid_config_url

    @patch("requests.get")
    def test_get_openid_config_connection_error(self, mock_requests_get):
        mock_requests_get.side_effect = requests.exceptions.ConnectionError("Network unreachable")
        with pytest.raises(requests.exceptions.ConnectionError):
            self.provider._get_openid_config()

    @patch("requests.post")
    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    def test_exchange_code_for_tokens_connection_error(self, mock_get_openid_config, mock_requests_post):
        mock_get_openid_config.return_value = self.mock_openid_config
        mock_requests_post.side_effect = requests.exceptions.ConnectionError("Network unreachable")
        with pytest.raises(requests.exceptions.ConnectionError):
            self.provider.exchange_code_for_tokens("test_code")

    @patch("requests.get")
    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    def test_get_user_info_connection_error(self, mock_get_openid_config, mock_requests_get):
        mock_get_openid_config.return_value = self.mock_openid_config
        mock_requests_get.side_effect = requests.exceptions.ConnectionError("Network unreachable")
        with pytest.raises(requests.exceptions.ConnectionError):
            self.provider.get_user_info("test_access_token")

    @patch("requests.get")
    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    def test_get_jwks_connection_error(self, mock_get_openid_config, mock_requests_get):
        mock_get_openid_config.return_value = self.mock_openid_config
        mock_requests_get.side_effect = requests.exceptions.ConnectionError("Network unreachable")
        with pytest.raises(requests.exceptions.ConnectionError):
            self.provider.get_jwks()

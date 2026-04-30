import unittest
from unittest.mock import patch, MagicMock
import json
import requests
import base64
import hashlib
from urllib.parse import urlparse, parse_qs, quote

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
        with self.assertRaises(ValueError):
            AzureConfig(tenant_id="", client_id="cid", client_secret="cs", redirect_uri="ru")
        with self.assertRaises(ValueError):
            AzureConfig(tenant_id="tid", client_id="", client_secret="cs", redirect_uri="ru")
        with self.assertRaises(ValueError):
            AzureConfig(tenant_id="tid", client_id="cid", client_secret="", redirect_uri="ru")
        with self.assertRaises(ValueError):
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
        self.assertEqual(config, self.mock_openid_config)
        mock_requests_get.assert_called_once_with(self.provider.openid_config_url, timeout=10)

        # Test caching
        mock_requests_get.reset_mock()
        config = self.provider._get_openid_config()
        self.assertEqual(config, self.mock_openid_config)
        mock_requests_get.assert_not_called()

    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    def test_get_authorization_url(self, mock_get_openid_config):
        mock_get_openid_config.return_value = self.mock_openid_config
        state = "test_state"
        auth_url = self.provider.get_authorization_url(state)

        self.assertIn(self.mock_openid_config["authorization_endpoint"], auth_url)
        self.assertIn(f"client_id={self.mock_config.client_id}", auth_url)
        self.assertIn("response_type=code", auth_url)
        quoted_redirect_uri = quote(self.mock_config.redirect_uri, safe="")
        quoted_scopes = quote(" ".join(self.mock_config.scopes), safe="").replace("%20", "+")
        self.assertIn(f"redirect_uri={quoted_redirect_uri}", auth_url)
        self.assertIn(f"scope={quoted_scopes}", auth_url)
        self.assertIn(f"state={state}", auth_url)
        self.assertIn("code_challenge=", auth_url)
        self.assertIn("code_challenge_method=S256", auth_url)

        parsed_url = urlparse(auth_url)
        query_params = parse_qs(parsed_url.query)
        self.assertIn("code_challenge", query_params)
        self.assertEqual(query_params["code_challenge_method"][0], "S256")

        code_verifier = base64.urlsafe_b64encode(hashlib.sha256(self.mock_config.client_secret.encode()).digest()).decode().rstrip("=")
        expected_code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).decode().rstrip("=")
        self.assertEqual(query_params["code_challenge"][0], expected_code_challenge)

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

        self.assertEqual(tokens["access_token"], "at")
        mock_requests_post.assert_called_once()
        args, kwargs = mock_requests_post.call_args
        self.assertEqual(args[0], self.mock_openid_config["token_endpoint"])
        self.assertIn("client_id", kwargs["data"])
        self.assertIn("client_secret", kwargs["data"])
        self.assertIn("code", kwargs["data"])
        self.assertIn("redirect_uri", kwargs["data"])
        self.assertIn("grant_type", kwargs["data"])
        self.assertIn("code_verifier", kwargs["data"])

        code_verifier = base64.urlsafe_b64encode(hashlib.sha256(self.mock_config.client_secret.encode()).digest()).decode().rstrip("=")
        self.assertEqual(kwargs["data"]["code_verifier"], code_verifier)

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

        self.assertEqual(user_info["name"], "Test User")
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
        self.assertEqual(jwks, self.mock_jwks)
        mock_requests_get.assert_called_once_with(self.mock_openid_config["jwks_uri"], timeout=10)

        # Test caching
        mock_requests_get.reset_mock()
        jwks = self.provider.get_jwks()
        self.assertEqual(jwks, self.mock_jwks)
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

        self.assertEqual(decoded_token["sub"], "123")
        mock_get_unverified_header.assert_called_once_with(id_token)
        mock_get_jwks.assert_called_once()
        mock_jwt_decode.assert_called_once()
        args, kwargs = mock_jwt_decode.call_args
        self.assertEqual(args[0], id_token)
        self.assertEqual(kwargs["audience"], self.mock_config.client_id)
        self.assertEqual(kwargs["issuer"], self.mock_openid_config["issuer"])

    @patch("portal.sso.providers.azure.AzureADProvider.get_jwks")
    @patch("jose.jwt.get_unverified_header")
    def test_validate_id_token_no_matching_jwk(self, mock_get_unverified_header, mock_get_jwks):
        mock_get_jwks.return_value = self.mock_jwks
        mock_get_unverified_header.return_value = {"kid": "unknown_kid"}

        id_token = "mock_id_token"
        with self.assertRaisesRegex(ValueError, "No matching JWK found for the ID token."):
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
        with self.assertRaisesRegex(ValueError, "ID token validation failed: Invalid token"):
            self.provider.validate_id_token(id_token)

    @patch("requests.get")
    def test_get_openid_config_http_error(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_requests_get.return_value = mock_response

        with self.assertRaises(requests.exceptions.HTTPError):
            self.provider._get_openid_config()

    @patch("requests.post")
    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    def test_exchange_code_for_tokens_http_error(self, mock_get_openid_config, mock_requests_post):
        mock_get_openid_config.return_value = self.mock_openid_config
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("400 Bad Request")
        mock_requests_post.return_value = mock_response

        with self.assertRaises(requests.exceptions.HTTPError):
            self.provider.exchange_code_for_tokens("test_code")

    @patch("requests.get")
    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    def test_get_user_info_http_error(self, mock_get_openid_config, mock_requests_get):
        mock_get_openid_config.return_value = self.mock_openid_config
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
        mock_requests_get.return_value = mock_response

        with self.assertRaises(requests.exceptions.HTTPError):
            self.provider.get_user_info("test_access_token")

    @patch("requests.get")
    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    def test_get_jwks_http_error(self, mock_get_openid_config, mock_requests_get):
        mock_get_openid_config.return_value = self.mock_openid_config
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Internal Server Error")
        mock_requests_get.return_value = mock_response

        self.provider._jwks = None # Clear cache to force API call
        with self.assertRaises(requests.exceptions.HTTPError):
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
        with self.assertRaisesRegex(ValueError, "An unexpected error occurred during ID token validation: Something unexpected"):
            self.provider.validate_id_token(id_token)

    def test_azure_config_default_scopes(self):
        config = AzureConfig(
            tenant_id="tid",
            client_id="cid",
            client_secret="cs",
            redirect_uri="ru"
        )
        self.assertEqual(config.scopes, ["openid", "email", "profile"])

    def test_azure_config_custom_scopes(self):
        custom_scopes = ["profile", "offline_access"]
        config = AzureConfig(
            tenant_id="tid",
            client_id="cid",
            client_secret="cs",
            redirect_uri="ru",
            scopes=custom_scopes
        )
        self.assertEqual(config.scopes, custom_scopes)

    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    def test_get_authorization_url_custom_scopes(self, mock_get_openid_config):
        mock_get_openid_config.return_value = self.mock_openid_config
        custom_scopes = ["profile", "offline_access"]
        self.mock_config.scopes = custom_scopes
        provider = AzureADProvider(self.mock_config)
        auth_url = provider.get_authorization_url("state")
        quoted_custom_scopes = quote(" ".join(custom_scopes), safe="").replace("%20", "+")
        self.assertIn(f"scope={quoted_custom_scopes}", auth_url)

    @patch("requests.post")
    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    def test_exchange_code_for_tokens_invalid_code(self, mock_get_openid_config, mock_requests_post):
        mock_get_openid_config.return_value = self.mock_openid_config
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("400 Invalid Grant")
        mock_requests_post.return_value = mock_response

        with self.assertRaises(requests.exceptions.HTTPError):
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
        with self.assertRaisesRegex(ValueError, "ID token validation failed: Invalid audience"):
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
        with self.assertRaisesRegex(ValueError, "ID token validation failed: Invalid issuer"):
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
        with self.assertRaisesRegex(ValueError, "ID token validation failed: Token expired"):
            self.provider.validate_id_token(id_token)

    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    def test_authority_url_construction(self, mock_get_openid_config):
        mock_get_openid_config.return_value = self.mock_openid_config
        expected_authority = f"https://login.microsoftonline.com/{self.mock_config.tenant_id}/v2.0"
        self.assertEqual(self.provider.authority, expected_authority)

    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    def test_openid_config_url_construction(self, mock_get_openid_config):
        mock_get_openid_config.return_value = self.mock_openid_config
        expected_openid_config_url = f"https://login.microsoftonline.com/{self.mock_config.tenant_id}/v2.0/.well-known/openid-configuration"
        self.assertEqual(self.provider.openid_config_url, expected_openid_config_url)

    @patch("requests.get")
    def test_get_openid_config_connection_error(self, mock_requests_get):
        mock_requests_get.side_effect = requests.exceptions.ConnectionError("Network unreachable")
        with self.assertRaises(requests.exceptions.ConnectionError):
            self.provider._get_openid_config()

    @patch("requests.post")
    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    def test_exchange_code_for_tokens_connection_error(self, mock_get_openid_config, mock_requests_post):
        mock_get_openid_config.return_value = self.mock_openid_config
        mock_requests_post.side_effect = requests.exceptions.ConnectionError("Network unreachable")
        with self.assertRaises(requests.exceptions.ConnectionError):
            self.provider.exchange_code_for_tokens("test_code")

    @patch("requests.get")
    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    def test_get_user_info_connection_error(self, mock_get_openid_config, mock_requests_get):
        mock_get_openid_config.return_value = self.mock_openid_config
        mock_requests_get.side_effect = requests.exceptions.ConnectionError("Network unreachable")
        with self.assertRaises(requests.exceptions.ConnectionError):
            self.provider.get_user_info("test_access_token")

    @patch("requests.get")
    @patch("portal.sso.providers.azure.AzureADProvider._get_openid_config")
    def test_get_jwks_connection_error(self, mock_get_openid_config, mock_requests_get):
        mock_get_openid_config.return_value = self.mock_openid_config
        mock_requests_get.side_effect = requests.exceptions.ConnectionError("Network unreachable")
        with self.assertRaises(requests.exceptions.ConnectionError):
            self.provider.get_jwks()

import hashlib
import base64
import json
import requests
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

@dataclass
class AzureConfig:
    tenant_id: str
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: List[str] = field(default_factory=lambda: ["openid", "email", "profile"])

    def __post_init__(self):
        if not all([self.tenant_id, self.client_id, self.client_secret, self.redirect_uri]):
            raise ValueError("AzureConfig: Missing required configuration parameters.")

class AzureADProvider:
    """
    Azure AD B2C provider for OAuth2/OpenID Connect authentication.
    """
    def __init__(self, config: AzureConfig):
        self.config = config
        self.authority = f"https://login.microsoftonline.com/{self.config.tenant_id}/v2.0"
        self.openid_config_url = f"{self.authority}/.well-known/openid-configuration"
        self._openid_config = None
        self._jwks = None

    def _get_openid_config(self) -> Dict[str, Any]:
        """
        Retrieves the OpenID Connect configuration from Azure AD B2C.
        """
        if not self._openid_config:
            response = requests.get(self.openid_config_url, timeout=10)
            response.raise_for_status()
            self._openid_config = response.json()
        return self._openid_config

    def get_authorization_url(self, state: str) -> str:
        """
        Generates the authorization URL for Azure AD B2C.

        Args:
            state: A unique value to prevent cross-site request forgery attacks.

        Returns:
            The authorization URL.
        """
        openid_config = self._get_openid_config()
        auth_endpoint = openid_config["authorization_endpoint"]

        # PKCE (Proof Key for Code Exchange) implementation
        code_verifier = base64.urlsafe_b64encode(hashlib.sha256(self.config.client_secret.encode()).digest()).decode().rstrip("=")
        code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).decode().rstrip("=")

        params = {
            "client_id": self.config.client_id,
            "response_type": "code",
            "redirect_uri": self.config.redirect_uri,
            "scope": " ".join(self.config.scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        from urllib.parse import urlencode
        return f"{auth_endpoint}?{urlencode(params)}"

    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """
        Exchanges the authorization code for access, ID, and refresh tokens.

        Args:
            code: The authorization code received from Azure AD B2C.

        Returns:
            A dictionary containing the tokens.
        """
        openid_config = self._get_openid_config()
        token_endpoint = openid_config["token_endpoint"]

        # PKCE (Proof Key for Code Exchange) implementation
        code_verifier = base64.urlsafe_b64encode(hashlib.sha256(self.config.client_secret.encode()).digest()).decode().rstrip("=")

        data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "code": code,
            "redirect_uri": self.config.redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": code_verifier,
        }
        response = requests.post(token_endpoint, data=data, timeout=10)
        response.raise_for_status()
        return response.json()

    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Retrieves user information from Azure AD B2C.

        Args:
            access_token: The access token obtained after code exchange.

        Returns:
            A dictionary containing user information.
        """
        openid_config = self._get_openid_config()
        userinfo_endpoint = openid_config["userinfo_endpoint"]

        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        response = requests.get(userinfo_endpoint, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()

    def get_jwks(self) -> Dict[str, Any]:
        """
        Retrieves the JSON Web Key Set (JWKS) from Azure AD B2C.

        Returns:
            A dictionary containing the JWKS.
        """
        if not self._jwks:
            openid_config = self._get_openid_config()
            jwks_uri = openid_config["jwks_uri"]
            response = requests.get(jwks_uri, timeout=10)
            response.raise_for_status()
            self._jwks = response.json()
        return self._jwks

    def validate_id_token(self, id_token: str) -> Dict[str, Any]:
        """
        Validates the ID token received from Azure AD B2C.

        Args:
            id_token: The ID token to validate.

        Returns:
            A dictionary containing the decoded and validated ID token claims.
        
        Raises:
            ValueError: If the token is invalid or validation fails.
        """
        from jose import jwt
        from jose.exceptions import JWTError

        jwks = self.get_jwks()
        try:
            # Azure AD B2C tokens often have a specific issuer format, e.g., https://<tenant_id>.b2clogin.com/<tenant_id>/v2.0/
            # We need to be flexible with the issuer check.
            # For simplicity, we\\'ll decode without issuer validation first and then manually check.
            # A more robust solution would involve fetching the exact issuer from the openid-configuration.
            decoded_header = jwt.get_unverified_header(id_token)
            kid = decoded_header["kid"]

            key = None
            for jwk in jwks["keys"]:
                if jwk["kid"] == kid:
                    key = jwk
                    break
            
            if not key:
                raise ValueError("No matching JWK found for the ID token.")

            # Reconstruct the issuer based on the tenant_id for validation
            # This might need adjustment based on the exact Azure B2C setup
            expected_issuer = self._get_openid_config()["issuer"]

            options = {
                "verify_signature": True,
                "verify_aud": True,
                "verify_exp": True,
                "verify_iss": True,
            }

            # The audience (aud) claim should match the client_id
            decoded_token = jwt.decode(
                id_token,
                key,
                algorithms=["RS256"], # Azure B2C typically uses RS256
                audience=self.config.client_id,
                issuer=expected_issuer,
                options=options
            )
            return decoded_token
        except JWTError as e:
            raise ValueError(f"ID token validation failed: {e}")
        except Exception as e:
            raise ValueError(f"An unexpected error occurred during ID token validation: {e}")

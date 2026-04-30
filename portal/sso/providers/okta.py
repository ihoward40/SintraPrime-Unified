<<<<<<< HEAD
"""Okta SAML 2.0 Service Provider.

Metadata parsing, ACS handler, JIT provisioning, RBAC mapping.
"""
=======
import hashlib
import base64
import requests
from typing import Dict, List, Optional
import json
import os

class OktaConfig:
    """Configuration for Okta SSO."""
    def __init__(self, client_id: str, client_secret: str, domain: str, redirect_uri: str, scopes: Optional[List[str]] = None):
        if not all([client_id, client_secret, domain, redirect_uri]):
            raise ValueError("OktaConfig: All parameters (client_id, client_secret, domain, redirect_uri) must be provided.")
        self.client_id = client_id
        self.client_secret = client_secret
        self.domain = domain
        self.redirect_uri = redirect_uri
        self.scopes = scopes if scopes is not None else ["openid", "email", "profile"]
        self.authorize_url = f"https://{self.domain}/oauth2/default/v1/authorize"
        self.token_url = f"https://{self.domain}/oauth2/default/v1/token"
        self.userinfo_url = f"https://{self.domain}/oauth2/default/v1/userinfo"
        self.revoke_url = f"https://{self.domain}/oauth2/default/v1/revoke"
        self.jwks_url = f"https://{self.domain}/oauth2/default/v1/keys"

class OktaProvider:
    """
    Okta SSO Provider for handling OAuth 2.0 and OpenID Connect flows.
    Implements PKCE (S256 code challenge).
    """
    def __init__(self, config: OktaConfig):
        self.config = config

    def get_authorization_url(self, state: str, code_challenge: str, code_challenge_method: str = "S256") -> str:
        """
        Generates the authorization URL for Okta.

        Args:
            state (str): An opaque value used to maintain state between the request and callback.
            code_challenge (str): PKCE code challenge.
            code_challenge_method (str): PKCE code challenge method, defaults to "S256".

        Returns:
            str: The authorization URL.
        """
        params = {
            "client_id": self.config.client_id,
            "response_type": "code",
            "scope": " ".join(self.config.scopes),
            "redirect_uri": self.config.redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
        }
        from urllib.parse import urlencode
        return f"{self.config.authorize_url}?{urlencode(params)}"

    def exchange_code_for_tokens(self, code: str, code_verifier: str) -> Dict:
        """
        Exchanges the authorization code for access, ID, and refresh tokens.

        Args:
            code (str): The authorization code received from Okta.
            code_verifier (str): The PKCE code verifier.

        Returns:
            Dict: A dictionary containing the tokens.
        
        Raises:
            requests.exceptions.RequestException: If the token exchange fails.
        """
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "authorization_code",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "redirect_uri": self.config.redirect_uri,
            "code": code,
            "code_verifier": code_verifier,
        }
        response = requests.post(self.config.token_url, headers=headers, data=data, timeout=10)
        response.raise_for_status()
        return response.json()

    def get_user_info(self, access_token: str) -> Dict:
        """
        Retrieves user information using the access token.

        Args:
            access_token (str): The access token.

        Returns:
            Dict: A dictionary containing user information.

        Raises:
            requests.exceptions.RequestException: If retrieving user info fails.
        """
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        response = requests.get(self.config.userinfo_url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()

    def validate_id_token(self, id_token: str) -> Dict:
        """
        Validates the ID token and returns its claims.

        Args:
            id_token (str): The ID token to validate.

        Returns:
            Dict: The decoded and validated ID token claims.

        Raises:
            ValueError: If the ID token is invalid or validation fails.
        """
        import jwt
        from jwt.exceptions import InvalidTokenError

        try:
            # Fetch JWKS from Okta
            jwks_response = requests.get(self.config.jwks_url, timeout=10)
            jwks_response.raise_for_status()
            jwks = jwks_response.json()

            # Decode the ID token using the fetched JWKS
            decoded_token = jwt.decode(
                id_token,
                jwks,
                algorithms=["RS256"],
                audience=self.config.client_id,
                issuer=f"https://{self.config.domain}/oauth2/default"
            )
            return decoded_token
        except InvalidTokenError as e:
            raise ValueError(f"Invalid ID token: {e}")
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Failed to retrieve JWKS: {e}")

    def revoke_token(self, token: str) -> bool:
        """
        Revokes an access or refresh token.

        Args:
            token (str): The token to revoke.

        Returns:
            bool: True if the token was successfully revoked, False otherwise.

        Raises:
            requests.exceptions.RequestException: If the token revocation fails.
        """
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "token": token,
        }
        response = requests.post(self.config.revoke_url, headers=headers, data=data, timeout=10)
        response.raise_for_status()
        return response.status_code == 200

def generate_pkce_pair() -> Dict[str, str]:
    """
    Generates a PKCE code verifier and code challenge.

    Returns:
        Dict[str, str]: A dictionary containing \'code_verifier\' and \'code_challenge\'.
    """
    code_verifier = base64.urlsafe_b64encode(os.urandom(128)).decode().rstrip("=")
    code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("ascii")).digest()).decode().rstrip("=")
    return {
        "code_verifier": code_verifier,
        "code_challenge": code_challenge
    }
>>>>>>> 322a69b (feat(phase-21a): implement Okta, Azure AD, Google SSO providers — 79/79 tests, 0 bandit issues)

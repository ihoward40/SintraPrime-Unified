
import requests
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from dataclasses import dataclass, field
from typing import List, Dict, Any
import time

@dataclass
class GoogleConfig:
    client_id: str
    client_secret: str
    redirect_uri: str
    hosted_domain: str = None
    scopes: List[str] = field(default_factory=lambda: ["openid", "email", "profile"])

    def __post_init__(self):
        if not self.client_id:
            raise ValueError("GoogleConfig: client_id is required")
        if not self.client_secret:
            raise ValueError("GoogleConfig: client_secret is required")
        if not self.redirect_uri:
            raise ValueError("GoogleConfig: redirect_uri is required")

class GoogleWorkspaceProvider:
    """Google Workspace SSO Provider"""

    def __init__(self, config: GoogleConfig):
        self.config = config
        self.authorize_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"  # nosec B105 - public OAuth2 endpoint, not a password
        self.userinfo_url = "https://openidconnect.googleapis.com/v1/userinfo"
        self.jwks_url = "https://www.googleapis.com/oauth2/v3/certs"

    def get_authorization_url(self, state: str) -> str:
        """Constructs the Google authorization URL."""
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.config.scopes),
            "access_type": "offline",
            "state": state,
            "prompt": "select_account",
        }
        if self.config.hosted_domain:
            params["hd"] = self.config.hosted_domain
        return f"{self.authorize_url}?{requests.compat.urlencode(params)}"

    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchanges authorization code for access, ID, and refresh tokens."""
        data = {
            "code": code,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "redirect_uri": self.config.redirect_uri,
            "grant_type": "authorization_code",
        }
        response = requests.post(self.token_url, data=data, timeout=10)
        response.raise_for_status()
        return response.json()

    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Retrieves user information using the access token."""
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        response = requests.get(self.userinfo_url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()

    def validate_id_token(self, id_token: str) -> Dict[str, Any]:
        """Validates the ID token and returns its claims."""
        jwks_client = jwt.PyJWKClient(self.jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(id_token)

        options = {
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

        decoded_token = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=self.config.client_id,
            issuer="https://accounts.google.com",
            options=options
        )
        return decoded_token

    def verify_hosted_domain(self, id_token_claims: Dict[str, Any]) -> bool:
        """Verifies if the hosted domain in the ID token matches the configured hosted domain."""
        if self.config.hosted_domain:
            return id_token_claims.get("hd") == self.config.hosted_domain
        return True

"""
Okta SSO Configuration.

Fail-closed: All settings required, no defaults.
"""

import os
from typing import Optional


class OktaConfig:
    """Okta provider configuration."""

    def __init__(
        self,
        okta_domain: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: Optional[list[str]] = None,
        timeout_seconds: int = 30,
    ):
        """
        Initialize Okta configuration.

        Args:
            okta_domain: Okta tenant domain (e.g., 'https://dev-12345.okta.com')
            client_id: OAuth 2.0 client ID
            client_secret: OAuth 2.0 client secret
            redirect_uri: OAuth 2.0 redirect URI
            scopes: OAuth scopes (default: ['openid', 'profile', 'email'])
            timeout_seconds: HTTP timeout in seconds

        Raises:
            ValueError: If any required config is missing
        """
        if not okta_domain or not okta_domain.startswith("https://"):
            raise ValueError("okta_domain must be absolute HTTPS URL")
        if not client_id:
            raise ValueError("client_id is required")
        if not client_secret:
            raise ValueError("client_secret is required")
        if not redirect_uri:
            raise ValueError("redirect_uri is required")

        self.okta_domain = okta_domain.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes or ["openid", "profile", "email"]
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls) -> "OktaConfig":
        """
        Load Okta configuration from environment variables.

        Environment variables:
            OKTA_DOMAIN: Okta tenant domain
            OKTA_CLIENT_ID: OAuth 2.0 client ID
            OKTA_CLIENT_SECRET: OAuth 2.0 client secret
            OKTA_REDIRECT_URI: OAuth 2.0 redirect URI
            OKTA_SCOPES: Comma-separated scopes (optional)
            OKTA_TIMEOUT_SECONDS: HTTP timeout (optional, default 30)

        Returns:
            OktaConfig instance

        Raises:
            ValueError: If required env vars are missing
        """
        okta_domain = os.getenv("OKTA_DOMAIN")
        client_id = os.getenv("OKTA_CLIENT_ID")
        client_secret = os.getenv("OKTA_CLIENT_SECRET")
        redirect_uri = os.getenv("OKTA_REDIRECT_URI")

        if not okta_domain:
            raise ValueError("OKTA_DOMAIN environment variable is required")
        if not client_id:
            raise ValueError("OKTA_CLIENT_ID environment variable is required")
        if not client_secret:
            raise ValueError("OKTA_CLIENT_SECRET environment variable is required")
        if not redirect_uri:
            raise ValueError("OKTA_REDIRECT_URI environment variable is required")

        scopes_str = os.getenv("OKTA_SCOPES")
        scopes = scopes_str.split(",") if scopes_str else None

        timeout_seconds = int(os.getenv("OKTA_TIMEOUT_SECONDS", "30"))

        return cls(
            okta_domain=okta_domain,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scopes=scopes,
            timeout_seconds=timeout_seconds,
        )
"""
Okta OAuth 2.0 Provider.

Implements OAuth 2.0 authorization code flow for Okta.
"""

import json
import logging
import secrets
import urllib.parse
from typing import Optional

from .okta_config import OktaConfig
from .okta_models import OktaTokenResponse, OktaUserInfo

logger = logging.getLogger(__name__)


class OktaProvider:
    """Okta OAuth 2.0 provider."""

    def __init__(self, config: OktaConfig):
        """
        Initialize Okta provider.

        Args:
            config: OktaConfig instance
        """
        self.config = config

    def get_authorization_url(self, state: Optional[str] = None) -> tuple[str, str]:
        """
        Generate OAuth authorization URL.

        Args:
            state: Optional CSRF protection state (generated if not provided)

        Returns:
            Tuple of (auth_url, state)
        """
        state = state or secrets.token_urlsafe(32)

        params = {
            "client_id": self.config.client_id,
            "response_type": "code",
            "scope": " ".join(self.config.scopes),
            "redirect_uri": self.config.redirect_uri,
            "state": state,
        }

        auth_url = (
            f"{self.config.okta_domain}/oauth2/v1/authorize?"
            + urllib.parse.urlencode(params)
        )

        return auth_url, state

    def exchange_code_for_token(self, code: str) -> OktaTokenResponse:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from callback

        Returns:
            OktaTokenResponse with access_token, id_token, etc.

        Raises:
            ValueError: If token exchange fails
        """
        # This is a mock implementation for testing.
        # In production, this would make an HTTPS POST to the token endpoint.
        if not code:
            raise ValueError("code is required")

        # Simulate token response
        return OktaTokenResponse(
            access_token=f"okta_access_{code[:20]}",
            token_type="Bearer",
            expires_in=3600,
            scope=" ".join(self.config.scopes),
            id_token=f"okta_id_{code[:20]}",
        )

    def get_user_info(self, access_token: str) -> OktaUserInfo:
        """
        Fetch user information using access token.

        Args:
            access_token: OAuth access token from token endpoint

        Returns:
            OktaUserInfo with user profile

        Raises:
            ValueError: If userinfo request fails
        """
        if not access_token:
            raise ValueError("access_token is required")

        # This is a mock implementation for testing.
        # In production, this would make an HTTPS GET to the userinfo endpoint.
        return OktaUserInfo(
            sub=f"okta_sub_{access_token[:20]}",
            email=f"user_{access_token[:10]}@example.com",
            email_verified=True,
            name="Test User",
        )

    def validate_state(self, state: str, expected_state: str) -> bool:
        """
        Validate state parameter for CSRF protection.

        Args:
            state: State from callback
            expected_state: State generated during authorization

        Returns:
            True if state is valid, False otherwise
        """
        # Constant-time comparison to prevent timing attacks
        return secrets.compare_digest(state, expected_state)
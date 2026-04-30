"""
Okta OAuth 2.0 Provider.

Implements OAuth 2.0 authorization code flow for Okta.
Real HTTP boundary: injectable httpx.AsyncClient for dependency injection.
Tests use mocked responses; production uses real HTTPS calls.
"""

import json
import logging
import secrets
import urllib.parse
from typing import Optional

import httpx

from .okta_config import OktaConfig
from .okta_models import OktaTokenResponse, OktaUserInfo

logger = logging.getLogger(__name__)


class OktaProvider:
    """Okta OAuth 2.0 provider with injectable HTTP client."""

    def __init__(self, config: OktaConfig, client: Optional[httpx.AsyncClient] = None):
        """
        Initialize Okta provider.

        Args:
            config: OktaConfig instance
            client: httpx.AsyncClient for HTTP requests (optional; creates default if None)
        """
        self.config = config
        self.client = client or httpx.AsyncClient()
        self._owns_client = client is None  # Track if we created the client

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit; closes client if we own it."""
        if self._owns_client:
            await self.client.aclose()

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

    async def exchange_code_for_token(self, code: str) -> OktaTokenResponse:
        """
        Exchange authorization code for access token via HTTPS.

        Args:
            code: Authorization code from callback

        Returns:
            OktaTokenResponse with access_token, id_token, etc.

        Raises:
            ValueError: If code is missing
            httpx.HTTPError: If token endpoint request fails
        """
        if not code:
            raise ValueError("code is required")

        token_url = f"{self.config.okta_domain}/oauth2/v1/token"
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "redirect_uri": self.config.redirect_uri,
        }

        try:
            response = await self.client.post(
                token_url,
                data=payload,
                headers={"Accept": "application/json"},
                timeout=10.0,
            )
            response.raise_for_status()
            token_data = response.json()

            return OktaTokenResponse(
                access_token=token_data.get("access_token", ""),
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data.get("expires_in", 3600),
                scope=token_data.get("scope", " ".join(self.config.scopes)),
                id_token=token_data.get("id_token", ""),
            )
        except httpx.HTTPError as e:
            logger.error(f"Okta token exchange failed: {e}")
            raise

    async def get_user_info(self, access_token: str) -> OktaUserInfo:
        """
        Fetch user information using access token via HTTPS.

        Args:
            access_token: OAuth access token from token endpoint

        Returns:
            OktaUserInfo with user profile

        Raises:
            ValueError: If access_token is missing
            httpx.HTTPError: If userinfo request fails
        """
        if not access_token:
            raise ValueError("access_token is required")

        userinfo_url = f"{self.config.okta_domain}/oauth2/v1/userinfo"

        try:
            response = await self.client.get(
                userinfo_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
                timeout=10.0,
            )
            response.raise_for_status()
            user_data = response.json()

            return OktaUserInfo(
                sub=user_data.get("sub", ""),
                email=user_data.get("email", ""),
                email_verified=user_data.get("email_verified", False),
                name=user_data.get("name", ""),
            )
        except httpx.HTTPError as e:
            logger.error(f"Okta userinfo request failed: {e}")
            raise

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

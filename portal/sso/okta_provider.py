"""
Okta OAuth 2.0 Provider.
Implements OAuth 2.0 authorization code flow for Okta using real HTTPS endpoints.
"""
import logging
import secrets
import urllib.parse
from typing import Optional

import httpx

from .okta_config import OktaConfig
from .okta_models import OktaTokenResponse, OktaUserInfo

logger = logging.getLogger(__name__)


class OktaProvider:
    """
    Okta OAuth 2.0 provider with real HTTPS boundary.

    Uses dependency injection for the HTTP client so tests can inject
    a mock AsyncClient without making real network calls.

    Usage (production):
        provider = OktaProvider(config)

    Usage (tests):
        provider = OktaProvider(config, client=AsyncMock(...))
    """

    def __init__(
        self,
        config: OktaConfig,
        client: Optional[httpx.AsyncClient] = None,
    ):
        """
        Initialize Okta provider.

        Args:
            config: OktaConfig instance (fail-closed validation)
            client: Optional injected AsyncClient for testing.
        """
        self.config = config
        self._client = client

    def get_authorization_url(self, state: Optional[str] = None) -> tuple[str, str]:
        """
        Generate OAuth 2.0 authorization URL.

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
        Exchange authorization code for tokens via real HTTPS POST.

        POST {okta_domain}/oauth2/v1/token

        Args:
            code: Authorization code from callback

        Returns:
            OktaTokenResponse

        Raises:
            ValueError: If code is empty or token exchange fails
        """
        if not code:
            raise ValueError("code is required")

        token_url = f"{self.config.okta_domain}/oauth2/v1/token"
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.config.redirect_uri,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }

        try:
            if self._client is not None:
                response = await self._client.post(
                    token_url,
                    data=payload,
                    timeout=self.config.timeout_seconds,
                )
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        token_url,
                        data=payload,
                        timeout=self.config.timeout_seconds,
                    )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Okta token exchange failed: %s %s",
                exc.response.status_code,
                exc.response.text[:200],
            )
            raise ValueError(
                f"Okta token exchange failed: {exc.response.status_code}"
            ) from exc

        return OktaTokenResponse(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_in=data.get("expires_in", 3600),
            scope=data.get("scope", " ".join(self.config.scopes)),
            id_token=data.get("id_token"),
            refresh_token=data.get("refresh_token"),
        )

    async def get_user_info(self, access_token: str) -> OktaUserInfo:
        """
        Fetch user profile via real HTTPS GET to Okta userinfo endpoint.

        GET {okta_domain}/oauth2/v1/userinfo

        Args:
            access_token: Bearer token from token exchange

        Returns:
            OktaUserInfo

        Raises:
            ValueError: If access_token is empty or request fails
        """
        if not access_token:
            raise ValueError("access_token is required")

        userinfo_url = f"{self.config.okta_domain}/oauth2/v1/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            if self._client is not None:
                response = await self._client.get(
                    userinfo_url,
                    headers=headers,
                    timeout=self.config.timeout_seconds,
                )
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        userinfo_url,
                        headers=headers,
                        timeout=self.config.timeout_seconds,
                    )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Okta userinfo failed: %s %s",
                exc.response.status_code,
                exc.response.text[:200],
            )
            raise ValueError(
                f"Okta userinfo request failed: {exc.response.status_code}"
            ) from exc

        return OktaUserInfo(
            sub=data["sub"],
            email=data.get("email", ""),
            email_verified=data.get("email_verified", False),
            name=data.get("name"),
            given_name=data.get("given_name"),
            family_name=data.get("family_name"),
            preferred_username=data.get("preferred_username"),
            groups=data.get("groups", []),
        )

    def validate_state(self, state: str, expected_state: str) -> bool:
        """
        Validate CSRF state parameter using constant-time comparison.

        Args:
            state: State received from callback
            expected_state: State generated during authorization

        Returns:
            True if states match, False otherwise
        """
        return secrets.compare_digest(state, expected_state)

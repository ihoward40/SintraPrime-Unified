"""
Okta OAuth 2.0 provider with injectable HTTP client.

Design decisions:
- All HTTP calls use real httpx.AsyncClient (no mock at module level).
- Timeout is sourced from OktaConfig.timeout_seconds (not hardcoded).
- HTTPStatusError is caught and re-raised as ValueError to avoid leaking
  raw httpx internals to callers.
- Refresh token revocation mirrors the Sessions layer: old token is
  revoked at Okta's /oauth2/v1/revoke endpoint before issuing a new one.
- Dependency injection: pass `client=` in tests to avoid real network calls.
"""
import logging
import secrets
import urllib.parse

import httpx

from .okta_config import OktaConfig
from .okta_models import OktaTokenResponse, OktaUserInfo

logger = logging.getLogger(__name__)


class OktaProvider:
    """Okta OAuth 2.0 OIDC provider."""

    def __init__(
        self,
        config: OktaConfig,
        client: httpx.AsyncClient | None = None,
    ):
        self.config = config
        self._timeout = httpx.Timeout(float(config.timeout_seconds))
        self.client = client or httpx.AsyncClient(timeout=self._timeout)
        self._owns_client = client is None

    async def __aenter__(self) -> "OktaProvider":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._owns_client:
            await self.client.aclose()

    def get_authorization_url(self, state: str | None = None) -> tuple[str, str]:
        """Generate the OAuth 2.0 authorization URL."""
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
        Exchange an authorization code for tokens via POST /oauth2/v1/token.

        Raises:
            ValueError: If code is empty, or Okta returns a non-2xx status.
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
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Okta token exchange failed: HTTP %s",
                exc.response.status_code,
            )
            raise ValueError(
                f"Okta token exchange failed with HTTP {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            logger.error("Okta token exchange network error: %s", exc)
            raise ValueError(f"Okta token exchange network error: {exc}") from exc

        token_data = response.json()
        return OktaTokenResponse(
            access_token=token_data.get("access_token", ""),
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data.get("expires_in", 3600),
            scope=token_data.get("scope", " ".join(self.config.scopes)),
            id_token=token_data.get("id_token"),
            refresh_token=token_data.get("refresh_token"),
        )

    async def get_user_info(self, access_token: str) -> OktaUserInfo:
        """
        Retrieve user profile from GET /oauth2/v1/userinfo.

        Raises:
            ValueError: If access_token is empty, or Okta returns a non-2xx status.
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
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Okta userinfo failed: HTTP %s",
                exc.response.status_code,
            )
            raise ValueError(
                f"Okta userinfo failed with HTTP {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            logger.error("Okta userinfo network error: %s", exc)
            raise ValueError(f"Okta userinfo network error: {exc}") from exc

        user_data = response.json()
        return OktaUserInfo(
            sub=user_data.get("sub", ""),
            email=user_data.get("email"),
            email_verified=user_data.get("email_verified", False),
            name=user_data.get("name"),
            given_name=user_data.get("given_name"),
            family_name=user_data.get("family_name"),
            preferred_username=user_data.get("preferred_username"),
            groups=user_data.get("groups", []),
        )

    async def refresh_access_token(self, refresh_token: str) -> OktaTokenResponse:
        """
        Exchange a refresh token for a new access token, revoking the old one first.

        The old refresh_token is revoked at /oauth2/v1/revoke before the new
        token is issued, mirroring the Sessions layer's revocation behaviour.

        Raises:
            ValueError: If refresh_token is empty, or Okta returns a non-2xx status.
        """
        if not refresh_token:
            raise ValueError("refresh_token is required")

        # Revoke old token first (fail-open: log but do not block refresh)
        await self._revoke_token(refresh_token, token_type_hint="refresh_token")  # nosec B106 - not a password, this is an OAuth token type hint  # nosec B106 — not a password, this is an OAuth token type hint

        token_url = f"{self.config.okta_domain}/oauth2/v1/token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "scope": " ".join(self.config.scopes),
        }
        try:
            response = await self.client.post(
                token_url,
                data=payload,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Okta token refresh failed: HTTP %s",
                exc.response.status_code,
            )
            raise ValueError(
                f"Okta token refresh failed with HTTP {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            logger.error("Okta token refresh network error: %s", exc)
            raise ValueError(f"Okta token refresh network error: {exc}") from exc

        token_data = response.json()
        return OktaTokenResponse(
            access_token=token_data.get("access_token", ""),
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data.get("expires_in", 3600),
            scope=token_data.get("scope", " ".join(self.config.scopes)),
            id_token=token_data.get("id_token"),
            refresh_token=token_data.get("refresh_token"),
        )

    async def _revoke_token(
        self, token: str, token_type_hint: str = "access_token"
    ) -> None:
        """Revoke a token at /oauth2/v1/revoke (fail-open)."""
        revoke_url = f"{self.config.okta_domain}/oauth2/v1/revoke"
        try:
            response = await self.client.post(
                revoke_url,
                data={
                    "token": token,
                    "token_type_hint": token_type_hint,
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                },
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            logger.debug("Revoked %s successfully", token_type_hint)
        except httpx.HTTPError as exc:
            logger.warning("Token revocation failed (non-fatal): %s", exc)

    def validate_state(self, state: str, expected_state: str) -> bool:
        """Validate OAuth state parameter using constant-time comparison."""
        return secrets.compare_digest(state, expected_state)

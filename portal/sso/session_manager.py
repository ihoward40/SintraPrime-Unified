"""
Session Manager
Orchestrates session creation, validation, refresh, and revocation.
Fail-closed security posture.
"""
from typing import Optional

from .jwt_service import JWTTokenService
from .session_config import SessionConfig
from .session_models import RefreshToken, SessionData, TokenPair
from .session_store import InMemorySessionStore, SessionStore


class SessionManager:
    """
    Manages user sessions, JWT tokens, and refresh flows.
    Fail-closed: invalid configs or missing dependencies raise errors.
    """

    def __init__(self, config: SessionConfig, store: Optional[SessionStore] = None):
        """
        Initialize SessionManager.

        Args:
            config: SessionConfig instance
            store: SessionStore instance (defaults to InMemorySessionStore)
        """
        config.validate()
        self.config = config

        # Resolve session store
        if store:
            self.store = store
        elif config.session_store_type == "redis":
            # Lazy initialization for Redis to avoid import errors in test
            raise ValueError(
                "Redis store requested but not provided. "
                "Pass RedisSessionStore instance or use 'memory' store type."
            )
        else:
            self.store = InMemorySessionStore()

        self.jwt_service = JWTTokenService(config)

    async def create_session(
        self,
        user_id: str,
        email: str,
        name_id: Optional[str] = None,
        identity_provider: Optional[str] = None,
        auth_method: Optional[str] = None,
        attributes: Optional[dict[str, str]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenPair:
        """
        Create new session and return token pair.
        """
        # Create session data
        session = SessionData.create(
            user_id=user_id,
            email=email,
            issuer=self.config.issuer,
            audience=self.config.audience,
            ttl_seconds=self.config.session_ttl_seconds,
            name_id=name_id,
            identity_provider=identity_provider,
            auth_method=auth_method,
            attributes=attributes or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Create refresh token
        refresh_token = RefreshToken.create(
            session_id=session.session_id,
            user_id=user_id,
            ttl_seconds=self.config.refresh_token_ttl_seconds,
        )

        # Save to store
        await self.store.save_session(session, self.config.session_ttl_seconds)
        await self.store.save_refresh_token(refresh_token, self.config.refresh_token_ttl_seconds)

        # Generate token pair
        return self.jwt_service.generate_token_pair(
            session_id=session.session_id,
            user_id=user_id,
            email=email,
            refresh_token_id=refresh_token.token_id,
            additional_claims={
                "identity_provider": identity_provider,
                "auth_method": auth_method,
            } if identity_provider or auth_method else None,
        )


    async def validate_session(self, access_token: str) -> Optional[SessionData]:
        """
        Validate access token and return session data if valid.
        Returns None if token is invalid or expired.
        """
        try:
            payload = self.jwt_service.validate_token(access_token, token_type="access")
            session_id = payload.get("session_id")

            if not session_id:
                return None

            session = await self.store.get_session(session_id)
            if not session or not session.is_valid():
                return None

            return session
        except Exception:
            return None

    async def refresh_session(self, refresh_token: str) -> Optional[TokenPair]:
        """
        Refresh an expired session using a refresh token.
        Returns new token pair if refresh token is valid, None otherwise.
        """
        try:
            payload = self.jwt_service.validate_token(refresh_token, token_type="refresh")

            session_id = payload.get("session_id")
            user_id = payload.get("sub")
            refresh_token_id = payload.get("refresh_token_id")

            if not all([session_id, user_id, refresh_token_id]):
                return None

            # Verify refresh token in store
            stored_token = await self.store.get_refresh_token(refresh_token_id)
            if not stored_token or not stored_token.is_valid():
                return None

            # Get original session
            session = await self.store.get_session(session_id)
            if not session:
                return None

            # Revoke old refresh token (prevent token replay attacks)
            stored_token.is_revoked = True
            await self.store.save_refresh_token(stored_token, self.config.refresh_token_ttl_seconds)

            # Create new refresh token
            new_refresh_token = RefreshToken.create(
                session_id=session_id,
                user_id=user_id,
                ttl_seconds=self.config.refresh_token_ttl_seconds,
            )

            # Save new refresh token
            await self.store.save_refresh_token(new_refresh_token, self.config.refresh_token_ttl_seconds)

            # Generate new token pair
            return self.jwt_service.generate_token_pair(
                session_id=session_id,
                user_id=user_id,
                email=session.email,
                refresh_token_id=new_refresh_token.token_id,
            )


        except Exception:
            return None

    async def revoke_session(self, session_id: str) -> bool:
        """
        Revoke a session (logout).
        """
        try:
            await self.store.revoke_session(session_id)
            return True
        except Exception:
            return False

    async def revoke_refresh_token(self, refresh_token_id: str) -> bool:
        """
        Revoke a specific refresh token.
        """
        try:
            await self.store.revoke_refresh_token(refresh_token_id)
            return True
        except Exception:
            return False

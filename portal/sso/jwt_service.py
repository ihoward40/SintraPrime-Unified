"""
JWT Token Generation and Validation Service
Fail-closed: invalid tokens raise explicit errors.
"""
from datetime import datetime, timedelta
from typing import Optional

import jwt
from jwt.exceptions import (
    DecodeError,
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidTokenError,
)

from .session_config import SessionConfig
from .session_models import TokenPair


class JWTTokenService:
    """Generate and validate JWT tokens for SSO sessions."""

    def __init__(self, config: SessionConfig):
        """Initialize with session config."""
        config.validate()
        self.config = config

    def generate_access_token(
        self,
        session_id: str,
        user_id: str,
        email: str,
        additional_claims: Optional[dict] = None,
    ) -> str:
        """
        Generate JWT access token.
        Fail-closed: raises on missing config.
        """
        if not self.config.jwt_secret_key:
            raise ValueError("JWT secret key not configured")
        if not self.config.issuer:
            raise ValueError("JWT issuer not configured")
        if not self.config.audience:
            raise ValueError("JWT audience not configured")

        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=self.config.jwt_expiration_seconds)

        payload = {
            "sub": user_id,
            "email": email,
            "session_id": session_id,
            "iat": now,
            "exp": expires_at,
            "iss": self.config.issuer,
            "aud": self.config.audience,
            "type": "access",
        }

        if additional_claims:
            payload.update(additional_claims)

        return jwt.encode(
            payload,
            self.config.jwt_secret_key,
            algorithm=self.config.jwt_algorithm,
        )

    def generate_refresh_token(
        self,
        session_id: str,
        user_id: str,
        refresh_token_id: str,
    ) -> str:
        """
        Generate JWT refresh token.
        Fail-closed: raises on missing config.
        """
        if not self.config.jwt_secret_key:
            raise ValueError("JWT secret key not configured")
        if not self.config.issuer:
            raise ValueError("JWT issuer not configured")
        if not self.config.audience:
            raise ValueError("JWT audience not configured")

        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=self.config.jwt_refresh_expiration_seconds)

        payload = {
            "sub": user_id,
            "session_id": session_id,
            "refresh_token_id": refresh_token_id,
            "iat": now,
            "exp": expires_at,
            "iss": self.config.issuer,
            "aud": self.config.audience,
            "type": "refresh",
        }

        return jwt.encode(
            payload,
            self.config.jwt_secret_key,
            algorithm=self.config.jwt_algorithm,
        )

    def validate_token(self, token: str, token_type: str = "access") -> dict:
        """
        Validate and decode JWT token.

        Args:
            token: JWT token string
            token_type: "access" or "refresh"

        Returns:
            Decoded token payload

        Raises:
            ExpiredSignatureError: Token has expired
            InvalidTokenError: Token is invalid
            InvalidIssuerError: Issuer mismatch
            InvalidAudienceError: Audience mismatch
        """
        if not self.config.jwt_secret_key:
            raise ValueError("JWT secret key not configured")

        try:
            payload = jwt.decode(
                token,
                self.config.jwt_secret_key,
                algorithms=[self.config.jwt_algorithm],
                issuer=self.config.issuer,
                audience=self.config.audience,
                options={"leeway": self.config.allowed_clock_skew_seconds},
            )

            # Verify token type
            if payload.get("type") != token_type:
                raise InvalidTokenError(f"Token type mismatch: expected {token_type}")

            return payload

        except ExpiredSignatureError:
            raise ExpiredSignatureError("Token has expired") from None
        except InvalidIssuerError:
            raise InvalidIssuerError("Token issuer mismatch") from None
        except InvalidAudienceError:
            raise InvalidAudienceError("Token audience mismatch") from None
        except DecodeError as e:
            raise InvalidTokenError(f"Token decode error: {str(e)}") from e
        except Exception as e:
            raise InvalidTokenError(f"Token validation failed: {str(e)}") from e

    def generate_token_pair(
        self,
        session_id: str,
        user_id: str,
        email: str,
        refresh_token_id: str,
        additional_claims: Optional[dict] = None,
    ) -> TokenPair:
        """
        Generate both access and refresh tokens.
        """
        access_token = self.generate_access_token(
            session_id=session_id,
            user_id=user_id,
            email=email,
            additional_claims=additional_claims,
        )

        refresh_token = self.generate_refresh_token(
            session_id=session_id,
            user_id=user_id,
            refresh_token_id=refresh_token_id,
        )

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.config.jwt_expiration_seconds,
        )

"""
Session and Token Data Models
"""
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta


@dataclass
class SessionData:
    """
    User session data.
    Immutable reference for session operations.
    """
    session_id: str
    user_id: str
    email: str
    issuer: str
    audience: str
    created_at: datetime
    expires_at: datetime

    # SAML/OIDC attributes
    name_id: str | None = None
    identity_provider: str | None = None
    auth_method: str | None = None
    attributes: dict[str, str] = field(default_factory=dict)

    # Session tracking
    ip_address: str | None = None
    user_agent: str | None = None
    is_revoked: bool = False
    revoked_at: datetime | None = None

    @classmethod
    def create(
        cls,
        user_id: str,
        email: str,
        issuer: str,
        audience: str,
        ttl_seconds: int,
        **kwargs
    ) -> "SessionData":
        """Create a new session with generated ID."""
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=ttl_seconds)

        return cls(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            email=email,
            issuer=issuer,
            audience=audience,
            created_at=now,
            expires_at=expires_at,
            **kwargs
        )

    def is_expired(self) -> bool:
        """Check if session has expired."""
        return datetime.utcnow() >= self.expires_at

    def is_valid(self) -> bool:
        """Check if session is valid (not expired, not revoked)."""
        return not self.is_expired() and not self.is_revoked

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["expires_at"] = self.expires_at.isoformat()
        if self.revoked_at:
            data["revoked_at"] = self.revoked_at.isoformat()
        return data


@dataclass
class RefreshToken:
    """
    Refresh token for extending sessions.
    Single-use or rotatable depending on implementation.
    """
    token_id: str
    session_id: str
    user_id: str
    issued_at: datetime
    expires_at: datetime
    is_revoked: bool = False
    revoked_at: datetime | None = None

    @classmethod
    def create(
        cls,
        session_id: str,
        user_id: str,
        ttl_seconds: int,
    ) -> "RefreshToken":
        """Create a new refresh token."""
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=ttl_seconds)

        return cls(
            token_id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user_id,
            issued_at=now,
            expires_at=expires_at,
        )

    def is_expired(self) -> bool:
        """Check if refresh token has expired."""
        return datetime.utcnow() >= self.expires_at

    def is_valid(self) -> bool:
        """Check if refresh token is valid (not expired, not revoked)."""
        return not self.is_expired() and not self.is_revoked

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["issued_at"] = self.issued_at.isoformat()
        data["expires_at"] = self.expires_at.isoformat()
        if self.revoked_at:
            data["revoked_at"] = self.revoked_at.isoformat()
        return data


@dataclass
class TokenPair:
    """
    JWT access token + refresh token pair.
    """
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
        }

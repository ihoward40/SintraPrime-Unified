"""
Okta OAuth 2.0 response models.
"""
from dataclasses import dataclass, field


@dataclass
class OktaTokenResponse:
    """Okta token endpoint response."""

    access_token: str
    token_type: str  # Usually "Bearer"
    expires_in: int  # Seconds
    scope: str
    id_token: str | None = None
    refresh_token: str | None = None  # Present when offline_access scope granted

    @classmethod
    def from_dict(cls, data: dict) -> "OktaTokenResponse":
        """Parse token response from dict."""
        return cls(
            access_token=data.get("access_token", ""),
            token_type=data.get("token_type", "Bearer"),
            expires_in=data.get("expires_in", 3600),
            scope=data.get("scope", ""),
            id_token=data.get("id_token"),
            refresh_token=data.get("refresh_token"),
        )


@dataclass
class OktaUserInfo:
    """Okta userinfo endpoint response."""

    sub: str  # Subject (unique user ID)
    name: str | None = None
    email: str | None = None
    email_verified: bool = False
    given_name: str | None = None
    family_name: str | None = None
    locale: str | None = None
    preferred_username: str | None = None  # Okta login / username
    groups: list[str] = field(default_factory=list)  # Okta group memberships

    @classmethod
    def from_dict(cls, data: dict) -> "OktaUserInfo":
        """Parse userinfo response from dict."""
        return cls(
            sub=data.get("sub", ""),
            name=data.get("name"),
            email=data.get("email"),
            email_verified=data.get("email_verified", False),
            given_name=data.get("given_name"),
            family_name=data.get("family_name"),
            locale=data.get("locale"),
            preferred_username=data.get("preferred_username"),
            groups=data.get("groups", []),
        )

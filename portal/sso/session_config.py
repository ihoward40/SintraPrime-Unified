"""
Session Configuration Model
Fail-closed: all required config must be present
"""
import os
from dataclasses import dataclass


@dataclass
class SessionConfig:
    """
    SSO Session configuration.
    All required fields must be set; missing values raise ValueError.
    """

    # JWT signing
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_seconds: int = 3600  # 1 hour
    jwt_refresh_expiration_seconds: int = 604800  # 7 days

    # Session storage
    redis_url: str | None = None
    session_store_type: str = "redis"  # "redis" or "memory"
    session_ttl_seconds: int = 3600
    refresh_token_ttl_seconds: int = 604800

    # SAML/OIDC
    issuer: str = None
    audience: str = None
    allowed_clock_skew_seconds: int = 60

    # Security
    require_https: bool = True
    secure_cookies: bool = True
    same_site_cookie: str = "Strict"

    @classmethod
    def from_env(cls) -> "SessionConfig":
        """
        Load configuration from environment variables.
        Fail-closed: raises ValueError if required vars are missing.
        """
        jwt_secret = os.getenv("SSO_JWT_SECRET_KEY")
        if not jwt_secret:
            raise ValueError("SSO_JWT_SECRET_KEY environment variable is required")

        issuer = os.getenv("SSO_ISSUER")
        if not issuer:
            raise ValueError("SSO_ISSUER environment variable is required")

        audience = os.getenv("SSO_AUDIENCE")
        if not audience:
            raise ValueError("SSO_AUDIENCE environment variable is required")

        return cls(
            jwt_secret_key=jwt_secret,
            jwt_algorithm=os.getenv("SSO_JWT_ALGORITHM", "HS256"),
            jwt_expiration_seconds=int(os.getenv("SSO_JWT_EXPIRATION_SECONDS", "3600")),
            jwt_refresh_expiration_seconds=int(os.getenv("SSO_JWT_REFRESH_EXPIRATION_SECONDS", "604800")),
            redis_url=os.getenv("REDIS_URL"),
            session_store_type=os.getenv("SSO_SESSION_STORE_TYPE", "redis"),
            session_ttl_seconds=int(os.getenv("SSO_SESSION_TTL_SECONDS", "3600")),
            refresh_token_ttl_seconds=int(os.getenv("SSO_REFRESH_TOKEN_TTL_SECONDS", "604800")),
            issuer=issuer,
            audience=audience,
            allowed_clock_skew_seconds=int(os.getenv("SSO_ALLOWED_CLOCK_SKEW_SECONDS", "60")),
            require_https=os.getenv("SSO_REQUIRE_HTTPS", "true").lower() == "true",
            secure_cookies=os.getenv("SSO_SECURE_COOKIES", "true").lower() == "true",
            same_site_cookie=os.getenv("SSO_SAME_SITE_COOKIE", "Strict"),
        )

    def validate(self) -> None:
        """
        Validate configuration values.
        Raises ValueError if any validation fails.
        """
        if not self.jwt_secret_key:
            raise ValueError("jwt_secret_key is required")
        if len(self.jwt_secret_key) < 32:
            raise ValueError("jwt_secret_key must be at least 32 characters")
        if not self.issuer:
            raise ValueError("issuer is required")
        if not self.audience:
            raise ValueError("audience is required")
        if self.jwt_expiration_seconds <= 0:
            raise ValueError("jwt_expiration_seconds must be positive")
        if self.jwt_refresh_expiration_seconds <= 0:
            raise ValueError("jwt_refresh_expiration_seconds must be positive")
        if self.same_site_cookie not in ("Strict", "Lax", "None"):
            raise ValueError("same_site_cookie must be one of: Strict, Lax, None")

"""
Portal SSO module — Session management and OAuth 2.0 providers.
Provides session management, JWT generation/validation, and SAML provider integration.
Fail-closed behavior enforced: missing config raises explicit errors.
"""
__version__ = "0.1.0"

# Sessions
from .session_config import SessionConfig
from .session_models import SessionData, RefreshToken, TokenPair
from .session_manager import SessionManager
from .jwt_service import JWTTokenService
from .session_store import SessionStore, RedisSessionStore, InMemorySessionStore

# Okta
from .okta_config import OktaConfig
from .okta_models import OktaTokenResponse, OktaUserInfo
from .okta_provider import OktaProvider

__all__ = [
    # Sessions
    "SessionConfig",
    "SessionManager",
    "SessionData",
    "RefreshToken",
    "TokenPair",
    "SessionStore",
    "InMemorySessionStore",
    "RedisSessionStore",
    "JWTTokenService",
    # Okta
    "OktaConfig",
    "OktaTokenResponse",
    "OktaUserInfo",
    "OktaProvider",
]

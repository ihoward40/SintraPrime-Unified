"""
Portal SSO module — Session management and OAuth 2.0 providers.
Fail-closed behavior enforced: missing config raises explicit errors.
"""
__version__ = "0.1.0"

# Sessions
from .session_config import SessionConfig
from .session_manager import SessionManager
from .session_models import SessionData, RefreshToken, TokenPair
from .session_store import InMemorySessionStore, RedisSessionStore, SessionStore
from .jwt_service import JWTTokenService

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

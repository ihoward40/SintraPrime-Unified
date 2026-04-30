"""
SintraPrime SSO/SAML Portal Module
Provides session management, JWT generation/validation, and SAML provider integration.
Fail-closed behavior enforced: missing config raises explicit errors.
"""

__version__ = "0.1.0"
__all__ = [
    "SessionManager",
    "SessionConfig",
    "JWTTokenService",
    "SessionStore",
    "RedisSessionStore",
    "InMemorySessionStore",
    "SessionData",
    "RefreshToken",
    "TokenPair",
]

from .session_config import SessionConfig
from .session_models import SessionData, RefreshToken, TokenPair
from .session_manager import SessionManager
from .jwt_service import JWTTokenService
from .session_store import SessionStore, RedisSessionStore, InMemorySessionStore
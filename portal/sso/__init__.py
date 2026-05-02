"""
Portal SSO module — Session management and OAuth 2.0 providers.
Provides session management, JWT generation/validation, and SAML provider integration.
Fail-closed behavior enforced: missing config raises explicit errors.
"""
__version__ = "0.2.0"

# Sessions
from .jwt_service import JWTTokenService

# Phase 21C Middleware
from .middleware import (
    IdPError,
    IdPErrorHandler,
    SessionMiddleware,
    SessionMiddlewareManager,
    SessionToken,
    TokenRefreshManager,
)

# Okta
from .okta_config import OktaConfig
from .okta_models import OktaTokenResponse, OktaUserInfo
from .okta_provider import OktaProvider

# Azure AD + Google Workspace
from .providers.azure import AzureADProvider, AzureConfig
from .providers.google import GoogleConfig, GoogleWorkspaceProvider
from .session_config import SessionConfig
from .session_manager import SessionManager
from .session_models import RefreshToken, SessionData, TokenPair
from .session_store import InMemorySessionStore, RedisSessionStore, SessionStore

__all__ = [
    # Azure AD
    "AzureADProvider",
    "AzureConfig",
    "GoogleConfig",
    # Google Workspace
    "GoogleWorkspaceProvider",
    "IdPError",
    "IdPErrorHandler",
    "InMemorySessionStore",
    "JWTTokenService",
    # Okta
    "OktaConfig",
    "OktaProvider",
    "OktaTokenResponse",
    "OktaUserInfo",
    "RedisSessionStore",
    "RefreshToken",
    # Sessions
    "SessionConfig",
    "SessionData",
    "SessionManager",
    "SessionMiddleware",
    "SessionMiddlewareManager",
    "SessionStore",
    # Phase 21C Middleware
    "SessionToken",
    "TokenPair",
    "TokenRefreshManager",
]

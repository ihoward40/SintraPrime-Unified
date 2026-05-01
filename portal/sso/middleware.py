"""
Phase 21C: Session Middleware & Token Refresh Manager

Handles session lifecycle, background token refresh, circuit breaker for IdP errors.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class SessionMiddlewareManager:
    """Manages session lifecycle: create, refresh, validate, destroy."""

    def __init__(
        self,
        session_store: "SessionStore",
        jwt_service: "JWTService",
    ):
        self.session_store = session_store
        self.jwt_service = jwt_service
        self._sessions = {}  # In-memory fallback

    async def create_session(
        self,
        user_id: str,
        email: str,
        provider: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> str:
        """Create a new session."""
        return await self.session_store.create_session(
            user_id=user_id,
            email=email,
            provider=provider,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def validate_session(self, session_id: str) -> Optional[dict]:
        """Validate and retrieve session."""
        session = await self.session_store.get_session(session_id)
        if not session:
            return None
        
        # Check expiry
        expires_at = datetime.fromisoformat(session.expires_at)
        if datetime.now(timezone.utc) > expires_at:
            await self.invalidate_session(session_id)
            return None
        
        return session.dict()

    async def invalidate_session(self, session_id: str) -> None:
        """Invalidate a session."""
        await self.session_store.invalidate_session(session_id)
        self._sessions.pop(session_id, None)  # Remove from in-memory

    async def destroy_session(self, session_id: str) -> None:
        """Alias for invalidate_session (compatibility)."""
        await self.invalidate_session(session_id)


class TokenRefreshManager:
    """Handles refresh token rotation and expiry."""

    def __init__(
        self,
        jwt_service: "JWTService",
        refresh_callback: Optional[Callable] = None,
        refresh_threshold: int = 300,  # Refresh 5 min before expiry
    ):
        self.jwt_service = jwt_service
        self.refresh_callback = refresh_callback
        self.refresh_threshold = timedelta(seconds=refresh_threshold)
        self.failed_refreshes = {}  # Track failures per token
        self.max_failures = 3

    async def should_refresh_token(self, token: str) -> bool:
        """Check if token should be refreshed."""
        try:
            claims = self.jwt_service.verify_token(token)
            exp = claims.get("exp")
            if not exp:
                return False
            
            exp_time = datetime.fromtimestamp(exp, tz=timezone.utc)
            time_until_exp = exp_time - datetime.now(timezone.utc)
            return time_until_exp < self.refresh_threshold
        except Exception:
            return False

    async def refresh_token(self, token: str, refresh_token: str) -> Optional[str]:
        """Refresh an access token using refresh token."""
        try:
            # Verify refresh token is valid
            claims = self.jwt_service.verify_token(refresh_token)
            user_id = claims.get("sub")
            if not user_id:
                return None
            
            # Issue new access token
            new_token = self.jwt_service.create_token(
                subject=user_id,
                expires_in=timedelta(hours=1),
                claims={"type": "access"},
            )
            
            # Call optional callback
            if self.refresh_callback:
                await self.refresh_callback(user_id, new_token)
            
            self.failed_refreshes.pop(token, None)  # Clear failure count
            logger.info(f"Token refreshed for user {user_id}")
            return new_token
        
        except Exception as e:
            # Track failures
            self.failed_refreshes[token] = self.failed_refreshes.get(token, 0) + 1
            logger.warning(f"Token refresh failed: {e}")
            return None

    def record_failure(self) -> None:
        """Record a token validation failure."""
        pass  # Used for circuit breaker logic

    def is_circuit_open(self) -> bool:
        """Check if circuit breaker is open (too many failures)."""
        return len([v for v in self.failed_refreshes.values() if v >= self.max_failures]) > 0


class IdPErrorHandler:
    """Handles errors from identity providers with graceful degradation."""

    def __init__(self, max_retries: int = 3, retry_delay: int = 1):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.error_counts = {}  # Track errors per IdP

    async def handle_error(
        self,
        provider: str,
        error: Exception,
        context: Optional[dict] = None,
    ) -> dict:
        """Handle and log an IdP error."""
        self.error_counts[provider] = self.error_counts.get(provider, 0) + 1
        
        error_response = {
            "provider": provider,
            "error": str(error),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "retryable": self._is_retryable(error),
            "attempts": self.error_counts[provider],
        }
        
        if context:
            error_response["context"] = context
        
        logger.error(f"IdP error from {provider}: {error}", extra=error_response)
        return error_response

    def _is_retryable(self, error: Exception) -> bool:
        """Determine if error is retryable."""
        retryable_errors = (
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
        )
        return isinstance(error, retryable_errors)


class SessionMiddleware(BaseHTTPMiddleware):
    """ASGI middleware for session management."""

    def __init__(
        self,
        app: ASGIApp,
        session_manager: SessionMiddlewareManager,
    ):
        super().__init__(app)
        self.session_manager = session_manager

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and manage session."""
        # Extract session ID from cookie or Authorization header
        session_id = request.cookies.get("session_id")
        
        if session_id:
            # Validate session
            session = await self.session_manager.validate_session(session_id)
            if not session:
                # Invalid or expired session
                response = Response(status_code=401)
                response.delete_cookie("session_id")
                return response
            
            # Attach session to request state
            request.state.session = session
        
        # Process request
        response = await call_next(request)
        return response

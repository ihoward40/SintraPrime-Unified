"""
Phase 21C: Session Middleware & Token Refresh Manager

Handles session lifecycle, background token refresh, circuit breaker for IdP errors.
"""

import asyncio
import hashlib
import hmac
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Callable, Dict, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# Routes that do NOT require a session cookie
_PUBLIC_PREFIXES = ("/public", "/health", "/auth/", "/sso/", "/docs", "/openapi")


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class SessionToken:
    """Represents a validated session token."""

    user_id: str
    email: str
    provider: str
    issued_at: datetime
    expires_at: datetime
    refresh_token: Optional[str] = None
    refresh_expires_at: Optional[datetime] = None
    request_id: str = field(default_factory=lambda: "")

    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.now(timezone.utc) >= self.expires_at

    def needs_refresh(self, threshold_seconds: int = 300) -> bool:
        """Check if token needs refresh (within threshold of expiry)."""
        remaining = (self.expires_at - datetime.now(timezone.utc)).total_seconds()
        return remaining < threshold_seconds


class SessionMiddlewareManager:
    """Manages session lifecycle using an in-memory store with HMAC-keyed session IDs."""

    def __init__(
        self,
        session_secret: str,
        session_ttl_seconds: int = 3600,
        # Legacy keyword arguments accepted for compatibility with async-store callers
        session_store: Optional[object] = None,
        jwt_service: Optional[object] = None,
    ):
        self._secret = session_secret.encode()
        self._ttl = session_ttl_seconds
        self.sessions: Dict[str, SessionToken] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _make_session_id(self, token: SessionToken) -> str:
        """Derive a deterministic, secret-keyed session ID from the token."""
        payload = f"{token.user_id}:{token.email}:{token.provider}:{token.issued_at.isoformat()}"
        return hmac.new(self._secret, payload.encode(), hashlib.sha256).hexdigest()

    # ------------------------------------------------------------------
    # Public API (synchronous — used by ASGI middleware and tests)
    # ------------------------------------------------------------------

    def create_session(
        self,
        token: Optional[SessionToken] = None,
        *,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        """Store a session and return its session ID.

        When called with a pre-built ``SessionToken`` as the first positional
        argument, returns the raw session-ID string (64-char hex digest).

        When called with keyword arguments ``user_id``, ``email``, ``provider``,
        builds a ``SessionToken`` internally and returns a dict containing
        ``session_id`` plus the token fields — suitable for JSON serialisation.
        """
        _kw_mode = token is None
        if _kw_mode:
            if user_id is None or email is None or provider is None:
                raise ValueError("Must supply either a SessionToken or user_id/email/provider")
            now = datetime.now(timezone.utc)
            token = SessionToken(
                user_id=user_id,
                email=email,
                provider=provider,
                issued_at=now,
                expires_at=now + timedelta(seconds=self._ttl),
            )
        sid = self._make_session_id(token)
        self.sessions[sid] = token
        if _kw_mode:
            return {
                "session_id": sid,
                "user_id": token.user_id,
                "email": token.email,
                "provider": token.provider,
                "issued_at": token.issued_at.isoformat(),
                "expires_at": token.expires_at.isoformat(),
            }
        return sid

    def validate_session(self, session_id: str) -> Optional[SessionToken]:
        """Return the SessionToken if the session exists and is not expired."""
        token = self.sessions.get(session_id)
        if token is None:
            return None
        if token.is_expired():
            del self.sessions[session_id]
            return None
        return token

    def invalidate_session(self, session_id: str) -> bool:
        """Remove a session. Returns True if it existed, False otherwise."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def get_session_ttl(self) -> int:
        """Return the configured session TTL in seconds."""
        return self._ttl

    def destroy_session(self, session_id: str) -> bool:
        """Remove a session synchronously (alias for invalidate_session)."""
        return self.invalidate_session(session_id)

    # ------------------------------------------------------------------
    # Async compatibility shims (for callers that await these methods)
    # ------------------------------------------------------------------

    async def create_session_async(
        self,
        user_id: str,
        email: str,
        provider: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> str:
        """Async shim — creates a synthetic SessionToken and stores it."""
        now = datetime.now(timezone.utc)
        token = SessionToken(
            user_id=user_id,
            email=email,
            provider=provider,
            issued_at=now,
            expires_at=now + timedelta(seconds=self._ttl),
        )
        return self.create_session(token)

    async def validate_session_async(self, session_id: str) -> Optional[dict]:
        """Async shim — returns session as dict for compatibility."""
        token = self.validate_session(session_id)
        if token is None:
            return None
        return {
            "user_id": token.user_id,
            "email": token.email,
            "provider": token.provider,
            "issued_at": token.issued_at.isoformat(),
            "expires_at": token.expires_at.isoformat(),
        }

    async def invalidate_session_async(self, session_id: str) -> None:
        """Async shim."""
        self.invalidate_session(session_id)

    async def destroy_session_async(self, session_id: str) -> None:
        """Async shim for callers that await session destruction."""
        self.invalidate_session(session_id)


class TokenRefreshManager:
    """Handles background token refresh loops with per-session circuit breakers."""

    def __init__(
        self,
        refresh_callback: Optional[Callable] = None,
        max_failures: int = 3,
        failure_window_seconds: int = 300,
        # Legacy keyword arguments
        jwt_service: Optional[object] = None,
        refresh_threshold: int = 300,
    ):
        self.refresh_callback = refresh_callback
        self.max_failures = max_failures
        self.failure_window_seconds = failure_window_seconds
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.circuit_breaker_status: Dict[str, bool] = {}  # True = open (tripped)
        self._failure_counts: Dict[str, int] = {}
        # Per-provider circuit breaker (for e2e-style callers using provider names)
        self._provider_failures: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # Refresh loop management
    # ------------------------------------------------------------------

    async def start_refresh_loop(self, session_id: str, token: SessionToken) -> None:
        """Start a background refresh loop for a session (noop if already running)."""
        if session_id in self.active_tasks:
            return  # Duplicate start is a noop
        task = asyncio.ensure_future(self._refresh_loop(session_id, token))
        self.active_tasks[session_id] = task

    async def stop_refresh_loop(self, session_id: str) -> None:
        """Cancel and remove the refresh loop for a session."""
        task = self.active_tasks.pop(session_id, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

    async def _refresh_loop(self, session_id: str, token: SessionToken) -> None:
        """Internal loop: attempt refresh until token expires or circuit opens."""
        while not token.is_expired():
            if token.needs_refresh():
                await self._attempt_refresh(session_id, token)
            await asyncio.sleep(1)
        self.active_tasks.pop(session_id, None)

    async def _attempt_refresh(self, session_id: str, token: SessionToken) -> bool:
        """Attempt a single refresh. Updates circuit breaker on failure."""
        if self.circuit_breaker_status.get(session_id):
            return False  # Circuit is open
        try:
            if self.refresh_callback:
                success = await self.refresh_callback(session_id, token)
            else:
                success = True
            if success:
                self._record_success(session_id)
                return True
            # Treat False return as failure
            raise RuntimeError("Refresh callback returned False")
        except Exception as exc:
            self._record_failure(session_id)
            logger.warning("Refresh attempt failed for %s: %s", session_id, exc)
            return False

    # ------------------------------------------------------------------
    # Circuit breaker helpers (used by both async loop and sync tests)
    # ------------------------------------------------------------------

    def _record_failure(self, session_id: str) -> None:
        """Increment failure count for a session; open circuit at threshold."""
        count = self._failure_counts.get(session_id, 0) + 1
        self._failure_counts[session_id] = count
        if count >= self.max_failures:
            self.circuit_breaker_status[session_id] = True
            logger.error("Circuit breaker OPEN for session %s", session_id)

    def _record_success(self, session_id: str) -> None:
        """Reset failure count and close circuit for a session."""
        self._failure_counts[session_id] = 0
        self.circuit_breaker_status[session_id] = False

    def _is_circuit_broken(self, session_id: str) -> bool:
        """Return True if the per-session circuit breaker is open."""
        return bool(self.circuit_breaker_status.get(session_id, False))

    # ------------------------------------------------------------------
    # Provider-level circuit breaker (for e2e-style callers)
    # ------------------------------------------------------------------

    def record_failure(self, provider: str) -> None:
        """Record a provider-level failure (opens circuit at max_failures)."""
        count = self._provider_failures.get(provider, 0) + 1
        self._provider_failures[provider] = count
        if count >= self.max_failures:
            self.circuit_breaker_status[provider] = True

    def record_success(self, provider: str) -> None:
        """Reset provider-level failure count and close circuit."""
        self._provider_failures[provider] = 0
        self.circuit_breaker_status[provider] = False

    def is_circuit_open(self, provider: str) -> bool:
        """Return True if the provider-level circuit breaker is open."""
        return bool(self.circuit_breaker_status.get(provider, False))


class IdPError(Exception):
    """Exception raised for identity provider errors, with classification metadata."""

    def __init__(
        self,
        provider: str,
        message: str,
        recovery_strategy: str = "reauth",
        request_id: str = "",
        user_message: str = "",
        retryable: bool = False,
    ):
        super().__init__(message)
        self.provider = provider
        self.recovery_strategy = recovery_strategy
        self.request_id = request_id
        self.user_message = user_message or message
        self.retryable = retryable


class IdPErrorHandler:
    """Classifies IdP errors and tracks per-provider circuit breaker state."""

    _STRATEGY_MAP = {
        "invalid_grant": "reauth",
        "invalid_token": "reauth",
        "access_denied": "reauth",
        "server_error": "retry",
        "temporarily_unavailable": "retry",
        "service_unavailable": "retry",
    }

    def __init__(self, max_retries: int = 3, retry_delay: int = 1):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        # provider -> {"failures": int, "opened_at": datetime | None}
        self.provider_circuit_breaker: Dict[str, dict] = {}
        self._circuit_threshold = 3
        self._circuit_reset_minutes = 5

    # ------------------------------------------------------------------
    # Error classification
    # ------------------------------------------------------------------

    def classify_error(
        self,
        provider: str,
        error_code: str,
        message: str,
        request_id: str = "",
    ) -> IdPError:
        """Return a classified IdPError with recovery strategy."""
        strategy = self._STRATEGY_MAP.get(error_code, "reauth")
        retryable = strategy == "retry"
        return IdPError(
            provider=provider,
            message=message,
            recovery_strategy=strategy,
            request_id=request_id,
            user_message=message,
            retryable=retryable,
        )

    # ------------------------------------------------------------------
    # Circuit breaker
    # ------------------------------------------------------------------

    def _ensure_provider(self, provider: str) -> None:
        if provider not in self.provider_circuit_breaker:
            self.provider_circuit_breaker[provider] = {"failures": 0, "opened_at": None}

    def record_provider_failure(self, provider: str) -> None:
        """Increment failure count; open circuit if threshold reached."""
        self._ensure_provider(provider)
        self.provider_circuit_breaker[provider]["failures"] += 1
        if self.provider_circuit_breaker[provider]["failures"] >= self._circuit_threshold:
            if self.provider_circuit_breaker[provider]["opened_at"] is None:
                self.provider_circuit_breaker[provider]["opened_at"] = datetime.now(timezone.utc)

    def record_provider_success(self, provider: str) -> None:
        """Reset failure count and close circuit on success."""
        self._ensure_provider(provider)
        self.provider_circuit_breaker[provider]["failures"] = 0
        self.provider_circuit_breaker[provider]["opened_at"] = None

    def is_provider_degraded(self, provider: str) -> bool:
        """Return True if the provider circuit is open (too many recent failures)."""
        self._ensure_provider(provider)
        state = self.provider_circuit_breaker[provider]
        if state["failures"] < self._circuit_threshold:
            return False
        opened_at = state.get("opened_at")
        if opened_at is None:
            return False
        elapsed = (datetime.now(timezone.utc) - opened_at).total_seconds() / 60
        if elapsed >= self._circuit_reset_minutes:
            # Auto-reset after timeout
            self.record_provider_success(provider)
            return False
        return True

    # ------------------------------------------------------------------
    # Legacy async error handler (kept for compatibility)
    # ------------------------------------------------------------------

    def handle_error(
        self,
        error_code: str,
        provider: str,
        message: str = "",
        context: Optional[dict] = None,
    ) -> dict:
        """Classify and log an IdP error synchronously.

        Returns a dict with ``strategy``, ``provider``, ``error_code``, and
        ``retryable`` keys.  Also records a provider failure for circuit-breaker
        tracking.
        """
        strategy = self._STRATEGY_MAP.get(error_code, "reauth")
        retryable = strategy == "retry"
        self.record_provider_failure(provider)
        result = {
            "strategy": strategy,
            "provider": provider,
            "error_code": error_code,
            "message": message,
            "retryable": retryable,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if context:
            result["context"] = context
        logger.error("IdP error from %s [%s]: %s", provider, error_code, message)
        return result

    async def handle_error_async(
        self,
        provider: str,
        error: Exception,
        context: Optional[dict] = None,
    ) -> dict:
        """Async variant for legacy callers that await handle_error."""
        return self.handle_error(
            error_code=type(error).__name__,
            provider=provider,
            message=str(error),
            context=context,
        )


class SessionMiddleware(BaseHTTPMiddleware):
    """ASGI middleware for session management.

    Public routes (matching _PUBLIC_PREFIXES) are allowed through without a
    session cookie.  All other routes require a valid session cookie; missing
    or invalid cookies result in a 401 response.
    """

    def __init__(
        self,
        app: ASGIApp,
        session_manager: SessionMiddlewareManager,
    ):
        super().__init__(app)
        self.session_manager = session_manager

    @staticmethod
    def _is_public(path: str) -> bool:
        return any(path.startswith(prefix) for prefix in _PUBLIC_PREFIXES)

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and enforce session requirement on protected routes."""
        path = request.url.path

        if self._is_public(path):
            return await call_next(request)

        session_id = request.cookies.get("session_id")
        if not session_id:
            return Response(status_code=401, content="Session required")

        token = self.session_manager.validate_session(session_id)
        if token is None:
            response = Response(status_code=401, content="Invalid or expired session")
            response.delete_cookie("session_id")
            return response

        request.state.session = token
        return await call_next(request)

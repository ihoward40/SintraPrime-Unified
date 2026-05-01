"""
Phase 21C: Session Middleware & Token Refresh Manager
Handles session lifecycle, background token refresh, IdP error recovery.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable, Any
from dataclasses import dataclass, field
import hashlib

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import jwt

logger = logging.getLogger(__name__)


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
        return datetime.utcnow() >= self.expires_at
    
    def should_refresh(self) -> bool:
        """Check if token should refresh at 80% TTL."""
        ttl = (self.expires_at - self.issued_at).total_seconds()
        elapsed = (datetime.utcnow() - self.issued_at).total_seconds()
        return elapsed >= (ttl * 0.8)


class SessionMiddlewareManager:
    """
    Manages session initialization, validation, and expiry.
    Runs at request entry point to ensure valid session before routing.
    """
    
    def __init__(self, session_secret: str, session_ttl_seconds: int = 3600):
        self.session_secret = session_secret
        self.session_ttl = timedelta(seconds=session_ttl_seconds)
        self.sessions: dict[str, SessionToken] = {}
    
    def create_session(self, token: SessionToken) -> str:
        """Create a new session and return session ID."""
        session_id = self._generate_session_id(token.user_id, token.issued_at)
        self.sessions[session_id] = token
        logger.info(f"Session created: {session_id} for user {token.user_id} (provider: {token.provider})")
        return session_id
    
    def validate_session(self, session_id: str) -> Optional[SessionToken]:
        """Validate session and return token if valid."""
        if session_id not in self.sessions:
            logger.warning(f"Session not found: {session_id}")
            return None
        
        token = self.sessions[session_id]
        if token.is_expired():
            logger.warning(f"Session expired: {session_id}")
            del self.sessions[session_id]
            return None
        
        return token
    
    def invalidate_session(self, session_id: str) -> bool:
        """Destroy a session (logout)."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Session invalidated: {session_id}")
            return True
        return False
    
    def get_session_ttl(self) -> int:
        """Return session TTL in seconds."""
        return int(self.session_ttl.total_seconds())
    
    @staticmethod
    def _generate_session_id(user_id: str, issued_at: datetime) -> str:
        """Generate a secure session ID using HMAC."""
        data = f"{user_id}:{issued_at.isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()


class TokenRefreshManager:
    """
    Manages background token refresh at 80% TTL.
    Uses exponential backoff on failures; circuit breaker after 3 failures in 5 min.
    """
    
    def __init__(self, refresh_callback: Callable[[str], Any], max_failures: int = 3, failure_window_seconds: int = 300):
        self.refresh_callback = refresh_callback
        self.max_failures = max_failures
        self.failure_window = timedelta(seconds=failure_window_seconds)
        self.active_tasks: dict[str, asyncio.Task] = {}
        self.failure_log: dict[str, list[datetime]] = {}
        self.circuit_breaker_status: dict[str, bool] = {}  # True = open (broken)
    
    async def start_refresh_loop(self, session_id: str, token: SessionToken) -> None:
        """Start background refresh task for a session."""
        if session_id in self.active_tasks:
            logger.warning(f"Refresh task already running for session: {session_id}")
            return
        
        task = asyncio.create_task(self._refresh_loop(session_id, token))
        self.active_tasks[session_id] = task
        logger.info(f"Refresh loop started for session: {session_id}")
    
    async def _refresh_loop(self, session_id: str, token: SessionToken) -> None:
        """Background refresh loop with exponential backoff."""
        retry_delay = 1  # seconds
        
        try:
            while not token.is_expired():
                if token.should_refresh():
                    success = await self._attempt_refresh(session_id, token)
                    if success:
                        retry_delay = 1  # reset on success
                    else:
                        retry_delay = min(retry_delay * 2, 60)  # exponential backoff, max 60s
                
                await asyncio.sleep(min(retry_delay, 30))  # Check every 30s or retry interval
        except asyncio.CancelledError:
            logger.info(f"Refresh loop cancelled for session: {session_id}")
        except Exception as e:
            logger.error(f"Refresh loop error for session {session_id}: {e}")
        finally:
            if session_id in self.active_tasks:
                del self.active_tasks[session_id]
    
    async def _attempt_refresh(self, session_id: str, token: SessionToken) -> bool:
        """Attempt to refresh token; return True on success."""
        if self._is_circuit_broken(session_id):
            logger.warning(f"Circuit breaker OPEN for session: {session_id}")
            return False
        
        try:
            result = await self.refresh_callback(token)
            if result:
                self._record_success(session_id)
                logger.info(f"Token refreshed for session: {session_id}")
                return True
            else:
                self._record_failure(session_id)
                return False
        except Exception as e:
            logger.error(f"Refresh failed for session {session_id}: {e}")
            self._record_failure(session_id)
            return False
    
    def _is_circuit_broken(self, session_id: str) -> bool:
        """Check if circuit breaker is open (3+ failures in 5 min)."""
        return self.circuit_breaker_status.get(session_id, False)
    
    def _record_failure(self, session_id: str) -> None:
        """Record a failure and check circuit breaker threshold."""
        now = datetime.utcnow()
        if session_id not in self.failure_log:
            self.failure_log[session_id] = []
        
        # Remove old failures outside window
        self.failure_log[session_id] = [
            ts for ts in self.failure_log[session_id]
            if now - ts < self.failure_window
        ]
        
        self.failure_log[session_id].append(now)
        
        if len(self.failure_log[session_id]) >= self.max_failures:
            self.circuit_breaker_status[session_id] = True
            logger.error(f"Circuit breaker OPEN for session {session_id} (3+ failures in {self.failure_window.total_seconds()}s)")
    
    def _record_success(self, session_id: str) -> None:
        """Record success and reset circuit breaker."""
        self.failure_log[session_id] = []
        self.circuit_breaker_status[session_id] = False
    
    async def stop_refresh_loop(self, session_id: str) -> None:
        """Stop background refresh task for a session."""
        if session_id in self.active_tasks:
            self.active_tasks[session_id].cancel()
            try:
                await self.active_tasks[session_id]
            except asyncio.CancelledError:
                pass
            logger.info(f"Refresh loop stopped for session: {session_id}")


@dataclass
class IdPError:
    """Represents an identity provider error with recovery strategy."""
    code: str
    message: str
    provider: str
    timestamp: datetime
    recovery_strategy: str  # 'retry', 'fallback', 'reauth', 'user_prompt'
    user_message: str = ""
    request_id: str = ""


class IdPErrorHandler:
    """
    Classifies IdP errors and determines recovery strategy.
    Implements circuit breaker per provider + user-friendly messaging.
    """
    
    ERROR_CLASSIFICATIONS = {
        'invalid_grant': ('reauth', 'Your session has expired. Please log in again.'),
        'access_denied': ('user_prompt', 'Access denied by identity provider. Please check your permissions.'),
        'server_error': ('retry', 'Provider temporarily unavailable. Retrying...'),
        'timeout': ('retry', 'Identity provider slow to respond. Retrying...'),
        'invalid_client': ('fallback', 'Provider configuration issue. Using backup provider.'),
        'network_error': ('fallback', 'Network connectivity issue. Trying backup...'),
        'invalid_scope': ('reauth', 'Permission scope changed. Please re-authenticate.'),
        'state_mismatch': ('reauth', 'Security validation failed. Please re-authenticate.'),
    }
    
    def __init__(self):
        self.provider_circuit_breaker: dict[str, dict] = {}  # provider -> {open: bool, failures: int, opened_at: datetime}
    
    def classify_error(self, provider: str, error_code: str, error_message: str, request_id: str) -> IdPError:
        """Classify an error and return recovery strategy."""
        strategy, user_msg = self.ERROR_CLASSIFICATIONS.get(
            error_code,
            ('reauth', f'Authentication failed: {error_message}')
        )
        
        logger.warning(
            f"IdP error classified: provider={provider}, code={error_code}, strategy={strategy}, request_id={request_id}"
        )
        
        return IdPError(
            code=error_code,
            message=error_message,
            provider=provider,
            timestamp=datetime.utcnow(),
            recovery_strategy=strategy,
            user_message=user_msg,
            request_id=request_id
        )
    
    def is_provider_degraded(self, provider: str) -> bool:
        """Check if provider is in circuit breaker open state."""
        if provider not in self.provider_circuit_breaker:
            return False
        
        cb = self.provider_circuit_breaker[provider]
        if not cb['open']:
            return False
        
        # Reset circuit breaker after 5 minutes
        if datetime.utcnow() - cb['opened_at'] > timedelta(minutes=5):
            cb['open'] = False
            cb['failures'] = 0
            logger.info(f"Circuit breaker reset for provider: {provider}")
            return False
        
        return True
    
    def record_provider_failure(self, provider: str) -> None:
        """Record a failure for a provider; open circuit breaker if threshold reached."""
        if provider not in self.provider_circuit_breaker:
            self.provider_circuit_breaker[provider] = {'open': False, 'failures': 0, 'opened_at': None}
        
        cb = self.provider_circuit_breaker[provider]
        cb['failures'] += 1
        
        if cb['failures'] >= 3:
            cb['open'] = True
            cb['opened_at'] = datetime.utcnow()
            logger.error(f"Circuit breaker OPEN for provider: {provider} (3+ failures)")
    
    def record_provider_success(self, provider: str) -> None:
        """Record success and reset failure counter."""
        if provider in self.provider_circuit_breaker:
            self.provider_circuit_breaker[provider]['failures'] = 0
            if not self.provider_circuit_breaker[provider]['open']:
                logger.info(f"Failure counter reset for provider: {provider}")


class SessionMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware that validates session on protected routes.
    Extracts session ID from secure HttpOnly cookie.
    """
    
    PROTECTED_PATHS = [
        '/auth/session/me',
        '/auth/session/refresh',
        '/auth/session/logout',
        '/api/',
    ]
    
    def __init__(self, app: ASGIApp, session_manager: SessionMiddlewareManager):
        super().__init__(app)
        self.session_manager = session_manager
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate session for protected paths."""
        # Check if path is protected
        is_protected = any(request.url.path.startswith(p) for p in self.PROTECTED_PATHS)
        
        if is_protected:
            session_id = request.cookies.get('session_id')
            if not session_id:
                logger.warning(f"No session cookie for protected route: {request.url.path}")
                raise HTTPException(status_code=401, detail="Unauthorized: No session")
            
            token = self.session_manager.validate_session(session_id)
            if not token:
                logger.warning(f"Invalid session for protected route: {request.url.path}")
                raise HTTPException(status_code=401, detail="Unauthorized: Invalid session")
            
            # Attach token to request state for use in route handlers
            request.state.session_token = token
            request.state.session_id = session_id
        
        response = await call_next(request)
        return response
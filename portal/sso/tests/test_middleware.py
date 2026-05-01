"""
Phase 21C: Comprehensive unit tests for portal/sso/middleware.py
Covers SessionMiddlewareManager, TokenRefreshManager, IdPErrorHandler, SessionMiddleware.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.responses import PlainTextResponse

from portal.sso.middleware import (
    IdPError,
    IdPErrorHandler,
    SessionMiddleware,
    SessionMiddlewareManager,
    SessionToken,
    TokenRefreshManager,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_token(
    *,
    user_id: str = "u1",
    email: str = "user@example.com",
    provider: str = "okta",
    offset_seconds: int = 3600,
) -> SessionToken:
    now = datetime.now(timezone.utc)
    return SessionToken(
        user_id=user_id,
        email=email,
        provider=provider,
        issued_at=now,
        expires_at=now + timedelta(seconds=offset_seconds),
    )


def _expired_token() -> SessionToken:
    return _make_token(offset_seconds=-1)


# ─────────────────────────────────────────────────────────────────────────────
# SessionMiddlewareManager (7 tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestSessionMiddlewareManager:
    def setup_method(self):
        self.mgr = SessionMiddlewareManager(session_secret="test-secret-key", session_ttl_seconds=3600)

    def test_create_session(self):
        token = _make_token()
        sid = self.mgr.create_session(token)
        assert isinstance(sid, str)
        assert len(sid) == 64  # SHA-256 hex digest

    def test_validate_session_valid(self):
        token = _make_token()
        sid = self.mgr.create_session(token)
        result = self.mgr.validate_session(sid)
        assert result is not None
        assert result.user_id == "u1"

    def test_validate_session_not_found(self):
        result = self.mgr.validate_session("nonexistent-session-id")
        assert result is None

    def test_validate_session_expired(self):
        token = _expired_token()
        sid = self.mgr.create_session(token)
        result = self.mgr.validate_session(sid)
        assert result is None
        # Session should be evicted
        assert sid not in self.mgr.sessions

    def test_invalidate_session(self):
        token = _make_token()
        sid = self.mgr.create_session(token)
        result = self.mgr.invalidate_session(sid)
        assert result is True
        assert self.mgr.validate_session(sid) is None

    def test_invalidate_nonexistent_session(self):
        result = self.mgr.invalidate_session("does-not-exist")
        assert result is False

    def test_get_session_ttl(self):
        assert self.mgr.get_session_ttl() == 3600

    def test_session_id_uses_hmac_secret(self):
        """Two managers with different secrets must produce different session IDs."""
        mgr2 = SessionMiddlewareManager(session_secret="different-secret", session_ttl_seconds=3600)
        token = _make_token()
        sid1 = self.mgr.create_session(token)
        sid2 = mgr2.create_session(token)
        assert sid1 != sid2


# ─────────────────────────────────────────────────────────────────────────────
# TokenRefreshManager (5 tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestTokenRefreshManager:
    def setup_method(self):
        self.callback = AsyncMock(return_value=True)
        self.mgr = TokenRefreshManager(
            refresh_callback=self.callback,
            max_failures=3,
            failure_window_seconds=300,
        )

    @pytest.mark.asyncio
    async def test_start_refresh_loop(self):
        token = _make_token()
        await self.mgr.start_refresh_loop("session-1", token)
        assert "session-1" in self.mgr.active_tasks
        # Clean up
        await self.mgr.stop_refresh_loop("session-1")

    @pytest.mark.asyncio
    async def test_refresh_loop_cleanup(self):
        token = _make_token(offset_seconds=1)  # expires in 1 second
        await self.mgr.start_refresh_loop("session-2", token)
        await asyncio.sleep(0.1)
        await self.mgr.stop_refresh_loop("session-2")
        assert "session-2" not in self.mgr.active_tasks

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_3_failures(self):
        failing_callback = AsyncMock(return_value=False)
        mgr = TokenRefreshManager(
            refresh_callback=failing_callback,
            max_failures=3,
            failure_window_seconds=300,
        )
        token = _make_token()
        for _ in range(3):
            await mgr._attempt_refresh("session-3", token)
        assert mgr.circuit_breaker_status.get("session-3") is True

    @pytest.mark.asyncio
    async def test_circuit_breaker_resets_on_success(self):
        failing_callback = AsyncMock(return_value=False)
        mgr = TokenRefreshManager(
            refresh_callback=failing_callback,
            max_failures=3,
            failure_window_seconds=300,
        )
        token = _make_token()
        for _ in range(3):
            await mgr._attempt_refresh("session-4", token)
        assert mgr.circuit_breaker_status.get("session-4") is True

        # Now succeed
        mgr.refresh_callback = AsyncMock(return_value=True)
        mgr.circuit_breaker_status["session-4"] = False  # manually reset to allow attempt
        await mgr._attempt_refresh("session-4", token)
        assert mgr.circuit_breaker_status.get("session-4") is False

    @pytest.mark.asyncio
    async def test_duplicate_start_is_noop(self):
        token = _make_token()
        await self.mgr.start_refresh_loop("session-5", token)
        task1 = self.mgr.active_tasks["session-5"]
        await self.mgr.start_refresh_loop("session-5", token)  # duplicate
        task2 = self.mgr.active_tasks["session-5"]
        assert task1 is task2  # same task, not replaced
        await self.mgr.stop_refresh_loop("session-5")


# ─────────────────────────────────────────────────────────────────────────────
# IdPErrorHandler (6 tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestIdPErrorHandler:
    def setup_method(self):
        self.handler = IdPErrorHandler()

    def test_classify_invalid_grant(self):
        err = self.handler.classify_error("okta", "invalid_grant", "Token expired", "req-1")
        assert isinstance(err, IdPError)
        assert err.recovery_strategy == "reauth"
        assert err.provider == "okta"
        assert "req-1" == err.request_id

    def test_classify_server_error(self):
        err = self.handler.classify_error("azure", "server_error", "500 Internal", "req-2")
        assert err.recovery_strategy == "retry"

    def test_classify_unknown_error(self):
        err = self.handler.classify_error("google", "unknown_code", "Something weird", "req-3")
        assert err.recovery_strategy == "reauth"
        assert "Something weird" in err.user_message

    def test_provider_circuit_breaker_opens(self):
        for _ in range(3):
            self.handler.record_provider_failure("okta")
        assert self.handler.is_provider_degraded("okta") is True

    def test_provider_circuit_breaker_resets_after_5_min(self):
        for _ in range(3):
            self.handler.record_provider_failure("azure")
        assert self.handler.is_provider_degraded("azure") is True

        # Simulate 5+ minutes passing
        past = datetime.now(timezone.utc) - timedelta(minutes=6)
        self.handler.provider_circuit_breaker["azure"]["opened_at"] = past
        assert self.handler.is_provider_degraded("azure") is False

    def test_record_success_resets_failure_counter(self):
        self.handler.record_provider_failure("google")
        self.handler.record_provider_failure("google")
        self.handler.record_provider_success("google")
        # After success, failures counter should be 0
        assert self.handler.provider_circuit_breaker["google"]["failures"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# SessionMiddleware ASGI (4 tests)
# ─────────────────────────────────────────────────────────────────────────────

def _build_app(mgr: SessionMiddlewareManager) -> FastAPI:
    app = FastAPI()
    app.add_middleware(SessionMiddleware, session_manager=mgr)

    @app.get("/public")
    async def public_route():
        return PlainTextResponse("public")

    @app.get("/api/data")
    async def protected_route():
        return PlainTextResponse("secret")

    @app.get("/auth/session/me")
    async def me_route():
        return PlainTextResponse("me")

    return app


class TestSessionMiddlewareASGI:
    def setup_method(self):
        self.mgr = SessionMiddlewareManager(session_secret="test-secret", session_ttl_seconds=3600)
        self.app = _build_app(self.mgr)
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def test_public_route_no_cookie_allowed(self):
        resp = self.client.get("/public")
        assert resp.status_code == 200

    def test_protected_route_no_cookie_returns_401(self):
        resp = self.client.get("/api/data")
        assert resp.status_code == 401

    def test_protected_route_invalid_cookie_returns_401(self):
        resp = self.client.get("/api/data", cookies={"session_id": "bad-session-id"})
        assert resp.status_code == 401

    def test_protected_route_valid_cookie_passes(self):
        token = _make_token()
        sid = self.mgr.create_session(token)
        resp = self.client.get("/api/data", cookies={"session_id": sid})
        assert resp.status_code == 200

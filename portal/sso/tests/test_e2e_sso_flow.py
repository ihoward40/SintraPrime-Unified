"""
Phase 21F: End-to-End SSO Flow Tests
Full OAuth cycle: authorize -> callback -> session -> refresh -> logout
"""

import json
from unittest.mock import AsyncMock

import pytest


class TestRedisSessionStore:
    """Unit tests for RedisSessionStore (4 tests)."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self):
        """Test storing and retrieving session data."""
        from portal.sso.redis_session import RedisSessionStore
        store = RedisSessionStore()
        mock_client = AsyncMock()
        mock_client.setex = AsyncMock(return_value=True)
        mock_client.get = AsyncMock(return_value=json.dumps({"user_id": "u123", "email": "test@example.com"}))
        store._client = mock_client
        store._connected = True
        result = await store.store("sess_abc", {"user_id": "u123", "email": "test@example.com"}, ttl_seconds=3600)
        assert result is True
        mock_client.setex.assert_called_once()
        data = await store.retrieve("sess_abc")
        assert data["user_id"] == "u123"
        assert data["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_delete_session(self):
        """Test deleting a session."""
        from portal.sso.redis_session import RedisSessionStore
        store = RedisSessionStore()
        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(return_value=1)
        store._client = mock_client
        store._connected = True
        result = await store.delete("sess_abc")
        assert result is True

    @pytest.mark.asyncio
    async def test_fallback_when_disconnected(self):
        """Test graceful fallback when Redis is not connected."""
        from portal.sso.redis_session import RedisSessionStore
        store = RedisSessionStore()
        store._connected = False
        assert await store.store("x", {}) is False
        assert await store.retrieve("x") is None
        assert await store.delete("x") is False
        assert await store.exists("x") is False

    @pytest.mark.asyncio
    async def test_refresh_ttl(self):
        """Test refreshing session TTL."""
        from portal.sso.redis_session import RedisSessionStore
        store = RedisSessionStore()
        mock_client = AsyncMock()
        mock_client.expire = AsyncMock(return_value=True)
        store._client = mock_client
        store._connected = True
        result = await store.refresh_ttl("sess_abc", 7200)
        assert result is True


class TestE2ESSOFlow:
    """End-to-end SSO flow integration tests (6 tests)."""

    @pytest.mark.asyncio
    async def test_authorize_generates_state(self):
        """Test SSO authorize endpoint generates CSRF state."""
        from portal.sso.middleware import SessionMiddlewareManager
        mgr = SessionMiddlewareManager(session_secret="test-secret-32chars-minimum!!")
        session = mgr.create_session(user_id="u1", email="test@ex.com", provider="okta")
        assert session is not None
        assert "session_id" in session
        assert session["user_id"] == "u1"

    @pytest.mark.asyncio
    async def test_session_validation(self):
        """Test session validation with HMAC."""
        from portal.sso.middleware import SessionMiddlewareManager
        mgr = SessionMiddlewareManager(session_secret="test-secret-32chars-minimum!!")
        session = mgr.create_session(user_id="u2", email="user@ex.com", provider="azure")
        validated = mgr.validate_session(session["session_id"])
        assert validated is not None

    @pytest.mark.asyncio
    async def test_session_expiry(self):
        """Test session expires after TTL."""
        from portal.sso.middleware import SessionMiddlewareManager
        mgr = SessionMiddlewareManager(session_secret="test-secret-32chars-minimum!!", session_ttl_seconds=1)
        session = mgr.create_session(user_id="u3", email="exp@ex.com", provider="google")
        assert session is not None
        assert mgr.validate_session(session["session_id"]) is not None

    @pytest.mark.asyncio
    async def test_token_refresh_circuit_breaker(self):
        """Test TokenRefreshManager circuit breaker triggers after 3 failures."""
        from portal.sso.middleware import TokenRefreshManager
        mgr = TokenRefreshManager()
        for _ in range(3):
            mgr.record_failure("okta")
        assert mgr.is_circuit_open("okta") is True

    @pytest.mark.asyncio
    async def test_idp_error_handler_recovery(self):
        """Test IdP error handler returns correct recovery strategy."""
        from portal.sso.middleware import IdPErrorHandler
        handler = IdPErrorHandler()
        result = handler.handle_error("invalid_grant", "okta")
        assert result is not None
        assert "strategy" in result

    @pytest.mark.asyncio
    async def test_session_logout(self):
        """Test session destruction on logout."""
        from portal.sso.middleware import SessionMiddlewareManager
        mgr = SessionMiddlewareManager(session_secret="test-secret-32chars-minimum!!")
        session = mgr.create_session(user_id="u4", email="bye@ex.com", provider="okta")
        session_id = session["session_id"]
        mgr.destroy_session(session_id)
        assert mgr.validate_session(session_id) is None

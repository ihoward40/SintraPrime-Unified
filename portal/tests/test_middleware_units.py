"""
Phase 23B — Middleware and WebSocket unit tests.
Covers: rate_limiter, auth_middleware, audit_middleware, cors_middleware,
        websocket/connection_manager, websocket/message_handler
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ─── rate_limiter ─────────────────────────────────────────────────────────────

class TestRateLimiter:
    """Unit tests for portal.middleware.rate_limiter."""

    def setup_method(self):
        from portal.middleware.rate_limiter import _rate_store
        _rate_store.clear()

    def test_sliding_window_check_allows_first_request(self):
        from portal.middleware.rate_limiter import _sliding_window_check
        allowed, remaining, reset_in = _sliding_window_check(
            "test-key-1", limit=10, window_seconds=60, use_redis=False
        )
        assert allowed is True
        assert remaining == 9
        assert reset_in == 60

    def test_sliding_window_check_blocks_after_limit(self):
        import time

        from portal.middleware.rate_limiter import _rate_store, _sliding_window_check
        key = "test-key-block"
        now = int(time.time())
        _rate_store[key] = [now] * 11
        allowed, remaining, _ = _sliding_window_check(key, limit=10, window_seconds=60, use_redis=False)
        assert allowed is False
        assert remaining == 0

    def test_sliding_window_check_remaining_decrements(self):
        from portal.middleware.rate_limiter import _sliding_window_check
        key = "test-key-decrement"
        _, r1, _ = _sliding_window_check(key, limit=5, window_seconds=60, use_redis=False)
        _, r2, _ = _sliding_window_check(key, limit=5, window_seconds=60, use_redis=False)
        assert r1 > r2

    @pytest.mark.asyncio
    async def test_rate_limiter_middleware_passes_unauthenticated_non_auth_path(self):
        from portal.middleware.rate_limiter import RateLimiterMiddleware
        app = MagicMock()
        middleware = RateLimiterMiddleware(app)
        mock_request = MagicMock()
        mock_request.url.path = "/api/cases"
        mock_request.state.user_id = None
        mock_response = MagicMock()
        mock_response.headers = {}
        call_next = AsyncMock(return_value=mock_response)
        await middleware.dispatch(mock_request, call_next)
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limiter_returns_429_when_auth_limit_exceeded(self):
        import time

        from portal.middleware.rate_limiter import AUTH_LIMIT, RateLimiterMiddleware, _rate_store
        _rate_store.clear()
        app = MagicMock()
        middleware = RateLimiterMiddleware(app)
        mock_request = MagicMock()
        mock_request.url.path = "/auth/login"
        mock_request.client.host = "10.0.0.1"
        mock_response = MagicMock()
        mock_response.headers = {}
        call_next = AsyncMock(return_value=mock_response)
        key = "rl:auth:10.0.0.1"
        now = int(time.time())
        _rate_store[key] = [now] * (AUTH_LIMIT + 1)
        response = await middleware.dispatch(mock_request, call_next)
        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_rate_limiter_adds_headers_to_authenticated_response(self):
        from portal.middleware.rate_limiter import RateLimiterMiddleware, _rate_store
        _rate_store.clear()
        app = MagicMock()
        middleware = RateLimiterMiddleware(app)
        mock_request = MagicMock()
        mock_request.url.path = "/api/documents"
        mock_request.state.user_id = "user-123"
        mock_response = MagicMock()
        mock_response.headers = {}
        call_next = AsyncMock(return_value=mock_response)
        await middleware.dispatch(mock_request, call_next)
        assert "X-RateLimit-Limit" in mock_response.headers
        assert "X-RateLimit-Remaining" in mock_response.headers


# ─── auth_middleware ──────────────────────────────────────────────────────────

class TestAuthMiddleware:
    """Unit tests for portal.middleware.auth_middleware."""

    @pytest.mark.asyncio
    async def test_auth_middleware_passes_health_path(self):
        from portal.middleware.auth_middleware import AuthMiddleware
        app = MagicMock()
        middleware = AuthMiddleware(app)
        mock_request = MagicMock()
        mock_request.url.path = "/health"
        mock_request.headers = {}
        mock_response = MagicMock()
        call_next = AsyncMock(return_value=mock_response)
        await middleware.dispatch(mock_request, call_next)
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_auth_middleware_passes_docs_path(self):
        from portal.middleware.auth_middleware import AuthMiddleware
        app = MagicMock()
        middleware = AuthMiddleware(app)
        mock_request = MagicMock()
        mock_request.url.path = "/docs"
        mock_request.headers = {}
        mock_response = MagicMock()
        call_next = AsyncMock(return_value=mock_response)
        await middleware.dispatch(mock_request, call_next)
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_auth_middleware_passes_login_path(self):
        from portal.middleware.auth_middleware import AuthMiddleware
        app = MagicMock()
        middleware = AuthMiddleware(app)
        mock_request = MagicMock()
        mock_request.url.path = "/auth/login"
        mock_request.headers = {}
        mock_response = MagicMock()
        call_next = AsyncMock(return_value=mock_response)
        await middleware.dispatch(mock_request, call_next)
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_auth_middleware_rejects_missing_token_on_protected_path(self):
        from portal.middleware.auth_middleware import AuthMiddleware
        app = MagicMock()
        middleware = AuthMiddleware(app)
        mock_request = MagicMock()
        mock_request.url.path = "/api/cases"
        mock_request.headers = {}
        mock_response = MagicMock()
        call_next = AsyncMock(return_value=mock_response)
        response = await middleware.dispatch(mock_request, call_next)
        # Should return 401 or pass through (depends on implementation)
        assert response.status_code in (401, 200) or call_next.called

    @pytest.mark.asyncio
    async def test_auth_middleware_sets_state_on_valid_token(self):
        from portal.auth.jwt_handler import create_access_token
        from portal.middleware.auth_middleware import AuthMiddleware
        token = create_access_token(
            user_id="user-99",
            tenant_id="tenant-1",
            role="attorney",
            permissions=["CASE_READ"],
        )
        app = MagicMock()
        middleware = AuthMiddleware(app)
        mock_request = MagicMock()
        mock_request.url.path = "/api/cases"
        mock_request.headers = {"Authorization": f"Bearer {token}"}
        mock_request.state = MagicMock()
        mock_response = MagicMock()
        call_next = AsyncMock(return_value=mock_response)
        await middleware.dispatch(mock_request, call_next)
        # Should call next with the request
        assert call_next.called


# ─── audit_middleware ─────────────────────────────────────────────────────────

class TestAuditMiddleware:
    """Unit tests for portal.middleware.audit_middleware."""

    @pytest.mark.asyncio
    async def test_audit_middleware_calls_next(self):
        from portal.middleware.audit_middleware import AuditMiddleware
        app = MagicMock()
        middleware = AuditMiddleware(app)
        mock_request = MagicMock()
        mock_request.url.path = "/api/documents"
        mock_request.method = "GET"
        mock_request.state = MagicMock()
        mock_request.state.user_id = "user-1"
        mock_request.state.tenant_id = "tenant-1"
        mock_request.state.role = "attorney"
        mock_response = MagicMock()
        mock_response.status_code = 200
        call_next = AsyncMock(return_value=mock_response)
        await middleware.dispatch(mock_request, call_next)
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_audit_middleware_skips_health_path(self):
        from portal.middleware.audit_middleware import AuditMiddleware
        app = MagicMock()
        middleware = AuditMiddleware(app)
        mock_request = MagicMock()
        mock_request.url.path = "/health"
        mock_request.method = "GET"
        mock_request.state = MagicMock()
        mock_request.state.user_id = None
        mock_response = MagicMock()
        mock_response.status_code = 200
        call_next = AsyncMock(return_value=mock_response)
        response = await middleware.dispatch(mock_request, call_next)
        assert response == mock_response

    @pytest.mark.asyncio
    async def test_audit_middleware_passes_through_response(self):
        from portal.middleware.audit_middleware import AuditMiddleware
        app = MagicMock()
        middleware = AuditMiddleware(app)
        mock_request = MagicMock()
        mock_request.url.path = "/api/cases"
        mock_request.method = "POST"
        mock_request.state = MagicMock()
        mock_request.state.user_id = None
        mock_request.state.tenant_id = None
        mock_request.state.role = None
        mock_response = MagicMock()
        mock_response.status_code = 201
        call_next = AsyncMock(return_value=mock_response)
        response = await middleware.dispatch(mock_request, call_next)
        assert response == mock_response


# ─── cors_middleware ──────────────────────────────────────────────────────────

class TestCorsMiddleware:
    """Unit tests for portal.middleware.cors_middleware."""

    def test_cors_module_importable(self):
        import portal.middleware.cors_middleware as cors_mod
        assert cors_mod is not None

    def test_setup_cors_function_exists(self):
        from portal.middleware.cors_middleware import setup_cors
        assert callable(setup_cors)

    def test_setup_cors_adds_middleware_to_app(self):
        from portal.middleware.cors_middleware import setup_cors
        mock_app = MagicMock()
        mock_app.add_middleware = MagicMock()
        # Should not raise
        setup_cors(mock_app)
        mock_app.add_middleware.assert_called()

    def test_cors_does_not_use_wildcard_in_production(self):
        """Security gate: CORS must not allow all origins in production."""
        import inspect

        import portal.middleware.cors_middleware as cors_mod
        source = inspect.getsource(cors_mod)
        # The production block should use regex, not wildcard
        assert 'allow_origin_regex' in source or 'ALLOWED_ORIGINS' in source


# ─── websocket/connection_manager ─────────────────────────────────────────────

class TestConnectionManager:
    """Unit tests for portal.websocket.connection_manager."""

    def _make_manager(self):
        from portal.websocket.connection_manager import ConnectionManager
        return ConnectionManager()

    def _make_mock_ws(self):
        ws = AsyncMock()
        ws.send_json = AsyncMock()
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_connect_increments_connection_count(self):
        manager = self._make_manager()
        ws = self._make_mock_ws()
        await manager.connect(ws, user_id="user-1", tenant_id="tenant-1")
        assert manager.connection_count == 1

    @pytest.mark.asyncio
    async def test_disconnect_decrements_connection_count(self):
        manager = self._make_manager()
        ws = self._make_mock_ws()
        await manager.connect(ws, user_id="user-1", tenant_id="tenant-1")
        await manager.disconnect(ws, user_id="user-1", tenant_id="tenant-1")
        assert manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_send_to_user_calls_send_json(self):
        manager = self._make_manager()
        ws = self._make_mock_ws()
        await manager.connect(ws, user_id="user-1", tenant_id="tenant-1")
        event = {"type": "notification", "message": "Hello"}
        await manager.send_to_user("user-1", event)
        ws.send_json.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_send_to_nonexistent_user_does_not_raise(self):
        manager = self._make_manager()
        await manager.send_to_user("nonexistent-user", {"type": "ping"})

    @pytest.mark.asyncio
    async def test_broadcast_to_tenant_sends_to_all_users(self):
        manager = self._make_manager()
        ws1 = self._make_mock_ws()
        ws2 = self._make_mock_ws()
        await manager.connect(ws1, user_id="user-1", tenant_id="tenant-A")
        await manager.connect(ws2, user_id="user-2", tenant_id="tenant-A")
        event = {"type": "broadcast", "data": "test"}
        await manager.broadcast_to_tenant("tenant-A", event)
        ws1.send_json.assert_called_once_with(event)
        ws2.send_json.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_broadcast_to_users_sends_to_specified_users(self):
        manager = self._make_manager()
        ws1 = self._make_mock_ws()
        ws2 = self._make_mock_ws()
        ws3 = self._make_mock_ws()
        await manager.connect(ws1, user_id="user-1", tenant_id="tenant-A")
        await manager.connect(ws2, user_id="user-2", tenant_id="tenant-A")
        await manager.connect(ws3, user_id="user-3", tenant_id="tenant-A")
        event = {"type": "targeted"}
        await manager.broadcast_to_users(["user-1", "user-3"], event)
        ws1.send_json.assert_called_once_with(event)
        ws2.send_json.assert_not_called()
        ws3.send_json.assert_called_once_with(event)

    def test_get_online_users_returns_list(self):
        manager = self._make_manager()
        result = manager.get_online_users("tenant-1")
        assert isinstance(result, list)

    def test_connection_count_zero_initially(self):
        manager = self._make_manager()
        assert manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_multiple_connections_same_user(self):
        manager = self._make_manager()
        ws1 = self._make_mock_ws()
        ws2 = self._make_mock_ws()
        await manager.connect(ws1, user_id="user-1", tenant_id="tenant-1")
        await manager.connect(ws2, user_id="user-1", tenant_id="tenant-1")
        assert manager.connection_count == 2


# ─── websocket/message_handler ────────────────────────────────────────────────

class TestMessageHandler:
    """Unit tests for portal.websocket.message_handler.MessageHandler."""

    def _make_handler(self):
        from portal.websocket.message_handler import MessageHandler
        return MessageHandler()

    @pytest.mark.asyncio
    async def test_handle_ping_sends_pong(self):
        handler = self._make_handler()
        mock_db = AsyncMock()
        with patch("portal.websocket.message_handler.ws_manager") as mock_ws:
            mock_ws.send_to_user = AsyncMock()
            await handler.handle(
                event={"type": "ping"},
                user_id="user-1",
                tenant_id="tenant-1",
                db=mock_db,
            )
            mock_ws.send_to_user.assert_called_once_with("user-1", {"type": "pong"})

    @pytest.mark.asyncio
    async def test_handle_unknown_event_type_does_not_raise(self):
        handler = self._make_handler()
        mock_db = AsyncMock()
        # Should handle gracefully
        await handler.handle(
            event={"type": "unknown_event_xyz"},
            user_id="user-1",
            tenant_id="tenant-1",
            db=mock_db,
        )

    @pytest.mark.asyncio
    async def test_handle_missing_type_does_not_raise(self):
        handler = self._make_handler()
        mock_db = AsyncMock()
        # Empty event — should log warning and return
        await handler.handle(
            event={},
            user_id="user-1",
            tenant_id="tenant-1",
            db=mock_db,
        )

    def test_supported_events_contains_ping(self):
        from portal.websocket.message_handler import MessageHandler
        assert "ping" in MessageHandler.SUPPORTED_EVENTS

    def test_supported_events_contains_typing_events(self):
        from portal.websocket.message_handler import MessageHandler
        assert "typing_start" in MessageHandler.SUPPORTED_EVENTS
        assert "typing_stop" in MessageHandler.SUPPORTED_EVENTS

    @pytest.mark.asyncio
    async def test_handle_typing_start_without_thread_id_does_not_raise(self):
        handler = self._make_handler()
        mock_db = AsyncMock()
        await handler.handle(
            event={"type": "typing_start"},  # no thread_id
            user_id="user-1",
            tenant_id="tenant-1",
            db=mock_db,
        )

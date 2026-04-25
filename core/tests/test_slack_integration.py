"""
Comprehensive Test Suite for Slack Integration

Tests OAuth flow, slash commands, event handling, permissions, rate limiting,
thread handling, and modal interactions.
"""

import asyncio
import json
import sqlite3
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from universe.integrations.slack_auth import SlackAuthManager
from universe.integrations.slack_bridge import SlackBot, RateLimiter, ConnectionPool
from universe.integrations.slack_handlers import (
    SlackHandlers,
    PermissionChecker,
    ThreadContext,
    create_handlers,
)
from universe.integrations.slack_ui_builder import SlackUIBuilder


class TestRateLimiter(unittest.TestCase):
    """Tests for rate limiting functionality."""

    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(capacity=10, refill_rate=1.0)
        self.assertEqual(limiter.capacity, 10)
        self.assertEqual(limiter.tokens, 10)

    def test_acquire_tokens(self):
        """Test token acquisition."""
        limiter = RateLimiter(capacity=5, refill_rate=1.0)
        self.assertTrue(limiter.acquire(3))
        self.assertEqual(limiter.tokens, 2)

    def test_rate_limit_exceeded(self):
        """Test rate limit enforcement."""
        limiter = RateLimiter(capacity=2, refill_rate=1.0)
        self.assertTrue(limiter.acquire(2))
        self.assertFalse(limiter.acquire(1))

    def test_token_refill(self):
        """Test token refill over time."""
        limiter = RateLimiter(capacity=10, refill_rate=10.0)
        limiter.acquire(8)  # Leave 2 tokens
        time.sleep(0.11)
        # Should have refilled approximately 1 token
        self.assertTrue(limiter.acquire(1))

    def test_wait_time_calculation(self):
        """Test wait time calculation."""
        limiter = RateLimiter(capacity=5, refill_rate=1.0)
        limiter.acquire(5)
        wait_time = limiter.wait_available(2)
        self.assertGreaterEqual(wait_time, 1.9)
        self.assertLess(wait_time, 2.1)


class TestSlackAuthManager(unittest.TestCase):
    """Tests for OAuth 2.0 authentication."""

    def setUp(self):
        """Set up test database."""
        # Use a unique db path for each test to ensure isolation
        import uuid
        self.db_path = f"file::memory:?cache=shared&id={uuid.uuid4()}"
        self.auth = SlackAuthManager(
            client_id="test_client_id",
            client_secret="test_client_secret",
            db_path=self.db_path,
        )

    def test_oauth_url_generation(self):
        """Test OAuth URL generation."""
        url, state = self.auth.generate_oauth_url("https://example.com/callback")

        self.assertIn("slack.com", url)
        self.assertIn("test_client_id", url)
        self.assertIn("state=", url)
        self.assertTrue(len(state) > 20)

    def test_state_validation(self):
        """Test OAuth state validation."""
        url, state = self.auth.generate_oauth_url("https://example.com/callback")

        self.assertTrue(self.auth.validate_state(state))
        self.assertFalse(self.auth.validate_state("invalid_state"))

    def test_state_expiration(self):
        """Test state token expiration."""
        url, state = self.auth.generate_oauth_url("https://example.com/callback")

        # Manually expire the state
        self.auth._oauth_states[state]["created_at"] = time.time() - 700

        self.assertFalse(self.auth.validate_state(state, max_age=600))

    def test_team_credentials_storage(self):
        """Test saving and retrieving team credentials."""
        self.auth.save_team_credentials(
            team_id="T12345678",
            team_name="Test Team",
            bot_token="xoxb-123456",
            access_token="xoxp-123456",
        )

        creds = self.auth.get_team_credentials("T12345678")
        self.assertIsNotNone(creds)
        self.assertEqual(creds["team_id"], "T12345678")
        self.assertEqual(creds["team_name"], "Test Team")

    def test_get_all_teams(self):
        """Test retrieving all teams."""
        self.auth.save_team_credentials(
            "T11111111", "Team 1", "bot1", "user1"
        )
        self.auth.save_team_credentials(
            "T22222222", "Team 2", "bot2", "user2"
        )

        teams = self.auth.get_all_teams()
        self.assertEqual(len(teams), 2)

    def test_revoke_team(self):
        """Test revoking team credentials."""
        self.auth.save_team_credentials(
            "T12345678", "Test Team", "bot_token", "access_token"
        )

        self.assertTrue(self.auth.revoke_team("T12345678"))
        self.assertIsNone(self.auth.get_team_credentials("T12345678"))

    def test_request_signature_verification(self):
        """Test request signature verification."""
        import hashlib
        import hmac

        timestamp = str(int(time.time()))
        body = "test_body"
        basestring = f"v0:{timestamp}:{body}"
        signature = (
            "v0="
            + hmac.new(
                "test_client_secret".encode(),
                basestring.encode(),
                hashlib.sha256,
            ).hexdigest()
        )

        is_valid = self.auth.verify_request_signature(timestamp, body, signature)
        self.assertTrue(is_valid)

    def test_invalid_request_signature(self):
        """Test invalid request signature rejection."""
        timestamp = str(int(time.time()))
        body = "test_body"
        invalid_signature = "v0=invalid"

        is_valid = self.auth.verify_request_signature(timestamp, body, invalid_signature)
        self.assertFalse(is_valid)


class TestSlackUIBuilder(unittest.TestCase):
    """Tests for UI building functionality."""

    def test_create_button(self):
        """Test button creation."""
        button = SlackUIBuilder.create_button(
            "Click Me", "button_action", value="test_value", style="primary"
        )

        self.assertEqual(button["type"], "button")
        self.assertEqual(button["action_id"], "button_action")
        self.assertEqual(button["value"], "test_value")
        self.assertEqual(button["style"], "primary")

    def test_create_section_block(self):
        """Test section block creation."""
        section = SlackUIBuilder.create_section_block("Test Section", markdown=True)

        self.assertEqual(section["type"], "section")
        self.assertEqual(section["text"]["type"], "mrkdwn")
        self.assertEqual(section["text"]["text"], "Test Section")

    def test_create_header_block(self):
        """Test header block creation."""
        header = SlackUIBuilder.create_header_block("Test Header")

        self.assertEqual(header["type"], "header")
        self.assertIn("Test Header", str(header))

    def test_create_status_message(self):
        """Test status message creation."""
        message = SlackUIBuilder.create_status_message(
            "Task", "running", "In progress..."
        )

        self.assertIn("blocks", message)
        self.assertGreater(len(message["blocks"]), 0)

    def test_create_task_result_message(self):
        """Test task result message creation."""
        message = SlackUIBuilder.create_task_result_message(
            "Test Task", True, result="Success!"
        )

        self.assertIn("blocks", message)
        self.assertIn("✅", str(message))

    def test_create_error_dialog(self):
        """Test error dialog creation."""
        dialog = SlackUIBuilder.create_error_dialog(
            "Error", "Something went wrong", "Details here"
        )

        self.assertEqual(dialog["type"], "modal")
        self.assertIn("❌", str(dialog))

    def test_validate_blocks(self):
        """Test block validation."""
        valid_blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": "Test"}},
            {"type": "divider"},
        ]

        self.assertTrue(SlackUIBuilder.validate_blocks(valid_blocks))

    def test_validate_invalid_blocks(self):
        """Test invalid block rejection."""
        invalid_blocks = [
            {"type": "invalid_type"},
        ]

        self.assertFalse(SlackUIBuilder.validate_blocks(invalid_blocks))


class TestSlackBotCore(unittest.IsolatedAsyncioTestCase):
    """Tests for SlackBot core functionality."""

    async def asyncSetUp(self):
        """Set up test bot."""
        self.bot = SlackBot(
            client_id="test_client",
            client_secret="test_secret",
            signing_secret="test_signing_secret",
            db_path=":memory:",
        )

    async def test_bot_initialization(self):
        """Test bot initialization."""
        self.assertEqual(self.bot.client_id, "test_client")
        self.assertFalse(self.bot.running)

    async def test_register_slash_handler(self):
        """Test slash command handler registration."""
        async def test_handler(**kwargs):
            return {"text": "test"}

        self.bot.register_slash_handler("test", test_handler)
        self.assertIn("test", self.bot.slash_handlers)

    async def test_register_event_handler(self):
        """Test event handler registration."""
        async def test_handler(event_data):
            pass

        self.bot.register_event_handler("message", test_handler)
        self.assertIn("message", self.bot.event_handlers)

    async def test_handle_slash_command(self):
        """Test slash command handling."""
        async def test_handler(**kwargs):
            return {"text": "Command executed"}

        self.bot.register_slash_handler("test", test_handler)

        result = await self.bot.handle_slash_command(
            team_id="T12345",
            command="test",
            user_id="U12345",
            text="test args",
            channel_id="C12345",
        )

        self.assertIsNotNone(result)
        self.assertIn("text", result)

    async def test_unknown_command(self):
        """Test handling of unknown command."""
        result = await self.bot.handle_slash_command(
            team_id="T12345",
            command="unknown",
            user_id="U12345",
            text="args",
            channel_id="C12345",
        )

        self.assertIn("Unknown command", result.get("text", ""))

    async def test_emit_event(self):
        """Test event emission."""
        event_data = {"type": "message", "text": "test"}
        await self.bot.emit_event(event_data)

        self.assertEqual(self.bot.event_queue.qsize(), 1)

    async def test_get_stats(self):
        """Test stats retrieval."""
        stats = self.bot.get_stats()

        self.assertIn("running", stats)
        self.assertIn("active_connections", stats)
        self.assertIn("handlers", stats)


class TestPermissionChecker(unittest.TestCase):
    """Tests for permission checking."""

    def setUp(self):
        """Set up test permission checker."""
        # Use a unique db path for each test to ensure isolation
        import uuid
        self.db_path = f"file::memory:?cache=shared&id={uuid.uuid4()}"
        self.checker = PermissionChecker(db_path=self.db_path)

    def test_default_user_role(self):
        """Test default user role."""
        role = self.checker.get_user_role("T12345", "U12345")
        self.assertEqual(role, "user")

    def test_set_user_role(self):
        """Test setting user role."""
        self.checker.set_user_role("T12345", "U12345", "Test User", "admin")
        role = self.checker.get_user_role("T12345", "U12345")
        self.assertEqual(role, "admin")

    def test_admin_permissions(self):
        """Test admin permissions."""
        self.checker.set_user_role("T12345", "U12345", "Admin", "admin")

        self.assertTrue(
            self.checker.check_permission("T12345", "U12345", "invoke_agent")
        )
        self.assertTrue(
            self.checker.check_permission("T12345", "U12345", "manage_swarm")
        )
        self.assertTrue(
            self.checker.check_permission("T12345", "U12345", "install_skill")
        )

    def test_user_permissions(self):
        """Test user permissions."""
        self.checker.set_user_role("T12345", "U12345", "User", "user")

        self.assertTrue(
            self.checker.check_permission("T12345", "U12345", "invoke_agent")
        )
        self.assertFalse(
            self.checker.check_permission("T12345", "U12345", "manage_swarm")
        )


class TestThreadContext(unittest.TestCase):
    """Tests for thread context preservation."""

    def test_get_thread_ts_from_payload(self):
        """Test getting thread timestamp."""
        payload = {"thread_ts": "1234567890.123456"}
        ts = ThreadContext.get_thread_ts(payload)
        self.assertEqual(ts, "1234567890.123456")

    def test_preserve_thread_in_response(self):
        """Test preserving thread in response."""
        payload = {"thread_ts": "1234567890.123456"}
        response = {"text": "Response"}

        response = ThreadContext.preserve_thread(payload, response)
        self.assertEqual(response["thread_ts"], "1234567890.123456")

    def test_no_thread_preservation(self):
        """Test response without thread."""
        payload = {}
        response = {"text": "Response"}

        response = ThreadContext.preserve_thread(payload, response)
        self.assertNotIn("thread_ts", response)


class TestSlackHandlers(unittest.IsolatedAsyncioTestCase):
    """Tests for slash command and event handlers."""

    async def asyncSetUp(self):
        """Set up test handlers."""
        self.bot = SlackBot(
            client_id="test_client",
            client_secret="test_secret",
            signing_secret="test_signing_secret",
            db_path=":memory:",
        )
        self.handlers = SlackHandlers(self.bot, db_path=":memory:")

    async def test_agent_command(self):
        """Test /agent command."""
        result = await self.handlers.handle_agent_command(
            team_id="T12345",
            user_id="U12345",
            text="task_name query text",
            channel_id="C12345",
        )

        self.assertIsNotNone(result)
        self.assertIn("response_type", result)

    async def test_agent_command_insufficient_args(self):
        """Test /agent command with insufficient arguments."""
        result = await self.handlers.handle_agent_command(
            team_id="T12345",
            user_id="U12345",
            text="only_one_arg",
            channel_id="C12345",
        )

        self.assertIn("Usage", result.get("text", ""))

    async def test_swarm_command(self):
        """Test /swarm command."""
        result = await self.handlers.handle_swarm_command(
            team_id="T12345",
            user_id="U12345",
            text="team_name task_description",
            channel_id="C12345",
        )

        self.assertIsNotNone(result)

    async def test_skill_command_search(self):
        """Test /skill search command."""
        result = await self.handlers.handle_skill_command(
            team_id="T12345",
            user_id="U12345",
            text="search test_skill",
            channel_id="C12345",
        )

        self.assertIsNotNone(result)
        self.assertIn("blocks", result)

    async def test_skill_command_list(self):
        """Test /skill list command."""
        result = await self.handlers.handle_skill_command(
            team_id="T12345",
            user_id="U12345",
            text="list",
            channel_id="C12345",
        )

        self.assertIsNotNone(result)

    async def test_message_event_handling(self):
        """Test message event handling."""
        event_data = {
            "type": "message",
            "team_id": "T12345",
            "user_id": "U12345",
            "text": "test message",
            "channel": "C12345",
        }

        await self.handlers.handle_message_event(event_data)
        # Verify no exception raised

    async def test_app_mention_event_handling(self):
        """Test app mention event handling."""
        event_data = {
            "type": "app_mention",
            "team_id": "T12345",
            "user_id": "U12345",
            "text": "<@U_BOT> hello",
            "channel": "C12345",
        }

        await self.handlers.handle_app_mention_event(event_data)
        # Verify no exception raised

    async def test_button_action(self):
        """Test button action handling."""
        payload = {
            "user": {"id": "U12345"},
            "actions": [{"value": "test_value"}],
        }

        result = await self.handlers.handle_button_action("T12345", payload)
        self.assertIn("text", result)


class TestConnectionPool(unittest.IsolatedAsyncioTestCase):
    """Tests for connection pool."""

    async def test_get_connection(self):
        """Test getting connection from pool."""
        pool = ConnectionPool(max_size=5)
        conn = await pool.get_connection("T12345")

        self.assertIsNotNone(conn)
        self.assertEqual(conn["team_id"], "T12345")

    async def test_mark_unhealthy(self):
        """Test marking connection as unhealthy."""
        pool = ConnectionPool(max_size=5)
        await pool.get_connection("T12345")
        pool.mark_unhealthy("T12345")

        conn = pool.connections["T12345"]
        self.assertFalse(conn["healthy"])


if __name__ == "__main__":
    unittest.main()

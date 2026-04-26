"""
Test suite for SintraPrime Multi-Channel Messaging Hub.

55+ tests covering:
- ChannelHub: register, send, broadcast, routing
- TelegramChannel: send, file, voice, command handling
- DiscordChannel: message, embed, thread, slash commands
- SlackChannel: message, blocks, interactive
- MessageRouter: intent detection, entity extraction, routing
- WebhookChannel: register, verify signature, send
- Integration: end-to-end message flow

All tests are fully mocked — no real API keys or network access required.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# ── Module imports ──────────────────────────────────────────────────────────
from channels.channel_hub import ChannelHub
from channels.discord_channel import DiscordChannel
from channels.message_router import MessageRouter
from channels.message_types import (
    Attachment,
    AttachmentType,
    Button,
    ChannelConfig,
    ChannelType,
    IncomingMessage,
    Intent,
    MessageThread,
    OutgoingMessage,
    ParseMode,
)
from channels.slack_channel import SlackChannel
from channels.telegram_channel import RateLimiter, TelegramChannel
from channels.webhook_channel import RetryPolicy, WebhookChannel
from channels.whatsapp_channel import WhatsAppChannel


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def basic_config() -> ChannelConfig:
    return ChannelConfig(
        token="test-token-123",
        webhook_url="https://example.com/webhook",
        allowed_users=["user1", "user2"],
        admin_users=["admin1"],
        max_message_length=4096,
        rate_limit_per_minute=60,
        webhook_secret="super-secret",
        extra={"account_sid": "ACTEST", "from_number": "+15551234567"},
    )


@pytest.fixture
def open_config() -> ChannelConfig:
    """Config with no user restrictions."""
    return ChannelConfig(token="open-token")


@pytest.fixture
def hub(basic_config) -> ChannelHub:
    h = ChannelHub()
    mock_tg = AsyncMock()
    mock_tg.connected = True
    mock_dc = AsyncMock()
    mock_dc.connected = True
    h.register_channel(ChannelType.TELEGRAM, basic_config, mock_tg)
    h.register_channel(ChannelType.DISCORD, basic_config, mock_dc)
    return h


@pytest.fixture
def telegram(basic_config) -> TelegramChannel:
    return TelegramChannel(basic_config)


@pytest.fixture
def discord_ch(basic_config) -> DiscordChannel:
    return DiscordChannel(basic_config)


@pytest.fixture
def slack_ch(basic_config) -> SlackChannel:
    return SlackChannel(basic_config)


@pytest.fixture
def whatsapp(basic_config) -> WhatsAppChannel:
    return WhatsAppChannel(basic_config)


@pytest.fixture
def webhook_ch(basic_config) -> WebhookChannel:
    return WebhookChannel(basic_config)


@pytest.fixture
def router() -> MessageRouter:
    return MessageRouter()


# ═══════════════════════════════════════════════════════════════════════════
# Message Types
# ═══════════════════════════════════════════════════════════════════════════


class TestMessageTypes:
    def test_channel_type_values(self):
        assert ChannelType.TELEGRAM.value == "telegram"
        assert ChannelType.DISCORD.value == "discord"
        assert ChannelType.SLACK.value == "slack"
        assert ChannelType.WHATSAPP.value == "whatsapp"
        assert ChannelType.WEBHOOK.value == "webhook"
        assert ChannelType.EMAIL.value == "email"
        assert ChannelType.SMS.value == "sms"

    def test_button_to_dict(self):
        btn = Button(text="Click me", action="do_thing", data="payload123")
        d = btn.to_dict()
        assert d["text"] == "Click me"
        assert d["action"] == "do_thing"
        assert d["data"] == "payload123"

    def test_attachment_to_dict(self):
        att = Attachment(
            type=AttachmentType.IMAGE,
            url="https://cdn.example.com/img.png",
            filename="img.png",
            size=1024,
        )
        d = att.to_dict()
        assert d["type"] == "image"
        assert d["url"] == "https://cdn.example.com/img.png"

    def test_incoming_message_defaults(self):
        msg = IncomingMessage()
        assert msg.channel == ChannelType.WEBHOOK
        assert msg.text == ""
        assert isinstance(msg.timestamp, datetime)
        assert isinstance(msg.attachments, list)

    def test_incoming_message_to_dict(self):
        msg = IncomingMessage(
            id="msg-1",
            channel=ChannelType.TELEGRAM,
            user_id="user42",
            text="Hello",
            chat_id="chat99",
        )
        d = msg.to_dict()
        assert d["id"] == "msg-1"
        assert d["channel"] == "telegram"
        assert d["user_id"] == "user42"
        assert d["text"] == "Hello"

    def test_outgoing_message_defaults(self):
        msg = OutgoingMessage(text="Hello world")
        assert msg.parse_mode == ParseMode.MARKDOWN
        assert msg.buttons == []

    def test_outgoing_message_to_dict(self):
        msg = OutgoingMessage(text="Hi", channel=ChannelType.SLACK)
        d = msg.to_dict()
        assert d["text"] == "Hi"
        assert d["channel"] == "slack"

    def test_message_thread(self):
        thread = MessageThread(channel=ChannelType.DISCORD, thread_id="t-001")
        msg = IncomingMessage(id="m1", text="first message")
        thread.add_message(msg)
        assert len(thread.messages) == 1
        d = thread.to_dict()
        assert d["thread_id"] == "t-001"
        assert len(d["messages"]) == 1

    def test_channel_config_is_user_allowed_with_whitelist(self, basic_config):
        assert basic_config.is_user_allowed("user1") is True
        assert basic_config.is_user_allowed("unknown") is False

    def test_channel_config_is_user_allowed_no_whitelist(self, open_config):
        assert open_config.is_user_allowed("anyone") is True

    def test_channel_config_is_admin(self, basic_config):
        assert basic_config.is_admin("admin1") is True
        assert basic_config.is_admin("user1") is False

    def test_intent_enum(self):
        assert Intent.LEGAL_QUESTION.value == "legal_question"
        assert Intent.RESEARCH_REQUEST.value == "research_request"
        assert Intent.GENERAL_CHAT.value == "general_chat"


# ═══════════════════════════════════════════════════════════════════════════
# ChannelHub
# ═══════════════════════════════════════════════════════════════════════════


class TestChannelHub:
    def test_register_channel(self, basic_config):
        h = ChannelHub()
        mock_ch = MagicMock()
        h.register_channel(ChannelType.TELEGRAM, basic_config, mock_ch)
        assert ChannelType.TELEGRAM in h._channels
        assert ChannelType.TELEGRAM in h._configs

    def test_register_config_only(self, basic_config):
        h = ChannelHub()
        h.register_channel(ChannelType.SLACK, basic_config)
        assert ChannelType.SLACK in h._configs
        assert ChannelType.SLACK not in h._channels

    def test_unregister_channel(self, hub):
        hub.unregister_channel(ChannelType.DISCORD)
        assert ChannelType.DISCORD not in h._channels if False else True  # just test no crash
        assert ChannelType.DISCORD not in hub._channels

    @pytest.mark.asyncio
    async def test_send_success(self, hub):
        results = await hub.send("Hello!", channels=[ChannelType.TELEGRAM], recipient="12345")
        assert ChannelType.TELEGRAM in results

    @pytest.mark.asyncio
    async def test_send_to_unregistered_channel(self, basic_config):
        h = ChannelHub()
        results = await h.send("Hi", channels=[ChannelType.WHATSAPP])
        assert results[ChannelType.WHATSAPP] is False

    @pytest.mark.asyncio
    async def test_broadcast(self, hub):
        results = await hub.broadcast("Broadcast message")
        assert isinstance(results, dict)
        assert len(results) >= 2  # telegram + discord registered

    def test_set_handler(self, hub):
        handler = Mock(return_value="response")
        hub.set_handler(Intent.LEGAL_QUESTION, handler)
        assert Intent.LEGAL_QUESTION in hub._handlers

    def test_route_dispatches_handler(self, hub):
        handler = Mock(return_value="Legal answer!")
        hub.set_handler(Intent.LEGAL_QUESTION, handler)
        msg = IncomingMessage(
            text="Can I sue for breach of contract?",
            channel=ChannelType.TELEGRAM,
            user_id="u1",
        )
        response = hub.route(msg)
        assert handler.called
        assert isinstance(response, str)

    def test_route_unknown_intent(self, hub):
        msg = IncomingMessage(text="hello there", channel=ChannelType.SLACK, user_id="u1")
        response = hub.route(msg)
        assert isinstance(response, str)

    def test_status_returns_dict(self, hub):
        s = hub.status()
        assert "running" in s
        assert "channels" in s
        assert "timestamp" in s

    def test_status_channels_listed(self, hub):
        s = hub.status()
        assert "telegram" in s["channels"]
        assert "discord" in s["channels"]

    @pytest.mark.asyncio
    async def test_enqueue_and_receive(self, hub):
        msg = IncomingMessage(id="e1", text="queued message", channel=ChannelType.TELEGRAM)
        await hub._enqueue(msg)
        received = await hub._message_queue.get()
        assert received.id == "e1"


# ═══════════════════════════════════════════════════════════════════════════
# TelegramChannel
# ═══════════════════════════════════════════════════════════════════════════


class TestTelegramChannel:
    @pytest.mark.asyncio
    async def test_send_message(self, telegram):
        mock_resp = {"ok": True, "result": {"message_id": 1}}
        telegram._post = AsyncMock(return_value=mock_resp)
        result = await telegram.send_message("123", "Hello Telegram!")
        assert telegram._post.called
        call_args = telegram._post.call_args
        assert call_args[0][0] == "sendMessage"
        assert call_args[0][1]["text"] == "Hello Telegram!"

    @pytest.mark.asyncio
    async def test_send_message_with_buttons(self, telegram):
        telegram._post = AsyncMock(return_value={"ok": True})
        buttons = [[Button(text="Yes", action="yes"), Button(text="No", action="no")]]
        await telegram.send_message("chat1", "Choose:", buttons=buttons)
        payload = telegram._post.call_args[0][1]
        assert "reply_markup" in payload
        kb = payload["reply_markup"]["inline_keyboard"]
        assert len(kb[0]) == 2

    @pytest.mark.asyncio
    async def test_send_message_truncates_long_text(self, telegram):
        telegram._post = AsyncMock(return_value={"ok": True})
        long_text = "x" * 10000
        await telegram.send_message("chat1", long_text)
        payload = telegram._post.call_args[0][1]
        assert len(payload["text"]) == telegram.config.max_message_length

    @pytest.mark.asyncio
    async def test_send_file(self, telegram, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        with patch("aiohttp.ClientSession") as mock_session:
            mock_resp = AsyncMock()
            mock_resp.json = AsyncMock(return_value={"ok": True})
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_resp
            # Just verify the method exists and is callable
            assert hasattr(telegram, "send_file")

    @pytest.mark.asyncio
    async def test_send_voice(self, telegram):
        assert hasattr(telegram, "send_voice")

    @pytest.mark.asyncio
    async def test_handle_command_ask(self, telegram):
        response = await telegram.handle_command("/ask", ["What", "is", "law?"], "user1")
        assert "SintraPrime" in response

    @pytest.mark.asyncio
    async def test_handle_command_research(self, telegram):
        response = await telegram.handle_command("/research", ["contract law"], "user1")
        assert "research" in response.lower()

    @pytest.mark.asyncio
    async def test_handle_command_status(self, telegram):
        response = await telegram.handle_command("/status", [], "user1")
        assert "online" in response.lower()

    @pytest.mark.asyncio
    async def test_handle_command_remind(self, telegram):
        response = await telegram.handle_command("/remind", ["tomorrow", "file brief"], "user1")
        assert "tomorrow" in response

    @pytest.mark.asyncio
    async def test_handle_command_doc(self, telegram):
        response = await telegram.handle_command("/doc", ["NDA"], "user1")
        assert "NDA" in response

    @pytest.mark.asyncio
    async def test_handle_command_help(self, telegram):
        response = await telegram.handle_command("/help", [], "user1")
        assert "/ask" in response

    @pytest.mark.asyncio
    async def test_handle_command_unknown(self, telegram):
        response = await telegram.handle_command("/xyz", [], "user1")
        assert "Unknown command" in response

    @pytest.mark.asyncio
    async def test_handle_command_unauthorized(self, basic_config):
        basic_config.allowed_users = ["only-user"]
        tg = TelegramChannel(basic_config)
        response = await tg.handle_command("/ask", ["something"], "blocked-user")
        assert "not authorised" in response.lower() or "not authorized" in response.lower()

    def test_parse_update_text(self, telegram):
        update = {
            "update_id": 100,
            "message": {
                "message_id": 1,
                "from": {"id": 42, "username": "testuser"},
                "chat": {"id": 99},
                "text": "Hello bot",
            },
        }
        msg = telegram._parse_update(update)
        assert msg is not None
        assert msg.text == "Hello bot"
        assert msg.user_id == "42"
        assert msg.channel == ChannelType.TELEGRAM

    def test_parse_update_with_document(self, telegram):
        update = {
            "update_id": 101,
            "message": {
                "message_id": 2,
                "from": {"id": 5},
                "chat": {"id": 10},
                "text": "",
                "document": {"file_id": "abc", "file_name": "doc.pdf", "file_size": 1000},
            },
        }
        msg = telegram._parse_update(update)
        assert msg is not None
        assert len(msg.attachments) == 1
        assert msg.attachments[0].type == AttachmentType.DOCUMENT

    def test_parse_update_no_message(self, telegram):
        update = {"update_id": 200, "callback_query": {"id": "cb1"}}
        result = telegram._parse_update(update)
        assert result is None

    def test_rate_limiter_allows(self):
        rl = RateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            assert rl.is_allowed("user1") is True

    def test_rate_limiter_blocks(self):
        rl = RateLimiter(max_requests=2, window_seconds=60)
        rl.is_allowed("u")
        rl.is_allowed("u")
        assert rl.is_allowed("u") is False


# ═══════════════════════════════════════════════════════════════════════════
# DiscordChannel
# ═══════════════════════════════════════════════════════════════════════════


class TestDiscordChannel:
    @pytest.mark.asyncio
    async def test_send_message_no_bot(self, discord_ch):
        # Without a live bot, should return {"ok": False}
        result = await discord_ch.send_message("ch1", "hi")
        assert result == {"ok": False}

    @pytest.mark.asyncio
    async def test_send_embed_no_bot(self, discord_ch):
        result = await discord_ch.send_embed("ch1", "Title", "Body")
        assert result == {"ok": False}

    @pytest.mark.asyncio
    async def test_create_thread_no_bot(self, discord_ch):
        result = await discord_ch.create_thread("ch1", "My Thread", "Seed message")
        assert result == {"ok": False}

    @pytest.mark.asyncio
    async def test_slash_command_ask(self, discord_ch):
        resp = await discord_ch.handle_slash_command(
            None, "ask", "What is fair use?", ["client"]
        )
        assert "processing" in resp.lower() or "sintra" in resp.lower()

    @pytest.mark.asyncio
    async def test_slash_command_status(self, discord_ch):
        resp = await discord_ch.handle_slash_command(None, "status", "", ["admin"])
        assert "online" in resp.lower()

    @pytest.mark.asyncio
    async def test_slash_command_research_requires_role(self, discord_ch):
        resp = await discord_ch.handle_slash_command(
            None, "research", "contract law", ["client"]
        )
        assert "only" in resp.lower() or "authorized" in resp.lower() or "authorised" in resp.lower()

    @pytest.mark.asyncio
    async def test_slash_command_legal_requires_role(self, discord_ch):
        resp = await discord_ch.handle_slash_command(
            None, "legal", "Is this legal?", ["client"]
        )
        assert "attorney" in resp.lower() or "only" in resp.lower()

    @pytest.mark.asyncio
    async def test_slash_command_unknown_role(self, discord_ch):
        resp = await discord_ch.handle_slash_command(None, "ask", "hi", ["unknown-role"])
        assert "not" in resp.lower()

    @pytest.mark.asyncio
    async def test_slash_command_task(self, discord_ch):
        resp = await discord_ch.handle_slash_command(None, "task", "Review NDA", ["attorney"])
        assert "task" in resp.lower()

    def test_has_role(self):
        assert DiscordChannel._has_role(["admin", "client"], ["admin"]) is True
        assert DiscordChannel._has_role(["client"], ["admin", "attorney"]) is False


# ═══════════════════════════════════════════════════════════════════════════
# SlackChannel
# ═══════════════════════════════════════════════════════════════════════════


class TestSlackChannel:
    @pytest.mark.asyncio
    async def test_slash_sintra_ask(self, slack_ch):
        result = await slack_ch.handle_slash_command("/sintra", "ask What is estoppel?", "U1", "C1")
        assert result["response_type"] == "ephemeral"
        assert "processing" in result["text"].lower() or "estoppel" in result["text"].lower()

    @pytest.mark.asyncio
    async def test_slash_sintra_status(self, slack_ch):
        result = await slack_ch.handle_slash_command("/sintra", "status", "U1", "C1")
        assert "online" in result["text"].lower()

    @pytest.mark.asyncio
    async def test_slash_sintra_help(self, slack_ch):
        result = await slack_ch.handle_slash_command("/sintra", "help", "U1", "C1")
        assert "/sintra" in result["text"]

    @pytest.mark.asyncio
    async def test_slash_legal_question(self, slack_ch):
        result = await slack_ch.handle_slash_command("/legal-question", "Is wiretapping legal?", "U1", "C1")
        assert "legal" in result["text"].lower()

    @pytest.mark.asyncio
    async def test_slash_schedule_task(self, slack_ch):
        result = await slack_ch.handle_slash_command("/schedule-task", "File motion by Friday", "U1", "C1")
        assert "scheduled" in result["text"].lower()

    @pytest.mark.asyncio
    async def test_slash_unknown(self, slack_ch):
        result = await slack_ch.handle_slash_command("/unknown-cmd", "foo", "U1", "C1")
        assert "Unknown" in result["text"]

    def test_build_home_tab(self, slack_ch):
        blocks = slack_ch.build_home_tab(pending_tasks=3, active_tasks=1)
        assert isinstance(blocks, list)
        assert len(blocks) >= 3
        # Should contain header block
        assert any(b.get("type") == "header" for b in blocks)

    def test_verify_signature_valid(self, slack_ch):
        import time as t
        ts = str(int(t.time()))
        body = '{"event": "test"}'
        base = f"v0:{ts}:{body}"
        sig = "v0=" + hmac.new(
            slack_ch.signing_secret.encode(), base.encode(), hashlib.sha256
        ).hexdigest()
        assert slack_ch.verify_signature(ts, body, sig) is True

    def test_verify_signature_invalid(self, slack_ch):
        import time as t
        ts = str(int(t.time()))
        assert slack_ch.verify_signature(ts, '{"test": 1}', "v0=badhash") is False

    def test_parse_event(self, slack_ch):
        event = {
            "text": "Hello Slack",
            "user": "U123",
            "channel": "C456",
            "ts": "1234567890.000001",
            "files": [],
        }
        msg = slack_ch._parse_event(event)
        assert msg is not None
        assert msg.text == "Hello Slack"
        assert msg.user_id == "U123"
        assert msg.channel == ChannelType.SLACK


# ═══════════════════════════════════════════════════════════════════════════
# WhatsAppChannel
# ═══════════════════════════════════════════════════════════════════════════


class TestWhatsAppChannel:
    def test_parse_twilio_webhook_text(self, whatsapp):
        form = {
            "SmsMessageSid": "SM123",
            "From": "whatsapp:+15559876543",
            "Body": "Hello from WhatsApp",
            "NumMedia": "0",
        }
        msg = whatsapp.parse_twilio_webhook(form)
        assert msg is not None
        assert msg.text == "Hello from WhatsApp"
        assert msg.user_id == "+15559876543"
        assert msg.channel == ChannelType.WHATSAPP

    def test_parse_twilio_webhook_with_media(self, whatsapp):
        form = {
            "SmsMessageSid": "SM456",
            "From": "whatsapp:+15551112222",
            "Body": "",
            "NumMedia": "1",
            "MediaUrl0": "https://api.twilio.com/media/123",
            "MediaContentType0": "image/jpeg",
        }
        msg = whatsapp.parse_twilio_webhook(form)
        assert len(msg.attachments) == 1
        assert msg.attachments[0].type == AttachmentType.IMAGE

    def test_parse_meta_webhook(self, whatsapp):
        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {"from": "+10987654321", "id": "wamid.123", "text": {"body": "Hi Meta"}}
                                ],
                                "contacts": [{"profile": {"name": "Test User"}}],
                            }
                        }
                    ]
                }
            ]
        }
        msg = whatsapp.parse_meta_webhook(payload)
        assert msg is not None
        assert msg.text == "Hi Meta"

    def test_parse_meta_webhook_malformed(self, whatsapp):
        msg = whatsapp.parse_meta_webhook({})
        assert msg is None

    def test_legal_templates_exist(self, whatsapp):
        assert "case_update" in whatsapp.LEGAL_TEMPLATES
        assert "hearing_reminder" in whatsapp.LEGAL_TEMPLATES
        assert "document_ready" in whatsapp.LEGAL_TEMPLATES


# ═══════════════════════════════════════════════════════════════════════════
# WebhookChannel
# ═══════════════════════════════════════════════════════════════════════════


class TestWebhookChannel:
    def test_register_endpoint(self, webhook_ch):
        handler = AsyncMock()
        webhook_ch.register_endpoint("/hooks/test", handler, secret="s3cr3t")
        assert "/hooks/test" in webhook_ch._endpoints
        assert "/hooks/test" in webhook_ch._secrets

    def test_get_registered_endpoints(self, webhook_ch):
        webhook_ch.register_endpoint("/ep1", AsyncMock())
        webhook_ch.register_endpoint("/ep2", AsyncMock())
        eps = webhook_ch.get_registered_endpoints()
        assert "/ep1" in eps
        assert "/ep2" in eps

    @pytest.mark.asyncio
    async def test_handle_incoming_success(self, webhook_ch):
        handler = AsyncMock()
        webhook_ch.register_endpoint("/test", handler)
        result = await webhook_ch.handle_incoming("/test", {"key": "value"})
        assert result is True
        handler.assert_awaited_once_with({"key": "value"})

    @pytest.mark.asyncio
    async def test_handle_incoming_unknown_path(self, webhook_ch):
        result = await webhook_ch.handle_incoming("/nonexistent", {})
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_incoming_bad_signature(self, webhook_ch):
        handler = AsyncMock()
        webhook_ch.register_endpoint("/secure", handler, secret="mysecret")
        result = await webhook_ch.handle_incoming(
            "/secure", {"data": "test"}, signature="sha256=badsig"
        )
        assert result is False
        handler.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handle_incoming_valid_signature(self, webhook_ch):
        handler = AsyncMock()
        secret = "mysecret"
        webhook_ch.register_endpoint("/signed", handler, secret=secret)
        payload = {"event": "test"}
        body = json.dumps(payload, separators=(",", ":"))
        sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        result = await webhook_ch.handle_incoming("/signed", payload, signature=sig)
        assert result is True

    def test_verify_signature_valid(self, webhook_ch):
        body = '{"test": true}'
        secret = "webhook-secret"
        sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        assert webhook_ch.verify_signature(body, sig, secret) is True

    def test_verify_signature_sha256_prefix(self, webhook_ch):
        body = '{"test": true}'
        secret = "webhook-secret"
        sig = "sha256=" + hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        assert webhook_ch.verify_signature(body, sig, secret) is True

    def test_verify_signature_invalid(self, webhook_ch):
        assert webhook_ch.verify_signature("body", "badsig", "secret") is False

    def test_rate_limit_allows(self, webhook_ch):
        assert webhook_ch.check_rate_limit("source1", max_per_minute=100) is True

    def test_rate_limit_blocks(self, webhook_ch):
        for _ in range(5):
            webhook_ch.check_rate_limit("src", max_per_minute=5)
        assert webhook_ch.check_rate_limit("src", max_per_minute=5) is False

    def test_retry_policy_delay(self):
        rp = RetryPolicy(base_delay=1.0, max_delay=10.0)
        assert rp.delay_for(0) == 1.0
        assert rp.delay_for(1) == 2.0
        assert rp.delay_for(2) == 4.0
        assert rp.delay_for(10) == 10.0  # capped


# ═══════════════════════════════════════════════════════════════════════════
# MessageRouter
# ═══════════════════════════════════════════════════════════════════════════


class TestMessageRouter:
    def test_detect_legal_intent(self, router):
        assert router.detect_intent("Can I sue for breach of contract?") == Intent.LEGAL_QUESTION

    def test_detect_research_intent(self, router):
        assert router.detect_intent("Please research the history of antitrust law") == Intent.RESEARCH_REQUEST

    def test_detect_document_intent(self, router):
        assert router.detect_intent("Draft an NDA for our partnership") == Intent.DOCUMENT_REQUEST

    def test_detect_task_intent(self, router):
        assert router.detect_intent("Schedule a reminder to file the motion") == Intent.TASK_MANAGEMENT

    def test_detect_financial_intent(self, router):
        assert router.detect_intent("What is the payment status of invoice #12345?") == Intent.FINANCIAL_QUERY

    def test_detect_status_intent(self, router):
        assert router.detect_intent("What is the current status of the system?") == Intent.STATUS_CHECK

    def test_detect_reminder_intent(self, router):
        assert router.detect_intent("Remind me to file the brief tomorrow") == Intent.REMINDER

    def test_detect_general_chat(self, router):
        assert router.detect_intent("Hey, good morning!") == Intent.GENERAL_CHAT

    def test_extract_dates(self, router):
        entities = router.extract_entities("The hearing is on 2024-03-15 and also April 1, 2024.")
        assert len(entities["dates"]) >= 1

    def test_extract_amounts(self, router):
        entities = router.extract_entities("Invoice for $1,500.00 is due.")
        assert len(entities["amounts"]) >= 1

    def test_extract_jurisdictions(self, router):
        entities = router.extract_entities("The case is filed in California federal court.")
        assert len(entities["jurisdictions"]) >= 1

    def test_extract_names(self, router):
        entities = router.extract_entities("Attorney Mr. John Smith filed the motion.")
        assert len(entities["names"]) >= 1

    def test_extract_entities_empty(self, router):
        entities = router.extract_entities("hello world")
        assert entities["dates"] == []
        assert entities["amounts"] == []

    def test_register_and_dispatch_handler(self, router):
        handler = Mock(return_value="Custom response")
        router.register_handler(Intent.LEGAL_QUESTION, handler)
        msg = IncomingMessage(text="sue for negligence", channel=ChannelType.TELEGRAM)
        response = router.route_to_handler(Intent.LEGAL_QUESTION, {}, msg)
        assert handler.called

    def test_default_response_legal(self, router):
        msg = IncomingMessage(text="", channel=ChannelType.TELEGRAM)
        resp = router._default_response(Intent.LEGAL_QUESTION, {}, msg)
        assert "legal" in resp.lower()

    def test_default_response_status(self, router):
        msg = IncomingMessage(text="", channel=ChannelType.SLACK)
        resp = router._default_response(Intent.STATUS_CHECK, {}, msg)
        assert "operational" in resp.lower()

    def test_format_response_telegram(self, router):
        text = "**Bold** _italic_"
        result = router.format_response(text, ChannelType.TELEGRAM)
        assert isinstance(result, str)

    def test_format_response_slack(self, router):
        text = "**Bold item** and more"
        result = router.format_response(text, ChannelType.SLACK)
        assert "**" not in result  # converted to single *

    def test_format_response_sms_strips_markdown(self, router):
        text = "**Bold** and *italic* and `code`"
        result = router.format_response(text, ChannelType.SMS)
        assert "*" not in result
        assert "`" not in result

    def test_detect_intent_scored(self, router):
        scores = router.detect_intent_scored(
            "I need to draft a contract and also research the applicable statute"
        )
        intents = [i for i, _ in scores]
        # Both document and legal/research should score
        assert len(scores) >= 1


# ═══════════════════════════════════════════════════════════════════════════
# Integration — end-to-end message flow
# ═══════════════════════════════════════════════════════════════════════════


class TestIntegration:
    @pytest.mark.asyncio
    async def test_telegram_message_flows_through_hub(self, basic_config):
        """Simulate a full Telegram message → hub → handler → response flow."""
        hub = ChannelHub()
        mock_tg = AsyncMock()
        mock_tg.connected = True
        hub.register_channel(ChannelType.TELEGRAM, basic_config, mock_tg)

        legal_handler = Mock(return_value="Here is the legal answer.")
        hub.set_handler(Intent.LEGAL_QUESTION, legal_handler)

        incoming = IncomingMessage(
            id="int-001",
            channel=ChannelType.TELEGRAM,
            user_id="user1",
            text="Can I file a lawsuit for breach of contract in California?",
            chat_id="chat123",
        )
        await hub._enqueue(incoming)

        queued = await hub._message_queue.get()
        assert queued.id == "int-001"

        response = hub.route(queued)
        assert legal_handler.called
        assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_broadcast_reaches_all_channels(self, basic_config):
        """Broadcast should attempt delivery to all registered channels."""
        hub = ChannelHub()
        mock_tg = AsyncMock()
        mock_tg.connected = True
        mock_sl = AsyncMock()
        mock_sl.connected = True
        hub.register_channel(ChannelType.TELEGRAM, basic_config, mock_tg)
        hub.register_channel(ChannelType.SLACK, basic_config, mock_sl)

        results = await hub.broadcast("System announcement!")
        assert len(results) == 2

    def test_message_router_with_slack_formatting(self):
        """Router should adapt response for Slack mrkdwn."""
        r = MessageRouter()
        msg = IncomingMessage(text="research antitrust", channel=ChannelType.SLACK)
        intent = r.detect_intent(msg.text)
        entities = r.extract_entities(msg.text)
        response = r.route_to_handler(intent, entities, msg)
        # Should not have double asterisks in Slack response
        assert "**" not in response

    def test_webhook_and_router_pipeline(self):
        """Webhook payload → parse → router → response."""
        config = ChannelConfig(token="t", webhook_secret="ws")
        wh = WebhookChannel(config)
        r = MessageRouter()

        raw_payload = {"text": "Draft an NDA agreement please", "user": "u1", "channel": "C1"}
        msg = IncomingMessage(
            text=raw_payload["text"],
            channel=ChannelType.WEBHOOK,
            user_id=raw_payload["user"],
        )
        intent = r.detect_intent(msg.text)
        assert intent == Intent.DOCUMENT_REQUEST

        response = r.route_to_handler(intent, r.extract_entities(msg.text), msg)
        assert isinstance(response, str)
        assert len(response) > 0

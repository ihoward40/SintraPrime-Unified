"""
Slack workspace integration for SintraPrime-Unified.

Features:
- Block Kit rich messages
- Socket Mode (real-time) or Events API
- App Home tab with task dashboard
- Slash commands: /sintra, /legal-question, /schedule-task
- Interactive buttons and modals
- File upload support

Inspired by ChatGPT Connected Apps Slack integration and Hermes Agent enterprise messaging.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from .message_types import Attachment, AttachmentType, ChannelConfig, ChannelType, IncomingMessage

logger = logging.getLogger(__name__)


class SlackChannel:
    """
    Slack channel adapter using the Bolt SDK or raw HTTP.
    Supports both Socket Mode (preferred) and Events API webhook mode.
    """

    def __init__(self, config: ChannelConfig) -> None:
        self.config = config
        self.token: str = config.token or ""  # Bot OAuth token (xoxb-...)
        self.signing_secret: str = config.webhook_secret or ""
        self.connected: bool = False
        self._handler: Optional[Callable] = None
        self._app: Optional[Any] = None

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    async def send_message(
        self,
        channel: str,
        text: str,
        blocks: Optional[List[Dict]] = None,
    ) -> Dict:
        """Post a message to a Slack channel or DM."""
        payload: Dict[str, Any] = {"channel": channel, "text": text}
        if blocks:
            payload["blocks"] = blocks
        return await self._api_call("chat.postMessage", payload)

    async def send_blocks(self, channel: str, blocks: List[Dict]) -> Dict:
        """Post a Block Kit message."""
        return await self.send_message(channel, "", blocks=blocks)

    async def update_message(self, ts: str, channel: str, text: str, blocks: Optional[List[Dict]] = None) -> Dict:
        """Edit an existing message identified by its timestamp."""
        payload: Dict[str, Any] = {"channel": channel, "ts": ts, "text": text}
        if blocks:
            payload["blocks"] = blocks
        return await self._api_call("chat.update", payload)

    async def post_file(self, channel: str, file_path: str, title: str = "") -> Dict:
        """Upload a file to a Slack channel."""
        import aiohttp  # type: ignore[import]
        url = "https://slack.com/api/files.upload"
        headers = {"Authorization": f"Bearer {self.token}"}
        async with aiohttp.ClientSession(headers=headers) as session:
            with open(file_path, "rb") as fh:
                form = aiohttp.FormData()
                form.add_field("channels", channel)
                form.add_field("title", title or file_path.split("/")[-1])
                form.add_field("file", fh, filename=file_path.split("/")[-1])
                async with session.post(url, data=form) as resp:
                    return await resp.json()

    # ------------------------------------------------------------------
    # Slash command handlers
    # ------------------------------------------------------------------

    async def handle_slash_command(self, command: str, text: str, user_id: str, channel_id: str) -> Dict:
        """
        Handle a Slack slash command payload.
        Returns a Slack response payload dict.
        """
        cmd = command.lower()
        if cmd in ("/sintra",):
            parts = text.strip().split(None, 1)
            action = parts[0].lower() if parts else "help"
            query = parts[1] if len(parts) > 1 else ""

            if action == "ask":
                return self._ephemeral(f"🤖 Processing: *{query}*")
            elif action == "research":
                return self._ephemeral(f"🔍 Autonomous research queued for: *{query}*")
            elif action == "legal":
                return self._ephemeral(f"⚖️ Legal question received: *{query}*")
            elif action == "status":
                return self._ephemeral("✅ SintraPrime is *online*. All systems nominal.")
            elif action == "task":
                return self._ephemeral(f"📋 Task: *{query}*")
            else:
                return self._ephemeral(self._help_text())
        elif cmd == "/legal-question":
            return self._ephemeral(f"⚖️ Legal query submitted: *{text}*\nRouting to legal intelligence…")
        elif cmd == "/schedule-task":
            return self._ephemeral(f"📅 Task scheduled: *{text}*")
        return self._ephemeral(f"❓ Unknown command: `{command}`")

    @staticmethod
    def _ephemeral(text: str) -> Dict:
        return {"response_type": "ephemeral", "text": text}

    @staticmethod
    def _help_text() -> str:
        return (
            "*SintraPrime Slack Commands*\n\n"
            "`/sintra ask [question]` — Ask anything\n"
            "`/sintra research [topic]` — Deep research\n"
            "`/sintra legal [question]` — Legal analysis\n"
            "`/sintra status` — System status\n"
            "`/sintra task [description]` — Manage tasks\n"
            "`/legal-question [q]` — Direct legal query\n"
            "`/schedule-task [desc]` — Schedule a task"
        )

    # ------------------------------------------------------------------
    # App Home tab
    # ------------------------------------------------------------------

    def build_home_tab(self, pending_tasks: int = 0, active_tasks: int = 0) -> List[Dict]:
        """Build Block Kit payload for the App Home tab task dashboard."""
        return [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🧠 SintraPrime Dashboard"},
            },
            {"type": "divider"},
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Pending Tasks:*\n{pending_tasks}"},
                    {"type": "mrkdwn", "text": f"*Active Tasks:*\n{active_tasks}"},
                ],
            },
            {"type": "divider"},
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📋 View Tasks"},
                        "action_id": "view_tasks",
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🔍 New Research"},
                        "action_id": "new_research",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "⚖️ Legal Query"},
                        "action_id": "legal_query",
                    },
                ],
            },
        ]

    # ------------------------------------------------------------------
    # Signature verification
    # ------------------------------------------------------------------

    def verify_signature(self, timestamp: str, body: str, signature: str) -> bool:
        """Verify a Slack request signature using the signing secret."""
        if abs(time.time() - float(timestamp)) > 300:
            return False  # replay attack guard
        base = f"v0:{timestamp}:{body}"
        computed = "v0=" + hmac.new(
            self.signing_secret.encode(), base.encode(), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(computed, signature)

    # ------------------------------------------------------------------
    # Listening
    # ------------------------------------------------------------------

    async def listen(self, handler_fn: Callable) -> None:
        """Start the Slack Socket Mode listener."""
        self._handler = handler_fn
        logger.info("SlackChannel: starting Socket Mode listener.")

        try:
            from slack_bolt.async_app import AsyncApp  # type: ignore[import]
            from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler  # type: ignore[import]

            app = AsyncApp(token=self.token, signing_secret=self.signing_secret)
            self._app = app
            self.connected = True

            @app.message("")
            async def handle_message(message, say):
                incoming = self._parse_event(message)
                if incoming:
                    await handler_fn(incoming)

            app_token = self.config.extra.get("app_token", "")
            handler = AsyncSocketModeHandler(app, app_token)
            await handler.start_async()
        except ImportError:
            logger.warning("slack_bolt not installed — running in stub mode.")
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            logger.info("SlackChannel: listener cancelled.")

    def _parse_event(self, event: Dict) -> Optional[IncomingMessage]:
        """Convert a raw Slack event dict to IncomingMessage."""
        text = event.get("text", "")
        user_id = event.get("user", "")
        channel = event.get("channel", "")
        ts = event.get("ts", "")
        files = event.get("files", [])

        attachments = [
            Attachment(
                type=AttachmentType.DOCUMENT,
                url=f.get("url_private", ""),
                filename=f.get("name"),
                size=f.get("size"),
                mime_type=f.get("mimetype"),
            )
            for f in files
        ]

        return IncomingMessage(
            id=ts,
            channel=ChannelType.SLACK,
            user_id=user_id,
            text=text,
            chat_id=channel,
            attachments=attachments,
            metadata={"ts": ts, "raw": event},
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _api_call(self, method: str, payload: Dict) -> Dict:
        """Call Slack Web API method."""
        import aiohttp  # type: ignore[import]
        url = f"https://slack.com/api/{method}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(url, json=payload) as resp:
                return await resp.json()

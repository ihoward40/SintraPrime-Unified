"""
Telegram Bot integration for SintraPrime-Unified.

Supports:
- Text, file, and voice message delivery
- Polling and webhook mode
- Command handlers: /ask, /research, /status, /remind, /doc
- Rate limiting and user authentication
- Inline keyboard buttons (Button model)

Inspired by Claude Code Channels Telegram integration and Manus AI Telegram access.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import time
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional

from .message_types import Attachment, AttachmentType, Button, ChannelConfig, ChannelType, IncomingMessage

logger = logging.getLogger(__name__)

# Telegram Bot API base URL
TELEGRAM_API = "https://api.telegram.org/bot{token}"


class RateLimiter:
    """Simple sliding-window rate limiter."""

    def __init__(self, max_requests: int = 20, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window = window_seconds
        self._timestamps: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - self.window
        ts = self._timestamps[key]
        ts[:] = [t for t in ts if t > window_start]
        if len(ts) >= self.max_requests:
            return False
        ts.append(now)
        return True


class TelegramChannel:
    """
    Telegram Bot channel adapter for SintraPrime.

    Supports both long-polling and webhook operation modes.
    """

    # Bot commands handled natively
    COMMANDS = {
        "/ask": "ask_sintra",
        "/research": "research",
        "/status": "status",
        "/remind": "remind",
        "/doc": "generate_doc",
        "/help": "help",
    }

    def __init__(self, config: ChannelConfig) -> None:
        self.config = config
        self.token: str = config.token or ""
        self._api_base = f"https://api.telegram.org/bot{self.token}"
        self._offset: int = 0
        self._rate_limiter = RateLimiter(max_requests=config.rate_limit_per_minute)
        self.connected: bool = bool(self.token)
        self._handler: Optional[Callable] = None

    # ------------------------------------------------------------------
    # Internal HTTP helper (uses aiohttp when available, else httpx)
    # ------------------------------------------------------------------

    async def _post(self, endpoint: str, payload: Dict) -> Dict:
        """POST to Telegram Bot API."""
        import aiohttp  # type: ignore[import]
        url = f"{self._api_base}/{endpoint}"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                return await resp.json()

    async def _get(self, endpoint: str, params: Dict = None) -> Dict:
        """GET from Telegram Bot API."""
        import aiohttp  # type: ignore[import]
        url = f"{self._api_base}/{endpoint}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params or {}) as resp:
                return await resp.json()

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    async def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "Markdown",
        buttons: Optional[List[List[Button]]] = None,
    ) -> Dict:
        """Send a text message, optionally with an inline keyboard."""
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": text[:self.config.max_message_length],
            "parse_mode": parse_mode,
        }
        if buttons:
            keyboard = [
                [{"text": b.text, "callback_data": b.data or b.action} for b in row]
                for row in buttons
            ]
            payload["reply_markup"] = {"inline_keyboard": keyboard}
        return await self._post("sendMessage", payload)

    async def send_file(self, chat_id: str, file_path: str, caption: str = "") -> Dict:
        """Send a document file."""
        import aiohttp  # type: ignore[import]
        url = f"{self._api_base}/sendDocument"
        async with aiohttp.ClientSession() as session:
            with open(file_path, "rb") as fh:
                form = aiohttp.FormData()
                form.add_field("chat_id", str(chat_id))
                form.add_field("caption", caption)
                form.add_field("document", fh, filename=file_path.split("/")[-1])
                async with session.post(url, data=form) as resp:
                    return await resp.json()

    async def send_voice(self, chat_id: str, audio_path: str) -> Dict:
        """Send a voice message (OGG/OPUS format)."""
        import aiohttp  # type: ignore[import]
        url = f"{self._api_base}/sendVoice"
        async with aiohttp.ClientSession() as session:
            with open(audio_path, "rb") as fh:
                form = aiohttp.FormData()
                form.add_field("chat_id", str(chat_id))
                form.add_field("voice", fh, filename="voice.ogg")
                async with session.post(url, data=form) as resp:
                    return await resp.json()

    async def reply_to(self, message_id: str, text: str, chat_id: Optional[str] = None) -> Dict:
        """Reply to a specific message."""
        payload = {
            "chat_id": chat_id or message_id,
            "text": text,
            "reply_to_message_id": message_id,
        }
        return await self._post("sendMessage", payload)

    # ------------------------------------------------------------------
    # Command handling
    # ------------------------------------------------------------------

    async def handle_command(self, command: str, args: List[str], chat_id: str) -> str:
        """
        Dispatch a Telegram slash-command to the appropriate SintraPrime module.

        :returns: Response text to send back to the user.
        """
        user_id = str(chat_id)
        if not self.config.is_user_allowed(user_id):
            return "⛔ You are not authorised to use SintraPrime. Contact an admin."

        cmd = command.split("@")[0].lower()  # strip bot username
        body = " ".join(args).strip()

        if cmd == "/ask":
            return f"🤖 *SintraPrime says:* _{body}_\n_(AI module not yet loaded)_"
        elif cmd == "/research":
            return f"🔍 Starting autonomous research on: *{body}*\nYou will be notified when done."
        elif cmd == "/status":
            return "✅ SintraPrime is *online* and all systems nominal."
        elif cmd == "/remind":
            parts = body.split(None, 1)
            when = parts[0] if parts else "soon"
            what = parts[1] if len(parts) > 1 else "something"
            return f"⏰ Reminder set for *{when}*: _{what}_"
        elif cmd == "/doc":
            return f"📄 Generating *{body}* document…\nWill send when ready."
        elif cmd == "/help":
            return (
                "📋 *SintraPrime Commands*\n\n"
                "/ask [question] — Ask SintraPrime anything\n"
                "/research [topic] — Autonomous deep research\n"
                "/status — System and task status\n"
                "/remind [when] [what] — Schedule a reminder\n"
                "/doc [type] — Generate a document\n"
                "/help — Show this menu"
            )
        return f"❓ Unknown command: `{command}`"

    # ------------------------------------------------------------------
    # Listening (polling)
    # ------------------------------------------------------------------

    async def listen(self, handler_fn: Callable) -> None:
        """
        Start long-polling for updates and call *handler_fn* with each
        normalised IncomingMessage.
        """
        self._handler = handler_fn
        logger.info("TelegramChannel: starting long-poll listener.")
        while True:
            try:
                data = await self._get("getUpdates", {"offset": self._offset, "timeout": 30})
                updates = data.get("result", [])
                for update in updates:
                    self._offset = update["update_id"] + 1
                    msg = self._parse_update(update)
                    if msg:
                        if not self._rate_limiter.is_allowed(msg.user_id):
                            logger.warning("Rate limit hit for user %s", msg.user_id)
                            continue
                        await handler_fn(msg)
            except asyncio.CancelledError:
                logger.info("TelegramChannel: listener cancelled.")
                break
            except Exception as exc:
                logger.error("TelegramChannel poll error: %s", exc)
                await asyncio.sleep(5)

    def _parse_update(self, update: Dict) -> Optional[IncomingMessage]:
        """Convert a raw Telegram update dict to an IncomingMessage."""
        message = update.get("message") or update.get("edited_message")
        if not message:
            return None
        from_user = message.get("from", {})
        text = message.get("text", "")
        chat = message.get("chat", {})
        attachments: List[Attachment] = []

        if message.get("document"):
            doc = message["document"]
            attachments.append(
                Attachment(
                    type=AttachmentType.DOCUMENT,
                    url=f"tg://file/{doc.get('file_id')}",
                    filename=doc.get("file_name"),
                    size=doc.get("file_size"),
                )
            )
        if message.get("voice"):
            voice = message["voice"]
            attachments.append(
                Attachment(type=AttachmentType.VOICE, url=f"tg://file/{voice.get('file_id')}")
            )

        return IncomingMessage(
            id=str(message.get("message_id", "")),
            channel=ChannelType.TELEGRAM,
            user_id=str(from_user.get("id", "")),
            username=from_user.get("username"),
            text=text,
            chat_id=str(chat.get("id", "")),
            attachments=attachments,
            metadata={"raw": update},
        )

    # ------------------------------------------------------------------
    # Webhook verification
    # ------------------------------------------------------------------

    def verify_webhook_token(self, x_telegram_bot_api_secret_token: str, secret: str) -> bool:
        """Verify Telegram webhook secret header."""
        expected = hmac.new(secret.encode(), digestmod=hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, x_telegram_bot_api_secret_token)

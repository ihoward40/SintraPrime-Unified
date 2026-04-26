"""
Discord Bot integration for SintraPrime-Unified.

Features:
- Rich embed messages
- Threaded responses
- Slash commands: /sintra ask|research|legal|status|task
- Role-based access control (admin, attorney, client)
- Auto-thread creation for long AI responses

Inspired by OpenClaw Discord integration and Claude Code Channels Discord bot.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

from .message_types import Attachment, AttachmentType, ChannelConfig, ChannelType, IncomingMessage

logger = logging.getLogger(__name__)

# Discord embed colour palette
COLOURS = {
    "primary": 0x5865F2,   # Discord blurple
    "success": 0x57F287,
    "warning": 0xFEE75C,
    "danger": 0xED4245,
    "info": 0x00B0F4,
    "legal": 0xF4B940,
}

# Role names for access control
ROLE_ADMIN = "sintra-admin"
ROLE_ATTORNEY = "attorney"
ROLE_CLIENT = "client"
ALLOWED_ROLES = {ROLE_ADMIN, ROLE_ATTORNEY, ROLE_CLIENT, "admin", "sintra_admin"}


class DiscordChannel:
    """
    Discord bot channel adapter.

    Wraps the discord.py library with SintraPrime-specific slash commands
    and role-based access control.
    """

    def __init__(self, config: ChannelConfig) -> None:
        self.config = config
        self.token: str = config.token or ""
        self.connected: bool = bool(self.token)
        self._handler: Optional[Callable] = None
        # In production this would hold a discord.Client/Bot instance
        self._bot: Optional[Any] = None

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    async def send_message(
        self,
        channel_id: str,
        text: str,
        embed: Optional[Dict[str, Any]] = None,
    ) -> Dict:
        """Send a plain text message to a channel, optionally with an embed."""
        if not self._bot:
            logger.warning("Discord bot not initialised — message not sent.")
            return {"ok": False}
        channel = await self._bot.fetch_channel(int(channel_id))
        if embed:
            import discord  # type: ignore[import]
            e = discord.Embed(**embed)
            return await channel.send(text, embed=e)
        return await channel.send(text)

    async def send_embed(
        self,
        channel_id: str,
        title: str,
        description: str,
        fields: Optional[List[Dict[str, Any]]] = None,
        color: int = COLOURS["primary"],
    ) -> Dict:
        """Send a rich embed message."""
        embed_data = {
            "title": title,
            "description": description,
            "color": color,
            "fields": fields or [],
        }
        return await self.send_message(channel_id, "", embed=embed_data)

    async def create_thread(
        self,
        channel_id: str,
        name: str,
        message: str,
    ) -> Dict:
        """Create a new thread in *channel_id* and post *message* there."""
        if not self._bot:
            logger.warning("Discord bot not initialised — thread not created.")
            return {"ok": False}
        channel = await self._bot.fetch_channel(int(channel_id))
        # Send the seed message then create a thread from it
        seed = await channel.send(message)
        thread = await seed.create_thread(name=name)
        return {"thread_id": str(thread.id), "message_id": str(seed.id)}

    # ------------------------------------------------------------------
    # Slash command dispatch
    # ------------------------------------------------------------------

    async def handle_slash_command(
        self,
        interaction: Any,
        sub_command: str,
        query: str,
        user_roles: List[str],
    ) -> str:
        """
        Handle a /sintra slash command interaction.

        :param interaction: discord.Interaction object.
        :param sub_command: Sub-command name (ask, research, legal, status, task).
        :param query: The user's query text.
        :param user_roles: List of role names the invoking user has.
        :returns: Response string.
        """
        if not self._user_has_access(user_roles):
            return "⛔ You do not have a role authorised to use SintraPrime."

        if sub_command == "ask":
            return f"🤖 *SintraPrime* is processing: **{query}**"
        elif sub_command == "research":
            if not self._has_role(user_roles, [ROLE_ADMIN, ROLE_ATTORNEY]):
                return "⛔ Only attorneys and admins may run deep research."
            return f"🔍 Autonomous research started for: **{query}**\nResults will be posted in a new thread."
        elif sub_command == "legal":
            if not self._has_role(user_roles, [ROLE_ADMIN, ROLE_ATTORNEY]):
                return "⛔ Only attorneys may submit legal questions."
            return f"⚖️ Legal question received: **{query}**\nRouting to legal intelligence module…"
        elif sub_command == "status":
            return "✅ SintraPrime is **online**. All subsystems nominal."
        elif sub_command == "task":
            return f"📋 Task management: **{query}**\nOpening task dashboard…"
        return f"❓ Unknown sub-command: `{sub_command}`"

    @staticmethod
    def _has_role(user_roles: List[str], required: List[str]) -> bool:
        return bool(set(user_roles) & set(required))

    def _user_has_access(self, user_roles: List[str]) -> bool:
        # Always enforce role-based access control
        return bool(set(user_roles) & ALLOWED_ROLES)

    # ------------------------------------------------------------------
    # Listening
    # ------------------------------------------------------------------

    async def listen(self, handler_fn: Callable) -> None:
        """
        Start the Discord bot event loop.
        Calls *handler_fn* with normalised IncomingMessage for each message.
        """
        self._handler = handler_fn
        logger.info("DiscordChannel: starting listener.")

        if not self.token:
            logger.error("DiscordChannel: no bot token configured.")
            return

        try:
            import discord  # type: ignore[import]
            intents = discord.Intents.default()
            intents.message_content = True
            bot = discord.Client(intents=intents)
            self._bot = bot

            @bot.event
            async def on_ready():
                self.connected = True
                logger.info("Discord bot connected as %s", bot.user)

            @bot.event
            async def on_message(message):
                if message.author.bot:
                    return
                attachments = [
                    Attachment(
                        type=AttachmentType.DOCUMENT,
                        url=a.url,
                        filename=a.filename,
                        size=a.size,
                    )
                    for a in message.attachments
                ]
                incoming = IncomingMessage(
                    id=str(message.id),
                    channel=ChannelType.DISCORD,
                    user_id=str(message.author.id),
                    username=str(message.author),
                    text=message.content,
                    chat_id=str(message.channel.id),
                    guild_id=str(message.guild.id) if message.guild else None,
                    attachments=attachments,
                    metadata={"raw_message_id": str(message.id)},
                )
                await handler_fn(incoming)

            await bot.start(self.token)
        except ImportError:
            logger.warning("discord.py not installed — running in stub mode.")
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            logger.info("DiscordChannel: listener cancelled.")

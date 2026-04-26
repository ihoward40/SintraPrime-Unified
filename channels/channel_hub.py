"""
ChannelHub — master message router for SintraPrime-Unified.

Inspired by Manus AI's multi-channel dispatcher and Hermes Agent enterprise
messaging layer. Provides a single interface to send, receive, and route
messages across Telegram, Discord, Slack, WhatsApp, and custom webhooks.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

from .message_types import (
    ChannelConfig,
    ChannelType,
    IncomingMessage,
    Intent,
    OutgoingMessage,
)

logger = logging.getLogger(__name__)


class ChannelHub:
    """
    Central orchestrator for all messaging channels.

    Usage::

        hub = ChannelHub()
        hub.register_channel(ChannelType.TELEGRAM, ChannelConfig(token="..."))
        await hub.send("Hello!", channels=[ChannelType.TELEGRAM], recipient="123456")

    Inspired by:
    - Manus AI — Telegram, WhatsApp, Slack, LINE
    - OpenClaw — Discord, Telegram, WeChat
    - Hermes Agent — enterprise messaging (WeChat Work, WhatsApp)
    """

    def __init__(self) -> None:
        self._channels: Dict[ChannelType, Any] = {}
        self._configs: Dict[ChannelType, ChannelConfig] = {}
        self._handlers: Dict[Intent, Callable] = {}
        self._message_queue: asyncio.Queue[IncomingMessage] = asyncio.Queue()
        self._running = False
        self._router: Optional[Any] = None  # MessageRouter injected lazily

    # ------------------------------------------------------------------
    # Channel registration
    # ------------------------------------------------------------------

    def register_channel(
        self, channel_type: ChannelType, config: ChannelConfig, channel_instance: Optional[Any] = None
    ) -> None:
        """Register a channel with its configuration."""
        self._configs[channel_type] = config
        if channel_instance is not None:
            self._channels[channel_type] = channel_instance
        logger.info("Registered channel: %s", channel_type.value)

    def unregister_channel(self, channel_type: ChannelType) -> None:
        """Remove a registered channel."""
        self._channels.pop(channel_type, None)
        self._configs.pop(channel_type, None)
        logger.info("Unregistered channel: %s", channel_type.value)

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    async def send(
        self,
        text: str,
        channels: Optional[List[ChannelType]] = None,
        recipient: Optional[str] = None,
        buttons: Optional[List] = None,
        attachments: Optional[List] = None,
        parse_mode: str = "Markdown",
    ) -> Dict[ChannelType, bool]:
        """
        Send *text* to one or more channels.

        :param text: Message body.
        :param channels: Target channel types; defaults to all registered.
        :param recipient: Destination (chat_id, phone, channel id…).
        :param buttons: Optional inline keyboard rows.
        :param attachments: Optional file attachments.
        :returns: Mapping of channel → success boolean.
        """
        from .message_types import OutgoingMessage, ParseMode

        targets = channels or list(self._channels.keys())
        msg = OutgoingMessage(
            text=text,
            recipient=recipient,
            buttons=buttons or [],
            attachments=attachments or [],
        )
        results: Dict[ChannelType, bool] = {}

        for ch_type in targets:
            ch = self._channels.get(ch_type)
            if ch is None:
                logger.warning("Channel %s not initialised — skipping send.", ch_type.value)
                results[ch_type] = False
                continue
            try:
                await ch.send_message(recipient, text)
                results[ch_type] = True
            except Exception as exc:
                logger.error("Send failed on %s: %s", ch_type.value, exc)
                results[ch_type] = False

        return results

    async def broadcast(self, text: str, channels: Optional[List[ChannelType]] = None) -> Dict[ChannelType, bool]:
        """Send *text* to every registered (or specified) channel."""
        targets = channels or list(self._channels.keys())
        return await self.send(text, channels=targets)

    # ------------------------------------------------------------------
    # Receiving
    # ------------------------------------------------------------------

    async def receive(self) -> AsyncIterator[IncomingMessage]:
        """
        Async generator that yields every incoming message across all channels.
        Messages are dispatched into an internal queue by the channel listeners.
        """
        while True:
            msg = await self._message_queue.get()
            yield msg

    async def _enqueue(self, msg: IncomingMessage) -> None:
        """Called by channel adapters to push inbound messages into the hub."""
        await self._message_queue.put(msg)

    # ------------------------------------------------------------------
    # Replying
    # ------------------------------------------------------------------

    async def reply(self, message_id: str, text: str, channel: ChannelType) -> bool:
        """Reply to a specific message by id on the given channel."""
        ch = self._channels.get(channel)
        if ch is None:
            logger.warning("Cannot reply — channel %s not registered.", channel.value)
            return False
        try:
            if hasattr(ch, "reply_to"):
                await ch.reply_to(message_id, text)
            else:
                await ch.send_message(message_id, text)
            return True
        except Exception as exc:
            logger.error("Reply failed on %s: %s", channel.value, exc)
            return False

    # ------------------------------------------------------------------
    # Intent routing
    # ------------------------------------------------------------------

    def set_handler(self, intent: Intent, handler_fn: Callable) -> None:
        """Register a handler for a specific detected intent."""
        self._handlers[intent] = handler_fn
        logger.debug("Registered handler for intent: %s", intent.value)

    def route(self, incoming: IncomingMessage) -> str:
        """
        Classify *incoming* message and dispatch to the appropriate handler.
        Returns the text response produced by the handler.
        """
        if self._router is None:
            from .message_router import MessageRouter
            self._router = MessageRouter()

        intent = self._router.detect_intent(incoming.text)
        entities = self._router.extract_entities(incoming.text)

        handler = self._handlers.get(intent)
        if handler:
            try:
                response = handler(intent, entities, incoming)
                return self._router.format_response(response, incoming.channel)
            except Exception as exc:
                logger.error("Handler for %s raised: %s", intent.value, exc)
                return "⚠️ An error occurred processing your request."

        # Fallback: delegate to router default
        return self._router.route_to_handler(intent, entities, incoming)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start_listening(self) -> None:
        """Start all registered channel listeners concurrently."""
        if self._running:
            logger.warning("ChannelHub is already running.")
            return

        self._running = True
        listener_tasks = []

        for ch_type, ch in self._channels.items():
            if hasattr(ch, "listen"):
                task = asyncio.create_task(
                    ch.listen(self._enqueue), name=f"listener-{ch_type.value}"
                )
                listener_tasks.append(task)
                logger.info("Started listener for %s", ch_type.value)

        if listener_tasks:
            await asyncio.gather(*listener_tasks, return_exceptions=True)

    async def stop_listening(self) -> None:
        """Gracefully stop all listeners."""
        self._running = False
        logger.info("ChannelHub stopped.")

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        """Return connection status for all registered channels."""
        result: Dict[str, Any] = {
            "running": self._running,
            "channels": {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        for ch_type, ch in self._channels.items():
            connected = getattr(ch, "connected", True)
            result["channels"][ch_type.value] = {
                "connected": connected,
                "has_config": ch_type in self._configs,
            }
        for ch_type in self._configs:
            if ch_type not in self._channels:
                result["channels"][ch_type.value] = {
                    "connected": False,
                    "has_config": True,
                    "note": "config registered but channel not initialised",
                }
        return result

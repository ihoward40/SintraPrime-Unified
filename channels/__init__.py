"""
SintraPrime-Unified — Multi-Channel Messaging Hub
Inspired by Manus AI, OpenClaw, Hermes Agent, Claude Code Channels, and ChatGPT Connected Apps
"""

from .channel_hub import ChannelHub
from .telegram_channel import TelegramChannel
from .discord_channel import DiscordChannel
from .slack_channel import SlackChannel
from .whatsapp_channel import WhatsAppChannel
from .webhook_channel import WebhookChannel
from .message_router import MessageRouter
from .message_types import (
    IncomingMessage,
    OutgoingMessage,
    ChannelType,
    Button,
    Attachment,
    MessageThread,
    ChannelConfig,
)

__all__ = [
    "ChannelHub",
    "TelegramChannel",
    "DiscordChannel",
    "SlackChannel",
    "WhatsAppChannel",
    "WebhookChannel",
    "MessageRouter",
    "IncomingMessage",
    "OutgoingMessage",
    "ChannelType",
    "Button",
    "Attachment",
    "MessageThread",
    "ChannelConfig",
]

__version__ = "1.0.0"
__author__ = "SintraPrime-Unified"

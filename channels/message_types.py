"""
Message data models for SintraPrime Multi-Channel Messaging Hub.
Defines all shared types used across Telegram, Discord, Slack, WhatsApp,
and Webhook channels.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ChannelType(str, Enum):
    """Supported messaging channel types."""

    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"
    WHATSAPP = "whatsapp"
    WEBHOOK = "webhook"
    EMAIL = "email"
    SMS = "sms"


class AttachmentType(str, Enum):
    """Types of file attachments."""

    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    VOICE = "voice"
    STICKER = "sticker"


class ParseMode(str, Enum):
    """Text formatting modes."""

    MARKDOWN = "Markdown"
    MARKDOWNV2 = "MarkdownV2"
    HTML = "HTML"
    PLAIN = "plain"


class Intent(str, Enum):
    """Detected message intents used by MessageRouter."""

    LEGAL_QUESTION = "legal_question"
    RESEARCH_REQUEST = "research_request"
    DOCUMENT_REQUEST = "document_request"
    TASK_MANAGEMENT = "task_management"
    GENERAL_CHAT = "general_chat"
    FINANCIAL_QUERY = "financial_query"
    STATUS_CHECK = "status_check"
    REMINDER = "reminder"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass
class Button:
    """Inline keyboard / interactive button."""

    text: str
    action: str  # callback_data key or URL
    data: Optional[str] = None  # arbitrary payload
    url: Optional[str] = None  # link button target

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "action": self.action,
            "data": self.data,
            "url": self.url,
        }


@dataclass
class Attachment:
    """File or media attachment."""

    type: AttachmentType
    url: str
    filename: Optional[str] = None
    size: Optional[int] = None  # bytes
    mime_type: Optional[str] = None
    thumbnail_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "url": self.url,
            "filename": self.filename,
            "size": self.size,
            "mime_type": self.mime_type,
        }


# ---------------------------------------------------------------------------
# Core message models
# ---------------------------------------------------------------------------


@dataclass
class IncomingMessage:
    """
    Normalised representation of a message received from any channel.
    Raw channel-specific data is preserved in *metadata*.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    channel: ChannelType = ChannelType.WEBHOOK
    user_id: str = ""
    text: str = ""
    attachments: List[Attachment] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Optional extras
    username: Optional[str] = None
    reply_to_id: Optional[str] = None
    thread_id: Optional[str] = None
    guild_id: Optional[str] = None  # Discord server id
    chat_id: Optional[str] = None   # Telegram chat id / Slack channel id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "channel": self.channel.value,
            "user_id": self.user_id,
            "text": self.text,
            "attachments": [a.to_dict() for a in self.attachments],
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "username": self.username,
            "reply_to_id": self.reply_to_id,
            "thread_id": self.thread_id,
            "chat_id": self.chat_id,
        }


@dataclass
class OutgoingMessage:
    """
    Message to be sent through one or more channels.
    The channel-specific adapters translate this into native payloads.
    """

    text: str
    channel: Optional[ChannelType] = None
    recipient: Optional[str] = None        # chat_id, channel_id, phone number …
    attachments: List[Attachment] = field(default_factory=list)
    parse_mode: ParseMode = ParseMode.MARKDOWN
    reply_to_id: Optional[str] = None
    buttons: List[List[Button]] = field(default_factory=list)  # rows of buttons
    embed: Optional[Dict[str, Any]] = None   # Discord embed / Slack blocks
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "channel": self.channel.value if self.channel else None,
            "recipient": self.recipient,
            "parse_mode": self.parse_mode.value,
            "reply_to_id": self.reply_to_id,
            "buttons": [[b.to_dict() for b in row] for row in self.buttons],
            "embed": self.embed,
        }


# ---------------------------------------------------------------------------
# Thread / history model
# ---------------------------------------------------------------------------


@dataclass
class MessageThread:
    """A conversation thread within a channel."""

    channel: ChannelType
    thread_id: str
    messages: List[IncomingMessage] = field(default_factory=list)
    title: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def add_message(self, msg: IncomingMessage) -> None:
        self.messages.append(msg)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel": self.channel.value,
            "thread_id": self.thread_id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "messages": [m.to_dict() for m in self.messages],
        }


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class ChannelConfig:
    """Runtime configuration for a single messaging channel."""

    token: Optional[str] = None
    webhook_url: Optional[str] = None
    app_id: Optional[str] = None
    app_secret: Optional[str] = None
    allowed_users: List[str] = field(default_factory=list)   # whitelist
    admin_users: List[str] = field(default_factory=list)
    max_message_length: int = 4096
    rate_limit_per_minute: int = 60
    webhook_secret: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def is_user_allowed(self, user_id: str) -> bool:
        if not self.allowed_users:
            return True  # open if no whitelist configured
        return user_id in self.allowed_users

    def is_admin(self, user_id: str) -> bool:
        return user_id in self.admin_users

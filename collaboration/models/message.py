"""ChannelMessage — durable channel message model (§LI)."""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import ContentType


@dataclass
class MessageContent:
    content_type: ContentType = ContentType.TEXT
    text: str = ""
    artifact_id: str = ""
    workflow_run_id: str = ""
    data: dict = field(default_factory=dict)


@dataclass
class ChannelMessage:
    id: str
    tenant_id: str
    channel_id: str
    author_type: str = "human"
    author_id: str = ""
    content: MessageContent = field(default_factory=MessageContent)
    reply_to: str = ""
    thread_id: str = ""
    created_at: str = ""
    correlation_id: str = ""
    origin_event_id: str = ""
    origin_activation_id: str = ""

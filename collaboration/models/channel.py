"""CollaborationChannel — persistent governed operational space."""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import ChannelStatus, ChannelType, ChannelVisibility


@dataclass
class CollaborationChannel:
    id: str
    tenant_id: str
    name: str
    slug: str
    description: str = ""
    channel_type: ChannelType = ChannelType.PRIVATE
    visibility: ChannelVisibility = ChannelVisibility.TENANT
    status: ChannelStatus = ChannelStatus.ACTIVE
    created_by: str = ""
    created_at: str = ""
    updated_at: str = ""
    max_message_history: int = 10000
    metadata: dict = field(default_factory=dict)

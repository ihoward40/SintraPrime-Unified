"""ChannelMembership — who participates in which channel."""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import ActorType, MembershipRole, MembershipStatus


@dataclass
class ChannelMembership:
    id: str
    channel_id: str
    tenant_id: str
    principal_id: str
    principal_type: ActorType = ActorType.HUMAN
    role: MembershipRole = MembershipRole.CONTRIBUTOR
    status: MembershipStatus = MembershipStatus.ACTIVE
    joined_at: str = ""
    left_at: str = ""
    metadata: dict = field(default_factory=dict)

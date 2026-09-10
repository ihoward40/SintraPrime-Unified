"""MembershipService — channel membership management (§V)."""

from __future__ import annotations

from datetime import UTC, datetime

from collaboration.models import ChannelMembership
from collaboration.models.enums import ActorType, MembershipRole, MembershipStatus
from collaboration.services.store import CollaborationStore


class MembershipService:
    def __init__(self, store: CollaborationStore):
        self.store = store

    def join(
        self,
        *,
        channel_id: str,
        tenant_id: str,
        principal_id: str,
        principal_type: ActorType = ActorType.HUMAN,
        role: MembershipRole = MembershipRole.CONTRIBUTOR,
    ) -> ChannelMembership:
        m = ChannelMembership(
            id=f"mem_{principal_id}_{channel_id}",
            channel_id=channel_id,
            tenant_id=tenant_id,
            principal_id=principal_id,
            principal_type=principal_type,
            role=role,
            joined_at=datetime.now(UTC).isoformat(),
        )
        self.store.save("memberships", m.id, m)
        return m

    def leave(self, membership_id: str) -> ChannelMembership | None:
        m = self.store.load("memberships", membership_id, ChannelMembership)
        if m is None:
            return None
        m.status = MembershipStatus.LEFT
        m.left_at = datetime.now(UTC).isoformat()
        self.store.save("memberships", m.id, m)
        return m

    def get(self, membership_id: str) -> ChannelMembership | None:
        return self.store.load("memberships", membership_id, ChannelMembership)

    def get_active(self, channel_id: str) -> list[ChannelMembership]:
        return [
            m
            for m in self.store.load_many("memberships", ChannelMembership)
            if m.channel_id == channel_id and m.status == MembershipStatus.ACTIVE
        ]

    def role_of(self, channel_id: str, principal_id: str) -> MembershipRole | None:
        for m in self.get_active(channel_id):
            if m.principal_id == principal_id:
                return m.role
        return None

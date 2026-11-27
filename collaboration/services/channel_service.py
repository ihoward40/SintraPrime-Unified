"""ChannelService — CRUD for CollaborationChannel (§III)."""

from __future__ import annotations

from datetime import UTC, datetime

from collaboration.models import CollaborationChannel
from collaboration.models.enums import ChannelStatus, ChannelType, ChannelVisibility
from collaboration.services.store import CollaborationStore


class ChannelService:
    def __init__(self, store: CollaborationStore):
        self.store = store

    def create(
        self,
        *,
        tenant_id: str,
        name: str,
        slug: str,
        channel_type: ChannelType = ChannelType.PRIVATE,
        visibility: ChannelVisibility = ChannelVisibility.TENANT,
        description: str = "",
        created_by: str = "",
    ) -> CollaborationChannel:
        ch = CollaborationChannel(
            id=f"ch_{slug}_{tenant_id}",
            tenant_id=tenant_id,
            name=name,
            slug=slug,
            description=description,
            channel_type=channel_type,
            visibility=visibility,
            created_by=created_by,
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        self.store.save("channels", ch.id, ch)
        return ch

    def get(self, channel_id: str) -> CollaborationChannel | None:
        return self.store.load("channels", channel_id, CollaborationChannel)

    def list_by_tenant(self, tenant_id: str) -> list[CollaborationChannel]:
        return [
            ch
            for ch in self.store.load_many("channels", CollaborationChannel)
            if ch.tenant_id == tenant_id
        ]

    def activate_kill_switch(self, channel_id: str) -> CollaborationChannel | None:
        ch = self.get(channel_id)
        if ch is None:
            return None
        ch.status = ChannelStatus.SUSPENDED
        ch.updated_at = datetime.now(UTC).isoformat()
        self.store.save("channels", ch.id, ch)
        return ch

    def deactivate_kill_switch(self, channel_id: str) -> CollaborationChannel | None:
        ch = self.get(channel_id)
        if ch is None:
            return None
        ch.status = ChannelStatus.ACTIVE
        ch.updated_at = datetime.now(UTC).isoformat()
        self.store.save("channels", ch.id, ch)
        return ch

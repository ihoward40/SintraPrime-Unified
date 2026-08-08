"""Capability leases (§108, §140)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from collaboration.services.store import CollaborationStore


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class CapabilityLease:
    """Ephemeral scoped capability grant (§108)."""

    lease_id: str
    agent_id: str
    capability: str
    scope: str
    purpose: str
    issued_at: str = field(default_factory=_now)
    expires_at: str = ""
    workflow_id: str = ""
    revoked: bool = False

    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        try:
            exp = datetime.fromisoformat(self.expires_at)
            return datetime.now(UTC) > exp
        except ValueError:
            return True


class LeaseService:
    """Issue, validate, revoke capability leases. Nothing permanent."""

    def __init__(self, store: CollaborationStore, *, default_ttl_minutes: int = 60):
        self.store = store
        self.default_ttl_minutes = default_ttl_minutes

    def issue(
        self,
        *,
        lease_id: str,
        agent_id: str,
        capability: str,
        scope: str,
        purpose: str,
        workflow_id: str = "",
        ttl_minutes: int | None = None,
    ) -> CapabilityLease:
        ttl = ttl_minutes if ttl_minutes is not None else self.default_ttl_minutes
        expires = (datetime.now(UTC) + timedelta(minutes=ttl)).isoformat()
        lease = CapabilityLease(
            lease_id=lease_id,
            agent_id=agent_id,
            capability=capability,
            scope=scope,
            purpose=purpose,
            expires_at=expires,
            workflow_id=workflow_id,
        )
        self.store.save("leases", lease_id, lease)
        return lease

    def get(self, lease_id: str) -> CapabilityLease | None:
        return self.store.load("leases", lease_id, CapabilityLease)

    def validate(
        self, lease_id: str, *, capability: str, scope: str, purpose: str
    ) -> tuple[bool, str]:
        """§140: expired lease rejected; wrong-purpose rejected; wrong-scope rejected."""
        lease = self.get(lease_id)
        if lease is None:
            return False, "lease_not_found"
        if lease.revoked:
            return False, "lease_revoked"
        if lease.is_expired():
            return False, "lease_expired"
        if lease.capability != capability:
            return False, f"capability_mismatch (lease={lease.capability}, request={capability})"
        if lease.scope != scope:
            return False, f"scope_mismatch (lease={lease.scope}, request={scope})"
        if lease.purpose != purpose:
            return False, f"purpose_mismatch (lease={lease.purpose}, request={purpose})"
        return True, "valid"

    def revoke(self, lease_id: str, *, revoked_by: str = "") -> CapabilityLease | None:
        del revoked_by
        lease = self.get(lease_id)
        if lease is None:
            return None
        lease.revoked = True
        self.store.save("leases", lease_id, lease)
        return lease

    def list_for_agent(self, agent_id: str) -> list[CapabilityLease]:
        return [
            lease
            for lease in self.store.load_many("leases", CapabilityLease)
            if lease.agent_id == agent_id
        ]

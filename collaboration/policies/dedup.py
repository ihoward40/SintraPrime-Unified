"""DeduplicationPolicy — event consumption keys (§XI, §LVI)."""

from __future__ import annotations

import hashlib

from collaboration.models import EventEnvelope


class DeduplicationPolicy:
    """Prevent repeated responses to identical events.

    consumption_key = hash(agent_id + event_id + policy_version).
    """

    def __init__(self, policy_version: str = "1"):
        self.policy_version = policy_version
        self._consumed: set[str] = set()

    @staticmethod
    def consumption_key(agent_id: str, event_id: str, policy_version: str) -> str:
        raw = f"{agent_id}:{event_id}:{policy_version}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    def key_for(self, event: EventEnvelope, agent_id: str) -> str:
        return self.consumption_key(agent_id, event.event_id, self.policy_version)

    def is_consumed(self, event: EventEnvelope, agent_id: str) -> bool:
        return self.key_for(event, agent_id) in self._consumed

    def mark_consumed(self, event: EventEnvelope, agent_id: str) -> str:
        key = self.key_for(event, agent_id)
        self._consumed.add(key)
        return key

    def reentry_allowed(self, event: EventEnvelope, agent_id: str) -> bool:
        """Re-entry protection: a re-join must NOT retrigger already-consumed events."""
        return not self.is_consumed(event, agent_id)

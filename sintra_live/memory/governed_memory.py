"""Governed memory retrieval for offline integration."""

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class MemoryTrust(Enum):
    """Trust labels for governed memory."""
    GOVERNED_FACT = "GOVERNED_FACT"
    PRINCIPAL_PREFERENCE = "PRINCIPAL_PREFERENCE"
    WORKING_CONTEXT = "WORKING_CONTEXT"
    UNTRUSTED_EXTERNAL = "UNTRUSTED_EXTERNAL"


@dataclass(frozen=True)
class MemoryItem:
    """Immutable memory item with provenance."""
    key: str
    value: Any
    trust: MemoryTrust
    source: str
    timestamp: float
    provenance_hash: str = ""
    scope: str = ""

    def __post_init__(self):
        if not self.provenance_hash:
            content = f"{self.key}|{json.dumps(self.value, sort_keys=True)}|{self.trust.value}|{self.source}|{self.timestamp}"
            object.__setattr__(self, 'provenance_hash', hashlib.sha256(content.encode()).hexdigest())


class GovernedMemory:
    """Governed memory store with provenance and trust labels."""

    FIXTURES = {
        "status_briefing": MemoryItem(
            key="status_briefing",
            value={
                "active_matters": 3,
                "informational": 2,
                "requires_approval": 1,
                "last_updated": "2026-08-21T10:00:00Z"
            },
            trust=MemoryTrust.GOVERNED_FACT,
            source="mission_control.status",
            timestamp=time.time(),
            scope="governed_status_briefing"
        ),
        "principal_preference_briefing_style": MemoryItem(
            key="principal_preference_briefing_style",
            value={"format": "conversational", "detail_level": "summary_first", "voice": True},
            trust=MemoryTrust.PRINCIPAL_PREFERENCE,
            source="principal.preferences",
            timestamp=time.time(),
            scope="governed_status_briefing"
        ),
        "safe_action_template": MemoryItem(
            key="safe_action_template",
            value={"type": "mock_status_update", "target": "status_dashboard", "action": "update_last_briefing_time"},
            trust=MemoryTrust.GOVERNED_FACT,
            source="capability_catalog",
            timestamp=time.time(),
            scope="governed_status_briefing"
        ),
    }

    def __init__(self):
        self.store = dict(self.FIXTURES)

    def retrieve(self, scope: str, trust_filter: Optional[List[MemoryTrust]] = None) -> List[MemoryItem]:
        """Retrieve memory items within scope and trust filter."""
        results = []
        for item in self.store.values():
            if item.scope == scope:
                if trust_filter is None or item.trust in trust_filter:
                    results.append(item)
        return results

    def get(self, key: str) -> Optional[MemoryItem]:
        return self.store.get(key)

    def get_provenance(self, key: str) -> Optional[str]:
        item = self.store.get(key)
        return item.provenance_hash if item else None

    def list_scopes(self) -> List[str]:
        scopes = set()
        for item in self.store.values():
            scopes.add(item.scope)
        return list(scopes)
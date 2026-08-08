"""Uncertainty registry and assumption ledger (§66-67)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from collaboration.services.store import CollaborationStore


def _now() -> str:
    return datetime.now(UTC).isoformat()


class UncertaintyType(str):
    UNKNOWN = "unknown"
    ASSUMPTION = "assumption"
    DISPUTED_FACT = "disputed_fact"
    MISSING_EVIDENCE = "missing_evidence"
    UNVERIFIED_DEPENDENCY = "unverified_dependency"
    IMPLEMENTATION_RISK = "implementation_risk"


@dataclass
class UncertaintyItem:
    """Persisted until resolved (§66)."""

    id: str
    uncertainty_type: str
    description: str
    source: str = ""
    created_at: str = field(default_factory=_now)
    resolved: bool = False
    resolved_at: str = ""
    resolution: str = ""


@dataclass
class Assumption:
    id: str
    assumption: str
    source: str
    owner: str
    status: str = "ACTIVE"  # ACTIVE | CONFIRMED | INVALIDATED | SUPERSEDED
    dependencies: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)


class UncertaintyRegistry:
    def __init__(self, store: CollaborationStore):
        self.store = store

    def register(self, item: UncertaintyItem) -> UncertaintyItem:
        self.store.save("uncertainties", item.id, item)
        return item

    def resolve(self, item_id: str, resolution: str) -> UncertaintyItem | None:
        item = self.store.load("uncertainties", item_id, UncertaintyItem)
        if item is None:
            return None
        item.resolved = True
        item.resolved_at = _now()
        item.resolution = resolution
        self.store.save("uncertainties", item_id, item)
        return item

    def list_open(self) -> list[UncertaintyItem]:
        return [u for u in self.store.load_many("uncertainties", UncertaintyItem) if not u.resolved]


class AssumptionLedger:
    def __init__(self, store: CollaborationStore):
        self.store = store

    def register(self, assumption: Assumption) -> Assumption:
        self.store.save("assumptions", assumption.id, assumption)
        return assumption

    def confirm(self, assumption_id: str) -> Assumption | None:
        a = self.store.load("assumptions", assumption_id, Assumption)
        if a is None:
            return None
        a.status = "CONFIRMED"
        self.store.save("assumptions", assumption_id, a)
        return a

    def invalidate(self, assumption_id: str) -> Assumption | None:
        a = self.store.load("assumptions", assumption_id, Assumption)
        if a is None:
            return None
        a.status = "INVALIDATED"
        self.store.save("assumptions", assumption_id, a)
        return a

    def list_active(self) -> list[Assumption]:
        return [a for a in self.store.load_many("assumptions", Assumption) if a.status == "ACTIVE"]

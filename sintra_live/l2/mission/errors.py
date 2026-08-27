"""Fail-closed result and error types for the L2-I1 mission store."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Optional


class TransitionOutcome(str, Enum):
    APPLIED = "APPLIED"
    REPLAYED = "REPLAYED"
    DENIED = "DENIED"


class DenialCode(str, Enum):
    INVALID_SCHEMA = "INVALID_SCHEMA"
    NONCANONICAL = "NONCANONICAL"
    MISSION_COLLISION = "MISSION_COLLISION"
    MISSION_NOT_FOUND = "MISSION_NOT_FOUND"
    LOCK_TIMEOUT = "LOCK_TIMEOUT"
    CAS_CONFLICT = "CAS_CONFLICT"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    INVALID_TRANSITION = "INVALID_TRANSITION"
    IMMUTABLE_FIELD_CHANGE = "IMMUTABLE_FIELD_CHANGE"
    TERMINAL_STATE = "TERMINAL_STATE"
    INTEGRITY_FAILURE = "INTEGRITY_FAILURE"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    PERSISTENCE_FAILURE = "PERSISTENCE_FAILURE"


class MissionStoreError(Exception):
    """Base fail-closed store exception."""


class SchemaError(MissionStoreError):
    pass


class IntegrityError(MissionStoreError):
    pass


class LockTimeoutError(MissionStoreError):
    pass


class PersistenceError(MissionStoreError):
    pass


@dataclass(frozen=True)
class TransitionResult:
    outcome: TransitionOutcome
    mission_id: str
    code: Optional[DenialCode]
    reason: str
    version: int
    state: str
    event_sha256: str
    aggregate_sha256: str
    details: Mapping[str, Any]

    @property
    def applied(self) -> bool:
        return self.outcome is TransitionOutcome.APPLIED

    @property
    def replayed(self) -> bool:
        return self.outcome is TransitionOutcome.REPLAYED

    @property
    def denied(self) -> bool:
        return self.outcome is TransitionOutcome.DENIED

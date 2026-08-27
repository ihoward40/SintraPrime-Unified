"""L2-I7B PrincipalApprovalRecord contract — single-use, envelope-hash-bound, zero authority.

Implements the frozen I7B design amendment schema:
  SP-LIVE-001:L2-I7B:PRINCIPAL-APPROVAL:V1

No execution authority, no capability resolution, no credential access.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Tuple

from sintra_live.l2.mission.model import canonical_bytes

SCHEMA_VERSION = "sp-live-001-l2-i7b-principal-approval-v1"
APPROVAL_VERSION = "v1"
HASH_DOMAIN = b"SP-LIVE-001:L2-I7B:PRINCIPAL-APPROVAL:V1\x00"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")
MAX = 2**63 - 1


class ApprovalResult(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    INVALIDATED = "INVALIDATED"
    CONSUMED = "CONSUMED"
    CONSUMPTION_AMBIGUOUS = "CONSUMPTION_AMBIGUOUS"


class ApprovalState(str, Enum):
    PROPOSED = "PROPOSED"
    DISCLOSED = "DISCLOSED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    INVALIDATED = "INVALIDATED"
    CONSUMPTION_PENDING = "CONSUMPTION_PENDING"
    CONSUMED = "CONSUMED"
    CONSUMPTION_AMBIGUOUS = "CONSUMPTION_AMBIGUOUS"


TERMINAL_STATES = frozenset({
    ApprovalState.REJECTED,
    ApprovalState.EXPIRED,
    ApprovalState.INVALIDATED,
    ApprovalState.CONSUMED,
    ApprovalState.CONSUMPTION_AMBIGUOUS,
})

VALID_TRANSITIONS: dict[ApprovalState, frozenset] = {
    ApprovalState.PROPOSED: frozenset({ApprovalState.DISCLOSED}),
    ApprovalState.DISCLOSED: frozenset({ApprovalState.APPROVAL_REQUIRED}),
    ApprovalState.APPROVAL_REQUIRED: frozenset({
        ApprovalState.APPROVED,
        ApprovalState.REJECTED,
        ApprovalState.EXPIRED,
        ApprovalState.INVALIDATED,
    }),
    ApprovalState.APPROVED: frozenset({
        ApprovalState.CONSUMPTION_PENDING,
        ApprovalState.EXPIRED,
        ApprovalState.INVALIDATED,
    }),
    ApprovalState.CONSUMPTION_PENDING: frozenset({
        ApprovalState.CONSUMED,
        ApprovalState.CONSUMPTION_AMBIGUOUS,
    }),
}


def _iv(x: Any) -> int:
    if isinstance(x, bool) or not isinstance(x, int) or not 0 <= x <= MAX:
        raise ValueError("INVALID_INTEGER")
    return x


def _ts(x: str) -> str:
    if not isinstance(x, str) or not TIMESTAMP_RE.match(x):
        raise ValueError("INVALID_TIME")
    return x


def _sha(x: str) -> str:
    if not isinstance(x, str) or not SHA256_RE.match(x):
        raise ValueError("INVALID_SHA256")
    return x


def _id(x: str) -> str:
    if not isinstance(x, str) or not re.match(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$", x):
        raise ValueError("INVALID_IDENTIFIER")
    return x


def _body(obj: Any, own: str) -> dict:
    d = asdict(obj)
    d.pop(own, None)
    for k, v in tuple(d.items()):
        if isinstance(v, Enum):
            d[k] = v.value
        elif isinstance(v, tuple):
            d[k] = [i.value if isinstance(i, Enum) else i for i in v]
    return d


def _seal(obj: Any, own: str) -> None:
    body = _body(obj, own)
    h = hashlib.sha256(HASH_DOMAIN + canonical_bytes(body)).hexdigest()
    old = getattr(obj, own)
    if old and old != h:
        raise ValueError("HASH_MISMATCH")
    object.__setattr__(obj, own, h)


@dataclass(frozen=True)
class PrincipalApprovalRecord:
    """Immutable single-use approval record bound to exact ActionEnvelope hash."""

    schema_version: str
    approval_version: str
    approval_id: str
    program_id: str
    gate_id: str
    mission_id: str
    request_sha256: str
    principal_identity_reference: str
    principal_session_id: str
    authentication_method: str
    authentication_timestamp: str
    action_envelope_sha256: str
    approval_nonce: str
    approval_disclosure_sha256: str
    approval_phrase_or_decision_sha256: str
    approval_result: str
    maximum_executions: int
    issued_at: str
    valid_from: str
    valid_until: str
    consumed_execution_id: str
    consumed_at: str
    prior_ledger_entry_sha256: str
    approval_record_sha256: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("INVALID_SCHEMA_VERSION")
        if self.approval_version != APPROVAL_VERSION:
            raise ValueError("INVALID_APPROVAL_VERSION")
        for n in ("approval_id", "program_id", "gate_id", "mission_id",
                   "principal_identity_reference", "principal_session_id",
                   "authentication_method", "approval_nonce"):
            _id(getattr(self, n))
        for n in ("request_sha256", "action_envelope_sha256", "approval_disclosure_sha256",
                   "approval_phrase_or_decision_sha256", "prior_ledger_entry_sha256"):
            _sha(getattr(self, n))
        _iv(self.maximum_executions)
        if self.maximum_executions != 1:
            raise ValueError("MAXIMUM_EXECUTIONS_MUST_BE_ONE")
        if self.approval_result not in ("APPROVED", "REJECTED", "EXPIRED", "INVALIDATED",
                                         "CONSUMED", "CONSUMPTION_AMBIGUOUS"):
            raise ValueError("INVALID_APPROVAL_RESULT")
        for n in ("authentication_timestamp", "issued_at", "valid_from", "valid_until"):
            _ts(getattr(self, n))
        if self.valid_from >= self.valid_until:
            raise ValueError("INVALID_VALIDITY_WINDOW")
        if not isinstance(self.consumed_execution_id, str):
            raise ValueError("INVALID_CONSUMED_EXECUTION_ID")
        if not isinstance(self.consumed_at, str):
            raise ValueError("INVALID_CONSUMED_AT")
        _seal(self, "approval_record_sha256")

    def body(self) -> dict:
        return _body(self, "approval_record_sha256")

    def to_dict(self) -> dict:
        return {**self.body(), "approval_record_sha256": self.approval_record_sha256}


def validate_transition(from_state: ApprovalState, to_state: ApprovalState) -> bool:
    """Check whether a ledger transition is permitted."""
    if from_state in TERMINAL_STATES:
        return False
    return to_state in VALID_TRANSITIONS.get(from_state, frozenset())


__all__ = [
    "PrincipalApprovalRecord",
    "ApprovalResult",
    "ApprovalState",
    "TERMINAL_STATES",
    "VALID_TRANSITIONS",
    "validate_transition",
    "SCHEMA_VERSION",
    "APPROVAL_VERSION",
    "HASH_DOMAIN",
]
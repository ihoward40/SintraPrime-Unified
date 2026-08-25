"""L2-I7B canonical ActionEnvelope contract — immutable, hash-bound, zero authority.

Implements the frozen I7B design amendment schema:
  SP-LIVE-001:L2-I7B:ACTION-ENVELOPE:V1

No execution authority, no credential access, no side effects.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Tuple

from sintra_live.l2.mission.model import canonical_bytes

SCHEMA_VERSION = "sp-live-001-l2-i7b-action-envelope-v1"
ENVELOPE_VERSION = "v1"
HASH_DOMAIN = b"SP-LIVE-001:L2-I7B:ACTION-ENVELOPE:V1\x00"
CONSEQUENCE_ORDER = (
    "READ_ONLY",
    "REVERSIBLE_INTERNAL",
    "SCOPED_WRITE",
    "EXTERNAL_COMMUNICATION",
    "FINANCIAL",
    "PRODUCTION",
    "LEGAL",
    "SECURITY_SENSITIVE",
    "GOVERNANCE_PROTECTED",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")
MAX = 2**63 - 1


class ConsequenceClass(str, Enum):
    READ_ONLY = "READ_ONLY"
    REVERSIBLE_INTERNAL = "REVERSIBLE_INTERNAL"
    SCOPED_WRITE = "SCOPED_WRITE"
    EXTERNAL_COMMUNICATION = "EXTERNAL_COMMUNICATION"
    FINANCIAL = "FINANCIAL"
    PRODUCTION = "PRODUCTION"
    LEGAL = "LEGAL"
    SECURITY_SENSITIVE = "SECURITY_SENSITIVE"
    GOVERNANCE_PROTECTED = "GOVERNANCE_PROTECTED"


class ProviderMode(str, Enum):
    LIVE = "LIVE"
    MOCK = "MOCK"
    DRY_RUN = "DRY_RUN"


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


def _ref(x: str) -> str:
    """Non-empty string reference (endpoint, destination, etc.)."""
    if not isinstance(x, str) or not x.strip():
        raise ValueError("INVALID_REFERENCE")
    return x


def _ss(x: tuple) -> tuple:
    x = tuple(x)
    if len(x) != len(set(x)):
        raise ValueError("NONCANONICAL_INPUT")
    return x


def _sorted(x: tuple) -> tuple:
    return tuple(sorted(set(x)))


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
class ActionEnvelope:
    """Immutable canonical action envelope binding exact mission, authority,
    capability, provider, baseline, and execution-identity fields."""

    schema_version: str
    envelope_version: str
    program_id: str
    gate_id: str
    mission_id: str
    request_sha256: str
    mission_scope_sha256: str
    aggregate_version: int
    aggregate_sha256: str
    principal_identity_reference: str
    principal_session_id: str
    policy_decision_sha256: str
    authority_resolution_sha256: str
    authority_snapshot_sha256: str
    capability_id: str
    capability_version: str
    adapter_id: str
    adapter_version: str
    canonical_entrypoint: str
    provider_class: str
    provider_mode: str
    provider_account_reference: str
    credential_boundary_reference: str
    operation_type: str
    http_method: str
    endpoint_or_operation_reference: str
    destination_class: str
    destination_reference: str
    parameters_sha256: str
    body_sha256: str
    expected_baseline_sha256: str
    baseline_commit_sha: str
    baseline_tree_sha: str
    execution_source_manifest_sha256: str
    execution_id: str
    nonce: str
    maximum_executions: int
    side_effect_ceiling: int
    cost_ceiling: int
    token_ceiling: int
    latency_ceiling_ms: int
    consequence_class: str
    required_evidence_types: Tuple[str, ...]
    issued_at: str
    valid_from: str
    valid_until: str
    previous_governance_evidence_sha256: str
    action_envelope_sha256: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("INVALID_SCHEMA_VERSION")
        if self.envelope_version != ENVELOPE_VERSION:
            raise ValueError("INVALID_ENVELOPE_VERSION")
        for n in ("program_id", "gate_id", "mission_id", "principal_identity_reference",
                   "principal_session_id", "capability_id", "capability_version",
                   "adapter_id", "adapter_version", "canonical_entrypoint",
                   "provider_class", "provider_account_reference",
                   "credential_boundary_reference", "operation_type", "http_method",
                   "execution_id", "nonce"):
            _id(getattr(self, n))
        for n in ("endpoint_or_operation_reference", "destination_class",
                   "destination_reference"):
            _ref(getattr(self, n))
        for n in ("request_sha256", "mission_scope_sha256", "aggregate_sha256",
                   "policy_decision_sha256", "authority_resolution_sha256",
                   "authority_snapshot_sha256", "parameters_sha256", "body_sha256",
                   "expected_baseline_sha256", "baseline_commit_sha", "baseline_tree_sha",
                   "execution_source_manifest_sha256", "previous_governance_evidence_sha256"):
            _sha(getattr(self, n))
        _iv(self.aggregate_version)
        for n in ("maximum_executions", "side_effect_ceiling", "cost_ceiling",
                   "token_ceiling", "latency_ceiling_ms"):
            _iv(getattr(self, n))
        if self.maximum_executions != 1:
            raise ValueError("MAXIMUM_EXECUTIONS_MUST_BE_ONE")
        if self.provider_mode not in ("LIVE", "MOCK", "DRY_RUN"):
            raise ValueError("INVALID_PROVIDER_MODE")
        if self.consequence_class not in CONSEQUENCE_ORDER:
            raise ValueError("INVALID_CONSEQUENCE_CLASS")
        object.__setattr__(self, "required_evidence_types", _sorted(self.required_evidence_types))
        for n in ("issued_at", "valid_from", "valid_until"):
            _ts(getattr(self, n))
        if self.valid_from >= self.valid_until:
            raise ValueError("INVALID_VALIDITY_WINDOW")
        _seal(self, "action_envelope_sha256")

    def body(self) -> dict:
        return _body(self, "action_envelope_sha256")

    def to_dict(self) -> dict:
        return {**self.body(), "action_envelope_sha256": self.action_envelope_sha256}


__all__ = [
    "ActionEnvelope",
    "ConsequenceClass",
    "ProviderMode",
    "SCHEMA_VERSION",
    "ENVELOPE_VERSION",
    "HASH_DOMAIN",
    "CONSEQUENCE_ORDER",
]
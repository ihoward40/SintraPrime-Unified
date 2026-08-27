"""L2-I8 capability registry contract — exact lookup, zero authority, zero execution.

Implements the frozen I8 design:
  Exact capability registry with immutable entries and exact lookup only.
  CanonicalCapabilityExecutor interface contract.
  No alias expansion, no execution authority, no credential access.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from sintra_live.l2.mission.model import canonical_bytes

SCHEMA_VERSION = "sp-live-001-l2-i8-capability-registry-v1"
HASH_DOMAIN = b"SP-LIVE-001:L2-I8:CAPABILITY-REGISTRY:V1\x00"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
MAX = 2**63 - 1


class ResolutionResult(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    INCOMPLETE = "INCOMPLETE"


class DenyReason(str, Enum):
    UNKNOWN_CAPABILITY = "UNKNOWN_CAPABILITY"
    CAPABILITY_ALIAS = "CAPABILITY_ALIAS"
    DEPRECATED_CAPABILITY = "DEPRECATED_CAPABILITY"
    ADAPTER_MISMATCH = "ADAPTER_MISMATCH"
    ENTRYPOINT_MISMATCH = "ENTRYPOINT_MISMATCH"
    PROVIDER_CLASS_MISMATCH = "PROVIDER_CLASS_MISMATCH"
    PROVIDER_MODE_MISMATCH = "PROVIDER_MODE_MISMATCH"
    ACCOUNT_MISMATCH = "ACCOUNT_MISMATCH"
    CREDENTIAL_BOUNDARY_MISMATCH = "CREDENTIAL_BOUNDARY_MISMATCH"
    MISSING_EXECUTION_ID = "MISSING_EXECUTION_ID"
    MISSING_NONCE = "MISSING_NONCE"
    EXECUTION_ID_MISMATCH = "EXECUTION_ID_MISMATCH"
    NONCE_MISMATCH = "NONCE_MISMATCH"
    EXECUTION_ID_AUTOGENERATION = "EXECUTION_ID_AUTOGENERATION"
    NONCE_AUTOGENERATION = "NONCE_AUTOGENERATION"
    MOCK_FALLBACK = "MOCK_FALLBACK"
    BASELINE_COMMIT_MISMATCH = "BASELINE_COMMIT_MISMATCH"
    BASELINE_TREE_MISMATCH = "BASELINE_TREE_MISMATCH"
    SOURCE_MANIFEST_MISMATCH = "SOURCE_MANIFEST_MISMATCH"
    TARGET_CLOSED = "TARGET_CLOSED"
    TARGET_MISSING = "TARGET_MISSING"
    DUPLICATE_TARGET = "DUPLICATE_TARGET"
    KILL_SWITCH = "KILL_SWITCH"
    CANCELLATION = "CANCELLATION"
    MISSING_APPROVAL = "MISSING_APPROVAL"
    EXPIRED_APPROVAL = "EXPIRED_APPROVAL"
    CONSUMED_APPROVAL = "CONSUMED_APPROVAL"
    AUTHORITY_MISMATCH = "AUTHORITY_MISMATCH"
    SIDE_EFFECT_CEILING_EXCEEDED = "SIDE_EFFECT_CEILING_EXCEEDED"
    AMBIGUOUS_MATCH = "AMBIGUOUS_MATCH"
    INVALID_INPUT = "INVALID_INPUT"


def _id(x: str) -> str:
    if not isinstance(x, str) or not ID_RE.match(x):
        raise ValueError("INVALID_IDENTIFIER")
    return x


def _sha(x: str) -> str:
    if not isinstance(x, str) or not SHA256_RE.match(x):
        raise ValueError("INVALID_SHA256")
    return x


def _iv(x: Any) -> int:
    if isinstance(x, bool) or not isinstance(x, int) or not 0 <= x <= MAX:
        raise ValueError("INVALID_INTEGER")
    return x


def _ref(x: str) -> str:
    if not isinstance(x, str) or not x.strip():
        raise ValueError("INVALID_REFERENCE")
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
class CapabilityRegistryEntry:
    """Immutable certified capability registry entry. Exact lookup only."""
    schema_version: str
    entry_version: str
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
    consequence_class: str
    certified: bool
    deprecated: bool
    capability_entry_sha256: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("INVALID_SCHEMA_VERSION")
        for n in ("capability_id", "capability_version", "adapter_id",
                   "adapter_version", "canonical_entrypoint", "provider_class",
                   "provider_account_reference", "credential_boundary_reference",
                   "operation_type", "http_method"):
            _id(getattr(self, n))
        for n in ("endpoint_or_operation_reference", "destination_class"):
            _ref(getattr(self, n))
        if self.consequence_class not in ("READ_ONLY", "REVERSIBLE_INTERNAL",
                "SCOPED_WRITE", "EXTERNAL_COMMUNICATION", "FINANCIAL",
                "PRODUCTION", "LEGAL", "SECURITY_SENSITIVE", "GOVERNANCE_PROTECTED"):
            raise ValueError("INVALID_CONSEQUENCE_CLASS")
        if self.provider_mode not in ("LIVE", "MOCK", "DRY_RUN"):
            raise ValueError("INVALID_PROVIDER_MODE")
        if not isinstance(self.certified, bool):
            raise ValueError("INVALID_CERTIFIED")
        if not isinstance(self.deprecated, bool):
            raise ValueError("INVALID_DEPRECATED")
        _seal(self, "capability_entry_sha256")

    def body(self) -> dict:
        return _body(self, "capability_entry_sha256")

    def to_dict(self) -> dict:
        return {**self.body(), "capability_entry_sha256": self.capability_entry_sha256}


@dataclass(frozen=True)
class CapabilityLookupRequest:
    """Exact lookup request — no fuzzy matching."""
    schema_version: str
    capability_id: str
    capability_version: str
    adapter_id: str
    adapter_version: str
    canonical_entrypoint: str
    lookup_request_sha256: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("INVALID_SCHEMA_VERSION")
        for n in ("capability_id", "capability_version", "adapter_id",
                   "adapter_version", "canonical_entrypoint"):
            _id(getattr(self, n))
        h = hashlib.sha256(
            HASH_DOMAIN + canonical_bytes(_body(self, "lookup_request_sha256"))
        ).hexdigest()
        object.__setattr__(self, "lookup_request_sha256", h)


@dataclass(frozen=True)
class CapabilityResolutionRecord:
    """Deterministic capability resolution result — zero authority delta."""
    schema_version: str
    resolution_id: str
    capability_id: str
    capability_version: str
    result: str
    deny_reason: str
    matched_entry_sha256: str
    adapter_id: str
    adapter_version: str
    canonical_entrypoint: str
    provider_class: str
    provider_mode: str
    provider_account_reference: str
    credential_boundary_reference: str
    authority_delta: int
    execution_ready: bool
    resolution_sha256: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("INVALID_SCHEMA_VERSION")
        _id(self.resolution_id)
        _id(self.capability_id)
        _id(self.capability_version)
        if self.result not in ("ALLOW", "DENY", "INCOMPLETE"):
            raise ValueError("INVALID_RESULT")
        if self.deny_reason and self.deny_reason not in tuple(DenyReason.__members__.values()):
            if self.deny_reason != "":
                raise ValueError("INVALID_DENY_REASON")
        if self.authority_delta != 0:
            raise ValueError("AUTHORITY_DELTA_MUST_BE_ZERO")
        if not isinstance(self.execution_ready, bool):
            raise ValueError("INVALID_EXECUTION_READY")
        if self.execution_ready is not False:
            raise ValueError("EXECUTION_READY_MUST_BE_FALSE")
        if self.matched_entry_sha256:
            _sha(self.matched_entry_sha256)
        _seal(self, "resolution_sha256")

    def body(self) -> dict:
        return _body(self, "resolution_sha256")

    def to_dict(self) -> dict:
        return {**self.body(), "resolution_sha256": self.resolution_sha256}


__all__ = [
    "CapabilityRegistryEntry",
    "CapabilityLookupRequest",
    "CapabilityResolutionRecord",
    "ResolutionResult",
    "DenyReason",
    "SCHEMA_VERSION",
    "HASH_DOMAIN",
]
# 03 — Interface Specifications: Executor Continuation Components

**Package:** Executor Continuation Implementation Planning
**Source ADR:** ADR-MC-001 (ACCEPTED, ratified 2026-08-05)
**Scope:** PLANNING ONLY — no runtime code. This document defines interface contracts and data models for the 14 components enumerated in ADR-MC-001 Section 9.1.
**Codebase conventions:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy. Type annotations follow the existing `backend/lead-router/models/lead.py` style: `str` enums subclassing `(str, Enum)`, Pydantic `BaseModel` with `Field(...)`, `Optional[...]` for nullable fields, `datetime` for timestamps.

---

## 0. Document Conventions

- All data models are expressed as Pydantic v2 `BaseModel` schemas or Python `Protocol`/`ABC` interfaces. They are planning artifacts, not committed runtime code.
- `datetime` fields are timezone-aware UTC unless stated otherwise.
- "Signed" fields carry a detached signature; the signing key identity is identified by a companion `*_signer_id` field.
- Every component section follows the same structure: Purpose, Primary Interface, Data Models, Error Conditions, Key Invariants.
- Shared enums and primitives are defined once in Section 1 and referenced throughout.
- Component numbering matches ADR-MC-001 Section 9.1 order.

---

## 1. Shared Primitives and Enums

```python
from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Literal, Optional, Protocol
from uuid import UUID

from pydantic import BaseModel, Field


# --- Enums ---------------------------------------------------------------

class ContinuationClass(str, Enum):
    """ADR Section 2.9 side-effect classification."""
    STOP = "STOP"          # No continuation permitted (default)
    CLASS_0 = "CLASS_0"    # Local computation only; no external effects
    CLASS_1 = "CLASS_1"    # Reversible internal writes / safe local state
    CLASS_2 = "CLASS_2"    # Idempotent external writes w/ downstream dedup
    CLASS_3 = "CLASS_3"    # Irreversible/destructive/financial/legal — PROHIBITED during continuation


class FinalState(str, Enum):
    """ADR Section 2.6.2 completion report final_state."""
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"
    TIMEOUT = "TIMEOUT"


class ReconciliationClass(str, Enum):
    """ADR Section 2.6.4 reconciliation classifications."""
    VALID_CONTINUATION = "VALID_CONTINUATION"
    VALID_BUT_RECONCILED = "VALID_BUT_RECONCILED"
    INVALID_CONTINUATION = "INVALID_CONTINUATION"
    CONFLICTING_REPORTS = "CONFLICTING_REPORTS"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"


class CommandState(str, Enum):
    """ADR Section 4.2 command state machine."""
    PENDING = "PENDING"
    LEASED = "LEASED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    CONTINUING = "CONTINUING"
    ABORTED = "ABORTED"
    RECONCILED = "RECONCILED"
    INVALID = "INVALID"
    CONFLICT = "CONFLICT"
    REPLAY = "REPLAY"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    CANCELLED = "CANCELLED"
    REVOKED = "REVOKED"


class LeaseState(str, Enum):
    """ADR Section 4.1 lease/capability state machine."""
    LEASE_ISSUED = "LEASE_ISSUED"
    ACTIVE = "ACTIVE"
    RENEWED = "RENEWED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class CapabilityState(str, Enum):
    ISSUED = "ISSUED"
    SUPERSEDED = "SUPERSEDED"   # replaced by a newer capability at renewal
    EXERCISED = "EXERCISED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class SignalType(str, Enum):
    """ADR Section 2.2.1 detection signals."""
    HEARTBEAT_ACK = "HEARTBEAT_ACK"
    LEASE_RENEWAL_REJECTION = "LEASE_RENEWAL_REJECTION"
    COMMAND_STATUS_QUERY_FAILURE = "COMMAND_STATUS_QUERY_FAILURE"
    WITNESS_OUTAGE_STATEMENT = "WITNESS_OUTAGE_STATEMENT"
    POLICY_BROADCAST_SILENCE = "POLICY_BROADCAST_SILENCE"


class RevocationEntryType(str, Enum):
    LEASE_REVOCATION = "LEASE_REVOCATION"
    COMMAND_CANCELLATION = "COMMAND_CANCELLATION"
    CAPABILITY_REVOCATION = "CAPABILITY_REVOCATION"
    EMERGENCY_DENY = "EMERGENCY_DENY"
    WITNESS_KEY_REVOCATION = "WITNESS_KEY_REVOCATION"


# --- Shared scalar primitives ---------------------------------------------

class SignedToken(BaseModel):
    """Detached-signature token envelope reused across the system."""
    payload_b64: str = Field(..., description="Base64url-encoded canonical JSON payload")
    signature_b64: str = Field(..., description="Base64url-encoded detached signature")
    signer_id: str = Field(..., description="Key identity that produced signature_b64")
    algorithm: Literal["Ed25519", "ECDSA-P256-SHA256"] = "Ed25519"


class Fingerprint(BaseModel):
    """Short hash fingerprint of a token or blob."""
    algorithm: Literal["sha256", "blake3"] = "sha256"
    digest_hex: str = Field(..., pattern=r"^[0-9a-f]{64}$")


class SignedTimeAnchor(BaseModel):
    """ADR Section 2.8 signed wall-clock anchor issued by the Brain."""
    anchor_id: str
    wall_time: datetime
    monotonic_marker: int = Field(..., description="Executor monotonic counter at anchor receipt")
    previous_anchor_id: Optional[str] = Field(default=None)
    signature: SignedToken
```

---

## 2. Component 1 — Signed Lease Token Service

**Purpose (ADR 2.1.1–2.1.3):** Issue, renew, and revoke cryptographically signed lease tokens binding one executor to one command under a time-bounded authority envelope.

### 2.1 Primary Interface

```python
class LeaseTokenService(Protocol):
    def issue_lease(self, request: LeaseIssueRequest) -> LeaseIssueResult: ...
    def renew_lease(self, request: LeaseRenewalRequest) -> LeaseRenewalResult: ...
    def revoke_lease(self, request: LeaseRevokeRequest) -> LeaseRevokeResult: ...
    def validate_lease(self, token: SignedToken, *, now: datetime) -> LeaseValidationResult: ...
    def fingerprint(self, token: SignedToken) -> Fingerprint: ...
```

### 2.2 Data Models

```python
class LeasePayload(BaseModel):
    """Payload carried inside a signed lease token (ADR 2.1.1)."""
    command_id: str
    executor_id: str
    tenant_id: str
    issued_at: datetime
    expires_at: datetime
    policy_snapshot_id: str
    continuation_class: ContinuationClass
    continuation_capability_id: Optional[str] = Field(
        default=None,
        description="Reference to the pre-issued continuation capability, if any"
    )


class LeaseIssueRequest(BaseModel):
    command_id: str
    executor_id: str
    tenant_id: str
    duration: timedelta = Field(..., gt=timedelta(0))
    policy_snapshot_id: str
    continuation_class: ContinuationClass = ContinuationClass.STOP
    issue_continuation_capability: bool = False


class LeaseIssueResult(BaseModel):
    lease_token: SignedToken
    lease: LeasePayload
    continuation_capability_id: Optional[str] = None
    audit_event_id: str


class LeaseRenewalRequest(BaseModel):
    current_lease_token: SignedToken
    extension: timedelta = Field(..., gt=timedelta(0))


class LeaseRenewalResult(BaseModel):
    status: Literal["RENEWED", "REJECTED"]
    new_lease_token: Optional[SignedToken] = None
    new_lease: Optional[LeasePayload] = None
    new_continuation_capability_id: Optional[str] = Field(
        default=None,
        description="Fresh capability issued at renewal; prior capability is superseded"
    )
    superseded_capability_id: Optional[str] = None
    rejection_reason: Optional[Literal[
        "COMMAND_CANCELLED",
        "NOT_LEASE_HOLDER",
        "MAX_EXECUTION_DURATION_EXCEEDED",
        "POLICY_SNAPSHOT_SUPERSEDED",
        "BRAIN_UNAVAILABLE",
    ]] = None
    audit_event_id: str


class LeaseRevokeRequest(BaseModel):
    lease_token: SignedToken
    reason: Literal["EXPLICIT_REVOKE", "CANCELLED", "SECURITY_EVENT"]


class LeaseRevokeResult(BaseModel):
    revoked: bool
    revoked_capability_ids: list[str] = Field(default_factory=list)
    audit_event_id: str


class LeaseValidationResult(BaseModel):
    valid: bool
    lease: Optional[LeasePayload] = None
    state: LeaseState
    failure_reason: Optional[Literal[
        "INVALID_SIGNATURE",
        "EXPIRED",
        "REVOKED",
        "TENANT_MISMATCH",
        "CLOCK_SKEW_EXCEEDED",
        "MALFORMED_PAYLOAD",
    ]] = None
```

### 2.3 Error Conditions

- `INVALID_SIGNATURE` — signature verification fails or signer unknown.
- `EXPIRED` — `now >= expires_at`.
- `REVOKED` — lease appears in the revocation stream (Component 6).
- `TENANT_MISMATCH` — token `tenant_id` does not match the validating context.
- `CLOCK_SKEW_EXCEEDED` — `now` diverges from Brain signed anchor beyond `max_clock_skew_tolerance`.
- `MALFORMED_PAYLOAD` — payload cannot be deserialized to `LeasePayload`.
- Renewal rejection reasons enumerated in `LeaseRenewalResult.rejection_reason`.

### 2.4 Key Invariants (enforced at interface boundary)

- INV-1: Exactly one executor holds an active lease per `command_id` at a time.
- INV-2: `expires_at > issued_at` and both are Brain-signed.
- INV-3: A renewed lease invalidates the prior token and any prior continuation capability (ADR 2.1.2); `superseded_capability_id` is recorded and must be rejected by downstream systems even if its `not_valid_after` is later (Invariant 3a).
- INV-4: Issuance and revocation are logged as immutable audit events with causation links (Component 12).
- INV-5: `validate_lease` is pure and side-effect free; it never mutates state.

---

## 3. Component 2 — Continuation Capability Service

**Purpose (ADR 2.1.4):** Issue, validate, and revoke signed continuation capabilities. A capability is cryptographically separate from the lease token and unusable before lease expiry.

### 3.1 Primary Interface

```python
class ContinuationCapabilityService(Protocol):
    def issue_capability(self, request: CapabilityIssueRequest) -> CapabilityIssueResult: ...
    def validate_capability(
        self, token: SignedToken, *, now: datetime, lease_state: LeaseState
    ) -> CapabilityValidationResult: ...
    def revoke_capability(self, request: CapabilityRevokeRequest) -> CapabilityRevokeResult: ...
    def supersede_capability(self, capability_id: str, *, by_capability_id: str) -> None: ...
    def is_superseded(self, capability_id: str) -> bool: ...
```

### 3.2 Data Models — Continuation Capability (ADR Section 2.1.4, all fields)

```python
class SideEffectSlotSpec(BaseModel):
    """Specification of permitted side-effect slots (ADR 2.1.4 side_effect_slot_spec)."""
    permitted_slots: list[str] = Field(
        ..., min_length=1,
        description="Explicit allow-list of side_effect_slot identifiers"
    )
    max_slots_per_operation: Optional[int] = Field(default=None, ge=1)


class ContinuationCapabilityPayload(BaseModel):
    """
    Continuation capability — all fields from ADR Section 2.1.4.
    This is the canonical structure; it is the single source of truth for the
    capability schema. Components 9, 10, 13, and 14 reference this model.
    """
    capability_id: str = Field(..., description="Unique identifier for this continuation grant")
    command_id: str = Field(..., description="The command for which continuation is authorized")
    tenant_id: str = Field(..., description="Tenant scope")
    executor_id: str = Field(..., description="Executor authorized to continue")
    issued_at: datetime = Field(..., description="When the capability was issued")
    not_valid_before: datetime = Field(
        ...,
        description="Must be equal to or after lease expires_at; prevents use while lease is active"
    )
    not_valid_after: datetime = Field(
        ...,
        description="Maximum absolute wall-clock time the capability may be exercised"
    )
    max_continuation_duration: timedelta = Field(
        ..., gt=timedelta(0),
        description="Bound on how long continuation may run"
    )
    max_continuation_operations: int = Field(..., ge=1, description="Bound on discrete operations")
    continuation_class: ContinuationClass = Field(
        ..., description="Side-effect class permitted (ADR 2.9)"
    )
    permitted_operation_ids: list[str] = Field(
        ..., min_length=1,
        description="Operation identifiers the executor may perform"
    )
    side_effect_slot_spec: SideEffectSlotSpec = Field(
        ..., description="Specification of permitted side-effect slots"
    )
    policy_snapshot_hash: str = Field(
        ..., pattern=r"^[0-9a-f]{64}$",
        description="Cryptographic hash of the pinned policy snapshot"
    )
    policy_snapshot_id: str = Field(..., description="Identifier of the pinned policy snapshot")
    policy_snapshot_not_valid_after: Optional[datetime] = Field(
        default=None,
        description=(
            "Wall-clock time after which the pinned policy snapshot expires; "
            "executor must not continue past this time. "
            "If absent, defaults to the capability's own not_valid_after."
        )
    )
    revocation_watermark_required: int = Field(
        ..., ge=0,
        description="Minimum revocation sequence number the executor must have observed"
    )
    signed_capability_token: SignedToken = Field(
        ..., description="Brain-signed token binding all fields; distinct from lease token"
    )


class CapabilityIssueRequest(BaseModel):
    command_id: str
    tenant_id: str
    executor_id: str
    lease_expires_at: datetime
    max_continuation_duration: timedelta
    max_continuation_operations: int = Field(..., ge=1)
    continuation_class: ContinuationClass
    permitted_operation_ids: list[str]
    side_effect_slot_spec: SideEffectSlotSpec
    policy_snapshot_id: str
    policy_snapshot_hash: str
    policy_snapshot_not_valid_after: Optional[datetime] = None
    revocation_watermark_required: int = Field(..., ge=0)
    not_valid_after: datetime
    not_valid_before: Optional[datetime] = Field(
        default=None,
        description="Defaults to lease_expires_at if omitted"
    )


class CapabilityIssueResult(BaseModel):
    capability: ContinuationCapabilityPayload
    audit_event_id: str


class CapabilityRevokeRequest(BaseModel):
    capability_id: str
    reason: Literal["EXPLICIT_REVOKE", "SUPERSEDED", "SECURITY_EVENT", "EMERGENCY_DENY"]


class CapabilityRevokeResult(BaseModel):
    revoked: bool
    audit_event_id: str


class CapabilityValidationResult(BaseModel):
    valid: bool
    capability: Optional[ContinuationCapabilityPayload] = None
    state: CapabilityState
    failure_reason: Optional[Literal[
        "INVALID_SIGNATURE",
        "BEFORE_NOT_VALID_BEFORE",
        "AFTER_NOT_VALID_AFTER",
        "POLICY_SNAPSHOT_EXPIRED",
        "SUPERSEDED",
        "REVOKED",
        "TENANT_MISMATCH",
        "EXECUTOR_MISMATCH",
        "LEASE_STILL_ACTIVE",
        "CLOCK_SKEW_EXCEEDED",
        "MALFORMED_PAYLOAD",
    ]] = None
```

### 3.3 Error Conditions

- `BEFORE_NOT_VALID_BEFORE` — `now < not_valid_before`; capability is unusable while the lease is active.
- `AFTER_NOT_VALID_AFTER` — `now > not_valid_after`.
- `POLICY_SNAPSHOT_EXPIRED` — `policy_snapshot_not_valid_after` present and `now > policy_snapshot_not_valid_after`.
- `SUPERSEDED` — capability was superseded at lease renewal (Component 1) even if `not_valid_after` is later.
- `LEASE_STILL_ACTIVE` — caller passes `lease_state=ACTIVE`; capability must not be exercised while the lease is valid.
- `EXECUTOR_MISMATCH` / `TENANT_MISMATCH` — context identity does not match the capability.
- `CLOCK_SKEW_EXCEEDED` — time anchors (Component 14) disagree beyond tolerance.

### 3.4 Key Invariants

- INV-3: Capability cannot be used before `not_valid_before` or after `not_valid_after` (ADR Invariant 3).
- INV-3a: Only the capability referenced by the latest valid lease may be exercised; superseded capabilities are rejected regardless of their own `not_valid_after` (ADR Invariant 3a).
- INV-4: Capability is narrowly scoped to a single command, tenant, executor, operation set, and time envelope.
- INV-5: `continuation_class == CLASS_3` capabilities must never be issued for continuation; issuance of a CLASS_3 capability is a contract violation and must be rejected at issue time.
- INV-6: `signed_capability_token` is cryptographically distinct from any lease token.

---

## 4. Component 3 — Brain Heartbeat Endpoint

**Purpose (ADR 2.2.1):** Allow executors to detect Brain availability via heartbeat acknowledgements.

### 4.1 Primary Interface

```python
class BrainHeartbeatEndpoint(Protocol):
    def heartbeat(self, request: HeartbeatRequest) -> HeartbeatResponse: ...
    def last_heartbeat(self, executor_id: str) -> Optional[HeartbeatRecord]: ...
```

### 4.2 Data Models

```python
class HeartbeatRequest(BaseModel):
    executor_id: str
    tenant_id: str
    monotonic_marker: int
    last_seen_anchor_id: Optional[str] = None


class HeartbeatResponse(BaseModel):
    status: Literal["OK", "DEGRADED", "UNAVAILABLE"]
    server_time: datetime
    signed_anchor: SignedTimeAnchor
    revocation_watermark: int = Field(..., ge=0)


class HeartbeatRecord(BaseModel):
    executor_id: str
    received_at: datetime
    response: HeartbeatResponse
```

### 4.3 Error Conditions

- Network timeout / unreachable → counts toward `brain_heartbeat_miss_threshold`.
- `UNAVAILABLE` status → counts as a missed heartbeat for outage detection (Component: outage detector, not enumerated separately).
- Invalid `tenant_id` → `403`-equivalent rejection; not counted as a Brain outage signal.

### 4.4 Key Invariants

- INV-1: Each successful heartbeat returns a fresh `SignedTimeAnchor` (Component 14).
- INV-2: `revocation_watermark` is monotonically non-decreasing across responses.
- INV-3: Heartbeat responses are tenant-scoped; cross-tenant probing is a security event.

---

## 5. Component 4 — Witness Statement Service

**Purpose (ADR 2.2.4):** Publish and validate signed witness statements about Brain availability from independent control-plane identities.

### 5.1 Primary Interface

```python
class WitnessStatementService(Protocol):
    def publish_statement(self, request: WitnessPublishRequest) -> WitnessStatement: ...
    def validate_statement(self, token: SignedToken, *, now: datetime) -> WitnessValidationResult: ...
    def collect_quorum(
        self, tenant_id: str, *, min_count: int, max_age: timedelta
    ) -> WitnessQuorumResult: ...
    def revoke_witness_key(self, witness_id: str, *, reason: str) -> None: ...
```

### 5.2 Data Models — Witness Statement (ADR Section 2.2.4)

```python
class WitnessStatement(BaseModel):
    """
    Witness statement — ADR Section 2.2.4.
    Witnesses are independent control-plane identities, not executors.
    """
    statement_id: str = Field(..., description="Unique statement identifier")
    witness_id: str = Field(..., description="Control-plane witness identity")
    tenant_id: str = Field(..., description="Tenant scope; witness for tenant A cannot cover tenant B")
    brain_region: str = Field(..., description="Brain partition observed")
    observed_state: Literal["AVAILABLE", "UNAVAILABLE", "DEGRADED"]
    nonce: int = Field(..., ge=0, description="Monotonically increasing per-witness nonce (replay resistance)")
    statement_time: datetime = Field(..., description="Signed wall-clock time of observation")
    monotonic_marker: int = Field(..., description="Witness monotonic marker")
    signature: SignedToken
    previous_statement_id: Optional[str] = Field(default=None)


class WitnessPublishRequest(BaseModel):
    witness_id: str
    tenant_id: str
    brain_region: str
    observed_state: Literal["AVAILABLE", "UNAVAILABLE", "DEGRADED"]
    monotonic_marker: int


class WitnessValidationResult(BaseModel):
    valid: bool
    statement: Optional[WitnessStatement] = None
    failure_reason: Optional[Literal[
        "INVALID_SIGNATURE",
        "UNKNOWN_WITNESS",
        "REVOKED_WITNESS_KEY",
        "STALE_STATEMENT",
        "NONCE_ROLLBACK",
        "TENANT_MISMATCH",
        "SELF_EXCLUSION_VIOLATION",
        "MALFORMED_PAYLOAD",
    ]] = None


class WitnessQuorumResult(BaseModel):
    quorum_satisfied: bool
    valid_statements: list[WitnessStatement] = Field(default_factory=list)
    distinct_witness_count: int = Field(..., ge=0)
    required_count: int = Field(..., ge=1)
    fault_model: Literal["BFT", "CFT"] = Field(
        ..., description="BFT: N>=3f+1, quorum>=2f+1; CFT: N>=2f+1, quorum>=f+1"
    )
    rejected_statements: list[WitnessValidationResult] = Field(default_factory=list)
```

### 5.3 Error Conditions

- `STALE_STATEMENT` — `now - statement_time > witness_statement_max_age`.
- `NONCE_ROLLBACK` — `nonce` is not strictly greater than the last accepted nonce for `witness_id`.
- `REVOKED_WITNESS_KEY` — witness key revoked via `revoke_witness_key`; all its statements invalid.
- `SELF_EXCLUSION_VIOLATION` — statement `witness_id` equals the executor's own identity or a peer under its control.

### 5.4 Key Invariants

- INV-1: A witness is never an executor participating in the command (ADR 2.2.4 self-exclusion).
- INV-2: Quorum requires `witness_quorum_size` valid statements from distinct witnesses; `witness_quorum_size < N`.
- INV-3: Witness statements alone are never sufficient to declare a Brain outage (ADR 2.2.2); at least one direct-Brain signal is required.
- INV-4: Statements are tenant-scoped; cross-tenant statements are rejected.
- INV-5: Replay resistance via monotonic nonce + signed anchor; stale/replayed statements rejected.

---

## 6. Component 5 — Executor Local State Cache

**Purpose (ADR 2.3):** Store inputs, configuration, and prior step outputs so the executor can self-check local state sufficiency before continuing.

### 6.1 Primary Interface

```python
class ExecutorLocalStateCache(Protocol):
    def store_inputs(self, command_id: str, inputs: CommandInputs) -> None: ...
    def store_step_output(self, command_id: str, operation_id: str, output: OperationOutput) -> None: ...
    def get_inputs(self, command_id: str) -> Optional[CommandInputs]: ...
    def get_step_output(self, command_id: str, operation_id: str) -> Optional[OperationOutput]: ...
    def check_sufficiency(self, command_id: str, required_ops: list[str]) -> StateSufficiencyResult: ...
    def evict(self, command_id: str) -> None: ...
```

### 6.2 Data Models

```python
class CommandInputs(BaseModel):
    command_id: str
    tenant_id: str
    task_manifest_digest: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    inputs: dict[str, str] = Field(..., description="Deterministic input map keyed by input name")


class OperationOutput(BaseModel):
    operation_id: str
    result_digest: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    output: dict[str, str]
    produced_at: datetime


class StateSufficiencyResult(BaseModel):
    sufficient: bool
    missing_inputs: list[str] = Field(default_factory=list)
    missing_operation_outputs: list[str] = Field(default_factory=list)
    deterministic_path_available: bool
```

### 6.3 Error Conditions

- Cache miss on `get_inputs` / `get_step_output` → returns `None`; sufficiency check reports the gap.
- `deterministic_path_available == False` → continuation eligibility fails (ADR 2.3 "Local state sufficient").

### 6.4 Key Invariants

- INV-1: Cache entries are scoped by `command_id`; cross-command reads are forbidden.
- INV-2: `check_sufficiency` must return `sufficient == False` if any required input or prior step output is missing or if the deterministic path is unavailable.
- INV-3: Cache is tenant-isolated; entries carry `tenant_id` and may not be read across tenants.

---

## 7. Component 6 — Revocation Stream

**Purpose (ADR 2.10):** Publish a signed, monotonic, tenant-partitioned stream of lease revocations, command cancellations, capability revocations, and emergency denies.

### 7.1 Primary Interface

```python
class RevocationStream(Protocol):
    def publish(self, entry: RevocationStreamEntryInput) -> RevocationStreamEntry: ...
    def read(self, tenant_id: str, *, since_seq: int, max_entries: int) -> list[RevocationStreamEntry]: ...
    def latest_watermark(self, tenant_id: str) -> int: ...
    def cache_age(self, tenant_id: str, *, now: datetime) -> timedelta: ...
```

### 7.2 Data Models — Revocation Stream Entry (ADR Section 2.10)

```python
class RevocationStreamEntry(BaseModel):
    """
    Revocation stream entry — ADR Section 2.10.
    Signed, monotonic, tenant-partitioned.
    """
    seq: int = Field(..., ge=0, description="Monotonic sequence number within tenant partition")
    tenant_id: str = Field(..., description="Tenant partition")
    entry_type: RevocationEntryType
    target_id: str = Field(
        ..., description="command_id, lease_token fingerprint, capability_id, or witness_id depending on entry_type"
    )
    issued_at: datetime = Field(..., description="Brain-signed issuance time")
    reason: Literal[
        "EXPLICIT_REVOKE", "CANCELLED", "SUPERSEDED",
        "EMERGENCY_DENY", "KEY_COMPROMISE", "SECURITY_EVENT"
    ]
    signature: SignedToken


class RevocationStreamEntryInput(BaseModel):
    tenant_id: str
    entry_type: RevocationEntryType
    target_id: str
    reason: Literal[
        "EXPLICIT_REVOKE", "CANCELLED", "SUPERSEDED",
        "EMERGENCY_DENY", "KEY_COMPROMISE", "SECURITY_EVENT"
    ]
```

### 7.3 Error Conditions

- `seq` collision within a tenant partition → publish rejected; publisher must retry with a higher seq.
- Signature invalid → read consumers drop the entry and treat the stream as potentially compromised (security event).
- `cache_age(tenant_id) > max_revocation_cache_age` at lease expiry → continuation fail-closed (ADR 2.10).

### 7.4 Key Invariants

- INV-1: `seq` is strictly monotonic per `tenant_id` partition.
- INV-2: Entries are append-only; no deletion or mutation.
- INV-3: Cross-tenant reads are forbidden; a stream for tenant A cannot contain entries for tenant B.
- INV-4: Fail-closed — if the watermark is missing, stale, or below the capability's `revocation_watermark_required`, continuation is not permitted (ADR 2.10).
- INV-5: A cancellation observed at or before the watermark is authoritative; continuation is forbidden.

---

## 8. Component 7 — Policy Snapshot Registry

**Purpose (ADR 2.11):** Pin and validate policy snapshots by cryptographic hash.

### 8.1 Primary Interface

```python
class PolicySnapshotRegistry(Protocol):
    def register(self, snapshot: PolicySnapshotInput) -> PolicySnapshotRecord: ...
    def get_by_id(self, snapshot_id: str) -> Optional[PolicySnapshotRecord]: ...
    def validate_hash(self, snapshot_id: str, expected_hash: str) -> PolicyHashValidationResult: ...
    def is_expired(self, snapshot_id: str, *, now: datetime, not_valid_after: Optional[datetime]) -> bool: ...
```

### 8.2 Data Models

```python
class PolicySnapshotInput(BaseModel):
    snapshot_id: str
    tenant_id: str
    policy_document: dict[str, str]
    not_valid_after: Optional[datetime] = None


class PolicySnapshotRecord(BaseModel):
    snapshot_id: str
    tenant_id: str
    policy_hash: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    policy_document: dict[str, str]
    registered_at: datetime
    not_valid_after: Optional[datetime] = None


class PolicyHashValidationResult(BaseModel):
    matches: bool
    snapshot: Optional[PolicySnapshotRecord] = None
    computed_hash: str = Field(..., pattern=r"^[0-9a-f]{64}$")
```

### 8.3 Error Conditions

- `snapshot_id` not found → `get_by_id` returns `None`; `validate_hash` returns `matches=False`.
- Hash mismatch → `matches=False`; security event.
- `is_expired` true when `now > not_valid_after` (or capability's `not_valid_after` when snapshot-level value absent).

### 8.4 Key Invariants

- INV-1: `policy_hash` is computed over the canonical (deterministically serialized) policy document.
- INV-2: A pinned snapshot cannot authorize side-effect classes or operations not explicitly permitted by the capability (ADR 2.11).
- INV-3: Snapshot records are immutable once registered.
- INV-4: Emergency deny channel revocations (Component 6) override any pinned snapshot allowance.

---

## 9. Component 8 — Continuation Journal Store

**Purpose (ADR 2.5.3):** Maintain an immutable per-continuation operation log recording every operation attempted, its input, output, success/failure, timestamp, and stable external-effect identity.

### 9.1 Primary Interface

```python
class ContinuationJournalStore(Protocol):
    def open(self, continuation_id: str, capability_id: str) -> ContinuationJournal: ...
    def append(self, continuation_id: str, entry: ContinuationJournalEntryInput) -> ContinuationJournalEntry: ...
    def read(self, continuation_id: str) -> ContinuationJournal: ...
    def seal(self, continuation_id: str) -> SealedJournalResult: ...
```

### 9.2 Data Models — Continuation Journal Entry (ADR Section 2.5.3)

```python
class StableEffectIdentity(BaseModel):
    """
    Stable external-effect identity — ADR Section 2.5.1.
    Uniqueness key for an externally visible effect, stable across
    normal execution, continuation, replay, and multiple executors.
    """
    root_command_id: str = Field(
        ..., description="Original command that initiated the work; never the replay-attempt command ID"
    )
    operation_id: str = Field(..., description="Deterministic operation within the command's plan")
    side_effect_slot: str = Field(..., description="Specific external-effect slot being claimed")


class ContinuationJournalEntryInput(BaseModel):
    operation_id: str
    side_effect_slot: str
    input_digest: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    output_digest: Optional[str] = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    status: Literal["SUCCEEDED", "FAILED", "SKIPPED_DUPLICATE", "ABORTED"]
    error_detail: Optional[str] = None


class ContinuationJournalEntry(BaseModel):
    """
    Continuation journal entry — ADR Section 2.5.3.
    Immutable per-continuation operation log record.
    """
    seq: int = Field(..., ge=0, description="Monotonic sequence within this continuation journal")
    continuation_id: str
    capability_id: str
    stable_effect_identity: StableEffectIdentity
    operation_id: str
    side_effect_slot: str
    input_digest: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    output_digest: Optional[str] = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    status: Literal["SUCCEEDED", "FAILED", "SKIPPED_DUPLICATE", "ABORTED"]
    error_detail: Optional[str] = None
    monotonic_marker: int
    wall_time: datetime
    signature: SignedToken


class ContinuationJournal(BaseModel):
    continuation_id: str
    capability_id: str
    entries: list[ContinuationJournalEntry] = Field(default_factory=list)
    sealed: bool = False
    seal_signature: Optional[SignedToken] = None


class SealedJournalResult(BaseModel):
    continuation_id: str
    sealed: bool
    seal_signature: SignedToken
    entry_count: int
```

### 9.3 Error Conditions

- Append after `seal` → rejected; journal is immutable once sealed.
- `seq` collision → rejected.
- Signature invalid on append → rejected.

### 9.4 Key Invariants

- INV-1: Entries are append-only; no mutation or deletion.
- INV-2: `stable_effect_identity.root_command_id` is always the original command, never a replay-attempt command ID (ADR 2.5.1 replay identity rule).
- INV-3: `SKIPPED_DUPLICATE` entries record that an effect was already applied and was not re-performed (ADR 2.5.2).
- INV-4: A sealed journal is immutable and tamper-evident via `seal_signature`.

---

## 10. Component 9 — Completion Receipt Service

**Purpose (ADR 2.6.2, 2.13):** Generate and verify signed continuation receipts. Every continuation produces an immutable, signed receipt.

### 10.1 Primary Interface

```python
class CompletionReceiptService(Protocol):
    def generate_receipt(self, report: CompletionReport) -> CompletionReceipt: ...
    def verify_receipt(self, receipt: CompletionReceipt) -> ReceiptVerificationResult: ...
    def store_receipt(self, receipt: CompletionReceipt) -> str: ...
    def get_receipt(self, receipt_id: str) -> Optional[CompletionReceipt]: ...
```

### 10.2 Data Models — Completion Report (ADR Section 2.6.2, all fields)

```python
class OperationPerformed(BaseModel):
    """Single operation as reported in completion_report.operations_performed."""
    operation_id: str
    side_effect_slot: str
    stable_effect_identity: StableEffectIdentity
    result_digest: str = Field(..., pattern=r"^[0-9a-f]{64}$")


class EvidenceRef(BaseModel):
    """Reference to a produced artifact."""
    ref_id: str
    ref_type: Literal["ARTIFACT", "JOURNAL", "WITNESS_STATEMENT", "OUTAGE_EVIDENCE"]
    uri: str
    digest: Optional[str] = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class OutageEvidenceBundle(BaseModel):
    """
    Outage evidence bundle — ADR Section 2.2 / 2.6.2.
    Replay-resistant signed bundle bound to capability_id and command_id.
    Downstream systems must reject continuation effects lacking valid,
    matching outage evidence.
    """
    bundle_id: str
    command_id: str
    capability_id: str
    tenant_id: str
    executor_id: str
    monotonic_outage_start: int = Field(
        ..., description="Monotonic clock marker when outage conditions began (ADR 2.2.3)"
    )
    wall_outage_declared_at: datetime = Field(
        ..., description="Signed wall-clock anchor when outage was declared (ADR 2.2.3)"
    )
    grace_period_end: datetime = Field(
        ..., description="Wall-clock time after which continuation may be considered (ADR 2.2.3)"
    )
    signals_observed: list[OutageSignalRecord] = Field(
        ..., min_length=2,
        description="At least two independent signals, one of which is a direct-Brain signal"
    )
    witness_statements: list[WitnessStatement] = Field(default_factory=list)
    signed_time_anchor: SignedTimeAnchor
    lease_token_fingerprint: Fingerprint
    signature: SignedToken


class OutageSignalRecord(BaseModel):
    """One detection signal crossing its threshold (ADR 2.2.1)."""
    signal_type: SignalType
    threshold_crossed_at: datetime
    consecutive_count: int = Field(..., ge=1)
    is_direct_brain_signal: bool = Field(
        ..., description="True for HEARTBEAT_ACK, LEASE_RENEWAL_REJECTION, or COMMAND_STATUS_QUERY_FAILURE"
    )


class CompletionReport(BaseModel):
    """
    Completion report — ADR Section 2.6.2, all fields.
    Submitted by every executor that continued, within completion_report_deadline
    of recovery detection. Reporting is mandatory regardless of outcome.
    """
    command_id: str = Field(..., description="The continued command")
    executor_id: str = Field(..., description="The continuing executor")
    continuation_id: str = Field(..., description="Unique continuation attempt (metadata only)")
    capability_id: str = Field(..., description="The continuation capability used")
    lease_token_fingerprint: str = Field(
        ..., pattern=r"^[0-9a-f]{64}$",
        description="Fingerprint of the expired lease token"
    )
    continuation_started_at: datetime = Field(..., description="When continuation began")
    continuation_ended_at: datetime = Field(..., description="When continuation ended")
    final_state: FinalState = Field(..., description="SUCCEEDED | FAILED | ABORTED | TIMEOUT")
    operations_performed: list[OperationPerformed] = Field(
        default_factory=list,
        description="Each operation with operation_id, side_effect_slot, stable_effect_identity, result_digest"
    )
    result_digest: str = Field(..., pattern=r"^[0-9a-f]{64}$", description="Digest of the completion result")
    evidence_refs: list[EvidenceRef] = Field(default_factory=list, description="References to produced artifacts")
    continuation_journal: bytes = Field(
        ..., description="Encrypted blob containing the full continuation journal"
    )
    audit_receipt_id: str = Field(..., description="Immutable audit receipt for the continuation")
    outage_evidence: OutageEvidenceBundle = Field(
        ..., description="Signed outage evidence bundle bound to capability_id and command_id"
    )
    revocation_watermark_observed: int = Field(
        ..., ge=0, description="Revocation sequence number the executor observed"
    )


class CompletionReceipt(BaseModel):
    receipt_id: str
    report: CompletionReport
    generated_at: datetime
    signature: SignedToken


class ReceiptVerificationResult(BaseModel):
    valid: bool
    failure_reason: Optional[Literal[
        "INVALID_SIGNATURE",
        "UNKNOWN_SIGNER",
        "TAMPERED_PAYLOAD",
        "MISSING_OUTAGE_EVIDENCE",
        "OUTAGE_EVIDENCE_MISMATCH",
        "REVOCATION_WATERMARK_BELOW_REQUIRED",
    ]] = None
```

### 10.3 Error Conditions

- `MISSING_OUTAGE_EVIDENCE` — `report.outage_evidence` absent or incomplete.
- `OUTAGE_EVIDENCE_MISMATCH` — bundle `capability_id`/`command_id` does not match the report.
- `REVOCATION_WATERMARK_BELOW_REQUIRED` — `revocation_watermark_observed` below the capability's `revocation_watermark_required`.
- `TAMPERED_PAYLOAD` — receipt payload hash does not match signed digest.

### 10.4 Key Invariants

- INV-1: Every continuation produces exactly one immutable, signed receipt (ADR Invariant 6).
- INV-2: Receipts are never mutated; `store_receipt` is idempotent on `receipt_id`.
- INV-3: A receipt without valid, matching outage evidence is invalid (ADR 2.1.4).
- INV-4: Silent continuation is forbidden; reporting is mandatory regardless of `final_state` (ADR 2.6.2).

---

## 11. Component 10 — Reconciliation Engine

**Purpose (ADR 2.6, 2.12):** Classify and resolve continuation reports with result selection, effect reconciliation, compensation, and manual review.

### 11.1 Primary Interface

```python
class ReconciliationEngine(Protocol):
    def submit_report(self, report: CompletionReport) -> ReconciliationSubmissionResult: ...
    def reconcile_command(self, command_id: str) -> ReconciliationOutcome: ...
    def detect_conflicts(self, command_id: str) -> ConflictDetectionResult: ...
    def authorize_replay(self, command_id: str) -> ReplayAuthorizationResult: ...
```

### 11.2 Data Models

```python
class ReconciliationSubmissionResult(BaseModel):
    accepted: bool
    duplicate: bool = Field(default=False, description="Duplicate (command_id, continuation_id) report")
    rejection_reason: Optional[Literal[
        "DUPLICATE_REPORT",
        "UNKNOWN_CAPABILITY",
        "INVALID_RECEIPT",
        "TENANT_MISMATCH",
    ]] = None


class ConflictDetectionResult(BaseModel):
    has_conflict: bool
    report_count: int
    distinct_continuation_ids: list[str] = Field(default_factory=list)
    divergent_result_digests: list[str] = Field(default_factory=list)
    conflicting_effect_identities: list[StableEffectIdentity] = Field(default_factory=list)


class ResultSelectionDecision(BaseModel):
    selected_continuation_id: Optional[str] = Field(
        default=None, description="None when routed to manual review"
    )
    tie_breaker: Optional[Literal["TRUSTED_SIGNED_TIME", "LOWEST_EXECUTOR_ID"]] = None
    duplicate_agreed_continuation_ids: list[str] = Field(default_factory=list)


class EffectReconciliationDecision(BaseModel):
    effect_identity: StableEffectIdentity
    action: Literal["APPLY", "MARK_DUPLICATE", "FREEZE", "COMPENSATE"]
    reversible: bool
    notes: Optional[str] = None


class ReconciliationOutcome(BaseModel):
    command_id: str
    classification: ReconciliationClass
    result_selection: Optional[ResultSelectionDecision] = None
    effect_decisions: list[EffectReconciliationDecision] = Field(default_factory=list)
    manual_review_required: bool
    final_command_state: CommandState
    audit_event_id: str


class ReplayAuthorizationResult(BaseModel):
    authorized: bool
    replay_attempt_id: Optional[str] = None
    new_lease_token: Optional[SignedToken] = None
    root_command_id: str = Field(..., description="Original command; effect identities derive from this, not the replay record")
    rejection_reason: Optional[Literal[
        "UNRECONCILED_CONTINUATIONS",
        "UNRESOLVED_EFFECTS",
        "MANUAL_REVIEW_PENDING",
        "NOT_ELIGIBLE",
    ]] = None
```

### 11.3 Error Conditions

- `DUPLICATE_REPORT` — `(command_id, continuation_id)` already submitted (ADR 2.5.2 Brain reconciliation layer).
- `UNRECONCILED_CONTINUATIONS` — replay blocked while continuation reports outstanding.
- Divergent `result_digest` values → `CONFLICTING_REPORTS`, no automatic selection.

### 11.4 Key Invariants

- INV-1: Result selection by timestamp is permitted only when all reported effects are provably idempotent and equivalent (ADR 2.6.3.1).
- INV-2: Conflicting results or non-reversible effects never resolve silently; they freeze and route to manual review (ADR Invariant 8).
- INV-3: Replay uses a new lease and execution identity but preserves original external-effect identities rooted at `root_command_id` (ADR 2.7).
- INV-4: Class 3 effects are never applied automatically; always freeze and manual review (ADR 2.6.3.2).
- INV-5: Compensation is itself a command with its own lease, idempotency key, and audit chain (ADR 2.6.3.3).

---

## 12. Component 11 — Conflict Review Queue

**Purpose (ADR 2.6.3.4, 2.12):** Surface conflicting continuation results, invalid continuations, and non-reversible effects for operator resolution.

### 12.1 Primary Interface

```python
class ConflictReviewQueue(Protocol):
    def enqueue(self, item: ConflictReviewItemInput) -> ConflictReviewItem: ...
    def list_pending(self, tenant_id: str, *, limit: int) -> list[ConflictReviewItem]: ...
    def resolve(self, item_id: str, decision: ConflictReviewDecision) -> ConflictReviewResolution: ...
    def get(self, item_id: str) -> Optional[ConflictReviewItem]: ...
```

### 12.2 Data Models

```python
class ConflictReviewItemInput(BaseModel):
    command_id: str
    tenant_id: str
    classification: ReconciliationClass
    reports: list[CompletionReport]
    conflicting_effect_identities: list[StableEffectIdentity] = Field(default_factory=list)
    reason: Literal[
        "DIVERGENT_RESULTS",
        "NON_REVERSIBLE_EFFECTS",
        "INVALID_CONTINUATION",
        "REVOCATION_STATUS_UNKNOWN",
        "CAPABILITY_DISPUTED",
        "NON_DETERMINISTIC_OUTCOME",
    ]


class ConflictReviewItem(BaseModel):
    item_id: str
    command_id: str
    tenant_id: str
    classification: ReconciliationClass
    reports: list[CompletionReport]
    conflicting_effect_identities: list[StableEffectIdentity]
    reason: str
    created_at: datetime
    resolved: bool = False


class ConflictReviewDecision(BaseModel):
    decision: Literal["SELECT_RESULT", "COMPENSATE", "FREEZE_PERMANENT", "REJECT_ALL"]
    selected_continuation_id: Optional[str] = None
    operator_id: str
    rationale: str


class ConflictReviewResolution(BaseModel):
    item_id: str
    resolved: bool
    final_command_state: CommandState
    audit_event_id: str
```

### 12.3 Error Conditions

- Resolving an already-resolved item → rejected.
- `operator_id` lacks authority for `tenant_id` → rejected with `403`-equivalent.
- `selected_continuation_id` not present in `reports` → validation error.

### 12.4 Key Invariants

- INV-1: The command remains in `MANUAL_REVIEW_REQUIRED` until an authorized operator resolves it (ADR 2.6.3.4).
- INV-2: All evidence, receipts, and continuation journals are surfaced to the operator.
- INV-3: No silent conflict resolution; every resolution is recorded as an audit event (Component 12).

---

## 13. Component 12 — Audit Event Pipeline

**Purpose (ADR 2.13):** Append continuation events to the immutable audit ledger. Authoritative audit storage is never truncated.

### 13.1 Primary Interface

```python
class AuditEventPipeline(Protocol):
    def append(self, event: AuditEventInput) -> AuditEvent: ...
    def get(self, event_id: str) -> Optional[AuditEvent]: ...
    def query(
        self, tenant_id: str, *, command_id: Optional[str] = None, limit: int = 100
    ) -> list[AuditEvent]: ...
    def causation_chain(self, command_id: str, *, max_links: int) -> CausationChainProjection: ...
```

### 13.2 Data Models

```python
class AuditEventType(str, Enum):
    LEASE_ISSUED = "LEASE_ISSUED"
    LEASE_RENEWED = "LEASE_RENEWED"
    LEASE_EXPIRED = "LEASE_EXPIRED"
    LEASE_REVOKED = "LEASE_REVOKED"
    CAPABILITY_ISSUED = "CAPABILITY_ISSUED"
    CAPABILITY_SUPERSEDED = "CAPABILITY_SUPERSEDED"
    CAPABILITY_REVOKED = "CAPABILITY_REVOKED"
    BRAIN_OUTAGE_DECLARED = "BRAIN_OUTAGE_DECLARED"
    CONTINUATION_ELIGIBILITY_DECISION = "CONTINUATION_ELIGIBILITY_DECISION"
    CONTINUATION_OPERATION_PERFORMED = "CONTINUATION_OPERATION_PERFORMED"
    CONTINUATION_COMPLETED = "CONTINUATION_COMPLETED"
    BRAIN_RECOVERY_DETECTED = "BRAIN_RECOVERY_DETECTED"
    RECONCILIATION_EVENT = "RECONCILIATION_EVENT"
    TERMINAL_STATE_EVENT = "TERMINAL_STATE_EVENT"


class AuditEventInput(BaseModel):
    tenant_id: str
    event_type: AuditEventType
    command_id: Optional[str] = None
    capability_id: Optional[str] = None
    continuation_id: Optional[str] = None
    payload: dict[str, str]
    causation_event_id: Optional[str] = None


class AuditEvent(BaseModel):
    event_id: str
    tenant_id: str
    event_type: AuditEventType
    command_id: Optional[str] = None
    capability_id: Optional[str] = None
    continuation_id: Optional[str] = None
    payload: dict[str, str]
    causation_event_id: Optional[str] = None
    recorded_at: datetime
    ledger_seq: int = Field(..., ge=0, description="Monotonic ledger sequence")
    hash_link: str = Field(..., pattern=r"^[0-9a-f]{64}$", description="Hash chaining this event to the previous")


class CausationChainProjection(BaseModel):
    command_id: str
    links: list[AuditEvent] = Field(default_factory=list)
    truncated: bool = Field(..., description="True when links exceed MAX_CAUSATION_LINKS (projection only)")
    total_event_count: int = Field(..., ge=0, description="Authoritative count; ledger is never truncated")
    max_causation_links: int
```

### 13.3 Error Conditions

- Append with invalid `causation_event_id` → rejected.
- Ledger write failure → caller must fail-closed; no continuation may proceed without audit capability (ADR 2.3 "Audit capability").

### 13.4 Key Invariants

- INV-1: Authoritative audit storage is never truncated (ADR Invariant 11).
- INV-2: Events are append-only and hash-chained (`hash_link`).
- INV-3: Projection APIs (e.g., `causation_chain`) may paginate/cap with truncation metadata, but the ledger itself is complete.
- INV-4: All ADR Section 2.13 events are recorded: lease expiry, capability issuance, outage declaration, eligibility decision, each operation, completion, recovery, reconciliation, terminal state.

---

## 14. Component 13 — Downstream Effect Identity Layer

**Purpose (ADR 2.5):** Validate `(command_id, operation_id, side_effect_slot)` before applying effects. Provides duplicate suppression at the downstream boundary.

### 14.1 Primary Interface

```python
class DownstreamEffectIdentityLayer(Protocol):
    def check_effect(
        self, request: EffectCheckRequest
    ) -> EffectCheckResult: ...
    def record_effect(self, request: EffectRecordRequest) -> EffectRecord: ...
    def query_effect(self, identity: StableEffectIdentity) -> Optional[EffectRecord]: ...
```

### 14.2 Data Models

```python
class EffectCheckRequest(BaseModel):
    identity: StableEffectIdentity
    capability: ContinuationCapabilityPayload
    outage_evidence: OutageEvidenceBundle
    tenant_id: str


class EffectCheckResult(BaseModel):
    permitted: bool
    duplicate: bool = Field(default=False, description="Effect already applied for this identity")
    failure_reason: Optional[Literal[
        "DUPLICATE_EFFECT",
        "CAPABILITY_INVALID",
        "OUTAGE_EVIDENCE_MISSING",
        "OUTAGE_EVIDENCE_MISMATCH",
        "CLASS_3_PROHIBITED",
        "OPERATION_NOT_PERMITTED",
        "SLOT_NOT_PERMITTED",
        "TENANT_MISMATCH",
    ]] = None


class EffectRecordRequest(BaseModel):
    identity: StableEffectIdentity
    result_digest: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    capability_id: str
    applied_at: datetime


class EffectRecord(BaseModel):
    identity: StableEffectIdentity
    result_digest: str
    capability_id: str
    applied_at: datetime
    recorded_at: datetime
```

### 14.3 Error Conditions

- `DUPLICATE_EFFECT` — `(root_command_id, operation_id, side_effect_slot)` already recorded.
- `CLASS_3_PROHIBITED` — capability `continuation_class == CLASS_3`; effects refused during continuation (ADR 2.9).
- `OPERATION_NOT_PERMITTED` — `operation_id` not in `capability.permitted_operation_ids`.
- `SLOT_NOT_PERMITTED` — `side_effect_slot` not in `capability.side_effect_slot_spec.permitted_slots`.
- `OUTAGE_EVIDENCE_MISSING` / `OUTAGE_EVIDENCE_MISMATCH` — bundle absent or not bound to the capability/command (ADR 2.1.4).

### 14.4 Key Invariants

- INV-1: The uniqueness key is `(root_command_id, operation_id, side_effect_slot)`; `continuation_id`, `executor_id`, `lease_token`, and replay attempt number are execution metadata, not part of the identity (ADR 2.5.1).
- INV-2: Downstream systems reject duplicate effects matching the same identity regardless of which executor or attempt produced them (ADR 2.5.2 downstream layer).
- INV-3: A capability alone is not sufficient proof of authority while the Brain is healthy; valid matching outage evidence is required (ADR 2.1.4).
- INV-4: Class 3 effects are always refused during continuation (ADR 2.9, Invariant 15).

---

## 15. Component 14 — Signed Time-Anchor Service

**Purpose (ADR 2.8):** Issue and validate signed wall-clock anchors. The Brain is the authoritative clock source; executors derive elapsed time from monotonic clocks corrected by signed anchors.

### 15.1 Primary Interface

```python
class SignedTimeAnchorService(Protocol):
    def issue_anchor(self, request: AnchorIssueRequest) -> SignedTimeAnchor: ...
    def validate_anchor(self, anchor: SignedTimeAnchor, *, last_anchor: Optional[SignedTimeAnchor]) -> AnchorValidationResult: ...
    def check_skew(self, executor_wall_time: datetime, anchor: SignedTimeAnchor) -> SkewCheckResult: ...
    def check_rollback(self, anchor: SignedTimeAnchor, *, last_anchor: SignedTimeAnchor) -> RollbackCheckResult: ...
```

### 15.2 Data Models

```python
class AnchorIssueRequest(BaseModel):
    tenant_id: str
    monotonic_marker: int
    previous_anchor_id: Optional[str] = None


class AnchorValidationResult(BaseModel):
    valid: bool
    failure_reason: Optional[Literal[
        "INVALID_SIGNATURE",
        "UNKNOWN_SIGNER",
        "PREVIOUS_ANCHOR_MISMATCH",
        "MALFORMED",
    ]] = None


class SkewCheckResult(BaseModel):
    within_tolerance: bool
    skew: timedelta
    max_skew_tolerance: timedelta
    security_event: bool = Field(
        ..., description="True when |skew| > max_clock_skew_tolerance (ADR 2.8)"
    )


class RollbackCheckResult(BaseModel):
    within_tolerance: bool
    rollback: timedelta
    max_rollback_tolerance: timedelta
    requires_operator_intervention: bool = Field(
        ..., description="True when rollback exceeds max_clock_rollback_tolerance (ADR 2.8)"
    )
```

### 15.3 Error Conditions

- `INVALID_SIGNATURE` / `UNKNOWN_SIGNER` — anchor not Brain-signed.
- `PREVIOUS_ANCHOR_MISMATCH` — `previous_anchor_id` does not match the last accepted anchor.
- Skew beyond `max_clock_skew_tolerance` → security event; executor must stop.
- Rollback beyond `max_clock_rollback_tolerance` → operator intervention required; executor must stop.

### 15.4 Key Invariants

- INV-1: The Brain is the authoritative clock source; all lease, capability, and revocation timestamps are Brain-signed (ADR 2.8).
- INV-2: `max_continuation_duration` and grace periods are measured with monotonic time to prevent extension via clock rollback (ADR 2.8).
- INV-3: Capability `not_valid_before` and `not_valid_after` are evaluated against signed Brain anchors, not executor wall-clock alone (ADR 2.8).
- INV-4: If executor and Brain time disagree beyond tolerance, the executor must stop and wait for a fresh signed anchor; continuation is not permitted under disputed time (ADR 2.8).
- INV-5: If the monotonic clock loses continuity (process restart, suspend/resume) or wall-clock drift exceeds tolerance, the executor must STOP (ADR 2.8).

---

## 16. Cross-Component Data Model Summary

The following structures are defined once above and referenced across components. This section indexes them for implementers.

| Structure | Defined In | Referenced By |
|---|---|---|
| `LeasePayload` / `SignedToken` (lease) | §2.2 (Component 1) | Components 2, 6, 9, 10, 12 |
| `ContinuationCapabilityPayload` | §3.2 (Component 2) | Components 8, 9, 10, 13, 14 |
| `WitnessStatement` | §5.2 (Component 4) | Components 9 (outage evidence), 12 |
| `RevocationStreamEntry` | §7.2 (Component 6) | Components 1, 2, 9, 10 |
| `ContinuationJournalEntry` / `StableEffectIdentity` | §9.2 (Component 8) | Components 9, 10, 11, 13 |
| `CompletionReport` / `OutageEvidenceBundle` | §10.2 (Component 9) | Components 10, 11, 12, 13 |
| `AuditEvent` | §13.2 (Component 12) | All components (causation chain) |
| `SignedTimeAnchor` | §1 / §15.2 (Component 14) | Components 1, 2, 4, 9 |

---

## 17. End-to-End Invariant Index

This section maps ADR-MC-001 Section 7 invariants to the interface boundaries that enforce them.

| ADR Inv # | Invariant (summary) | Primary Enforcement Boundary |
|---|---|---|
| 1 | No authoritative effects without valid lease | Component 1 `validate_lease`; Component 13 `check_effect` |
| 2 | Expired lease cannot authorize continuation/effects | Component 1 `validate_lease` → `EXPIRED`; Component 2 `validate_capability` requires `lease_state=EXPIRED` |
| 3 | Capability unusable before lease expiry or after own expiry | Component 2 `validate_capability` → `BEFORE_NOT_VALID_BEFORE` / `AFTER_NOT_VALID_AFTER` |
| 3a | Only latest-lease capability may be exercised; superseded rejected | Component 2 `is_superseded` / `supersede_capability`; Component 13 rejects superseded `capability_id` |
| 4 | Continuation is never the default | Component 2 issues capabilities only on explicit request; `ContinuationClass.STOP` default |
| 5 | Continuation cannot exceed its bounded envelope | Component 2 `max_continuation_duration` / `max_continuation_operations`; Component 8 journal seq limit |
| 6 | Every continuation produces an immutable signed receipt | Component 9 `generate_receipt` / `verify_receipt` |
| 7 | Every continuation is reconciled before terminal state | Component 10 `reconcile_command` |
| 8 | Conflicting results / non-reversible effects never resolve silently | Component 10 `detect_conflicts`; Component 11 enqueue |
| 9 | Cross-tenant continuation is impossible | All components enforce `tenant_id` match at boundary |
| 10 | Idempotency preserved across continuation, replay, normal execution | Component 13 `StableEffectIdentity`; Component 8 journal `SKIPPED_DUPLICATE` |
| 11 | Authoritative audit storage is never truncated | Component 12 `CausationChainProjection.truncated` (projection only) |
| 12 | Policy snapshot bounded to exact pinned hash | Component 7 `validate_hash`; Component 2 `policy_snapshot_hash` |
| 13 | Revocation knowledge must be fresh; absence ≠ permission | Component 6 `cache_age` / watermark; Component 2 `revocation_watermark_required` |
| 14 | Time cannot be manipulated to extend authority | Component 14 `check_skew` / `check_rollback`; monotonic time bounds |
| 15 | High-risk/irreversible side effects cannot be produced during continuation | Component 2 rejects `CLASS_3` issuance; Component 13 `CLASS_3_PROHIBITED` |

---

## 18. Open Questions for Implementation Phase

These are deliberately deferred to implementation planning (documents 04+) and are not resolved here:

1. **Persistence backend selection** for the immutable audit ledger (Component 12) and continuation journal store (Component 8) — append-only log vs. SQLAlchemy table with hash chaining.
2. **Signing key management** — HSM/KMS integration for Brain signing keys and witness identity keys.
3. **Witness topology** — concrete witness deployment, peer discovery, and the BFT-vs-CFT election (ADR 2.2.4 allows a CFT first implementation with documentation).
4. **Tenant configuration transport** — how the Section 9.2 configuration settings are delivered to executors and capped by platform maximums.
5. **Recovery notification channel** — how executors are notified of Brain recovery (heartbeat channel vs. witness broadcast).

---

**End of document.** This is a planning artifact only. No runtime code is authorized by this document. Implementation requires separate ADRs, branches, and authorizations per ADR-MC-001 Section 10.
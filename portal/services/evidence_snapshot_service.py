"""
EvidenceSnapshot service — create and retrieve only.

Engineering Doctrines:
  ED-003: Immutable evidence ≠ mutable presentation.
  ED-005: Single source of truth — snapshots are the authoritative record.
  ED-006: Verification before promotion — no advancement without evidence.

This service enforces:
  - Append-only: snapshots can be created but never modified or deleted.
  - Immutability: any attempt to update a snapshot raises ImmutableSnapshotError.
  - Supersession: old snapshots are marked SUPERSEDED only when a new one is created.
  - Version monotonicity: each new snapshot for a case gets the next integer version.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timezone
from typing import ClassVar


class ImmutableSnapshotError(Exception):
    """Raised when attempting to modify or delete an EvidenceSnapshot."""
    pass


class SnapshotNotFoundError(Exception):
    """Raised when a requested snapshot does not exist."""
    pass


class SnapshotVersionConflictError(Exception):
    """Raised when version assignment detects a conflict."""
    pass


class InvalidStateTransitionError(Exception):
    """Raised when an invalid status transition is attempted."""
    pass


class SnapshotStatus:
    """Canonical status values for EvidenceSnapshot lifecycle.

    State transitions (forward only):
      ACTIVE → SUPERSEDED  (new snapshot created for same case)
      ACTIVE → ARCHIVED    (evidence retired from operations)
      SUPERSEDED → ARCHIVED (retention/governance)

    No reverse transitions. No deletion.
    """
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"

    # Valid forward transitions
    _VALID_TRANSITIONS: ClassVar[dict[str, set[str]]] = {
        "active": {"superseded", "archived"},
        "superseded": {"archived"},
        "archived": set(),  # terminal state
    }

    @classmethod
    def is_valid_transition(cls, from_status: str, to_status: str) -> bool:
        """Check if a status transition is allowed."""
        allowed = cls._VALID_TRANSITIONS.get(from_status, set())
        return to_status in allowed


@dataclass(frozen=True)
class SnapshotRecord:
    """Immutable value object representing a persisted EvidenceSnapshot.

    Using frozen=True ensures the Python object cannot be mutated after creation.
    This is the in-memory representation; the database row is also immutable.
    """
    snapshot_id: str
    case_id: str
    evidence_hash: str
    manifest_hash: str
    snapshot_version: int
    created_at: datetime
    created_by: str
    evidence_count: int
    status: str

    def to_dict(self) -> dict:
        """Deterministic serialization with stable key ordering."""
        return {
            "case_id": self.case_id,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "evidence_count": self.evidence_count,
            "evidence_hash": self.evidence_hash,
            "manifest_hash": self.manifest_hash,
            "snapshot_id": self.snapshot_id,
            "snapshot_version": self.snapshot_version,
            "status": self.status,
        }


class EvidenceSnapshotService:
    """In-memory service for EvidenceSnapshot CRUD (no database dependency).

    This service manages snapshots using an in-memory store, suitable for
    testing and verification. A database-backed implementation will replace
    the storage layer in production but must preserve the same invariants.

    Invariants enforced:
      1. Append-only: create() adds, never overwrites.
      2. Immutable: update() and delete() always raise ImmutableSnapshotError.
      3. Monotonic versioning: each case's snapshots get v1, v2, v3, ...
      4. Supersession: creating a new snapshot for a case supersedes the old active one.
      5. Unique IDs: every snapshot gets a unique UUID.
      6. Valid state transitions: only forward transitions allowed.
    """

    def __init__(self) -> None:
        # snapshot_id → SnapshotRecord
        self._store: dict[str, SnapshotRecord] = {}
        # case_id → latest version number
        self._case_versions: dict[str, int] = {}

    def create(
        self,
        *,
        case_id: str,
        evidence_hash: str,
        manifest_hash: str,
        created_by: str,
        evidence_count: int = 0,
    ) -> SnapshotRecord:
        """Create a new EvidenceSnapshot. Append-only.

        If the case already has an ACTIVE snapshot, it is marked SUPERSEDED.
        The new snapshot becomes the ACTIVE one with an incremented version.

        Args:
            case_id: The case this evidence belongs to.
            evidence_hash: Pre-computed SHA-256 of evidence content.
            manifest_hash: Pre-computed SHA-256 of the evidence manifest.
            created_by: User ID of the creator.
            evidence_count: Number of evidence items.

        Returns:
            The newly created SnapshotRecord (frozen/immutable).
        """
        # Supersede any existing active snapshot for this case
        for sid, record in self._store.items():
            if record.case_id == case_id and record.status == SnapshotStatus.ACTIVE:
                # Create a new record with superseded status
                # (we cannot mutate the frozen dataclass)
                superseded = SnapshotRecord(
                    snapshot_id=record.snapshot_id,
                    case_id=record.case_id,
                    evidence_hash=record.evidence_hash,
                    manifest_hash=record.manifest_hash,
                    snapshot_version=record.snapshot_version,
                    created_at=record.created_at,
                    created_by=record.created_by,
                    evidence_count=record.evidence_count,
                    status=SnapshotStatus.SUPERSEDED,
                )
                self._store[sid] = superseded

        # Assign next version
        current_version = self._case_versions.get(case_id, 0)
        next_version = current_version + 1
        self._case_versions[case_id] = next_version

        snapshot_id = str(uuid.uuid4())
        now = datetime.now(UTC)

        record = SnapshotRecord(
            snapshot_id=snapshot_id,
            case_id=case_id,
            evidence_hash=evidence_hash,
            manifest_hash=manifest_hash,
            snapshot_version=next_version,
            created_at=now,
            created_by=created_by,
            evidence_count=evidence_count,
            status=SnapshotStatus.ACTIVE,
        )

        self._store[snapshot_id] = record
        return record

    def get(self, snapshot_id: str) -> SnapshotRecord:
        """Retrieve a snapshot by ID.

        Args:
            snapshot_id: The unique snapshot identifier.

        Returns:
            The SnapshotRecord.

        Raises:
            SnapshotNotFoundError: If the snapshot doesn't exist.
        """
        record = self._store.get(snapshot_id)
        if record is None:
            raise SnapshotNotFoundError(f"Snapshot {snapshot_id} not found")
        return record

    def get_active_for_case(self, case_id: str) -> SnapshotRecord | None:
        """Get the current active snapshot for a case, if any."""
        for record in self._store.values():
            if record.case_id == case_id and record.status == SnapshotStatus.ACTIVE:
                return record
        return None

    def get_all_for_case(self, case_id: str) -> list[SnapshotRecord]:
        """Get all snapshots for a case, ordered by version."""
        return sorted(
            [r for r in self._store.values() if r.case_id == case_id],
            key=lambda r: r.snapshot_version,
        )

    def archive(self, snapshot_id: str) -> SnapshotRecord:
        """Transition a snapshot to ARCHIVED status.

        Valid from ACTIVE or SUPERSEDED only. ARCHIVED is terminal.

        Args:
            snapshot_id: The snapshot to archive.

        Returns:
            New SnapshotRecord with ARCHIVED status.

        Raises:
            SnapshotNotFoundError: If the snapshot doesn't exist.
            InvalidStateTransitionError: If transition is not allowed.
        """
        record = self.get(snapshot_id)
        if not SnapshotStatus.is_valid_transition(record.status, SnapshotStatus.ARCHIVED):
            raise InvalidStateTransitionError(
                f"Cannot transition from '{record.status}' to 'archived'. "
                f"Valid transitions from '{record.status}': "
                f"{SnapshotStatus._VALID_TRANSITIONS.get(record.status, set())}"
            )
        archived = SnapshotRecord(
            snapshot_id=record.snapshot_id,
            case_id=record.case_id,
            evidence_hash=record.evidence_hash,
            manifest_hash=record.manifest_hash,
            snapshot_version=record.snapshot_version,
            created_at=record.created_at,
            created_by=record.created_by,
            evidence_count=record.evidence_count,
            status=SnapshotStatus.ARCHIVED,
        )
        self._store[snapshot_id] = archived
        return archived

    def update(self, snapshot_id: str, **kwargs) -> None:
        """ALWAYS raises ImmutableSnapshotError.

        EvidenceSnapshots are immutable. This method exists to explicitly
        enforce the invariant and produce a clear error message.
        """
        raise ImmutableSnapshotError(
            f"Cannot modify EvidenceSnapshot {snapshot_id}. "
            "Snapshots are immutable after creation (ED-003). "
            "Create a new snapshot to supersede this one."
        )

    def delete(self, snapshot_id: str) -> None:
        """ALWAYS raises ImmutableSnapshotError.

        EvidenceSnapshots are append-only. This method exists to explicitly
        enforce the invariant and produce a clear error message.
        """
        raise ImmutableSnapshotError(
            f"Cannot delete EvidenceSnapshot {snapshot_id}. "
            "Snapshots are append-only and never deleted (ED-003)."
        )

    @property
    def count(self) -> int:
        """Total number of snapshots in the store."""
        return len(self._store)



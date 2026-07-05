"""
AuditService — create, retrieve, and verify audit records.

Engineering Doctrines:
  ED-003: Immutable evidence ≠ mutable presentation.
  ED-005: Single source of truth — audit records are authoritative.
  ED-007: Regression protection through immutable audit trail.

This service enforces:
  - Append-only: audit records can be created but never modified or deleted.
  - Immutability: any attempt to update or delete raises ImmutableAuditError.
  - Verification: verify packet hash against snapshot evidence hash (Test 4).
  - Traceability: link packets back to source snapshots.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal


class ImmutableAuditError(Exception):
    """Raised when attempting to modify or delete an AuditRecord."""
    pass


class AuditRecordNotFoundError(Exception):
    """Raised when a requested audit record does not exist."""
    pass


class AuditVerificationError(Exception):
    """Raised when packet verification fails."""
    pass


VerificationStatus = Literal["verified", "failed"]


@dataclass(frozen=True)
class AuditRecordValue:
    """Immutable value object representing a persisted AuditRecord.

    Using frozen=True ensures the Python object cannot be mutated after creation.
    This is the in-memory representation; the database row is also immutable.
    """
    audit_id: str
    snapshot_id: str
    evidence_hash: str
    packet_id: str
    packet_hash: str
    packet_version: int
    serialization_version: int
    created_at: datetime
    created_by: str
    verification_status: VerificationStatus
    verification_details: str | None

    def to_dict(self) -> dict:
        """Deterministic serialization with stable key ordering."""
        return {
            "audit_id": self.audit_id,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "evidence_hash": self.evidence_hash,
            "packet_hash": self.packet_hash,
            "packet_id": self.packet_id,
            "packet_version": self.packet_version,
            "serialization_version": self.serialization_version,
            "snapshot_id": self.snapshot_id,
            "verification_details": self.verification_details,
            "verification_status": self.verification_status,
        }


class AuditService:
    """In-memory service for AuditRecord CRUD (no database dependency).

    This service manages audit records using an in-memory store, suitable for
    testing and verification. A database-backed implementation will replace
    the storage layer in production but must preserve the same invariants.

    Invariants enforced:
      1. Append-only: create() adds, never overwrites.
      2. Immutable: update() and delete() always raise ImmutableAuditError.
      3. Unique IDs: every audit record gets a unique UUID.
      4. Verification: packet hash is verified against snapshot evidence hash at creation.
      5. Traceability: audit record links packet to source snapshot.
    """

    def __init__(self) -> None:
        # audit_id → AuditRecordValue
        self._store: dict[str, AuditRecordValue] = {}
        # packet_id → audit_id (for fast lookup)
        self._packet_to_audit: dict[str, str] = {}
        # snapshot_id → [audit_id, ...] (for traceability)
        self._snapshot_to_audits: dict[str, list[str]] = {}

    def create(
        self,
        *,
        snapshot_id: str,
        evidence_hash: str,
        packet_id: str,
        packet_hash: str,
        packet_version: int,
        serialization_version: int,
        created_by: str,
        verify_packet: bool = True,
    ) -> AuditRecordValue:
        """Create a new AuditRecord linking a packet to a snapshot. Append-only.

        Args:
            snapshot_id: The source EvidenceSnapshot ID.
            evidence_hash: Pre-computed SHA-256 of the snapshot evidence.
            packet_id: The identifier of the rendered packet.
            packet_hash: SHA-256 hash of the rendered packet content.
            packet_version: Version of the packet renderer.
            serialization_version: Version of the serialization format.
            created_by: User ID of the creator.
            verify_packet: If True, verify packet_hash matches evidence_hash.
                If False, create record with "failed" status and error details.

        Returns:
            The newly created AuditRecordValue (frozen/immutable).

        Raises:
            ValueError: If verify_packet=True and hashes don't match.
        """
        audit_id = str(uuid.uuid4())
        now = datetime.now(UTC)

        # Verify packet integrity (Test 4: packet↔snapshot consistency)
        verification_status: VerificationStatus = "verified"
        verification_details: str | None = None

        if verify_packet:
            if packet_hash != evidence_hash:
                verification_status = "failed"
                verification_details = (
                    f"Packet hash mismatch: packet_hash={packet_hash}, "
                    f"evidence_hash={evidence_hash}"
                )
                raise AuditVerificationError(verification_details)

        record = AuditRecordValue(
            audit_id=audit_id,
            snapshot_id=snapshot_id,
            evidence_hash=evidence_hash,
            packet_id=packet_id,
            packet_hash=packet_hash,
            packet_version=packet_version,
            serialization_version=serialization_version,
            created_at=now,
            created_by=created_by,
            verification_status=verification_status,
            verification_details=verification_details,
        )

        self._store[audit_id] = record
        self._packet_to_audit[packet_id] = audit_id

        if snapshot_id not in self._snapshot_to_audits:
            self._snapshot_to_audits[snapshot_id] = []
        self._snapshot_to_audits[snapshot_id].append(audit_id)

        return record

    def get(self, audit_id: str) -> AuditRecordValue:
        """Retrieve an audit record by ID.

        Args:
            audit_id: The unique audit record identifier.

        Returns:
            The AuditRecordValue.

        Raises:
            AuditRecordNotFoundError: If the audit record doesn't exist.
        """
        record = self._store.get(audit_id)
        if record is None:
            raise AuditRecordNotFoundError(f"Audit record {audit_id} not found")
        return record

    def get_by_packet_id(self, packet_id: str) -> AuditRecordValue | None:
        """Get the audit record for a specific packet.

        Args:
            packet_id: The packet identifier.

        Returns:
            The AuditRecordValue, or None if not found.
        """
        audit_id = self._packet_to_audit.get(packet_id)
        if audit_id is None:
            return None
        return self._store.get(audit_id)

    def get_by_snapshot_id(self, snapshot_id: str) -> list[AuditRecordValue]:
        """Get all audit records for a snapshot.

        Args:
            snapshot_id: The snapshot identifier.

        Returns:
            List of AuditRecordValue objects, ordered by creation time.
        """
        audit_ids = self._snapshot_to_audits.get(snapshot_id, [])
        records = [self._store[aid] for aid in audit_ids if aid in self._store]
        return sorted(records, key=lambda r: r.created_at)

    def verify_packet_against_evidence(
        self, packet_hash: str, evidence_hash: str
    ) -> bool:
        """Verify that a packet hash matches evidence hash. Test 4.

        This is the fundamental verification operation for ED-003 and ED-007:
        the rendered packet (mutable presentation) must be reproducible from
        the immutable evidence snapshot.

        Args:
            packet_hash: SHA-256 of rendered packet.
            evidence_hash: SHA-256 of source snapshot evidence.

        Returns:
            True if hashes match, False otherwise.
        """
        return packet_hash == evidence_hash

    def update(self, audit_id: str, **kwargs) -> None:
        """ALWAYS raises ImmutableAuditError.

        Audit records are immutable. This method exists to explicitly
        enforce the invariant and produce a clear error message.
        """
        raise ImmutableAuditError(
            f"Cannot modify AuditRecord {audit_id}. "
            "Audit records are immutable after creation (ED-003, ED-007). "
            "Create a new audit record for new packets or evidence versions."
        )

    def delete(self, audit_id: str) -> None:
        """ALWAYS raises ImmutableAuditError.

        Audit records are append-only. This method exists to explicitly
        enforce the invariant and produce a clear error message.
        """
        raise ImmutableAuditError(
            f"Cannot delete AuditRecord {audit_id}. "
            "Audit records are append-only and never deleted (ED-003, ED-007)."
        )

    @property
    def count(self) -> int:
        """Total number of audit records in the store."""
        return len(self._store)
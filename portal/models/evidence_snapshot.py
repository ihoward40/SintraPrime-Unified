"""
EvidenceSnapshot — immutable, append-only evidence record.

Engineering Doctrines:
  ED-003: Immutable evidence separate from mutable presentation.
  ED-005: Single source of truth for evidence integrity.

This model is NEVER modified after creation. To supersede a snapshot,
create a new snapshot with a new SnapshotID and incremented version.
The original remains permanently in the database.
"""

from __future__ import annotations

import enum as _enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class SnapshotStatus(_enum.StrEnum):
    """Lifecycle status for an EvidenceSnapshot.

    State transitions:
      ACTIVE → SUPERSEDED  (when a new snapshot is created for the same case)
      ACTIVE → ARCHIVED    (when evidence is no longer operationally relevant)
      SUPERSEDED → ARCHIVED (governance/retention policy)

    No reverse transitions. No deletion.
    """
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class EvidenceSnapshot(Base):
    """
    Immutable, append-only evidence snapshot.

    Invariants:
      - No updated_at column: rows are never modified.
      - No soft-delete: rows are never removed.
      - Status transitions: ACTIVE → SUPERSEDED | ARCHIVED; SUPERSEDED → ARCHIVED.
      - All fields are set at creation time and frozen thereafter.

    The EvidenceHash and ManifestHash fields store pre-computed hashes.
    Hash computation (the hash boundary function) belongs to Step 2;
    this model accepts hashes as inputs without computing them.
    """
    __tablename__ = "evidence_snapshots"

    # ── Identity ──────────────────────────────────────────────────────
    snapshot_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
    )
    case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cases.id"), nullable=False, index=True,
    )

    # ── Evidence integrity ────────────────────────────────────────────
    evidence_hash: Mapped[str] = mapped_column(
        String(64), nullable=False,
        doc="SHA-256 hex digest of immutable evidence content.",
    )
    manifest_hash: Mapped[str] = mapped_column(
        String(64), nullable=False,
        doc="SHA-256 hex digest of the evidence manifest.",
    )

    # ── Versioning ────────────────────────────────────────────────────
    snapshot_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1,
        doc="Monotonically increasing version per case. v1, v2, v3, ...",
    )

    # ── Provenance ────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Server-set creation timestamp. Never modified.",
    )
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False,
        doc="User who created this snapshot.",
    )

    # ── Content metadata ──────────────────────────────────────────────
    evidence_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        doc="Number of evidence items included in this snapshot.",
    )

    # ── Status ────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SnapshotStatus.ACTIVE,
        doc="'active', 'superseded', or 'archived'. Forward transitions only.",
    )

    # ── NO updated_at, NO deleted_at ──────────────────────────────────
    # This is intentional. EvidenceSnapshot rows are immutable.
    # See ED-003: immutable evidence ≠ mutable presentation.

    __table_args__ = ()

    def to_dict(self) -> dict:
        """Deterministic serialization for verification.

        Returns a plain dict with stable key ordering (alphabetical).
        Timestamps are serialized as ISO-8601 UTC strings.
        This representation is reproducible: the same snapshot always
        produces the same dict output.
        """
        return {
            "case_id": self.case_id,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "created_by": self.created_by,
            "evidence_count": self.evidence_count,
            "evidence_hash": self.evidence_hash,
            "manifest_hash": self.manifest_hash,
            "snapshot_id": self.snapshot_id,
            "snapshot_version": self.snapshot_version,
            "status": self.status,
        }

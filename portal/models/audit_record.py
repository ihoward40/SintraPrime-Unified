"""
AuditRecord — immutable, append-only audit trail linking packets to snapshots.

Engineering Doctrines:
  ED-003: Immutable evidence separate from mutable presentation.
  ED-005: Single source of truth for audit integrity.
  ED-007: Regression protection through immutable audit trail.

This model records the link between rendered packets and their source snapshots.
Each record is permanent and never modified. No deletion, no updates.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .types import PortableUUID


class AuditRecord(Base):
    """
    Immutable, append-only audit record linking rendered packets to snapshots.

    Invariants:
      - No updated_at column: rows are never modified.
      - No soft-delete: rows are never removed.
      - All fields are set at creation time and frozen thereafter.
      - Records the complete chain: snapshot → evidence hash → packet → packet hash

    Purpose:
      - Verify packet integrity against its source snapshot
      - Trace packet provenance back to snapshot version
      - Maintain audit trail for ED-007 regression verification
      - Support Test 4: packet↔snapshot consistency verification
    """
    __tablename__ = "audit_records"

    # ── Identity ──────────────────────────────────────────────────────
    audit_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, primary_key=True, default=uuid.uuid4,
        doc="Unique audit record identifier.",
    )

    # ── Evidence chain ────────────────────────────────────────────────
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("evidence_snapshots.snapshot_id"),
        nullable=False, index=True,
        doc="Source EvidenceSnapshot this audit record references.",
    )
    evidence_hash: Mapped[str] = mapped_column(
        String(64), nullable=False,
        doc="SHA-256 hex digest of the source snapshot evidence (immutable copy).",
    )

    # ── Packet identity ───────────────────────────────────────────────
    packet_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, nullable=False, index=True,
        doc="Identifier of the rendered EvidencePacket.",
    )
    packet_hash: Mapped[str] = mapped_column(
        String(64), nullable=False,
        doc="SHA-256 hex digest of the rendered packet content.",
    )

    # ── Serialization metadata ────────────────────────────────────────
    packet_version: Mapped[int] = mapped_column(
        nullable=False,
        doc="Version of the packet renderer that produced this packet.",
    )
    serialization_version: Mapped[int] = mapped_column(
        nullable=False, default=1,
        doc="Version of the canonical serialization format (Step 2).",
    )

    # ── Provenance ────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Server-set creation timestamp. Never modified.",
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("users.id"), nullable=False,
        doc="User/system that created this audit record.",
    )

    # ── Verification metadata ────────────────────────────────────────
    verification_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="verified",
        doc="'verified' (packet hash matches snapshot content), or 'failed' if mismatch detected.",
    )
    verification_details: Mapped[str | None] = mapped_column(
        String(512), nullable=True,
        doc="Optional error details if verification failed.",
    )

    # ── NO updated_at, NO deleted_at ──────────────────────────────────
    # This is intentional. AuditRecord rows are immutable and permanent.
    # See ED-003: immutable evidence ≠ mutable presentation.

    __table_args__ = ()

    def to_dict(self) -> dict:
        """Deterministic serialization for verification.

        Returns a plain dict with stable key ordering (alphabetical).
        Timestamps are serialized as ISO-8601 UTC strings.
        This representation is reproducible for audit verification.
        """
        return {
            "audit_id": str(self.audit_id),
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "created_by": str(self.created_by),
            "evidence_hash": self.evidence_hash,
            "packet_hash": self.packet_hash,
            "packet_id": str(self.packet_id),
            "packet_version": self.packet_version,
            "serialization_version": self.serialization_version,
            "snapshot_id": str(self.snapshot_id),
            "verification_details": self.verification_details,
            "verification_status": self.verification_status,
        }

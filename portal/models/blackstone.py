"""
Evidence Ledger persistence layer for the Blackstone engines.

Stores claims, evidence, sources, recommendations, provenance chains, and
risk records in the portal database. Uses JSON columns to remain flexible
while the BRA data models evolve.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from portal.database import Base
from portal.models.types import PortableUUID


class EvidenceLedger(Base):
    """Append-only ledger of governance knowledge objects."""

    __tablename__ = "evidence_ledger"

    id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    object_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    object_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    parent_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    provenance_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    __table_args__ = (
        Index("ix_evidence_ledger_object", "object_type", "object_id"),
        Index("ix_evidence_ledger_actor", "actor"),
        Index("ix_evidence_ledger_recorded_at", "recorded_at"),
    )


class BlackstoneEvaluation(Base):
    """Snapshot of a Blackstone orchestrator evaluation."""

    __tablename__ = "blackstone_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    case_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    claim_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    question: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    controlling_authority: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    conflicts: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    risks: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    agents: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    evaluated_by: Mapped[str] = mapped_column(String(128), nullable=False, default="system")

    __table_args__ = (
        Index("ix_blackstone_evaluations_claim", "tenant_id", "claim_id"),
        Index("ix_blackstone_evaluations_case", "tenant_id", "case_id"),
        Index("ix_blackstone_evaluations_evaluated_at", "evaluated_at"),
    )

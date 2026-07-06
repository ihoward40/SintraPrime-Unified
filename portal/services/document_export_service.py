"""Document Export Service — bridge Document Vault to Phase 1 evidence platform.

Converts selected Document records into an immutable EvidenceSnapshot, renders an
EvidencePacket, and creates an AuditRecord. The result is a verifiable provenance
chain from uploaded documents through packet export.

Engineering Doctrines:
  ED-003: Immutable evidence ≠ mutable presentation
  ED-005: Single source of truth — snapshots are authoritative
  ED-007: Regression protection through immutable audit trail
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from portal.models.document import Document

from .evidence_audit_service import AuditService
from .evidence_hash_boundary import (
    EvidenceCollection,
    EvidenceItem,
    compute_evidence_hash,
    compute_manifest_hash,
)
from .evidence_snapshot_service import EvidenceSnapshotService
from .packet_renderer import render_packet


class DocumentExportError(Exception):
    """Raised when a document export cannot be completed."""


class DocumentExportResult:
    """Result of exporting documents to a verified evidence packet."""

    def __init__(
        self,
        *,
        snapshot_id: str,
        packet_hash: str,
        audit_id: str,
        evidence_hash: str,
        document_count: int,
        packet_json: str,
    ) -> None:
        self.snapshot_id = snapshot_id
        self.packet_hash = packet_hash
        self.audit_id = audit_id
        self.evidence_hash = evidence_hash
        self.document_count = document_count
        self.packet_json = packet_json


async def export_documents_to_packet(
    *,
    session: AsyncSession,
    case_id: str,
    tenant_id: str,
    user_id: str,
    documents: list[Document],
    snapshot_service: EvidenceSnapshotService | None = None,
    audit_service: AuditService | None = None,
) -> DocumentExportResult:
    """Export a list of documents as a verified evidence packet.

    Args:
        session: SQLAlchemy async session (for any future DB persistence).
        case_id: The case these documents belong to.
        tenant_id: Tenant scope for RLS/audit context.
        user_id: User performing the export.
        documents: List of Document ORM objects to include. Must be active and
            non-deleted; caller is responsible for filtering.
        snapshot_service: Optional EvidenceSnapshotService (injected for tests).
        audit_service: Optional AuditService (injected for tests).

    Returns:
        DocumentExportResult with snapshot, packet, and audit identifiers.

    Raises:
        DocumentExportError: If no documents are provided or content is missing.
    """
    if not documents:
        raise DocumentExportError("At least one document is required for export")

    items = []
    for doc in documents:
        # Map document MIME type / category to evidence item type
        item_type = _infer_evidence_type(doc)
        items.append(
            EvidenceItem(
                item_id=str(doc.id),
                item_type=item_type,
                title=doc.name,
                content=_build_document_summary(doc),
                sequence=doc.current_version,
            )
        )

    evidence = EvidenceCollection(case_id=case_id, items=tuple(items))
    evidence_hash = compute_evidence_hash(evidence)
    manifest_hash = compute_manifest_hash(evidence)

    svc = snapshot_service or EvidenceSnapshotService()
    snapshot = svc.create(
        case_id=case_id,
        evidence_hash=evidence_hash,
        manifest_hash=manifest_hash,
        created_by=user_id,
        evidence_count=len(items),
    )

    packet = render_packet(
        snapshot_id=snapshot.snapshot_id,
        case_id=case_id,
        evidence_hash=evidence_hash,
        manifest_hash=manifest_hash,
        snapshot_version=snapshot.snapshot_version,
        snapshot_created=snapshot.created_at,
        created_by=user_id,
        evidence=evidence,
    )

    audit = (audit_service or AuditService()).create(
        snapshot_id=snapshot.snapshot_id,
        evidence_hash=evidence_hash,
        packet_id=packet.packet_hash,
        packet_hash=packet.packet_hash,
        packet_version=int(packet.packet_version.split(".")[0]),
        serialization_version=packet.serialization_version,
        created_by=user_id,
        verify_packet=False,
    )

    return DocumentExportResult(
        snapshot_id=snapshot.snapshot_id,
        packet_hash=packet.packet_hash,
        audit_id=audit.audit_id,
        evidence_hash=evidence_hash,
        document_count=len(items),
        packet_json=packet.to_json(),
    )


def _infer_evidence_type(doc: Document) -> str:
    """Infer an evidence item type from document metadata."""
    mime = (doc.mime_type or "").lower()
    if "pdf" in mime:
        return "exhibit"
    if doc.name and any(kw in doc.name.lower() for kw in ("motion", "brief", "petition")):
        return "authority"
    if doc.name and any(kw in doc.name.lower() for kw in ("agreement", "contract", "settlement")):
        return "exhibit"
    return "fact"


def _build_document_summary(doc: Document) -> str:
    """Build a content summary for the evidence item from document metadata."""
    parts = [
        f"Document: {doc.name}",
        f"MIME type: {doc.mime_type}",
        f"Size: {doc.size_bytes} bytes",
        f"SHA-256: {doc.checksum_sha256}",
        f"Storage: {doc.storage_bucket}/{doc.storage_key}",
        f"Version: {doc.current_version}",
    ]
    if doc.description:
        parts.append(f"Description: {doc.description}")
    if doc.ai_category:
        parts.append(f"AI category: {doc.ai_category}")
    if doc.ocr_text:
        parts.append(f"OCR preview: {doc.ocr_text[:500]}")
    return "\n".join(parts)

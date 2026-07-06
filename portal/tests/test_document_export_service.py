"""Tests for Document Export Service — Phase 1 evidence integration."""

from __future__ import annotations

import uuid

import pytest

from portal.services.document_export_service import (
    DocumentExportError,
    export_documents_to_packet,
)


class FakeDocument:
    """Minimal stand-in for portal.models.document.Document."""

    def __init__(
        self,
        *,
        name: str,
        mime_type: str,
        size_bytes: int,
        checksum_sha256: str,
        current_version: int = 1,
        description: str | None = None,
        storage_bucket: str = "test-bucket",
        storage_key: str = "test/key",
        ai_category: str | None = None,
        ocr_text: str | None = None,
    ) -> None:
        self.id = uuid.uuid4()
        self.name = name
        self.mime_type = mime_type
        self.size_bytes = size_bytes
        self.checksum_sha256 = checksum_sha256
        self.current_version = current_version
        self.description = description
        self.storage_bucket = storage_bucket
        self.storage_key = storage_key
        self.ai_category = ai_category
        self.ocr_text = ocr_text


class TestDocumentExportService:
    @pytest.mark.asyncio
    async def test_export_single_document_creates_snapshot_packet_and_audit(self):
        doc = FakeDocument(
            name="Bank Statement.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            checksum_sha256="a" * 64,
        )

        result = await export_documents_to_packet(
            session=None,  # service does not use DB session yet
            case_id="case-001",
            tenant_id="tenant-001",
            user_id="user-001",
            documents=[doc],
        )

        assert result.document_count == 1
        assert result.snapshot_id
        assert result.packet_hash
        assert result.audit_id
        assert result.evidence_hash
        assert result.packet_json
        assert doc.name in result.packet_json
        assert "Document:" in result.packet_json
        assert "Storage:" in result.packet_json

    @pytest.mark.asyncio
    async def test_export_multiple_documents_maps_evidence_types(self):
        docs = [
            FakeDocument(name="Bank Statement.pdf", mime_type="application/pdf", size_bytes=512, checksum_sha256="a" * 64),
            FakeDocument(name="Motion to Dismiss.pdf", mime_type="application/pdf", size_bytes=1024, checksum_sha256="b" * 64),
            FakeDocument(name="Settlement Agreement.pdf", mime_type="application/pdf", size_bytes=2048, checksum_sha256="c" * 64),
            FakeDocument(name="Residence Note.txt", mime_type="text/plain", size_bytes=128, checksum_sha256="d" * 64),
        ]

        result = await export_documents_to_packet(
            session=None,
            case_id="case-002",
            tenant_id="tenant-001",
            user_id="user-001",
            documents=docs,
        )

        assert result.document_count == 4
        assert len(result.packet_json) > 0
        # All four titles appear in the rendered packet JSON
        for doc in docs:
            assert doc.name in result.packet_json

    @pytest.mark.asyncio
    async def test_export_empty_documents_raises(self):
        with pytest.raises(DocumentExportError, match="At least one document"):
            await export_documents_to_packet(
                session=None,
                case_id="case-003",
                tenant_id="tenant-001",
                user_id="user-001",
                documents=[],
            )

    @pytest.mark.asyncio
    async def test_export_uses_injected_services(self):
        from portal.services.evidence_audit_service import AuditService
        from portal.services.evidence_snapshot_service import EvidenceSnapshotService

        doc = FakeDocument(
            name="Injection Test.pdf",
            mime_type="application/pdf",
            size_bytes=256,
            checksum_sha256="e" * 64,
        )
        snapshot_service = EvidenceSnapshotService()
        audit_service = AuditService()

        result = await export_documents_to_packet(
            session=None,
            case_id="case-004",
            tenant_id="tenant-001",
            user_id="user-001",
            documents=[doc],
            snapshot_service=snapshot_service,
            audit_service=audit_service,
        )

        # Verify the audit record was persisted in the injected audit service
        retrieved = audit_service.get(result.audit_id)
        assert retrieved.snapshot_id == result.snapshot_id
        assert retrieved.packet_id == result.packet_hash

        # Verify snapshot exists in the injected snapshot service
        snapshot = snapshot_service.get(result.snapshot_id)
        assert snapshot.evidence_hash == result.evidence_hash

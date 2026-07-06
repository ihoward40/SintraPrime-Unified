"""API integration tests for POST /documents/cases/{case_id}/export-packet."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from portal.auth.jwt_handler import create_access_token
from portal.auth.rbac import Permission
from portal.main import create_app


def _make_token(
    *,
    user_id: str,
    tenant_id: str,
    role: str,
    permissions: list[str],
) -> str:
    return create_access_token(
        user_id=user_id,
        tenant_id=tenant_id,
        role=role,
        permissions=permissions,
    )


def _make_doc(*, doc_id: str, tenant_id: str, case_id: str, name: str = "Test Doc"):
    doc = MagicMock()
    doc.id = uuid.UUID(doc_id)
    doc.tenant_id = uuid.UUID(tenant_id)
    doc.case_id = uuid.UUID(case_id)
    doc.name = name
    doc.mime_type = "application/pdf"
    doc.file_extension = "pdf"
    doc.size_bytes = 1024
    doc.checksum_sha256 = "a" * 64
    doc.storage_object_name = "obj-1"
    doc.encrypted = False
    doc.ai_category = "legal"
    doc.is_confidential = False
    doc.current_version = 1
    doc.created_at = datetime.now(UTC)
    doc.updated_at = datetime.now(UTC)
    doc.description = None
    doc.tags = []
    return doc


TENANT_1 = "11111111-1111-1111-1111-111111111111"
TENANT_2 = "22222222-2222-2222-2222-222222222222"


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def auth_headers_attorney():
    token = _make_token(
        user_id="11111111-1111-1111-1111-111111111112",
        tenant_id=TENANT_1,
        role="ATTORNEY",
        permissions=list(Permission),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_client():
    token = _make_token(
        user_id="11111111-1111-1111-1111-111111111113",
        tenant_id=TENANT_1,
        role="CLIENT",
        permissions=[Permission.DOC_READ],  # client has read in this tenant
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_no_doc_read():
    token = _make_token(
        user_id="11111111-1111-1111-1111-111111111114",
        tenant_id=TENANT_1,
        role="PARALEGAL",
        permissions=[Permission.DOC_UPLOAD],  # missing DOC_READ
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_wrong_tenant():
    token = _make_token(
        user_id="22222222-2222-2222-2222-222222222222",
        tenant_id=TENANT_2,
        role="ATTORNEY",
        permissions=list(Permission),
    )
    return {"Authorization": f"Bearer {token}"}


def _fake_db(documents=None):
    """Build a mocked AsyncSession that returns the given documents for .execute()."""
    documents = documents or []
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = documents
    session.execute.return_value = mock_result
    return session


def _patch_get_db(app, documents=None):
    from portal.database import get_db

    async def _override_get_db():
        yield _fake_db(documents)

    app.dependency_overrides[get_db] = _override_get_db


def _remove_override(app):
    from portal.database import get_db

    app.dependency_overrides.pop(get_db, None)


class TestDocumentExportEndpoint:
    """Integration tests for the M3 export-packet endpoint."""

    def test_export_packet_happy_path(self, client, auth_headers_attorney):
        """Authorized user with DOC_READ can export selected documents."""
        doc_id = str(uuid.uuid4())
        case_id = str(uuid.uuid4())
        doc = _make_doc(doc_id=doc_id, tenant_id=TENANT_1, case_id=case_id)
        _patch_get_db(client.app, [doc])

        try:
            response = client.post(
                f"/api/v1/documents/cases/{case_id}/export-packet",
                json={"document_ids": [doc_id]},
                headers=auth_headers_attorney,
            )
        finally:
            _remove_override(client.app)

        assert response.status_code == 200
        data = response.json()
        assert "snapshot_id" in data
        assert "packet_hash" in data
        assert "audit_id" in data
        assert "evidence_hash" in data
        assert data["document_count"] == 1
        assert data["packet_json"]

    def test_export_packet_client_with_doc_read(self, client, auth_headers_client):
        """A client role with DOC_READ permission can export documents."""
        doc_id = str(uuid.uuid4())
        case_id = str(uuid.uuid4())
        doc = _make_doc(doc_id=doc_id, tenant_id=TENANT_1, case_id=case_id)
        _patch_get_db(client.app, [doc])

        try:
            response = client.post(
                f"/api/v1/documents/cases/{case_id}/export-packet",
                json={"document_ids": [doc_id]},
                headers=auth_headers_client,
            )
        finally:
            _remove_override(client.app)

        assert response.status_code == 200
        assert response.json()["document_count"] == 1

    def test_export_packet_missing_permission_returns_403(self, client, auth_headers_no_doc_read):
        """User without DOC_READ cannot access the export endpoint."""
        case_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        _patch_get_db(client.app, [])

        try:
            response = client.post(
                f"/api/v1/documents/cases/{case_id}/export-packet",
                json={"document_ids": [doc_id]},
                headers=auth_headers_no_doc_read,
            )
        finally:
            _remove_override(client.app)

        assert response.status_code == 403
        assert "DOC_READ" in response.json()["detail"] or "Missing permissions" in response.json()["detail"]

    def test_export_packet_missing_document_returns_404(self, client, auth_headers_attorney):
        """Requesting a document that does not exist or is not accessible returns 404."""
        case_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        _patch_get_db(client.app, [])  # no documents returned

        try:
            response = client.post(
                f"/api/v1/documents/cases/{case_id}/export-packet",
                json={"document_ids": [doc_id]},
                headers=auth_headers_attorney,
            )
        finally:
            _remove_override(client.app)

        assert response.status_code == 404

    def test_export_packet_cross_tenant_document_not_accessible(self, client, auth_headers_attorney):
        """A document from another tenant must not be exported."""
        doc_id = str(uuid.uuid4())
        case_id = str(uuid.uuid4())
        # document belongs to a different tenant; DB filter should exclude it
        _ = _make_doc(doc_id=doc_id, tenant_id=TENANT_2, case_id=case_id)
        _patch_get_db(client.app, [])

        try:
            response = client.post(
                f"/api/v1/documents/cases/{case_id}/export-packet",
                json={"document_ids": [doc_id]},
                headers=auth_headers_attorney,
            )
        finally:
            _remove_override(client.app)

        assert response.status_code == 404

    def test_export_packet_no_auth_returns_401(self, client):
        """Missing Authorization header returns 401."""
        case_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        _patch_get_db(client.app, [])

        try:
            response = client.post(
                f"/api/v1/documents/cases/{case_id}/export-packet",
                json={"document_ids": [doc_id]},
            )
        finally:
            _remove_override(client.app)

        assert response.status_code == 401

    def test_export_packet_multiple_documents(self, client, auth_headers_attorney):
        """Exporting multiple documents creates a single packet with all items."""
        case_id = str(uuid.uuid4())
        doc1_id = str(uuid.uuid4())
        doc2_id = str(uuid.uuid4())
        docs = [
            _make_doc(doc_id=doc1_id, tenant_id=TENANT_1, case_id=case_id, name="Doc One"),
            _make_doc(doc_id=doc2_id, tenant_id=TENANT_1, case_id=case_id, name="Doc Two"),
        ]
        _patch_get_db(client.app, docs)

        try:
            response = client.post(
                f"/api/v1/documents/cases/{case_id}/export-packet",
                json={"document_ids": [doc1_id, doc2_id]},
                headers=auth_headers_attorney,
            )
        finally:
            _remove_override(client.app)

        assert response.status_code == 200
        data = response.json()
        assert data["document_count"] == 2
        assert data["snapshot_id"]
        assert data["packet_hash"]

    def test_export_packet_response_contains_distinct_hashes(self, client, auth_headers_attorney):
        """evidence_hash (immutable content) must differ from packet_hash (presentation)."""
        doc_id = str(uuid.uuid4())
        case_id = str(uuid.uuid4())
        doc = _make_doc(doc_id=doc_id, tenant_id=TENANT_1, case_id=case_id)
        _patch_get_db(client.app, [doc])

        try:
            response = client.post(
                f"/api/v1/documents/cases/{case_id}/export-packet",
                json={"document_ids": [doc_id]},
                headers=auth_headers_attorney,
            )
        finally:
            _remove_override(client.app)

        assert response.status_code == 200
        data = response.json()
        assert data["evidence_hash"] != data["packet_hash"], (
            "ED-003 violation: evidence_hash must be independent of packet_hash"
        )

    def test_export_packet_invalid_payload_returns_422(self, client, auth_headers_attorney):
        """Empty document_ids list violates the schema."""
        case_id = str(uuid.uuid4())
        _patch_get_db(client.app, [])

        try:
            response = client.post(
                f"/api/v1/documents/cases/{case_id}/export-packet",
                json={"document_ids": []},
                headers=auth_headers_attorney,
            )
        finally:
            _remove_override(client.app)

        assert response.status_code == 422

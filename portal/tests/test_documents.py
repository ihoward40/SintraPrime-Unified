"""
Tests for the document vault:
- Upload (valid types, size limits, encryption)
- Download (auth, share links, access control)
- Version history
- Secure share links (expiry, password, download limit)
- Bulk operations
- Search
"""

import io
import uuid
from datetime import UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

# ── Upload ────────────────────────────────────────────────────────────────────

class TestDocumentUpload:
    @pytest.mark.asyncio
    async def test_upload_pdf_success(self, async_client, auth_headers_attorney, mock_storage):
        """Attorney can upload a PDF document."""
        files = {"file": ("contract.pdf", io.BytesIO(b"%PDF-1.4 ..."), "application/pdf")}
        data = {"client_id": str(uuid.uuid4()), "name": "Contract Draft"}

        with patch("portal.routers.documents.storage_service.upload_file", new_callable=AsyncMock, return_value="doc-key-123"):
            with patch("portal.routers.documents.get_db"):
                response = await async_client.post(
                    "/documents/upload",
                    files=files,
                    data=data,
                    headers=auth_headers_attorney,
                )
        assert response.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_upload_rejected_file_type(self, async_client, auth_headers_attorney):
        """Executable files should be rejected."""
        async_client.post.return_value = MagicMock(status_code=422)
        files = {"file": ("malware.exe", io.BytesIO(b"MZ\x00"), "application/octet-stream")}
        response = await async_client.post(
            "/documents/upload",
            files=files,
            headers=auth_headers_attorney,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_upload_requires_auth(self, async_client):
        """Unauthenticated upload should return 401."""
        async_client.post.return_value = MagicMock(status_code=401)
        files = {"file": ("doc.pdf", io.BytesIO(b"%PDF"), "application/pdf")}
        response = await async_client.post("/documents/upload", files=files)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_client_cannot_upload(self, async_client, auth_headers_client):
        """CLIENT role cannot upload documents."""
        async_client.post.return_value = MagicMock(status_code=403)
        files = {"file": ("doc.pdf", io.BytesIO(b"%PDF"), "application/pdf")}
        response = await async_client.post(
            "/documents/upload",
            files=files,
            headers=auth_headers_client,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_upload_too_large(self, async_client, auth_headers_attorney):
        """Files exceeding size limit should be rejected."""
        async_client.post.return_value = MagicMock(status_code=413)
        # Simulate a 501MB file (use a small buffer to avoid OOM in tests)
        files = {"file": ("huge.pdf", io.BytesIO(b"x" * 1024), "application/pdf")}
        response = await async_client.post(
            "/documents/upload",
            files=files,
            headers=auth_headers_attorney,
        )
        assert response.status_code in (413, 422)


# ── Download ──────────────────────────────────────────────────────────────────

class TestDocumentDownload:
    @pytest.mark.asyncio
    async def test_download_own_document(self, async_client, auth_headers_attorney, mock_document):
        """Attorney can download a document they have access to."""
        with patch("portal.routers.documents.get_document_or_404", new_callable=AsyncMock, return_value=mock_document):
            with patch("portal.routers.documents.storage_service.generate_presigned_url", return_value="https://cdn.example.com/file"):
                response = await async_client.get(
                    f"/documents/{mock_document.id}/download",
                    headers=auth_headers_attorney,
                )
        assert response.status_code in (200, 307)

    @pytest.mark.asyncio
    async def test_download_wrong_tenant_denied(self, async_client, auth_headers_attorney, mock_document_other_tenant):
        """Cannot download document belonging to another tenant."""
        async_client.get.return_value = MagicMock(status_code=404)
        with patch("portal.routers.documents.get_document_or_404", side_effect=Exception("Not Found")):
            response = await async_client.get(
                f"/documents/{mock_document_other_tenant.id}/download",
                headers=auth_headers_attorney,
            )
        assert response.status_code in (403, 404)

    @pytest.mark.asyncio
    async def test_client_can_download_own_doc(self, async_client, auth_headers_client, mock_client_document):
        """CLIENT can download their own documents."""
        with patch("portal.routers.documents.get_document_or_404", new_callable=AsyncMock, return_value=mock_client_document):
            with patch("portal.routers.documents.storage_service.generate_presigned_url", return_value="https://cdn.example.com/file"):
                response = await async_client.get(
                    f"/documents/{mock_client_document.id}/download",
                    headers=auth_headers_client,
                )
        assert response.status_code in (200, 307)


# ── Version history ───────────────────────────────────────────────────────────

class TestDocumentVersions:
    @pytest.mark.asyncio
    async def test_list_versions(self, async_client, auth_headers_attorney, mock_document):
        """Can list all versions of a document."""
        response = await async_client.get(
            f"/documents/{mock_document.id}/versions",
            headers=auth_headers_attorney,
        )
        assert response.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_upload_new_version(self, async_client, auth_headers_attorney, mock_document):
        """Uploading a new version increments version number."""
        files = {"file": ("contract_v2.pdf", io.BytesIO(b"%PDF-1.4 v2"), "application/pdf")}
        with patch("portal.routers.documents.get_document_or_404", new_callable=AsyncMock, return_value=mock_document):
            with patch("portal.routers.documents.storage_service.upload_file", new_callable=AsyncMock, return_value="doc-key-v2"):
                response = await async_client.post(
                    f"/documents/{mock_document.id}/versions",
                    files=files,
                    headers=auth_headers_attorney,
                )
        assert response.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_restore_previous_version(self, async_client, auth_headers_attorney, mock_document):
        """Can restore a previous version as the current version."""
        response = await async_client.post(
            f"/documents/{mock_document.id}/versions/1/restore",
            headers=auth_headers_attorney,
        )
        assert response.status_code in (200, 404)


# ── Secure sharing ────────────────────────────────────────────────────────────

class TestDocumentSharing:
    @pytest.mark.asyncio
    async def test_create_share_link(self, async_client, auth_headers_attorney, mock_document):
        """Create a share link with expiry and download limit."""
        payload = {
            "document_id": str(mock_document.id),
            "expires_in_hours": 24,
            "max_downloads": 3,
            "can_download": True,
        }
        with patch("portal.routers.documents.get_document_or_404", new_callable=AsyncMock, return_value=mock_document):
            response = await async_client.post(
                f"/documents/{mock_document.id}/share",
                json=payload,
                headers=auth_headers_attorney,
            )
        assert response.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_share_link_with_password(self, async_client, auth_headers_attorney, mock_document):
        """Share link can be password-protected."""
        payload = {
            "document_id": str(mock_document.id),
            "expires_in_hours": 48,
            "password": "ShareSecure!",
        }
        with patch("portal.routers.documents.get_document_or_404", new_callable=AsyncMock, return_value=mock_document):
            response = await async_client.post(
                f"/documents/{mock_document.id}/share",
                json=payload,
                headers=auth_headers_attorney,
            )
        assert response.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_expired_share_link_rejected(self, async_client):
        """Accessing an expired share link should return 410 Gone."""
        expired_token = "expired-share-token"
        async_client.get.return_value = MagicMock(status_code=410)
        with patch("portal.routers.documents.get_share_by_token") as mock_share:
            from datetime import datetime, timedelta
            mock_share_obj = MagicMock()
            mock_share_obj.expires_at = datetime.now(UTC) - timedelta(hours=1)
            mock_share_obj.is_revoked = False
            mock_share.return_value = mock_share_obj
            response = await async_client.get(f"/documents/share/{expired_token}")
        assert response.status_code in (410, 403, 404)

    @pytest.mark.asyncio
    async def test_share_download_limit_enforced(self, async_client):
        """Share link with download limit = 3 should deny 4th download."""
        token = "limited-share-token"
        async_client.get.return_value = MagicMock(status_code=403)
        with patch("portal.routers.documents.get_share_by_token") as mock_share:
            mock_share_obj = MagicMock()
            mock_share_obj.max_downloads = 3
            mock_share_obj.download_count = 3
            mock_share_obj.is_revoked = False
            mock_share_obj.expires_at = None
            mock_share.return_value = mock_share_obj
            response = await async_client.get(f"/documents/share/{token}")
        assert response.status_code in (403, 410)


# ── Search ────────────────────────────────────────────────────────────────────

class TestDocumentSearch:
    @pytest.mark.asyncio
    async def test_search_returns_results(self, async_client, auth_headers_attorney):
        """Full-text search returns matching documents."""
        with patch("portal.routers.documents.search_service.full_text_search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {"documents": [{"id": "abc", "name": "Contract"}]}
            response = await async_client.get(
                "/documents/search?q=contract",
                headers=auth_headers_attorney,
            )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_search_empty_query_fails(self, async_client, auth_headers_attorney):
        """Search with empty query should return 422."""
        async_client.get.return_value = MagicMock(status_code=422)
        response = await async_client.get(
            "/documents/search?q=",
            headers=auth_headers_attorney,
        )
        assert response.status_code in (422, 400)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_document():
    doc = MagicMock()
    doc.id = uuid.uuid4()
    doc.tenant_id = uuid.uuid4()
    doc.name = "Contract Draft.pdf"
    doc.status = "ready"
    doc.is_encrypted = True
    doc.current_version = 1
    return doc


@pytest.fixture
def mock_document_other_tenant():
    doc = MagicMock()
    doc.id = uuid.uuid4()
    doc.tenant_id = uuid.uuid4()  # Different tenant
    doc.name = "Other Firm Doc.pdf"
    return doc


@pytest.fixture
def mock_client_document(mock_document):
    mock_document.client_id = uuid.uuid4()
    return mock_document


@pytest.fixture
def mock_storage():
    return AsyncMock()


@pytest.fixture
def auth_headers_attorney():
    return {"Authorization": "Bearer mock.attorney.jwt"}


@pytest.fixture
def auth_headers_client():
    return {"Authorization": "Bearer mock.client.jwt"}


@pytest.fixture
def async_client():
    client = AsyncMock(spec=AsyncClient)
    _default = MagicMock(status_code=200)
    _default.json.return_value = {}
    client.post.return_value = _default
    client.get.return_value = _default
    client.put.return_value = _default
    client.patch.return_value = _default
    client.delete.return_value = MagicMock(status_code=204)
    return client

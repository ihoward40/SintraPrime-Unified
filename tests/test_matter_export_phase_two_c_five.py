from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from legal_authority.repository import LegalAuthorityRepository
from portal.auth.jwt_handler import create_access_token
from portal.auth.rbac import ROLE_PERMISSIONS, Permission, Role
from portal.main import create_app
from portal.services.matter_export_service import (
    MatterExportResult,
    MatterExportService,
    render_pdf,
)
from portal.services.matter_intelligence_service import redact_sensitive


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalars(self):
        return self

    def first(self):
        return self._value

    def scalar_one_or_none(self):
        return self._value

    def all(self):
        return self._value if isinstance(self._value, list) else [self._value]


class _FakeDB:
    def __init__(self):
        self.flush = AsyncMock()
        self.event = SimpleNamespace(id="audit-export-1")

    async def execute(self, _statement):
        return _ScalarResult(self.event)


class _FixtureExportService(MatterExportService):
    async def _matter_payload(self, db, matter_id, tenant_id):
        return {
            "id": matter_id,
            "tenant_id": tenant_id,
            "title": "Creditor matter",
            "status": "active",
        }

    async def _rows(self, db, model, matter_id, tenant_id, *, ascending=True):
        name = model.__name__
        fixtures = {
            "MatterParty": [{"id": "party-1", "display_name": "Client", "role": "CLIENT"}],
            "MatterAccount": [
                {"id": "account-1", "account_reference_redacted": "****1234", "status": "open"}
            ],
            "MatterCommunication": [
                {
                    "id": "communication-1",
                    "occurred_at": "2026-08-03T12:00:00+00:00",
                    "subject_redacted": "Dispute sent",
                }
            ],
            "MatterDeadline": [
                {
                    "id": "deadline-1",
                    "due_at": "2026-08-10T12:00:00+00:00",
                    "title": "Response deadline",
                }
            ],
            "MatterEvidenceNode": [
                {"id": "node-1", "title": "Redacted claim", "statement_redacted": "Claim text"}
            ],
            "MatterEvidenceFinding": [
                {"id": "finding-1", "finding_type": "MISSING_EVIDENCE", "status": "OPEN"}
            ],
            "MatterAttachment": [
                {
                    "id": "attachment-1",
                    "label_redacted": "Notice",
                    "checksum_sha256": "a" * 64,
                    "redaction_status": "REDACTED",
                }
            ],
            "MatterAuditEvent": [],
        }
        return fixtures.get(name, [])

    async def _write_audit(self, *args, **kwargs):
        return None


@pytest.mark.asyncio
async def test_packet_contains_required_redacted_sections_hashes_and_pdf():
    service = _FixtureExportService()
    db = _FakeDB()
    result = await service.build_packet(
        db,
        matter_id="matter-1",
        tenant_id="tenant-1",
        actor_id="attorney-1",
        actor_role="ATTORNEY",
        export_format="JSON",
    )
    packet = json.loads(result.content)
    assert packet["schema"] == "sintraprime.matter-export.v1"
    assert packet["chronology"]
    assert packet["sections"]["evidence_findings"]
    assert packet["redacted_evidence_manifest"][0]["redaction_status"] == "REDACTED"
    assert packet["integrity"]["packet_hash"] == result.packet_hash
    assert result.redacted_manifest_hash
    assert result.audit_event_id == "audit-export-1"

    pdf = render_pdf(json.dumps(packet), "Creditor matter")
    assert pdf.startswith(b"%PDF-1.4")
    assert b"%%EOF" in pdf


def test_export_permission_is_limited_to_internal_review_roles():
    assert Permission.MATTER_INTELLIGENCE_EXPORT in ROLE_PERMISSIONS[Role.ATTORNEY]
    assert Permission.MATTER_INTELLIGENCE_EXPORT in ROLE_PERMISSIONS[Role.FIRM_ADMIN]
    assert Permission.MATTER_INTELLIGENCE_EXPORT not in ROLE_PERMISSIONS[Role.CLIENT]
    assert Permission.MATTER_INTELLIGENCE_EXPORT not in ROLE_PERMISSIONS[Role.PARALEGAL]


def test_packet_redaction_defense_in_depth():
    value = redact_sensitive({"statement": "SSN 123-45-6789 and account 123456789012"})
    assert "123-45-6789" not in str(value)
    assert "123456789012" not in str(value)


def _headers(*, role: str, permissions: list[Permission]) -> dict[str, str]:
    token = create_access_token(
        user_id="11111111-1111-1111-1111-111111111112",
        tenant_id="11111111-1111-1111-1111-111111111111",
        role=role,
        permissions=permissions,
    )
    return {"Authorization": f"Bearer {token}"}


def test_export_route_requires_auth_and_registers_scope():
    client = TestClient(create_app())
    assert (
        client.post("/api/v1/matters/matter-1/exports", json={"format": "JSON"}).status_code == 401
    )
    from portal.tests.support.route_enumeration import get_terminal_route_paths

    paths = get_terminal_route_paths(create_app())
    assert "/api/v1/matters/{matter_id}/exports" in paths


def test_export_route_rejects_client_without_export_permission():
    client = TestClient(create_app())
    response = client.post(
        "/api/v1/matters/matter-1/exports",
        json={"format": "JSON"},
        headers=_headers(role="CLIENT", permissions=[Permission.MATTER_INTELLIGENCE_READ]),
    )
    assert response.status_code == 403


def test_export_route_returns_hash_headers(monkeypatch):
    from portal.database import get_db
    from portal.routers import matter_export

    async def fake_build_packet(*_args, **_kwargs):
        return MatterExportResult(
            export_id="export-1",
            matter_id="matter-1",
            export_format="JSON",
            packet_hash="b" * 64,
            redacted_manifest_hash="c" * 64,
            audit_event_id="audit-1",
            content=b'{"schema":"sintra.matter-export.v1"}',
        )

    monkeypatch.setattr(matter_export.service, "build_packet", fake_build_packet)

    # The route depends on `db: AsyncSession = Depends(get_db)` purely to pass
    # it through to `service.build_packet`, which is fully mocked above and
    # never touches `db`. The default `get_db` dependency opens a real
    # PostgreSQL session and executes an RLS-context-setting query merely to
    # construct/yield the session -- before the route body (and therefore
    # the mocked service call) ever runs. Override it here with the same
    # `_FakeDB` fixture already used by the service-level unit test above,
    # matching this repo's established `app.dependency_overrides[get_db]`
    # pattern (see e.g. portal/tests/test_router_coverage.py,
    # portal/tests/test_mission_control_commands.py) so this route-level
    # test exercises only what it claims to verify -- request/response
    # wiring -- without requiring a real database.
    app = create_app()

    async def _override_get_db():
        yield _FakeDB()

    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app)
    response = client.post(
        "/api/v1/matters/matter-1/exports",
        json={"format": "JSON"},
        headers=_headers(role="ATTORNEY", permissions=[Permission.MATTER_INTELLIGENCE_EXPORT]),
    )
    assert response.status_code == 200
    assert response.headers["x-matter-packet-hash"] == "b" * 64
    assert response.headers["x-matter-manifest-hash"] == "c" * 64
    assert response.headers["x-matter-audit-event-id"] == "audit-1"
    assert response.json()["schema"] == "sintra.matter-export.v1"


def test_export_migration_not_needed_and_scope_is_documented():
    migration = (
        LegalAuthorityRepository().root
        / "portal"
        / "migrations"
        / "add_deadline_evidence_intelligence.sql"
    ).read_text(encoding="utf-8")
    assert "matter_deadlines" in migration
    assert "export generation" in migration

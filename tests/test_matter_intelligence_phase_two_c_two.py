from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from legal_authority.repository import LegalAuthorityRepository
from portal.auth.rbac import ROLE_PERMISSIONS, Permission, Role
from portal.main import create_app
from portal.models.matter_intelligence import (
    MatterAccount,
    MatterAssessment,
    MatterAssessmentVersion,
    MatterAttachment,
    MatterAuditEvent,
    MatterCommunication,
    MatterDispute,
    MatterFiling,
    MatterParty,
)
from portal.schemas.matter_intelligence import (
    MatterAssessmentVersionCreate,
    MatterCommunicationCreate,
)
from portal.services.matter_intelligence_service import MatterIntelligenceService, redact_sensitive


def test_matter_intelligence_models_are_persistent_and_tenant_scoped():
    expected = {
        MatterParty: "matter_parties",
        MatterAccount: "matter_accounts",
        MatterFiling: "matter_filings",
        MatterCommunication: "matter_communications",
        MatterDispute: "matter_disputes",
        MatterAttachment: "matter_attachments",
        MatterAssessment: "matter_assessments",
        MatterAssessmentVersion: "matter_assessment_versions",
        MatterAuditEvent: "matter_audit_events",
    }
    for model, table_name in expected.items():
        assert model.__tablename__ == table_name
        assert "tenant_id" in model.__table__.columns
        assert "matter_id" in model.__table__.columns


def test_matter_intelligence_roles_are_explicitly_gated():
    assert Permission.MATTER_INTELLIGENCE_READ in ROLE_PERMISSIONS[Role.ATTORNEY]
    assert Permission.MATTER_INTELLIGENCE_WRITE in ROLE_PERMISSIONS[Role.PARALEGAL]
    assert Permission.MATTER_INTELLIGENCE_REVIEW in ROLE_PERMISSIONS[Role.ACCOUNTANT]
    assert Permission.MATTER_INTELLIGENCE_REVIEW not in ROLE_PERMISSIONS[Role.PARALEGAL]


def test_redaction_removes_sensitive_identifiers_recursively():
    value = {
        "ssn": "123-45-6789",
        "account": "Account 123456789012",
        "nested": ["card 4111111111111111", "ordinary text"],
    }
    redacted = redact_sensitive(value)
    assert "123-45-6789" not in str(redacted)
    assert "123456789012" not in str(redacted)
    assert "4111111111111111" not in str(redacted)
    assert redacted["nested"][1] == "ordinary text"


def test_assessment_version_schema_rejects_extra_fields():
    with pytest.raises(ValueError):
        MatterAssessmentVersionCreate.model_validate({"facts": {}, "unexpected": True})


def test_communication_schema_restricts_direction():
    with pytest.raises(ValueError):
        MatterCommunicationCreate(
            communication_type="email",
            direction="sideways",
            occurred_at="2026-08-03T00:00:00Z",
        )


@pytest.mark.asyncio
async def test_party_reference_validation_is_tenant_and_matter_scoped():
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = ["party-in-scope"]
    db.execute.return_value = result
    service = MatterIntelligenceService()
    await service._party_ids(db, "matter-1", "tenant-1", ["party-in-scope"])
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_party_reference_validation_rejects_cross_matter_reference():
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db.execute.return_value = result
    with pytest.raises(ValueError, match="outside this matter"):
        await MatterIntelligenceService()._party_ids(db, "matter-1", "tenant-1", ["party-other"])


def test_matter_routes_require_authenticated_rbac_context():
    client = TestClient(create_app())
    response = client.get("/api/v1/matters/matter-1/intelligence/parties")
    assert response.status_code == 401
    assert (
        client.post(
            "/api/v1/matters/matter-1/intelligence/assessments",
            json={"assessment_type": "ucc", "title": "Assessment"},
        ).status_code
        == 401
    )


def test_matter_routes_are_registered_without_deadline_or_frontend_surface():
    app = create_app()
    paths = {route.path for route in app.routes}
    assert "/api/v1/matters/{matter_id}/intelligence/parties" in paths
    assert "/api/v1/matters/{matter_id}/intelligence/assessments/{assessment_id}/versions" in paths
    assert not any("deadline" in path for path in paths if "matter" in path)


def test_matter_migration_contains_down_contract_and_no_deadline_engine():
    migration = (
        LegalAuthorityRepository().root / "portal" / "migrations" / "add_matter_intelligence.sql"
    ).read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS matter_assessment_versions" in migration
    assert "CREATE TABLE IF NOT EXISTS matter_audit_events" in migration
    assert "-- DOWN MIGRATION:" in migration
    assert "matter_deadlines" not in migration

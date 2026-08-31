from __future__ import annotations

import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from legal_authority.repository import LegalAuthorityRepository
from portal.main import create_app
from portal.models.deadline_evidence import (
    MatterDeadline,
    MatterDeadlineVersion,
    MatterEvidenceFinding,
    MatterEvidenceLink,
    MatterEvidenceNode,
)
from portal.schemas.deadline_evidence import MatterEvidenceLinkCreate
from portal.services.deadline_evidence_service import DeadlineEvidenceService
from portal.services.matter_intelligence_service import MatterIntelligenceError


def test_deadline_and_evidence_models_are_tenant_scoped():
    for model in (
        MatterDeadline,
        MatterDeadlineVersion,
        MatterEvidenceNode,
        MatterEvidenceLink,
        MatterEvidenceFinding,
    ):
        assert "tenant_id" in model.__table__.columns
        assert "matter_id" in model.__table__.columns


def test_calendar_deadline_is_timezone_safe():
    trigger = datetime.fromisoformat("2026-08-03T09:00:00-04:00")
    due = DeadlineEvidenceService.calculate_due_at(
        trigger, timezone_name="America/New_York", calendar_type="CALENDAR_DAYS", days_count=5
    )
    assert due.isoformat() == "2026-08-08T09:00:00-04:00"


def test_business_deadline_skips_weekends_and_holidays():
    trigger = datetime.fromisoformat("2026-08-07T09:00:00-04:00")
    due = DeadlineEvidenceService.calculate_due_at(
        trigger,
        timezone_name="America/New_York",
        calendar_type="BUSINESS_DAYS",
        days_count=1,
        holidays=["2026-08-10"],
    )
    assert due.date().isoformat() == "2026-08-11"


def test_naive_or_unknown_timezone_requires_reviewable_error():
    with pytest.raises(MatterIntelligenceError, match="timezone"):
        DeadlineEvidenceService.calculate_due_at(
            datetime.fromisoformat("2026-08-03T09:00:00"),
            timezone_name="America/New_York",
            calendar_type="CALENDAR_DAYS",
            days_count=1,
        )
    with pytest.raises(MatterIntelligenceError, match="unknown timezone"):
        DeadlineEvidenceService.calculate_due_at(
            datetime.fromisoformat("2026-08-03T09:00:00-04:00"),
            timezone_name="Mars/Phobos",
            calendar_type="CALENDAR_DAYS",
            days_count=1,
        )


def test_evidence_link_schema_rejects_invalid_relationship():
    with pytest.raises(ValueError):
        MatterEvidenceLinkCreate(
            source_node_id="a", target_node_id="b", relationship_type="INSTRUCTS"
        )


def test_evidence_approval_requires_attorney():
    service = DeadlineEvidenceService()
    db = AsyncMock()
    db.execute.side_effect = [
        SimpleNamespace(scalar_one_or_none=lambda: object()),
        SimpleNamespace(scalar_one_or_none=lambda: SimpleNamespace(id="node-1")),
    ]
    with pytest.raises(MatterIntelligenceError, match="attorney"):
        asyncio.run(
            service.review_evidence_node(
                db,
                "node-1",
                "matter-1",
                "tenant-1",
                "actor-1",
                "PARALEGAL",
                {"review_status": "APPROVED", "notes": "approve"},
            )
        )


def test_routes_require_authentication_and_register_scope():
    client = TestClient(create_app())
    assert client.get("/api/v1/matters/matter-1/intelligence/deadlines").status_code == 401
    from portal.tests.support.route_enumeration import get_terminal_route_paths

    paths = get_terminal_route_paths(create_app())
    assert "/api/v1/matters/{matter_id}/intelligence/deadlines/calculate" in paths
    assert "/api/v1/matters/{matter_id}/intelligence/evidence/nodes" in paths
    assert not any(
        path.startswith("/api/v1/jurisdictions/") and "deadline" in path for path in paths
    )


def test_deadline_evidence_migration_has_rollback_and_scope_contract():
    migration = (
        LegalAuthorityRepository().root
        / "portal"
        / "migrations"
        / "add_deadline_evidence_intelligence.sql"
    ).read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS matter_deadlines" in migration
    assert "CREATE TABLE IF NOT EXISTS matter_evidence_links" in migration
    assert "UNIQUE (deadline_id, version_number)" in migration
    assert "-- DOWN MIGRATION:" in migration
    assert (
        "matter_deadlines"
        not in migration.split("-- DOWN MIGRATION:", 1)[0].split(
            "CREATE TABLE IF NOT EXISTS matter_deadlines", 1
        )[0]
    )

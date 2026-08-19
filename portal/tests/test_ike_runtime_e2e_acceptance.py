import asyncio
import hashlib
import json
from collections.abc import AsyncGenerator

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.auth.jwt_handler import create_access_token
from portal.auth.rbac import Permission, Role
from portal.database import Base, get_db
from portal.main import create_app
from portal.models.audit import AuditLog
from portal.models.orchestration import (
    ApprovalRequest,
    BudgetUsage,
    EvidenceReference,
    OrchestrationEvent,
    OrchestrationNode,
    OrchestrationRun,
    ProviderDefinition,
    ReconciliationResult,
    RoutingDecision,
    VerificationResult,
)
from portal.models.user import Role as UserRole
from portal.models.user import Tenant, User
from portal.services.governed_identity import identity_service
from portal.services.orchestration import orchestrator

TENANT_ID = "00000000-0000-0000-0000-00000000e285"
PRINCIPAL_ID = "00000000-0000-0000-0000-000000000285"

PRINCIPAL_PERMISSIONS = (
    Permission.MISSION_COMMAND_ADMIN,
    Permission.ORCHESTRATION_CREATE,
    Permission.ORCHESTRATION_READ,
    Permission.ORCHESTRATION_CANCEL,
    Permission.ORCHESTRATION_APPROVE,
)


def _sqlite_sessionmaker():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async def init():
        async with engine.begin() as conn:
            await conn.run_sync(
                lambda sync_conn: Base.metadata.create_all(
                    sync_conn,
                    tables=[
                        Tenant.__table__,
                        UserRole.__table__,
                        User.__table__,
                        AuditLog.__table__,
                        OrchestrationRun.__table__,
                        OrchestrationNode.__table__,
                        OrchestrationEvent.__table__,
                        ProviderDefinition.__table__,
                        RoutingDecision.__table__,
                        VerificationResult.__table__,
                        ReconciliationResult.__table__,
                        ApprovalRequest.__table__,
                        BudgetUsage.__table__,
                        EvidenceReference.__table__,
                    ],
                )
            )

    asyncio.run(init())
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def _db_override(session_maker):
    async def override() -> AsyncGenerator[AsyncSession, None]:
        async with session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return override


def _client() -> TestClient:
    orchestrator.RUNS.clear()
    identity_service.identities.clear()
    app = create_app()
    maker = _sqlite_sessionmaker()
    app.dependency_overrides[get_db] = _db_override(maker)

    token = create_access_token(
        user_id=PRINCIPAL_ID,
        tenant_id=TENANT_ID,
        role=Role.SUPER_ADMIN.value,
        permissions=[permission.value for permission in PRINCIPAL_PERMISSIONS],
    )
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def _sha256_json(value: object) -> str:
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def test_governed_ike_runtime_acceptance_mission_end_to_end():
    """Certify the bounded governance chain used by IKE-Bot PR #285.

    Certified here:
    real Bearer JWT Principal -> scoped service identity -> living context ->
    specialist orchestration/model routing -> computer-use draft hash ->
    Principal approval -> one acceptance-only side effect -> hash-chained evidence ->
    Principal Brief receipt.

    This test intentionally does not claim production external computer control.
    """
    client = _client()

    # 1. Principal gateway: identity comes from the verified Bearer JWT.
    session = client.get("/api/v1/principal/session")
    assert session.status_code == 200
    assert session.json()["authenticated"] is True
    assert session.json()["principal_id"] == PRINCIPAL_ID
    assert session.json()["tenant_id"] == TENANT_ID

    # 2. Mission-scoped service identity; no credential material is stored here.
    identity_response = client.post(
        "/api/v1/principal/service-identities",
        json={
            "display_name": "IKE Computer Draft Executor",
            "agent_id": "ike-computer-drafter",
            "scopes": ["runtime:side-effect", "living-context:read"],
            "allowed_capabilities": ["computer_control", "living_file_memory"],
            "ttl_minutes": 30,
        },
    )
    assert identity_response.status_code == 201
    service_identity = identity_response.json()
    assert service_identity["identity_id"].startswith("svc-")
    assert service_identity["status"] == "ACTIVE"

    # 3. Living memory is retrieved from a bounded, hashed Markdown source.
    living = client.post(
        "/api/v1/principal/living-context",
        json={
            "query": "Principal approval living context",
            "refs": ["docs/planning/SP-IKE-002_GOVERNED_TOP_FEATURES.md"],
        },
    )
    assert living.status_code == 200
    living_items = living.json()
    assert living_items
    assert len(living_items[0]["content_hash"]) == 64
    assert "approval" in living_items[0]["matched_terms"]

    # 4. Build a computer-use draft but do not cross the side-effect boundary.
    computer_use_draft = {
        "mode": "computer_control",
        "agent_id": "ike-computer-drafter",
        "steps": [
            {"kind": "focus", "target": "acceptance-harness"},
            {"kind": "type", "target": "evidence-note", "text": "SP-IKE-002 acceptance"},
            {"kind": "commit", "target": "acceptance-marker", "requires_approval": True},
        ],
        "draft_only": True,
    }
    draft_hash = _sha256_json(computer_use_draft)

    # 5. Existing orchestration supplies the specialist graph and model routing.
    run_response = client.post(
        "/api/orchestration/execute",
        json={
            "objective": (
                "Implement code with specialist review, then send external communications "
                "only after Principal approval"
            ),
            "constraints": {
                "draft_hash": draft_hash,
                "computer_use_mode": "draft-first",
                "living_context_hash": living_items[0]["content_hash"],
            },
        },
    )
    assert run_response.status_code == 200
    run = run_response.json()
    assert run["status"] == "APPROVAL_REQUIRED"
    assert len(run["routing_decisions"]) >= 2
    assert run["verification"]
    assert run["approvals"][0]["status"] == "REQUESTED"
    run_id = run["run_id"]

    # 6. Side effect is blocked before Principal approval.
    blocked = client.post(
        "/api/v1/principal/acceptance-side-effects",
        json={
            "run_id": run_id,
            "draft_hash": draft_hash,
            "service_identity_id": service_identity["identity_id"],
            "side_effect_type": "ACCEPTANCE_MARKER",
            "principal_brief": {"status": "must-not-commit-yet"},
        },
    )
    assert blocked.status_code == 409

    # 7. Principal approves the exact pending run.
    approval_response = client.post(
        f"/api/orchestration/runs/{run_id}/approve",
        json={"approved": True, "reason": "Reviewed draft hash and bounded acceptance action"},
    )
    assert approval_response.status_code == 200
    approved_run = approval_response.json()
    approval = approved_run["approvals"][0]
    assert approval["status"] == "APPROVED"
    assert approval["principal_id"] == PRINCIPAL_ID

    # 8. Approval diffing: changing the draft invalidates the previous approval.
    stale_hash = _sha256_json({**computer_use_draft, "changed_after_approval": True})
    stale = client.post(
        "/api/v1/principal/acceptance-side-effects",
        json={
            "run_id": run_id,
            "draft_hash": stale_hash,
            "service_identity_id": service_identity["identity_id"],
            "side_effect_type": "ACCEPTANCE_MARKER",
            "principal_brief": {"status": "stale-approval-must-fail"},
        },
    )
    assert stale.status_code == 409

    # 9. Commit exactly one bounded approved side effect and receive hashed evidence.
    principal_brief = {
        "objective": "Certify SP-IKE-002 governed E2E mission",
        "specialists": len(run["routing_decisions"]),
        "living_context": living_items[0]["uri"],
        "model_routing_verified": True,
        "computer_use": "draft-first",
        "approval_id": approval["approval_id"],
        "external_action_performed": False,
        "remaining_gate": "production external computer-use adapter",
    }
    committed = client.post(
        "/api/v1/principal/acceptance-side-effects",
        json={
            "run_id": run_id,
            "draft_hash": draft_hash,
            "service_identity_id": service_identity["identity_id"],
            "side_effect_type": "ACCEPTANCE_MARKER",
            "principal_brief": principal_brief,
        },
    )
    assert committed.status_code == 201
    side_effect_receipt = committed.json()
    assert side_effect_receipt["committed"] is True
    assert len(side_effect_receipt["evidence_hash"]) == 64

    # 10. IKE writes the final mission receipt into the same canonical hash chain.
    final_receipt = client.post(
        "/api/v1/principal/runtime-receipts",
        json={
            "receipt_id": "sp-ike-002-e2e-final",
            "mission_id": run_id,
            "causation_id": run_id,
            "capability": "evidence_receipts",
            "action": "principal_brief_completed",
            "actor_agent_id": "ike-reconciler",
            "timestamp": "2026-08-19T08:41:00Z",
            "input_hash": draft_hash,
            "output_hash": side_effect_receipt["evidence_hash"],
            "approval_id": approval["approval_id"],
            "side_effect_reference": side_effect_receipt["audit_log_id"],
            "metadata": {"principal_brief": principal_brief},
        },
    )
    assert final_receipt.status_code == 201
    receipt = final_receipt.json()
    assert len(receipt["evidence_hash"]) == 64
    assert receipt["previous_evidence_hash"] == side_effect_receipt["evidence_hash"]

    # 11. Service identity can be revoked immediately after mission completion.
    revoked = client.post(
        f"/api/v1/principal/service-identities/{service_identity['identity_id']}/revoke",
        json={"reason": "Acceptance mission complete"},
    )
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "REVOKED"

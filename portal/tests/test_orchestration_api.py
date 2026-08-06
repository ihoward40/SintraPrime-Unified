import asyncio
from collections.abc import AsyncGenerator

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.auth.rbac import CurrentUser, Permission, Role, get_current_user
from portal.database import Base, get_db
from portal.main import create_app
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
from portal.services.orchestration import orchestrator

TENANT_A = "00000000-0000-0000-0000-0000000000a1"
TENANT_B = "00000000-0000-0000-0000-0000000000b2"
USER_A = "00000000-0000-0000-0000-000000000101"
USER_B = "00000000-0000-0000-0000-000000000202"


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

ALL_ORCHESTRATION_PERMS = (
    Permission.ORCHESTRATION_CREATE,
    Permission.ORCHESTRATION_READ,
    Permission.ORCHESTRATION_CANCEL,
    Permission.ORCHESTRATION_APPROVE,
)


def _user(*permissions: Permission, tenant_id: str = TENANT_A, user_id: str = USER_A) -> CurrentUser:
    return CurrentUser(
        {
            "sub": user_id,
            "tenant_id": tenant_id,
            "role": Role.ATTORNEY.value,
            "permissions": [permission.value for permission in permissions],
        }
    )


def client(*permissions: Permission, tenant_id: str = TENANT_A, user_id: str = USER_A, session_maker=None):
    orchestrator.RUNS.clear()
    app = create_app()
    maker = session_maker or _sqlite_sessionmaker()
    app.dependency_overrides[get_db] = _db_override(maker)
    app.dependency_overrides[get_current_user] = lambda: _user(
        *(permissions or ALL_ORCHESTRATION_PERMS),
        tenant_id=tenant_id,
        user_id=user_id,
    )
    return TestClient(app)


def test_orchestration_endpoints_require_authentication():
    orchestrator.RUNS.clear()
    response = TestClient(create_app()).post(
        "/api/orchestration/plan",
        json={"objective": "Implement secure code with independent review"},
    )

    assert response.status_code == 401


def test_plan_endpoint_returns_graph_and_events_with_tenant_scope():
    response = client().post(
        "/api/orchestration/plan",
        json={"objective": "Implement secure code with independent review"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] == TENANT_A
    assert body["created_by"] == USER_A
    assert body["status"] == "PLANNED"
    assert body["nodes"]
    assert body["events"][0]["event_type"] == "RUN_PLANNED"


def test_execute_endpoint_records_routing_verification_and_approval():
    response = client().post(
        "/api/orchestration/execute",
        json={"objective": "Implement code and preserve Principal approval for external actions"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "APPROVAL_REQUIRED"
    assert body["routing_decisions"]
    assert body["verification"]
    assert body["reconciliation"]["disputed_claims"]
    assert body["approvals"][0]["status"] == "REQUESTED"


def test_run_retrieval_and_events_endpoints_are_tenant_bound():
    session_maker = _sqlite_sessionmaker()
    test_client = client(session_maker=session_maker)
    created = test_client.post("/api/orchestration/plan", json={"objective": "Draft operations runbook"}).json()

    run_response = test_client.get(f"/api/orchestration/runs/{created['run_id']}")
    events_response = test_client.get(f"/api/orchestration/runs/{created['run_id']}/events")

    assert run_response.status_code == 200
    assert events_response.status_code == 200
    assert events_response.json()[0]["event_hash"]

    other_tenant_client = client(
        *ALL_ORCHESTRATION_PERMS,
        tenant_id=TENANT_B,
        user_id=USER_B,
        session_maker=session_maker,
    )

    assert other_tenant_client.get(f"/api/orchestration/runs/{created['run_id']}").status_code == 404
    assert other_tenant_client.get(f"/api/orchestration/runs/{created['run_id']}/events").status_code == 404


def test_cancel_endpoint_marks_run_cancelled_for_authorized_user():
    test_client = client()
    created = test_client.post("/api/orchestration/plan", json={"objective": "Research public facts"}).json()

    response = test_client.post(
        f"/api/orchestration/runs/{created['run_id']}/cancel",
        json={"reason": "Principal stopped mock run"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    assert response.json()["cancelled_by"] == USER_A


def test_cancel_endpoint_rejects_missing_permission():
    test_client = client(Permission.ORCHESTRATION_CREATE, Permission.ORCHESTRATION_READ)
    created = test_client.post("/api/orchestration/plan", json={"objective": "Research public facts"}).json()

    response = test_client.post(
        f"/api/orchestration/runs/{created['run_id']}/cancel",
        json={"reason": "No authority"},
    )

    assert response.status_code == 403


def test_approve_endpoint_records_authenticated_principal_decision():
    test_client = client()
    created = test_client.post("/api/orchestration/execute", json={"objective": "Implement code"}).json()

    response = test_client.post(
        f"/api/orchestration/runs/{created['run_id']}/approve",
        json={"approved": True, "reason": "Reviewed mock evidence"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["approvals"][0]["status"] == "APPROVED"
    assert body["approvals"][0]["principal_id"] == USER_A
    assert body["status"] == "COMPLETED"


def test_approve_endpoint_rejects_missing_permission_and_non_pending_runs():
    test_client = client(Permission.ORCHESTRATION_CREATE, Permission.ORCHESTRATION_READ)
    approval_run = test_client.post("/api/orchestration/execute", json={"objective": "Implement code"}).json()

    denied_response = test_client.post(
        f"/api/orchestration/runs/{approval_run['run_id']}/approve",
        json={"approved": True},
    )
    assert denied_response.status_code == 403

    authorized_client = client()
    planned = authorized_client.post("/api/orchestration/plan", json={"objective": "Draft operations runbook"}).json()
    non_pending_response = authorized_client.post(
        f"/api/orchestration/runs/{planned['run_id']}/approve",
        json={"approved": True},
    )
    assert non_pending_response.status_code == 409


def test_approval_cannot_be_replayed_after_completion():
    test_client = client()
    created = test_client.post("/api/orchestration/execute", json={"objective": "Implement code"}).json()

    first = test_client.post(f"/api/orchestration/runs/{created['run_id']}/approve", json={"approved": True})
    second = test_client.post(f"/api/orchestration/runs/{created['run_id']}/approve", json={"approved": True})

    assert first.status_code == 200
    assert second.status_code == 409


def test_execute_returns_blocked_when_budget_exhausted():
    response = client().post(
        "/api/orchestration/execute",
        json={
            "objective": "Implement code",
            "budget_limits": {"maximum_nodes": 0},
        },
    )

    assert response.status_code == 422


def test_execute_returns_partial_when_node_budget_is_reached_after_work():
    response = client().post(
        "/api/orchestration/execute",
        json={
            "objective": "Implement code",
            "budget_limits": {"maximum_nodes": 1},
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] in {"PARTIAL", "BLOCKED"}
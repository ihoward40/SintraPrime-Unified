"""
C1 Boundary Hardening — Isolated real-router post-auth boundary tests.

Test layer classification: ISOLATED REAL-ROUTER POST-AUTH BOUNDARY TESTS.

What these tests exercise (real, unmodified code paths):
  * authenticated-user dependency output (CurrentUser override);
  * real role enforcement via require_role(...);
  * real principal-context derivation via get_principal_context;
  * real route dependency composition;
  * real ExecutionGuard enforcement;
  * real database-backed route behavior (Observatory tables on SQLite);
  * real boundary audit-event persistence (BOUNDARY_REQUESTED/REFUSED/EXECUTED/FAILED).

What these tests do NOT exercise (delegated to existing auth tests, cited below):
  * bearer-token parsing;
  * JWT signature / expiration / audience validation;
  * the full create_app() dependency graph.

Because get_current_user is overridden, a no-token request cannot legitimately
prove a 401 here. JWT transport rejection is covered by the existing auth tests
(see checkpoint report, section B).

SQLite compatibility note:
  The Observatory models use no JSONB / ARRAY / PG-enum / UUID-server-default and
  are created via Base.metadata.create_all, mirroring test_authorization_matrix.py
  and test_blackstone_case_workflow.py. EventService.create uses SELECT ... FOR UPDATE
  on the run-head; under SQLite we monkeypatch its default skip_lock=True (single-
  threaded test). This is a concurrency seam only — no production code is altered.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.auth.rbac import CurrentUser, Permission, Role
from portal.database import Base, get_db
from portal.models.observatory import (
    Approval,
    Evidence,
    Incident,
    KillSwitchState,
    Mission,
    MissionAgent,
    ObservatoryEvent,
    ObservatoryRunHead,
)
from portal.schemas.observatory import ApprovalStatus
from portal.routers import observatory as observatory_router_module
from portal.routers.observatory import router as observatory_router
from portal.services.execution_guard import (
    ExecutionAction,
    ExecutionGuard,
    ExecutionGuardError,
    PrincipalContext,
)

# Tables required by the hardened routes.
OBSERVATORY_TABLES = [
    Mission.__table__,
    MissionAgent.__table__,
    ObservatoryEvent.__table__,
    ObservatoryRunHead.__table__,
    Approval.__table__,
    Evidence.__table__,
    Incident.__table__,
    KillSwitchState.__table__,
]


# ── Principal fixtures (real CurrentUser model) ──────────────────────────────

def _make_user(role: Role, user_id: str | None = None) -> CurrentUser:
    uid = user_id or str(uuid.uuid4())
    # Construct via the JWT payload shape that get_current_user produces after
    # decoding a valid token. This exercises the real CurrentUser model and the
    # real require_role / get_principal_context derivation — only the bearer
    # transport is bypassed (see test-layer classification in module docstring).
    payload = {
        "sub": uid,
        "tenant_id": str(uuid.uuid4()),
        "role": role.value,
        "permissions": [p.value for p in Permission],
    }
    return CurrentUser(payload)


@pytest_asyncio.fixture
def super_admin() -> CurrentUser:
    return _make_user(Role.SUPER_ADMIN, user_id="u-super")


@pytest_asyncio.fixture
def firm_admin() -> CurrentUser:
    return _make_user(Role.FIRM_ADMIN, user_id="u-firm")


@pytest_asyncio.fixture
def attorney() -> CurrentUser:
    # Authenticated, but below FIRM_ADMIN — must be refused by require_role(FIRM_ADMIN).
    return _make_user(Role.ATTORNEY, user_id="u-attorney")


@pytest_asyncio.fixture
def viewer() -> CurrentUser:
    # Authenticated, no relevant privileged role.
    return _make_user(Role.VIEWER, user_id="u-viewer")


# ── Test app + DB override ───────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client_and_db(super_admin):
    """Build a minimal app with the REAL observatory router; override only
    get_db (SQLite) and get_current_user (real CurrentUser)."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync: Base.metadata.create_all(sync, tables=OBSERVATORY_TABLES))
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # Default authenticated user for routes that read get_current_user indirectly
    # via the get_principal_context dependency. We override get_current_user to return
    # the fixture user supplied per-test through a mutable holder.
    state = {"user": super_admin}

    def _override_current_user() -> CurrentUser:
        return state["user"]

    # Make EventService.create skip row locking under SQLite (concurrency seam only).
    import portal.services.observatory_service as obs_svc

    orig_create = obs_svc.EventService.create

    async def _patched_create(*args, **kwargs):
        kwargs.setdefault("skip_lock", True)
        return await orig_create(*args, **kwargs)

    obs_svc.EventService.create = staticmethod(_patched_create)

    ExecutionGuard._audit_enabled = False  # avoid guard's own event pollution in this layer
    try:
        app = FastAPI()
        app.include_router(observatory_router)
        app.dependency_overrides[get_db] = lambda: session_factory()
        app.dependency_overrides[observatory_router_module.get_current_user] = _override_current_user

        with TestClient(app) as test_client:
            yield test_client, session_factory, state
    finally:
        ExecutionGuard._audit_enabled = True
        obs_svc.EventService.create = staticmethod(orig_create)
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest_asyncio.fixture
async def session(client_and_db) -> AsyncGenerator[AsyncSession, None]:
    _, session_factory, _ = client_and_db
    async with session_factory() as s:
        yield s


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _boundary_events(session, correlation_id: str) -> list[ObservatoryEvent]:
    from sqlalchemy import select as _select
    stmt = _select(ObservatoryEvent).where(ObservatoryEvent.run_id == "boundary")
    result = await session.execute(stmt)
    events = list(result.scalars().all())
    if correlation_id is not None:
        events = [e for e in events if e.payload.get("correlation_id") == correlation_id]
    return events


async def _clear_state(db: AsyncSession) -> None:
    from sqlalchemy import delete, select
    # Clear kill switch + boundary events so each test starts clean.
    active = (await db.execute(select(KillSwitchState))).scalars().all()
    for ks in active:
        await db.delete(ks)
    bounds = (await db.execute(select(ObservatoryEvent).where(ObservatoryEvent.run_id == "boundary"))).scalars().all()
    for ev in bounds:
        await db.delete(ev)
    await db.commit()


# ── A. Post-auth boundary tests ──────────────────────────────────────────────

class TestRoleEnforcement:
    """G-B2: require_role is enforced for real."""

    def test_firm_admin_reaches_approval_decision(self, client_and_db, firm_admin, session):
        client, _, state = client_and_db
        state["user"] = firm_admin
        # No approval exists yet -> 404 from service, proves FIRM_ADMIN passed require_role.
        resp = client.post(
            "/api/v1/approvals/00000000-0000-0000-0000-000000000001/decide",
            json={"decision": "APPROVED", "reviewer": "firm"},
        )
        assert resp.status_code in (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN)
        # 403 would indicate role failure; 404 indicates role passed and service ran.
        assert resp.status_code != status.HTTP_403_FORBIDDEN

    def test_attorney_refused_on_approval_decision(self, client_and_db, attorney):
        client, _, state = client_and_db
        state["user"] = attorney
        resp = client.post(
            "/api/v1/approvals/00000000-0000-0000-0000-000000000001/decide",
            json={"decision": "APPROVED", "reviewer": "atty"},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestMissionCreationBoundary:
    """G-B1/B-B2/B-B3/B-B4 on POST /missions."""

    @pytest.mark.asyncio
    async def test_authorized_mission_creation_success_once(self, client_and_db, firm_admin, session):
        client, _, state = client_and_db
        state["user"] = firm_admin
        await _clear_state(session)
        cid = "corr-mission-1"
        resp = client.post(
            "/api/v1/missions",
            json={"title": "Test mission", "metadata": {"correlation_id": cid}},
        )
        assert resp.status_code == status.HTTP_201_CREATED
        # Exactly one mission created.
        missions = (await session.execute(select(Mission))).scalars().all()
        assert len(missions) == 1
        # Boundary lifecycle persisted: REQUESTED -> AUTHORIZED -> EXECUTED, same correlation_id.
        events = await _boundary_events(session, cid)
        types = sorted(e.event_type for e in events)
        assert "BOUNDARY_REQUESTED" in types
        assert "BOUNDARY_AUTHORIZED" in types
        assert "BOUNDARY_EXECUTED" in types
        assert "BOUNDARY_REFUSED" not in types
        assert "BOUNDARY_FAILED" not in types
        for e in events:
            assert e.payload["correlation_id"] == cid
            assert "secret" not in str(e.payload).lower() or "***MASKED***" in str(e.payload)

    @pytest.mark.asyncio
    async def test_viewer_refused_on_mission_creation(self, client_and_db, viewer, session):
        client, _, state = client_and_db
        state["user"] = viewer
        await _clear_state(session)
        cid = "corr-mission-2"
        resp = client.post(
            "/api/v1/missions",
            json={"title": "Nope", "metadata": {"correlation_id": cid}},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        # No mission created.
        missions = (await session.execute(select(Mission))).scalars().all()
        assert len(missions) == 0
        # Insufficient-role refusal is now fully audited by require_audited_role:
        #   BOUNDARY_REQUESTED -> BOUNDARY_REFUSED (reason=insufficient_role)
        # No BOUNDARY_AUTHORIZED and no BOUNDARY_EXECUTED are emitted.
        events = await _boundary_events(session, cid)
        types = sorted(e.event_type for e in events)
        assert "BOUNDARY_REQUESTED" in types
        assert "BOUNDARY_REFUSED" in types
        assert "BOUNDARY_AUTHORIZED" not in types
        assert "BOUNDARY_EXECUTED" not in types
        refused = next(e for e in events if e.event_type == "BOUNDARY_REFUSED")
        assert refused.payload.get("detail") == "insufficient_role"
        assert refused.payload.get("subject") == "u-viewer"


class TestKillSwitchBoundary:
    """G-B1/B-B2/B-B3/B-B4 on emergency kill switch; policy-aware semantics."""

    @pytest.mark.asyncio
    async def test_super_admin_activates_kill_switch(self, client_and_db, super_admin, session):
        client, _, state = client_and_db
        state["user"] = super_admin
        await _clear_state(session)
        cid = "corr-ks-act-1"
        resp = client.post(
            "/api/v1/emergency/kill-switch",
            json={"reason": "drill", "scope": "all", "metadata": {"correlation_id": cid}},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["activated"] is True
        # Activated-by derived from principal, NOT request body.
        assert resp.json()["activated_by"] == "u-super"
        # Domain event emitted by service.
        ks = (await session.execute(select(KillSwitchState))).scalars().one()
        assert ks.is_active is True
        events = await _boundary_events(session, cid)
        assert any(e.event_type == "BOUNDARY_EXECUTED" for e in events)
        assert any(e.event_type == "BOUNDARY_AUTHORIZED" for e in events)
        assert any(e.event_type == "BOUNDARY_REQUESTED" for e in events)

    @pytest.mark.asyncio
    async def test_firm_admin_refused_on_kill_switch_activation(self, client_and_db, firm_admin, session):
        client, _, state = client_and_db
        state["user"] = firm_admin
        await _clear_state(session)
        cid = "corr-ks-act-2"
        resp = client.post(
            "/api/v1/emergency/kill-switch",
            json={"reason": "drill", "scope": "all", "metadata": {"correlation_id": cid}},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        ks = (await session.execute(select(KillSwitchState))).scalars().all()
        assert len(ks) == 0
        # Insufficient-role refusal: REQUESTED -> REFUSED(insufficient_role), no AUTHORIZED.
        events = await _boundary_events(session, cid)
        assert any(e.event_type == "BOUNDARY_REQUESTED" for e in events)
        refused = next(e for e in events if e.event_type == "BOUNDARY_REFUSED")
        assert refused.payload.get("detail") == "insufficient_role"
        assert "BOUNDARY_AUTHORIZED" not in [e.event_type for e in events]

    @pytest.mark.asyncio
    async def test_protected_write_blocked_while_kill_switch_active(self, client_and_db, super_admin, firm_admin, session):
        client, _, state = client_and_db
        # Activate first as SUPER_ADMIN.
        state["user"] = super_admin
        await _clear_state(session)
        act = client.post("/api/v1/emergency/kill-switch", json={"reason": "drill", "scope": "all"})
        assert act.status_code == status.HTTP_200_OK
        # Now a FIRM_ADMIN mission creation must be blocked by the guard.
        state["user"] = firm_admin
        cid = "corr-ks-block-1"
        resp = client.post(
            "/api/v1/missions",
            json={"title": "Should be blocked", "metadata": {"correlation_id": cid}},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        # No mission created while switch active.
        missions = (await session.execute(select(Mission))).scalars().all()
        assert len(missions) == 0
        # Boundary REFUSED persisted. Lifecycle: REQUESTED -> AUTHORIZED -> REFUSED(guard).
        events = await _boundary_events(session, cid)
        assert any(e.event_type == "BOUNDARY_REFUSED" for e in events)
        assert any(e.event_type == "BOUNDARY_AUTHORIZED" for e in events)
        refused = next(e for e in events if e.event_type == "BOUNDARY_REFUSED")
        # Refusal reason must identify the guard, not RBAC.
        assert refused.payload.get("detail") != "insufficient_role"

    @pytest.mark.asyncio
    async def test_clear_requires_super_admin(self, client_and_db, super_admin, firm_admin, session):
        client, _, state = client_and_db
        state["user"] = super_admin
        await _clear_state(session)
        client.post("/api/v1/emergency/kill-switch", json={"reason": "drill", "scope": "all"})
        # FIRM_ADMIN cannot clear.
        state["user"] = firm_admin
        resp = client.request("DELETE", "/api/v1/emergency/kill-switch",
                               json={"reason": "done", "metadata": {}})
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        # SUPER_ADMIN can clear (recovery path).
        state["user"] = super_admin
        resp2 = client.request("DELETE", "/api/v1/emergency/kill-switch",
                                json={"reason": "done", "metadata": {}})
        assert resp2.status_code == status.HTTP_200_OK
        assert resp2.json()["is_active"] is False


class TestEventAppendBoundary:
    """G-B4 recursion prevention for append_event."""

    @pytest.mark.asyncio
    async def test_append_event_records_lifecycle_no_recursion(self, client_and_db, firm_admin, session):
        client, _, state = client_and_db
        state["user"] = firm_admin
        await _clear_state(session)
        cid = "corr-append-1"
        resp = client.post(
            "/api/v1/events",
            json={
                "event_type": "MISSION_CREATED",  # valid EventType (validator rejects others)
                "payload": {"note": "hello"},
                "metadata": {"correlation_id": cid},
            },
        )
        assert resp.status_code == status.HTTP_201_CREATED
        # Domain event created exactly once.
        domain = (await session.execute(
            select(ObservatoryEvent).where(ObservatoryEvent.event_type == "MISSION_CREATED")
        )).scalars().all()
        assert len(domain) == 1
        # Boundary lifecycle: REQUESTED -> AUTHORIZED (no BOUNDARY_EXECUTED because
        # the recursion guard suppresses EXECUTED/FAILED for EVENT_APPEND — the
        # domain ObservatoryEvent IS the execution record).
        bounds = await _boundary_events(session, cid)
        assert any(e.event_type == "BOUNDARY_REQUESTED" for e in bounds)
        assert any(e.event_type == "BOUNDARY_AUTHORIZED" for e in bounds)
        # Recursion guard: append_event must NOT emit a BOUNDARY_EXECUTED for itself.
        assert not any(e.event_type == "BOUNDARY_EXECUTED" for e in bounds)


class TestGuardDenialNoMutation:
    """G-B3: guard denial causes no underlying mutation (covered by kill-switch-block above)
    and boundary REFUSED is persisted without EXECUTED."""

    @pytest.mark.asyncio
    async def test_refused_has_no_executed(self, client_and_db, viewer, session):
        client, _, state = client_and_db
        state["user"] = viewer
        await _clear_state(session)
        cid = "corr-refuse-1"
        resp = client.post("/api/v1/evidence",
                           json={"mission_id": str(uuid.uuid4()), "source": "x",
                                 "content_hash": "abc", "metadata": {"correlation_id": cid}})
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        ev = (await session.execute(select(Evidence))).scalars().all()
        assert len(ev) == 0
        bounds = await _boundary_events(session, cid)
        assert any(e.event_type == "BOUNDARY_REFUSED" for e in bounds)
        assert not any(e.event_type == "BOUNDARY_EXECUTED" for e in bounds)

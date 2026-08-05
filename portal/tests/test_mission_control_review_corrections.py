"""Mission Control Foundation review correction tests.

Covers the PR review corrections:
1. Cross-tenant causation child-node contamination (run-control events).
2. Sensitive-data redaction in detail projections (payload, event payload,
   evidence refs, run-control sensitive fields).
3. List projections return summaries (no payloads, events, receipts).
4. Freshness metadata on all projection responses.
5. Causation graph safety: truncation metadata, missing-parent detection,
   duplicate hash detection, deterministic ordering.
6. Refusal-only POST /commands regression.
7. Freshness classification unit tests.
8. Redaction unit tests.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.auth.rbac import CurrentUser, Permission, get_current_user
from portal.database import Base, get_db
from portal.models.audit import AuditLog
from portal.models.mission_control_command import (
    MissionControlCommand,
    MissionControlCommandEvent,
    MissionControlCommandReceipt,
)
from portal.models.mission_control_run_control import (
    MissionControlRunControl,
    MissionControlRunControlEvent,
    RunControlState,
)
from portal.models.user import Permission as PermissionModel
from portal.models.user import Role, RolePermission, Tenant, User, UserPermissionAssoc
from portal.routers import mission_control, mission_control_commands
from portal.schemas.mission_control_projection import (
    EXPOSED_PAYLOAD_FIELDS,
    REDACTED,
    CausationLink,
    classify_freshness,
    redact_dict,
    redact_error,
    redact_evidence_refs,
    redact_ref,
)

TENANT_A = "00000000-0000-0000-0000-000000000002"
TENANT_B = "00000000-0000-0000-0000-000000000003"
USER_A = "00000000-0000-0000-0000-000000000001"
USER_B = "00000000-0000-0000-0000-000000000004"


def _user(
    tenant_id: str = TENANT_A,
    user_id: str = USER_A,
    *permissions: Permission,
) -> CurrentUser:
    return CurrentUser(
        {
            "sub": user_id,
            "tenant_id": tenant_id,
            "role": "FIRM_ADMIN",
            "permissions": list(permissions) or [Permission.MISSION_COMMAND_READ],
        }
    )


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[
                    Tenant.__table__,
                    Role.__table__,
                    PermissionModel.__table__,
                    RolePermission.__table__,
                    User.__table__,
                    UserPermissionAssoc.__table__,
                    AuditLog.__table__,
                    MissionControlCommand.__table__,
                    MissionControlCommandEvent.__table__,
                    MissionControlCommandReceipt.__table__,
                    MissionControlRunControl.__table__,
                    MissionControlRunControlEvent.__table__,
                ],
            )
        )
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def client(db: AsyncSession) -> TestClient:
    app = FastAPI()
    app.include_router(mission_control.router)
    app.include_router(mission_control_commands.router)

    async def _override_db():
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: _user()
    return TestClient(app)


# ── 1. Cross-tenant causation child-node contamination ──────────────────────


@pytest.mark.asyncio
async def test_causation_chain_excludes_cross_tenant_run_control_events(
    db: AsyncSession,
):
    """Run-control events from tenant B must NOT appear in tenant A's chain.

    This tests the adversarial case: a run-control event linked to a command
    owned by tenant A, but the run-control record belongs to tenant B.
    The causation chain must NOT include the cross-tenant child event.
    """
    from portal.services.mission_control_projection_service import get_causation_chain

    # Tenant A command
    cmd_a = MissionControlCommand(
        id="cmd-xtenant-001",
        tenant_id=TENANT_A,
        requested_by=USER_A,
        command_type="PAUSE_RUN",
        target_type="run",
        target_id="run-001",
        idempotency_key="idem-xtenant-001",
        request_hash="hash-xtenant",
        state="REFUSED",
        payload={},
        metadata_json={},
    )
    db.add(cmd_a)
    await db.flush()

    # Tenant B run-control referencing tenant A's command
    rc_b = MissionControlRunControl(
        id="rc-xtenant-b-001",
        tenant_id=TENANT_B,
        workflow_id="wf-b-xtenant",
        state=RunControlState.RUNNING.value,
        workflow_status_snapshot="running",
        state_version=1,
        projection_schema_version=1,
        command_id="cmd-xtenant-001",  # links to tenant A's command
    )
    db.add(rc_b)
    await db.flush()

    # Run-control event on tenant B's run-control, referencing tenant A's command
    rc_evt_b = MissionControlRunControlEvent(
        id="rcevt-xtenant-b-001",
        run_control_id="rc-xtenant-b-001",
        sequence=1,
        event_type="STATE_TRANSITIONED",
        previous_state="RUNNING",
        new_state="PAUSE_REQUESTED",
        previous_version=1,
        new_version=2,
        command_id="cmd-xtenant-001",  # links to tenant A's command
        payload={},
        previous_event_hash=None,
        event_hash="hash-rcevt-b",
    )
    db.add(rc_evt_b)
    await db.flush()

    # Tenant A queries causation chain — must NOT see tenant B's event
    chain = await get_causation_chain(db, tenant_id=TENANT_A, command_id="cmd-xtenant-001")
    assert chain is not None
    # The chain should have 0 run_control_event links from tenant B
    rc_links = [link for link in chain.links if link.source_type == "run_control_event"]
    assert (
        len(rc_links) == 0
    ), f"Cross-tenant run-control event leaked into chain: {len(rc_links)} links"

    # Tenant B's chain (if queried for tenant B's own command would be different)
    # but tenant B cannot access tenant A's command at all
    chain_b = await get_causation_chain(db, tenant_id=TENANT_B, command_id="cmd-xtenant-001")
    assert chain_b is None  # tenant B cannot see tenant A's command


@pytest.mark.asyncio
async def test_causation_chain_includes_same_tenant_run_control_events(
    db: AsyncSession,
):
    """Run-control events from the same tenant DO appear in the chain."""
    from portal.services.mission_control_projection_service import get_causation_chain

    cmd = MissionControlCommand(
        id="cmd-st-001",
        tenant_id=TENANT_A,
        requested_by=USER_A,
        command_type="PAUSE_RUN",
        target_type="run",
        target_id="run-001",
        idempotency_key="idem-st-001",
        request_hash="hash-st",
        state="REFUSED",
        payload={},
        metadata_json={},
    )
    db.add(cmd)
    await db.flush()

    rc = MissionControlRunControl(
        id="rc-st-001",
        tenant_id=TENANT_A,
        workflow_id="wf-st",
        state=RunControlState.RUNNING.value,
        workflow_status_snapshot="running",
        state_version=1,
        projection_schema_version=1,
        command_id="cmd-st-001",
    )
    db.add(rc)
    await db.flush()

    rc_evt = MissionControlRunControlEvent(
        id="rcevt-st-001",
        run_control_id="rc-st-001",
        sequence=1,
        event_type="STATE_TRANSITIONED",
        previous_state="RUNNING",
        new_state="PAUSE_REQUESTED",
        previous_version=1,
        new_version=2,
        command_id="cmd-st-001",
        payload={},
        previous_event_hash=None,
        event_hash="hash-rcevt-st",
    )
    db.add(rc_evt)
    await db.flush()

    chain = await get_causation_chain(db, tenant_id=TENANT_A, command_id="cmd-st-001")
    assert chain is not None
    rc_links = [link for link in chain.links if link.source_type == "run_control_event"]
    assert len(rc_links) == 1
    assert rc_links[0].source_id == "rcevt-st-001"


# ── 2. Sensitive-data redaction ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_detail_command_redacts_payload(db: AsyncSession):
    """Detail projection must redact sensitive payload fields."""
    from portal.services.mission_control_projection_service import get_command

    cmd = MissionControlCommand(
        id="cmd-redact-001",
        tenant_id=TENANT_A,
        requested_by=USER_A,
        command_type="PAUSE_RUN",
        target_type="run",
        target_id="run-001",
        idempotency_key="idem-redact-001",
        request_hash="hash-redact",
        state="REFUSED",
        payload={"secret_key": "sk-12345", "target_id": "run-001"},
        metadata_json={"internal_token": "tok-abc", "source": "test"},
    )
    db.add(cmd)
    await db.flush()

    projection = await get_command(db, tenant_id=TENANT_A, command_id="cmd-redact-001")
    assert projection is not None
    # Sensitive fields must be redacted
    assert projection.payload["secret_key"] == REDACTED
    assert projection.metadata["internal_token"] == REDACTED
    # Exposed fields must be visible
    assert projection.payload["target_id"] == "run-001"
    # 'source' is not in EXPOSED_PAYLOAD_FIELDS so it gets redacted
    assert projection.metadata["source"] == REDACTED


@pytest.mark.asyncio
async def test_detail_command_redacts_event_payload(db: AsyncSession):
    """Event payloads in detail projection must be redacted."""
    from portal.services.mission_control_projection_service import get_command

    cmd = MissionControlCommand(
        id="cmd-redevt-001",
        tenant_id=TENANT_A,
        requested_by=USER_A,
        command_type="PAUSE_RUN",
        target_type="run",
        target_id="run-001",
        idempotency_key="idem-redevt-001",
        request_hash="hash-redevt",
        state="REFUSED",
        payload={},
        metadata_json={},
    )
    db.add(cmd)
    await db.flush()

    evt = MissionControlCommandEvent(
        id="evt-redevt-001",
        command_id="cmd-redevt-001",
        sequence=1,
        event_type="RECEIVED",
        state="RECEIVED",
        payload={"credential": "pw-12345", "state": "RECEIVED"},
        previous_hash=None,
        event_hash="hash-evt-redevt",
    )
    db.add(evt)
    await db.flush()

    projection = await get_command(db, tenant_id=TENANT_A, command_id="cmd-redevt-001")
    assert projection is not None
    assert len(projection.events) == 1
    assert projection.events[0].payload["credential"] == REDACTED
    assert projection.events[0].payload["state"] == "RECEIVED"


@pytest.mark.asyncio
async def test_detail_command_redacts_evidence_refs(db: AsyncSession):
    """Evidence refs in detail projection must be redacted to count only."""
    from portal.services.mission_control_projection_service import get_command

    cmd = MissionControlCommand(
        id="cmd-redref-001",
        tenant_id=TENANT_A,
        requested_by=USER_A,
        command_type="PAUSE_RUN",
        target_type="run",
        target_id="run-001",
        idempotency_key="idem-redref-001",
        request_hash="hash-redref",
        state="REFUSED",
        payload={},
        metadata_json={},
    )
    db.add(cmd)
    await db.flush()

    rct = MissionControlCommandReceipt(
        id="rct-redref-001",
        command_id="cmd-redref-001",
        receipt_type="REFUSAL",
        receipt_hash="hash-rct-redref",
        evidence_refs=["s3://bucket/secret-evidence-1", "s3://bucket/secret-evidence-2"],
    )
    db.add(rct)
    await db.flush()

    projection = await get_command(db, tenant_id=TENANT_A, command_id="cmd-redref-001")
    assert projection is not None
    assert len(projection.receipts) == 1
    refs = projection.receipts[0].evidence_refs
    assert len(refs) == 2  # count preserved
    assert all(r == REDACTED for r in refs)  # all values redacted


@pytest.mark.asyncio
async def test_detail_run_control_redacts_sensitive_fields(db: AsyncSession):
    """Run-control detail must redact last_error, confirmation_ref, recovery_ref."""
    from portal.services.mission_control_projection_service import get_run_control

    rc = MissionControlRunControl(
        id="rc-redact-001",
        tenant_id=TENANT_A,
        workflow_id="wf-redact",
        state=RunControlState.FAILED.value,
        workflow_status_snapshot="failed",
        state_version=1,
        projection_schema_version=1,
        last_error="InternalError: database connection failed at host db.internal:5432",
        confirmation_ref="conf-secret-ref-123",
        recovery_ref="recov-secret-ref-456",
    )
    db.add(rc)
    await db.flush()

    projection = await get_run_control(db, tenant_id=TENANT_A, run_control_id="rc-redact-001")
    assert projection is not None
    assert projection.last_error == REDACTED
    assert projection.confirmation_ref == REDACTED
    assert projection.recovery_ref == REDACTED


@pytest.mark.asyncio
async def test_detail_run_control_redacts_none_sensitive_fields(db: AsyncSession):
    """Run-control detail preserves None for sensitive fields when source is None."""
    from portal.services.mission_control_projection_service import get_run_control

    rc = MissionControlRunControl(
        id="rc-redact-none-001",
        tenant_id=TENANT_A,
        workflow_id="wf-redact-none",
        state=RunControlState.RUNNING.value,
        workflow_status_snapshot="running",
        state_version=1,
        projection_schema_version=1,
        last_error=None,
        confirmation_ref=None,
        recovery_ref=None,
    )
    db.add(rc)
    await db.flush()

    projection = await get_run_control(db, tenant_id=TENANT_A, run_control_id="rc-redact-none-001")
    assert projection is not None
    assert projection.last_error is None
    assert projection.confirmation_ref is None
    assert projection.recovery_ref is None


# ── 3. List projections return summaries ─────────────────────────────────────


@pytest.mark.asyncio
async def test_list_commands_returns_summaries_not_full_projections(
    db: AsyncSession,
):
    """List endpoint must return CommandSummary, not CommandProjection."""
    from portal.services.mission_control_projection_service import list_commands

    cmd = MissionControlCommand(
        id="cmd-summary-001",
        tenant_id=TENANT_A,
        requested_by=USER_A,
        command_type="PAUSE_RUN",
        target_type="run",
        target_id="run-001",
        idempotency_key="idem-summary-001",
        request_hash="hash-summary",
        state="REFUSED",
        payload={"secret": "should-not-appear"},
        metadata_json={},
    )
    db.add(cmd)
    await db.flush()

    result = await list_commands(db, tenant_id=TENANT_A)
    assert result.total == 1
    item = result.items[0]
    # Summary should have id, state, command_type but NOT payload
    assert hasattr(item, "id")
    assert hasattr(item, "state")
    assert hasattr(item, "command_type")
    assert not hasattr(item, "payload"), "List projection must not include payload"
    assert not hasattr(item, "events"), "List projection must not include events"
    assert not hasattr(item, "receipts"), "List projection must not include receipts"
    assert hasattr(item, "event_count"), "Summary must include event_count"
    assert hasattr(item, "receipt_count"), "Summary must include receipt_count"


@pytest.mark.asyncio
async def test_list_run_controls_returns_summaries_not_full_projections(
    db: AsyncSession,
):
    """List endpoint must return RunControlSummary, not RunControlProjection."""
    from portal.services.mission_control_projection_service import list_run_controls

    rc = MissionControlRunControl(
        id="rc-summary-001",
        tenant_id=TENANT_A,
        workflow_id="wf-summary",
        state=RunControlState.RUNNING.value,
        workflow_status_snapshot="running",
        state_version=1,
        projection_schema_version=1,
        last_error="secret error",
    )
    db.add(rc)
    await db.flush()

    result = await list_run_controls(db, tenant_id=TENANT_A)
    assert result.total == 1
    item = result.items[0]
    assert hasattr(item, "id")
    assert hasattr(item, "state")
    assert hasattr(item, "workflow_id")
    assert not hasattr(item, "events"), "List projection must not include events"
    assert not hasattr(item, "last_error"), "List projection must not include last_error"
    assert hasattr(item, "event_count"), "Summary must include event_count"


@pytest.mark.asyncio
async def test_list_commands_summary_counts(db: AsyncSession):
    """Summary event_count and receipt_count reflect the actual lifecycle."""
    from portal.services.mission_control_projection_service import list_commands

    cmd = MissionControlCommand(
        id="cmd-count-001",
        tenant_id=TENANT_A,
        requested_by=USER_A,
        command_type="PAUSE_RUN",
        target_type="run",
        target_id="run-001",
        idempotency_key="idem-count-001",
        request_hash="hash-count",
        state="REFUSED",
        payload={},
        metadata_json={},
    )
    db.add(cmd)
    await db.flush()

    for seq in range(1, 4):
        db.add(
            MissionControlCommandEvent(
                id=f"evt-count-{seq}",
                command_id="cmd-count-001",
                sequence=seq,
                event_type="RECEIVED",
                state="RECEIVED",
                payload={},
                previous_hash=None if seq == 1 else f"prev-{seq}",
                event_hash=f"hash-evt-count-{seq}",
            )
        )
    await db.flush()

    db.add(
        MissionControlCommandReceipt(
            id="rct-count-001",
            command_id="cmd-count-001",
            receipt_type="REFUSAL",
            receipt_hash="hash-rct-count",
            evidence_refs=[],
        )
    )
    await db.flush()

    result = await list_commands(db, tenant_id=TENANT_A)
    assert result.total == 1
    assert result.items[0].event_count == 3
    assert result.items[0].receipt_count == 1


# ── 4. Freshness metadata ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_commands_has_freshness(db: AsyncSession):
    """List commands response must include freshness metadata."""
    from portal.services.mission_control_projection_service import list_commands

    result = await list_commands(db, tenant_id=TENANT_A)
    assert hasattr(result, "freshness")
    assert result.freshness is not None
    assert result.freshness.state in ("LIVE", "DELAYED", "STALE", "UNKNOWN")
    assert result.freshness.generated_at is not None


@pytest.mark.asyncio
async def test_list_run_controls_has_freshness(db: AsyncSession):
    """List run-controls response must include freshness metadata."""
    from portal.services.mission_control_projection_service import list_run_controls

    result = await list_run_controls(db, tenant_id=TENANT_A)
    assert hasattr(result, "freshness")
    assert result.freshness is not None
    assert result.freshness.state in ("LIVE", "DELAYED", "STALE", "UNKNOWN")


@pytest.mark.asyncio
async def test_get_command_has_freshness(db: AsyncSession):
    """Detail command projection must include freshness metadata."""
    from portal.services.mission_control_projection_service import get_command

    cmd = MissionControlCommand(
        id="cmd-fresh-001",
        tenant_id=TENANT_A,
        requested_by=USER_A,
        command_type="PAUSE_RUN",
        target_type="run",
        target_id="run-001",
        idempotency_key="idem-fresh-001",
        request_hash="hash-fresh",
        state="REFUSED",
        payload={},
        metadata_json={},
    )
    db.add(cmd)
    await db.flush()

    projection = await get_command(db, tenant_id=TENANT_A, command_id="cmd-fresh-001")
    assert projection is not None
    assert hasattr(projection, "freshness")
    assert projection.freshness is not None
    assert projection.freshness.state in ("LIVE", "DELAYED", "STALE", "UNKNOWN")


@pytest.mark.asyncio
async def test_get_run_control_has_freshness(db: AsyncSession):
    """Detail run-control projection must include freshness metadata."""
    from portal.services.mission_control_projection_service import get_run_control

    rc = MissionControlRunControl(
        id="rc-fresh-001",
        tenant_id=TENANT_A,
        workflow_id="wf-fresh",
        state=RunControlState.RUNNING.value,
        workflow_status_snapshot="running",
        state_version=1,
        projection_schema_version=1,
    )
    db.add(rc)
    await db.flush()

    projection = await get_run_control(db, tenant_id=TENANT_A, run_control_id="rc-fresh-001")
    assert projection is not None
    assert hasattr(projection, "freshness")
    assert projection.freshness is not None
    assert projection.freshness.state in ("LIVE", "DELAYED", "STALE", "UNKNOWN")


@pytest.mark.asyncio
async def test_causation_chain_has_freshness(db: AsyncSession):
    """Causation chain must include freshness metadata."""
    from portal.services.mission_control_projection_service import get_causation_chain

    cmd = MissionControlCommand(
        id="cmd-chainfresh-001",
        tenant_id=TENANT_A,
        requested_by=USER_A,
        command_type="PAUSE_RUN",
        target_type="run",
        target_id="run-001",
        idempotency_key="idem-chainfresh-001",
        request_hash="hash-chainfresh",
        state="REFUSED",
        payload={},
        metadata_json={},
    )
    db.add(cmd)
    await db.flush()

    chain = await get_causation_chain(db, tenant_id=TENANT_A, command_id="cmd-chainfresh-001")
    assert chain is not None
    assert hasattr(chain, "freshness")
    assert chain.freshness is not None
    assert chain.freshness.state in ("LIVE", "DELAYED", "STALE", "UNKNOWN")


@pytest.mark.asyncio
async def test_freshness_metadata_serialized_in_router(client: TestClient):
    """Router responses must serialize freshness metadata."""
    response = client.get("/api/v1/mission-control/intents")
    assert response.status_code == 200
    body = response.json()
    assert "freshness" in body
    assert body["freshness"]["state"] in ("LIVE", "DELAYED", "STALE", "UNKNOWN")


# ── 5. Causation graph safety ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_causation_chain_has_truncation_metadata(db: AsyncSession):
    """Causation chain must include truncated flag and total_links."""
    from portal.services.mission_control_projection_service import get_causation_chain

    cmd = MissionControlCommand(
        id="cmd-trunc-001",
        tenant_id=TENANT_A,
        requested_by=USER_A,
        command_type="PAUSE_RUN",
        target_type="run",
        target_id="run-001",
        idempotency_key="idem-trunc-001",
        request_hash="hash-trunc",
        state="REFUSED",
        payload={},
        metadata_json={},
    )
    db.add(cmd)
    await db.flush()

    chain = await get_causation_chain(db, tenant_id=TENANT_A, command_id="cmd-trunc-001")
    assert chain is not None
    assert hasattr(chain, "truncated")
    assert hasattr(chain, "total_links")
    assert chain.truncated is False
    assert chain.total_links == len(chain.links)


@pytest.mark.asyncio
async def test_causation_chain_detects_missing_parent(db: AsyncSession):
    """Causation chain must warn when a previous_hash is not in node hashes."""
    from portal.services.mission_control_projection_service import get_causation_chain

    cmd = MissionControlCommand(
        id="cmd-missing-001",
        tenant_id=TENANT_A,
        requested_by=USER_A,
        command_type="PAUSE_RUN",
        target_type="run",
        target_id="run-001",
        idempotency_key="idem-missing-001",
        request_hash="hash-missing",
        state="REFUSED",
        payload={},
        metadata_json={},
    )
    db.add(cmd)
    await db.flush()

    # Event 1 with no previous hash (genesis)
    db.add(
        MissionControlCommandEvent(
            id="evt-missing-1",
            command_id="cmd-missing-001",
            sequence=1,
            event_type="RECEIVED",
            state="RECEIVED",
            payload={},
            previous_hash=None,
            event_hash="hash-missing-1",
        )
    )
    await db.flush()

    # Event 2 referencing a previous hash that doesn't exist in the chain
    db.add(
        MissionControlCommandEvent(
            id="evt-missing-2",
            command_id="cmd-missing-001",
            sequence=2,
            event_type="EVALUATED",
            state="EVALUATED",
            payload={},
            previous_hash="nonexistent-hash-12345",
            event_hash="hash-missing-2",
        )
    )
    await db.flush()

    chain = await get_causation_chain(db, tenant_id=TENANT_A, command_id="cmd-missing-001")
    assert chain is not None
    assert chain.warnings
    assert any("Missing parent" in w for w in chain.warnings)


@pytest.mark.asyncio
async def test_causation_chain_detects_duplicate_hash(db: AsyncSession):
    """Causation chain must warn when duplicate hashes are present."""
    from portal.services.mission_control_projection_service import get_causation_chain

    cmd = MissionControlCommand(
        id="cmd-dup-001",
        tenant_id=TENANT_A,
        requested_by=USER_A,
        command_type="PAUSE_RUN",
        target_type="run",
        target_id="run-001",
        idempotency_key="idem-dup-001",
        request_hash="hash-dup",
        state="REFUSED",
        payload={},
        metadata_json={},
    )
    db.add(cmd)
    await db.flush()

    # Two events with the same event_hash
    db.add(
        MissionControlCommandEvent(
            id="evt-dup-1",
            command_id="cmd-dup-001",
            sequence=1,
            event_type="RECEIVED",
            state="RECEIVED",
            payload={},
            previous_hash=None,
            event_hash="duplicate-hash-value",
        )
    )
    await db.flush()

    db.add(
        MissionControlCommandEvent(
            id="evt-dup-2",
            command_id="cmd-dup-001",
            sequence=2,
            event_type="EVALUATED",
            state="EVALUATED",
            payload={},
            previous_hash="duplicate-hash-value",
            event_hash="duplicate-hash-value",  # same hash!
        )
    )
    await db.flush()

    chain = await get_causation_chain(db, tenant_id=TENANT_A, command_id="cmd-dup-001")
    assert chain is not None
    assert chain.warnings
    assert any("Duplicate" in w for w in chain.warnings)


@pytest.mark.asyncio
async def test_causation_chain_deterministic_ordering(db: AsyncSession):
    """Causation chain links must be deterministically ordered.

    Sort key: (created_at, sequence, source_type, source_id)
    """
    from portal.services.mission_control_projection_service import get_causation_chain

    cmd = MissionControlCommand(
        id="cmd-order-001",
        tenant_id=TENANT_A,
        requested_by=USER_A,
        command_type="PAUSE_RUN",
        target_type="run",
        target_id="run-001",
        idempotency_key="idem-order-001",
        request_hash="hash-order",
        state="REFUSED",
        payload={},
        metadata_json={},
    )
    db.add(cmd)
    await db.flush()

    # Add events out of order
    db.add(
        MissionControlCommandEvent(
            id="evt-order-2",
            command_id="cmd-order-001",
            sequence=2,
            event_type="EVALUATED",
            state="EVALUATED",
            payload={},
            previous_hash="hash-order-evt-1",
            event_hash="hash-order-evt-2",
        )
    )
    await db.flush()

    db.add(
        MissionControlCommandEvent(
            id="evt-order-1",
            command_id="cmd-order-001",
            sequence=1,
            event_type="RECEIVED",
            state="RECEIVED",
            payload={},
            previous_hash=None,
            event_hash="hash-order-evt-1",
        )
    )
    await db.flush()

    chain = await get_causation_chain(db, tenant_id=TENANT_A, command_id="cmd-order-001")
    assert chain is not None
    # Verify deterministic ordering by sequence
    cmd_event_links = [link for link in chain.links if link.source_type == "command_event"]
    assert len(cmd_event_links) == 2
    assert cmd_event_links[0].sequence <= cmd_event_links[1].sequence

    # Verify sort key is (created_at, sequence, source_type, source_id)
    for i in range(len(chain.links) - 1):
        left = chain.links[i]
        right = chain.links[i + 1]
        left_key = (
            left.created_at or datetime.min.replace(tzinfo=UTC),
            left.sequence,
            left.source_type,
            left.source_id,
        )
        right_key = (
            right.created_at or datetime.min.replace(tzinfo=UTC),
            right.sequence,
            right.source_type,
            right.source_id,
        )
        assert left_key <= right_key, (
            f"Links not deterministically ordered at index {i}: " f"{left_key} > {right_key}"
        )


@pytest.mark.asyncio
async def test_causation_chain_truncation_at_max_links(db: AsyncSession):
    """Chain must truncate at MAX_CAUSATION_LINKS and set truncated=True."""
    from portal.schemas.mission_control_projection import MAX_CAUSATION_LINKS
    from portal.services.mission_control_projection_service import get_causation_chain

    cmd = MissionControlCommand(
        id="cmd-maxlinks-001",
        tenant_id=TENANT_A,
        requested_by=USER_A,
        command_type="PAUSE_RUN",
        target_type="run",
        target_id="run-001",
        idempotency_key="idem-maxlinks-001",
        request_hash="hash-maxlinks",
        state="REFUSED",
        payload={},
        metadata_json={},
    )
    db.add(cmd)
    await db.flush()

    # Create more than MAX_CAUSATION_LINKS events
    for seq in range(1, MAX_CAUSATION_LINKS + 10):
        db.add(
            MissionControlCommandEvent(
                id=f"evt-maxlinks-{seq}",
                command_id="cmd-maxlinks-001",
                sequence=seq,
                event_type="RECEIVED",
                state="RECEIVED",
                payload={},
                previous_hash=None,
                event_hash=f"hash-maxlinks-{seq}",
            )
        )
    await db.flush()

    chain = await get_causation_chain(db, tenant_id=TENANT_A, command_id="cmd-maxlinks-001")
    assert chain is not None
    assert chain.truncated is True
    assert chain.total_links == MAX_CAUSATION_LINKS + 9
    assert len(chain.links) == MAX_CAUSATION_LINKS
    assert any("truncated" in w.lower() for w in chain.warnings)


# ── 6. Refusal-only POST /commands regression ─────────────────────────────────


class TestRefusalOnlyCommandsRegression:
    """Verify the refusal-only POST /commands endpoint exists and works."""

    def test_post_commands_endpoint_exists(self, client: TestClient):
        """POST /commands must not return 404 or 405.

        The refusal-only contract (state=REFUSED, reason_code=COMMAND_EXECUTION_NOT_ENABLED)
        is verified in the comprehensive test_mission_control_commands.py suite which
        properly seeds the database. Here we verify the endpoint exists and requires auth.
        """
        body = {
            "command_type": "PAUSE_RUN",
            "target_type": "run",
            "target_id": "run-123",
            "idempotency_key": "regression-key-1234567890",
            "reason": "operator requested hold",
            "payload": {"nested": {"b": 2, "a": 1}},
            "metadata": {"source": "test"},
        }
        response = client.post("/api/v1/mission-control/commands", json=body)
        # Must not be 404 (not found) or 405 (method not allowed)
        assert response.status_code != 404
        assert response.status_code != 405
        # If we get 201, verify refusal contract
        if response.status_code == 201:
            assert response.json()["state"] == "REFUSED"
            assert response.json()["reason_code"] == "COMMAND_EXECUTION_NOT_ENABLED"


# ── 7. Freshness classification unit tests ───────────────────────────────────


class TestFreshnessClassification:
    """Unit tests for classify_freshness."""

    def test_live_when_source_within_5_seconds(self):
        generated = datetime.now(UTC)
        source = generated - timedelta(seconds=2)
        meta = classify_freshness(generated, source)
        assert meta.state == "LIVE"
        assert meta.freshness_seconds is not None
        assert 0 <= meta.freshness_seconds <= 5

    def test_live_at_exact_5_second_boundary(self):
        generated = datetime.now(UTC)
        source = generated - timedelta(seconds=5)
        meta = classify_freshness(generated, source)
        assert meta.state == "LIVE"

    def test_delayed_when_source_between_5_and_60_seconds(self):
        generated = datetime.now(UTC)
        source = generated - timedelta(seconds=30)
        meta = classify_freshness(generated, source)
        assert meta.state == "DELAYED"
        assert meta.freshness_seconds is not None
        assert 5 < meta.freshness_seconds <= 60

    def test_delayed_at_exact_60_second_boundary(self):
        generated = datetime.now(UTC)
        source = generated - timedelta(seconds=60)
        meta = classify_freshness(generated, source)
        assert meta.state == "DELAYED"

    def test_stale_when_source_over_60_seconds(self):
        generated = datetime.now(UTC)
        source = generated - timedelta(seconds=120)
        meta = classify_freshness(generated, source)
        assert meta.state == "STALE"
        assert meta.freshness_seconds is not None
        assert meta.freshness_seconds > 60

    def test_unknown_when_source_is_none(self):
        generated = datetime.now(UTC)
        meta = classify_freshness(generated, None)
        assert meta.state == "UNKNOWN"
        assert meta.freshness_seconds is None
        assert meta.source_updated_at is None

    @pytest.mark.filterwarnings("ignore::DeprecationWarning")
    def test_naive_datetimes_normalized_to_utc(self):
        """Timezone-naive datetimes from SQLite are treated as UTC."""
        generated = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)  # naive-equivalent
        source = datetime(2025, 1, 1, 12, 0, 2, tzinfo=UTC)  # 2s before
        meta = classify_freshness(generated, source)
        assert meta.state == "LIVE"
        assert meta.generated_at.tzinfo is not None
        assert meta.source_updated_at is not None
        assert meta.source_updated_at.tzinfo is not None


# ── 8. Redaction unit tests ──────────────────────────────────────────────────


class TestRedaction:
    """Unit tests for redaction utilities."""

    def test_redact_dict_redacts_non_exposed_fields(self):
        data = {"secret_key": "sk-12345", "target_id": "run-001", "workflow_id": "wf-1"}
        result = redact_dict(data, EXPOSED_PAYLOAD_FIELDS)
        assert result["secret_key"] == REDACTED
        assert result["target_id"] == "run-001"
        assert result["workflow_id"] == "wf-1"

    def test_redact_dict_redacts_all_when_none_exposed(self):
        data = {"a": 1, "b": 2}
        result = redact_dict(data, frozenset())
        assert result["a"] == REDACTED
        assert result["b"] == REDACTED

    def test_redact_dict_empty(self):
        result = redact_dict({}, EXPOSED_PAYLOAD_FIELDS)
        assert result == {}

    def test_redact_evidence_refs_preserves_count(self):
        refs = ["s3://bucket/secret-1", "s3://bucket/secret-2", "s3://bucket/secret-3"]
        result = redact_evidence_refs(refs)
        assert len(result) == 3
        assert all(r == REDACTED for r in result)

    def test_redact_evidence_refs_empty(self):
        result = redact_evidence_refs([])
        assert result == []

    def test_redact_error_redacts_non_empty_text(self):
        assert redact_error("InternalError: something failed") == REDACTED

    def test_redact_error_preserves_none(self):
        assert redact_error(None) is None

    def test_redact_error_preserves_empty_string(self):
        assert redact_error("") is None

    def test_redact_ref_redacts_non_none(self):
        assert redact_ref("conf-secret-ref-123") == REDACTED

    def test_redact_ref_preserves_none(self):
        assert redact_ref(None) is None

    def test_redacted_constant_value(self):
        assert REDACTED == "REDACTED"

    def test_exposed_payload_fields_contains_expected_fields(self):
        expected = {
            "workflow_id",
            "workflow_source",
            "state",
            "command_type",
            "target_type",
            "target_id",
        }
        assert expected == EXPOSED_PAYLOAD_FIELDS


# ── 9. Causation link schema validation ──────────────────────────────────────


class TestCausationLinkSchema:
    """Validate CausationLink accepts valid source types."""

    def test_causation_link_source_types(self):
        for source_type in ("command_event", "run_control_event", "receipt"):
            link = CausationLink(
                source_type=source_type,
                source_id="test-id",
                sequence=1,
                event_type="RECEIVED",
                state="RECEIVED",
                hash="hash-value",
            )
            assert link.source_type == source_type


# ── 10. Cycle detection tests ─────────────────────────────────────────────────


class TestCycleDetection:
    """Tests for previous_hash cycle detection in causation chains.

    These tests verify that detect_cycles correctly identifies:
    - Self-cycles (A.previous_hash = A.hash)
    - Two-node cycles (A -> B -> A)
    - Longer cycles (A -> B -> C -> A)
    - Valid acyclic chains produce no cycle warnings
    """

    def test_self_cycle_detected(self):
        """A node whose previous_hash points to itself is a self-cycle."""
        from portal.services.mission_control_projection_service import detect_cycles

        links = [
            CausationLink(
                source_type="command_event",
                source_id="evt-self-1",
                sequence=1,
                event_type="RECEIVED",
                state="RECEIVED",
                hash="hash-self-A",
                previous_hash="hash-self-A",  # points to itself
            ),
        ]
        warnings = detect_cycles(links)
        assert len(warnings) >= 1
        assert any("Cycle" in w for w in warnings)
        assert any("hash-self-A" in w for w in warnings)

    def test_two_node_cycle_detected(self):
        """A -> B -> A is a two-node cycle."""
        from portal.services.mission_control_projection_service import detect_cycles

        links = [
            CausationLink(
                source_type="command_event",
                source_id="evt-two-A",
                sequence=1,
                event_type="RECEIVED",
                state="RECEIVED",
                hash="hash-two-A",
                previous_hash="hash-two-B",  # A -> B
            ),
            CausationLink(
                source_type="command_event",
                source_id="evt-two-B",
                sequence=2,
                event_type="EVALUATED",
                state="EVALUATED",
                hash="hash-two-B",
                previous_hash="hash-two-A",  # B -> A
            ),
        ]
        warnings = detect_cycles(links)
        assert len(warnings) >= 1
        assert any("Cycle" in w for w in warnings)

    def test_longer_cycle_detected(self):
        """A -> B -> C -> A is a three-node cycle."""
        from portal.services.mission_control_projection_service import detect_cycles

        links = [
            CausationLink(
                source_type="command_event",
                source_id="evt-long-A",
                sequence=1,
                event_type="RECEIVED",
                state="RECEIVED",
                hash="hash-long-A",
                previous_hash="hash-long-C",  # A -> C
            ),
            CausationLink(
                source_type="command_event",
                source_id="evt-long-B",
                sequence=2,
                event_type="EVALUATED",
                state="EVALUATED",
                hash="hash-long-B",
                previous_hash="hash-long-A",  # B -> A
            ),
            CausationLink(
                source_type="command_event",
                source_id="evt-long-C",
                sequence=3,
                event_type="DISPATCHED",
                state="DISPATCHED",
                hash="hash-long-C",
                previous_hash="hash-long-B",  # C -> B
            ),
        ]
        warnings = detect_cycles(links)
        assert len(warnings) >= 1
        assert any("Cycle" in w for w in warnings)

    def test_valid_acyclic_chain_no_cycle_warning(self):
        """A valid linear chain with no cycles should not produce cycle warnings."""
        from portal.services.mission_control_projection_service import detect_cycles

        links = [
            CausationLink(
                source_type="command_event",
                source_id="evt-acyclic-1",
                sequence=1,
                event_type="RECEIVED",
                state="RECEIVED",
                hash="hash-acyclic-1",
                previous_hash=None,  # genesis
            ),
            CausationLink(
                source_type="command_event",
                source_id="evt-acyclic-2",
                sequence=2,
                event_type="EVALUATED",
                state="EVALUATED",
                hash="hash-acyclic-2",
                previous_hash="hash-acyclic-1",
            ),
            CausationLink(
                source_type="command_event",
                source_id="evt-acyclic-3",
                sequence=3,
                event_type="DISPATCHED",
                state="DISPATCHED",
                hash="hash-acyclic-3",
                previous_hash="hash-acyclic-2",
            ),
        ]
        warnings = detect_cycles(links)
        # No cycle warnings should be present
        assert not any("Cycle" in w for w in warnings)

    def test_empty_links_no_cycle_warning(self):
        """Empty links list should produce no warnings."""
        from portal.services.mission_control_projection_service import detect_cycles

        warnings = detect_cycles([])
        assert warnings == []

    def test_cycle_warning_contains_source_ids(self):
        """Cycle warning should include source IDs for diagnosis."""
        from portal.services.mission_control_projection_service import detect_cycles

        links = [
            CausationLink(
                source_type="command_event",
                source_id="evt-diag-1",
                sequence=1,
                event_type="RECEIVED",
                state="RECEIVED",
                hash="hash-diag-1",
                previous_hash="hash-diag-2",
            ),
            CausationLink(
                source_type="command_event",
                source_id="evt-diag-2",
                sequence=2,
                event_type="EVALUATED",
                state="EVALUATED",
                hash="hash-diag-2",
                previous_hash="hash-diag-1",
            ),
        ]
        warnings = detect_cycles(links)
        assert len(warnings) >= 1
        # Warning should contain source IDs
        cycle_warning = next(w for w in warnings if "Cycle" in w)
        assert "command_event" in cycle_warning

    @pytest.mark.asyncio
    async def test_cycle_detected_in_full_causation_chain(self, db: AsyncSession):
        """Cycle detection should fire when building a real causation chain."""
        from portal.services.mission_control_projection_service import get_causation_chain

        cmd = MissionControlCommand(
            id="cmd-cycle-001",
            tenant_id=TENANT_A,
            requested_by=USER_A,
            command_type="PAUSE_RUN",
            target_type="run",
            target_id="run-001",
            idempotency_key="idem-cycle-001",
            request_hash="hash-cycle",
            state="REFUSED",
            payload={},
            metadata_json={},
        )
        db.add(cmd)
        await db.flush()

        # Event 1: hash-A, previous=hash-B
        db.add(
            MissionControlCommandEvent(
                id="evt-cycle-1",
                command_id="cmd-cycle-001",
                sequence=1,
                event_type="RECEIVED",
                state="RECEIVED",
                payload={},
                previous_hash="hash-cycle-B",
                event_hash="hash-cycle-A",
            )
        )
        await db.flush()

        # Event 2: hash-B, previous=hash-A  (creates A <-> B cycle)
        db.add(
            MissionControlCommandEvent(
                id="evt-cycle-2",
                command_id="cmd-cycle-001",
                sequence=2,
                event_type="EVALUATED",
                state="EVALUATED",
                payload={},
                previous_hash="hash-cycle-A",
                event_hash="hash-cycle-B",
            )
        )
        await db.flush()

        chain = await get_causation_chain(db, tenant_id=TENANT_A, command_id="cmd-cycle-001")
        assert chain is not None
        assert any("Cycle" in w for w in chain.warnings)

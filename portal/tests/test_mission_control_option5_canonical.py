"""Focused canonical Mission/Run convergence tests."""
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from orchestration.durable_execution import DurableWorkflowEngine
from portal.database import Base
from portal.models.mission_control_command import (
    MissionControlCommand,
    MissionControlCommandEvent,
    MissionControlCommandReceipt,
)
from portal.models.mission_control_execution import Mission, Run
from portal.models.audit import AuditLog
from portal.services import mission_control_capability_policy as policy_module
from portal.services.durable_orchestration_authority import DurableOrchestrationAuthority
from portal.services.mission_control_capability_policy import (
    CapabilityDecision,
    CapabilityPolicyError,
)
from portal.services.mission_control_command_service import (
    CommandSubmission,
    CommandTargetType,
    CommandType,
    submit_canonical_command,
)
from portal.auth.rbac import CurrentUser


def _user():
    return CurrentUser(
        {
            "sub": "actor-a",
            "tenant_id": "tenant-a",
            "role": "ATTORNEY",
            "permissions": [],
        }
    )


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(
            lambda sync_connection: Base.metadata.create_all(
                sync_connection,
                tables=[
                    AuditLog.__table__,
                    MissionControlCommand.__table__,
                    MissionControlCommandEvent.__table__,
                    MissionControlCommandReceipt.__table__,
                    Mission.__table__,
                    Run.__table__,
                ],
            )
        )
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        yield session
    await engine.dispose()


def _register_engine(engine, name):
    # Mutate the internal registry only for the test fixture mock engine.
    engine._registered = {name: lambda _context, _input: _input}


def _classify(monkeypatch, mapping):
    monkeypatch.setattr(policy_module, "_CAPABILITY_CLASSIFICATIONS", mapping)


def start(mission_id, key="canonical-start-0001", approval=False):
    return CommandSubmission(
        CommandType.START_GOVERNED_RUN,
        CommandTargetType.MISSION,
        mission_id,
        key,
        None,
        {"workflow_type": "client-value-ignored", "require_approval": approval},
        {},
    )


def cancel(run_id, key="canonical-cancel-0001"):
    return CommandSubmission(
        CommandType.CANCEL_RUN,
        CommandTargetType.RUN,
        run_id,
        key,
        None,
        {},
        {},
    )


@pytest.mark.asyncio
async def test_start_duplicate_dispatches_once_and_preserves_identity(db, monkeypatch):
    _classify(monkeypatch, {"protected.real": CapabilityDecision.DIRECT_ALLOWED})
    mission = Mission(tenant_id="tenant-a", created_by="actor-a", workflow_type="protected.real", status="ACTIVE")
    db.add(mission)
    await db.flush()

    engine = AsyncMock()
    engine.start_workflow.return_value = "workflow-1"
    _register_engine(engine, "protected.real")
    authority = DurableOrchestrationAuthority(engine)
    first = await submit_canonical_command(db, start(mission.mission_id), _user(), authority)
    second = await submit_canonical_command(db, start(mission.mission_id), _user(), authority)
    assert first.run_id == second.run_id
    assert first.execution_ref == second.execution_ref == "workflow-1"
    assert second.duplicate is True
    assert engine.start_workflow.await_count == 1


@pytest.mark.asyncio
async def test_duplicate_start_conflict_does_not_dispatch_or_create_run(db, monkeypatch):
    _classify(monkeypatch, {"protected.real": CapabilityDecision.DIRECT_ALLOWED})
    mission = Mission(tenant_id="tenant-a", created_by="actor-a", workflow_type="protected.real", status="ACTIVE")
    db.add(mission)
    await db.flush()

    from portal.services.mission_control_command_service import DuplicateCommandConflictError

    engine = AsyncMock()
    engine.start_workflow.return_value = "workflow-1"
    _register_engine(engine, "protected.real")
    authority = DurableOrchestrationAuthority(engine)
    first = await submit_canonical_command(db, start(mission.mission_id), _user(), authority)
    assert first.command.state == "COMPLETED"

    changed = start(mission.mission_id, key="canonical-start-0001")
    changed.payload["input_data"] = {"altered": True}
    with pytest.raises(DuplicateCommandConflictError):
        await submit_canonical_command(db, changed, _user(), authority)

    runs = (await db.execute(select(Run).where(Run.mission_id == mission.mission_id))).scalars().all()
    assert len(runs) == 1
    assert engine.start_workflow.await_count == 1


@pytest.mark.asyncio
async def test_approval_required_never_dispatches_engine(db, monkeypatch):
    _classify(monkeypatch, {"protected.approval": CapabilityDecision.APPROVAL_REQUIRED})
    mission = Mission(tenant_id="tenant-a", created_by="actor-a", workflow_type="protected.approval", status="ACTIVE")
    db.add(mission)
    await db.flush()

    engine = AsyncMock()
    _register_engine(engine, "protected.approval")
    authority = DurableOrchestrationAuthority(engine)
    result = await submit_canonical_command(
        db,
        start(mission.mission_id, key="canonical-approval-0001"),
        _user(),
        authority,
    )
    assert result.command.state == "APPROVAL_REQUIRED"
    assert result.run_id
    assert result.execution_ref is None
    run = (await db.execute(select(Run).where(Run.run_id == result.run_id))).scalar_one()
    assert run.workflow_type == "protected.approval"
    assert run.input_data_hash is not None
    assert engine.start_workflow.await_count == 0


@pytest.mark.asyncio
async def test_inactive_mission_is_refused_without_dispatch(db, monkeypatch):
    _classify(monkeypatch, {"protected.real": CapabilityDecision.DIRECT_ALLOWED})
    mission = Mission(tenant_id="tenant-a", created_by="actor-a", workflow_type="protected.real", status="DRAFT")
    db.add(mission)
    await db.flush()

    engine = AsyncMock()
    _register_engine(engine, "protected.real")
    authority = DurableOrchestrationAuthority(engine)
    result = await submit_canonical_command(db, start(mission.mission_id), _user(), authority)
    assert result.command.state == "REFUSED"
    assert result.command.reason_code == "MISSION_INVALID_STATE"
    assert engine.start_workflow.await_count == 0


@pytest.mark.asyncio
async def test_dispatch_failure_leaves_no_false_active_state(db, monkeypatch):
    _classify(monkeypatch, {"protected.real": CapabilityDecision.DIRECT_ALLOWED})
    mission = Mission(tenant_id="tenant-a", created_by="actor-a", workflow_type="protected.real", status="ACTIVE")
    db.add(mission)
    await db.flush()

    engine = AsyncMock()
    engine.start_workflow.side_effect = RuntimeError("durable store unavailable")
    _register_engine(engine, "protected.real")
    authority = DurableOrchestrationAuthority(engine)
    result = await submit_canonical_command(db, start(mission.mission_id), _user(), authority)
    assert result.command.state == "FAILED"
    assert result.command.reason_code == "DURABLE_DISPATCH_FAILED"
    run = (await db.execute(select(Run).where(Run.run_id == result.run_id))).scalar_one()
    assert run.status == "FAILED"
    assert run.execution_ref is None
    assert run.failure_reason == "durable store unavailable"


@pytest.mark.asyncio
async def test_local_cancel_without_execution_ref_succeeds(db, monkeypatch):
    _classify(monkeypatch, {"protected.real": CapabilityDecision.DIRECT_ALLOWED})
    mission = Mission(tenant_id="tenant-a", created_by="actor-a", workflow_type="protected.real", status="ACTIVE")
    db.add(mission)
    await db.flush()
    run = Run(
        mission_id=mission.mission_id,
        tenant_id="tenant-a",
        status="PENDING",
        workflow_type="protected.real",
        input_data={},
        input_data_hash="abc",
        created_by="actor-a",
    )
    db.add(run)
    await db.flush()

    engine = AsyncMock()
    _register_engine(engine, "protected.real")
    authority = DurableOrchestrationAuthority(engine)
    result = await submit_canonical_command(db, cancel(run.run_id), _user(), authority)
    assert result.command.state == "COMPLETED"
    assert engine.cancel_workflow.await_count == 0


@pytest.mark.asyncio
async def test_durable_cancel_uses_exact_execution_ref(db, monkeypatch):
    _classify(monkeypatch, {"protected.real": CapabilityDecision.DIRECT_ALLOWED})
    mission = Mission(tenant_id="tenant-a", created_by="actor-a", workflow_type="protected.real", status="ACTIVE")
    db.add(mission)
    await db.flush()
    run = Run(
        mission_id=mission.mission_id,
        tenant_id="tenant-a",
        status="ACTIVE",
        workflow_type="protected.real",
        execution_ref="workflow-b",
        input_data={},
        input_data_hash="abc",
        created_by="actor-a",
    )
    db.add(run)
    await db.flush()

    engine = AsyncMock()
    engine.cancel_workflow.return_value = True
    _register_engine(engine, "protected.real")
    authority = DurableOrchestrationAuthority(engine)
    result = await submit_canonical_command(db, cancel(run.run_id), _user(), authority)
    assert result.command.state == "COMPLETED"
    assert engine.cancel_workflow.await_count == 1
    assert engine.cancel_workflow.await_args.args[0] == "workflow-b"


@pytest.mark.asyncio
async def test_durable_cancel_failure_reports_truthfully(db, monkeypatch):
    _classify(monkeypatch, {"protected.real": CapabilityDecision.DIRECT_ALLOWED})
    mission = Mission(tenant_id="tenant-a", created_by="actor-a", workflow_type="protected.real", status="ACTIVE")
    db.add(mission)
    await db.flush()
    run = Run(
        mission_id=mission.mission_id,
        tenant_id="tenant-a",
        status="ACTIVE",
        workflow_type="protected.real",
        execution_ref="workflow-missing",
        input_data={},
        input_data_hash="abc",
        created_by="actor-a",
    )
    db.add(run)
    await db.flush()

    engine = AsyncMock()
    engine.cancel_workflow.return_value = False
    _register_engine(engine, "protected.real")
    authority = DurableOrchestrationAuthority(engine)
    result = await submit_canonical_command(db, cancel(run.run_id), _user(), authority)
    assert result.command.state == "FAILED"
    assert result.command.reason_code == "DURABLE_WORKFLOW_NOT_FOUND"


@pytest.mark.asyncio
async def test_cross_tenant_cancellation_with_zero_engine_calls(db, monkeypatch):
    _classify(monkeypatch, {"protected.real": CapabilityDecision.DIRECT_ALLOWED})
    mission = Mission(tenant_id="tenant-a", created_by="actor-a", workflow_type="protected.real", status="ACTIVE")
    db.add(mission)
    await db.flush()
    run = Run(
        mission_id=mission.mission_id,
        tenant_id="tenant-a",
        status="ACTIVE",
        workflow_type="protected.real",
        execution_ref="workflow-b",
        input_data={},
        input_data_hash="abc",
        created_by="actor-a",
    )
    db.add(run)
    await db.flush()

    engine = AsyncMock()
    _register_engine(engine, "protected.real")
    authority = DurableOrchestrationAuthority(engine)
    attacker = CurrentUser(
        {
            "sub": "actor-b",
            "tenant_id": "tenant-b",
            "role": "ATTORNEY",
            "permissions": [],
        }
    )
    result = await submit_canonical_command(db, cancel(run.run_id), attacker, authority)
    assert result.command.state == "REFUSED"
    assert result.command.reason_code == "RUN_NOT_FOUND"
    assert engine.cancel_workflow.await_count == 0


@pytest.mark.asyncio
async def test_tenant_scoped_read_only_returns_same_tenant_runs(db, monkeypatch):
    _classify(monkeypatch, {})
    mission_a = Mission(tenant_id="tenant-a", created_by="actor-a", workflow_type=None, status="ACTIVE")
    mission_b = Mission(tenant_id="tenant-b", created_by="actor-b", workflow_type=None, status="ACTIVE")
    db.add_all([mission_a, mission_b])
    await db.flush()

    run_a = Run(mission_id=mission_a.mission_id, tenant_id="tenant-a", status="ACTIVE", workflow_type="protected.real", input_data={}, input_data_hash="a", created_by="actor-a")
    run_b = Run(mission_id=mission_b.mission_id, tenant_id="tenant-b", status="ACTIVE", workflow_type="protected.real", input_data={}, input_data_hash="b", created_by="actor-b")
    db.add_all([run_a, run_b])
    await db.flush()

    tenant_a_runs = (await db.execute(select(Run).where(Run.tenant_id == "tenant-a"))).scalars().all()
    tenant_b_runs = (await db.execute(select(Run).where(Run.tenant_id == "tenant-b"))).scalars().all()
    assert len(tenant_a_runs) == 1
    assert len(tenant_b_runs) == 1


@pytest.mark.asyncio
async def test_client_workflow_and_approval_flags_are_ignored(db, monkeypatch):
    _classify(monkeypatch, {"protected.real": CapabilityDecision.DIRECT_ALLOWED})
    mission = Mission(tenant_id="tenant-a", created_by="actor-a", workflow_type="protected.real", status="ACTIVE")
    db.add(mission)
    await db.flush()

    engine = AsyncMock()
    engine.start_workflow.return_value = "wf-1"
    _register_engine(engine, "protected.real")
    authority = DurableOrchestrationAuthority(engine)
    submission = CommandSubmission(
        CommandType.START_GOVERNED_RUN,
        CommandTargetType.MISSION,
        mission.mission_id,
        "canonical-filter-01",
        None,
        {"require_approval": True, "workflow_type": "client-controlled"},
        {},
    )
    request = await submit_canonical_command(db, submission, _user(), authority)
    assert request.command.state == "COMPLETED"
    run = (await db.execute(select(Run).where(Run.run_id == request.run_id))).scalar_one()
    assert run.workflow_type == "protected.real"
    assert engine.start_workflow.await_count == 1
    assert engine.start_workflow.await_args.args[0] == "protected.real"


@pytest.mark.asyncio
async def test_unbound_mission_is_refused(db, monkeypatch):
    _classify(monkeypatch, {})
    mission = Mission(tenant_id="tenant-a", created_by="actor-a", workflow_type=None, status="ACTIVE")
    db.add(mission)
    await db.flush()

    engine = AsyncMock()
    authority = DurableOrchestrationAuthority(engine)
    result = await submit_canonical_command(db, start(mission.mission_id), _user(), authority)
    assert result.command.state == "REFUSED"
    assert result.command.reason_code == "MISSION_CAPABILITY_UNBOUND"
    assert engine.start_workflow.await_count == 0


@pytest.mark.asyncio
async def test_unknown_capability_is_refused(db, monkeypatch):
    _classify(monkeypatch, {})
    mission = Mission(tenant_id="tenant-a", created_by="actor-a", workflow_type="unknown.workflow", status="ACTIVE")
    db.add(mission)
    await db.flush()

    engine = AsyncMock()
    authority = DurableOrchestrationAuthority(engine)
    result = await submit_canonical_command(db, start(mission.mission_id), _user(), authority)
    assert result.command.state == "REFUSED"
    assert result.command.reason_code == "CAPABILITY_DENIED"
    assert engine.start_workflow.await_count == 0

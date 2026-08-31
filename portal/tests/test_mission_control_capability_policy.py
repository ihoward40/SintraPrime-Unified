"""Server-owned Mission Control capability binding and policy tests."""

from __future__ import annotations

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from orchestration.durable_execution import DurableWorkflowEngine
from portal.database import Base
from portal.models.audit import AuditLog
from portal.models.mission_control_command import (
    MissionControlCommand,
    MissionControlCommandEvent,
    MissionControlCommandReceipt,
)
from portal.models.mission_control_execution import Mission, Run
from portal.services.durable_orchestration_authority import DurableOrchestrationAuthority
from portal.services import mission_control_capability_policy as policy_module
from portal.services.mission_control_capability_policy import (
    CapabilityDecision,
    CapabilityPolicyError,
    resolve_capability_policy,
)
from portal.services.mission_control_execution_binding import (
    ExecutionBindingError,
    resolve_mission_capability,
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


class TestResolveMissionCapability:
    @pytest.mark.asyncio
    async def test_missing_workflow_type_raises(self, db):
        mission = Mission(tenant_id="tenant-a", created_by="actor-a")
        db.add(mission)
        await db.flush()

        with pytest.raises(ExecutionBindingError, match="MISSION_CAPABILITY_UNBOUND"):
            await resolve_mission_capability(db, mission_id=mission.mission_id, tenant_id="tenant-a")

    @pytest.mark.asyncio
    async def test_cross_tenant_mission_capability_raises(self, db):
        mission_a = Mission(tenant_id="tenant-a", created_by="actor-a", workflow_type="protected.wf")
        db.add(mission_a)
        await db.flush()

        with pytest.raises(ExecutionBindingError, match="MISSION_NOT_FOUND"):
            await resolve_mission_capability(db, mission_id=mission_a.mission_id, tenant_id="tenant-b")

    @pytest.mark.asyncio
    async def test_returns_server_bound_capability(self, db):
        mission = Mission(tenant_id="tenant-a", created_by="actor-a", workflow_type="protected.real")
        db.add(mission)
        await db.flush()

        result = await resolve_mission_capability(db, mission_id=mission.mission_id, tenant_id="tenant-a")
        assert result == "protected.real"


class TestResolveCapabilityPolicy:
    def test_missing_capability_raises(self):
        engine = DurableWorkflowEngine()
        with pytest.raises(CapabilityPolicyError, match="CAPABILITY_DENIED"):
            resolve_capability_policy(engine, capability=None)

    def test_unknown_capability_raises(self):
        engine = DurableWorkflowEngine()
        with pytest.raises(CapabilityPolicyError, match="CAPABILITY_DENIED"):
            resolve_capability_policy(engine, capability="unknown.wf")

    def test_runtime_unregistered_capability_raises(self):
        engine = DurableWorkflowEngine()
        with pytest.raises(CapabilityPolicyError, match="CAPABILITY_DENIED"):
            resolve_capability_policy(engine, capability="protected.real")

    def test_direct_allowed_registered_capability(self, monkeypatch):
        engine = DurableWorkflowEngine()
        engine.register_workflow("protected.real", lambda ctx, data: data)
        monkeypatch.setattr(policy_module, "_CAPABILITY_CLASSIFICATIONS", {"protected.real": CapabilityDecision.DIRECT_ALLOWED})
        decision = resolve_capability_policy(engine, capability="protected.real")
        assert decision == CapabilityDecision.DIRECT_ALLOWED

    def test_approval_required_registered_capability(self, monkeypatch):
        engine = DurableWorkflowEngine()
        engine.register_workflow("protected.approval", lambda ctx, data: data)
        monkeypatch.setattr(policy_module, "_CAPABILITY_CLASSIFICATIONS", {"protected.approval": CapabilityDecision.APPROVAL_REQUIRED})
        decision = resolve_capability_policy(engine, capability="protected.approval")
        assert decision == CapabilityDecision.APPROVAL_REQUIRED

    def test_client_workflow_type_is_ignored_by_policy(self, monkeypatch):
        engine = DurableWorkflowEngine()
        engine.register_workflow("protected.real", lambda ctx, data: data)
        monkeypatch.setattr(policy_module, "_CAPABILITY_CLASSIFICATIONS", {"protected.real": CapabilityDecision.DIRECT_ALLOWED})
        with pytest.raises(CapabilityPolicyError, match="CAPABILITY_DENIED"):
            resolve_capability_policy(engine, capability="client-choice")

    def test_noop_capability_is_not_server_allowed(self):
        engine = DurableWorkflowEngine()
        engine.register_workflow("mission_control.noop", lambda ctx, data: data)
        with pytest.raises(CapabilityPolicyError, match="CAPABILITY_DENIED"):
            resolve_capability_policy(engine, capability="mission_control.noop")

    def test_test_capability_is_not_server_allowed(self):
        engine = DurableWorkflowEngine()
        engine.register_workflow("mission_control.test.echo", lambda ctx, data: data)
        with pytest.raises(CapabilityPolicyError, match="CAPABILITY_DENIED"):
            resolve_capability_policy(engine, capability="mission_control.test.echo")


class TestStartRunRespectsPolicy:
    @pytest.mark.asyncio
    async def test_approval_required_creates_run_without_dispatch(self, db):
        mission = Mission(tenant_id="tenant-a", created_by="actor-a", workflow_type="protected.approval")
        db.add(mission)
        await db.flush()

        engine = AsyncMock()
        authority = DurableOrchestrationAuthority(engine=engine)

        run = await authority.start_run(
            db,
            mission_id=mission.mission_id,
            tenant_id="tenant-a",
            created_by="actor-a",
            workflow_type="protected.approval",
            input_data={"x": 1},
            policy_decision=CapabilityDecision.APPROVAL_REQUIRED,
        )

        assert run.status == "APPROVAL_REQUIRED"
        assert run.execution_ref is None
        assert run.workflow_type == "protected.approval"
        assert run.input_data == {"x": 1}
        assert run.input_data_hash is not None
        engine.start_workflow.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_direct_allowed_dispatches_exactly_once(self, db):
        mission = Mission(tenant_id="tenant-a", created_by="actor-a", workflow_type="protected.real")
        db.add(mission)
        await db.flush()

        engine = AsyncMock()
        engine.start_workflow.return_value = "workflow-123"
        authority = DurableOrchestrationAuthority(engine=engine)

        run = await authority.start_run(
            db,
            mission_id=mission.mission_id,
            tenant_id="tenant-a",
            created_by="actor-a",
            workflow_type="protected.real",
            input_data={"x": 1},
            policy_decision=CapabilityDecision.DIRECT_ALLOWED,
        )

        assert run.status == "ACTIVE"
        assert run.execution_ref == "workflow-123"
        assert run.workflow_type == "protected.real"
        assert run.input_data_hash is not None
        engine.start_workflow.await_count == 1
        call_args = engine.start_workflow.await_args
        assert call_args.args[0] == "protected.real"

    @pytest.mark.asyncio
    async def test_input_hash_mismatch_after_approval_fails_closed(self, db):
        mission = Mission(tenant_id="tenant-a", created_by="actor-a", workflow_type="protected.approval")
        db.add(mission)
        await db.flush()

        engine = AsyncMock()
        authority = DurableOrchestrationAuthority(engine=engine)

        run = await authority.start_run(
            db,
            mission_id=mission.mission_id,
            tenant_id="tenant-a",
            created_by="actor-a",
            workflow_type="protected.approval",
            input_data={"x": 1},
            policy_decision=CapabilityDecision.APPROVAL_REQUIRED,
        )

        with pytest.raises(ValueError, match="INPUT_HASH_MISMATCH"):
            await authority.approve_and_start(
                db,
                run_id=run.run_id,
                tenant_id="tenant-a",
                input_data={"x": 2},
                principal_approval_artifact={"verified": True, "run_id": run.run_id},
            )

    @pytest.mark.asyncio
    async def test_approval_required_run_can_resume_with_matching_input(self, db):
        mission = Mission(tenant_id="tenant-a", created_by="actor-a", workflow_type="protected.approval")
        db.add(mission)
        await db.flush()

        engine = AsyncMock()
        engine.start_workflow.return_value = "workflow-123"
        authority = DurableOrchestrationAuthority(engine=engine)

        run = await authority.start_run(
            db,
            mission_id=mission.mission_id,
            tenant_id="tenant-a",
            created_by="actor-a",
            workflow_type="protected.approval",
            input_data={"x": 1},
            policy_decision=CapabilityDecision.APPROVAL_REQUIRED,
        )

        resumed = await authority.approve_and_start(
            db,
            run_id=run.run_id,
            tenant_id="tenant-a",
            input_data={"x": 1},
            principal_approval_artifact={"verified": True, "run_id": run.run_id},
        )
        assert resumed.status == "ACTIVE"
        assert resumed.execution_ref == "workflow-123"
        assert engine.start_workflow.await_count == 1

    @pytest.mark.asyncio
    async def test_approve_and_start_fails_closed_without_principal_artifact(self, db):
        from portal.services.durable_orchestration_authority import MissingPrincipalApprovalArtifactError
        mission = Mission(tenant_id="tenant-a", created_by="actor-a", workflow_type="protected.approval")
        db.add(mission)
        await db.flush()

        engine = AsyncMock()
        authority = DurableOrchestrationAuthority(engine=engine)
        run = await authority.start_run(
            db,
            mission_id=mission.mission_id,
            tenant_id="tenant-a",
            created_by="actor-a",
            workflow_type="protected.approval",
            input_data={"x": 1},
            policy_decision=CapabilityDecision.APPROVAL_REQUIRED,
        )

        with pytest.raises(MissingPrincipalApprovalArtifactError):
            await authority.approve_and_start(
                db,
                run_id=run.run_id,
                tenant_id="tenant-a",
                input_data={"x": 1},
            )
        assert engine.start_workflow.await_count == 0

    @pytest.mark.asyncio
    async def test_replay_of_approval_required_run_is_idempotent(self, db, monkeypatch):
        monkeypatch.setattr(policy_module, "_CAPABILITY_CLASSIFICATIONS", {"protected.approval": CapabilityDecision.APPROVAL_REQUIRED})
        from portal.services.mission_control_command_service import CommandSubmission, CommandTargetType, CommandType, submit_canonical_command
        from portal.auth.rbac import CurrentUser

        mission = Mission(tenant_id="tenant-a", created_by="actor-a", workflow_type="protected.approval", status="ACTIVE")
        db.add(mission)
        await db.flush()

        engine = AsyncMock()
        engine._registered = {"protected.approval": lambda _context, _input: _input}
        authority = DurableOrchestrationAuthority(engine=engine)
        user = CurrentUser({"sub": "actor-a", "tenant_id": "tenant-a", "role": "ATTORNEY", "permissions": []})

        submission = CommandSubmission(
            CommandType.START_GOVERNED_RUN,
            CommandTargetType.MISSION,
            mission.mission_id,
            "approval-idem-0001",
            None,
            {"input_data": {"x": 1}},
            {},
        )
        first = await submit_canonical_command(db, submission, user, authority)
        second = await submit_canonical_command(db, submission, user, authority)
        assert first.command.state == second.command.state == "APPROVAL_REQUIRED"
        assert first.run_id == second.run_id
        assert engine.start_workflow.await_count == 0

    @pytest.mark.asyncio
    async def test_approval_required_replay_with_changed_input_conflicts(self, db, monkeypatch):
        from portal.services.mission_control_command_service import (
            CommandSubmission,
            CommandTargetType,
            CommandType,
            DuplicateCommandConflictError,
            submit_canonical_command,
        )
        from portal.auth.rbac import CurrentUser

        monkeypatch.setattr(policy_module, "_CAPABILITY_CLASSIFICATIONS", {"protected.approval": CapabilityDecision.APPROVAL_REQUIRED})
        mission = Mission(tenant_id="tenant-a", created_by="actor-a", workflow_type="protected.approval", status="ACTIVE")
        db.add(mission)
        await db.flush()

        engine = AsyncMock()
        engine._registered = {"protected.approval": lambda _context, _input: _input}
        authority = DurableOrchestrationAuthority(engine=engine)
        user = CurrentUser({"sub": "actor-a", "tenant_id": "tenant-a", "role": "ATTORNEY", "permissions": []})

        first = CommandSubmission(
            CommandType.START_GOVERNED_RUN,
            CommandTargetType.MISSION,
            mission.mission_id,
            "approval-idem-conflict-0001",
            None,
            {"input_data": {"x": 1}},
            {},
        )
        await submit_canonical_command(db, first, user, authority)
        changed = CommandSubmission(
            CommandType.START_GOVERNED_RUN,
            CommandTargetType.MISSION,
            mission.mission_id,
            "approval-idem-conflict-0001",
            None,
            {"input_data": {"x": 2}},
            {},
        )
        with pytest.raises(DuplicateCommandConflictError):
            await submit_canonical_command(db, changed, user, authority)
        assert engine.start_workflow.await_count == 0

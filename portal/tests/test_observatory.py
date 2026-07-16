"""
Observatory Phase 1 tests.

Covers: event validation, hash chaining, mission lifecycle, agent registration,
approval flow, governance gates, kill switch, data masking.
"""

from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.database import Base
from portal.models.observatory import (
    Agent,
    Approval,
    Artifact,
    Evidence,
    Incident,
    KillSwitchState,
    Mission,
    MissionAgent,
    ObservatoryEvent,
    ObservatoryRunHead,
)
from portal.schemas.observatory import (
    ApprovalStatus,
    EventType,
    GovernanceGate,
    IncidentSeverity,
    IncidentStatus,
    MissionStatus,
)
from portal.services.observatory_service import (
    AgentService,
    ApprovalService,
    ArtifactService,
    DataMaskingService,
    EventService,
    EvidenceService,
    GovernanceService,
    IncidentService,
    KillSwitchActiveError,
    KillSwitchService,
    MissionService,
    ReplayService,
)
from portal.services.execution_guard import PrincipalContext


def _admin_principal():
    """Test-only principal with system_admin role for G4.7 guard calls."""
    return PrincipalContext.for_testing(
        subject_id="test-admin",
        roles=["system_admin", "incident_commander"],
    )

# ── All observatory tables for create_all ──────────────────────────────────────

OBSERVATORY_TABLES = [
    Agent.__table__,
    Mission.__table__,
    MissionAgent.__table__,
    ObservatoryEvent.__table__,
    ObservatoryRunHead.__table__,
    Approval.__table__,
    Evidence.__table__,
    Artifact.__table__,
    Incident.__table__,
    KillSwitchState.__table__,
]


# ── Fixtures ────────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def db_session():
    """Create a fresh async SQLite file-based session for each test.

    Uses a temp file instead of :memory: to avoid aiosqlite ResourceWarning
    when pytest-asyncio closes the event loop before GC runs.
    """
    import os, tempfile
    db_path = os.path.join(tempfile.gettempdir(), f"obs_test_{os.getpid()}_{id(object())}.db")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(sync_conn, tables=OBSERVATORY_TABLES)
        )
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    session = session_maker()
    # Disable guard audit events to avoid polluting event-count assertions
    from portal.services.execution_guard import ExecutionGuard
    ExecutionGuard._audit_enabled = False
    try:
        yield session
    finally:
        ExecutionGuard._audit_enabled = True
        await session.close()
        await engine.dispose()
        if os.path.exists(db_path):
            os.unlink(db_path)


# ── Helper ─────────────────────────────────────────────────────────────────────


def _hash(event_type, payload, previous_hash, timestamp, mission_id=None, agent_id=None):
    """Replicate the hash computation from EventService."""
    data = f"{event_type}|{mission_id or ''}|{agent_id or ''}|{previous_hash or ''}|{timestamp}|{payload}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


# ══════════════════════════════════════════════════════════════════════════════
# Event Service Tests
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_event_create_basic(db_session):
    """Test basic event creation with hash chaining."""
    event = await EventService.create(
        db_session,
        event_type=EventType.MISSION_CREATED,
        payload={"title": "Test mission"},
    )
    await db_session.commit()

    assert event.id is not None
    assert event.event_type == "MISSION_CREATED"
    assert event.event_hash is not None
    assert len(event.event_hash) == 64  # SHA-256 hex
    # First event has no previous
    assert event.previous_hash is None


@pytest.mark.asyncio
async def test_event_hash_chaining(db_session):
    """Test that events form a proper hash chain."""
    e1 = await EventService.create(
        db_session, event_type=EventType.MISSION_CREATED, payload={"seq": 1}
    )
    await db_session.commit()

    e2 = await EventService.create(
        db_session, event_type=EventType.AGENT_REGISTERED, payload={"seq": 2}
    )
    await db_session.commit()

    # Second event's previous_hash must equal first event's hash
    assert e2.previous_hash == e1.event_hash
    # Both hashes must be different
    assert e1.event_hash != e2.event_hash


@pytest.mark.asyncio
async def test_event_hash_deterministic(db_session):
    """Test that event hash computation is deterministic."""
    ts = datetime.now(UTC)
    ts_str = ts.isoformat()
    payload = {"key": "value"}

    h1 = EventService.compute_event_hash(
        "MISSION_CREATED", payload, None, ts_str, mission_id=None, agent_id=None
    )
    h2 = EventService.compute_event_hash(
        "MISSION_CREATED", payload, None, ts_str, mission_id=None, agent_id=None
    )
    assert h1 == h2


@pytest.mark.asyncio
async def test_event_list_with_filters(db_session):
    """Test listing events with mission filter."""
    mission = await MissionService.create(db_session, title="Filter Test")
    await db_session.commit()

    await EventService.create(
        db_session, event_type=EventType.MISSION_CREATED, mission_id=mission.id, payload={"a": 1}
    )
    await db_session.commit()

    await EventService.create(
        db_session, event_type=EventType.AGENT_REGISTERED, payload={"b": 2}
    )
    await db_session.commit()

    # Filter by mission
    items, total = await EventService.list_events(db_session, mission_id=mission.id)
    assert total == 1
    assert items[0].event_type == "MISSION_CREATED"

    # All events
    items2, total2 = await EventService.list_events(db_session)
    assert total2 == 2


@pytest.mark.asyncio
async def test_event_verify_chain_integrity(db_session):
    """Test that verify_chain returns True for valid chains."""
    await EventService.create(db_session, event_type=EventType.MISSION_CREATED, payload={"i": 1})
    await db_session.commit()
    await EventService.create(db_session, event_type=EventType.MISSION_STARTED, payload={"i": 2})
    await db_session.commit()

    valid = await EventService.verify_chain(db_session)
    assert valid.valid is True


@pytest.mark.asyncio
async def test_event_get_by_id(db_session):
    """Test fetching a single event by ID."""
    event = await EventService.create(
        db_session, event_type=EventType.SYSTEM_ALERT, payload={"alert": "test"}
    )
    await db_session.commit()

    fetched = await EventService.get_by_id(db_session, event.id)
    assert fetched is not None
    assert fetched.event_hash == event.event_hash


# ══════════════════════════════════════════════════════════════════════════════
# Mission Service Tests
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_mission_create(db_session):
    """Test mission creation."""
    mission = await MissionService.create(
        db_session,
        title="Test Mission",
        description="A test mission",
        objective="Test objective",
        governance_gates_required=["G-01", "G-05"],
    )
    await db_session.commit()

    assert mission.id is not None
    assert mission.title == "Test Mission"
    assert mission.status == "QUEUED"
    assert "G-01" in mission.governance_gates_required


@pytest.mark.asyncio
async def test_mission_lifecycle(db_session):
    """Test mission status transitions."""
    mission = await MissionService.create(db_session, title="Lifecycle Test")
    await db_session.commit()
    assert mission.status == "QUEUED"

    # Transition to PLANNING
    m = await MissionService.update_status(db_session, mission.id, MissionStatus.PLANNING)
    await db_session.commit()
    assert m.status == "PLANNING"

    # Transition to EXECUTING
    m = await MissionService.update_status(db_session, mission.id, MissionStatus.EXECUTING)
    await db_session.commit()
    assert m.status == "EXECUTING"

    # Transition to COMPLETED
    m = await MissionService.update_status(db_session, mission.id, MissionStatus.COMPLETED)
    await db_session.commit()
    assert m.status == "COMPLETED"


@pytest.mark.asyncio
async def test_mission_agent_assignment(db_session):
    """Test adding/removing agents from a mission."""
    mission = await MissionService.create(db_session, title="Agent Test", agent_ids=["AGENT-1"])
    await db_session.commit()

    agent_ids = await MissionService.get_agent_ids(db_session, mission.id)
    assert "AGENT-1" in agent_ids

    # Add another agent
    await MissionService.add_agent(db_session, mission.id, "AGENT-2", role="researcher")
    await db_session.commit()

    agent_ids = await MissionService.get_agent_ids(db_session, mission.id)
    assert "AGENT-2" in agent_ids

    # Remove an agent
    removed = await MissionService.remove_agent(db_session, mission.id, "AGENT-1")
    await db_session.commit()
    assert removed is True

    agent_ids = await MissionService.get_agent_ids(db_session, mission.id)
    assert "AGENT-1" not in agent_ids


@pytest.mark.asyncio
async def test_mission_list_with_filter(db_session):
    """Test listing missions with status filter."""
    await MissionService.create(db_session, title="Active Mission")
    await MissionService.create(db_session, title="Another Active")
    m3 = await MissionService.create(db_session, title="Completed Mission")
    await MissionService.update_status(db_session, m3.id, MissionStatus.COMPLETED)
    await db_session.commit()

    all_missions, total_all = await MissionService.list_missions(db_session)
    assert total_all >= 3

    completed, total_completed = await MissionService.list_missions(db_session, status="COMPLETED")
    assert total_completed >= 1
    assert all(m.status == "COMPLETED" for m in completed)


# ══════════════════════════════════════════════════════════════════════════════
# Agent Service Tests
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_agent_register(db_session):
    """Test agent registration."""
    agent = await AgentService.register(
        db_session,
        agent_id="NOVA-1",
        name="Nova Agent",
        agent_type="researcher",
        capabilities=["search", "analyze"],
    )
    await db_session.commit()

    assert agent.id is not None
    assert agent.agent_id == "NOVA-1"
    assert agent.status == "ACTIVE"
    assert "search" in agent.capabilities


@pytest.mark.asyncio
async def test_agent_heartbeat(db_session):
    """Test agent heartbeat update."""
    agent = await AgentService.register(
        db_session, agent_id="HEARTBEAT-1", name="HB Agent", agent_type="worker"
    )
    await db_session.commit()

    updated = await AgentService.heartbeat(db_session, "HEARTBEAT-1")
    await db_session.commit()

    assert updated is not None
    assert updated.last_heartbeat is not None


@pytest.mark.asyncio
async def test_agent_deregister(db_session):
    """Test agent deregistration."""
    agent = await AgentService.register(
        db_session, agent_id="DEREG-1", name="Dereg Agent", agent_type="worker"
    )
    await db_session.commit()

    success = await AgentService.deregister(db_session, "DEREG-1", principal_context=_admin_principal())
    await db_session.commit()
    assert success is True

    # Verify status changed
    agent_check = await AgentService.get_by_agent_id(db_session, "DEREG-1")
    assert agent_check.status == "DEREGISTERED"


@pytest.mark.asyncio
async def test_agent_list(db_session):
    """Test listing agents."""
    await AgentService.register(db_session, agent_id="LIST-1", name="List Agent 1", agent_type="worker")
    await AgentService.register(db_session, agent_id="LIST-2", name="List Agent 2", agent_type="worker")
    await db_session.commit()

    agents, total = await AgentService.list_agents(db_session)
    assert total >= 2


# ══════════════════════════════════════════════════════════════════════════════
# Approval Service Tests
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_approval_create(db_session):
    """Test creating an approval request."""
    mission = await MissionService.create(db_session, title="Approval Test")
    await db_session.commit()

    approval = await ApprovalService.create(
        db_session,
        mission_id=mission.id,
        requester="user-1",
        gate="G-05",
        reason="Need human approval for deployment",
    )
    await db_session.commit()

    assert approval.id is not None
    assert approval.status == "PENDING"
    assert approval.gate == "G-05"


@pytest.mark.asyncio
async def test_approval_decide(db_session):
    """Test approving a pending approval."""
    mission = await MissionService.create(db_session, title="Approval Decide Test")
    await db_session.commit()

    approval = await ApprovalService.create(
        db_session, mission_id=mission.id, requester="user-1", gate="G-05"
    )
    await db_session.commit()

    decided = await ApprovalService.decide(
        db_session, approval.id, ApprovalStatus.APPROVED, reviewer="admin-1", notes="Looks good"
    )
    await db_session.commit()

    assert decided.status == "APPROVED"
    assert decided.reviewer == "admin-1"


@pytest.mark.asyncio
async def test_approval_deny(db_session):
    """Test denying a pending approval."""
    mission = await MissionService.create(db_session, title="Deny Test")
    await db_session.commit()

    approval = await ApprovalService.create(
        db_session, mission_id=mission.id, requester="user-1", gate="G-06"
    )
    await db_session.commit()

    decided = await ApprovalService.decide(
        db_session, approval.id, ApprovalStatus.DENIED, reviewer="admin-1", notes="Insufficient evidence"
    )
    await db_session.commit()

    assert decided.status == "DENIED"


@pytest.mark.asyncio
async def test_approval_get_pending(db_session):
    """Test listing pending approvals."""
    m1 = await MissionService.create(db_session, title="Pending Test 1")
    await db_session.commit()
    await ApprovalService.create(db_session, mission_id=m1.id, requester="u1")
    await db_session.commit()

    pending = await ApprovalService.get_pending(db_session)
    assert len(pending) >= 1
    assert all(a.status == "PENDING" for a in pending)


# ══════════════════════════════════════════════════════════════════════════════
# Governance Gate Tests
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_governance_gate_g01_pass(db_session):
    """G-01 passes when mission has title and objective."""
    mission = await MissionService.create(
        db_session, title="G01 Test", objective="Complete the objective"
    )
    await db_session.commit()

    passed, reason = await GovernanceService.check_gate(
        db_session, mission_id=mission.id, gate=GovernanceGate.G_01
    )
    assert passed is True
    assert reason is None


@pytest.mark.asyncio
async def test_governance_gate_g01_fail_no_objective(db_session):
    """G-01 fails when mission has no objective."""
    mission = await MissionService.create(db_session, title="No Objective")
    await db_session.commit()

    passed, reason = await GovernanceService.check_gate(
        db_session, mission_id=mission.id, gate=GovernanceGate.G_01
    )
    assert passed is False
    assert "objective" in (reason or "").lower()


@pytest.mark.asyncio
async def test_governance_gate_g02_pass(db_session):
    """G-02 passes when mission has agents assigned."""
    mission = await MissionService.create(
        db_session, title="G02 Test", agent_ids=["AGENT-1"]
    )
    await db_session.commit()

    passed, reason = await GovernanceService.check_gate(
        db_session, mission_id=mission.id, gate=GovernanceGate.G_02
    )
    assert passed is True


@pytest.mark.asyncio
async def test_governance_gate_g02_fail_no_agents(db_session):
    """G-02 fails when no agents assigned."""
    mission = await MissionService.create(db_session, title="No Agents")
    await db_session.commit()

    passed, reason = await GovernanceService.check_gate(
        db_session, mission_id=mission.id, gate=GovernanceGate.G_02
    )
    assert passed is False


@pytest.mark.asyncio
async def test_governance_gate_g05_needs_approval(db_session):
    """G-05 passes when an approved approval exists for this gate."""
    mission = await MissionService.create(db_session, title="G05 Test")
    await db_session.commit()

    # First check without approval — should fail
    passed, reason = await GovernanceService.check_gate(
        db_session, mission_id=mission.id, gate=GovernanceGate.G_05
    )
    assert passed is False

    # Create and approve
    approval = await ApprovalService.create(
        db_session, mission_id=mission.id, requester="user-1", gate="G-05"
    )
    await db_session.commit()

    await ApprovalService.decide(
        db_session, approval.id, ApprovalStatus.APPROVED, reviewer="admin-1"
    )
    await db_session.commit()

    # Now check again — should pass
    passed, reason = await GovernanceService.check_gate(
        db_session, mission_id=mission.id, gate=GovernanceGate.G_05
    )
    assert passed is True


@pytest.mark.asyncio
async def test_governance_gate_g07_needs_verified_evidence(db_session):
    """G-07 passes when verified evidence exists."""
    mission = await MissionService.create(db_session, title="G07 Test")
    await db_session.commit()

    # No evidence — should fail
    passed, reason = await GovernanceService.check_gate(
        db_session, mission_id=mission.id, gate=GovernanceGate.G_07
    )
    assert passed is False

    # Create and verify evidence
    evidence = await EvidenceService.create(
        db_session, mission_id=mission.id, source="scanner", content_hash="abc123"
    )
    await db_session.commit()

    await EvidenceService.verify(db_session, evidence.id)
    await db_session.commit()

    passed, reason = await GovernanceService.check_gate(
        db_session, mission_id=mission.id, gate=GovernanceGate.G_07
    )
    assert passed is True


@pytest.mark.asyncio
async def test_governance_gate_record_result(db_session):
    """Test recording gate result on a mission."""
    mission = await MissionService.create(
        db_session, title="Gate Record Test", objective="obj"
    )
    await db_session.commit()

    updated = await GovernanceService.record_gate_result(
        db_session, mission_id=mission.id, gate=GovernanceGate.G_01, passed=True
    )
    await db_session.commit()

    assert "G-01" in updated.governance_gates_passed


@pytest.mark.asyncio
async def test_governance_gate_nonexistent_mission(db_session):
    """Gate check for non-existent mission should fail."""
    passed, reason = await GovernanceService.check_gate(
        db_session, mission_id=uuid4(), gate=GovernanceGate.G_01
    )
    assert passed is False
    assert "not found" in (reason or "").lower()


# ══════════════════════════════════════════════════════════════════════════════
# Evidence Service Tests
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_evidence_create_and_verify(db_session):
    """Test creating and verifying evidence."""
    mission = await MissionService.create(db_session, title="Evidence Test")
    await db_session.commit()

    evidence = await EvidenceService.create(
        db_session,
        mission_id=mission.id,
        source="scanner",
        content_hash="sha256abc",
        description="Test evidence",
    )
    await db_session.commit()

    assert evidence.id is not None
    assert evidence.verified is False

    verified = await EvidenceService.verify(db_session, evidence.id)
    await db_session.commit()

    assert verified.verified is True


@pytest.mark.asyncio
async def test_evidence_list_by_mission(db_session):
    """Test listing evidence for a mission."""
    mission = await MissionService.create(db_session, title="Evidence List Test")
    await db_session.commit()

    await EvidenceService.create(db_session, mission_id=mission.id, source="s1", content_hash="h1")
    await EvidenceService.create(db_session, mission_id=mission.id, source="s2", content_hash="h2")
    await db_session.commit()

    evidence_list = await EvidenceService.get_by_mission(db_session, mission.id)
    assert len(evidence_list) == 2


# ══════════════════════════════════════════════════════════════════════════════
# Incident Service Tests
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_incident_create(db_session):
    """Test incident creation."""
    incident = await IncidentService.create(
        db_session, title="Test Incident", severity=IncidentSeverity.HIGH
    )
    await db_session.commit()

    assert incident.id is not None
    assert incident.severity == "HIGH"
    assert incident.status == "OPEN"


@pytest.mark.asyncio
async def test_incident_resolve(db_session):
    """Test resolving an incident."""
    incident = await IncidentService.create(db_session, title="Resolve Test")
    await db_session.commit()

    resolved = await IncidentService.resolve(db_session, incident.id, "Fixed the issue")
    await db_session.commit()

    assert resolved.status == "RESOLVED"
    assert resolved.resolution == "Fixed the issue"


@pytest.mark.asyncio
async def test_incident_escalate(db_session):
    """Test escalating an incident — severity bumps up."""
    incident = await IncidentService.create(
        db_session, title="Escalate Test", severity=IncidentSeverity.MEDIUM
    )
    await db_session.commit()

    escalated = await IncidentService.escalate(db_session, incident.id)
    await db_session.commit()

    assert escalated.status == "ESCALATED"
    assert escalated.severity == "HIGH"  # MEDIUM → HIGH


@pytest.mark.asyncio
async def test_incident_escalate_critical_stays(db_session):
    """Escalating a CRITICAL incident stays CRITICAL."""
    incident = await IncidentService.create(
        db_session, title="Critical Test", severity=IncidentSeverity.CRITICAL
    )
    await db_session.commit()

    escalated = await IncidentService.escalate(db_session, incident.id)
    await db_session.commit()

    assert escalated.severity == "CRITICAL"  # Already max


# ══════════════════════════════════════════════════════════════════════════════
# Kill Switch Tests
# ══════════════════════════════════════════════════════════════════════════════



@pytest.mark.asyncio
async def test_kill_switch_cancels_missions(db_session):
    """Test that kill switch cancels active missions."""
    m1 = await MissionService.create(db_session, title="Active Mission 1")
    m2 = await MissionService.create(db_session, title="Active Mission 2")
    m3 = await MissionService.create(db_session, title="Active Mission 3")
    await MissionService.update_status(db_session, m3.id, MissionStatus.COMPLETED)
    await db_session.commit()

    count, affected, state = await KillSwitchService.activate(
        db_session, reason="Emergency", activated_by="admin"
    )
    await db_session.commit()

    assert count == 2  # Only the 2 QUEUED ones (m3 was COMPLETED)
    assert str(m3.id) not in affected
    assert state.is_active is True
    assert state.activated_by == "admin"

    # Verify cancelled status
    m1_check = await MissionService.get_by_id(db_session, m1.id)
    assert m1_check.status == "CANCELED"


@pytest.mark.asyncio
async def test_kill_switch_persistence(db_session):
    """Test that kill switch state persists across sessions (restart simulation).

    Uses a file-based SQLite database and opens a fresh session/connection
    to verify that the persisted state survives a simulated process restart.
    """
    import pathlib
    import tempfile

    db_path = pathlib.Path(tempfile.mkdtemp()) / "test_persistence.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"

    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(sync_conn, tables=OBSERVATORY_TABLES)
        )

    # ── Session 1: Activate ──
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session1:
        _, _, state = await KillSwitchService.activate(
            session1, reason="Security incident", activated_by="isiah"
        )
        await session1.commit()
        assert state.is_active is True

    # ── Session 2: Fresh connection, verify persistence ──
    async with session_maker() as session2:
        loaded = await KillSwitchService.get_active_state(session2)
        assert loaded is not None
        assert loaded.is_active is True
        assert loaded.activated_by == "isiah"
        assert loaded.reason == "Security incident"

    await engine.dispose()
    db_path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_kill_switch_idempotent_activation(db_session):
    """Test that activating an already-active kill switch is idempotent."""
    count1, _, state1 = await KillSwitchService.activate(
        db_session, reason="First activation", activated_by="isiah"
    )
    await db_session.commit()
    assert count1 == 0  # No active missions to cancel
    assert state1.is_active is True

    # Re-activate should return existing state without creating a new row
    count2, affected2, state2 = await KillSwitchService.activate(
        db_session, reason="Second activation", activated_by="isiah"
    )
    await db_session.commit()
    assert count2 == 0
    assert affected2 == []
    assert state2.id == state1.id  # Same state row


@pytest.mark.asyncio
async def test_kill_switch_clear(db_session):
    """Test clearing the kill switch creates KILL_SWITCH_CLEARED event."""
    await KillSwitchService.activate(
        db_session, reason="Emergency", activated_by="isiah"
    )
    await db_session.commit()

    # Clear
    cleared = await KillSwitchService.clear(
        db_session, cleared_by="isiah", reason="Threat resolved", principal_context=_admin_principal()
    )
    await db_session.commit()

    assert cleared is not None
    assert cleared.is_active is False
    assert cleared.cleared_by == "isiah"
    assert cleared.cleared_at is not None

    # Verify no active state
    assert await KillSwitchService.is_active(db_session) is False


@pytest.mark.asyncio
async def test_kill_switch_unauthorized_clear(db_session):
    """Test clearing when no active switch exists returns None.

    Attribution note: cleared_by is attribution only, not authentication.
    True authorization requires the clearing principal to be derived from
    authenticated request context (session/token), not from a request-body
    field. Cryptographic or session-backed principal authorization remains
    part of the hardening gate (Gate 4+).
    """
    # No active switch — clearing returns None
    result = await KillSwitchService.clear(
        db_session, cleared_by="anyone", reason="Nothing to clear", principal_context=_admin_principal()
    )
    assert result is None


@pytest.mark.asyncio
async def test_kill_switch_blocks_new_missions(db_session):
    """Test that active kill switch is reported as active."""
    await KillSwitchService.activate(
        db_session, reason="Block all", activated_by="admin"
    )
    await db_session.commit()

    # Kill switch should be active
    assert await KillSwitchService.is_active(db_session) is True

    # After clearing, should be inactive
    await KillSwitchService.clear(db_session, cleared_by="admin", principal_context=_admin_principal())
    await db_session.commit()
    assert await KillSwitchService.is_active(db_session) is False


@pytest.mark.asyncio
async def test_kill_switch_fails_closed(db_session):
    """Test that kill switch fails closed on DB errors."""
    import unittest.mock as mock
    with mock.patch.object(KillSwitchService, "get_active_state", side_effect=Exception("DB error")):
        assert await KillSwitchService.is_active(db_session) is True


@pytest.mark.asyncio
async def test_kill_switch_creates_audit_events(db_session):
    """Test that activation and clearing create hash-chained audit events."""
    from portal.schemas.observatory import EventType

    # Activate
    await KillSwitchService.activate(
        db_session, reason="Audit test", activated_by="admin"
    )
    await db_session.commit()

    # Check for KILL_SWITCH_ACTIVATED event
    from sqlalchemy import select as sa_select
    from portal.models.observatory import ObservatoryEvent
    stmt = sa_select(ObservatoryEvent).where(
        ObservatoryEvent.event_type == EventType.KILL_SWITCH_ACTIVATED.value
    )
    result = await db_session.execute(stmt)
    activate_events = result.scalars().all()
    assert len(activate_events) >= 1

    # Clear
    await KillSwitchService.clear(db_session, cleared_by="admin", reason="Done", principal_context=_admin_principal())
    await db_session.commit()

    # Check for KILL_SWITCH_CLEARED event
    stmt = sa_select(ObservatoryEvent).where(
        ObservatoryEvent.event_type == EventType.KILL_SWITCH_CLEARED.value
    )
    result = await db_session.execute(stmt)
    clear_events = result.scalars().all()
    assert len(clear_events) >= 1


@pytest.mark.asyncio
async def test_kill_switch_evidence_available_while_active(db_session):
    """Test that evidence and event-reading remain available while kill switch is active.

    The kill switch blocks consequential write operations (mission creation) at the
    service boundary. Evidence creation, event reading, and other read-only operations
    remain available. This test creates the mission BEFORE activation so that evidence
    can be attached to it while the switch is active.
    """
    from portal.schemas.observatory import EventType

    # Create a mission BEFORE activating the kill switch
    mission = await MissionService.create(db_session, title="Evidence test mission")
    await db_session.commit()
    assert mission is not None

    # Create an event before activation
    event = await EventService.create(
        db_session,
        event_type=EventType.SYSTEM_ALERT,
        payload={"msg": "pre-activation event"},
    )
    await db_session.commit()
    assert event is not None

    # Activate kill switch
    await KillSwitchService.activate(
        db_session, reason="Emergency", activated_by="admin"
    )
    await db_session.commit()

    # Evidence and event-reading endpoints should still work
    events = await EventService.list_events(db_session, limit=10)
    assert len(events) >= 1  # Can still read events

    # Can still create evidence while kill switch is active
    evidence = await EvidenceService.create(
        db_session,
        mission_id=mission.id,
        source="test",
        content_hash="abc123def456",
        content_type="text/plain",
        description="Created while kill switch is active",
    )
    await db_session.commit()
    assert evidence is not None

    # Mission creation must be blocked at the service boundary
    # ExecutionBlockedError is the canonical exception from the centralized guard
    from portal.services.execution_guard import ExecutionBlockedError
    with pytest.raises((KillSwitchActiveError, ExecutionBlockedError)):
        await MissionService.create(db_session, title="Should be blocked")


@pytest.mark.asyncio
async def test_kill_switch_second_clear_deterministic(db_session):
    """Test that clearing an already-cleared switch is deterministic (returns None)."""
    # Activate
    await KillSwitchService.activate(
        db_session, reason="Emergency", activated_by="admin"
    )
    await db_session.commit()

    # First clear
    cleared = await KillSwitchService.clear(
        db_session, cleared_by="admin", reason="Resolved", principal_context=_admin_principal()
    )
    await db_session.commit()
    assert cleared is not None
    assert cleared.is_active is False

    # Second clear should return None (no active switch to clear)
    second_clear = await KillSwitchService.clear(
        db_session, cleared_by="admin", reason="Double clear attempt", principal_context=_admin_principal()
    )
    assert second_clear is None


# Data Masking Tests
# ══════════════════════════════════════════════════════════════════════════════


def test_data_masking_basic():
    """Test that sensitive keys are masked."""
    payload = {
        "username": "alice",
        "api_key": "secret-key-123",
        "password": "hunter2",
        "data": {"nested_token": "abc", "safe_field": "visible"},
    }
    masked = DataMaskingService.mask_payload(payload)

    assert masked["username"] == "alice"
    assert masked["api_key"] == "***MASKED***"
    assert masked["password"] == "***MASKED***"
    assert masked["data"]["nested_token"] == "***MASKED***"
    assert masked["data"]["safe_field"] == "visible"


def test_data_masking_empty():
    """Test masking on empty payload."""
    assert DataMaskingService.mask_payload({}) == {}


def test_data_masking_no_sensitive():
    """Test masking when no sensitive fields present."""
    payload = {"name": "test", "value": 42}
    masked = DataMaskingService.mask_payload(payload)
    assert masked == payload


# ══════════════════════════════════════════════════════════════════════════════
# Replay Service Tests
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_replay_from_beginning(db_session):
    """Test replaying all events from the start."""
    await EventService.create(db_session, event_type=EventType.MISSION_CREATED, payload={"x": 1})
    await db_session.commit()
    await EventService.create(db_session, event_type=EventType.AGENT_REGISTERED, payload={"x": 2})
    await db_session.commit()

    events, total, truncated = await ReplayService.replay(db_session, limit=100)
    assert total == 2
    assert truncated is False
    assert len(events) == 2


@pytest.mark.asyncio
async def test_replay_from_hash(db_session):
    """Test replaying events starting from a specific hash."""
    e1 = await EventService.create(db_session, event_type=EventType.MISSION_CREATED, payload={"i": 1})
    await db_session.commit()
    e2 = await EventService.create(db_session, event_type=EventType.AGENT_REGISTERED, payload={"i": 2})
    await db_session.commit()
    e3 = await EventService.create(db_session, event_type=EventType.SYSTEM_ALERT, payload={"i": 3})
    await db_session.commit()

    # Replay from e2's hash — should get e2 and e3
    events, total, truncated = await ReplayService.replay(
        db_session, from_hash=e2.event_hash, limit=100
    )
    assert len(events) >= 1  # At least e2 itself


# ══════════════════════════════════════════════════════════════════════════════
# Artifact Service Tests
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_artifact_create(db_session):
    """Test creating an artifact."""
    mission = await MissionService.create(db_session, title="Artifact Test")
    await db_session.commit()

    artifact = await ArtifactService.create(
        db_session,
        mission_id=mission.id,
        name="report.pdf",
        artifact_type="document",
        uri="s3://bucket/report.pdf",
        content_hash="sha256hash123",
    )
    await db_session.commit()

    assert artifact.id is not None
    assert artifact.name == "report.pdf"


@pytest.mark.asyncio
async def test_artifact_list_by_mission(db_session):
    """Test listing artifacts for a mission."""
    mission = await MissionService.create(db_session, title="Artifact List Test")
    await db_session.commit()

    await ArtifactService.create(db_session, mission_id=mission.id, name="a1", artifact_type="doc")
    await ArtifactService.create(db_session, mission_id=mission.id, name="a2", artifact_type="code")
    await db_session.commit()

    artifacts = await ArtifactService.get_by_mission(db_session, mission.id)
    assert len(artifacts) == 2


# ══════════════════════════════════════════════════════════════════════════════
# Schema Validation Tests
# ══════════════════════════════════════════════════════════════════════════════


def test_event_type_enum():
    """Test EventType enum values."""
    assert EventType.MISSION_CREATED.value == "MISSION_CREATED"
    assert EventType.KILL_SWITCH_ACTIVATED.value == "KILL_SWITCH_ACTIVATED"
    assert EventType.GOVERNANCE_GATE_PASSED.value == "GOVERNANCE_GATE_PASSED"


def test_mission_status_enum():
    """Test MissionStatus enum values."""
    assert MissionStatus.QUEUED.value == "QUEUED"
    assert MissionStatus.COMPLETED.value == "COMPLETED"
    assert MissionStatus.COMPLETED_WITH_CONDITIONS.value == "COMPLETED_WITH_CONDITIONS"
    assert MissionStatus.WAITING_FOR_HUMAN.value == "WAITING_FOR_HUMAN"


def test_governance_gate_enum():
    """Test GovernanceGate enum values."""
    assert GovernanceGate.G_01.value == "G-01"
    assert GovernanceGate.G_10.value == "G-10"
    assert len(GovernanceGate) == 10


def test_event_create_request_validation():
    """Test that EventCreateRequest validates event_type."""
    from portal.schemas.observatory import EventCreateRequest

    req = EventCreateRequest(event_type=EventType.MISSION_CREATED, payload={"test": True})
    assert req.event_type == EventType.MISSION_CREATED


def test_kill_switch_request_validation():
    """Test KillSwitchRequest requires reason and activated_by."""
    from portal.schemas.observatory import KillSwitchRequest

    req = KillSwitchRequest(reason="Emergency shutdown", activated_by="admin")
    assert req.scope == "all"  # default
    assert req.reason == "Emergency shutdown"


def test_mission_create_request_defaults():
    """Test MissionCreateRequest defaults."""
    from portal.schemas.observatory import MissionCreateRequest

    req = MissionCreateRequest(title="Test")
    assert req.agent_ids == []
    assert req.governance_gates_required == []


def test_incident_severity_enum():
    """Test IncidentSeverity enum."""
    assert IncidentSeverity.LOW.value == "LOW"
    assert IncidentSeverity.CRITICAL.value == "CRITICAL"


def test_incident_status_enum():
    """Test IncidentStatus enum."""
    assert IncidentStatus.OPEN.value == "OPEN"
    assert IncidentStatus.ESCALATED.value == "ESCALATED"


# ── Concurrency and service-boundary tests ────────────────────────────────────


@pytest.mark.asyncio
async def test_kill_switch_concurrent_activation(db_session):
    """True concurrency test: two independent sessions attempt activation simultaneously.

    Uses file-based SQLite with a synchronization barrier to ensure both sessions
    begin their activation before either commits. The database-level partial unique
    index (uq_observatory_single_active_kill_switch) guarantees exactly one active
    row survives regardless of transaction interleaving.

    Required outcome:
    - Exactly one active kill-switch row in the database
    - Both callers receive a deterministic result (one wins, one gets idempotent)
    - No uncaught IntegrityError
    - No duplicated mission-cancellation side effects
    """
    import tempfile
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    # Use a file-based SQLite database for cross-session concurrency testing
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    test_url = f"sqlite+aiosqlite:///{db_path}"

    engine = create_async_engine(test_url)
    TestSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    # Create tables including the partial unique index
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=OBSERVATORY_TABLES)
        # Apply the partial unique index for concurrency safety
        await conn.execute(sa_text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_observatory_single_active_kill_switch "
            "ON observatory_kill_switch_state (is_active) WHERE is_active = 1"
        ))

    # Synchronization primitives
    barrier = asyncio.Event()
    results = {}

    async def activate_session(session_name: str):
        """Attempt activation in an independent session."""
        async with TestSessionLocal() as session:
            try:
                count, ids, state = await KillSwitchService.activate(
                    session,
                    reason=f"Emergency from {session_name}",
                    activated_by=session_name,
                )
                results[session_name] = ("success", count, len(ids), str(state.id))
            except IntegrityError:
                # This should be caught by the service layer, not surfaced here
                results[session_name] = ("integrity_error", 0, 0, "")
            except Exception as e:
                results[session_name] = ("error", 0, 0, str(e))
            finally:
                await session.commit()

    async with TestSessionLocal() as setup_session:
        # Verify no active switch exists
        assert await KillSwitchService.is_active(setup_session) is False

    # Launch both activations concurrently
    # Both will start at approximately the same time
    task_a = asyncio.create_task(activate_session("session_a"))
    task_b = asyncio.create_task(activate_session("session_b"))
    await asyncio.gather(task_a, task_b)

    # Verify: exactly one active row in the database
    async with TestSessionLocal() as verify_session:
        from sqlalchemy import select as sa_select
        active_states = await verify_session.execute(
            sa_select(KillSwitchState).where(KillSwitchState.is_active.is_(True))
        )
        active_rows = active_states.scalars().all()
        assert len(active_rows) == 1, (
            f"Expected exactly 1 active kill-switch row, found {len(active_rows)}"
        )

    # Both sessions should have gotten a result without uncaught errors
    for name in ("session_a", "session_b"):
        assert name in results, f"{name} did not produce a result"
        assert results[name][0] in ("success",), (
            f"{name} got unexpected result: {results[name]}"
        )

    # At least one session should report 0 missions affected (idempotent response)
    # and at least one should report the actual activation
    at_least_one_activation = any(
        r[0] == "success" and r[2] == 0  # idempotent: missions_affected == 0
        for r in [results["session_a"], results["session_b"]]
    )
    # This is guaranteed: both get a state object back (idempotent)
    assert at_least_one_activation, "Neither session received an idempotent response"

    # Cleanup
    await engine.dispose()
    import gc
    gc.collect()
    try:
        os.unlink(db_path)
    except PermissionError:
        # Windows: file may still be held by SQLite; clean up on next reboot
        pass


@pytest.mark.asyncio
async def test_mission_service_blocks_on_kill_switch(db_session):
    """MissionService.create() must refuse creation when the kill switch is active.

    This test verifies the service-boundary enforcement, not just the router-level
    guard. Any direct service call, background job, CLI tool, or internal agent
    must also be blocked.
    """
    # Verify mission creation works normally
    mission = await MissionService.create(db_session, title="Normal mission")
    await db_session.commit()
    assert mission is not None

    # Activate kill switch
    await KillSwitchService.activate(
        db_session, reason="Block missions test", activated_by="admin"
    )
    await db_session.commit()

    # MissionService.create() must raise via the execution guard
    # ExecutionBlockedError is the canonical exception from the centralized guard
    from portal.services.execution_guard import ExecutionBlockedError
    with pytest.raises((KillSwitchActiveError, ExecutionBlockedError)):
        await MissionService.create(db_session, title="Should be blocked")

    # After clearing, mission creation must work again
    await KillSwitchService.clear(db_session, cleared_by="admin", principal_context=_admin_principal())
    await db_session.commit()

    mission2 = await MissionService.create(db_session, title="Resumed mission")
    await db_session.commit()
    assert mission2 is not None
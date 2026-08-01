"""
Observatory service layer for the SintraPrime Portal.

Business logic for events, missions, agents, approvals, governance gates,
evidence, incidents, and replay — all async, using SQLAlchemy sessions.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from portal.models.observatory import (
    Agent,
    Approval,
    Artifact,
    ChainVerificationResult,
    Evidence,
    Incident,
    KillSwitchState,
    Mission,
    MissionAgent,
    ObservatoryEvent,
    ObservatoryRunHead,
    VerificationFailureReason,
)
from portal.schemas.observatory import (
    ApprovalStatus,
    EventType,
    GovernanceGate,
    IncidentSeverity,
    IncidentStatus,
    MissionStatus,
)

# Lazy import in function body to avoid circular dependency with execution_guard

logger = logging.getLogger(__name__)


class KillSwitchActiveError(Exception):
    """Raised when a consequential write operation is attempted while the kill switch is active.

    This is the centralized execution guard. All service methods that perform
    consequential operations (mission creation, mission resumption, agent spawning,
    external communication, repository publication, file mutation, production deployment)
    must raise this error when the kill switch is active.

    Read-only operations (evidence reading, event replay, incident review, switch
    status checking, switch clearing) remain available and must NOT raise this error.
    """


# ── Event Service ──────────────────────────────────────────────────────────────


class EventService:
    """Create, hash-chain, and query observatory events."""

    @staticmethod
    async def get_latest_hash(db: AsyncSession) -> str | None:
        """Return the event_hash of the most recent event, or None."""
        stmt = select(ObservatoryEvent.event_hash).order_by(
            ObservatoryEvent.created_at.desc()
        ).limit(1)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def compute_event_hash(
        event_type: str,
        payload: dict[str, Any],
        previous_hash: str | None,
        timestamp: str,
        mission_id: str | None = None,
        agent_id: str | None = None,
    ) -> str:
        """Compute SHA-256 hash for an event, chaining to previous."""
        data = f"{event_type}|{mission_id or ''}|{agent_id or ''}|{previous_hash or ''}|{timestamp}|{payload}"
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    @staticmethod
    async def create(
        db: AsyncSession,
        event_type: EventType | str,
        mission_id: UUID | None = None,
        agent_id: str | None = None,
        payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
        run_id: str = "default",
        skip_lock: bool = False,
    ) -> ObservatoryEvent:
        """Create a new hash-chained event with run-scoped concurrency control.

        This method uses the run-head row as the authoritative serialization
        point. The protocol is:

        1. SELECT ... FOR UPDATE on the run-head row (or INSERT if new)
        2. Read last_sequence and last_event_hash
        3. Assign sequence = last_sequence + 1
        4. Set previous_hash = last_event_hash (null for genesis)
        5. Compute canonical event hash
        6. Insert the event
        7. Update the run-head with new sequence and hash
        8. Commit (releases the lock)

        Genesis rule: sequence=1, previous_hash=null for the first event
        in any run.

        Set skip_lock=True only in test code that runs single-threaded.
        """
        from portal.services.chain_lock import get_or_create_run_head, advance_run_head

        # Step 1-2: Acquire run-head lock and read current state
        head = await get_or_create_run_head(db, run_id, for_update=not skip_lock)

        # Step 3: Assign sequence
        sequence = head.last_sequence + 1

        # Step 4: Determine previous_hash (genesis rule)
        if head.last_sequence == 0 and head.last_event_hash is None:
            previous_hash = None  # Genesis: first event in the run
        else:
            previous_hash = head.last_event_hash

        ts = timestamp or datetime.now(UTC)
        if ts.tzinfo is None:
            # Naive timestamp: reject for new events. Legacy verification
            # may treat naive timestamps as UTC, but new ingestion must not
            # accept them without explicit normalization.
            raise ValueError(
                f"Naive datetime received for event ingestion in run {run_id}. "
                f"All new events must use timezone-aware timestamps. "
                f"Use datetime.now(UTC) or pass an explicit tzinfo."
            )
        ts_str = ObservatoryEvent.canonical_timestamp(ts)
        payload = payload or {}
        event_type_str = event_type.value if isinstance(event_type, EventType) else event_type
        mission_str = str(mission_id) if mission_id else None

        # Step 5: Compute canonical event hash (includes run_id and sequence)
        event_hash = ObservatoryEvent.compute_hash(
            event_type_str, payload, previous_hash, ts_str,
            mission_id=mission_str, agent_id=agent_id,
            run_id=run_id, sequence=sequence,
        )

        # Compute payload digest for idempotency
        from portal.services.canonical import canonical_event_hash
        payload_digest = canonical_event_hash(payload)

        # Step 6: Insert the event
        event = ObservatoryEvent(
            run_id=run_id,
            sequence=sequence,
            hash_version=2,  # v2: includes run_id and sequence in hash
            event_type=event_type_str,
            mission_id=mission_id,
            agent_id=agent_id,
            payload=payload,
            payload_digest=payload_digest,
            metadata_=metadata,
            event_hash=event_hash,
            previous_hash=previous_hash,
            timestamp=ts,
        )
        db.add(event)

        # Step 7: Advance the run head
        await advance_run_head(db, run_id, sequence, event_hash)

        await db.flush()
        return event

    @staticmethod
    async def get_by_id(db: AsyncSession, event_id: UUID) -> ObservatoryEvent | None:
        stmt = select(ObservatoryEvent).where(ObservatoryEvent.id == event_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_events(
        db: AsyncSession,
        mission_id: UUID | None = None,
        agent_id: str | None = None,
        event_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[Sequence[ObservatoryEvent], int]:
        """List events with optional filters, return (items, total)."""
        stmt = select(ObservatoryEvent)
        count_stmt = select(func.count(ObservatoryEvent.id))

        if mission_id:
            stmt = stmt.where(ObservatoryEvent.mission_id == mission_id)
            count_stmt = count_stmt.where(ObservatoryEvent.mission_id == mission_id)
        if agent_id:
            stmt = stmt.where(ObservatoryEvent.agent_id == agent_id)
            count_stmt = count_stmt.where(ObservatoryEvent.agent_id == agent_id)
        if event_type:
            stmt = stmt.where(ObservatoryEvent.event_type == event_type)
            count_stmt = count_stmt.where(ObservatoryEvent.event_type == event_type)

        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.order_by(ObservatoryEvent.timestamp.asc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        items = result.scalars().all()
        return items, total

    @staticmethod
    async def verify_chain(db: AsyncSession, run_id: str | None = None, from_hash: str | None = None) -> ChainVerificationResult:
        """Verify the integrity of a hash chain.

        When run_id is specified, verifies only that run's chain.
        When run_id is None, verifies all chains (global verification).

        Returns a ChainVerificationResult with:
        - valid: True if the entire chain verifies, False otherwise
        - reason: specific failure reason when valid=False
        - run_id, sequence, event_id: identifying the failing event
        - detail: human-readable description of the failure

        Hash version semantics:
          v1: legacy formula — event_type, mission_id, agent_id, previous_hash, timestamp, payload
          v2: run-scoped formula — run_id, sequence, event_type, mission_id, agent_id,
              previous_hash, timestamp, payload

        The hash_version controls computation of the current event hash.
        The previous_hash always references the exact stored hash of the
        preceding event, regardless of that preceding event's version.
        """
        stmt = select(ObservatoryEvent).order_by(
            ObservatoryEvent.run_id.asc(),
            ObservatoryEvent.sequence.asc(),
        )
        if run_id:
            stmt = stmt.where(ObservatoryEvent.run_id == run_id)
        if from_hash:
            stmt = stmt.where(ObservatoryEvent.event_hash == from_hash)
        result = await db.execute(stmt)
        events = list(result.scalars().all())

        if not events:
            return ChainVerificationResult(valid=True)

        # Group by run_id
        from collections import defaultdict
        runs: dict[str, list] = defaultdict(list)
        for event in events:
            runs[event.run_id].append(event)

        for rid, run_events in runs.items():
            for i, event in enumerate(run_events):
                # Genesis rule: first event in a run
                if i == 0:
                    if event.sequence != 1:
                        return ChainVerificationResult(
                            valid=False,
                            reason=VerificationFailureReason.INVALID_GENESIS,
                            run_id=rid,
                            sequence=event.sequence,
                            event_id=event.id,
                            detail=f"Genesis event has sequence {event.sequence}, expected 1",
                        )
                    if event.previous_hash is not None:
                        return ChainVerificationResult(
                            valid=False,
                            reason=VerificationFailureReason.INVALID_GENESIS,
                            run_id=rid,
                            sequence=event.sequence,
                            event_id=event.id,
                            detail=f"Genesis event has previous_hash={event.previous_hash[:16]}..., expected null",
                        )
                else:
                    # Chain linkage: previous_hash must reference the stored
                    # hash of the preceding event, regardless of version.
                    expected_prev = run_events[i - 1].event_hash
                    if event.previous_hash != expected_prev:
                        return ChainVerificationResult(
                            valid=False,
                            reason=VerificationFailureReason.PREVIOUS_HASH_MISMATCH,
                            run_id=rid,
                            sequence=event.sequence,
                            event_id=event.id,
                            detail=f"previous_hash={event.previous_hash[:16] if event.previous_hash else 'None'}... "
                                   f"does not match preceding event hash={expected_prev[:16]}...",
                        )
                    # Sequence ordering
                    if event.sequence != run_events[i - 1].sequence + 1:
                        return ChainVerificationResult(
                            valid=False,
                            reason=VerificationFailureReason.SEQUENCE_GAP,
                            run_id=rid,
                            sequence=event.sequence,
                            event_id=event.id,
                            detail=f"Sequence {event.sequence} does not follow {run_events[i - 1].sequence}",
                        )

                # Hash verification: dispatch by hash_version
                if event.hash_version == 1:
                    expected_hash = ObservatoryEvent.compute_hash_v1(
                        event_type=event.event_type,
                        payload=event.payload,
                        previous_hash=event.previous_hash,
                        timestamp=ObservatoryEvent.canonical_timestamp(event.timestamp),
                        mission_id=str(event.mission_id) if event.mission_id else None,
                        agent_id=event.agent_id,
                    )
                elif event.hash_version == 2:
                    expected_hash = ObservatoryEvent.compute_hash_v2(
                        event_type=event.event_type,
                        payload=event.payload,
                        previous_hash=event.previous_hash,
                        timestamp=ObservatoryEvent.canonical_timestamp(event.timestamp),
                        mission_id=str(event.mission_id) if event.mission_id else None,
                        agent_id=event.agent_id,
                        run_id=event.run_id,
                        sequence=event.sequence,
                    )
                else:
                    return ChainVerificationResult(
                        valid=False,
                        reason=VerificationFailureReason.UNSUPPORTED_HASH_VERSION,
                        run_id=rid,
                        sequence=event.sequence,
                        event_id=event.id,
                        detail=f"Unsupported hash_version={event.hash_version}",
                    )

                if event.event_hash != expected_hash:
                    return ChainVerificationResult(
                        valid=False,
                        reason=VerificationFailureReason.EVENT_HASH_MISMATCH,
                        run_id=rid,
                        sequence=event.sequence,
                        event_id=event.id,
                        detail=f"Stored hash={event.event_hash[:16]}... computed={expected_hash[:16]}...",
                    )

            # Verify run-head terminal state
            head_stmt = select(ObservatoryRunHead).where(
                ObservatoryRunHead.run_id == rid
            )
            head_result = await db.execute(head_stmt)
            head = head_result.scalars().first()

            last_event = run_events[-1]
            if head is None:
                return ChainVerificationResult(
                    valid=False,
                    reason=VerificationFailureReason.RUN_HEAD_MISSING,
                    run_id=rid,
                    sequence=last_event.sequence,
                    detail=f"No run-head row for run_id={rid} with {len(run_events)} events",
                )
            # Run-head must match terminal event
            if head.last_sequence != last_event.sequence:
                return ChainVerificationResult(
                    valid=False,
                    reason=VerificationFailureReason.RUN_HEAD_SEQUENCE_MISMATCH,
                    run_id=rid,
                    sequence=last_event.sequence,
                    detail=f"Run-head last_sequence={head.last_sequence} != event sequence={last_event.sequence}",
                )
            if head.last_event_hash != last_event.event_hash:
                return ChainVerificationResult(
                    valid=False,
                    reason=VerificationFailureReason.RUN_HEAD_HASH_MISMATCH,
                    run_id=rid,
                    sequence=last_event.sequence,
                    detail=f"Run-head hash={head.last_event_hash[:16]}... != event hash={last_event.event_hash[:16]}...",
                )

        return ChainVerificationResult(valid=True)


# ── Mission Service ─────────────────────────────────────────────────────────────


class MissionService:

    @staticmethod
    async def create(
        db: AsyncSession,
        title: str,
        description: str | None = None,
        objective: str | None = None,
        agent_ids: list[str] | None = None,
        governance_gates_required: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Mission:
        # ── Kill-switch enforcement at service boundary ──────────────────
        # Uses the centralized execution guard. All consequential write
        # operations must use require_execution_allowed() — not inline checks.
        # Lazy import to avoid circular dependency.
        from portal.services.execution_guard import ActionType, require_execution_allowed
        await require_execution_allowed(
            db, ActionType.MISSION_CREATE, mission_id=None, agent_id=None,
        )

        mission = Mission(
            title=title,
            description=description,
            objective=objective,
            status=MissionStatus.QUEUED.value,
            governance_gates_required=governance_gates_required or [],
            governance_gates_passed=[],
            metadata_=metadata,
        )
        db.add(mission)
        await db.flush()

        # Assign agents
        for aid in (agent_ids or []):
            ma = MissionAgent(mission_id=mission.id, agent_id=aid)
            db.add(ma)
        await db.flush()
        return mission

    @staticmethod
    async def get_by_id(db: AsyncSession, mission_id: UUID) -> Mission | None:
        stmt = select(Mission).where(Mission.id == mission_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_status(db: AsyncSession, mission_id: UUID, status: MissionStatus | str) -> Mission | None:
        mission = await MissionService.get_by_id(db, mission_id)
        if mission is None:
            return None
        status_str = status.value if isinstance(status, MissionStatus) else status
        mission.status = status_str
        await db.flush()
        return mission

    @staticmethod
    async def list_missions(
        db: AsyncSession,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[Mission], int]:
        stmt = select(Mission)
        count_stmt = select(func.count(Mission.id))

        if status:
            stmt = stmt.where(Mission.status == status)
            count_stmt = count_stmt.where(Mission.status == status)

        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.order_by(Mission.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        items = result.scalars().all()
        return items, total

    @staticmethod
    async def add_agent(db: AsyncSession, mission_id: UUID, agent_id: str, role: str | None = None) -> MissionAgent:
        ma = MissionAgent(mission_id=mission_id, agent_id=agent_id, role=role)
        db.add(ma)
        await db.flush()
        return ma

    @staticmethod
    async def remove_agent(db: AsyncSession, mission_id: UUID, agent_id: str) -> bool:
        stmt = select(MissionAgent).where(
            MissionAgent.mission_id == mission_id,
            MissionAgent.agent_id == agent_id,
        )
        result = await db.execute(stmt)
        ma = result.scalar_one_or_none()
        if ma is None:
            return False
        await db.delete(ma)
        await db.flush()
        return True

    @staticmethod
    async def get_agent_ids(db: AsyncSession, mission_id: UUID) -> list[str]:
        stmt = select(MissionAgent.agent_id).where(MissionAgent.mission_id == mission_id)
        result = await db.execute(stmt)
        return [row[0] for row in result.all()]


# ── Agent Service ──────────────────────────────────────────────────────────────


class AgentService:

    @staticmethod
    async def register(
        db: AsyncSession,
        agent_id: str,
        name: str,
        agent_type: str,
        capabilities: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Agent:
        agent = Agent(
            agent_id=agent_id,
            name=name,
            agent_type=agent_type,
            status="ACTIVE",
            capabilities=capabilities or [],
            metadata_=metadata,
        )
        db.add(agent)
        await db.flush()
        return agent

    @staticmethod
    async def get_by_agent_id(db: AsyncSession, agent_id: str) -> Agent | None:
        stmt = select(Agent).where(Agent.agent_id == agent_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def heartbeat(db: AsyncSession, agent_id: str) -> Agent | None:
        agent = await AgentService.get_by_agent_id(db, agent_id)
        if agent is None:
            return None
        agent.last_heartbeat = datetime.now(UTC)
        await db.flush()
        return agent

    @staticmethod
    async def deregister(db: AsyncSession, agent_id: str) -> bool:
        agent = await AgentService.get_by_agent_id(db, agent_id)
        if agent is None:
            return False
        agent.status = "DEREGISTERED"
        await db.flush()
        return True

    @staticmethod
    async def list_agents(
        db: AsyncSession,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[Agent], int]:
        stmt = select(Agent)
        count_stmt = select(func.count(Agent.id))

        if status:
            stmt = stmt.where(Agent.status == status)
            count_stmt = count_stmt.where(Agent.status == status)

        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.order_by(Agent.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        items = result.scalars().all()
        return items, total


# ── Approval Service ──────────────────────────────────────────────────────────


class ApprovalService:

    @staticmethod
    async def create(
        db: AsyncSession,
        mission_id: UUID,
        requester: str,
        gate: str | None = None,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Approval:
        approval = Approval(
            mission_id=mission_id,
            gate=gate,
            requester=requester,
            status=ApprovalStatus.PENDING.value,
            reason=reason,
            metadata_=metadata,
        )
        db.add(approval)
        await db.flush()
        return approval

    @staticmethod
    async def decide(
        db: AsyncSession,
        approval_id: UUID,
        decision: ApprovalStatus | str,
        reviewer: str,
        notes: str | None = None,
    ) -> Approval | None:
        stmt = select(Approval).where(Approval.id == approval_id)
        result = await db.execute(stmt)
        approval = result.scalar_one_or_none()
        if approval is None:
            return None
        decision_str = decision.value if isinstance(decision, ApprovalStatus) else decision
        approval.status = decision_str
        approval.reviewer = reviewer
        approval.notes = notes
        await db.flush()
        return approval

    @staticmethod
    async def get_by_mission(db: AsyncSession, mission_id: UUID) -> Sequence[Approval]:
        stmt = select(Approval).where(Approval.mission_id == mission_id).order_by(Approval.created_at.asc())
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_pending(db: AsyncSession, mission_id: UUID | None = None) -> Sequence[Approval]:
        stmt = select(Approval).where(Approval.status == ApprovalStatus.PENDING.value)
        if mission_id:
            stmt = stmt.where(Approval.mission_id == mission_id)
        stmt = stmt.order_by(Approval.created_at.asc())
        result = await db.execute(stmt)
        return result.scalars().all()


# ── Governance Service ─────────────────────────────────────────────────────────


class GovernanceService:
    """Check and enforce governance gates G-01 through G-10."""

    # Gate definitions with check logic
    GATE_DEFINITIONS: ClassVar[dict[GovernanceGate, str]] = {
        GovernanceGate.G_01: "Mission scope validated",
        GovernanceGate.G_02: "Agent authorization verified",
        GovernanceGate.G_03: "Data access policy checked",
        GovernanceGate.G_04: "Output quality threshold met",
        GovernanceGate.G_05: "Human approval obtained",
        GovernanceGate.G_06: "Compliance review passed",
        GovernanceGate.G_07: "Security scan completed",
        GovernanceGate.G_08: "Impact assessment approved",
        GovernanceGate.G_09: "Rollback plan verified",
        GovernanceGate.G_10: "Final sign-off received",
    }

    @staticmethod
    async def check_gate(
        db: AsyncSession,
        mission_id: UUID,
        gate: GovernanceGate,
        evidence_ids: list[UUID] | None = None,
    ) -> tuple[bool, str | None]:
        """Check if a mission passes a governance gate.

        Returns (passed, reason).
        Gate checks are rule-based:
        - G-01: Mission must exist and have a title/objective
        - G-02: Mission must have at least one agent assigned
        - G-05: Must have an APPROVED approval for this gate
        - G-07: Must have at least one evidence item (verified)
        - Others: Pass if evidence provided, fail if not
        """
        mission = await MissionService.get_by_id(db, mission_id)
        if mission is None:
            return False, "Mission not found"

        gate_str = gate.value if isinstance(gate, GovernanceGate) else gate

        if gate == GovernanceGate.G_01:
            # Mission scope validated — need title and objective
            if not mission.title or not mission.objective:
                return False, "Mission missing title or objective"
            return True, None

        if gate == GovernanceGate.G_02:
            # Agent authorization — need at least one assigned agent
            agent_ids = await MissionService.get_agent_ids(db, mission_id)
            if not agent_ids:
                return False, "No agents assigned to mission"
            return True, None

        if gate == GovernanceGate.G_03:
            # Data access policy — pass by default with evidence
            if evidence_ids:
                return True, None
            return False, "No evidence provided for data access check"

        if gate == GovernanceGate.G_04:
            # Output quality — pass by default with evidence
            if evidence_ids:
                return True, None
            return False, "No evidence provided for quality check"

        if gate == GovernanceGate.G_05:
            # Human approval — must have an APPROVED approval for this gate
            approvals = await ApprovalService.get_by_mission(db, mission_id)
            for a in approvals:
                if a.gate == gate_str and a.status == ApprovalStatus.APPROVED.value:
                    return True, None
            return False, "No approved human approval for this gate"

        if gate == GovernanceGate.G_06:
            # Compliance review — pass with evidence
            if evidence_ids:
                return True, None
            return False, "No evidence provided for compliance review"

        if gate == GovernanceGate.G_07:
            # Security scan — need verified evidence
            stmt = select(Evidence).where(
                Evidence.mission_id == mission_id,
                Evidence.verified == True,  # noqa: E712
            )
            result = await db.execute(stmt)
            verified = result.scalars().all()
            if verified:
                return True, None
            return False, "No verified evidence for security scan"

        if gate == GovernanceGate.G_08:
            # Impact assessment — pass with evidence
            if evidence_ids:
                return True, None
            return False, "No evidence provided for impact assessment"

        if gate == GovernanceGate.G_09:
            # Rollback plan — pass with evidence
            if evidence_ids:
                return True, None
            return False, "No evidence provided for rollback plan"

        if gate == GovernanceGate.G_10:
            # Final sign-off — must have all required gates passed
            required = mission.governance_gates_required
            if required and set(required).issubset(set(mission.governance_gates_passed)):
                return True, None
            missing = set(required) - set(mission.governance_gates_passed)
            return False, f"Missing passed gates: {sorted(missing)}"

        return False, f"Unknown gate: {gate}"

    @staticmethod
    async def record_gate_result(
        db: AsyncSession,
        mission_id: UUID,
        gate: GovernanceGate,
        passed: bool,
        reason: str | None = None,
    ) -> Mission | None:
        """Record a gate check result on the mission."""
        mission = await MissionService.get_by_id(db, mission_id)
        if mission is None:
            return None
        gate_str = gate.value if isinstance(gate, GovernanceGate) else gate
        passed_gates = list(mission.governance_gates_passed) or []
        if passed and gate_str not in passed_gates:
            passed_gates.append(gate_str)
            mission.governance_gates_passed = passed_gates
            await db.flush()
        return mission


# ── Evidence Service ───────────────────────────────────────────────────────────


class EvidenceService:

    @staticmethod
    async def create(
        db: AsyncSession,
        mission_id: UUID,
        source: str,
        content_hash: str,
        content_type: str = "text/plain",
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Evidence:
        evidence = Evidence(
            mission_id=mission_id,
            source=source,
            content_type=content_type,
            content_hash=content_hash,
            description=description,
            metadata_=metadata,
        )
        db.add(evidence)
        await db.flush()
        return evidence

    @staticmethod
    async def verify(db: AsyncSession, evidence_id: UUID) -> Evidence | None:
        stmt = select(Evidence).where(Evidence.id == evidence_id)
        result = await db.execute(stmt)
        evidence = result.scalar_one_or_none()
        if evidence is None:
            return None
        evidence.verified = True
        await db.flush()
        return evidence

    @staticmethod
    async def get_by_mission(db: AsyncSession, mission_id: UUID) -> Sequence[Evidence]:
        stmt = select(Evidence).where(Evidence.mission_id == mission_id).order_by(Evidence.created_at.asc())
        result = await db.execute(stmt)
        return result.scalars().all()


# ── Artifact Service ───────────────────────────────────────────────────────────


class ArtifactService:

    @staticmethod
    async def create(
        db: AsyncSession,
        mission_id: UUID,
        name: str,
        artifact_type: str,
        uri: str | None = None,
        content_hash: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Artifact:
        artifact = Artifact(
            mission_id=mission_id,
            name=name,
            artifact_type=artifact_type,
            uri=uri,
            content_hash=content_hash,
            metadata_=metadata,
        )
        db.add(artifact)
        await db.flush()
        return artifact

    @staticmethod
    async def get_by_mission(db: AsyncSession, mission_id: UUID) -> Sequence[Artifact]:
        stmt = select(Artifact).where(Artifact.mission_id == mission_id).order_by(Artifact.created_at.asc())
        result = await db.execute(stmt)
        return result.scalars().all()


# ── Incident Service ──────────────────────────────────────────────────────────


class IncidentService:

    @staticmethod
    async def create(
        db: AsyncSession,
        title: str,
        severity: IncidentSeverity | str = IncidentSeverity.MEDIUM,
        mission_id: UUID | None = None,
        agent_id: str | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Incident:
        severity_str = severity.value if isinstance(severity, IncidentSeverity) else severity
        incident = Incident(
            mission_id=mission_id,
            agent_id=agent_id,
            severity=severity_str,
            status=IncidentStatus.OPEN.value,
            title=title,
            description=description,
            metadata_=metadata,
        )
        db.add(incident)
        await db.flush()
        return incident

    @staticmethod
    async def resolve(db: AsyncSession, incident_id: UUID, resolution: str) -> Incident | None:
        stmt = select(Incident).where(Incident.id == incident_id)
        result = await db.execute(stmt)
        incident = result.scalar_one_or_none()
        if incident is None:
            return None
        incident.status = IncidentStatus.RESOLVED.value
        incident.resolution = resolution
        await db.flush()
        return incident

    @staticmethod
    async def escalate(db: AsyncSession, incident_id: UUID) -> Incident | None:
        stmt = select(Incident).where(Incident.id == incident_id)
        result = await db.execute(stmt)
        incident = result.scalar_one_or_none()
        if incident is None:
            return None
        incident.status = IncidentStatus.ESCALATED.value
        # Escalate severity if possible
        severity_order = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        idx = severity_order.index(incident.severity) if incident.severity in severity_order else 0
        if idx < len(severity_order) - 1:
            incident.severity = severity_order[idx + 1]
        await db.flush()
        return incident

    @staticmethod
    async def list_incidents(
        db: AsyncSession,
        mission_id: UUID | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[Incident], int]:
        stmt = select(Incident)
        count_stmt = select(func.count(Incident.id))

        if mission_id:
            stmt = stmt.where(Incident.mission_id == mission_id)
            count_stmt = count_stmt.where(Incident.mission_id == mission_id)
        if status:
            stmt = stmt.where(Incident.status == status)
            count_stmt = count_stmt.where(Incident.status == status)

        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.order_by(Incident.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        items = result.scalars().all()
        return items, total


# ── Replay Service ─────────────────────────────────────────────────────────────


class ReplayService:
    """Replay events from a given point in the hash chain."""

    @staticmethod
    async def replay(
        db: AsyncSession,
        from_hash: str | None = None,
        from_timestamp: datetime | None = None,
        mission_id: UUID | None = None,
        limit: int = 100,
    ) -> tuple[Sequence[ObservatoryEvent], int, bool]:
        """Replay events from a given hash or timestamp.

        Returns (events, total, truncated).
        """
        stmt = select(ObservatoryEvent)
        count_stmt = select(func.count(ObservatoryEvent.id))

        if mission_id:
            stmt = stmt.where(ObservatoryEvent.mission_id == mission_id)
            count_stmt = count_stmt.where(ObservatoryEvent.mission_id == mission_id)

        if from_hash:
            # Find the event with this hash and start from there
            start_event = await db.execute(
                select(ObservatoryEvent).where(ObservatoryEvent.event_hash == from_hash)
            )
            start = start_event.scalar_one_or_none()
            if start:
                stmt = stmt.where(ObservatoryEvent.timestamp >= start.timestamp)
                count_stmt = count_stmt.where(ObservatoryEvent.timestamp >= start.timestamp)
        elif from_timestamp:
            stmt = stmt.where(ObservatoryEvent.timestamp >= from_timestamp)
            count_stmt = count_stmt.where(ObservatoryEvent.timestamp >= from_timestamp)

        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        truncated = total > limit
        stmt = stmt.order_by(ObservatoryEvent.timestamp.asc()).limit(limit)
        result = await db.execute(stmt)
        events = result.scalars().all()
        return events, total, truncated


# ── Kill Switch ────────────────────────────────────────────────────────────────


class KillSwitchService:
    """Emergency kill switch — persistent, idempotent, fails closed.

    The kill switch state is persisted in the database. On startup, the
    application must load the current state. An active switch prevents
    new executable missions and consequential tool calls. Evidence and
    event-reading endpoints remain available while active. The switch
    fails closed: if persistence state cannot be safely determined, it
    is treated as active.
    """

    @staticmethod
    async def get_active_state(db: AsyncSession) -> KillSwitchState | None:
        """Return the currently active kill switch, or None if cleared."""
        stmt = (
            select(KillSwitchState)
            .where(KillSwitchState.is_active.is_(True))
            .order_by(KillSwitchState.activated_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def is_active(db: AsyncSession) -> bool:
        """Check if the kill switch is currently active. Fails closed."""
        try:
            state = await KillSwitchService.get_active_state(db)
            return state is not None
        except Exception:
            # If we cannot determine state, fail closed
            return True

    @staticmethod
    async def activate(
        db: AsyncSession,
        reason: str,
        activated_by: str,
        scope: str = "all",
    ) -> tuple[int, list[str], KillSwitchState]:
        """Activate the kill switch. Idempotent — re-activation returns existing state.

        Concurrency safety: a partial unique index (uq_observatory_single_active_kill_switch)
        guarantees at most one active row at the database level. If two concurrent calls
        both observe no active state and attempt insertion, the database rejects the
        second with an IntegrityError. This method catches that error, re-queries for
        the winning state, and returns it idempotently.

        The service-layer pre-check (get_active_state) is a performance optimization,
        not a correctness guarantee. The database constraint is the authoritative guard.

        Returns (missions_affected, affected_mission_ids, kill_switch_state).
        """
        # Idempotency: if already active, return existing state
        existing = await KillSwitchService.get_active_state(db)
        if existing is not None:
            # Already active — return existing state without re-creating
            return 0, [], existing

        # Find active missions
        active_statuses = [
            MissionStatus.QUEUED.value,
            MissionStatus.PLANNING.value,
            MissionStatus.RESEARCHING.value,
            MissionStatus.EXECUTING.value,
            MissionStatus.TESTING.value,
            MissionStatus.VERIFYING.value,
            MissionStatus.WAITING_FOR_AGENT.value,
            MissionStatus.WAITING_FOR_HUMAN.value,
        ]
        stmt = select(Mission).where(Mission.status.in_(active_statuses))
        if scope != "all":
            try:
                scope_uuid = UUID(scope)
                stmt = stmt.where(Mission.id == scope_uuid)
            except ValueError:
                ma_stmt = select(MissionAgent.mission_id).where(MissionAgent.agent_id == scope)
                ma_result = await db.execute(ma_stmt)
                mission_ids = [row[0] for row in ma_result.all()]
                stmt = stmt.where(Mission.id.in_(mission_ids))

        result = await db.execute(stmt)
        missions = result.scalars().all()

        affected_ids = []
        for mission in missions:
            mission.status = MissionStatus.CANCELED.value
            affected_ids.append(str(mission.id))

        await db.flush()

        # Create a kill switch event with explicit system run ID
        event = await EventService.create(
            db,
            event_type=EventType.KILL_SWITCH_ACTIVATED,
            payload={"reason": reason, "activated_by": activated_by, "scope": scope},
            run_id="system:kill-switch",
        )

        # Persist the kill switch state
        # The partial unique index uq_observatory_single_active_kill_switch
        # guarantees at most one active row. Under concurrent activation, the
        # database rejects the second insert — we catch and return the winner.
        state = KillSwitchState(
            is_active=True,
            reason=reason,
            activated_by=activated_by,
            scope=scope,
            activation_event_id=event.id if event else None,
        )
        db.add(state)

        try:
            await db.flush()
        except IntegrityError:
            # Concurrent activation race: another transaction won.
            # Roll back the state insert but keep the session usable.
            await db.rollback()
            # Re-query for the winning active state.
            winning_state = await KillSwitchService.get_active_state(db)
            if winning_state is not None:
                # Another activation won — missions may or may not have been
                # canceled by the winner. Return zero to indicate idempotency.
                return 0, [], winning_state
            # Extremely rare: the winning transaction rolled back after winning.
            # Fail closed — the caller should retry.
            raise

        # Create an incident
        await IncidentService.create(
            db,
            title=f"Kill switch activated: {reason}",
            severity=IncidentSeverity.CRITICAL.value,
            description=f"Kill switch activated by {activated_by}. Scope: {scope}. "
                        f"Missions affected: {len(affected_ids)}",
        )

        await db.flush()
        return len(affected_ids), affected_ids, state

    @staticmethod
    async def clear(
        db: AsyncSession,
        cleared_by: str,
        reason: str = "",
    ) -> KillSwitchState | None:
        """Clear (deactivate) the kill switch.

        The cleared_by field provides attribution only — it is NOT authentication.
        True authorization requires the clearing principal to be derived from an
        authenticated session or token context, not from a request-body string.
        That enforcement belongs in the router/middleware layer (Gate 4+ hardening).

        Marks the active kill switch as inactive. Returns the cleared state
        or None if no active switch exists.
        """
        state = await KillSwitchService.get_active_state(db)
        if state is None:
            return None

        state.is_active = False
        state.cleared_by = cleared_by
        state.cleared_at = datetime.now(UTC)
        if reason:
            state.metadata_ = (state.metadata_ or {})
            state.metadata_["clear_reason"] = reason

        # Create a KILL_SWITCH_CLEARED event with explicit system run ID
        await EventService.create(
            db,
            event_type=EventType.KILL_SWITCH_CLEARED,
            payload={
                "cleared_by": cleared_by,
                "reason": reason,
                "original_activation_by": state.activated_by,
                "original_reason": state.reason,
            },
            run_id="system:kill-switch",
        )

        await db.flush()
        return state


# ── Data masking ──────────────────────────────────────────────────────────────


class DataMaskingService:
    """Mask sensitive fields in event payloads."""

    SENSITIVE_KEYS = {"api_key", "secret", "password", "token", "credential", "private_key"}

    @classmethod
    def mask_payload(cls, payload: dict[str, Any]) -> dict[str, Any]:
        """Return a copy of payload with sensitive keys masked."""
        masked = {}
        for key, value in payload.items():
            if isinstance(value, dict):
                masked[key] = cls.mask_payload(value)
            elif key.lower() in cls.SENSITIVE_KEYS or any(
                s in key.lower() for s in cls.SENSITIVE_KEYS
            ):
                masked[key] = "***MASKED***"
            else:
                masked[key] = value
        return masked
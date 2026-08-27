"""Mission state machine for SP-LIVE-001 offline integration."""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import hashlib
import time
import uuid


class MissionState(Enum):
    """Frozen D1 mission states."""
    RECEIVED = "RECEIVED"
    PRINCIPAL_IDENTIFIED = "PRINCIPAL_IDENTIFIED"
    MISSION_SCOPED = "MISSION_SCOPED"
    MEMORY_RESOLVED = "MISSION_RESOLVED"  # Note: D1 says MEMORY_RESOLVED, not MISSION_RESOLVED
    SPECIALISTS_DISPATCHED = "SPECIALISTS_DISPATCHED"
    RECONCILED = "RECONCILED"
    ACTION_PROPOSED = "ACTION_PROPOSED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVED = "APPROVED"
    CAPABILITY_RESOLVED = "CAPABILITY_RESOLVED"
    READY = "READY"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    EVIDENCE_RECONCILIATION = "EVIDENCE_RECONCILIATION"
    COMPLETE = "COMPLETE"
    
    # Terminal failure/interruption states
    IDENTITY_AMBIGUOUS = "IDENTITY_AMBIGUOUS"
    AUTHORITY_MISSING = "AUTHORITY_MISSING"
    APPROVAL_INVALID = "APPROVAL_INVALID"
    APPROVAL_EXPIRED = "APPROVAL_EXPIRED"
    CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    EVIDENCE_INCOMPLETE = "EVIDENCE_INCOMPLETE"
    CANCELLED = "CANCELLED"


# Frozen D1 valid transitions
VALID_TRANSITIONS = {
    MissionState.RECEIVED: [MissionState.PRINCIPAL_IDENTIFIED, MissionState.IDENTITY_AMBIGUOUS],
    MissionState.PRINCIPAL_IDENTIFIED: [MissionState.MISSION_SCOPED, MissionState.AUTHORITY_MISSING],
    MissionState.MISSION_SCOPED: [MissionState.MEMORY_RESOLVED],
    MissionState.MEMORY_RESOLVED: [MissionState.SPECIALISTS_DISPATCHED],
    MissionState.SPECIALISTS_DISPATCHED: [MissionState.RECONCILED],
    MissionState.RECONCILED: [MissionState.ACTION_PROPOSED],
    MissionState.ACTION_PROPOSED: [MissionState.APPROVAL_REQUIRED],
    MissionState.APPROVAL_REQUIRED: [MissionState.APPROVED, MissionState.APPROVAL_INVALID, MissionState.APPROVAL_EXPIRED],
    MissionState.APPROVED: [MissionState.CAPABILITY_RESOLVED, MissionState.CAPABILITY_UNAVAILABLE],
    MissionState.CAPABILITY_RESOLVED: [MissionState.READY],
    MissionState.READY: [MissionState.EXECUTING],
    MissionState.EXECUTING: [MissionState.VERIFYING, MissionState.EXECUTION_FAILED],
    MissionState.VERIFYING: [MissionState.EVIDENCE_RECONCILIATION, MissionState.VERIFICATION_FAILED],
    MissionState.EVIDENCE_RECONCILIATION: [MissionState.COMPLETE, MissionState.EVIDENCE_INCOMPLETE],
    MissionState.COMPLETE: [],
    # Terminal states have no outgoing transitions
    MissionState.IDENTITY_AMBIGUOUS: [],
    MissionState.AUTHORITY_MISSING: [],
    MissionState.APPROVAL_INVALID: [],
    MissionState.APPROVAL_EXPIRED: [],
    MissionState.CAPABILITY_UNAVAILABLE: [],
    MissionState.EXECUTION_FAILED: [],
    MissionState.VERIFICATION_FAILED: [],
    MissionState.EVIDENCE_INCOMPLETE: [],
    MissionState.CANCELLED: [],
}


@dataclass(frozen=True)
class TransitionRecord:
    """Immutable record of a state transition."""
    from_state: MissionState
    to_state: MissionState
    timestamp: float
    evidence_hash: str
    reason: str = ""


class MissionStateMachine:
    """Enforces frozen D1 state transitions with evidence."""

    def __init__(self):
        self.current_state = MissionState.RECEIVED
        self.history: List[TransitionRecord] = []

    def can_transition(self, to_state: MissionState) -> bool:
        return to_state in VALID_TRANSITIONS.get(self.current_state, [])

    def transition(self, to_state: MissionState, evidence_hash: str, reason: str = "") -> bool:
        if not self.can_transition(to_state):
            return False
        record = TransitionRecord(
            from_state=self.current_state,
            to_state=to_state,
            timestamp=time.time(),
            evidence_hash=evidence_hash,
            reason=reason
        )
        self.history.append(record)
        self.current_state = to_state
        return True

    def is_terminal(self) -> bool:
        return len(VALID_TRANSITIONS.get(self.current_state, [])) == 0

    def is_failure(self) -> bool:
        return self.current_state in (
            MissionState.IDENTITY_AMBIGUOUS,
            MissionState.AUTHORITY_MISSING,
            MissionState.APPROVAL_INVALID,
            MissionState.APPROVAL_EXPIRED,
            MissionState.CAPABILITY_UNAVAILABLE,
            MissionState.EXECUTION_FAILED,
            MissionState.VERIFICATION_FAILED,
            MissionState.EVIDENCE_INCOMPLETE,
            MissionState.CANCELLED,
        )

    def get_evidence_chain(self) -> List[Dict[str, Any]]:
        return [{"from": r.from_state.value, "to": r.to_state.value, "timestamp": r.timestamp, "evidence_hash": r.evidence_hash, "reason": r.reason} for r in self.history]


@dataclass(frozen=True)
class MissionScope:
    """Immutable mission scope from D1 contract."""
    mission_id: str
    purpose: str
    allowed_operations: List[str]
    prohibited_operations: List[str]
    consequence_ceiling: str  # E0, E1, E2, E3
    budgets: Dict[str, Any]
    memory_scope: str
    specialist_roles: List[str]
    capability_requirements: List[str]
    evidence_requirements: List[str]
    expiry: float
    cancellation_authority: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "purpose": self.purpose,
            "allowed_operations": self.allowed_operations,
            "prohibited_operations": self.prohibited_operations,
            "consequence_ceiling": self.consequence_ceiling,
            "budgets": self.budgets,
            "memory_scope": self.memory_scope,
            "specialist_roles": self.specialist_roles,
            "capability_requirements": self.capability_requirements,
            "evidence_requirements": self.evidence_requirements,
            "expiry": self.expiry,
            "cancellation_authority": self.cancellation_authority
        }


class MissionManager:
    """Creates and manages bounded missions."""

    def __init__(self, state_machine: MissionStateMachine):
        self.state_machine = state_machine
        self.mission_id = str(uuid.uuid4())
        self.scope: Optional[MissionScope] = None
        self.request_hash: Optional[str] = None

    def create_mission(self, request: str, principal_identity) -> MissionScope:
        """Create a bounded mission from a synthetic request."""
        request_content = f"{self.mission_id}|{request}|{principal_identity.principal_id}|{time.time()}"
        self.request_hash = hashlib.sha256(request_content.encode()).hexdigest()
        
        self.scope = MissionScope(
            mission_id=self.mission_id,
            purpose="Status briefing with one safe action",
            allowed_operations=["governed_memory.read", "specialist.dispatch", "model.route", "approval.request", "synthetic_side_effect.execute"],
            prohibited_operations=["external_api.call", "credential.use", "oauth.execute", "real_side_effect.execute", "microphone.activate", "speaker.activate"],
            consequence_ceiling="E0",
            budgets={"tokens": 50000, "wall_time_seconds": 120, "specialist_calls": 10, "side_effects": 1},
            memory_scope="governed_status_briefing",
            specialist_roles=["status_analyst", "authority_reviewer"],
            capability_requirements=["synthetic_side_effect"],
            evidence_requirements=["authority_decision", "principal_approval", "action_envelope", "provider_attempt", "provider_receipt", "independent_verification", "evidence_chain", "written_principal_brief", "spoken_principal_brief"],
            expiry=time.time() + 3600,
            cancellation_authority="PRINCIPAL"
        )
        
        evidence = f"mission_created|{self.mission_id}|{self.request_hash}".encode()
        evidence_hash = hashlib.sha256(evidence).hexdigest()
        self.state_machine.transition(MissionState.MISSION_SCOPED, evidence_hash, "Mission scoped from synthetic request")
        
        return self.scope

    def get_mission_id(self) -> str:
        return self.mission_id
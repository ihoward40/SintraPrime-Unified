"""Approval binding and validation for SP-LIVE-001."""

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class ApprovalState(Enum):
    """Approval lifecycle states."""
    PENDING = "PENDING"
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    INVALIDATED = "INVALIDATED"
    USED = "USED"


@dataclass(frozen=True)
class ActionEnvelope:
    """Immutable action envelope per D1 schema."""
    schema_version: str
    mission_id: str
    principal_identity: Dict[str, Any]
    action: Dict[str, Any]
    capability: str
    destination: Dict[str, Any]
    parameters: Dict[str, Any]
    consequence_class: str
    mission_authority_hash: str
    capability_certification: Dict[str, Any]
    evidence_requirements: List[str] = field(default_factory=list)
    approval: Optional[Dict[str, Any]] = None
    idempotency_key: str = ""
    action_hash: str = ""
    created_at: float = 0.0
    expires_at: float = 0.0

    def __post_init__(self):
        if not self.idempotency_key:
            object.__setattr__(self, 'idempotency_key', str(uuid.uuid4()))
        if not self.action_hash:
            content = f"{self.mission_id}|{self.action}|{self.capability}|{self.destination}|{self.parameters}"
            object.__setattr__(self, 'action_hash', hashlib.sha256(content.encode()).hexdigest())
        if not self.created_at:
            object.__setattr__(self, 'created_at', time.time())
        if not self.expires_at:
            object.__setattr__(self, 'expires_at', time.time() + 3600)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "mission_id": self.mission_id,
            "principal_identity": self.principal_identity,
            "action": self.action,
            "capability": self.capability,
            "destination": self.destination,
            "parameters": self.parameters,
            "consequence_class": self.consequence_class,
            "mission_authority_hash": self.mission_authority_hash,
            "capability_certification": self.capability_certification,
            "action_hash": self.action_hash,
            "approval": self.approval,
            "idempotency_key": self.idempotency_key,
            "evidence_requirements": self.evidence_requirements,
            "created_at": self.created_at,
            "expires_at": self.expires_at
        }


@dataclass(frozen=True)
class ApprovalRecord:
    """Immutable approval record bound to action hash."""
    approval_hash: str
    principal_id: str
    session_id: str
    action_hash: str
    approved_at: float
    expires_at: float
    nonce: str
    transcript_hash: str
    spoken_proposal_hash: str
    displayed_proposal_hash: str
    approval_phrase: str
    state: ApprovalState = ApprovalState.APPROVED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approval_hash": self.approval_hash,
            "principal_id": self.principal_id,
            "session_id": self.session_id,
            "action_hash": self.action_hash,
            "approved_at": self.approved_at,
            "expires_at": self.expires_at,
            "nonce": self.nonce,
            "transcript_hash": self.transcript_hash,
            "spoken_proposal_hash": self.spoken_proposal_hash,
            "displayed_proposal_hash": self.displayed_proposal_hash,
            "approval_phrase": self.approval_phrase,
            "state": self.state.value
        }


class ApprovalManager:
    """Manages approval binding and invalidation."""

    def __init__(self, mission_id: str):
        self.mission_id = mission_id
        self.action_envelope: Optional[ActionEnvelope] = None
        self.approval_record: Optional[ApprovalRecord] = None
        self.approval_state = ApprovalState.PENDING

    def create_action_envelope(self, principal_identity, mission_scope, safe_action: Dict[str, Any]) -> ActionEnvelope:
        """Create immutable action envelope for the one authorized side effect."""
        envelope = ActionEnvelope(
            schema_version="1.0",
            mission_id=self.mission_id,
            principal_identity=principal_identity.to_dict() if hasattr(principal_identity, 'to_dict') else principal_identity,
            action=safe_action["action"],
            capability=safe_action["capability"],
            destination=safe_action["destination"],
            parameters=safe_action.get("parameters", {}),
            consequence_class=safe_action.get("consequence_class", "E0"),
            mission_authority_hash=mission_scope.get("authority_hash", hashlib.sha256(f"mission|{self.mission_id}".encode()).hexdigest()),
            capability_certification={
                "certification_id": "SP-LIVE-001-SYNTHETIC-001",
                "exact_head": "ab222ee61c87c2d06e98ec3f843189595f9b0fc0",
                "contract_hash": hashlib.sha256(f"sp-live-001-d1|contract".encode()).hexdigest(),
                "valid_at_execution": True
            },
            evidence_requirements=[
                "authority_decision", "principal_approval", "action_envelope", "provider_attempt",
                "provider_receipt", "independent_verification", "evidence_chain",
                "written_principal_brief", "spoken_principal_brief"
            ],
            created_at=time.time(),
            expires_at=time.time() + 3600
        )
        self.action_envelope = envelope
        self.approval_state = ApprovalState.REQUESTED
        return envelope

    def request_approval(self, envelope: ActionEnvelope, voice_input) -> Dict[str, Any]:
        """Generate approval request with hashes for Principal."""
        action_hash = envelope.action_hash
        # Spoken proposal hash (simulated)
        spoken_proposal = f"Action: {json.dumps(envelope.action, sort_keys=True)}. Capability: {envelope.capability}. Destination: {json.dumps(envelope.destination, sort_keys=True)}."
        spoken_proposal_hash = hashlib.sha256(spoken_proposal.encode()).hexdigest()
        # Displayed proposal hash (simulated)
        displayed_proposal = json.dumps(envelope.to_dict(), sort_keys=True, separators=(",", ":"))
        displayed_proposal_hash = hashlib.sha256(displayed_proposal.encode()).hexdigest()
        transcript = f"Proposed action: {envelope.action}. Do you approve?"
        transcript_hash = hashlib.sha256(transcript.encode()).hexdigest()

        return {
            "action_hash": action_hash,
            "spoken_proposal": spoken_proposal,
            "spoken_proposal_hash": spoken_proposal_hash,
            "displayed_proposal_hash": displayed_proposal_hash,
            "transcript": transcript,
            "transcript_hash": transcript_hash,
            "consequence_class": envelope.consequence_class,
            "capability": envelope.capability,
            "destination": envelope.destination,
            "parameters": envelope.parameters,
            "idempotency_key": envelope.idempotency_key,
            "expires_at": envelope.expires_at
        }

    def bind_approval(self, envelope: ActionEnvelope, approval_fixture: Dict[str, Any], proposal_hashes: Dict[str, str]) -> ApprovalRecord:
        """Bind explicit approval to exact action hash."""
        if self.approval_state != ApprovalState.REQUESTED:
            raise RuntimeError("Approval not in requested state")

        action_hash = envelope.action_hash
        principal_id = approval_fixture.get("principal_id", "principal-001")
        session_id = approval_fixture.get("session_id", "session-001")
        approval_phrase = approval_fixture.get("approval_phrase", "Yes, I approve.")
        approved_at = approval_fixture.get("timestamp", time.time())
        expires_at = envelope.expires_at
        nonce = str(uuid.uuid4())

        # Verify approval phrase indicates explicit consent
        valid_phrases = ["yes", "approve", "approved", "i approve", "yes i approve"]
        if not any(phrase in approval_phrase.lower() for phrase in valid_phrases):
            self.approval_state = ApprovalState.REJECTED
            raise ValueError("Approval phrase does not indicate explicit consent")

        approval_hash = hashlib.sha256(f"{action_hash}|{principal_id}|{session_id}|{approved_at}|{nonce}".encode()).hexdigest()

        record = ApprovalRecord(
            approval_hash=approval_hash,
            principal_id=principal_id,
            session_id=session_id,
            action_hash=action_hash,
            approved_at=approved_at,
            expires_at=expires_at,
            nonce=nonce,
            transcript_hash=proposal_hashes.get("transcript_hash", ""),
            spoken_proposal_hash=proposal_hashes.get("spoken_proposal_hash", ""),
            displayed_proposal_hash=proposal_hashes.get("displayed_proposal_hash", ""),
            approval_phrase=approval_phrase,
            state=ApprovalState.APPROVED
        )

        # Bind approval to envelope
        envelope_dict = envelope.to_dict()
        envelope_dict["approval"] = record.to_dict()
        self.action_envelope = ActionEnvelope(**envelope_dict)
        self.approval_record = record
        self.approval_state = ApprovalState.APPROVED

        return record

    def validate_approval(self, envelope: ActionEnvelope, current_time: float = None) -> bool:
        """Validate that approval is current and matches action exactly."""
        if current_time is None:
            current_time = time.time()

        if self.approval_state != ApprovalState.APPROVED:
            return False

        if self.approval_record is None:
            return False

        if envelope.action_hash != self.approval_record.action_hash:
            self.approval_state = ApprovalState.INVALIDATED
            return False

        if current_time > self.approval_record.expires_at:
            self.approval_state = ApprovalState.EXPIRED
            return False

        # Check session binding
        if self.action_envelope.principal_identity.get("session_id") != self.approval_record.session_id:
            self.approval_state = ApprovalState.INVALIDATED
            return False

        return True

    def mark_used(self):
        self.approval_state = ApprovalState.USED
        if self.approval_record:
            # Can't modify frozen dataclass, but state is tracked
            pass

    def get_envelope(self) -> Optional[ActionEnvelope]:
        return self.action_envelope

    def get_approval_record(self) -> Optional[ApprovalRecord]:
        return self.approval_record
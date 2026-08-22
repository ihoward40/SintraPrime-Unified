"""Principal session binding and voice approval protocol for SP-LIVE-001 I2."""

import time
import uuid
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class SessionState(Enum):
    """Principal session states."""
    INACTIVE = "INACTIVE"
    ACTIVE = "ACTIVE"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    AMBIGUOUS = "AMBIGUOUS"
    EXPIRED = "EXPIRED"


class ApprovalPhraseType(Enum):
    """Types of approval/rejection phrases."""
    EXPLICIT_APPROVAL = "EXPLICIT_APPROVAL"
    EXPLICIT_REJECTION = "EXPLICIT_REJECTION"
    AMBIGUOUS = "AMBIGUOUS"
    CORRECTION = "CORRECTION"
    CANCELLATION = "CANCELLATION"
    CLARIFICATION = "CLARIFICATION"


@dataclass(frozen=True)
class VoiceTranscript:
    """Voice transcript with metadata."""
    transcript_id: str
    text: str
    confidence: float
    timestamp: float
    is_final: bool
    session_id: str
    segment_id: str
    alternatives: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class SpokenApproval:
    """Spoken approval record."""
    approval_id: str
    transcript: VoiceTranscript
    phrase_type: ApprovalPhraseType
    action_hash: str
    mission_id: str
    principal_session_id: str
    confidence: float
    timestamp: float
    hash_binding: str = ""

    def __post_init__(self):
        if not self.hash_binding:
            content = f"{self.action_hash}|{self.transcript.text}|{self.timestamp}|{self.mission_id}"
            object.__setattr__(self, 'hash_binding', hashlib.sha256(content.encode()).hexdigest())


@dataclass
class PrincipalSession:
    """Principal interactive session."""
    session_id: str
    principal_id: str
    state: SessionState = SessionState.INACTIVE
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    transcripts: List[VoiceTranscript] = field(default_factory=list)
    pending_approval: Optional[SpokenApproval] = None
    approval_history: List[SpokenApproval] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


class PrincipalSessionManager:
    """Manages Principal voice sessions."""

    def __init__(self, session_timeout: float = 3600.0):
        self.sessions: Dict[str, PrincipalSession] = {}
        self.session_timeout = session_timeout
        self.current_session_id: Optional[str] = None

    def create_session(self, principal_id: str = "principal-001") -> PrincipalSession:
        """Create a new Principal session."""
        session_id = str(uuid.uuid4())
        session = PrincipalSession(
            session_id=session_id,
            principal_id=principal_id,
            state=SessionState.ACTIVE
        )
        self.sessions[session_id] = session
        self.current_session_id = session_id
        return session

    def get_session(self, session_id: str = None) -> Optional[PrincipalSession]:
        """Get session by ID or current session."""
        if session_id:
            return self.sessions.get(session_id)
        if self.current_session_id:
            return self.sessions.get(self.current_session_id)
        return None

    def activate_session(self, session_id: str) -> bool:
        """Activate a session."""
        if session_id in self.sessions:
            self.current_session_id = session_id
            session = self.sessions[session_id]
            session.state = SessionState.ACTIVE
            session.last_activity = time.time()
            return True
        return False

    def add_transcript(self, transcript: VoiceTranscript) -> PrincipalSession:
        """Add transcript to current session."""
        session = self.get_session(transcript.session_id)
        if session:
            session.transcripts.append(transcript)
            session.last_activity = time.time()
        return session

    def request_approval(self, mission_id: str, action_hash: str, action_description: str) -> SpokenApproval:
        """Request approval for an action."""
        session = self.get_session()
        if not session:
            raise RuntimeError("No active Principal session")

        session.state = SessionState.WAITING_APPROVAL

        # Create a pending approval record (will be filled when Principal speaks)
        approval = SpokenApproval(
            approval_id=str(uuid.uuid4()),
            transcript=VoiceTranscript(
                transcript_id=str(uuid.uuid4()),
                text="",
                confidence=0.0,
                timestamp=time.time(),
                is_final=False,
                session_id=session.session_id,
                segment_id=""
            ),
            phrase_type=ApprovalPhraseType.AMBIGUOUS,
            action_hash=action_hash,
            mission_id=mission_id,
            principal_session_id=session.session_id,
            confidence=0.0,
            timestamp=time.time()
        )

        session.pending_approval = approval
        return approval

    def process_approval_response(self, transcript: VoiceTranscript) -> Optional[SpokenApproval]:
        """Process Principal's spoken response to approval request."""
        session = self.get_session(transcript.session_id)
        if not session or not session.pending_approval:
            return None

        phrase_type = self._classify_approval_phrase(transcript.text)

        approval = SpokenApproval(
            approval_id=session.pending_approval.approval_id,
            transcript=transcript,
            phrase_type=phrase_type,
            action_hash=session.pending_approval.action_hash,
            mission_id=session.pending_approval.mission_id,
            principal_session_id=session.session_id,
            confidence=transcript.confidence,
            timestamp=transcript.timestamp
        )

        session.approval_history.append(approval)
        session.pending_approval = None

        if phrase_type == ApprovalPhraseType.EXPLICIT_APPROVAL:
            session.state = SessionState.APPROVED
        elif phrase_type == ApprovalPhraseType.EXPLICIT_REJECTION:
            session.state = SessionState.REJECTED
        elif phrase_type == ApprovalPhraseType.CANCELLATION:
            session.state = SessionState.REJECTED
        else:
            session.state = SessionState.AMBIGUOUS

        return approval

    def _classify_approval_phrase(self, text: str) -> ApprovalPhraseType:
        """Classify spoken phrase as approval, rejection, or ambiguous."""
        text_lower = text.lower().strip()

        # Explicit approval phrases
        approval_phrases = [
            "yes", "yeah", "yep", "sure", "okay", "ok", "proceed", "go ahead",
            "do it", "execute", "confirm", "approved", "approve", "yes please",
            "that's correct", "correct", "right", "affirmative"
        ]

        # Explicit rejection phrases
        rejection_phrases = [
            "no", "nope", "cancel", "stop", "don't", "do not", "reject",
            "disapprove", "abort", "never mind", "wait", "hold on"
        ]

        # Cancellation phrases
        cancel_phrases = [
            "cancel", "stop", "abort", "never mind", "forget it"
        ]

        # Correction phrases
        correction_phrases = [
            "actually", "wait", "no wait", "correction", "change", "different"
        ]

        # Check for cancellation first
        for phrase in cancel_phrases:
            if phrase in text_lower:
                return ApprovalPhraseType.CANCELLATION

        # Check for correction
        for phrase in correction_phrases:
            if phrase in text_lower:
                return ApprovalPhraseType.CORRECTION

        # Check for approval
        for phrase in approval_phrases:
            if phrase in text_lower or text_lower == phrase:
                return ApprovalPhraseType.EXPLICIT_APPROVAL

        # Check for rejection
        for phrase in rejection_phrases:
            if phrase in text_lower or text_lower == phrase:
                return ApprovalPhraseType.EXPLICIT_REJECTION

        return ApprovalPhraseType.AMBIGUOUS

    def is_approval_valid(self, approval: SpokenApproval) -> bool:
        """Check if spoken approval is valid."""
        return (
            approval.phrase_type == ApprovalPhraseType.EXPLICIT_APPROVAL and
            approval.confidence >= 0.7 and
            approval.hash_binding
        )

    def get_approval_binding(self, approval: SpokenApproval) -> Dict[str, Any]:
        """Get approval binding evidence."""
        return {
            "approval_id": approval.approval_id,
            "action_hash": approval.action_hash,
            "transcript": approval.transcript.text,
            "confidence": approval.confidence,
            "phrase_type": approval.phrase_type.value,
            "hash_binding": approval.hash_binding,
            "timestamp": approval.timestamp,
            "session_id": approval.principal_session_id,
            "mission_id": approval.mission_id
        }

    def cleanup_expired_sessions(self):
        """Remove expired sessions."""
        now = time.time()
        expired = [
            sid for sid, s in self.sessions.items()
            if now - s.last_activity > self.session_timeout
        ]
        for sid in expired:
            del self.sessions[sid]
            if self.current_session_id == sid:
                self.current_session_id = None


def create_session_manager() -> PrincipalSessionManager:
    """Factory function to create session manager."""
    return PrincipalSessionManager()
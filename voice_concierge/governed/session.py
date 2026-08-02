"""Voice session state machine for SP-VOICE-001 (directive §5).

    IDLE
      -> LISTENING
      -> TRANSCRIBING
      -> CLASSIFYING
      -> PLANNING
      -> AWAITING_CONFIRMATION (when required)
      -> EXECUTING
      -> COMPLETED | REFUSED | CANCELLED | FAILED

Transitions are explicit and validated; illegal transitions raise. Interruption
commands (stop / cancel / pause / resume / show plan) are handled deterministically
and always preserve the audit trail. Cancellation propagates to child tasks that
are safe to cancel and marks non-cancellable operations clearly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class SessionState(StrEnum):
    IDLE = "idle"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    CLASSIFYING = "classifying"
    PLANNING = "planning"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    EXECUTING = "executing"
    COMPLETED = "completed"
    REFUSED = "refused"
    CANCELLED = "cancelled"
    FAILED = "failed"


TERMINAL_STATES = frozenset(
    {SessionState.COMPLETED, SessionState.REFUSED, SessionState.CANCELLED, SessionState.FAILED}
)

# Allowed forward transitions. Interruptions (cancel/refuse/fail) are handled
# separately and may fire from any non-terminal state.
_ALLOWED: dict[SessionState, frozenset[SessionState]] = {
    SessionState.IDLE: frozenset({SessionState.LISTENING}),
    SessionState.LISTENING: frozenset({SessionState.TRANSCRIBING, SessionState.IDLE}),
    SessionState.TRANSCRIBING: frozenset({SessionState.CLASSIFYING}),
    SessionState.CLASSIFYING: frozenset({SessionState.PLANNING, SessionState.REFUSED}),
    SessionState.PLANNING: frozenset(
        {SessionState.AWAITING_CONFIRMATION, SessionState.EXECUTING, SessionState.REFUSED}
    ),
    SessionState.AWAITING_CONFIRMATION: frozenset({SessionState.EXECUTING, SessionState.REFUSED}),
    SessionState.EXECUTING: frozenset({SessionState.COMPLETED, SessionState.FAILED}),
}


class InvalidTransitionError(Exception):
    """Raised when an illegal state transition is attempted."""


@dataclass
class ChildTask:
    """A child task spawned by a voice-originated request."""

    task_id: str
    cancellable: bool = True
    cancelled: bool = False
    marked_noncancellable: bool = False


@dataclass
class TransitionRecord:
    """Immutable-ish audit record of one transition (kept for the trail)."""

    from_state: SessionState
    to_state: SessionState
    reason: str
    at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class VoiceSession:
    """A governed voice session tracking state and child tasks.

    The session never executes business actions; it only models lifecycle so the
    orchestrator (Increment Two) can drive it. The audit trail is append-only.
    """

    session_id: str
    principal_id: str
    state: SessionState = SessionState.IDLE
    children: list[ChildTask] = field(default_factory=list)
    history: list[TransitionRecord] = field(default_factory=list)
    paused_from: SessionState | None = None

    def _record(self, to_state: SessionState, reason: str) -> None:
        self.history.append(TransitionRecord(self.state, to_state, reason))
        self.state = to_state

    def transition(self, to_state: SessionState, reason: str = "") -> None:
        """Perform a validated forward transition."""
        if self.state in TERMINAL_STATES:
            raise InvalidTransitionError(f"session is terminal ({self.state}); cannot transition")
        allowed = _ALLOWED.get(self.state, frozenset())
        if to_state not in allowed:
            raise InvalidTransitionError(f"illegal transition {self.state} -> {to_state}")
        self._record(to_state, reason)

    # ── Interruption semantics (directive §5) ────────────────────────────────

    def add_child(self, task: ChildTask) -> None:
        self.children.append(task)

    def cancel(self, reason: str = "cancelled by principal") -> list[ChildTask]:
        """Cancel the session; propagate to safe-to-cancel children.

        Non-cancellable operations are flagged, not force-killed. Returns the
        list of children that could not be cancelled so callers can surface them.
        """
        if self.state in TERMINAL_STATES:
            raise InvalidTransitionError(f"session already terminal ({self.state})")
        non_cancellable: list[ChildTask] = []
        for child in self.children:
            if child.cancellable:
                child.cancelled = True
            else:
                child.marked_noncancellable = True
                non_cancellable.append(child)
        self._record(SessionState.CANCELLED, reason)
        return non_cancellable

    def refuse(self, reason: str) -> None:
        if self.state in TERMINAL_STATES:
            raise InvalidTransitionError(f"session already terminal ({self.state})")
        self._record(SessionState.REFUSED, reason)

    def fail(self, reason: str) -> None:
        if self.state in TERMINAL_STATES:
            raise InvalidTransitionError(f"session already terminal ({self.state})")
        self._record(SessionState.FAILED, reason)

    def pause(self, reason: str = "paused by principal") -> None:
        """Pause an active session, remembering where to resume."""
        if self.state in TERMINAL_STATES:
            raise InvalidTransitionError(f"session terminal ({self.state}); cannot pause")
        if self.paused_from is not None:
            return  # already paused; idempotent
        self.paused_from = self.state
        self.history.append(TransitionRecord(self.state, self.state, f"paused: {reason}"))

    def resume(self, reason: str = "resumed by principal") -> None:
        """Resume a paused session back to the state it was paused from."""
        if self.paused_from is None:
            return  # not paused; idempotent
        resumed_from = self.paused_from
        self.paused_from = None
        self.history.append(TransitionRecord(self.state, resumed_from, f"resumed: {reason}"))

    @property
    def is_paused(self) -> bool:
        return self.paused_from is not None

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES

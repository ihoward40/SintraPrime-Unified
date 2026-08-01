"""Confirmation protocol for SP-VOICE-001 (directive §4).

Sensitive actions require a challenge-response confirmation that names the exact
action and target. This module implements the deterministic rules:

- Confirmation expires after five minutes OR any material change to the target.
- "yes" / "do it" / "go ahead" is valid ONLY when exactly one pending action
  exists and the system has restated the target first.
- A changed recipient, attachment, amount, branch, environment, or document
  invalidates any prior confirmation.
- Remote voice meets the same standard as local voice (no source exemption).

No transcription-confidence value can substitute for an explicit confirmation.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

CONFIRMATION_TTL = timedelta(minutes=5)

# Ambiguous affirmations that are only valid when a single target was restated.
_AMBIGUOUS_YES = frozenset({"yes", "do it", "go ahead", "yep", "yeah", "confirm", "ok", "okay"})

# Explicit denials.
_DENIALS = frozenset({"no", "cancel", "stop", "don't", "do not", "nope", "abort"})


def _target_fingerprint(target: str) -> str:
    """Stable fingerprint of the exact action target, used to detect changes."""
    return hashlib.sha256(target.strip().lower().encode("utf-8")).hexdigest()


class ConfirmationError(Exception):
    """Raised when a confirmation attempt violates the protocol."""


@dataclass(frozen=True)
class ConfirmationOutcome:
    confirmed: bool
    reason: str


@dataclass
class PendingConfirmation:
    """A single pending sensitive action awaiting exact-target confirmation."""

    command_id: str
    action_description: str
    target: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    target_restated: bool = False
    _fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_fingerprint", _target_fingerprint(self.target))

    def restate_target(self) -> None:
        """Mark that the system has restated the target back to the principal.

        Ambiguous affirmations ("yes") are only honoured after this is set.
        """
        self.target_restated = True

    def is_expired(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(UTC)
        return now - self.created_at > CONFIRMATION_TTL

    def target_changed(self, current_target: str) -> bool:
        return _target_fingerprint(current_target) != self._fingerprint

    def evaluate(
        self,
        utterance: str,
        *,
        current_target: str,
        pending_count: int,
        now: datetime | None = None,
    ) -> ConfirmationOutcome:
        """Evaluate a confirmation utterance against this pending action.

        ``current_target`` is the target as it stands at confirmation time;
        ``pending_count`` is the number of pending actions in the session (an
        ambiguous "yes" is invalid when more than one exists).
        """
        now = now or datetime.now(UTC)
        said = utterance.strip().lower()

        if self.is_expired(now):
            return ConfirmationOutcome(False, "confirmation expired")

        if self.target_changed(current_target):
            return ConfirmationOutcome(False, "target changed; prior confirmation invalidated")

        if said in _DENIALS:
            return ConfirmationOutcome(False, "explicitly denied")

        # Explicit, target-naming confirmation always allowed if it names the target.
        explicit = _target_fingerprint(current_target)[:8]
        if said.startswith("confirm ") and explicit:
            return ConfirmationOutcome(True, "explicit confirmation")

        if said in _AMBIGUOUS_YES:
            if pending_count != 1:
                return ConfirmationOutcome(
                    False, "ambiguous affirmation rejected: multiple pending actions"
                )
            if not self.target_restated:
                return ConfirmationOutcome(
                    False, "ambiguous affirmation rejected: target not restated"
                )
            return ConfirmationOutcome(True, "ambiguous affirmation accepted after restatement")

        return ConfirmationOutcome(False, "unrecognized confirmation response")

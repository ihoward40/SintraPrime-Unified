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


def target_fingerprint(target: str) -> str:
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
    target_restated_at: datetime | None = None
    target_restated_fingerprint: str | None = None
    target_restated_command_id: str | None = None
    _fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_fingerprint", target_fingerprint(self.target))

    def restate_target(self, *, restated_at: datetime | None = None) -> None:
        """Persist evidence that this command's target was restated.

        Ambiguous affirmations ("yes") are only honoured when this evidence is
        current, target-matching, and tied to this command.
        """
        self.target_restated = True
        self.target_restated_at = restated_at or datetime.now(UTC)
        self.target_restated_fingerprint = self._fingerprint
        self.target_restated_command_id = self.command_id

    def apply_restated_evidence(
        self,
        *,
        restated_at: datetime | None,
        target_fingerprint: str | None,
        command_id: str,
    ) -> None:
        self.target_restated = restated_at is not None and target_fingerprint is not None
        self.target_restated_at = restated_at
        self.target_restated_fingerprint = target_fingerprint
        self.target_restated_command_id = command_id

    def has_current_restated_evidence(self, *, current_target: str, now: datetime) -> bool:
        if not self.target_restated:
            return False
        if self.target_restated_command_id != self.command_id:
            return False
        if self.target_restated_at is None or self.target_restated_at < self.created_at:
            return False
        if now - self.target_restated_at > CONFIRMATION_TTL:
            return False
        return self.target_restated_fingerprint == target_fingerprint(current_target)

    def is_expired(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(UTC)
        return now - self.created_at > CONFIRMATION_TTL

    def target_changed(self, current_target: str) -> bool:
        return target_fingerprint(current_target) != self._fingerprint

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

        # Explicit confirmation is only valid if the named word actually
        # references the pending action or its target — a bare "confirm "
        # prefix with unrelated content must NOT be treated as confirmation.
        if said.startswith("confirm "):
            named = said[len("confirm ") :].strip()
            action_words = set(self.action_description.strip().lower().split())
            target_words = set(
                self.target.strip().lower().replace("@", " ").replace(".", " ").split()
            )
            if named and (named in action_words or named in target_words):
                return ConfirmationOutcome(True, "explicit confirmation")
            return ConfirmationOutcome(
                False, "explicit confirmation rejected: action or target not named"
            )

        if said in _AMBIGUOUS_YES:
            if pending_count != 1:
                return ConfirmationOutcome(
                    False, "ambiguous affirmation rejected: multiple pending actions"
                )
            if not self.has_current_restated_evidence(current_target=current_target, now=now):
                return ConfirmationOutcome(
                    False, "ambiguous affirmation rejected: target not restated"
                )
            return ConfirmationOutcome(True, "ambiguous affirmation accepted after restatement")

        return ConfirmationOutcome(False, "unrecognized confirmation response")

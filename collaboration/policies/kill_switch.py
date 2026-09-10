"""KillSwitch — tenant-level emergency control (§XVI, §LXXII)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class KillSwitchState:
    active: bool = False
    activated_by: str = ""
    activated_at: str = ""
    reason: str = ""
    channel_ids: list[str] = field(default_factory=list)  # empty = all channels


class KillSwitch:
    """COLLABORATION_KILL_SWITCH: stops agent activation, keeps humans online.

    Only authorized Principal/governance operators may activate/deactivate.
    """

    def __init__(self):
        self._state = KillSwitchState()

    @property
    def active(self) -> bool:
        return self._state.active

    def activate(
        self, *, operator: str, reason: str = "", channel_ids: list[str] | None = None
    ) -> None:
        now = datetime.now(UTC).isoformat()
        self._state = KillSwitchState(
            active=True,
            activated_by=operator,
            activated_at=now,
            reason=reason,
            channel_ids=list(channel_ids or []),
        )

    def deactivate(self, *, operator: str) -> None:
        # operator is recorded by callers for audit; kept for API symmetry
        del operator
        if not self._state.active:
            return
        self._state = KillSwitchState()

    def is_blocked(self, *, tenant_id: str | None = None, channel_id: str | None = None) -> bool:
        """New agent activations blocked. Human messages unaffected."""
        del tenant_id  # tenant scoping is caller-side in CF-1
        if not self._state.active:
            return False
        if self._state.channel_ids:
            if channel_id is None or channel_id not in self._state.channel_ids:
                return False
        return True

    def snapshot(self) -> dict:
        return {
            "active": self._state.active,
            "activated_by": self._state.activated_by,
            "activated_at": self._state.activated_at,
            "reason": self._state.reason,
            "channel_ids": list(self._state.channel_ids),
        }

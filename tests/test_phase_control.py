"""Phase control regression tests for SP-LIVE-001.

These tests ensure that unauthorized phase advancement is blocked.
"""

import pytest
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Optional, Set


class ProgramPhase(Enum):
    """SP-LIVE-001 program phases."""
    C1 = "C1"
    I1 = "I1"
    I2 = "I2"
    M1 = "M1"
    M2 = "M2"
    M3 = "M3"
    M4 = "M4"
    M5 = "M5"


@dataclass(frozen=True)
class PhaseAuthorization:
    """Authorization for a program phase."""
    phase: ProgramPhase
    authorized: bool
    baseline_commit: str
    authorization_token: str = ""
    granted_at: float = 0.0


class PhaseController:
    """Controls phase transitions and enforces authorization."""

    def __init__(self):
        self.current_phase: ProgramPhase = ProgramPhase.C1
        self.authorizations: Dict[ProgramPhase, PhaseAuthorization] = {}
        self.proposed_next_phase: Optional[ProgramPhase] = None
        self._phase_order = [
            ProgramPhase.C1,
            ProgramPhase.I1,
            ProgramPhase.I2,
            ProgramPhase.M1,
            ProgramPhase.M2,
            ProgramPhase.M3,
            ProgramPhase.M4,
            ProgramPhase.M5,
        ]

    def authorize_phase(self, phase: ProgramPhase, baseline: str, token: str) -> bool:
        """Grant authorization for a phase."""
        if phase in self.authorizations and self.authorizations[phase].authorized:
            return False  # Already authorized

        self.authorizations[phase] = PhaseAuthorization(
            phase=phase,
            authorized=True,
            baseline_commit=baseline,
            authorization_token=token,
        )
        return True

    def propose_next_phase(self, phase: ProgramPhase) -> bool:
        """Propose a next phase (does NOT grant authority)."""
        # Can only propose the immediate next phase in sequence
        current_idx = self._phase_order.index(self.current_phase)
        if current_idx + 1 < len(self._phase_order):
            expected_next = self._phase_order[current_idx + 1]
            if phase == expected_next:
                self.proposed_next_phase = phase
                return True
        return False

    def can_execute_phase(self, phase: ProgramPhase) -> bool:
        """Check if a phase can be executed (requires explicit authorization)."""
        auth = self.authorizations.get(phase)
        return auth is not None and auth.authorized

    def advance_phase(self, phase: ProgramPhase) -> bool:
        """Advance to a phase (requires authorization)."""
        if not self.can_execute_phase(phase):
            return False

        # Must be the proposed next phase
        if self.proposed_next_phase != phase:
            return False

        self.current_phase = phase
        self.proposed_next_phase = None
        return True

    def get_status(self) -> Dict:
        """Get current phase status."""
        return {
            "current_phase": self.current_phase.value,
            "proposed_next_phase": self.proposed_next_phase.value if self.proposed_next_phase else None,
            "authorized_phases": [p.value for p, a in self.authorizations.items() if a.authorized],
            "can_execute_proposed": self.can_execute_phase(self.proposed_next_phase) if self.proposed_next_phase else False,
        }


# =============================================================================
# REGRESSION TESTS
# =============================================================================

class TestPhaseControl:
    """Tests for phase control enforcement."""

    def setup_method(self):
        """Set up fresh phase controller for each test."""
        self.controller = PhaseController()
        # Simulate C1 authorized
        self.controller.authorize_phase(ProgramPhase.C1, "4c86aff2...", "C1_TOKEN")
        self.controller.current_phase = ProgramPhase.C1

    def test_initial_state_c1_only(self):
        """Initial state: only C1 authorized."""
        assert self.controller.current_phase == ProgramPhase.C1
        assert self.controller.can_execute_phase(ProgramPhase.C1)
        assert not self.controller.can_execute_phase(ProgramPhase.I1)
        assert not self.controller.can_execute_phase(ProgramPhase.I2)
        assert not self.controller.can_execute_phase(ProgramPhase.M1)

    def test_propose_next_phase_i1_after_c1(self):
        """Can propose I1 after C1."""
        assert self.controller.propose_next_phase(ProgramPhase.I1)
        assert self.controller.proposed_next_phase == ProgramPhase.I1
        # Proposing does NOT grant authority
        assert not self.controller.can_execute_phase(ProgramPhase.I1)

    def test_cannot_propose_skip_phase(self):
        """Cannot skip phases in proposal."""
        assert not self.controller.propose_next_phase(ProgramPhase.I2)  # Skip I1
        assert not self.controller.propose_next_phase(ProgramPhase.M1)  # Skip I1, I2
        assert self.controller.proposed_next_phase is None

    def test_proposal_does_not_create_authority(self):
        """Proposal never creates execution authority."""
        self.controller.propose_next_phase(ProgramPhase.I1)
        assert self.controller.proposed_next_phase == ProgramPhase.I1
        assert not self.controller.can_execute_phase(ProgramPhase.I1)
        assert self.controller.get_status()["can_execute_proposed"] is False

    def test_unauthorized_next_phase_cannot_start(self):
        """Unauthorized phase cannot execute even if proposed."""
        self.controller.propose_next_phase(ProgramPhase.I1)
        assert self.controller.proposed_next_phase == ProgramPhase.I1
        # Try to execute without authorization
        assert not self.controller.advance_phase(ProgramPhase.I1)
        assert self.controller.current_phase == ProgramPhase.C1  # Still at C1

    def test_authorized_phase_can_execute(self):
        """Authorized phase can execute after proposal."""
        self.controller.authorize_phase(ProgramPhase.I1, "e4d260da...", "I1_TOKEN")
        self.controller.propose_next_phase(ProgramPhase.I1)
        assert self.controller.advance_phase(ProgramPhase.I1)
        assert self.controller.current_phase == ProgramPhase.I1

    def test_memory_cannot_advance_phase(self):
        """Historical/proposed phase info cannot create authority."""
        # Simulate "memory" of past phase proposal
        self.controller.propose_next_phase(ProgramPhase.I1)
        proposed = self.controller.proposed_next_phase

        # Clear and recreate controller (simulating new session with memory)
        new_controller = PhaseController()
        new_controller.current_phase = ProgramPhase.C1
        new_controller.proposed_next_phase = proposed  # "Remembered" proposal

        # Memory of proposal does NOT grant authority
        assert not new_controller.can_execute_phase(ProgramPhase.I1)
        assert not new_controller.advance_phase(ProgramPhase.I1)
        assert new_controller.current_phase == ProgramPhase.C1

    def test_past_principal_intent_not_current_authority(self):
        """Past intent recorded in memory does not equal current authorization."""
        # Record that Principal previously said "next is M1"
        self.controller.propose_next_phase(ProgramPhase.I1)
        self.controller.authorize_phase(ProgramPhase.I1, "e4d260da...", "I1_TOKEN")
        self.controller.advance_phase(ProgramPhase.I1)

        # Now at I1, propose M1
        self.controller.propose_next_phase(ProgramPhase.M1)

        # But M1 not authorized
        assert not self.controller.can_execute_phase(ProgramPhase.M1)

        # Even if we "remember" Principal wanted M1
        self.controller.proposed_next_phase = ProgramPhase.M1
        assert not self.controller.advance_phase(ProgramPhase.M1)

    def test_i2_must_be_authorized_before_m1(self):
        """I2 must be authorized and completed before M1 can be proposed."""
        # C1 -> I1 authorized
        self.controller.authorize_phase(ProgramPhase.I1, "e4d260da...", "I1_TOKEN")
        self.controller.propose_next_phase(ProgramPhase.I1)
        self.controller.advance_phase(ProgramPhase.I1)

        # At I1, can propose I2
        assert self.controller.propose_next_phase(ProgramPhase.I2)
        assert self.controller.proposed_next_phase == ProgramPhase.I2

        # Cannot propose M1 from I1
        assert not self.controller.propose_next_phase(ProgramPhase.M1)

    def test_full_sequence_c1_i1_i2_m1(self):
        """Full authorized sequence works."""
        # C1 already authorized, at C1
        # Authorize I1
        self.controller.authorize_phase(ProgramPhase.I1, "e4d260da...", "I1_TOKEN")
        self.controller.propose_next_phase(ProgramPhase.I1)
        assert self.controller.advance_phase(ProgramPhase.I1)
        assert self.controller.current_phase == ProgramPhase.I1

        # Authorize I2
        self.controller.authorize_phase(ProgramPhase.I2, "86f192a4...", "I2_TOKEN")
        self.controller.propose_next_phase(ProgramPhase.I2)
        assert self.controller.advance_phase(ProgramPhase.I2)
        assert self.controller.current_phase == ProgramPhase.I2

        # Now can propose M1
        assert self.controller.propose_next_phase(ProgramPhase.M1)
        assert self.controller.proposed_next_phase == ProgramPhase.M1

        # But M1 not executable without authorization
        assert not self.controller.can_execute_phase(ProgramPhase.M1)
        assert not self.controller.advance_phase(ProgramPhase.M1)

        # Authorize M1
        self.controller.authorize_phase(ProgramPhase.M1, "M1_BASELINE", "M1_TOKEN")
        assert self.controller.can_execute_phase(ProgramPhase.M1)
        assert self.controller.advance_phase(ProgramPhase.M1)
        assert self.controller.current_phase == ProgramPhase.M1

    def test_cannot_advance_to_unproposed_phase(self):
        """Cannot advance to a phase that wasn't proposed."""
        self.controller.authorize_phase(ProgramPhase.I1, "e4d260da...", "I1_TOKEN")
        # Don't propose, just try to advance
        assert not self.controller.advance_phase(ProgramPhase.I1)
        assert self.controller.current_phase == ProgramPhase.C1

    def test_status_reporting(self):
        """Status correctly reports state."""
        status = self.controller.get_status()
        assert status["current_phase"] == "C1"
        assert status["proposed_next_phase"] is None
        assert "C1" in status["authorized_phases"]
        assert "I1" not in status["authorized_phases"]

        self.controller.propose_next_phase(ProgramPhase.I1)
        status = self.controller.get_status()
        assert status["proposed_next_phase"] == "I1"
        assert status["can_execute_proposed"] is False

        self.controller.authorize_phase(ProgramPhase.I1, "e4d260da...", "I1_TOKEN")
        status = self.controller.get_status()
        assert status["can_execute_proposed"] is True


class TestPhaseControlIntegration:
    """Integration tests for phase control in the program context."""

    def test_i2_authorization_blocks_m1(self):
        """I2 authorization does not implicitly authorize M1."""
        controller = PhaseController()
        controller.authorize_phase(ProgramPhase.C1, "4c86aff2...", "C1_TOKEN")
        controller.current_phase = ProgramPhase.C1
        controller.authorize_phase(ProgramPhase.I1, "e4d260da...", "I1_TOKEN")
        controller.propose_next_phase(ProgramPhase.I1)
        controller.advance_phase(ProgramPhase.I1)
        controller.authorize_phase(ProgramPhase.I2, "86f192a4...", "I2_TOKEN")
        controller.propose_next_phase(ProgramPhase.I2)
        controller.advance_phase(ProgramPhase.I2)

        # Now at I2, M1 proposed but NOT authorized
        controller.propose_next_phase(ProgramPhase.M1)
        assert controller.proposed_next_phase == ProgramPhase.M1
        assert not controller.can_execute_phase(ProgramPhase.M1)
        assert not controller.advance_phase(ProgramPhase.M1)
        assert controller.current_phase == ProgramPhase.I2  # Still at I2

    def test_phase_deviation_detected(self):
        """Deviation from authorized sequence is detected."""
        controller = PhaseController()
        controller.authorize_phase(ProgramPhase.C1, "4c86aff2...", "C1_TOKEN")
        controller.current_phase = ProgramPhase.C1
        controller.authorize_phase(ProgramPhase.I1, "e4d260da...", "I1_TOKEN")
        controller.authorize_phase(ProgramPhase.I2, "86f192a4...", "I2_TOKEN")
        controller.current_phase = ProgramPhase.I2

        # Try to jump to M2 (skipping M1)
        controller.proposed_next_phase = ProgramPhase.M2
        assert not controller.advance_phase(ProgramPhase.M2)

        # Try to jump to M3
        controller.proposed_next_phase = ProgramPhase.M3
        assert not controller.advance_phase(ProgramPhase.M3)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
"""Independent verification for offline integration."""

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class VerificationResult:
    """Immutable verification result."""
    mission_id: str
    action_hash: str
    verifier_id: str
    provider_receipt_hash: str
    expected_state: Dict[str, Any]
    observed_state: Dict[str, Any]
    success: bool
    discrepancies: List[str]
    verified_at: float
    verification_hash: str = ""

    def __post_init__(self):
        if not self.verification_hash:
            content = f"{self.mission_id}|{self.action_hash}|{self.verifier_id}|{self.provider_receipt_hash}|{self.success}"
            object.__setattr__(self, 'verification_hash', hashlib.sha256(content.encode()).hexdigest())


class IndependentVerifier:
    """Separately verifies external state after synthetic execution."""

    def __init__(self, mission_id: str):
        self.mission_id = mission_id
        self.verifier_id = f"verifier-{mission_id[:8]}"

    def verify(self, action_hash: str, provider_receipt_hash: str, fake_provider, expected_action_envelope) -> VerificationResult:
        """Independently verify the resulting external state."""
        # Get observed state from fake provider
        observed_state = fake_provider.get_state()
        
        # Compute expected state
        expected_state = dict(fake_provider.state)
        # Apply the expected action
        if expected_action_envelope.action.get("operation_id") == "mock_status_update":
            expected_state["status_dashboard"]["last_briefing_time"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            expected_state["status_dashboard"]["briefing_count"] += 1
            expected_state["status_dashboard"]["last_briefing_by"] = "SintraPrime (offline)"

        # Compare
        discrepancies = []
        for key in ["last_briefing_time", "briefing_count", "last_briefing_by"]:
            if expected_state["status_dashboard"][key] != observed_state["status_dashboard"][key]:
                discrepancies.append(f"status_dashboard.{key}: expected {expected_state['status_dashboard'][key]}, observed {observed_state['status_dashboard'][key]}")

        success = len(discrepancies) == 0

        result = VerificationResult(
            mission_id=self.mission_id,
            action_hash=action_hash,
            verifier_id=self.verifier_id,
            provider_receipt_hash=provider_receipt_hash,
            expected_state=expected_state,
            observed_state=observed_state,
            success=success,
            discrepancies=discrepancies,
            verified_at=time.time()
        )

        return result
"""Synthetic side effect executor and fake provider for offline integration."""

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class ExecutionState(Enum):
    """Side effect execution states."""
    PENDING = "PENDING"
    ATTEMPTING = "ATTEMPTING"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    DUPLICATE = "DUPLICATE"


@dataclass(frozen=True)
class ExecutionAttempt:
    """Immutable execution attempt record."""
    attempt_id: str
    mission_id: str
    action_hash: str
    idempotency_key: str
    state: ExecutionState
    timestamp: float
    provider_request_hash: str
    provider_response: Optional[Dict[str, Any]] = None
    provider_receipt_hash: Optional[str] = None
    error: Optional[str] = None


@dataclass(frozen=True)
class SyntheticProviderReceipt:
    """Immutable synthetic provider receipt."""
    receipt_id: str
    attempt_id: str
    action_hash: str
    success: bool
    state_after: Dict[str, Any]
    timestamp: float
    receipt_hash: str = ""

    def __post_init__(self):
        if not self.receipt_hash:
            content = f"{self.receipt_id}|{self.attempt_id}|{self.action_hash}|{self.success}|{json.dumps(self.state_after, sort_keys=True)}|{self.timestamp}"
            object.__setattr__(self, 'receipt_hash', hashlib.sha256(content.encode()).hexdigest())


class FakeProvider:
    """Fake provider that simulates external service without real I/O."""

    def __init__(self):
        self.state = {
            "status_dashboard": {
                "last_briefing_time": "2026-08-20T15:00:00Z",
                "briefing_count": 42,
                "last_briefing_by": "SintraPrime"
            }
        }
        self.attempts: Dict[str, ExecutionAttempt] = {}
        self.receipts: Dict[str, SyntheticProviderReceipt] = {}

    def execute(self, action_envelope) -> SyntheticProviderReceipt:
        """Execute the synthetic side effect."""
        attempt_id = f"attempt-{uuid.uuid4().hex[:12]}"
        action_hash = action_envelope.action_hash
        idempotency_key = action_envelope.idempotency_key

        # Check for duplicate attempt
        for attempt in self.attempts.values():
            if attempt.idempotency_key == idempotency_key:
                raise RuntimeError(f"Duplicate execution attempt: {idempotency_key}")

        # Record attempt
        attempt = ExecutionAttempt(
            attempt_id=attempt_id,
            mission_id=action_envelope.mission_id,
            action_hash=action_hash,
            idempotency_key=idempotency_key,
            state=ExecutionState.ATTEMPTING,
            timestamp=time.time(),
            provider_request_hash=hashlib.sha256(json.dumps(action_envelope.to_dict(), sort_keys=True).encode()).hexdigest()
        )
        self.attempts[attempt_id] = attempt

        # Execute the mock action
        action_type = action_envelope.action.get("operation_id", "unknown")
        if action_type == "mock_status_update":
            # Simulate updating status dashboard
            self.state["status_dashboard"]["last_briefing_time"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self.state["status_dashboard"]["briefing_count"] += 1
            self.state["status_dashboard"]["last_briefing_by"] = "SintraPrime (offline)"
            success = True
        else:
            success = False

        # Create receipt
        receipt = SyntheticProviderReceipt(
            receipt_id=f"receipt-{uuid.uuid4().hex[:12]}",
            attempt_id=attempt_id,
            action_hash=action_hash,
            success=success,
            state_after=self.state,
            timestamp=time.time()
        )
        self.receipts[receipt.receipt_id] = receipt

        # Update attempt state
        updated_attempt = ExecutionAttempt(
            attempt_id=attempt_id,
            mission_id=action_envelope.mission_id,
            action_hash=action_hash,
            idempotency_key=idempotency_key,
            state=ExecutionState.EXECUTED if success else ExecutionState.FAILED,
            timestamp=time.time(),
            provider_request_hash=attempt.provider_request_hash,
            provider_response={"success": success, "state": self.state},
            provider_receipt_hash=receipt.receipt_hash
        )
        self.attempts[attempt_id] = updated_attempt

        return receipt

    def get_state(self) -> Dict[str, Any]:
        return dict(self.state)

    def get_attempts(self) -> List[ExecutionAttempt]:
        return list(self.attempts.values())

    def get_receipts(self) -> List[SyntheticProviderReceipt]:
        return list(self.receipts.values())

    def verify_state(self, expected_action_hash: str) -> bool:
        """Verify that the expected action was executed."""
        for attempt in self.attempts.values():
            if attempt.action_hash == expected_action_hash and attempt.state == ExecutionState.EXECUTED:
                return True
        return False


class SyntheticSideEffectExecutor:
    """Executes the one authorized synthetic side effect."""

    def __init__(self):
        self.provider = FakeProvider()
        self.executed = False
        self.receipt: Optional[SyntheticProviderReceipt] = None

    def execute(self, action_envelope, approval_manager) -> SyntheticProviderReceipt:
        """Execute exactly one authorized side effect."""
        if self.executed:
            raise RuntimeError("Side effect already executed; exactly one allowed")

        if not approval_manager.validate_approval(action_envelope):
            raise RuntimeError("Approval invalid, expired, or missing")

        if action_envelope.capability != "synthetic_side_effect":
            raise RuntimeError(f"Unauthorized capability: {action_envelope.capability}")

        if action_envelope.consequence_class != "E0":
            raise RuntimeError(f"Consequence class {action_envelope.consequence_class} exceeds mission ceiling")

        # Execute
        receipt = self.provider.execute(action_envelope)
        self.executed = True
        self.receipt = receipt
        approval_manager.mark_used()

        return receipt

    def get_receipt(self) -> Optional[SyntheticProviderReceipt]:
        return self.receipt

    def verify_execution(self, action_hash: str) -> bool:
        return self.provider.verify_state(action_hash)
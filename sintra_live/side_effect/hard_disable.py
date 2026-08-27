"""Hard side-effect disablement boundary for SP-LIVE-001 I2.

This module enforces that NO real external side effects can execute
during the I2 milestone. All execution paths that would lead to
external actions are mechanically blocked.
"""

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class SideEffectType(Enum):
    """Types of side effects."""
    MOCK = "MOCK"
    EXTERNAL_API = "EXTERNAL_API"
    EMAIL = "EMAIL"
    SLACK = "SLACK"
    GOOGLE_DRIVE = "GOOGLE_DRIVE"
    GITHUB = "GITHUB"
    FINANCIAL = "FINANCIAL"
    LEGAL = "LEGAL"
    FILE_SYSTEM = "FILE_SYSTEM"
    DATABASE = "DATABASE"
    DEPLOYMENT = "DEPLOYMENT"
    RELEASE = "RELEASE"
    COMPUTER_USE = "COMPUTER_USE"


class ExecutionDecision(Enum):
    """Execution decisions."""
    ALLOW = "ALLOW"
    DENY = "DENY"
    DISABLED = "DISABLED"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"


@dataclass(frozen=True)
class ExecutionRequest:
    """Request to execute a side effect."""
    request_id: str
    mission_id: str
    action_hash: str
    side_effect_type: SideEffectType
    capability: str
    destination: Dict[str, Any]
    parameters: Dict[str, Any]
    consequence_class: str
    approval_hash: Optional[str] = None
    approval_timestamp: Optional[float] = None
    idempotency_key: str = ""
    timestamp: float = field(default_factory=lambda: __import__('time').time())


@dataclass(frozen=True)
class ExecutionResult:
    """Result of execution decision."""
    request_id: str
    decision: ExecutionDecision
    reason: str
    evidence: Dict[str, Any]
    timestamp: float = field(default_factory=lambda: __import__('time').time())


class HardDisableRegistry:
    """Registry of hard-disabled side effect types."""

    # These are MECHANICALLY disabled - no code path can enable them
    HARD_DISABLED = frozenset([
        SideEffectType.EXTERNAL_API,
        SideEffectType.EMAIL,
        SideEffectType.SLACK,
        SideEffectType.GOOGLE_DRIVE,
        SideEffectType.GITHUB,
        SideEffectType.FINANCIAL,
        SideEffectType.LEGAL,
        SideEffectType.DEPLOYMENT,
        SideEffectType.RELEASE,
        SideEffectType.COMPUTER_USE,
    ])

    # These require explicit configuration to enable (not in I2)
    CONDITIONALLY_DISABLED = frozenset([
        SideEffectType.FILE_SYSTEM,
        SideEffectType.DATABASE,
    ])

    # Only mock side effects allowed in I2
    ALLOWED_IN_I2 = frozenset([
        SideEffectType.MOCK,
    ])

    @classmethod
    def is_hard_disabled(cls, effect_type: SideEffectType) -> bool:
        return effect_type in cls.HARD_DISABLED

    @classmethod
    def is_allowed_in_i2(cls, effect_type: SideEffectType) -> bool:
        return effect_type in cls.ALLOWED_IN_I2

    @classmethod
    def get_decision(cls, effect_type: SideEffectType) -> ExecutionDecision:
        if effect_type in cls.HARD_DISABLED:
            return ExecutionDecision.DISABLED
        elif effect_type in cls.ALLOWED_IN_I2:
            return ExecutionDecision.ALLOW
        else:
            return ExecutionDecision.DENY


class SideEffectExecutor:
    """Side effect executor with hard disablement boundary."""

    def __init__(self, phase: str = "I2"):
        self.phase = phase
        self.execution_log: List[ExecutionResult] = []
        self.mock_provider = MockProvider()

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute or deny side effect based on hard boundary."""
        # Check hard disablement first
        if HardDisableRegistry.is_hard_disabled(request.side_effect_type):
            result = ExecutionResult(
                request_id=request.request_id,
                decision=ExecutionDecision.DISABLED,
                reason=f"Side effect type {request.side_effect_type.value} is hard-disabled in {self.phase}",
                evidence={
                    "side_effect_type": request.side_effect_type.value,
                    "phase": self.phase,
                    "hard_disabled": True,
                    "action_hash": request.action_hash,
                }
            )
            self.execution_log.append(result)
            return result

        # Check if allowed in current phase
        if not HardDisableRegistry.is_allowed_in_i2(request.side_effect_type):
            result = ExecutionResult(
                request_id=request.request_id,
                decision=ExecutionDecision.DENY,
                reason=f"Side effect type {request.side_effect_type.value} not allowed in {self.phase}",
                evidence={
                    "side_effect_type": request.side_effect_type.value,
                    "phase": self.phase,
                    "allowed_types": [t.value for t in HardDisableRegistry.ALLOWED_IN_I2],
                }
            )
            self.execution_log.append(result)
            return result

        # Verify approval for consequential actions
        if request.consequence_class in ("E1", "E2", "E3", "E4") and not request.approval_hash:
            result = ExecutionResult(
                request_id=request.request_id,
                decision=ExecutionDecision.REQUIRES_APPROVAL,
                reason=f"Consequential action {request.consequence_class} requires approval",
                evidence={
                    "consequence_class": request.consequence_class,
                    "has_approval": False,
                }
            )
            self.execution_log.append(result)
            return result

        # Execute mock side effect
        if request.side_effect_type == SideEffectType.MOCK:
            mock_result = self.mock_provider.execute(request)
            result = ExecutionResult(
                request_id=request.request_id,
                decision=ExecutionDecision.ALLOW,
                reason="Mock side effect executed",
                evidence={
                    "mock_result": mock_result,
                    "action_hash": request.action_hash,
                }
            )
            self.execution_log.append(result)
            return result

        # Should never reach here
        result = ExecutionResult(
            request_id=request.request_id,
            decision=ExecutionDecision.DENY,
            reason="Unhandled side effect type",
            evidence={"side_effect_type": request.side_effect_type.value}
        )
        self.execution_log.append(result)
        return result

    def get_execution_log(self) -> List[ExecutionResult]:
        """Get execution log for evidence."""
        return self.execution_log

    def verify_no_real_effects(self) -> bool:
        """Verify no real side effects were executed."""
        for result in self.execution_log:
            if result.decision == ExecutionDecision.ALLOW:
                evidence = result.evidence
                if "mock_result" not in evidence:
                    return False
        return True


class MockProvider:
    """Mock provider for safe side effect simulation."""

    def __init__(self):
        self.state = {
            "mock_actions": [],
            "status_dashboard": {
                "last_briefing_time": "2026-08-20T15:00:00Z",
                "actions_completed": 0,
            }
        }

    def execute(self, request: ExecutionRequest) -> Dict[str, Any]:
        """Execute mock action."""
        action_record = {
            "action_id": request.request_id,
            "action_hash": request.action_hash,
            "capability": request.capability,
            "destination": request.destination,
            "parameters": request.parameters,
            "timestamp": request.timestamp,
            "idempotency_key": request.idempotency_key,
        }

        self.state["mock_actions"].append(action_record)
        self.state["status_dashboard"]["actions_completed"] += 1
        self.state["status_dashboard"]["last_briefing_time"] = __import__('datetime').datetime.utcnow().isoformat() + "Z"

        return {
            "success": True,
            "action_id": request.request_id,
            "state_after": dict(self.state["status_dashboard"]),
            "receipt_hash": hashlib.sha256(str(action_record).encode()).hexdigest()[:32]
        }


# Global singleton for I2 phase
I2_EXECUTOR = SideEffectExecutor(phase="I2")


def get_i2_executor() -> SideEffectExecutor:
    """Get the I2 phase executor singleton."""
    return I2_EXECUTOR


def verify_i2_hard_disablement() -> Dict[str, Any]:
    """Verify I2 hard disablement is active."""
    executor = get_i2_executor()
    return {
        "phase": executor.phase,
        "hard_disabled_types": [t.value for t in HardDisableRegistry.HARD_DISABLED],
        "allowed_types": [t.value for t in HardDisableRegistry.ALLOWED_IN_I2],
        "no_real_effects": executor.verify_no_real_effects(),
        "execution_count": len(executor.execution_log),
    }
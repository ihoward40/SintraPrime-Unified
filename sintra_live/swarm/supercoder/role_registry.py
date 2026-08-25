"""SuperCoder role registry — persistent coding agent roles and quality levels."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class SuperCoderRole(str, Enum):
    """Persistent coding agent roles."""
    ARCHITECT = "ARCHITECT"
    IMPLEMENTER = "IMPLEMENTER"
    TEST_ENGINEER = "TEST_ENGINEER"
    DEBUGGER = "DEBUGGER"
    SECURITY_REVIEWER = "SECURITY_REVIEWER"
    CODE_REVIEWER = "CODE_REVIEWER"
    INTEGRATOR = "INTEGRATOR"
    CONTEXT_KEEPER = "CONTEXT_KEEPER"
    SUPERVISOR = "SUPERVISOR"


class QualityLevel(str, Enum):
    """Quality control modes for the supervisor."""
    FAST = "FAST"
    STANDARD = "STANDARD"
    DEEP = "DEEP"
    FORENSIC = "FORENSIC"


# Default quality by mission type
DEFAULT_QUALITY = {
    "product": QualityLevel.STANDARD,
    "authority": QualityLevel.DEEP,
    "security": QualityLevel.DEEP,
    "live_execution": QualityLevel.FORENSIC,
    "governance": QualityLevel.FORENSIC,
}


@dataclass
class RoleAssignment:
    """A role assigned to a specific worker for a specific packet."""
    role: SuperCoderRole
    worker_id: str
    packet_id: str
    mission_id: str


class RoleRegistry:
    """Manages role assignments and quality levels for coding missions.

    The registry tracks which roles are active and enforces the
    separation of concerns: BUILDER != CERTIFIER.
    """

    def __init__(self):
        self._assignments: List[RoleAssignment] = []
        self._quality: Dict[str, QualityLevel] = {}

    def assign(self, role: SuperCoderRole, worker_id: str, packet_id: str, mission_id: str) -> RoleAssignment:
        assignment = RoleAssignment(
            role=role,
            worker_id=worker_id,
            packet_id=packet_id,
            mission_id=mission_id,
        )
        self._assignments.append(assignment)
        return assignment

    def get_role_for_packet(self, packet_id: str) -> Optional[SuperCoderRole]:
        for a in reversed(self._assignments):
            if a.packet_id == packet_id:
                return a.role
        return None

    def get_assignments_for_mission(self, mission_id: str) -> List[RoleAssignment]:
        return [a for a in self._assignments if a.mission_id == mission_id]

    def set_quality(self, mission_id: str, level: QualityLevel) -> None:
        self._quality[mission_id] = level

    def get_quality(self, mission_id: str) -> QualityLevel:
        return self._quality.get(mission_id, QualityLevel.STANDARD)

    def has_separate_certifier(self, mission_id: str) -> bool:
        """Check that the builder and certifier are different agents."""
        roles_for_mission = [a.role for a in self._assignments if a.mission_id == mission_id]
        has_builder = SuperCoderRole.IMPLEMENTER in roles_for_mission
        has_certifier = any(
            r in roles_for_mission
            for r in [SuperCoderRole.TEST_ENGINEER, SuperCoderRole.CODE_REVIEWER,
                      SuperCoderRole.SECURITY_REVIEWER]
        )
        return has_builder and has_certifier

    def required_roles_for_quality(self, level: QualityLevel) -> Tuple[SuperCoderRole, ...]:
        """Return required roles for a given quality level."""
        if level == QualityLevel.FAST:
            return (SuperCoderRole.IMPLEMENTER,)
        elif level == QualityLevel.STANDARD:
            return (
                SuperCoderRole.ARCHITECT,
                SuperCoderRole.IMPLEMENTER,
                SuperCoderRole.TEST_ENGINEER,
                SuperCoderRole.CODE_REVIEWER,
            )
        elif level == QualityLevel.DEEP:
            return (
                SuperCoderRole.ARCHITECT,
                SuperCoderRole.IMPLEMENTER,
                SuperCoderRole.TEST_ENGINEER,
                SuperCoderRole.CODE_REVIEWER,
                SuperCoderRole.SECURITY_REVIEWER,
                SuperCoderRole.INTEGRATOR,
            )
        elif level == QualityLevel.FORENSIC:
            return (
                SuperCoderRole.ARCHITECT,
                SuperCoderRole.IMPLEMENTER,
                SuperCoderRole.TEST_ENGINEER,
                SuperCoderRole.CODE_REVIEWER,
                SuperCoderRole.SECURITY_REVIEWER,
                SuperCoderRole.INTEGRATOR,
            )
        return ()
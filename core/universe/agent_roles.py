"""
Agent Roles System: Defines all agent roles, capabilities, and permissions.
Supports inheritance, dynamic role creation, and permission matrices.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Set
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RoleCategory(Enum):
    """Categories for agent roles."""
    ANALYSIS = "analysis"
    EXECUTION = "execution"
    LEARNING = "learning"
    COORDINATION = "coordination"
    SECURITY = "security"
    CREATION = "creation"
    RESEARCH = "research"
    OPTIMIZATION = "optimization"


class ProficiencyLevel(Enum):
    """Proficiency levels for capabilities."""
    NOVICE = 1
    APPRENTICE = 2
    JOURNEYMAN = 3
    EXPERT = 4
    MASTER = 5


class BaseRole:
    """Base class for all agent roles."""

    def __init__(
        self,
        role_id: str,
        role_name: str,
        description: str,
        category: RoleCategory,
        capabilities: Optional[List[str]] = None,
        parent_role: Optional["BaseRole"] = None,
        priority_weight: float = 1.0,
    ):
        """
        Initialize a role.

        Args:
            role_id: Unique role identifier
            role_name: Human-readable role name
            description: Role description
            category: Role category
            capabilities: List of capability names
            parent_role: Parent role for inheritance
            priority_weight: Priority weight for task assignment
        """
        self.role_id = role_id
        self.role_name = role_name
        self.description = description
        self.category = category
        self.capabilities = set(capabilities or [])
        self.parent_role = parent_role
        self.priority_weight = priority_weight
        self.permissions: Dict[str, bool] = {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def add_capability(self, capability: str) -> None:
        """Add a capability to this role."""
        self.capabilities.add(capability)
        self.updated_at = datetime.now()

    def remove_capability(self, capability: str) -> None:
        """Remove a capability from this role."""
        self.capabilities.discard(capability)
        self.updated_at = datetime.now()

    def has_capability(self, capability: str) -> bool:
        """Check if role has a capability (including inherited)."""
        if capability in self.capabilities:
            return True
        if self.parent_role:
            return self.parent_role.has_capability(capability)
        return False

    def get_all_capabilities(self) -> Set[str]:
        """Get all capabilities (including inherited)."""
        all_caps = self.capabilities.copy()
        if self.parent_role:
            all_caps.update(self.parent_role.get_all_capabilities())
        return all_caps

    def set_permission(self, permission: str, allowed: bool) -> None:
        """Set a permission for this role."""
        self.permissions[permission] = allowed
        self.updated_at = datetime.now()

    def has_permission(self, permission: str) -> bool:
        """Check if role has a permission (including inherited)."""
        if permission in self.permissions:
            return self.permissions[permission]
        if self.parent_role:
            return self.parent_role.has_permission(permission)
        return False

    def to_dict(self) -> Dict:
        """Serialize role to dictionary."""
        return {
            "role_id": self.role_id,
            "role_name": self.role_name,
            "description": self.description,
            "category": self.category.value,
            "capabilities": list(self.capabilities),
            "all_capabilities": list(self.get_all_capabilities()),
            "parent_role_id": self.parent_role.role_id if self.parent_role else None,
            "priority_weight": self.priority_weight,
            "permissions": self.permissions,
            "created_at": self.created_at.isoformat(),
        }


class RoleManager:
    """Manages all agent roles and role operations."""

    # Define base roles
    ANALYST_ROLE = BaseRole(
        role_id="analyst",
        role_name="Analyst",
        description="Analyzes data, patterns, and information for insights",
        category=RoleCategory.ANALYSIS,
        capabilities=[
            "data_analysis",
            "pattern_recognition",
            "report_generation",
            "data_visualization",
            "statistical_analysis",
        ],
        priority_weight=1.0,
    )

    EXECUTOR_ROLE = BaseRole(
        role_id="executor",
        role_name="Executor",
        description="Executes tasks and actions in the system",
        category=RoleCategory.EXECUTION,
        capabilities=[
            "task_execution",
            "command_execution",
            "file_operations",
            "api_calls",
            "resource_management",
        ],
        priority_weight=1.2,
    )

    LEARNER_ROLE = BaseRole(
        role_id="learner",
        role_name="Learner",
        description="Learns from tasks and generates new knowledge",
        category=RoleCategory.LEARNING,
        capabilities=[
            "experience_capture",
            "knowledge_generation",
            "pattern_learning",
            "skill_development",
            "knowledge_sharing",
        ],
        priority_weight=0.9,
    )

    COORDINATOR_ROLE = BaseRole(
        role_id="coordinator",
        role_name="Coordinator",
        description="Coordinates and orchestrates other agents",
        category=RoleCategory.COORDINATION,
        capabilities=[
            "task_distribution",
            "agent_orchestration",
            "dependency_management",
            "team_coordination",
            "resource_allocation",
        ],
        priority_weight=1.5,
    )

    VISION_ROLE = BaseRole(
        role_id="vision",
        role_name="Vision",
        description="Processes images and visual information",
        category=RoleCategory.ANALYSIS,
        capabilities=[
            "image_analysis",
            "object_detection",
            "scene_understanding",
            "text_extraction",
            "visual_processing",
        ],
        parent_role=ANALYST_ROLE,
        priority_weight=1.1,
    )

    GUARD_ROLE = BaseRole(
        role_id="guard",
        role_name="Guard",
        description="Ensures security and validates actions",
        category=RoleCategory.SECURITY,
        capabilities=[
            "security_validation",
            "access_control",
            "threat_detection",
            "audit_logging",
            "compliance_checking",
        ],
        priority_weight=1.6,
    )

    RESEARCHER_ROLE = BaseRole(
        role_id="researcher",
        role_name="Researcher",
        description="Conducts research and gathers information",
        category=RoleCategory.RESEARCH,
        capabilities=[
            "information_gathering",
            "literature_review",
            "hypothesis_testing",
            "data_collection",
            "research_synthesis",
        ],
        priority_weight=0.95,
    )

    CREATOR_ROLE = BaseRole(
        role_id="creator",
        role_name="Creator",
        description="Creates new content and solutions",
        category=RoleCategory.CREATION,
        capabilities=[
            "content_generation",
            "code_generation",
            "creative_thinking",
            "solution_design",
            "innovation",
        ],
        priority_weight=1.1,
    )

    NEGOTIATOR_ROLE = BaseRole(
        role_id="negotiator",
        role_name="Negotiator",
        description="Negotiates and resolves conflicts between agents",
        category=RoleCategory.COORDINATION,
        capabilities=[
            "conflict_resolution",
            "negotiation",
            "consensus_building",
            "decision_facilitation",
            "mediation",
        ],
        parent_role=COORDINATOR_ROLE,
        priority_weight=1.3,
    )

    MONITOR_ROLE = BaseRole(
        role_id="monitor",
        role_name="Monitor",
        description="Monitors system health and performance",
        category=RoleCategory.OPTIMIZATION,
        capabilities=[
            "system_monitoring",
            "performance_tracking",
            "health_checking",
            "metric_collection",
            "alerting",
        ],
        priority_weight=1.2,
    )

    DEBUGGER_ROLE = BaseRole(
        role_id="debugger",
        role_name="Debugger",
        description="Debugs issues and troubleshoots problems",
        category=RoleCategory.EXECUTION,
        capabilities=[
            "error_diagnosis",
            "log_analysis",
            "issue_tracking",
            "root_cause_analysis",
            "solution_testing",
        ],
        parent_role=EXECUTOR_ROLE,
        priority_weight=1.3,
    )

    OPTIMIZER_ROLE = BaseRole(
        role_id="optimizer",
        role_name="Optimizer",
        description="Optimizes performance and efficiency",
        category=RoleCategory.OPTIMIZATION,
        capabilities=[
            "performance_optimization",
            "resource_optimization",
            "algorithm_improvement",
            "bottleneck_identification",
            "efficiency_enhancement",
        ],
        parent_role=ANALYST_ROLE,
        priority_weight=1.2,
    )

    def __init__(self):
        """Initialize role manager with all predefined roles."""
        self.roles: Dict[str, BaseRole] = {
            "analyst": self.ANALYST_ROLE,
            "executor": self.EXECUTOR_ROLE,
            "learner": self.LEARNER_ROLE,
            "coordinator": self.COORDINATOR_ROLE,
            "vision": self.VISION_ROLE,
            "guard": self.GUARD_ROLE,
            "researcher": self.RESEARCHER_ROLE,
            "creator": self.CREATOR_ROLE,
            "negotiator": self.NEGOTIATOR_ROLE,
            "monitor": self.MONITOR_ROLE,
            "debugger": self.DEBUGGER_ROLE,
            "optimizer": self.OPTIMIZER_ROLE,
        }
        self.custom_roles: Dict[str, BaseRole] = {}

    def get_role(self, role_id: str) -> Optional[BaseRole]:
        """Get a role by ID."""
        return self.roles.get(role_id) or self.custom_roles.get(role_id)

    def create_custom_role(
        self,
        role_name: str,
        description: str,
        category: RoleCategory,
        capabilities: Optional[List[str]] = None,
        parent_role_id: Optional[str] = None,
        priority_weight: float = 1.0,
    ) -> BaseRole:
        """
        Create a custom role from template.

        Args:
            role_name: Human-readable role name
            description: Role description
            category: Role category
            capabilities: List of capability names
            parent_role_id: Parent role for inheritance
            priority_weight: Priority weight for task assignment

        Returns:
            Created custom role
        """
        role_id = f"custom_{uuid.uuid4().hex[:8]}"
        parent_role = None
        if parent_role_id:
            parent_role = self.get_role(parent_role_id)

        custom_role = BaseRole(
            role_id=role_id,
            role_name=role_name,
            description=description,
            category=category,
            capabilities=capabilities,
            parent_role=parent_role,
            priority_weight=priority_weight,
        )

        self.custom_roles[role_id] = custom_role
        logger.info(f"Created custom role: {role_id} - {role_name}")
        return custom_role

    def list_roles(self, category: Optional[RoleCategory] = None) -> List[BaseRole]:
        """
        List all roles, optionally filtered by category.

        Args:
            category: Optional category filter

        Returns:
            List of roles
        """
        all_roles = list(self.roles.values()) + list(self.custom_roles.values())
        if category:
            return [r for r in all_roles if r.category == category]
        return all_roles

    def get_roles_for_task(
        self, task_type: str, required_capabilities: Optional[List[str]] = None
    ) -> List[BaseRole]:
        """
        Get suitable roles for a specific task type.

        Args:
            task_type: Type of task
            required_capabilities: Required capabilities

        Returns:
            List of suitable roles, sorted by priority
        """
        suitable_roles = []

        for role in self.list_roles():
            # Check if role has all required capabilities
            if required_capabilities:
                if not all(role.has_capability(cap) for cap in required_capabilities):
                    continue

            suitable_roles.append(role)

        # Sort by priority weight (descending)
        suitable_roles.sort(key=lambda r: r.priority_weight, reverse=True)
        return suitable_roles

    def add_capability_to_role(self, role_id: str, capability: str) -> bool:
        """Add a capability to a role."""
        role = self.get_role(role_id)
        if role:
            role.add_capability(capability)
            logger.info(f"Added capability '{capability}' to role '{role_id}'")
            return True
        return False

    def remove_capability_from_role(self, role_id: str, capability: str) -> bool:
        """Remove a capability from a role."""
        role = self.get_role(role_id)
        if role:
            role.remove_capability(capability)
            logger.info(f"Removed capability '{capability}' from role '{role_id}'")
            return True
        return False

    def export_roles(self) -> Dict:
        """Export all roles as dictionary."""
        return {
            "built_in": {role_id: role.to_dict() for role_id, role in self.roles.items()},
            "custom": {
                role_id: role.to_dict() for role_id, role in self.custom_roles.items()
            },
        }

    def get_role_count(self) -> int:
        """Get total number of roles."""
        return len(self.roles) + len(self.custom_roles)


# Global role manager instance
_role_manager = None


def get_role_manager() -> RoleManager:
    """Get or create the global role manager."""
    global _role_manager
    if _role_manager is None:
        _role_manager = RoleManager()
    return _role_manager

"""
Agent Factory: Dynamically generates agents from natural language descriptions.
Handles validation, capability mapping, and automatic registration.
"""

import json
import uuid
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import logging
import inspect
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class AgentTemplate:
    """Template for agent definitions."""

    def __init__(
        self,
        name: str,
        role_id: str,
        description: str,
        capabilities: List[str],
        specialization: Optional[str] = None,
        skill_level: int = 3,
        max_concurrent_tasks: int = 5,
        retry_policy: Optional[Dict] = None,
    ):
        """
        Initialize agent template.

        Args:
            name: Agent name
            role_id: Role ID
            description: Agent description
            capabilities: List of capabilities
            specialization: Optional specialization
            skill_level: Initial skill level (1-5)
            max_concurrent_tasks: Max concurrent tasks
            retry_policy: Retry policy configuration
        """
        self.name = name
        self.role_id = role_id
        self.description = description
        self.capabilities = capabilities
        self.specialization = specialization
        self.skill_level = max(1, min(5, skill_level))
        self.max_concurrent_tasks = max_concurrent_tasks
        self.retry_policy = retry_policy or {
            "max_retries": 3,
            "backoff_factor": 2,
            "initial_delay_ms": 100,
        }

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "role_id": self.role_id,
            "description": self.description,
            "capabilities": self.capabilities,
            "specialization": self.specialization,
            "skill_level": self.skill_level,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "retry_policy": self.retry_policy,
        }


class AgentValidator:
    """Validates agents before deployment."""

    # Required fields for any agent
    REQUIRED_FIELDS = {"name", "role_id", "description", "capabilities"}

    # Validation rules
    VALIDATION_RULES = {
        "name": {"type": str, "min_length": 1, "max_length": 100},
        "role_id": {"type": str, "min_length": 1},
        "description": {"type": str, "min_length": 10},
        "capabilities": {"type": list, "min_items": 1, "max_items": 50},
        "skill_level": {"type": int, "min": 1, "max": 5},
        "max_concurrent_tasks": {"type": int, "min": 1, "max": 100},
    }

    def __init__(self):
        """Initialize validator."""
        self.validation_errors: List[str] = []

    def validate(self, definition: Dict) -> bool:
        """
        Validate agent definition.

        Args:
            definition: Agent definition dictionary

        Returns:
            True if valid, False otherwise
        """
        self.validation_errors = []

        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in definition:
                self.validation_errors.append(f"Missing required field: {field}")
        
        if self.validation_errors:
            return False

        # Check field types and constraints
        for field, rules in self.VALIDATION_RULES.items():
            if field not in definition:
                continue

            value = definition[field]

            # Type check
            if "type" in rules and not isinstance(value, rules["type"]):
                self.validation_errors.append(
                    f"Field '{field}' must be of type {rules['type'].__name__}"
                )
                continue

            # String length validation
            if isinstance(value, str):
                if "min_length" in rules and len(value) < rules["min_length"]:
                    self.validation_errors.append(
                        f"Field '{field}' must be at least {rules['min_length']} characters"
                    )
                if "max_length" in rules and len(value) > rules["max_length"]:
                    self.validation_errors.append(
                        f"Field '{field}' must be at most {rules['max_length']} characters"
                    )

            # List validation
            if isinstance(value, list):
                if "min_items" in rules and len(value) < rules["min_items"]:
                    self.validation_errors.append(
                        f"Field '{field}' must have at least {rules['min_items']} items"
                    )
                if "max_items" in rules and len(value) > rules["max_items"]:
                    self.validation_errors.append(
                        f"Field '{field}' must have at most {rules['max_items']} items"
                    )

            # Number validation
            if isinstance(value, (int, float)):
                if "min" in rules and value < rules["min"]:
                    self.validation_errors.append(
                        f"Field '{field}' must be at least {rules['min']}"
                    )
                if "max" in rules and value > rules["max"]:
                    self.validation_errors.append(
                        f"Field '{field}' must be at most {rules['max']}"
                    )

        return len(self.validation_errors) == 0

    def get_errors(self) -> List[str]:
        """Get validation errors."""
        return self.validation_errors


class GeneratedAgent:
    """Dynamically generated agent instance."""

    def __init__(self, definition: Dict, agent_id: str, creation_time: float):
        """
        Initialize generated agent.

        Args:
            definition: Agent definition
            agent_id: Unique agent ID
            creation_time: Creation time in seconds
        """
        self.agent_id = agent_id
        self.definition = definition
        self.name = definition["name"]
        self.role_id = definition["role_id"]
        self.description = definition["description"]
        self.capabilities = definition["capabilities"]
        self.specialization = definition.get("specialization")
        self.skill_level = definition.get("skill_level", 3)
        self.max_concurrent_tasks = definition.get("max_concurrent_tasks", 5)
        self.retry_policy = definition.get("retry_policy", {})
        self.creation_time = creation_time
        self.status = "ready"
        self.performance = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "success_rate": 0.0,
            "avg_execution_time_ms": 0,
        }
        self.created_at = datetime.now()

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role_id": self.role_id,
            "description": self.description,
            "capabilities": self.capabilities,
            "specialization": self.specialization,
            "skill_level": self.skill_level,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "status": self.status,
            "performance": self.performance,
            "creation_time_ms": int(self.creation_time * 1000),
            "created_at": self.created_at.isoformat(),
        }


class AgentFactory:
    """
    Factory for dynamically generating agents from descriptions.
    Handles validation, capability mapping, and registration.
    """

    def __init__(self, max_creation_time_ms: float = 5000):
        """
        Initialize factory.

        Args:
            max_creation_time_ms: Maximum time to create agent
        """
        self.agents: Dict[str, GeneratedAgent] = {}
        self.agent_registry: Dict[str, Dict] = {}  # For tracking all agents
        self.max_creation_time = max_creation_time_ms / 1000  # Convert to seconds
        self.validator = AgentValidator()
        self.creation_count = 0
        logger.info(f"AgentFactory initialized with {max_creation_time_ms}ms timeout")

    def create_agent(
        self,
        description: str,
        role_id: str,
        name: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        specialization: Optional[str] = None,
        skill_level: int = 3,
        max_concurrent_tasks: int = 5,
    ) -> tuple[Optional[GeneratedAgent], Optional[str]]:
        """
        Create an agent from natural language description.

        Args:
            description: Natural language description
            role_id: Role ID
            name: Optional agent name (auto-generated if not provided)
            capabilities: Optional list of capabilities
            specialization: Optional specialization
            skill_level: Skill level (1-5)
            max_concurrent_tasks: Max concurrent tasks

        Returns:
            Tuple of (agent, error_message)
        """
        start_time = time.time()

        # Auto-generate name if not provided
        if not name:
            name = f"Agent_{uuid.uuid4().hex[:8]}"

        # Auto-infer capabilities if not provided
        if not capabilities:
            capabilities = self._infer_capabilities(description, role_id)

        # Create definition
        definition = {
            "name": name,
            "role_id": role_id,
            "description": description,
            "capabilities": capabilities,
            "specialization": specialization,
            "skill_level": skill_level,
            "max_concurrent_tasks": max_concurrent_tasks,
            "retry_policy": {
                "max_retries": 3,
                "backoff_factor": 2,
                "initial_delay_ms": 100,
            },
        }

        # Validate definition
        if not self.validator.validate(definition):
            error_msg = "; ".join(self.validator.get_errors())
            logger.error(f"Validation failed: {error_msg}")
            return None, error_msg

        # Check creation time
        if time.time() - start_time > self.max_creation_time:
            error_msg = f"Creation time exceeded {self.max_creation_time * 1000}ms"
            logger.error(error_msg)
            return None, error_msg

        # Create agent
        agent_id = f"agent_{uuid.uuid4().hex[:12]}"
        creation_time = time.time() - start_time

        agent = GeneratedAgent(definition, agent_id, creation_time)
        self.agents[agent_id] = agent
        self.agent_registry[agent_id] = definition
        self.creation_count += 1

        logger.info(
            f"Created agent {agent_id} ({name}) in {creation_time*1000:.2f}ms, "
            f"role={role_id}, capabilities={len(capabilities)}"
        )

        return agent, None

    def _infer_capabilities(self, description: str, role_id: str) -> List[str]:
        """
        Infer capabilities from description and role.

        Args:
            description: Agent description
            role_id: Role ID

        Returns:
            List of inferred capabilities
        """
        # Map keywords to capabilities
        keyword_map = {
            "analyze": "data_analysis",
            "execute": "task_execution",
            "learn": "experience_capture",
            "coordinate": "task_distribution",
            "research": "information_gathering",
            "create": "content_generation",
            "code": "code_generation",
            "debug": "error_diagnosis",
            "monitor": "system_monitoring",
            "optimize": "performance_optimization",
            "visualize": "data_visualization",
            "report": "report_generation",
        }

        inferred = []
        description_lower = description.lower()

        for keyword, capability in keyword_map.items():
            if keyword in description_lower:
                inferred.append(capability)

        # Add default capabilities for role
        role_defaults = {
            "analyst": ["data_analysis", "pattern_recognition", "report_generation"],
            "executor": ["task_execution", "command_execution", "file_operations"],
            "learner": ["experience_capture", "knowledge_generation", "pattern_learning"],
            "coordinator": ["task_distribution", "agent_orchestration", "team_coordination"],
            "vision": ["image_analysis", "object_detection", "scene_understanding"],
            "guard": ["security_validation", "access_control", "audit_logging"],
            "researcher": ["information_gathering", "literature_review", "data_collection"],
            "creator": ["content_generation", "code_generation", "creative_thinking"],
            "debugger": ["error_diagnosis", "log_analysis", "root_cause_analysis"],
            "monitor": ["system_monitoring", "performance_tracking", "health_checking"],
            "optimizer": ["performance_optimization", "bottleneck_identification"],
            "negotiator": ["conflict_resolution", "consensus_building"],
        }

        # Add role defaults if not already present
        defaults = role_defaults.get(role_id, [])
        for cap in defaults:
            if cap not in inferred:
                inferred.append(cap)

        # Remove duplicates and ensure at least 3 capabilities
        inferred = list(set(inferred))
        if len(inferred) < 3:
            inferred.extend(defaults[: 3 - len(inferred)])

        return list(set(inferred))[:10]  # Limit to 10 capabilities

    def get_agent(self, agent_id: str) -> Optional[GeneratedAgent]:
        """Get agent by ID."""
        return self.agents.get(agent_id)

    def list_agents(self) -> List[GeneratedAgent]:
        """List all created agents."""
        return list(self.agents.values())

    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            if agent_id in self.agent_registry:
                del self.agent_registry[agent_id]
            logger.info(f"Deleted agent {agent_id}")
            return True
        return False

    def export_agents(self) -> Dict:
        """Export all agents as dictionary."""
        return {
            agent_id: agent.to_dict() for agent_id, agent in self.agents.items()
        }

    def get_stats(self) -> Dict:
        """Get factory statistics."""
        total_agents = len(self.agents)
        total_capabilities = sum(len(agent.capabilities) for agent in self.agents.values())
        avg_capabilities = (
            total_capabilities / total_agents if total_agents > 0 else 0
        )

        return {
            "total_agents": total_agents,
            "agents_created": self.creation_count,
            "total_capabilities": total_capabilities,
            "avg_capabilities_per_agent": avg_capabilities,
            "agents_by_role": self._count_agents_by_role(),
            "avg_creation_time_ms": self._avg_creation_time(),
        }

    def _count_agents_by_role(self) -> Dict[str, int]:
        """Count agents by role."""
        counts = {}
        for agent in self.agents.values():
            role = agent.role_id
            counts[role] = counts.get(role, 0) + 1
        return counts

    def _avg_creation_time(self) -> float:
        """Calculate average creation time."""
        if not self.agents:
            return 0
        total_time = sum(agent.creation_time for agent in self.agents.values())
        return (total_time / len(self.agents)) * 1000  # Convert to ms


# Global factory instance
_factory = None


def get_factory() -> AgentFactory:
    """Get or create the global factory."""
    global _factory
    if _factory is None:
        _factory = AgentFactory()
    return _factory


# Example agent definitions
EXAMPLE_AGENT_DEFINITIONS = [
    {
        "name": "DataAnalyzer",
        "role_id": "analyst",
        "description": "Analyzes data patterns and generates insights",
        "capabilities": ["data_analysis", "pattern_recognition", "report_generation"],
    },
    {
        "name": "TaskExecutor",
        "role_id": "executor",
        "description": "Executes system commands and API calls",
        "capabilities": ["task_execution", "command_execution", "api_calls"],
    },
    {
        "name": "VisionProcessor",
        "role_id": "vision",
        "description": "Processes images and extracts visual information",
        "capabilities": ["image_analysis", "object_detection", "text_extraction"],
    },
    {
        "name": "SecurityGuard",
        "role_id": "guard",
        "description": "Ensures security and validates all actions",
        "capabilities": ["security_validation", "access_control", "audit_logging"],
    },
    {
        "name": "CodeCreator",
        "role_id": "creator",
        "description": "Generates code and creates solutions",
        "capabilities": ["code_generation", "creative_thinking", "solution_design"],
    },
    {
        "name": "TeamCoordinator",
        "role_id": "coordinator",
        "description": "Coordinates teams and distributes tasks",
        "capabilities": ["task_distribution", "agent_orchestration", "team_coordination"],
    },
    {
        "name": "Researcher",
        "role_id": "researcher",
        "description": "Gathers and synthesizes research information",
        "capabilities": ["information_gathering", "literature_review", "data_collection"],
    },
    {
        "name": "Debugger",
        "role_id": "debugger",
        "description": "Diagnoses and fixes system issues",
        "capabilities": ["error_diagnosis", "log_analysis", "root_cause_analysis"],
    },
    {
        "name": "PerformanceMonitor",
        "role_id": "monitor",
        "description": "Monitors system health and performance metrics",
        "capabilities": ["system_monitoring", "performance_tracking", "health_checking"],
    },
    {
        "name": "SystemOptimizer",
        "role_id": "optimizer",
        "description": "Optimizes performance and resource usage",
        "capabilities": ["performance_optimization", "bottleneck_identification"],
    },
    {
        "name": "ConflictResolver",
        "role_id": "negotiator",
        "description": "Resolves conflicts and builds consensus",
        "capabilities": ["conflict_resolution", "consensus_building", "mediation"],
    },
    {
        "name": "KnowledgeLearner",
        "role_id": "learner",
        "description": "Learns from experiences and generates knowledge",
        "capabilities": ["experience_capture", "knowledge_generation", "skill_development"],
    },
]

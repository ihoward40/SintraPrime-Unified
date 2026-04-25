"""
BaseAgent: Foundation class for all agents in the UniVerse ecosystem.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all agents in SintraPrime UniVerse."""

    def __init__(
        self,
        name: str,
        role: str,
        specialization: Optional[str] = None,
        model: str = "claude-3.5-sonnet",
    ):
        """
        Initialize a new agent.

        Args:
            name: Agent display name
            role: Agent role (analyst, executor, learner, coordinator, vision, guard)
            specialization: Optional specialization area
            model: LLM model to use
        """
        self.agent_id = str(uuid.uuid4())
        self.name = name
        self.role = role
        self.specialization = specialization
        self.model = model
        self.status = "idle"
        self.current_task_id: Optional[str] = None
        self.skills: Dict[str, Any] = {}
        self.performance_metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "success_rate": 0.0,
            "avg_execution_time_ms": 0,
        }
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    @abstractmethod
    async def execute(self, task_id: str, command: str) -> Dict[str, Any]:
        """
        Execute a task command.

        Args:
            task_id: Unique task identifier
            command: Task command/description

        Returns:
            Task result dictionary
        """
        pass

    @abstractmethod
    async def learn(self, task_id: str, result: Dict[str, Any]) -> Optional[str]:
        """
        Learn from completed task to generate new skills.

        Args:
            task_id: Completed task ID
            result: Task result

        Returns:
            Generated skill ID or None
        """
        pass

    @abstractmethod
    async def collaborate(
        self, other_agent: "BaseAgent", message: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Collaborate with another agent.

        Args:
            other_agent: Target agent for collaboration
            message: Collaboration message

        Returns:
            Collaboration response
        """
        pass

    def get_status(self) -> Dict[str, Any]:
        """Get agent current status."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "status": self.status,
            "current_task_id": self.current_task_id,
            "skills_count": len(self.skills),
            "performance": self.performance_metrics,
        }

    def add_skill(self, skill_id: str, skill_def: Dict[str, Any]) -> None:
        """Add a new skill to this agent."""
        self.skills[skill_id] = skill_def
        self.updated_at = datetime.now()
        logger.info(f"Agent {self.name} acquired skill: {skill_id}")

    def remove_skill(self, skill_id: str) -> None:
        """Remove a skill from this agent."""
        if skill_id in self.skills:
            del self.skills[skill_id]
            self.updated_at = datetime.now()

    def update_performance(self, success: bool, execution_time_ms: int) -> None:
        """Update performance metrics after task completion."""
        if success:
            self.performance_metrics["tasks_completed"] += 1
        else:
            self.performance_metrics["tasks_failed"] += 1

        total_tasks = (
            self.performance_metrics["tasks_completed"]
            + self.performance_metrics["tasks_failed"]
        )
        self.performance_metrics["success_rate"] = (
            self.performance_metrics["tasks_completed"] / total_tasks
            if total_tasks > 0
            else 0
        )
        self.updated_at = datetime.now()

    def set_status(self, status: str) -> None:
        """Update agent status."""
        self.status = status
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize agent to dictionary."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "specialization": self.specialization,
            "model": self.model,
            "status": self.status,
            "current_task_id": self.current_task_id,
            "skills": self.skills,
            "performance_metrics": self.performance_metrics,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

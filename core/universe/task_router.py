"""
Intelligent Task Router: Routes tasks to agents based on capabilities,
load, performance, and priority. Implements load balancing and skill matching.
"""

import uuid
import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = 5
    HIGH = 4
    NORMAL = 3
    LOW = 2
    MINIMAL = 1


class RoutingStrategy(Enum):
    """Task routing strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    BEST_FIT = "best_fit"
    WEIGHTED_SCORE = "weighted_score"
    AVAILABILITY = "availability"


class TaskDefinition:
    """Definition of a task to be routed."""

    def __init__(
        self,
        task_id: str,
        task_type: str,
        description: str,
        required_capabilities: List[str],
        priority: TaskPriority = TaskPriority.NORMAL,
        estimated_duration_ms: Optional[int] = None,
        dependencies: Optional[List[str]] = None,
        deadline: Optional[datetime] = None,
    ):
        """
        Initialize task definition.

        Args:
            task_id: Unique task ID
            task_type: Type of task
            description: Task description
            required_capabilities: Required agent capabilities
            priority: Task priority
            estimated_duration_ms: Estimated execution time
            dependencies: Task IDs this task depends on
            deadline: Optional deadline
        """
        self.task_id = task_id
        self.task_type = task_type
        self.description = description
        self.required_capabilities = required_capabilities
        self.priority = priority
        self.estimated_duration_ms = estimated_duration_ms or 5000
        self.dependencies = dependencies or []
        self.deadline = deadline
        self.created_at = datetime.now()

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "description": self.description,
            "required_capabilities": self.required_capabilities,
            "priority": self.priority.name,
            "estimated_duration_ms": self.estimated_duration_ms,
            "dependencies": self.dependencies,
            "deadline": self.deadline.isoformat() if self.deadline else None,
        }


class AgentState:
    """Track current state of an agent for routing."""

    def __init__(
        self,
        agent_id: str,
        name: str,
        role_id: str,
        capabilities: List[str],
        max_concurrent_tasks: int = 5,
        skill_level: int = 3,
    ):
        """
        Initialize agent state.

        Args:
            agent_id: Agent ID
            name: Agent name
            role_id: Agent role
            capabilities: Agent capabilities
            max_concurrent_tasks: Max concurrent tasks
            skill_level: Agent skill level (1-5)
        """
        self.agent_id = agent_id
        self.name = name
        self.role_id = role_id
        self.capabilities = set(capabilities)
        self.max_concurrent_tasks = max_concurrent_tasks
        self.skill_level = skill_level
        self.current_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.success_rate = 0.0
        self.avg_execution_time_ms = 0
        self.last_used = None

    def get_available_capacity(self) -> int:
        """Get available task slots."""
        return max(0, self.max_concurrent_tasks - self.current_tasks)

    def get_load_percentage(self) -> float:
        """Get current load as percentage."""
        return (self.current_tasks / self.max_concurrent_tasks) * 100

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role_id": self.role_id,
            "capabilities": list(self.capabilities),
            "current_tasks": self.current_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": self.success_rate,
            "load_percentage": self.get_load_percentage(),
            "available_capacity": self.get_available_capacity(),
        }


class RoutingDecision:
    """Result of routing decision."""

    def __init__(
        self,
        task_id: str,
        assigned_agent_id: str,
        agent_name: str,
        score: float,
        strategy: RoutingStrategy,
        confidence: float,
        reason: str,
    ):
        """
        Initialize routing decision.

        Args:
            task_id: Task ID
            assigned_agent_id: Assigned agent ID
            agent_name: Agent name
            score: Routing score (0-100)
            strategy: Routing strategy used
            confidence: Confidence level (0-1)
            reason: Decision reason
        """
        self.task_id = task_id
        self.assigned_agent_id = assigned_agent_id
        self.agent_name = agent_name
        self.score = score
        self.strategy = strategy
        self.confidence = confidence
        self.reason = reason
        self.created_at = datetime.now()

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "task_id": self.task_id,
            "assigned_agent_id": self.assigned_agent_id,
            "agent_name": self.agent_name,
            "score": self.score,
            "strategy": self.strategy.value,
            "confidence": self.confidence,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
        }


class TaskRouter:
    """
    Intelligent task router for agent assignment.
    Uses multiple strategies for optimal task distribution.
    """

    def __init__(self, default_strategy: RoutingStrategy = RoutingStrategy.WEIGHTED_SCORE):
        """
        Initialize router.

        Args:
            default_strategy: Default routing strategy
        """
        self.agents: Dict[str, AgentState] = {}
        self.default_strategy = default_strategy
        self.routing_history: List[RoutingDecision] = []
        self.agent_counter = {}  # For round-robin
        logger.info(f"TaskRouter initialized with strategy: {default_strategy.value}")

    def register_agent(
        self,
        agent_id: str,
        name: str,
        role_id: str,
        capabilities: List[str],
        max_concurrent_tasks: int = 5,
        skill_level: int = 3,
    ) -> bool:
        """
        Register an agent for task routing.

        Args:
            agent_id: Agent ID
            name: Agent name
            role_id: Agent role
            capabilities: Agent capabilities
            max_concurrent_tasks: Max concurrent tasks
            skill_level: Skill level (1-5)

        Returns:
            True if registered successfully
        """
        agent_state = AgentState(
            agent_id, name, role_id, capabilities, max_concurrent_tasks, skill_level
        )
        self.agents[agent_id] = agent_state
        self.agent_counter[agent_id] = 0
        logger.info(f"Registered agent {agent_id} ({name}) with role {role_id}")
        return True

    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            if agent_id in self.agent_counter:
                del self.agent_counter[agent_id]
            logger.info(f"Unregistered agent {agent_id}")
            return True
        return False

    def update_agent_state(
        self,
        agent_id: str,
        current_tasks: int,
        completed_tasks: int,
        failed_tasks: int,
        avg_execution_time_ms: float,
    ) -> bool:
        """Update agent state."""
        if agent_id not in self.agents:
            return False

        agent = self.agents[agent_id]
        agent.current_tasks = current_tasks
        agent.completed_tasks = completed_tasks
        agent.failed_tasks = failed_tasks
        agent.avg_execution_time_ms = avg_execution_time_ms

        # Calculate success rate
        total = completed_tasks + failed_tasks
        if total > 0:
            agent.success_rate = completed_tasks / total
        else:
            agent.success_rate = 1.0

        agent.last_used = datetime.now()
        return True

    def route_task(
        self,
        task: TaskDefinition,
        strategy: Optional[RoutingStrategy] = None,
    ) -> Optional[RoutingDecision]:
        """
        Route a task to an appropriate agent.

        Args:
            task: Task definition
            strategy: Optional routing strategy (uses default if not provided)

        Returns:
            Routing decision or None if no suitable agent found
        """
        strategy = strategy or self.default_strategy

        # Find capable agents
        capable_agents = self._find_capable_agents(task.required_capabilities)

        if not capable_agents:
            logger.warning(f"No agents capable of task {task.task_id}")
            return None

        # Apply strategy
        if strategy == RoutingStrategy.ROUND_ROBIN:
            decision = self._route_round_robin(task, capable_agents)
        elif strategy == RoutingStrategy.LEAST_LOADED:
            decision = self._route_least_loaded(task, capable_agents)
        elif strategy == RoutingStrategy.BEST_FIT:
            decision = self._route_best_fit(task, capable_agents)
        elif strategy == RoutingStrategy.WEIGHTED_SCORE:
            decision = self._route_weighted_score(task, capable_agents)
        elif strategy == RoutingStrategy.AVAILABILITY:
            decision = self._route_availability(task, capable_agents)
        else:
            decision = self._route_weighted_score(task, capable_agents)

        if decision:
            self.routing_history.append(decision)
            agent = self.agents[decision.assigned_agent_id]
            agent.current_tasks += 1
            logger.info(
                f"Routed task {task.task_id} to agent {decision.assigned_agent_id} "
                f"({decision.agent_name}) with score {decision.score:.2f}"
            )

        return decision

    def _find_capable_agents(self, required_capabilities: List[str]) -> List[str]:
        """Find agents with required capabilities."""
        capable = []
        for agent_id, agent in self.agents.items():
            # Check if agent has all required capabilities
            if all(cap in agent.capabilities for cap in required_capabilities):
                # Agent must have available capacity
                if agent.get_available_capacity() > 0:
                    capable.append(agent_id)
        return capable

    def _route_round_robin(
        self, task: TaskDefinition, capable_agents: List[str]
    ) -> Optional[RoutingDecision]:
        """Round-robin strategy - distributes evenly."""
        if not capable_agents:
            return None

        # Find agent with lowest counter
        selected = min(capable_agents, key=lambda a: self.agent_counter.get(a, 0))
        self.agent_counter[selected] = self.agent_counter.get(selected, 0) + 1

        agent = self.agents[selected]
        return RoutingDecision(
            task_id=task.task_id,
            assigned_agent_id=selected,
            agent_name=agent.name,
            score=80.0,
            strategy=RoutingStrategy.ROUND_ROBIN,
            confidence=0.7,
            reason="Round-robin distribution",
        )

    def _route_least_loaded(
        self, task: TaskDefinition, capable_agents: List[str]
    ) -> Optional[RoutingDecision]:
        """Least-loaded strategy - routes to agent with least load."""
        if not capable_agents:
            return None

        # Find agent with least load
        selected = min(
            capable_agents, key=lambda a: self.agents[a].get_load_percentage()
        )
        agent = self.agents[selected]

        score = 100 - agent.get_load_percentage()
        return RoutingDecision(
            task_id=task.task_id,
            assigned_agent_id=selected,
            agent_name=agent.name,
            score=score,
            strategy=RoutingStrategy.LEAST_LOADED,
            confidence=0.8,
            reason=f"Least loaded agent ({agent.get_load_percentage():.1f}% load)",
        )

    def _route_best_fit(
        self, task: TaskDefinition, capable_agents: List[str]
    ) -> Optional[RoutingDecision]:
        """Best-fit strategy - matches capability requirements closely."""
        if not capable_agents:
            return None

        best_agent = None
        best_score = -1

        for agent_id in capable_agents:
            agent = self.agents[agent_id]
            # Score based on exact capability match
            matching_caps = sum(
                1
                for cap in task.required_capabilities
                if cap in agent.capabilities
            )
            score = (matching_caps / len(task.required_capabilities)) * 100

            if score > best_score:
                best_score = score
                best_agent = agent_id

        if best_agent:
            agent = self.agents[best_agent]
            return RoutingDecision(
                task_id=task.task_id,
                assigned_agent_id=best_agent,
                agent_name=agent.name,
                score=best_score,
                strategy=RoutingStrategy.BEST_FIT,
                confidence=0.85,
                reason=f"Best capability match ({best_score:.1f}%)",
            )

        return None

    def _route_weighted_score(
        self, task: TaskDefinition, capable_agents: List[str]
    ) -> Optional[RoutingDecision]:
        """Weighted score strategy - combines multiple factors."""
        if not capable_agents:
            return None

        best_agent = None
        best_score = -1

        for agent_id in capable_agents:
            agent = self.agents[agent_id]

            # Calculate weighted score
            # 40% success rate, 30% load, 20% skill level, 10% capability match
            success_score = (
                (agent.success_rate * 40) if agent.completed_tasks > 0 else 40
            )
            load_score = (100 - agent.get_load_percentage()) * 0.30
            skill_score = (agent.skill_level / 5) * 100 * 0.20
            capability_match = (
                len(
                    [
                        c
                        for c in task.required_capabilities
                        if c in agent.capabilities
                    ]
                )
                / max(len(task.required_capabilities), 1)
            ) * 100 * 0.10

            total_score = success_score + load_score + skill_score + capability_match

            if total_score > best_score:
                best_score = total_score
                best_agent = agent_id

        if best_agent:
            agent = self.agents[best_agent]
            return RoutingDecision(
                task_id=task.task_id,
                assigned_agent_id=best_agent,
                agent_name=agent.name,
                score=min(best_score, 100.0),
                strategy=RoutingStrategy.WEIGHTED_SCORE,
                confidence=0.9,
                reason="Weighted score optimization",
            )

        return None

    def _route_availability(
        self, task: TaskDefinition, capable_agents: List[str]
    ) -> Optional[RoutingDecision]:
        """Availability strategy - prefers available agents."""
        if not capable_agents:
            return None

        # Sort by available capacity
        available_agents = sorted(
            capable_agents,
            key=lambda a: self.agents[a].get_available_capacity(),
            reverse=True,
        )

        selected = available_agents[0]
        agent = self.agents[selected]

        return RoutingDecision(
            task_id=task.task_id,
            assigned_agent_id=selected,
            agent_name=agent.name,
            score=float(agent.get_available_capacity() / agent.max_concurrent_tasks) * 100,
            strategy=RoutingStrategy.AVAILABILITY,
            confidence=0.75,
            reason=f"Available capacity: {agent.get_available_capacity()} slots",
        )

    def complete_task(
        self, agent_id: str, success: bool, actual_duration_ms: int
    ) -> bool:
        """Mark task as completed and update agent state."""
        if agent_id not in self.agents:
            return False

        agent = self.agents[agent_id]
        agent.current_tasks = max(0, agent.current_tasks - 1)

        if success:
            agent.completed_tasks += 1
        else:
            agent.failed_tasks += 1

        # Update average execution time
        total = agent.completed_tasks + agent.failed_tasks
        if total > 0:
            agent.avg_execution_time_ms = (
                (agent.avg_execution_time_ms * (total - 1) + actual_duration_ms)
                / total
            )

        return True

    def get_agent_stats(self, agent_id: str) -> Optional[Dict]:
        """Get statistics for an agent."""
        agent = self.agents.get(agent_id)
        if agent:
            return agent.to_dict()
        return None

    def get_all_agents_stats(self) -> List[Dict]:
        """Get statistics for all agents."""
        return [agent.to_dict() for agent in self.agents.values()]

    def get_routing_stats(self) -> Dict:
        """Get routing statistics."""
        strategy_counts = {}
        for decision in self.routing_history:
            strategy = decision.strategy.value
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

        avg_score = (
            sum(d.score for d in self.routing_history) / len(self.routing_history)
            if self.routing_history
            else 0
        )
        avg_confidence = (
            sum(d.confidence for d in self.routing_history)
            / len(self.routing_history)
            if self.routing_history
            else 0
        )

        return {
            "total_routings": len(self.routing_history),
            "strategy_distribution": strategy_counts,
            "average_score": avg_score,
            "average_confidence": avg_confidence,
            "agents_registered": len(self.agents),
        }

    def get_routing_history(self, limit: int = 50) -> List[Dict]:
        """Get recent routing history."""
        return [
            d.to_dict() for d in self.routing_history[-limit:]
        ]


# Global router instance
_router = None


def get_router() -> TaskRouter:
    """Get or create the global task router."""
    global _router
    if _router is None:
        _router = TaskRouter()
    return _router

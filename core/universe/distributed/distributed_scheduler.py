"""
Distributed Scheduler - Task scheduling with work-stealing and load balancing

Provides:
- Distributed task queue
- Work stealing algorithm
- Load balancing
- Task affinity support
- SLA enforcement
"""

import asyncio
import heapq
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Callable, Optional, Any, Tuple, Set
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    DEFERRED = 4


class TaskStatus(Enum):
    """Status of a task."""
    PENDING = "pending"
    QUEUED = "queued"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class TaskSLA:
    """Service Level Agreement for a task."""
    max_duration_ms: int = 5000
    max_retries: int = 3
    timeout_ms: int = 10000
    priority: TaskPriority = TaskPriority.NORMAL


@dataclass
class DistributedTask:
    """Task in the distributed scheduler."""
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    sla: TaskSLA
    status: TaskStatus
    assigned_agent_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    affinity_tags: Set[str] = field(default_factory=set)
    dependencies: List[str] = field(default_factory=list)

    def __lt__(self, other: 'DistributedTask') -> bool:
        """Comparison for priority queue."""
        if self.sla.priority.value != other.sla.priority.value:
            return self.sla.priority.value < other.sla.priority.value
        return self.created_at < other.created_at

    def is_overdue(self) -> bool:
        """Check if task has exceeded SLA."""
        if self.started_at is None:
            elapsed = time.time() - self.created_at
            # Queue timeout
            return elapsed > (self.sla.timeout_ms / 1000.0)
        else:
            elapsed = time.time() - self.started_at
            return elapsed > (self.sla.max_duration_ms / 1000.0)

    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return self.retry_count < self.sla.max_retries


@dataclass
class AgentCapacity:
    """Capacity information for an agent."""
    agent_id: str
    max_capacity: int
    current_load: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    avg_task_duration_ms: float = 0.0
    supported_task_types: Set[str] = field(default_factory=set)
    affinity_tags: Set[str] = field(default_factory=set)

    def get_available_capacity(self) -> int:
        """Get available capacity."""
        return self.max_capacity - self.current_load

    def get_utilization(self) -> float:
        """Get utilization percentage."""
        return self.current_load / self.max_capacity if self.max_capacity > 0 else 0.0


class WorkStealingAlgorithm:
    """Work stealing algorithm for load balancing."""

    def __init__(self, steal_threshold: float = 0.75):
        self.steal_threshold = steal_threshold
        self.steal_history: Dict[str, List[float]] = defaultdict(list)

    def should_steal(self, agent_id: str, agent_load: float, global_avg_load: float) -> bool:
        """Determine if an agent should steal work."""
        if agent_load > self.steal_threshold:
            return False
        if global_avg_load < 0.5:
            return False
        return agent_load < global_avg_load * 0.5

    def find_victim_agent(
        self,
        agents: Dict[str, AgentCapacity],
        stealing_agent_id: str
    ) -> Optional[str]:
        """Find agent with most work to steal from."""
        candidates = []
        for agent_id, capacity in agents.items():
            if agent_id != stealing_agent_id and capacity.current_load > 0:
                candidates.append((capacity.current_load, agent_id))

        if not candidates:
            return None

        candidates.sort(reverse=True)
        return candidates[0][1]

    def record_steal(self, agent_id: str) -> None:
        """Record a work steal event."""
        self.steal_history[agent_id].append(time.time())
        # Keep only recent history (last 100 events or last 5 minutes)
        cutoff_time = time.time() - 300
        self.steal_history[agent_id] = [
            t for t in self.steal_history[agent_id] if t > cutoff_time
        ]


class DistributedScheduler:
    """Distributed task scheduler with work-stealing and load balancing."""

    def __init__(self, work_stealing_enabled: bool = True):
        self.task_queue: List[DistributedTask] = []
        self.tasks_by_id: Dict[str, DistributedTask] = {}
        self.agent_capacities: Dict[str, AgentCapacity] = {}
        self.work_stealer = WorkStealingAlgorithm() if work_stealing_enabled else None
        
        # Task affinity and dependencies
        self.task_affinity_map: Dict[str, Set[str]] = defaultdict(set)  # tag -> task_ids
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self.task_completion_callbacks: Dict[str, List[Callable]] = defaultdict(list)

        # Scheduling metrics
        self.total_scheduled = 0
        self.total_completed = 0
        self.total_failed = 0
        self.scheduling_start_time = time.time()

    def register_agent(
        self,
        agent_id: str,
        max_capacity: int,
        supported_task_types: Set[str] = None,
        affinity_tags: Set[str] = None
    ) -> AgentCapacity:
        """Register an agent with the scheduler."""
        capacity = AgentCapacity(
            agent_id=agent_id,
            max_capacity=max_capacity,
            supported_task_types=supported_task_types or set(),
            affinity_tags=affinity_tags or set()
        )
        self.agent_capacities[agent_id] = capacity
        logger.info(f"Registered agent {agent_id} with capacity {max_capacity}")
        return capacity

    def submit_task(
        self,
        task_type: str,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        sla: Optional[TaskSLA] = None,
        affinity_tags: Optional[Set[str]] = None,
        dependencies: Optional[List[str]] = None
    ) -> str:
        """Submit a new task to the scheduler."""
        task_id = str(uuid.uuid4())
        sla = sla or TaskSLA(priority=priority)

        task = DistributedTask(
            task_id=task_id,
            task_type=task_type,
            payload=payload,
            sla=sla,
            status=TaskStatus.PENDING,
            affinity_tags=affinity_tags or set(),
            dependencies=dependencies or []
        )

        heapq.heappush(self.task_queue, task)
        self.tasks_by_id[task_id] = task
        self.total_scheduled += 1

        # Record affinity mappings
        for tag in task.affinity_tags:
            self.task_affinity_map[tag].add(task_id)

        # Record dependencies
        for dep_id in task.dependencies:
            self.dependency_graph[dep_id].add(task_id)

        logger.debug(f"Submitted task {task_id} of type {task_type}")
        return task_id

    def get_best_agent_for_task(self, task: DistributedTask) -> Optional[str]:
        """Find the best agent to execute a task."""
        candidates = []

        for agent_id, capacity in self.agent_capacities.items():
            # Skip if agent doesn't support task type
            if capacity.supported_task_types and task.task_type not in capacity.supported_task_types:
                continue

            # Skip if no available capacity
            if capacity.get_available_capacity() <= 0:
                continue

            # Score based on affinity match
            affinity_score = len(task.affinity_tags & capacity.affinity_tags)

            # Score based on availability (lower load is better)
            availability_score = capacity.get_available_capacity()

            # Score based on task success rate
            total_tasks = capacity.completed_tasks + capacity.failed_tasks
            success_rate = (capacity.completed_tasks / total_tasks) if total_tasks > 0 else 1.0

            # Combined score (higher is better)
            score = (affinity_score * 100) + availability_score + (success_rate * 50)
            candidates.append((score, agent_id))

        if not candidates:
            return None

        candidates.sort(reverse=True)
        return candidates[0][1]

    async def schedule_task(self, task: DistributedTask) -> bool:
        """Schedule a task to an agent."""
        # Check dependencies
        for dep_id in task.dependencies:
            if dep_id in self.tasks_by_id:
                dep_task = self.tasks_by_id[dep_id]
                if dep_task.status != TaskStatus.COMPLETED:
                    logger.debug(f"Task {task.task_id} waiting for dependency {dep_id}")
                    return False

        # Find best agent
        agent_id = self.get_best_agent_for_task(task)
        if not agent_id:
            logger.warning(f"No suitable agent for task {task.task_id}")
            return False

        # Assign task
        task.assigned_agent_id = agent_id
        task.status = TaskStatus.ASSIGNED
        self.agent_capacities[agent_id].current_load += 1

        logger.info(f"Scheduled task {task.task_id} to agent {agent_id}")
        return True

    async def complete_task(
        self,
        task_id: str,
        result: Any = None,
        error: Optional[str] = None
    ) -> bool:
        """Mark a task as completed."""
        if task_id not in self.tasks_by_id:
            return False

        task = self.tasks_by_id[task_id]
        task.completed_at = time.time()
        task.result = result
        task.error = error

        if error:
            task.status = TaskStatus.FAILED
            self.total_failed += 1
            if task.assigned_agent_id and task.assigned_agent_id in self.agent_capacities:
                self.agent_capacities[task.assigned_agent_id].failed_tasks += 1
        else:
            task.status = TaskStatus.COMPLETED
            self.total_completed += 1
            if task.assigned_agent_id and task.assigned_agent_id in self.agent_capacities:
                agent = self.agent_capacities[task.assigned_agent_id]
                agent.completed_tasks += 1
                # Update average task duration
                duration_ms = (task.completed_at - (task.started_at or task.created_at)) * 1000
                if agent.avg_task_duration_ms == 0:
                    agent.avg_task_duration_ms = duration_ms
                else:
                    agent.avg_task_duration_ms = (agent.avg_task_duration_ms + duration_ms) / 2

        # Reduce agent load
        if task.assigned_agent_id and task.assigned_agent_id in self.agent_capacities:
            self.agent_capacities[task.assigned_agent_id].current_load = max(
                0, self.agent_capacities[task.assigned_agent_id].current_load - 1
            )

        # Trigger dependent tasks
        for dependent_id in self.dependency_graph.get(task_id, set()):
            if dependent_id in self.tasks_by_id:
                dependent_task = self.tasks_by_id[dependent_id]
                if dependent_task.status == TaskStatus.PENDING:
                    await self.schedule_task(dependent_task)

        # Call registered callbacks
        for callback in self.task_completion_callbacks[task_id]:
            try:
                result_val = callback(task)
                if asyncio.iscoroutine(result_val):
                    await result_val
            except Exception as e:
                logger.error(f"Error in task completion callback: {e}")

        logger.info(f"Task {task_id} completed with status {task.status.value}")
        return True

    def register_task_callback(self, task_id: str, callback: Callable) -> None:
        """Register a callback for task completion."""
        self.task_completion_callbacks[task_id].append(callback)

    async def retry_task(self, task_id: str) -> bool:
        """Retry a failed task."""
        if task_id not in self.tasks_by_id:
            return False

        task = self.tasks_by_id[task_id]
        if not task.can_retry():
            logger.warning(f"Task {task_id} has exceeded max retries")
            return False

        task.retry_count += 1
        task.status = TaskStatus.RETRYING
        task.assigned_agent_id = None
        return await self.schedule_task(task)

    def get_pending_tasks(self, limit: int = 10) -> List[DistributedTask]:
        """Get pending tasks ready for scheduling."""
        pending = [
            task for task in self.task_queue
            if task.status in (TaskStatus.PENDING, TaskStatus.RETRYING)
        ]
        return sorted(pending, key=lambda t: (t.sla.priority.value, t.created_at))[:limit]

    def get_overdue_tasks(self) -> List[DistributedTask]:
        """Get tasks that have exceeded their SLA."""
        return [task for task in self.tasks_by_id.values() if task.is_overdue()]

    def get_agent_load(self) -> Dict[str, float]:
        """Get load for each agent."""
        return {
            agent_id: capacity.get_utilization()
            for agent_id, capacity in self.agent_capacities.items()
        }

    def get_global_average_load(self) -> float:
        """Get global average load across all agents."""
        if not self.agent_capacities:
            return 0.0
        loads = self.get_agent_load()
        return sum(loads.values()) / len(loads)

    def suggest_work_steal(self) -> Optional[Tuple[str, str]]:
        """Suggest a work steal operation using work-stealing algorithm."""
        if not self.work_stealer:
            return None

        global_avg = self.get_global_average_load()
        loads = self.get_agent_load()

        for agent_id, load in loads.items():
            if self.work_stealer.should_steal(agent_id, load, global_avg):
                victim = self.work_stealer.find_victim_agent(self.agent_capacities, agent_id)
                if victim:
                    return (agent_id, victim)

        return None

    def get_scheduler_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        uptime_s = time.time() - self.scheduling_start_time
        throughput = self.total_completed / max(uptime_s, 1)

        return {
            'total_scheduled': self.total_scheduled,
            'total_completed': self.total_completed,
            'total_failed': self.total_failed,
            'pending_tasks': len(self.task_queue),
            'throughput_per_sec': throughput,
            'uptime_seconds': uptime_s,
            'agent_count': len(self.agent_capacities),
            'global_avg_load': self.get_global_average_load(),
            'overdue_tasks': len(self.get_overdue_tasks()),
        }

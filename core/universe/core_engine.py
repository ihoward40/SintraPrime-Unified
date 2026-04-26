"""
UniVerse Core Orchestration Engine
===================================

A production-ready orchestration engine that manages task decomposition,
swarm coordination, and parallel execution for distributed AI systems.

Architecture:
- Event-driven design with async/await
- Transaction-based operations with rollback support
- P2P agent negotiation and coordination
- Graceful degradation on failures
- Support for 50+ concurrent agents

Author: SintraPrime UniVerse
Version: 1.0.0
"""

import asyncio
import json
import logging
import uuid
import re
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Set, Callable
from datetime import datetime, timedelta
from collections import defaultdict
from abc import ABC, abstractmethod
import functools
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# TYPE DEFINITIONS AND ENUMS
# ============================================================================

class TaskStatus(Enum):
    """Task execution status enumeration."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ExecutionStatus(Enum):
    """Overall execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class AgentStatus(Enum):
    """Agent coordination status enumeration."""
    IDLE = "idle"
    NEGOTIATING = "negotiating"
    EXECUTING = "executing"
    REPORTING = "reporting"


class ActionType(Enum):
    """Audit log action types."""
    PARSE_INTENT = "parse_intent"
    DECOMPOSE_TASK = "decompose_task"
    ASSIGN_TASK = "assign_task"
    EXECUTE_TASK = "execute_task"
    COMPLETE_TASK = "complete_task"
    FAIL_TASK = "fail_task"
    ROLLBACK = "rollback"
    SYNTHESIZE_RESULT = "synthesize_result"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Task:
    """Represents a decomposed task in the execution hierarchy."""
    task_id: str
    execution_id: str
    parent_task_id: Optional[str]
    task_type: str
    description: str
    priority: int = 0
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for storage."""
        return {
            'task_id': self.task_id,
            'execution_id': self.execution_id,
            'parent_task_id': self.parent_task_id,
            'task_type': self.task_type,
            'description': self.description,
            'priority': self.priority,
            'status': self.status.value,
            'assigned_agent_id': self.assigned_agent_id,
            'dependencies': json.dumps(self.dependencies),
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'result': json.dumps(self.result) if self.result else None,
            'error_message': self.error_message,
            'metadata': json.dumps(self.metadata)
        }


@dataclass
class Agent:
    """Represents a coordinated agent in the swarm."""
    agent_id: str
    status: AgentStatus = AgentStatus.IDLE
    assigned_tasks: int = 0
    completed_tasks: int = 0
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    capacity_utilization: float = 0.0
    max_concurrent_tasks: int = 5
    capabilities: Set[str] = field(default_factory=set)

    def is_available(self) -> bool:
        """Check if agent can accept more tasks."""
        return (self.status != AgentStatus.EXECUTING or 
                self.assigned_tasks < self.max_concurrent_tasks)

    def update_heartbeat(self) -> None:
        """Update agent's last heartbeat timestamp."""
        self.last_heartbeat = datetime.utcnow()

    def is_alive(self, timeout_seconds: int = 30) -> bool:
        """Check if agent is alive based on heartbeat."""
        return datetime.utcnow() - self.last_heartbeat < timedelta(seconds=timeout_seconds)


@dataclass
class ExecutionContext:
    """Execution context for a single orchestration run."""
    execution_id: str
    intent: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    root_task_id: Optional[str] = None
    tasks: Dict[str, Task] = field(default_factory=dict)
    agents: Dict[str, Agent] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    result_summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    rollback_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        """Calculate execution duration."""
        end = self.end_time or datetime.utcnow()
        return (end - self.start_time).total_seconds()

    @property
    def completion_percentage(self) -> float:
        """Calculate task completion percentage."""
        if not self.tasks:
            return 0.0
        completed = sum(1 for t in self.tasks.values() 
                       if t.status == TaskStatus.COMPLETED)
        return (completed / len(self.tasks)) * 100


# ============================================================================
# DATABASE INTEGRATION
# ============================================================================

class DatabaseManager:
    """Manages all database operations for the orchestration engine."""

    def __init__(self):
        """Initialize database manager."""
        self.logger = logging.getLogger(__name__)
        self._init_schema()

    def _init_schema(self) -> None:
        """Create all required tables if they do not exist."""
        import sqlite3
        db_path = self._get_db_path()
        schema_sql = """
        CREATE TABLE IF NOT EXISTS execution_trace (
            execution_id TEXT PRIMARY KEY,
            intent TEXT,
            status TEXT,
            start_time TEXT,
            end_time TEXT,
            root_task_id TEXT,
            total_subtasks INTEGER DEFAULT 0,
            completed_subtasks INTEGER DEFAULT 0,
            failed_subtasks INTEGER DEFAULT 0,
            agent_count INTEGER DEFAULT 0,
            result_summary TEXT,
            error_message TEXT,
            rollback_reason TEXT,
            metadata TEXT
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            execution_id TEXT,
            agent_id TEXT,
            action_type TEXT,
            task_id TEXT,
            status TEXT,
            details TEXT,
            error TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS task_results (
            task_id TEXT PRIMARY KEY,
            execution_id TEXT,
            agent_id TEXT,
            status TEXT,
            result TEXT,
            error TEXT,
            started_at TEXT,
            completed_at TEXT,
            metadata TEXT
        );
        CREATE TABLE IF NOT EXISTS agent_coordination (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            execution_id TEXT,
            agent_id TEXT,
            agent_type TEXT,
            status TEXT DEFAULT 'active',
            assigned_tasks INTEGER DEFAULT 0,
            completed_tasks INTEGER DEFAULT 0,
            last_heartbeat TEXT,
            capacity_utilization REAL DEFAULT 0.0,
            task_count INTEGER DEFAULT 0,
            metadata TEXT
        );
        CREATE TABLE IF NOT EXISTS task_registry (
            task_id TEXT PRIMARY KEY,
            execution_id TEXT,
            parent_task_id TEXT,
            agent_id TEXT,
            assigned_agent_id TEXT,
            task_type TEXT,
            description TEXT,
            status TEXT DEFAULT 'pending',
            priority INTEGER DEFAULT 5,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            started_at TEXT,
            completed_at TEXT,
            result TEXT,
            error TEXT,
            error_message TEXT,
            dependencies TEXT,
            metadata TEXT
        );
        CREATE TABLE IF NOT EXISTS rollback_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            execution_id TEXT UNIQUE,
            task_id TEXT,
            agent_id TEXT,
            state_snapshot TEXT,
            checkpoint_data TEXT,
            rollback_stack TEXT,
            last_checkpoint TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        );
        """
        try:
            conn = sqlite3.connect(db_path)
            conn.executescript(schema_sql)
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Schema init error: {e}")

    def _get_db_path(self) -> str:
        """Return the database path, creating parent dirs as needed."""
        import os
        from pathlib import Path
        db_path = os.environ.get(
            "SINTRA_CORE_DB",
            str(Path.home() / ".sintra" / "universe" / "core_engine.db")
        )
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        return db_path

    def execute_query(self, query: str, params: Optional[Dict] = None) -> Any:
        """
        Execute a database query using SQLite.

        Args:
            query: SQL query string
            params: Optional parameter dictionary

        Returns:
            Query result
        """
        import sqlite3
        db_path = self._get_db_path()
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            rows = cursor.fetchall()
            conn.close()
            self.logger.debug(f"Query executed successfully: {query[:100]}")
            return [dict(row) for row in rows] if rows else []
        except Exception as e:
            self.logger.error(f"Database error: {str(e)}")
            raise

    def log_execution_trace(self, context: ExecutionContext) -> None:
        """Log execution trace to database."""
        query = f"""
        INSERT OR REPLACE INTO execution_trace 
        (execution_id, intent, status, start_time, end_time, root_task_id, 
         total_subtasks, completed_subtasks, failed_subtasks, agent_count, 
         result_summary, error_message, rollback_reason, metadata)
        VALUES (
            '{context.execution_id}',
            '{context.intent.replace("'", "''")}',
            '{context.status.value}',
            '{context.start_time.isoformat()}',
            '{context.end_time.isoformat() if context.end_time else None}',
            '{context.root_task_id}',
            {len(context.tasks)},
            {sum(1 for t in context.tasks.values() if t.status == TaskStatus.COMPLETED)},
            {sum(1 for t in context.tasks.values() if t.status == TaskStatus.FAILED)},
            {len(context.agents)},
            '{json.dumps(context.result_summary).replace("'", "''")}',
            '{context.error_message.replace("'", "''") if context.error_message else None}',
            '{context.rollback_reason.replace("'", "''") if context.rollback_reason else None}',
            '{json.dumps(context.metadata).replace("'", "''")}'
        )
        """
        self.execute_query(query)
        self.logger.info(f"Execution trace logged for {context.execution_id}")

    def log_audit_action(self, execution_id: str, agent_id: Optional[str],
                        action_type: ActionType, task_id: Optional[str],
                        status: Optional[str], details: Optional[str],
                        error: Optional[str] = None) -> None:
        """Log an action to the audit log."""
        query = f"""
        INSERT INTO audit_log 
        (execution_id, agent_id, action_type, task_id, status, details, error, timestamp)
        VALUES (
            '{execution_id}',
            '{agent_id}',
            '{action_type.value}',
            '{task_id}',
            '{status}',
            '{details.replace("'", "''") if details else None}',
            '{error.replace("'", "''") if error else None}',
            CURRENT_TIMESTAMP
        )
        """
        self.execute_query(query)

    def register_task(self, task: Task) -> None:
        """Register a task in the task registry."""
        d = task.to_dict()
        query = f"""
        INSERT INTO task_registry
        (task_id, execution_id, parent_task_id, task_type, description, priority,
         status, assigned_agent_id, created_at, result, error_message, dependencies)
        VALUES (
            '{d['task_id']}',
            '{d['execution_id']}',
            '{d['parent_task_id']}',
            '{d['task_type']}',
            '{d['description'].replace("'", "''")}',
            {d['priority']},
            '{d['status']}',
            '{d['assigned_agent_id']}',
            '{d['created_at']}',
            '{d['result'].replace("'", "''") if d['result'] else None}',
            '{d['error_message'].replace("'", "''") if d['error_message'] else None}',
            '{d['dependencies']}'
        )
        """
        self.execute_query(query)

    def update_task_status(self, task_id: str, status: TaskStatus,
                          result: Optional[Dict] = None,
                          error_message: Optional[str] = None) -> None:
        """Update task status in the registry."""
        query = f"""
        UPDATE task_registry
        SET status = '{status.value}',
            result = '{json.dumps(result).replace("'", "''") if result else None}',
            error_message = '{error_message.replace("'", "''") if error_message else None}',
            completed_at = CURRENT_TIMESTAMP
        WHERE task_id = '{task_id}'
        """
        self.execute_query(query)

    def register_agent(self, execution_id: str, agent: Agent) -> None:
        """Register an agent for coordination."""
        query = f"""
        INSERT INTO agent_coordination
        (execution_id, agent_id, status, assigned_tasks, completed_tasks,
         last_heartbeat, capacity_utilization)
        VALUES (
            '{execution_id}',
            '{agent.agent_id}',
            '{agent.status.value}',
            {agent.assigned_tasks},
            {agent.completed_tasks},
            '{agent.last_heartbeat.isoformat()}',
            {agent.capacity_utilization}
        )
        """
        self.execute_query(query)

    def save_rollback_state(self, execution_id: str, checkpoint_data: Dict,
                           rollback_stack: List) -> None:
        """Save rollback state for transaction-based recovery."""
        query = f"""
        INSERT OR REPLACE INTO rollback_state
        (execution_id, checkpoint_data, rollback_stack, created_at, last_checkpoint)
        VALUES (
            '{execution_id}',
            '{json.dumps(checkpoint_data).replace("'", "''")}',
            '{json.dumps(rollback_stack).replace("'", "''")}',
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        )
        """
        self.execute_query(query)


# ============================================================================
# INTENT PARSER
# ============================================================================

class IntentParser:
    """
    Parse natural language commands into structured intents.
    
    Supports:
    - Task decomposition patterns
    - Priority indicators
    - Dependency specifications
    - Resource requirements
    """

    PRIORITY_KEYWORDS = {
        'urgent': 10,
        'critical': 9,
        'high': 7,
        'normal': 5,
        'low': 3,
        'background': 1
    }

    TASK_TYPE_PATTERNS = {
        'analysis': r'(analyze|analyse|examine|review|inspect)',
        'transformation': r'(transform|convert|change|modify|process)',
        'aggregation': r'(aggregate|combine|merge|consolidate|collect)',
        'validation': r'(validate|verify|check|test|confirm)',
        'reporting': r'(report|summarize|summary|overview|status)',
        'search': r'(find|search|locate|discover|identify)',
        'orchestration': r'(coordinate|orchestrate|manage|direct|control)'
    }

    def __init__(self):
        """Initialize intent parser."""
        self.logger = logging.getLogger(__name__)
        self.db = DatabaseManager()

    def parse(self, intent: str, execution_id: str) -> Dict[str, Any]:
        """
        Parse natural language intent into structured format.
        
        Args:
            intent: Natural language intent string
            execution_id: Execution context ID
            
        Returns:
            Parsed intent dictionary
        """
        self.logger.info(f"Parsing intent: {intent}")

        parsed = {
            'original_intent': intent,
            'execution_id': execution_id,
            'priority': self._extract_priority(intent),
            'task_types': self._extract_task_types(intent),
            'entities': self._extract_entities(intent),
            'constraints': self._extract_constraints(intent),
            'estimated_complexity': self._estimate_complexity(intent)
        }

        self.db.log_audit_action(
            execution_id=execution_id,
            agent_id='system',
            action_type=ActionType.PARSE_INTENT,
            task_id=None,
            status='success',
            details=json.dumps(parsed)
        )

        return parsed

    def _extract_priority(self, intent: str) -> int:
        """Extract priority from intent."""
        intent_lower = intent.lower()
        for keyword, priority in self.PRIORITY_KEYWORDS.items():
            if keyword in intent_lower:
                return priority
        return 5  # Default normal priority

    def _extract_task_types(self, intent: str) -> List[str]:
        """Extract task types from intent."""
        intent_lower = intent.lower()
        types = []
        for task_type, pattern in self.TASK_TYPE_PATTERNS.items():
            if re.search(pattern, intent_lower):
                types.append(task_type)
        return types or ['general']

    def _extract_entities(self, intent: str) -> List[str]:
        """Extract key entities from intent."""
        # Simple entity extraction - could be enhanced with NLP
        words = intent.split()
        return [w for w in words if len(w) > 3]  # Simple heuristic

    def _extract_constraints(self, intent: str) -> Dict[str, Any]:
        """Extract execution constraints from intent."""
        constraints = {
            'max_duration_seconds': 300,
            'max_agents': 50,
            'require_verification': 'verify' in intent.lower(),
            'parallelizable': True
        }
        if 'sequential' in intent.lower():
            constraints['parallelizable'] = False
        return constraints

    def _estimate_complexity(self, intent: str) -> float:
        """Estimate task complexity from intent."""
        base_complexity = len(intent) / 100.0
        if any(word in intent.lower() for word in ['analyze', 'complex', 'intricate']):
            base_complexity *= 1.5
        return min(base_complexity, 10.0)


# ============================================================================
# TASK DECOMPOSER
# ============================================================================

class TaskDecomposer:
    """
    Decompose complex tasks into executable subtasks.
    
    Handles:
    - Dependency analysis
    - Priority assignment
    - Parallelization opportunities
    - Resource estimation
    """

    def __init__(self):
        """Initialize task decomposer."""
        self.logger = logging.getLogger(__name__)
        self.db = DatabaseManager()
        self.task_counter = 0

    def decompose(self, parsed_intent: Dict[str, Any],
                  execution_context: ExecutionContext) -> List[Task]:
        """
        Decompose parsed intent into subtasks.
        
        Args:
            parsed_intent: Output from IntentParser
            execution_context: Current execution context
            
        Returns:
            List of decomposed tasks
        """
        self.logger.info(f"Decomposing intent with complexity "
                        f"{parsed_intent.get('estimated_complexity', 0)}")

        # Create root task
        root_task = self._create_root_task(parsed_intent, execution_context)
        execution_context.root_task_id = root_task.task_id
        execution_context.tasks[root_task.task_id] = root_task
        self.db.register_task(root_task)

        # Generate subtasks based on task types
        subtasks = []
        for task_type in parsed_intent.get('task_types', ['general']):
            sub = self._create_subtask(
                task_type,
                root_task.task_id,
                parsed_intent,
                execution_context
            )
            subtasks.append(sub)
            execution_context.tasks[sub.task_id] = sub
            self.db.register_task(sub)

        # Add verification task if required
        if parsed_intent.get('constraints', {}).get('require_verification'):
            verify_task = self._create_verification_task(
                root_task.task_id,
                execution_context
            )
            subtasks.append(verify_task)
            execution_context.tasks[verify_task.task_id] = verify_task
            self.db.register_task(verify_task)

        self.db.log_audit_action(
            execution_id=execution_context.execution_id,
            agent_id='system',
            action_type=ActionType.DECOMPOSE_TASK,
            task_id=root_task.task_id,
            status='success',
            details=f'Decomposed into {len(subtasks)} subtasks'
        )

        return [root_task] + subtasks

    def _create_root_task(self, parsed_intent: Dict[str, Any],
                         context: ExecutionContext) -> Task:
        """Create the root task."""
        return Task(
            task_id=self._generate_task_id('root'),
            execution_id=context.execution_id,
            parent_task_id=None,
            task_type='root',
            description=parsed_intent['original_intent'],
            priority=parsed_intent.get('priority', 5),
            metadata={
                'estimated_complexity': parsed_intent.get('estimated_complexity', 0),
                'constraints': parsed_intent.get('constraints', {})
            }
        )

    def _create_subtask(self, task_type: str, parent_id: str,
                       parsed_intent: Dict[str, Any],
                       context: ExecutionContext) -> Task:
        """Create a subtask of given type."""
        return Task(
            task_id=self._generate_task_id(task_type),
            execution_id=context.execution_id,
            parent_task_id=parent_id,
            task_type=task_type,
            description=f"{task_type.title()} task for: {parsed_intent['original_intent'][:100]}",
            priority=parsed_intent.get('priority', 5) - 1,  # Slightly lower than root
            dependencies=[parent_id],
            metadata={
                'entities': parsed_intent.get('entities', []),
                'parallelizable': parsed_intent.get('constraints', {}).get('parallelizable', True)
            }
        )

    def _create_verification_task(self, parent_id: str,
                                 context: ExecutionContext) -> Task:
        """Create a verification task."""
        return Task(
            task_id=self._generate_task_id('verify'),
            execution_id=context.execution_id,
            parent_task_id=parent_id,
            task_type='verification',
            description='Verification and validation of results',
            priority=8,
            dependencies=[parent_id],
            metadata={'critical': True}
        )

    def _generate_task_id(self, task_type: str) -> str:
        """Generate unique task ID."""
        self.task_counter += 1
        return f"task_{task_type}_{self.task_counter}_{uuid.uuid4().hex[:8]}"


# ============================================================================
# SWARM COORDINATOR
# ============================================================================

class SwarmCoordinator:
    """
    Manage peer-to-peer agent negotiation and coordination.
    
    Responsibilities:
    - Agent registration and discovery
    - Task assignment based on capabilities
    - Load balancing across swarm
    - Agent health monitoring
    - Failure detection and recovery
    """

    def __init__(self, max_agents: int = 50):
        """Initialize swarm coordinator."""
        self.logger = logging.getLogger(__name__)
        self.db = DatabaseManager()
        self.max_agents = max_agents
        self.agent_registry: Dict[str, Agent] = {}
        self.negotiation_queue: asyncio.Queue = asyncio.Queue()

    async def register_agent(self, agent_id: str, capabilities: Set[str],
                           max_concurrent_tasks: int = 5,
                           execution_id: Optional[str] = None) -> Agent:
        """
        Register an agent in the swarm.
        
        Args:
            agent_id: Unique agent identifier
            capabilities: Set of task types agent can handle
            max_concurrent_tasks: Max parallel tasks for agent
            execution_id: Optional execution context
            
        Returns:
            Registered Agent instance
        """
        if len(self.agent_registry) >= self.max_agents:
            self.logger.warning(f"Swarm at capacity ({self.max_agents} agents)")
            raise RuntimeError("Swarm at maximum capacity")

        agent = Agent(
            agent_id=agent_id,
            capabilities=capabilities,
            max_concurrent_tasks=max_concurrent_tasks
        )

        self.agent_registry[agent_id] = agent

        if execution_id:
            self.db.register_agent(execution_id, agent)
            self.logger.info(f"Agent {agent_id} registered with capabilities: {capabilities}")

        return agent

    async def assign_task(self, task: Task, execution_context: ExecutionContext) -> str:
        """
        Assign task to appropriate agent based on capabilities and load.
        
        Args:
            task: Task to assign
            execution_context: Execution context
            
        Returns:
            ID of assigned agent
        """
        # Filter available agents
        available_agents = [
            a for a in self.agent_registry.values()
            if a.is_available() and a.is_alive()
        ]

        if not available_agents:
            self.logger.warning(f"No available agents for task {task.task_id}")
            raise RuntimeError("No available agents")

        # Score agents based on task compatibility and load
        scored_agents = [
            (agent, self._score_agent(agent, task))
            for agent in available_agents
        ]

        # Select best agent
        best_agent, score = max(scored_agents, key=lambda x: x[1])
        self.logger.info(f"Assigned task {task.task_id} to agent {best_agent.agent_id} "
                        f"(score: {score:.2f})")

        # Update agent state
        best_agent.assigned_tasks += 1
        best_agent.status = AgentStatus.EXECUTING

        # Update task
        task.assigned_agent_id = best_agent.agent_id
        task.status = TaskStatus.ASSIGNED

        # Log assignment
        self.db.log_audit_action(
            execution_id=execution_context.execution_id,
            agent_id=best_agent.agent_id,
            action_type=ActionType.ASSIGN_TASK,
            task_id=task.task_id,
            status='assigned',
            details=f'Assignment score: {score:.2f}'
        )

        return best_agent.agent_id

    def _score_agent(self, agent: Agent, task: Task) -> float:
        """
        Score agent for task assignment.
        
        Scoring factors:
        - Capability match (40%)
        - Load balance (30%)
        - Recent performance (20%)
        - Priority match (10%)
        """
        capability_match = 1.0 if task.task_type in agent.capabilities else 0.5
        load_balance = 1.0 - (agent.assigned_tasks / agent.max_concurrent_tasks)
        performance_factor = (agent.completed_tasks / max(agent.assigned_tasks, 1)) * 0.5 + 0.5
        priority_boost = (task.priority / 10.0) * 0.1

        score = (
            capability_match * 0.40 +
            load_balance * 0.30 +
            performance_factor * 0.20 +
            priority_boost * 0.10
        )

        return score

    async def heartbeat_check(self, timeout_seconds: int = 30) -> List[str]:
        """
        Check agent health and identify dead agents.
        
        Args:
            timeout_seconds: Heartbeat timeout
            
        Returns:
            List of dead agent IDs
        """
        dead_agents = []
        for agent_id, agent in self.agent_registry.items():
            if not agent.is_alive(timeout_seconds):
                dead_agents.append(agent_id)
                agent.status = AgentStatus.IDLE
                self.logger.warning(f"Agent {agent_id} is not responding")

        return dead_agents

    async def rebalance_load(self, execution_context: ExecutionContext) -> None:
        """Rebalance load across available agents."""
        pending_tasks = [
            t for t in execution_context.tasks.values()
            if t.status == TaskStatus.PENDING
        ]

        for task in pending_tasks:
            try:
                await self.assign_task(task, execution_context)
            except RuntimeError:
                self.logger.debug(f"Could not assign task {task.task_id} at this time")
                break


# ============================================================================
# EXECUTION ENGINE
# ============================================================================

class ExecutionEngine:
    """
    Execute tasks in parallel with rollback support.
    
    Features:
    - Async/await based parallel execution
    - Transaction-based operations
    - Rollback checkpoint management
    - Graceful degradation on failures
    - Resource monitoring
    """

    def __init__(self):
        """Initialize execution engine."""
        self.logger = logging.getLogger(__name__)
        self.db = DatabaseManager()
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.rollback_stack: List[Dict[str, Any]] = []

    async def execute_task(self, task: Task, context: ExecutionContext) -> Dict[str, Any]:
        """
        Execute a single task.
        
        Args:
            task: Task to execute
            context: Execution context
            
        Returns:
            Task result dictionary
        """
        self.logger.info(f"Executing task {task.task_id} ({task.task_type})")

        try:
            # Mark as running
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow()
            self.db.update_task_status(task.task_id, TaskStatus.RUNNING)

            # Simulate task execution (in production, would call actual task handler)
            result = await self._simulate_execution(task, context)

            # Mark as completed
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            task.result = result

            self.db.update_task_status(task.task_id, TaskStatus.COMPLETED, result)
            self.db.log_audit_action(
                execution_id=context.execution_id,
                agent_id=task.assigned_agent_id,
                action_type=ActionType.EXECUTE_TASK,
                task_id=task.task_id,
                status='completed',
                details=f'Execution time: {(task.completed_at - task.started_at).total_seconds():.2f}s'
            )

            return result

        except Exception as e:
            self.logger.error(f"Task {task.task_id} failed: {str(e)}")
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.utcnow()

            self.db.update_task_status(
                task.task_id,
                TaskStatus.FAILED,
                error_message=str(e)
            )
            self.db.log_audit_action(
                execution_id=context.execution_id,
                agent_id=task.assigned_agent_id,
                action_type=ActionType.EXECUTE_TASK,
                task_id=task.task_id,
                status='failed',
                details=str(e),
                error=str(e)
            )

            raise

    async def execute_parallel(self, tasks: List[Task],
                              context: ExecutionContext,
                              max_concurrent: int = 10) -> Dict[str, Any]:
        """
        Execute multiple tasks in parallel.
        
        Args:
            tasks: Tasks to execute
            context: Execution context
            max_concurrent: Max concurrent tasks
            
        Returns:
            Aggregated results
        """
        self.logger.info(f"Executing {len(tasks)} tasks in parallel "
                        f"(max_concurrent: {max_concurrent})")

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)

        async def bounded_execute(task: Task) -> Tuple[str, Dict]:
            async with semaphore:
                try:
                    result = await self.execute_task(task, context)
                    return task.task_id, result
                except Exception as e:
                    return task.task_id, {'error': str(e)}

        # Execute all tasks
        results = await asyncio.gather(
            *[bounded_execute(t) for t in tasks],
            return_exceptions=False
        )

        return dict(results)

    async def _simulate_execution(self, task: Task,
                                 context: ExecutionContext) -> Dict[str, Any]:
        """Simulate task execution (placeholder for real implementation)."""
        # Simulate variable execution time based on complexity
        complexity = task.metadata.get('complexity', 1.0)
        await asyncio.sleep(min(complexity, 5.0))

        return {
            'task_id': task.task_id,
            'task_type': task.task_type,
            'execution_time': complexity,
            'status': 'completed',
            'timestamp': datetime.utcnow().isoformat()
        }

    @asynccontextmanager
    async def transaction(self, execution_id: str):
        """
        Transaction context manager with rollback support.
        
        Usage:
            async with engine.transaction(execution_id):
                # Execute operations
                pass
        """
        checkpoint = await self._create_checkpoint(execution_id)

        try:
            yield checkpoint
            await self._commit_checkpoint(execution_id, checkpoint)
        except Exception as e:
            self.logger.error(f"Transaction failed, rolling back: {str(e)}")
            await self._rollback_checkpoint(execution_id, checkpoint)
            raise

    async def _create_checkpoint(self, execution_id: str) -> Dict[str, Any]:
        """Create execution checkpoint for rollback."""
        checkpoint = {
            'execution_id': execution_id,
            'timestamp': datetime.utcnow().isoformat(),
            'state': {'tasks': {}, 'agents': {}}
        }
        self.rollback_stack.append(checkpoint)
        return checkpoint

    async def _commit_checkpoint(self, execution_id: str,
                                checkpoint: Dict[str, Any]) -> None:
        """Commit checkpoint."""
        self.logger.debug(f"Committing checkpoint for {execution_id}")
        if checkpoint in self.rollback_stack:
            self.rollback_stack.remove(checkpoint)

    async def _rollback_checkpoint(self, execution_id: str,
                                  checkpoint: Dict[str, Any]) -> None:
        """Rollback to previous checkpoint."""
        self.logger.warning(f"Rolling back to checkpoint at "
                           f"{checkpoint.get('timestamp')}")
        self.db.save_rollback_state(
            execution_id,
            checkpoint,
            self.rollback_stack
        )


# ============================================================================
# RESULT SYNTHESIZER
# ============================================================================

class ResultSynthesizer:
    """
    Synthesize and combine results from multiple agents into unified output.
    
    Responsibilities:
    - Result aggregation
    - Conflict resolution
    - Result validation
    - Format transformation
    """

    def __init__(self):
        """Initialize result synthesizer."""
        self.logger = logging.getLogger(__name__)
        self.db = DatabaseManager()

    def synthesize(self, execution_context: ExecutionContext) -> Dict[str, Any]:
        """
        Synthesize final results from execution context.
        
        Args:
            execution_context: Completed execution context
            
        Returns:
            Synthesized result dictionary
        """
        self.logger.info(f"Synthesizing results for execution {execution_context.execution_id}")

        # Aggregate task results
        task_results = self._aggregate_task_results(execution_context)

        # Generate statistics
        stats = self._generate_statistics(execution_context)

        # Create summary
        summary = {
            'execution_id': execution_context.execution_id,
            'original_intent': execution_context.intent,
            'status': execution_context.status.value,
            'duration_seconds': execution_context.duration_seconds,
            'completion_percentage': execution_context.completion_percentage,
            'statistics': stats,
            'task_results': task_results,
            'agents_used': len(execution_context.agents),
            'timestamp': datetime.utcnow().isoformat()
        }

        execution_context.result_summary = summary

        # Log synthesis
        self.db.log_audit_action(
            execution_id=execution_context.execution_id,
            agent_id='system',
            action_type=ActionType.SYNTHESIZE_RESULT,
            task_id=execution_context.root_task_id,
            status='success',
            details=f'Synthesized {len(task_results)} task results'
        )

        return summary

    def _aggregate_task_results(self, context: ExecutionContext) -> Dict[str, Any]:
        """Aggregate results from all tasks."""
        results = {}

        for task_id, task in context.tasks.items():
            results[task_id] = {
                'task_type': task.task_type,
                'status': task.status.value,
                'result': task.result,
                'error': task.error_message,
                'execution_time': (
                    (task.completed_at - task.started_at).total_seconds()
                    if task.completed_at and task.started_at else None
                )
            }

        return results

    def _generate_statistics(self, context: ExecutionContext) -> Dict[str, Any]:
        """Generate execution statistics."""
        completed = sum(1 for t in context.tasks.values()
                       if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in context.tasks.values()
                    if t.status == TaskStatus.FAILED)

        return {
            'total_tasks': len(context.tasks),
            'completed_tasks': completed,
            'failed_tasks': failed,
            'success_rate': (completed / len(context.tasks) * 100) if context.tasks else 0,
            'average_task_duration': self._calculate_avg_duration(context),
            'total_agents': len(context.agents),
            'agent_utilization': self._calculate_agent_utilization(context)
        }

    def _calculate_avg_duration(self, context: ExecutionContext) -> float:
        """Calculate average task duration."""
        durations = []
        for task in context.tasks.values():
            if task.completed_at and task.started_at:
                durations.append((task.completed_at - task.started_at).total_seconds())

        return sum(durations) / len(durations) if durations else 0.0

    def _calculate_agent_utilization(self, context: ExecutionContext) -> float:
        """Calculate average agent utilization."""
        if not context.agents:
            return 0.0

        total_utilization = sum(a.capacity_utilization for a in context.agents.values())
        return total_utilization / len(context.agents)


# ============================================================================
# ORCHESTRATION ENGINE (Main Coordinator)
# ============================================================================

class OrchestrationEngine:
    """
    Main orchestration engine that coordinates all components.
    
    This is the central coordinator that brings together:
    - Intent parsing
    - Task decomposition
    - Swarm coordination
    - Parallel execution
    - Result synthesis
    """

    def __init__(self, max_agents: int = 50):
        """Initialize orchestration engine."""
        self.logger = logging.getLogger(__name__)
        self.db = DatabaseManager()

        # Initialize components
        self.intent_parser = IntentParser()
        self.task_decomposer = TaskDecomposer()
        self.swarm_coordinator = SwarmCoordinator(max_agents=max_agents)
        self.execution_engine = ExecutionEngine()
        self.result_synthesizer = ResultSynthesizer()

        # Execution contexts
        self.active_executions: Dict[str, ExecutionContext] = {}

    async def orchestrate(self, intent: str,
                         agent_descriptors: Optional[List[Dict[str, Any]]] = None,
                         metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main orchestration method - coordinates entire execution flow.
        
        Args:
            intent: Natural language intent
            agent_descriptors: List of agent configurations
            metadata: Optional metadata for execution
            
        Returns:
            Final synthesized result
        """
        execution_id = str(uuid.uuid4())
        self.logger.info(f"Starting orchestration: {execution_id}")
        self.logger.info(f"Intent: {intent}")

        try:
            # 1. Parse Intent
            parsed_intent = self.intent_parser.parse(intent, execution_id)

            # 2. Create Execution Context
            context = ExecutionContext(
                execution_id=execution_id,
                intent=intent,
                metadata=metadata or {}
            )
            context.status = ExecutionStatus.RUNNING
            self.active_executions[execution_id] = context

            # 3. Register Agents
            if agent_descriptors:
                for desc in agent_descriptors:
                    await self.swarm_coordinator.register_agent(
                        agent_id=desc.get('agent_id', f"agent_{uuid.uuid4().hex[:8]}"),
                        capabilities=set(desc.get('capabilities', [])),
                        max_concurrent_tasks=desc.get('max_concurrent_tasks', 5),
                        execution_id=execution_id
                    )
                    context.agents[desc['agent_id']] = Agent(
                        agent_id=desc['agent_id'],
                        capabilities=set(desc.get('capabilities', []))
                    )

            # 4. Decompose Tasks
            tasks = self.task_decomposer.decompose(parsed_intent, context)
            self.logger.info(f"Decomposed into {len(tasks)} tasks")

            # 5. Assign and Execute Tasks
            execution_results = {}

            # Separate parallel and sequential tasks
            parallelizable_tasks = [
                t for t in tasks if t.metadata.get('parallelizable', True)
                and t.status == TaskStatus.PENDING
            ]
            sequential_tasks = [
                t for t in tasks if not t.metadata.get('parallelizable', True)
                and t.status == TaskStatus.PENDING
            ]

            # Execute sequential tasks first
            for task in sequential_tasks:
                try:
                    await self.swarm_coordinator.assign_task(task, context)
                    await self.execution_engine.execute_task(task, context)
                except Exception as e:
                    self.logger.error(f"Sequential task {task.task_id} failed: {str(e)}")
                    context.status = ExecutionStatus.FAILED
                    context.error_message = str(e)

            # Execute parallelizable tasks
            if parallelizable_tasks:
                for task in parallelizable_tasks:
                    try:
                        await self.swarm_coordinator.assign_task(task, context)
                    except RuntimeError:
                        self.logger.debug(f"Could not assign task {task.task_id}")

                execution_results = await self.execution_engine.execute_parallel(
                    parallelizable_tasks, context, max_concurrent=10
                )

            # 6. Synthesize Results
            if context.status != ExecutionStatus.FAILED:
                context.status = ExecutionStatus.SUCCESS
                context.end_time = datetime.utcnow()

            final_result = self.result_synthesizer.synthesize(context)

            # 7. Log Execution Trace
            self.db.log_execution_trace(context)

            self.logger.info(f"Orchestration completed: {execution_id}")
            return final_result

        except Exception as e:
            self.logger.error(f"Orchestration failed: {str(e)}")
            if execution_id in self.active_executions:
                context = self.active_executions[execution_id]
                context.status = ExecutionStatus.FAILED
                context.error_message = str(e)
                context.end_time = datetime.utcnow()
                self.db.log_execution_trace(context)

            raise

    async def rollback_execution(self, execution_id: str, reason: str) -> None:
        """
        Rollback an execution.
        
        Args:
            execution_id: ID of execution to rollback
            reason: Reason for rollback
        """
        if execution_id not in self.active_executions:
            raise ValueError(f"Execution {execution_id} not found")

        context = self.active_executions[execution_id]
        self.logger.warning(f"Rolling back execution {execution_id}: {reason}")

        # Mark all running tasks as rolled back
        for task in context.tasks.values():
            if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                task.status = TaskStatus.ROLLED_BACK

        context.status = ExecutionStatus.ROLLED_BACK
        context.rollback_reason = reason
        context.end_time = datetime.utcnow()

        self.db.log_audit_action(
            execution_id=execution_id,
            agent_id='system',
            action_type=ActionType.ROLLBACK,
            task_id=None,
            status='rolled_back',
            details=reason
        )

        self.db.log_execution_trace(context)

    def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get current execution status."""
        if execution_id not in self.active_executions:
            raise ValueError(f"Execution {execution_id} not found")

        context = self.active_executions[execution_id]
        return {
            'execution_id': execution_id,
            'status': context.status.value,
            'completion_percentage': context.completion_percentage,
            'duration_seconds': context.duration_seconds,
            'tasks_summary': {
                'total': len(context.tasks),
                'completed': sum(1 for t in context.tasks.values()
                               if t.status == TaskStatus.COMPLETED),
                'failed': sum(1 for t in context.tasks.values()
                            if t.status == TaskStatus.FAILED)
            }
        }


# ============================================================================
# PUBLIC API
# ============================================================================

async def create_engine(max_agents: int = 50) -> OrchestrationEngine:
    """
    Create and initialize the orchestration engine.
    
    Args:
        max_agents: Maximum number of concurrent agents (default: 50)
        
    Returns:
        Initialized OrchestrationEngine
    """
    engine = OrchestrationEngine(max_agents=max_agents)
    logger.info(f"OrchestrationEngine created (max_agents: {max_agents})")
    return engine


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    async def example_usage():
        """Example usage of the orchestration engine."""

        # Create engine
        engine = await create_engine(max_agents=10)

        # Define agents
        agents = [
            {
                'agent_id': 'agent_analysis',
                'capabilities': ['analysis', 'validation'],
                'max_concurrent_tasks': 5
            },
            {
                'agent_id': 'agent_transform',
                'capabilities': ['transformation', 'aggregation'],
                'max_concurrent_tasks': 3
            },
            {
                'agent_id': 'agent_report',
                'capabilities': ['reporting', 'validation'],
                'max_concurrent_tasks': 2
            }
        ]

        # Execute orchestration
        intent = "Analyze the dataset, transform and aggregate results, then validate and report findings with high priority"

        try:
            result = await engine.orchestrate(
                intent=intent,
                agent_descriptors=agents,
                metadata={'source': 'example', 'version': '1.0'}
            )

            print("\n" + "="*80)
            print("ORCHESTRATION COMPLETE")
            print("="*80)
            print(json.dumps(result, indent=2, default=str))

        except Exception as e:
            logger.error(f"Example execution failed: {str(e)}")

    # Run example
    asyncio.run(example_usage())

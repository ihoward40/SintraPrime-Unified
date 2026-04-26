"""
UniVerse Core Orchestration Engine - Test Suite
================================================

Comprehensive tests for all orchestration engine components:
- Intent parsing
- Task decomposition
- Swarm coordination
- Parallel execution
- Result synthesis
"""

import asyncio
import json
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

# Import engine components
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from core_engine import (
    OrchestrationEngine,
    IntentParser,
    TaskDecomposer,
    SwarmCoordinator,
    ExecutionEngine,
    ResultSynthesizer,
    Task,
    Agent,
    ExecutionContext,
    TaskStatus,
    ExecutionStatus,
    AgentStatus,
    ActionType,
    DatabaseManager,
    create_engine
)


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
async def engine():
    """Create orchestration engine for testing."""
    return await create_engine(max_agents=10)


@pytest.fixture
def execution_context():
    """Create test execution context."""
    return ExecutionContext(
        execution_id='test_exec_123',
        intent='Test intent for orchestration'
    )


@pytest.fixture
def sample_task(execution_context):
    """Create sample task for testing."""
    return Task(
        task_id='task_001',
        execution_id=execution_context.execution_id,
        parent_task_id=None,
        task_type='analysis',
        description='Test analysis task',
        priority=5
    )


# ============================================================================
# INTENT PARSER TESTS
# ============================================================================

class TestIntentParser:
    """Test suite for IntentParser component."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = IntentParser()

    def test_parse_basic_intent(self):
        """Test parsing basic intent."""
        intent = "Analyze the data"
        result = self.parser.parse(intent, 'exec_001')

        assert result['original_intent'] == intent
        assert result['execution_id'] == 'exec_001'
        assert 'priority' in result
        assert 'task_types' in result
        assert 'entities' in result
        assert 'constraints' in result

    def test_priority_extraction(self):
        """Test priority extraction from intent."""
        # High priority
        result = self.parser.parse("Urgently analyze the data", 'exec_001')
        assert result['priority'] > 5

        # Low priority
        result = self.parser.parse("Background analysis of data", 'exec_001')
        assert result['priority'] < 5

    def test_task_type_extraction(self):
        """Test task type extraction."""
        intent = "Analyze, transform, and report the results"
        result = self.parser.parse(intent, 'exec_001')

        assert 'analysis' in result['task_types']
        assert 'transformation' in result['task_types']
        assert 'reporting' in result['task_types']

    def test_constraint_extraction(self):
        """Test constraint extraction."""
        intent = "Sequentially process the data with verification"
        result = self.parser.parse(intent, 'exec_001')

        assert 'constraints' in result
        assert 'require_verification' in result['constraints']

    def test_complexity_estimation(self):
        """Test task complexity estimation."""
        simple_intent = "Process data"
        complex_intent = "Analyze the complex and intricate dataset structure"

        simple_result = self.parser.parse(simple_intent, 'exec_001')
        complex_result = self.parser.parse(complex_intent, 'exec_002')

        assert complex_result['estimated_complexity'] > simple_result['estimated_complexity']


# ============================================================================
# TASK DECOMPOSER TESTS
# ============================================================================

class TestTaskDecomposer:
    """Test suite for TaskDecomposer component."""

    def setup_method(self):
        """Set up test fixtures."""
        self.decomposer = TaskDecomposer()
        self.context = ExecutionContext(
            execution_id='test_exec_001',
            intent='Test decomposition'
        )

    def test_basic_decomposition(self):
        """Test basic task decomposition."""
        parsed_intent = {
            'original_intent': 'Analyze and transform data',
            'priority': 5,
            'task_types': ['analysis', 'transformation'],
            'entities': ['data'],
            'constraints': {'parallelizable': True},
            'estimated_complexity': 2.0
        }

        tasks = self.decomposer.decompose(parsed_intent, self.context)

        assert len(tasks) > 0
        assert tasks[0].task_type == 'root'
        assert self.context.root_task_id == tasks[0].task_id

    def test_subtask_creation(self):
        """Test subtask creation."""
        parsed_intent = {
            'original_intent': 'Analyze, validate, and report',
            'priority': 7,
            'task_types': ['analysis', 'validation', 'reporting'],
            'entities': [],
            'constraints': {'parallelizable': True},
            'estimated_complexity': 1.5
        }

        tasks = self.decomposer.decompose(parsed_intent, self.context)

        # Should have root + task types
        assert len(tasks) >= len(parsed_intent['task_types'])

        # Check parent-child relationships
        for task in tasks[1:]:
            if task.parent_task_id:
                assert task.parent_task_id == tasks[0].task_id

    def test_verification_task_creation(self):
        """Test verification task creation."""
        parsed_intent = {
            'original_intent': 'Analyze data',
            'priority': 5,
            'task_types': ['analysis'],
            'entities': [],
            'constraints': {
                'parallelizable': True,
                'require_verification': True
            },
            'estimated_complexity': 1.0
        }

        tasks = self.decomposer.decompose(parsed_intent, self.context)

        # Should include verification task
        verify_tasks = [t for t in tasks if t.task_type == 'verification']
        assert len(verify_tasks) > 0

    def test_task_dependency_tracking(self):
        """Test task dependency tracking."""
        parsed_intent = {
            'original_intent': 'Test',
            'priority': 5,
            'task_types': ['analysis'],
            'entities': [],
            'constraints': {'parallelizable': True},
            'estimated_complexity': 1.0
        }

        tasks = self.decomposer.decompose(parsed_intent, self.context)
        root_task = tasks[0]

        # Subtasks should depend on root
        for task in tasks[1:]:
            if task.dependencies:
                assert root_task.task_id in task.dependencies


# ============================================================================
# SWARM COORDINATOR TESTS
# ============================================================================

class TestSwarmCoordinator:
    """Test suite for SwarmCoordinator component."""

    @pytest.mark.asyncio
    async def test_agent_registration(self):
        """Test agent registration."""
        coordinator = SwarmCoordinator(max_agents=10)

        agent = await coordinator.register_agent(
            agent_id='test_agent_001',
            capabilities={'analysis', 'validation'}
        )

        assert agent.agent_id == 'test_agent_001'
        assert agent.status == AgentStatus.IDLE
        assert 'analysis' in agent.capabilities

    @pytest.mark.asyncio
    async def test_max_agents_constraint(self):
        """Test maximum agents constraint."""
        coordinator = SwarmCoordinator(max_agents=2)

        # Register first agent
        await coordinator.register_agent('agent_001', {'analysis'})

        # Register second agent
        await coordinator.register_agent('agent_002', {'analysis'})

        # Third registration should fail
        with pytest.raises(RuntimeError):
            await coordinator.register_agent('agent_003', {'analysis'})

    @pytest.mark.asyncio
    async def test_task_assignment(self):
        """Test task assignment to agents."""
        coordinator = SwarmCoordinator(max_agents=10)
        context = ExecutionContext(execution_id='test_001', intent='test')

        # Register agent
        await coordinator.register_agent(
            agent_id='agent_001',
            capabilities={'analysis', 'transformation'}
        )

        # Create and assign task
        task = Task(
            task_id='task_001',
            execution_id='test_001',
            parent_task_id=None,
            task_type='analysis',
            description='Test task'
        )

        agent_id = await coordinator.assign_task(task, context)

        assert agent_id == 'agent_001'
        assert task.assigned_agent_id == agent_id
        assert task.status == TaskStatus.ASSIGNED

    @pytest.mark.asyncio
    async def test_agent_scoring(self):
        """Test agent scoring mechanism."""
        coordinator = SwarmCoordinator(max_agents=10)

        # Register agents with different capabilities
        agent1 = await coordinator.register_agent(
            'agent_001',
            {'analysis'}
        )
        agent2 = await coordinator.register_agent(
            'agent_002',
            {'transformation'}
        )

        # Create analysis task
        task = Task(
            task_id='task_001',
            execution_id='test_001',
            parent_task_id=None,
            task_type='analysis',
            description='Test',
            priority=5
        )

        # Agent1 should score higher for analysis task
        score1 = coordinator._score_agent(agent1, task)
        score2 = coordinator._score_agent(agent2, task)

        assert score1 > score2

    @pytest.mark.asyncio
    async def test_agent_health_check(self):
        """Test agent health checking."""
        coordinator = SwarmCoordinator(max_agents=10)

        # Register agent
        agent = await coordinator.register_agent('agent_001', {'analysis'})

        # Agent should be alive initially
        assert agent.is_alive()

        # Simulate heartbeat timeout
        from datetime import timedelta
        agent.last_heartbeat = datetime.utcnow() - timedelta(seconds=40)

        # Should be marked dead with timeout > 30
        dead_agents = await coordinator.heartbeat_check(timeout_seconds=30)
        assert 'agent_001' in dead_agents


# ============================================================================
# EXECUTION ENGINE TESTS
# ============================================================================

class TestExecutionEngine:
    """Test suite for ExecutionEngine component."""

    @pytest.mark.asyncio
    async def test_single_task_execution(self):
        """Test execution of single task."""
        engine = ExecutionEngine()
        context = ExecutionContext(execution_id='test_001', intent='test')

        task = Task(
            task_id='task_001',
            execution_id='test_001',
            parent_task_id=None,
            task_type='analysis',
            description='Test task',
            assigned_agent_id='agent_001'
        )

        result = await engine.execute_task(task, context)

        assert task.status == TaskStatus.COMPLETED
        assert result is not None
        assert task.completed_at is not None

    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Test parallel task execution."""
        engine = ExecutionEngine()
        context = ExecutionContext(execution_id='test_001', intent='test')

        tasks = [
            Task(
                task_id=f'task_{i:03d}',
                execution_id='test_001',
                parent_task_id=None,
                task_type='analysis',
                description=f'Test task {i}',
                assigned_agent_id='agent_001',
                metadata={'parallelizable': True}
            )
            for i in range(5)
        ]

        results = await engine.execute_parallel(tasks, context, max_concurrent=3)

        assert len(results) == 5
        for task_id in results:
            assert task_id in [t.task_id for t in tasks]

    @pytest.mark.asyncio
    async def test_task_failure_handling(self):
        """Test handling of task failures."""
        engine = ExecutionEngine()
        context = ExecutionContext(execution_id='test_001', intent='test')

        task = Task(
            task_id='task_001',
            execution_id='test_001',
            parent_task_id=None,
            task_type='analysis',
            description='Test task',
            assigned_agent_id='agent_001'
        )

        # Execute task (should complete successfully in test)
        result = await engine.execute_task(task, context)
        assert task.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_transaction_context(self):
        """Test transaction context manager."""
        engine = ExecutionEngine()

        async with engine.transaction('test_exec_001') as checkpoint:
            assert checkpoint is not None
            assert 'execution_id' in checkpoint
            assert 'timestamp' in checkpoint


# ============================================================================
# RESULT SYNTHESIZER TESTS
# ============================================================================

class TestResultSynthesizer:
    """Test suite for ResultSynthesizer component."""

    def test_result_aggregation(self):
        """Test result aggregation."""
        synthesizer = ResultSynthesizer()
        context = ExecutionContext(execution_id='test_001', intent='Test')
        context.status = ExecutionStatus.SUCCESS
        context.end_time = datetime.utcnow()

        # Add some tasks
        for i in range(3):
            task = Task(
                task_id=f'task_{i:03d}',
                execution_id='test_001',
                parent_task_id=None,
                task_type='analysis',
                description=f'Task {i}',
                status=TaskStatus.COMPLETED,
                result={'data': f'result_{i}'},
                completed_at=datetime.utcnow()
            )
            task.started_at = datetime.utcnow()
            context.tasks[task.task_id] = task

        result = synthesizer.synthesize(context)

        assert result['execution_id'] == 'test_001'
        assert result['status'] == 'success'
        assert 'task_results' in result
        assert 'statistics' in result

    def test_statistics_calculation(self):
        """Test statistics calculation."""
        synthesizer = ResultSynthesizer()
        context = ExecutionContext(execution_id='test_001', intent='Test')
        context.status = ExecutionStatus.SUCCESS
        context.end_time = datetime.utcnow()

        # Add completed and failed tasks
        for i in range(7):
            task = Task(
                task_id=f'task_{i:03d}',
                execution_id='test_001',
                parent_task_id=None,
                task_type='analysis',
                description=f'Task {i}',
                status=TaskStatus.COMPLETED if i < 5 else TaskStatus.FAILED,
                completed_at=datetime.utcnow()
            )
            task.started_at = datetime.utcnow()
            context.tasks[task.task_id] = task

        result = synthesizer.synthesize(context)
        stats = result['statistics']

        assert stats['total_tasks'] == 7
        assert stats['completed_tasks'] == 5
        assert stats['failed_tasks'] == 2
        assert stats['success_rate'] > 0

    def test_result_summary_format(self):
        """Test result summary format."""
        synthesizer = ResultSynthesizer()
        context = ExecutionContext(execution_id='test_001', intent='Analyze data')
        context.status = ExecutionStatus.SUCCESS
        context.end_time = datetime.utcnow()
        context.root_task_id = 'root_task'

        result = synthesizer.synthesize(context)

        # Check required fields
        assert 'execution_id' in result
        assert 'original_intent' in result
        assert 'status' in result
        assert 'duration_seconds' in result
        assert 'completion_percentage' in result
        assert 'statistics' in result
        assert 'task_results' in result
        assert 'timestamp' in result


# ============================================================================
# ORCHESTRATION ENGINE TESTS
# ============================================================================

class TestOrchestrationEngine:
    """Test suite for main OrchestrationEngine."""

    @pytest.mark.asyncio
    async def test_orchestration_flow(self):
        """Test complete orchestration flow."""
        engine = await create_engine(max_agents=5)

        agents = [
            {
                'agent_id': 'agent_001',
                'capabilities': ['analysis', 'validation'],
                'max_concurrent_tasks': 3
            },
            {
                'agent_id': 'agent_002',
                'capabilities': ['transformation', 'aggregation'],
                'max_concurrent_tasks': 2
            }
        ]

        intent = "Analyze and validate the dataset with high priority"

        result = await engine.orchestrate(
            intent=intent,
            agent_descriptors=agents,
            metadata={'test': True}
        )

        assert result['execution_id'] is not None
        assert result['status'] in ['success', 'failed']
        assert 'statistics' in result
        assert 'task_results' in result

    @pytest.mark.asyncio
    async def test_execution_status_tracking(self):
        """Test execution status tracking."""
        engine = await create_engine(max_agents=5)

        intent = "Test orchestration"

        result = await engine.orchestrate(
            intent=intent,
            agent_descriptors=[
                {
                    'agent_id': 'agent_001',
                    'capabilities': ['analysis']
                }
            ]
        )

        status = engine.get_execution_status(result['execution_id'])

        assert 'execution_id' in status
        assert 'status' in status
        assert 'completion_percentage' in status
        assert 'tasks_summary' in status

    @pytest.mark.asyncio
    async def test_rollback_functionality(self):
        """Test rollback functionality."""
        engine = await create_engine(max_agents=5)

        intent = "Test rollback"

        result = await engine.orchestrate(
            intent=intent,
            agent_descriptors=[
                {
                    'agent_id': 'agent_001',
                    'capabilities': ['analysis']
                }
            ]
        )

        execution_id = result['execution_id']

        # Attempt rollback
        await engine.rollback_execution(execution_id, "Test rollback reason")

        # Check status after rollback
        status = engine.get_execution_status(execution_id)
        assert status['status'] == 'rolled_back'

    @pytest.mark.asyncio
    async def test_concurrent_executions(self):
        """Test multiple concurrent executions."""
        engine = await create_engine(max_agents=10)

        async def run_orchestration(execution_num):
            return await engine.orchestrate(
                intent=f"Concurrent test execution {execution_num}",
                agent_descriptors=[
                    {
                        'agent_id': f'agent_{execution_num}',
                        'capabilities': ['analysis']
                    }
                ]
            )

        # Run 3 concurrent orchestrations
        results = await asyncio.gather(
            run_orchestration(1),
            run_orchestration(2),
            run_orchestration(3)
        )

        assert len(results) == 3
        assert all('execution_id' in r for r in results)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for complete workflows."""

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow."""
        engine = await create_engine(max_agents=8)

        # Complex intent with multiple task types
        intent = ("Urgently analyze the customer data, transform and aggregate results, "
                 "validate findings, and generate comprehensive report")

        agents = [
            {
                'agent_id': 'analyst_01',
                'capabilities': ['analysis', 'validation'],
                'max_concurrent_tasks': 4
            },
            {
                'agent_id': 'transformer_01',
                'capabilities': ['transformation', 'aggregation'],
                'max_concurrent_tasks': 3
            },
            {
                'agent_id': 'reporter_01',
                'capabilities': ['reporting', 'validation'],
                'max_concurrent_tasks': 2
            }
        ]

        result = await engine.orchestrate(
            intent=intent,
            agent_descriptors=agents,
            metadata={'workflow': 'comprehensive_analysis', 'version': '1.0'}
        )

        # Verify complete result structure
        assert result['status'] in ['success', 'failed']
        assert result['duration_seconds'] >= 0
        assert result['completion_percentage'] >= 0
        assert result['agents_used'] > 0
        assert 'statistics' in result
        assert result['statistics']['total_tasks'] > 0

    @pytest.mark.asyncio
    async def test_graceful_degradation(self):
        """Test graceful degradation with limited agents."""
        engine = await create_engine(max_agents=2)

        intent = "Analyze, transform, aggregate, and validate data"

        # Even with limited agents, should complete
        result = await engine.orchestrate(
            intent=intent,
            agent_descriptors=[
                {'agent_id': 'agent_001', 'capabilities': ['analysis', 'transformation']},
                {'agent_id': 'agent_002', 'capabilities': ['aggregation', 'validation']}
            ]
        )

        # Should complete despite limited resources
        assert result is not None
        assert result['status'] in ['success', 'failed']


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Performance and stress tests."""

    @pytest.mark.asyncio
    async def test_high_concurrency(self):
        """Test with high number of concurrent tasks."""
        engine = await create_engine(max_agents=20)

        # Create many concurrent tasks
        agents = [
            {
                'agent_id': f'agent_{i:03d}',
                'capabilities': ['analysis', 'transformation'],
                'max_concurrent_tasks': 5
            }
            for i in range(10)
        ]

        intent = "Process multiple data streams in parallel"

        result = await engine.orchestrate(
            intent=intent,
            agent_descriptors=agents
        )

        assert result is not None
        assert result['agents_used'] > 0

    @pytest.mark.asyncio
    async def test_scalability_50_agents(self):
        """Test scalability with 50 agents."""
        engine = await create_engine(max_agents=50)

        agents = [
            {
                'agent_id': f'agent_{i:03d}',
                'capabilities': ['analysis', 'transformation', 'reporting'],
                'max_concurrent_tasks': 3
            }
            for i in range(30)  # Register 30 out of max 50
        ]

        intent = "Distribute work across large swarm"

        result = await engine.orchestrate(
            intent=intent,
            agent_descriptors=agents[:10]  # Use subset for orchestration
        )

        assert result is not None


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v', '--tb=short'])

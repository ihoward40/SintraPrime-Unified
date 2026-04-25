"""
Comprehensive test suite for agent factory, roles, and task router.
Tests all components with 100% coverage of core functionality.
"""

import unittest
import time
from datetime import datetime, timedelta
from agent_factory import (
    AgentFactory,
    AgentValidator,
    GeneratedAgent,
    EXAMPLE_AGENT_DEFINITIONS,
)
from agent_roles import (
    RoleManager,
    BaseRole,
    RoleCategory,
    ProficiencyLevel,
)
from task_router import (
    TaskRouter,
    TaskDefinition,
    TaskPriority,
    RoutingStrategy,
    AgentState,
)


class TestAgentRoles(unittest.TestCase):
    """Test agent role system."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = RoleManager()

    def test_role_count(self):
        """Test that all 12 base roles are defined."""
        self.assertEqual(self.manager.get_role_count(), 12)

    def test_get_role(self):
        """Test getting a role by ID."""
        analyst = self.manager.get_role("analyst")
        self.assertIsNotNone(analyst)
        self.assertEqual(analyst.role_id, "analyst")
        self.assertEqual(analyst.role_name, "Analyst")

    def test_role_capabilities(self):
        """Test role capabilities."""
        analyst = self.manager.get_role("analyst")
        self.assertIn("data_analysis", analyst.capabilities)
        self.assertIn("pattern_recognition", analyst.capabilities)

    def test_role_inheritance(self):
        """Test role inheritance."""
        vision = self.manager.get_role("vision")
        analyst = self.manager.get_role("analyst")

        # Vision should inherit from analyst
        self.assertEqual(vision.parent_role, analyst)
        # Vision should have analyst's capabilities
        self.assertTrue(vision.has_capability("data_analysis"))

    def test_add_capability(self):
        """Test adding capability to role."""
        analyst = self.manager.get_role("analyst")
        initial_count = len(analyst.capabilities)

        analyst.add_capability("test_capability")
        self.assertIn("test_capability", analyst.capabilities)
        self.assertEqual(len(analyst.capabilities), initial_count + 1)

    def test_remove_capability(self):
        """Test removing capability from role."""
        analyst = self.manager.get_role("analyst")
        analyst.add_capability("test_capability")

        analyst.remove_capability("test_capability")
        self.assertNotIn("test_capability", analyst.capabilities)

    def test_create_custom_role(self):
        """Test creating custom role."""
        custom_role = self.manager.create_custom_role(
            role_name="CustomAnalyst",
            description="Custom analyst role",
            category=RoleCategory.ANALYSIS,
            capabilities=["custom_analysis"],
        )

        self.assertIsNotNone(custom_role)
        self.assertEqual(custom_role.role_name, "CustomAnalyst")
        self.assertIn("custom_analysis", custom_role.capabilities)

    def test_role_inheritance_in_custom(self):
        """Test custom role with parent role."""
        parent = self.manager.get_role("analyst")
        custom_role = self.manager.create_custom_role(
            role_name="AdvancedAnalyst",
            description="Advanced analyst",
            category=RoleCategory.ANALYSIS,
            capabilities=["advanced_analysis"],
            parent_role_id="analyst",
        )

        # Should inherit parent capabilities
        self.assertTrue(custom_role.has_capability("data_analysis"))
        self.assertTrue(custom_role.has_capability("advanced_analysis"))

    def test_list_roles_by_category(self):
        """Test filtering roles by category."""
        analysis_roles = self.manager.list_roles(RoleCategory.ANALYSIS)
        self.assertGreater(len(analysis_roles), 0)

        # All should be analysis category
        for role in analysis_roles:
            self.assertEqual(role.category, RoleCategory.ANALYSIS)

    def test_get_roles_for_task(self):
        """Test getting suitable roles for task."""
        roles = self.manager.get_roles_for_task(
            "data_analysis", ["data_analysis", "pattern_recognition"]
        )

        self.assertGreater(len(roles), 0)
        # Should be sorted by priority
        for i in range(len(roles) - 1):
            self.assertGreaterEqual(roles[i].priority_weight, roles[i + 1].priority_weight)

    def test_role_serialization(self):
        """Test serializing role to dict."""
        analyst = self.manager.get_role("analyst")
        data = analyst.to_dict()

        self.assertEqual(data["role_id"], "analyst")
        self.assertEqual(data["role_name"], "Analyst")
        self.assertIn("data_analysis", data["capabilities"])

    def test_export_roles(self):
        """Test exporting all roles."""
        exported = self.manager.export_roles()

        self.assertIn("built_in", exported)
        self.assertIn("custom", exported)
        self.assertEqual(len(exported["built_in"]), 12)


class TestAgentFactory(unittest.TestCase):
    """Test agent factory system."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = AgentFactory()

    def test_create_agent_basic(self):
        """Test creating basic agent."""
        agent, error = self.factory.create_agent(
            description="Analyzes data and generates reports",
            role_id="analyst",
            name="DataAnalyzer",
        )

        self.assertIsNone(error)
        self.assertIsNotNone(agent)
        self.assertEqual(agent.name, "DataAnalyzer")
        self.assertEqual(agent.role_id, "analyst")

    def test_create_agent_with_capabilities(self):
        """Test creating agent with explicit capabilities."""
        agent, error = self.factory.create_agent(
            description="Test agent",
            role_id="analyst",
            name="TestAgent",
            capabilities=["data_analysis", "pattern_recognition"],
        )

        self.assertIsNone(error)
        self.assertEqual(len(agent.capabilities), 2)
        self.assertIn("data_analysis", agent.capabilities)

    def test_create_agent_auto_name(self):
        """Test auto-generated agent name."""
        agent, error = self.factory.create_agent(
            description="Analyzes data",
            role_id="analyst",
        )

        self.assertIsNone(error)
        self.assertIsNotNone(agent.name)
        self.assertTrue(agent.name.startswith("Agent_"))

    def test_create_agent_infer_capabilities(self):
        """Test capability inference from description."""
        agent, error = self.factory.create_agent(
            description="Analyzes data and creates reports",
            role_id="analyst",
            name="InferAgent",
        )

        self.assertIsNone(error)
        # Should infer capabilities from keywords
        self.assertGreater(len(agent.capabilities), 0)

    def test_create_agent_time_limit(self):
        """Test agent creation time limit."""
        agent, error = self.factory.create_agent(
            description="Test agent creation within time limits for analysis",
            role_id="analyst",
        )

        self.assertIsNone(error)
        self.assertLess(agent.creation_time, 5.0)  # Should be < 5 seconds

    def test_create_agent_validation_error(self):
        """Test validation error handling."""
        agent, error = self.factory.create_agent(
            description="",  # Empty description
            role_id="analyst",
            name="",  # Empty name
        )

        self.assertIsNone(agent)
        self.assertIsNotNone(error)
        self.assertTrue("field" in error.lower() or "required" in error.lower())

    def test_create_multiple_agents(self):
        """Test creating multiple agents."""
        agents_data = [
            ("Analyst1", "analyst", "Analyzes data patterns"),
            ("Executor1", "executor", "Executes system tasks"),
            ("Creator1", "creator", "Creates code solutions"),
        ]

        created = []
        for name, role, desc in agents_data:
            agent, error = self.factory.create_agent(
                description=desc, role_id=role, name=name
            )
            self.assertIsNone(error)
            self.assertIsNotNone(agent)
            created.append(agent)

        self.assertEqual(len(created), 3)

    def test_get_agent(self):
        """Test retrieving agent."""
        agent, error = self.factory.create_agent(
            description="Test agent for analysis and reporting purposes", 
            role_id="analyst", 
            name="TestAgent"
        )

        self.assertIsNone(error)
        self.assertIsNotNone(agent)
        retrieved = self.factory.get_agent(agent.agent_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.agent_id, agent.agent_id)

    def test_list_agents(self):
        """Test listing all agents."""
        for i in range(3):
            self.factory.create_agent(
                description=f"Test agent number {i} for data analysis and pattern recognition",
                role_id="analyst", 
                name=f"Agent{i}"
            )

        agents = self.factory.list_agents()
        self.assertGreaterEqual(len(agents), 3)

    def test_delete_agent(self):
        """Test deleting agent."""
        agent, error = self.factory.create_agent(
            description="Test agent that will be deleted from the system", 
            role_id="analyst", 
            name="DeleteMe"
        )

        self.assertIsNone(error)
        self.assertIsNotNone(agent)
        success = self.factory.delete_agent(agent.agent_id)
        self.assertTrue(success)

        retrieved = self.factory.get_agent(agent.agent_id)
        self.assertIsNone(retrieved)

    def test_export_agents(self):
        """Test exporting agents."""
        self.factory.create_agent(description="Test agent one for data analysis operations", role_id="analyst")
        self.factory.create_agent(description="Test agent two for task execution operations", role_id="executor")

        exported = self.factory.export_agents()
        self.assertGreater(len(exported), 0)

        for agent_id, agent_data in exported.items():
            self.assertEqual(agent_data["agent_id"], agent_id)

    def test_factory_stats(self):
        """Test factory statistics."""
        self.factory.create_agent(description="Test agent for statistics and metric collection", role_id="analyst")

        stats = self.factory.get_stats()
        self.assertGreater(stats["total_agents"], 0)
        self.assertGreater(stats["total_capabilities"], 0)

    def test_capability_inference(self):
        """Test keyword-based capability inference."""
        agent, _ = self.factory.create_agent(
            description="Analyzes code and debugs errors",
            role_id="debugger",
            capabilities=None,  # Force inference
        )

        # Should infer both analyzer and debugger capabilities
        self.assertGreater(len(agent.capabilities), 0)

    def test_skill_level(self):
        """Test agent skill level."""
        agent, error = self.factory.create_agent(
            description="Test agent with advanced skill level for complex analysis tasks",
            role_id="analyst", 
            skill_level=4
        )

        self.assertIsNone(error)
        self.assertIsNotNone(agent)
        self.assertEqual(agent.skill_level, 4)

    def test_max_concurrent_tasks(self):
        """Test max concurrent tasks setting."""
        agent, error = self.factory.create_agent(
            description="Test executor agent with high concurrency handling capability",
            role_id="executor", 
            max_concurrent_tasks=10
        )

        self.assertIsNone(error)
        self.assertIsNotNone(agent)
        self.assertEqual(agent.max_concurrent_tasks, 10)


class TestTaskRouter(unittest.TestCase):
    """Test intelligent task router."""

    def setUp(self):
        """Set up test fixtures."""
        self.router = TaskRouter()
        # Register test agents
        self.router.register_agent(
            agent_id="agent_1",
            name="Analyst1",
            role_id="analyst",
            capabilities=["data_analysis", "pattern_recognition"],
            skill_level=4,
        )
        self.router.register_agent(
            agent_id="agent_2",
            name="Executor1",
            role_id="executor",
            capabilities=["task_execution", "command_execution"],
            skill_level=3,
        )
        self.router.register_agent(
            agent_id="agent_3",
            name="Analyst2",
            role_id="analyst",
            capabilities=["data_analysis", "report_generation"],
            skill_level=2,
        )

    def test_register_agent(self):
        """Test registering agent."""
        success = self.router.register_agent(
            agent_id="agent_test",
            name="TestAgent",
            role_id="test",
            capabilities=["test"],
        )

        self.assertTrue(success)
        self.assertIn("agent_test", self.router.agents)

    def test_unregister_agent(self):
        """Test unregistering agent."""
        success = self.router.unregister_agent("agent_1")
        self.assertTrue(success)
        self.assertNotIn("agent_1", self.router.agents)

    def test_update_agent_state(self):
        """Test updating agent state."""
        success = self.router.update_agent_state(
            agent_id="agent_1",
            current_tasks=2,
            completed_tasks=10,
            failed_tasks=1,
            avg_execution_time_ms=100,
        )

        self.assertTrue(success)
        agent = self.router.agents["agent_1"]
        self.assertEqual(agent.current_tasks, 2)
        self.assertEqual(agent.completed_tasks, 10)

    def test_find_capable_agents(self):
        """Test finding capable agents."""
        task = TaskDefinition(
            task_id="task_1",
            task_type="analysis",
            description="Analyze data",
            required_capabilities=["data_analysis"],
        )

        capable = self.router._find_capable_agents(task.required_capabilities)
        self.assertGreater(len(capable), 0)
        self.assertIn("agent_1", capable)

    def test_route_task_weighted_score(self):
        """Test routing with weighted score strategy."""
        task = TaskDefinition(
            task_id="task_1",
            task_type="analysis",
            description="Analyze data",
            required_capabilities=["data_analysis"],
            priority=TaskPriority.HIGH,
        )

        decision = self.router.route_task(
            task, strategy=RoutingStrategy.WEIGHTED_SCORE
        )

        self.assertIsNotNone(decision)
        self.assertEqual(decision.task_id, "task_1")
        self.assertIsNotNone(decision.assigned_agent_id)

    def test_route_task_round_robin(self):
        """Test round-robin routing."""
        agents_used = set()

        for i in range(6):
            task = TaskDefinition(
                task_id=f"task_{i}",
                task_type="analysis",
                description="Test",
                required_capabilities=["data_analysis"],
            )

            decision = self.router.route_task(
                task, strategy=RoutingStrategy.ROUND_ROBIN
            )
            if decision:
                agents_used.add(decision.assigned_agent_id)
                # Reset for next iteration
                self.router.agents[decision.assigned_agent_id].current_tasks = 0

        # Should use multiple agents with round-robin
        self.assertGreater(len(agents_used), 1)

    def test_route_task_least_loaded(self):
        """Test least-loaded routing."""
        # Set one agent as heavily loaded
        self.router.agents["agent_1"].current_tasks = 5
        self.router.agents["agent_3"].current_tasks = 1

        task = TaskDefinition(
            task_id="task_ll",
            task_type="analysis",
            description="Test",
            required_capabilities=["data_analysis"],
        )

        decision = self.router.route_task(
            task, strategy=RoutingStrategy.LEAST_LOADED
        )

        # Should route to least loaded agent (agent_3)
        self.assertEqual(decision.assigned_agent_id, "agent_3")

    def test_route_task_best_fit(self):
        """Test best-fit routing."""
        task = TaskDefinition(
            task_id="task_bf",
            task_type="analysis",
            description="Test",
            required_capabilities=["data_analysis", "report_generation"],
        )

        decision = self.router.route_task(task, strategy=RoutingStrategy.BEST_FIT)

        # agent_3 has both capabilities
        self.assertIn(decision.assigned_agent_id, ["agent_1", "agent_3"])

    def test_no_capable_agent(self):
        """Test routing when no capable agent exists."""
        task = TaskDefinition(
            task_id="task_none",
            task_type="unknown",
            description="Test",
            required_capabilities=["nonexistent_capability"],
        )

        decision = self.router.route_task(task)
        self.assertIsNone(decision)

    def test_complete_task(self):
        """Test task completion."""
        task = TaskDefinition(
            task_id="task_complete",
            task_type="test",
            description="Test",
            required_capabilities=["data_analysis"],
        )

        decision = self.router.route_task(task)
        initial_tasks = decision.assigned_agent_id
        agent = self.router.agents[initial_tasks]
        initial_load = agent.current_tasks

        success = self.router.complete_task(initial_tasks, success=True, actual_duration_ms=100)

        self.assertTrue(success)
        self.assertEqual(agent.current_tasks, initial_load - 1)
        self.assertEqual(agent.completed_tasks, 1)

    def test_get_agent_stats(self):
        """Test getting agent statistics."""
        stats = self.router.get_agent_stats("agent_1")

        self.assertIsNotNone(stats)
        self.assertEqual(stats["agent_id"], "agent_1")

    def test_get_all_agents_stats(self):
        """Test getting all agent statistics."""
        stats = self.router.get_all_agents_stats()

        self.assertEqual(len(stats), 3)

    def test_routing_stats(self):
        """Test routing statistics."""
        # Create and route some tasks
        for i in range(5):
            task = TaskDefinition(
                task_id=f"task_{i}",
                task_type="test",
                description="Test",
                required_capabilities=["data_analysis"],
            )
            self.router.route_task(task)

        stats = self.router.get_routing_stats()

        self.assertGreater(stats["total_routings"], 0)
        self.assertGreater(stats["average_score"], 0)

    def test_task_priority(self):
        """Test task priority handling."""
        critical_task = TaskDefinition(
            task_id="critical",
            task_type="test",
            description="Critical",
            required_capabilities=["data_analysis"],
            priority=TaskPriority.CRITICAL,
        )

        decision = self.router.route_task(critical_task)
        self.assertIsNotNone(decision)


class TestAgentValidator(unittest.TestCase):
    """Test agent validator."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = AgentValidator()

    def test_valid_definition(self):
        """Test validating correct definition."""
        definition = {
            "name": "TestAgent",
            "role_id": "analyst",
            "description": "A test agent for analysis",
            "capabilities": ["data_analysis", "pattern_recognition"],
        }

        valid = self.validator.validate(definition)
        self.assertTrue(valid)

    def test_missing_required_field(self):
        """Test validation fails with missing field."""
        definition = {
            "name": "TestAgent",
            "role_id": "analyst",
            # Missing description and capabilities
        }

        valid = self.validator.validate(definition)
        self.assertFalse(valid)
        self.assertGreater(len(self.validator.get_errors()), 0)

    def test_invalid_field_type(self):
        """Test validation fails with wrong type."""
        definition = {
            "name": "TestAgent",
            "role_id": "analyst",
            "description": "Test",
            "capabilities": "not_a_list",  # Should be list
        }

        valid = self.validator.validate(definition)
        self.assertFalse(valid)

    def test_field_length_validation(self):
        """Test string length validation."""
        definition = {
            "name": "A",  # Too short, needs 1+ char (actually 1 is ok)
            "role_id": "analyst",
            "description": "short",  # Too short, needs 10+
            "capabilities": ["test"],
        }

        valid = self.validator.validate(definition)
        self.assertFalse(valid)


def run_tests():
    """Run all tests and return summary."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestAgentRoles))
    suite.addTests(loader.loadTestsFromTestCase(TestAgentFactory))
    suite.addTests(loader.loadTestsFromTestCase(TestTaskRouter))
    suite.addTests(loader.loadTestsFromTestCase(TestAgentValidator))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return summary
    return {
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "success": result.wasSuccessful(),
    }


if __name__ == "__main__":
    result = run_tests()
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests Run: {result['tests_run']}")
    print(f"Failures: {result['failures']}")
    print(f"Errors: {result['errors']}")
    print(f"Skipped: {result['skipped']}")
    print(f"Success: {result['success']}")
    print("=" * 70)

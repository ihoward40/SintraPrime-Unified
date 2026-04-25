"""
Comprehensive test suite for UniVerse Skill Generation System.

Tests all major components:
- Skill Extraction
- Skill Generation
- Skill Validation
- Skill Library Management
- Skill Inheritance and Distribution
"""

import unittest
import tempfile
import os
import json
from datetime import datetime
from skill_system import (
    UniVersSkillSystem,
    SkillExtractor,
    SkillGenerator,
    SkillValidator,
    SkillLibraryManager,
    SkillInheritanceSystem,
    DatabaseManager,
    SkillSchema,
    SkillMetadata,
    ValidationResult,
    SkillCategory,
    SkillStatus
)


class TestSkillExtractor(unittest.TestCase):
    """Tests for SkillExtractor component."""

    def setUp(self):
        """Set up test fixtures."""
        self.extractor = SkillExtractor()

    def test_extract_from_task(self):
        """Test basic skill extraction from a task."""
        task_result = {
            'inputs': {'data': 'input_data', 'params': 'parameters'},
            'outputs': {'result': 'output_data'},
            'operations': ['parse', 'process', 'format']
        }

        pattern = self.extractor.extract_from_task(
            task_description="Process data and generate output",
            task_result=task_result,
            task_type="data_processing"
        )

        self.assertIsNotNone(pattern)
        self.assertEqual(pattern['task_type'], 'data_processing')
        self.assertIn('data', pattern['input_keys'])
        self.assertIn('result', pattern['output_keys'])

    def test_category_classification(self):
        """Test category classification logic."""
        # Test coding category
        pattern = self.extractor.extract_from_task(
            task_description="Write Python code and test it",
            task_result={'inputs': {}, 'outputs': {}},
            task_type="coding"
        )
        self.assertEqual(pattern['category'], SkillCategory.CODING.value)

        # Test analysis category
        pattern = self.extractor.extract_from_task(
            task_description="Analyze data and generate report",
            task_result={'inputs': {}, 'outputs': {}},
            task_type="analysis"
        )
        self.assertEqual(pattern['category'], SkillCategory.ANALYSIS.value)

    def test_complexity_calculation(self):
        """Test complexity score calculation."""
        simple_task = {
            'inputs': {'x': 1},
            'outputs': {'y': 2},
            'operations': ['add']
        }

        complex_task = {
            'inputs': {'data': [1, 2, 3] * 400},
            'outputs': {'result': []},
            'operations': ['load', 'clean', 'transform', 'analyze', 'visualize'],
            'data_volume': 5000
        }

        simple_pattern = self.extractor.extract_from_task(
            "Simple task", simple_task, "simple"
        )
        complex_pattern = self.extractor.extract_from_task(
            "Complex task", complex_task, "complex"
        )

        self.assertLess(
            simple_pattern['complexity_score'],
            complex_pattern['complexity_score']
        )


class TestSkillGenerator(unittest.TestCase):
    """Tests for SkillGenerator component."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_manager = DatabaseManager(
            os.path.join(self.temp_dir, 'test.db')
        )
        self.generator = SkillGenerator(self.db_manager)

    def tearDown(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generate_skill_name(self):
        """Test skill name generation."""
        pattern = {'task_type': 'data_analysis'}
        name = self.generator._generate_skill_name(pattern, 'analysis')
        self.assertIn('data_analysis', name)

    def test_generate_schema(self):
        """Test schema generation from pattern."""
        pattern = {
            'input_keys': ['data', 'params'],
            'output_keys': ['result', 'metadata']
        }
        examples = [{
            'inputs': {'data': [], 'params': {}},
            'outputs': {'result': None, 'metadata': {}}
        }]

        schema = self.generator._generate_schema(pattern, examples)
        self.assertEqual(len(schema.inputs), 2)
        self.assertEqual(len(schema.outputs), 2)
        self.assertIn('data', schema.required_inputs)

    def test_generate_code(self):
        """Test Python code generation."""
        schema = SkillSchema(
            inputs={'x': {'type': 'int'}, 'y': {'type': 'int'}},
            outputs={'result': {'type': 'int'}},
            required_inputs=['x', 'y'],
            required_outputs=['result']
        )

        pattern = {
            'task_type': 'add',
            'input_keys': ['x', 'y'],
            'output_keys': ['result']
        }

        code = self.generator._generate_code(
            'AddNumbers', schema, pattern, [], 'coding'
        )

        self.assertIn('def AddNumbers', code)
        self.assertIn('return result', code)
        self.assertIn('try:', code)
        self.assertIn('except Exception', code)

    def test_generate_documentation(self):
        """Test documentation generation."""
        schema = SkillSchema(
            inputs={'x': {'type': 'int', 'description': 'First number'}},
            outputs={'result': {'type': 'int', 'description': 'Sum'}},
            required_inputs=['x'],
            required_outputs=['result']
        )

        doc = self.generator._generate_documentation('TestSkill', schema, [])
        self.assertIn('TestSkill', doc)
        self.assertIn('Input Parameters', doc)
        self.assertIn('Output Parameters', doc)


class TestSkillValidator(unittest.TestCase):
    """Tests for SkillValidator component."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_manager = DatabaseManager(
            os.path.join(self.temp_dir, 'test.db')
        )
        self.validator = SkillValidator(self.db_manager)

    def tearDown(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate_skill_success(self):
        """Test successful skill validation."""
        schema = SkillSchema(
            inputs={'x': {'type': 'int'}},
            outputs={'result': {'type': 'int'}},
            required_inputs=['x'],
            required_outputs=['result']
        )

        test_data = [
            {'inputs': {'x': 1}, 'outputs': {'result': 2}},
            {'inputs': {'x': 2}, 'outputs': {'result': 4}}
        ]

        code = "def test(): pass"
        result = self.validator.validate_skill(code, schema, test_data)

        self.assertIsInstance(result, ValidationResult)
        self.assertGreater(result.confidence_score, 0)

    def test_confidence_calculation(self):
        """Test confidence score calculation."""
        test_results_all_pass = {
            'passed': 10,
            'failed': 0,
            'total': 10,
            'errors': []
        }

        test_results_mixed = {
            'passed': 7,
            'failed': 3,
            'total': 10,
            'errors': ['error1', 'error2']
        }

        conf_all_pass = self.validator._calculate_confidence(test_results_all_pass)
        conf_mixed = self.validator._calculate_confidence(test_results_mixed)

        self.assertGreater(conf_all_pass, conf_mixed)
        self.assertGreaterEqual(conf_all_pass, 0.9)


class TestSkillLibraryManager(unittest.TestCase):
    """Tests for SkillLibraryManager component."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_manager = DatabaseManager(
            os.path.join(self.temp_dir, 'test.db')
        )
        self.library = SkillLibraryManager(self.db_manager)

    def tearDown(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_publish_skill(self):
        """Test skill publishing to library."""
        schema = SkillSchema(
            inputs={'data': {'type': 'list'}},
            outputs={'count': {'type': 'int'}},
            required_inputs=['data'],
            required_outputs=['count']
        )

        validation = ValidationResult(
            is_valid=True,
            confidence_score=0.95,
            test_passed=10,
            test_failed=0,
            test_total=10
        )

        skill_id = self.library.publish_skill(
            name="CountItems",
            code="def count(data): return len(data)",
            schema=schema,
            category="analysis",
            author="test_author",
            validation_result=validation
        )

        self.assertIsNotNone(skill_id)

        # Verify skill was stored
        stored_skill = self.db_manager.get_skill(skill_id)
        self.assertIsNotNone(stored_skill)
        # Skill name includes UUID suffix for uniqueness
        self.assertIn("CountItems", stored_skill['name'])

    def test_get_skill_by_name(self):
        """Test retrieving skill by name."""
        schema = SkillSchema(
            inputs={},
            outputs={},
            required_inputs=[],
            required_outputs=[]
        )

        validation = ValidationResult(
            is_valid=True,
            confidence_score=0.9,
            test_passed=5,
            test_failed=0,
            test_total=5
        )

        self.library.publish_skill(
            name="TestSkill",
            code="pass",
            schema=schema,
            category="analysis",
            author="test",
            validation_result=validation
        )

        found_skill = self.library.get_skill_by_name("TestSkill")
        self.assertIsNotNone(found_skill)
        # Skill name includes UUID suffix for uniqueness
        self.assertIn("TestSkill", found_skill['name'])

    def test_search_skills(self):
        """Test skill search functionality."""
        schema = SkillSchema(
            inputs={},
            outputs={},
            required_inputs=[],
            required_outputs=[]
        )

        validation = ValidationResult(
            is_valid=True,
            confidence_score=0.85,
            test_passed=8,
            test_failed=2,
            test_total=10
        )

        # Publish multiple skills
        for i in range(3):
            self.library.publish_skill(
                name=f"DataProcess_{i}",
                code="pass",
                schema=schema,
                category="analysis",
                author="test",
                validation_result=validation
            )

        results = self.library.search_skills("DataProcess")
        self.assertEqual(len(results), 3)


class TestSkillInheritanceSystem(unittest.TestCase):
    """Tests for SkillInheritanceSystem component."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_manager = DatabaseManager(
            os.path.join(self.temp_dir, 'test.db')
        )
        self.library = SkillLibraryManager(self.db_manager)
        self.inheritance = SkillInheritanceSystem(self.db_manager)

        # Create and publish a test skill
        schema = SkillSchema(
            inputs={},
            outputs={},
            required_inputs=[],
            required_outputs=[]
        )
        validation = ValidationResult(
            is_valid=True,
            confidence_score=0.9,
            test_passed=9,
            test_failed=1,
            test_total=10
        )
        self.skill_id = self.library.publish_skill(
            name="TestSkill",
            code="pass",
            schema=schema,
            category="analysis",
            author="test",
            validation_result=validation
        )

    def tearDown(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_grant_skill_to_agent(self):
        """Test granting skill to agent."""
        result = self.inheritance.grant_skill_to_agent("agent_1", self.skill_id)
        self.assertTrue(result)

    def test_get_agent_skills(self):
        """Test retrieving agent's skills."""
        # Grant skill to agent
        self.inheritance.grant_skill_to_agent("agent_1", self.skill_id)

        # Get agent's skills
        skills = self.inheritance.get_agent_skills("agent_1")
        self.assertEqual(len(skills), 1)
        self.assertEqual(skills[0]['skill_id'], self.skill_id)

    def test_distribute_skill_to_agents(self):
        """Test distributing skill to multiple agents."""
        agent_ids = ["agent_1", "agent_2", "agent_3"]
        results = self.inheritance.distribute_skill_to_agents(self.skill_id, agent_ids)

        self.assertEqual(len(results), 3)
        self.assertTrue(all(results.values()))

    def test_revoke_skill_from_agent(self):
        """Test revoking skill from agent."""
        # Grant skill
        self.inheritance.grant_skill_to_agent("agent_1", self.skill_id)

        # Verify granted
        skills = self.inheritance.get_agent_skills("agent_1")
        self.assertEqual(len(skills), 1)

        # Revoke skill
        self.inheritance.revoke_skill_from_agent("agent_1", self.skill_id)

        # Verify revoked
        skills = self.inheritance.get_agent_skills("agent_1")
        self.assertEqual(len(skills), 0)

    def test_log_skill_usage(self):
        """Test logging skill usage."""
        result = self.inheritance.log_skill_usage(
            agent_id="agent_1",
            skill_id=self.skill_id,
            execution_time_ms=250.5,
            success=True
        )
        self.assertTrue(result)


class TestUniVersSkillSystem(unittest.TestCase):
    """Integration tests for the complete UniVerse Skill System."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.system = UniVersSkillSystem(
            os.path.join(self.temp_dir, 'test.db')
        )

    def tearDown(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_complete_workflow(self):
        """Test complete skill creation and distribution workflow."""
        # Step 1: Learn from a task
        task_result = {
            'inputs': {'data': 'input_file.csv'},
            'outputs': {'analysis': 'report.pdf'},
            'operations': ['load', 'clean', 'analyze'],
            'data_volume': 2000
        }

        skill_id = self.system.learn_from_task(
            task_description="Analyze customer data",
            task_result=task_result,
            task_type="analysis",
            author="test_admin"
        )

        self.assertIsNotNone(skill_id)

        # Step 2: Distribute to agents
        agents = ["agent_1", "agent_2", "agent_3"]
        distribution = self.system.distribute_skill(skill_id, agents)
        self.assertEqual(sum(distribution.values()), 3)

        # Step 3: Verify agent capabilities
        agent_skills = self.system.get_agent_capabilities("agent_1")
        self.assertGreater(len(agent_skills), 0)

        # Step 4: Report usage
        for agent in agents:
            self.system.report_skill_usage(
                agent_id=agent,
                skill_id=skill_id,
                execution_time_ms=150.0,
                success=True
            )

        # Step 5: Check statistics
        stats = self.system.get_skill_stats()
        self.assertGreater(stats['total_skills'], 0)
        self.assertGreater(stats['published_skills'], 0)

    def test_skill_export_import(self):
        """Test exporting and importing skills."""
        # Create and publish a skill
        task_result = {
            'inputs': {'x': 5},
            'outputs': {'y': 10},
            'operations': ['double']
        }

        skill_id = self.system.learn_from_task(
            task_description="Double a number",
            task_result=task_result,
            task_type="math",
            author="test"
        )

        # Export skill
        exported = self.system.export_skill(skill_id)
        self.assertIsNotNone(exported)
        self.assertIn('skill', exported)

        # Import into new system
        new_system = UniVersSkillSystem(
            os.path.join(self.temp_dir, 'test2.db')
        )
        imported_id = new_system.import_skill(exported)
        self.assertIsNotNone(imported_id)

    def test_system_statistics(self):
        """Test system statistics gathering."""
        # Create multiple skills
        for i in range(3):
            task_result = {
                'inputs': {'data': f'data_{i}'},
                'outputs': {'result': f'result_{i}'},
                'operations': ['process']
            }

            self.system.learn_from_task(
                task_description=f"Task {i}",
                task_result=task_result,
                task_type="process",
                author="test"
            )

        stats = self.system.get_skill_stats()
        self.assertEqual(stats['total_skills'], 3)
        self.assertGreater(len(stats['categories']), 0)


def run_all_tests():
    """Run all tests and print summary."""
    print("\n" + "="*70)
    print("UniVerse Skill Generation System - Test Suite")
    print("="*70 + "\n")

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSkillExtractor))
    suite.addTests(loader.loadTestsFromTestCase(TestSkillGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestSkillValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestSkillLibraryManager))
    suite.addTests(loader.loadTestsFromTestCase(TestSkillInheritanceSystem))
    suite.addTests(loader.loadTestsFromTestCase(TestUniVersSkillSystem))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*70 + "\n")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)

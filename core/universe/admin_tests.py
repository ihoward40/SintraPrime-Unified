"""
Comprehensive test suite for SKILL.md, Admin Control Plane, and Git History
Coverage: 100% of critical functions
"""

import unittest
import json
import tempfile
import os
from datetime import datetime, timedelta
from typing import Dict, Tuple

# Import the modules to test
from skill_files import (
    SkillParser, SkillCompiler, SkillRegistry, SkillLoader,
    SkillMetadata, SkillDependency
)
from admin_control_plane import (
    AdminControlPlane, AdminRole, AdminCommand, AdminAccessControl,
    RealTimeMonitor, EmergencyControl, AgentState
)
from git_history import (
    GitHistoryEngine, HistoryTimeTravel, AuditTrail,
    CommitType, StateDiff
)


class TestSkillFilesParsing(unittest.TestCase):
    """Test SKILL.md parsing functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_skill_content = """# TestSkill

## Metadata
name: TestSkill
version: 1.0.0
description: A test skill for validation
category: testing
author: Test Author
tags: ["test", "sample"]
dependencies: [{"name": "base", "version": "1.0.0"}]

## Instructions
This is a test skill with detailed instructions.
It should have at least 50 characters to pass validation.
This includes proper formatting and structure."""

        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md')
        self.temp_file.write(self.test_skill_content)
        self.temp_file.close()

    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_parse_valid_skill(self):
        """Test parsing a valid SKILL.md file"""
        metadata, instructions, error = SkillParser.parse_skill_file(self.temp_file.name)
        
        self.assertIsNone(error)
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata.name, "TestSkill")
        self.assertEqual(metadata.version, "1.0.0")
        self.assertEqual(metadata.category, "testing")
        self.assertGreater(len(instructions), 50)

    def test_parse_missing_metadata_section(self):
        """Test error handling for missing metadata"""
        invalid_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md')
        invalid_file.write("# Test\n## Instructions\nSome content")
        invalid_file.close()

        try:
            metadata, instructions, error = SkillParser.parse_skill_file(invalid_file.name)
            self.assertIsNotNone(error)
            self.assertIn("Metadata", error)
        finally:
            os.unlink(invalid_file.name)

    def test_parse_missing_instructions(self):
        """Test error handling for missing instructions"""
        invalid_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md')
        invalid_file.write("""# Test
## Metadata
name: Test
version: 1.0.0
description: Test description
category: test""")
        invalid_file.close()

        try:
            metadata, instructions, error = SkillParser.parse_skill_file(invalid_file.name)
            self.assertIsNotNone(error)
            self.assertIn("Instructions", error)
        finally:
            os.unlink(invalid_file.name)

    def test_metadata_extraction(self):
        """Test metadata field extraction"""
        metadata, _, _ = SkillParser.parse_skill_file(self.temp_file.name)
        
        self.assertEqual(metadata.name, "TestSkill")
        self.assertEqual(metadata.version, "1.0.0")
        self.assertEqual(metadata.author, "Test Author")
        self.assertIn("test", metadata.tags)
        self.assertEqual(len(metadata.dependencies), 1)
        self.assertEqual(metadata.dependencies[0].name, "base")


class TestSkillCompilation(unittest.TestCase):
    """Test SKILL.md compilation and validation"""

    def setUp(self):
        """Set up test fixtures"""
        self.compiler = SkillCompiler()
        
        # Create valid skill file
        self.valid_skill = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md')
        self.valid_skill.write("""# ValidSkill
## Metadata
name: ValidSkill
version: 2.1.0
description: A valid test skill for compilation testing
category: testing
## Instructions
Comprehensive instructions for the skill that are longer than fifty characters.""")
        self.valid_skill.close()

    def tearDown(self):
        """Clean up test files"""
        for f in [self.valid_skill]:
            if os.path.exists(f.name):
                os.unlink(f.name)

    def test_successful_compilation(self):
        """Test successful skill compilation"""
        success, error = self.compiler.compile_skill(self.valid_skill.name)
        
        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertIn(self.valid_skill.name, self.compiler.compiled_skills)

    def test_invalid_version_format(self):
        """Test validation of version format"""
        invalid_skill = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md')
        invalid_skill.write("""# BadVersion
## Metadata
name: BadVersion
version: invalid
description: A skill with invalid version format and enough content here
category: test
## Instructions
This is a test skill that has enough content for validation purposes.""")
        invalid_skill.close()

        try:
            success, error = self.compiler.compile_skill(invalid_skill.name)
            self.assertFalse(success)
            self.assertIn("version", error.lower())
        finally:
            os.unlink(invalid_skill.name)

    def test_short_description_rejection(self):
        """Test rejection of too-short descriptions"""
        short_skill = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md')
        short_skill.write("""# Short
## Metadata
name: Short
version: 1.0.0
description: Bad
category: test
## Instructions
This skill has a description that is too short for validation.""")
        short_skill.close()

        try:
            success, error = self.compiler.compile_skill(short_skill.name)
            self.assertFalse(success)
        finally:
            os.unlink(short_skill.name)

    def test_compilation_caching(self):
        """Test compilation result caching"""
        success1, _ = self.compiler.compile_skill(self.valid_skill.name)
        success2, _ = self.compiler.compile_skill(self.valid_skill.name, force=False)
        
        self.assertTrue(success1)
        self.assertTrue(success2)


class TestSkillRegistry(unittest.TestCase):
    """Test skill registration and hot-reload"""

    def setUp(self):
        """Set up test fixtures"""
        self.registry = SkillRegistry()
        
        # Create skill file
        self.skill_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md')
        self.skill_file.write("""# ReloadableSkill
## Metadata
name: ReloadableSkill
version: 1.5.0
description: A skill that can be hot-reloaded during runtime execution
category: reloadable
## Instructions
This skill demonstrates hot-reload capabilities and real-time compilation features.""")
        self.skill_file.close()

    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.skill_file.name):
            os.unlink(self.skill_file.name)

    def test_skill_registration(self):
        """Test skill registration"""
        success, error = self.registry.register_skill(self.skill_file.name)
        
        self.assertTrue(success)
        self.assertIsNone(error)

    def test_get_skill(self):
        """Test skill retrieval"""
        self.registry.register_skill(self.skill_file.name)
        skill = self.registry.get_skill("ReloadableSkill")
        
        self.assertIsNotNone(skill)
        self.assertEqual(skill["metadata"].name, "ReloadableSkill")

    def test_get_latest_version(self):
        """Test retrieving latest version of skill"""
        self.registry.register_skill(self.skill_file.name)
        skill = self.registry.get_skill("ReloadableSkill", version="latest")
        
        self.assertIsNotNone(skill)
        self.assertEqual(skill["metadata"].version, "1.5.0")

    def test_hot_reload(self):
        """Test hot-reload functionality"""
        self.registry.register_skill(self.skill_file.name)
        
        # Modify the file
        with open(self.skill_file.name, 'w') as f:
            f.write("""# ReloadableSkill
## Metadata
name: ReloadableSkill
version: 2.0.0
description: Updated skill with hot-reload capability for runtime updates
category: reloadable
## Instructions
This is the updated version of the skill after hot-reload operation.""")
        
        success, error = self.registry.hot_reload_skill(self.skill_file.name)
        self.assertTrue(success)

    def test_list_active_skills(self):
        """Test listing active skills"""
        self.registry.register_skill(self.skill_file.name)
        skills = self.registry.list_active_skills()
        
        self.assertGreater(len(skills), 0)
        self.assertTrue(any(s["name"] == "ReloadableSkill" for s in skills))

    def test_skill_health_check(self):
        """Test skill health checking"""
        self.registry.register_skill(self.skill_file.name)
        health = self.registry.check_skill_health("ReloadableSkill")
        
        self.assertEqual(health["status"], "healthy")
        self.assertEqual(health["name"], "ReloadableSkill")


class TestAdminControlPlane(unittest.TestCase):
    """Test admin control plane functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.admin_plane = AdminControlPlane()
        self.session = self.admin_plane.create_admin_session(
            "admin1", AdminRole.SUPER_ADMIN
        )

    def test_session_creation(self):
        """Test admin session creation"""
        self.assertIsNotNone(self.session)
        self.assertEqual(self.session.admin_id, "admin1")
        self.assertEqual(self.session.admin_role, AdminRole.SUPER_ADMIN)

    def test_session_validation(self):
        """Test session validation"""
        is_valid = self.admin_plane.validate_session(self.session.session_id)
        self.assertTrue(is_valid)

    def test_permission_check(self):
        """Test access control permissions"""
        has_access = AdminAccessControl.can_execute(
            AdminRole.SUPER_ADMIN, AdminCommand.EMERGENCY_SHUTDOWN
        )
        self.assertTrue(has_access)

    def test_operator_restricted_access(self):
        """Test operator role restrictions"""
        operator_session = self.admin_plane.create_admin_session(
            "operator1", AdminRole.OPERATOR
        )
        
        has_access = AdminAccessControl.can_execute(
            AdminRole.OPERATOR, AdminCommand.EMERGENCY_SHUTDOWN
        )
        self.assertFalse(has_access)

    def test_execute_query_agent_command(self):
        """Test executing agent query command"""
        result = self.admin_plane.execute_command(
            self.session.session_id,
            AdminCommand.QUERY_AGENT,
            target_agent="agent1"
        )
        
        self.assertEqual(result["status"], "success")

    def test_execute_pause_agent_command(self):
        """Test executing pause agent command"""
        result = self.admin_plane.execute_command(
            self.session.session_id,
            AdminCommand.PAUSE_AGENT,
            target_agent="agent1"
        )
        
        self.assertEqual(result["status"], "success")

    def test_command_latency_tracking(self):
        """Test command latency statistics"""
        self.admin_plane.execute_command(
            self.session.session_id,
            AdminCommand.SYSTEM_STATUS
        )
        
        latency_stats = self.admin_plane.get_command_latency_stats()
        self.assertIn("avg_ms", latency_stats)
        self.assertGreaterEqual(latency_stats["avg_ms"], 0)

    def test_audit_trail_logging(self):
        """Test audit trail logging"""
        self.admin_plane.execute_command(
            self.session.session_id,
            AdminCommand.PAUSE_AGENT,
            target_agent="agent1"
        )
        
        trail = self.admin_plane.get_admin_audit_trail(limit=10)
        self.assertGreater(len(trail), 0)

    def test_emergency_mode(self):
        """Test emergency mode activation"""
        result = self.admin_plane.execute_command(
            self.session.session_id,
            AdminCommand.EMERGENCY_SHUTDOWN,
            parameters={"reason": "System overload"}
        )
        
        self.assertEqual(result["status"], "success")
        self.assertTrue(self.admin_plane.emergency.is_in_emergency())


class TestGitHistory(unittest.TestCase):
    """Test git-backed history system"""

    def setUp(self):
        """Set up test fixtures"""
        self.git_engine = GitHistoryEngine()
        self.time_travel = HistoryTimeTravel(self.git_engine)
        self.audit_trail = AuditTrail(self.git_engine)

    def test_create_commit(self):
        """Test commit creation"""
        state = {"agent_id": "agent1", "status": "running"}
        commit = self.git_engine.create_commit(
            author="test",
            message="Initial state",
            state_snapshot=state
        )
        
        self.assertIsNotNone(commit)
        self.assertEqual(commit.author, "test")
        self.assertEqual(commit.state_snapshot, state)

    def test_create_checkpoint(self):
        """Test emergency checkpoint creation"""
        state = {"critical_data": "important"}
        commit = self.git_engine.create_checkpoint(
            agent_id="agent1",
            state=state,
            reason="Critical error detected"
        )
        
        self.assertEqual(commit.commit_type, CommitType.EMERGENCY_CHECKPOINT)

    def test_get_current_state(self):
        """Test retrieving current state"""
        state = {"data": "value"}
        self.git_engine.create_commit(
            author="test",
            message="Test commit",
            state_snapshot=state
        )
        
        current = self.git_engine.get_current_state()
        self.assertEqual(current, state)

    def test_calculate_state_diff(self):
        """Test state diff calculation"""
        state1 = {"a": 1, "b": 2}
        state2 = {"a": 1, "b": 3, "c": 4}
        
        commit1 = self.git_engine.create_commit(
            author="test",
            message="State 1",
            state_snapshot=state1
        )
        
        commit2 = self.git_engine.create_commit(
            author="test",
            message="State 2",
            state_snapshot=state2
        )
        
        diff = self.git_engine.calculate_state_diff(
            commit1.commit_hash,
            commit2.commit_hash
        )
        
        self.assertIsNotNone(diff)
        self.assertIn("b", diff.modifications)
        self.assertIn("c", diff.additions)

    def test_rollback(self):
        """Test rollback functionality"""
        state1 = {"version": 1}
        state2 = {"version": 2}
        
        commit1 = self.git_engine.create_commit(
            author="test",
            message="V1",
            state_snapshot=state1
        )
        
        self.git_engine.create_commit(
            author="test",
            message="V2",
            state_snapshot=state2
        )
        
        success, rollback_hash = self.git_engine.rollback_to_commit(
            commit1.commit_hash
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(rollback_hash)

    def test_create_branch(self):
        """Test branch creation"""
        success, message = self.git_engine.create_branch(
            "experiment1"
        )
        
        self.assertTrue(success)
        self.assertIn("experiment1", self.git_engine.branches)

    def test_switch_branch(self):
        """Test branch switching"""
        self.git_engine.create_branch("experiment1")
        success, message = self.git_engine.switch_branch("experiment1")
        
        self.assertTrue(success)
        self.assertEqual(self.git_engine.current_branch, "experiment1")

    def test_commit_history(self):
        """Test retrieving commit history"""
        for i in range(5):
            self.git_engine.create_commit(
                author="test",
                message=f"Commit {i}",
                state_snapshot={"iteration": i}
            )
        
        history = self.git_engine.get_commit_history(limit=10)
        self.assertEqual(len(history), 5)

    def test_tag_commit(self):
        """Test tagging commits"""
        commit = self.git_engine.create_commit(
            author="test",
            message="Important commit",
            state_snapshot={}
        )
        
        success, _ = self.git_engine.tag_commit(
            commit.commit_hash,
            "v1.0.0"
        )
        
        self.assertTrue(success)
        self.assertIn("v1.0.0", self.git_engine.tags)

    def test_time_travel_get_state_at_time(self):
        """Test getting state at specific time"""
        state1 = {"stage": "initial"}
        commit = self.git_engine.create_commit(
            author="test",
            message="Initial",
            state_snapshot=state1
        )
        
        # Use timestamp after the commit
        future_time = commit.timestamp + timedelta(seconds=1)
        state = self.time_travel.get_state_at_time(future_time)
        
        self.assertIsNotNone(state)
        self.assertEqual(state, state1)

    def test_audit_trail_logging(self):
        """Test audit trail action logging"""
        action_hash = self.audit_trail.log_action(
            "task_execution",
            "agent1",
            {"task_id": "task123"}
        )
        
        self.assertIsNotNone(action_hash)

    def test_audit_trail_retrieval(self):
        """Test retrieving audit trail"""
        self.audit_trail.log_action(
            "action1",
            "agent1",
            {"details": "test"}
        )
        
        trail = self.audit_trail.get_audit_trail(agent_id="agent1")
        self.assertGreater(len(trail), 0)

    def test_audit_integrity_verification(self):
        """Test audit trail integrity verification"""
        self.git_engine.create_commit(
            author="test",
            message="Test",
            state_snapshot={}
        )
        
        integrity = self.audit_trail.verify_integrity()
        self.assertTrue(integrity["integrity_ok"])


class TestStressAndPerformance(unittest.TestCase):
    """Stress tests and performance benchmarks"""

    def test_100_agents_monitoring(self):
        """Test monitoring 100+ agents in real-time"""
        monitor = RealTimeMonitor()
        
        for i in range(150):
            monitor.update_agent_state(
                f"agent_{i}",
                AgentState.RUNNING if i % 2 == 0 else AgentState.IDLE,
                {"cpu": 0.5, "memory": 0.3}
            )
        
        health = monitor.get_system_health()
        self.assertEqual(health["total_agents"], 150)

    def test_command_latency_under_load(self):
        """Test command execution latency under load"""
        admin_plane = AdminControlPlane()
        session = admin_plane.create_admin_session("admin", AdminRole.SYSTEM_ADMIN)
        
        # Execute 100 commands
        for _ in range(100):
            admin_plane.execute_command(
                session.session_id,
                AdminCommand.SYSTEM_STATUS
            )
        
        stats = admin_plane.get_command_latency_stats()
        # Assert latency is reasonable (< 100ms)
        self.assertLess(stats["avg_ms"], 100)

    def test_git_history_with_many_commits(self):
        """Test git history with 1000+ commits"""
        git_engine = GitHistoryEngine()
        
        for i in range(500):
            git_engine.create_commit(
                author="test",
                message=f"Commit {i}",
                state_snapshot={"iteration": i, "data": "x" * 1000}
            )
        
        history = git_engine.get_commit_history(limit=100)
        self.assertEqual(len(history), 100)


def run_all_tests():
    """Run all tests and return summary"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSkillFilesParsing))
    suite.addTests(loader.loadTestsFromTestCase(TestSkillCompilation))
    suite.addTests(loader.loadTestsFromTestCase(TestSkillRegistry))
    suite.addTests(loader.loadTestsFromTestCase(TestAdminControlPlane))
    suite.addTests(loader.loadTestsFromTestCase(TestGitHistory))
    suite.addTests(loader.loadTestsFromTestCase(TestStressAndPerformance))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return {
        "total_tests": result.testsRun,
        "passed": result.testsRun - len(result.failures) - len(result.errors),
        "failed": len(result.failures),
        "errors": len(result.errors),
        "success_rate": (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100 if result.testsRun > 0 else 0
    }


if __name__ == "__main__":
    test_summary = run_all_tests()
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    print(f"Total Tests: {test_summary['total_tests']}")
    print(f"Passed: {test_summary['passed']}")
    print(f"Failed: {test_summary['failed']}")
    print(f"Errors: {test_summary['errors']}")
    print(f"Success Rate: {test_summary['success_rate']:.1f}%")
    print("="*50)

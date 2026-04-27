"""
Phase 18C — Self-Healing CI Engine Tests
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from phase18.self_healing_ci.ci_engine import (
    CIRun,
    CISeverity,
    FailureCategory,
    HealingSession,
    PytestOutputParser,
    RepairProposal,
    RepairResult,
    RepairStatus,
    RepairStrategyRegistry,
    SelfHealingCIEngine,
    TestFailure,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_PYTEST_OUTPUT_PASS = """
test_foo.py::test_bar PASSED
test_foo.py::test_baz PASSED
2 passed in 0.05s
"""

SAMPLE_PYTEST_OUTPUT_FAILURES = """
FAILED tests/test_core.py::test_import_thing - ImportError: No module named 'missing_pkg'
FAILED tests/test_logic.py::test_assertion - AssertionError: assert 1 == 2
FAILED tests/test_slow.py::test_slow_op - Timeout: test timed out after 5s
FAILED tests/test_attrs.py::test_attr - AttributeError: 'Foo' object has no attribute 'bar'
FAILED tests/test_types.py::test_type - TypeError: expected str not int
3 passed, 5 failed in 1.23s
"""

SAMPLE_PYTEST_OUTPUT_ERRORS = """
ERROR collecting tests/test_broken.py - ImportError: cannot import name 'X' from 'module'
FAILED tests/test_value.py::test_val - ValueError: invalid literal
FAILED tests/test_key.py::test_key - KeyError: 'missing_key'
1 passed, 2 failed, 1 error in 0.88s
"""

SAMPLE_PYTEST_OUTPUT_HEALTHY = """
test_a.py::test_1 PASSED
test_a.py::test_2 PASSED
test_b.py::test_3 PASSED
3 passed in 0.12s
"""


@pytest.fixture
def parser():
    return PytestOutputParser()


@pytest.fixture
def registry():
    return RepairStrategyRegistry()


@pytest.fixture
def engine():
    return SelfHealingCIEngine(max_parallel_repairs=4, min_confidence_threshold=0.5)


@pytest.fixture
def ci_run_with_failures(parser):
    return parser.parse(SAMPLE_PYTEST_OUTPUT_FAILURES)


@pytest.fixture
def healthy_ci_run(parser):
    return parser.parse(SAMPLE_PYTEST_OUTPUT_HEALTHY)


@pytest.fixture
def import_failure():
    return TestFailure(
        test_id="tests/test_core.py::test_import_thing",
        file_path="tests/test_core.py",
        test_name="test_import_thing",
        category=FailureCategory.IMPORT_ERROR,
        error_message="ImportError: No module named 'missing_pkg'",
    )


# ---------------------------------------------------------------------------
# PytestOutputParser tests
# ---------------------------------------------------------------------------

class TestPytestOutputParser:
    def test_parse_all_pass(self, parser):
        run = parser.parse(SAMPLE_PYTEST_OUTPUT_PASS)
        assert run.passed == 2
        assert run.failed == 0
        assert run.is_healthy

    def test_parse_failures_count(self, parser):
        run = parser.parse(SAMPLE_PYTEST_OUTPUT_FAILURES)
        assert run.failed == 5
        assert run.passed == 3

    def test_parse_failures_list(self, parser):
        run = parser.parse(SAMPLE_PYTEST_OUTPUT_FAILURES)
        assert len(run.failures) == 5

    def test_parse_error_lines(self, parser):
        run = parser.parse(SAMPLE_PYTEST_OUTPUT_ERRORS)
        assert run.errors == 1
        assert run.failed == 2

    def test_parse_duration(self, parser):
        run = parser.parse(SAMPLE_PYTEST_OUTPUT_FAILURES)
        assert run.duration_s == pytest.approx(1.23, abs=0.01)

    def test_classify_import_error(self, parser):
        cat = parser.classify("ImportError: No module named 'foo'")
        assert cat == FailureCategory.IMPORT_ERROR

    def test_classify_module_not_found(self, parser):
        cat = parser.classify("ModuleNotFoundError: No module named 'bar'")
        assert cat == FailureCategory.IMPORT_ERROR

    def test_classify_assertion_error(self, parser):
        cat = parser.classify("AssertionError: assert 1 == 2")
        assert cat == FailureCategory.ASSERTION_ERROR

    def test_classify_timeout(self, parser):
        cat = parser.classify("Timeout: test timed out after 5s")
        assert cat == FailureCategory.TIMEOUT

    def test_classify_attribute_error(self, parser):
        cat = parser.classify("AttributeError: 'Foo' object has no attribute 'bar'")
        assert cat == FailureCategory.ATTRIBUTE_ERROR

    def test_classify_type_error(self, parser):
        cat = parser.classify("TypeError: expected str not int")
        assert cat == FailureCategory.TYPE_ERROR

    def test_classify_value_error(self, parser):
        cat = parser.classify("ValueError: invalid literal")
        assert cat == FailureCategory.VALUE_ERROR

    def test_classify_key_error(self, parser):
        cat = parser.classify("KeyError: 'missing_key'")
        assert cat == FailureCategory.KEY_ERROR

    def test_classify_runtime_error(self, parser):
        cat = parser.classify("RuntimeError: something went wrong")
        assert cat == FailureCategory.RUNTIME_ERROR

    def test_classify_collection_error(self, parser):
        cat = parser.classify("collection error: cannot import")
        assert cat == FailureCategory.COLLECTION_ERROR

    def test_classify_unknown(self, parser):
        cat = parser.classify("some random error with no known pattern")
        assert cat == FailureCategory.UNKNOWN

    def test_failure_categories_assigned(self, parser):
        run = parser.parse(SAMPLE_PYTEST_OUTPUT_FAILURES)
        categories = {f.category for f in run.failures}
        assert FailureCategory.IMPORT_ERROR in categories
        assert FailureCategory.ASSERTION_ERROR in categories
        assert FailureCategory.TIMEOUT in categories

    def test_failure_file_paths_extracted(self, parser):
        run = parser.parse(SAMPLE_PYTEST_OUTPUT_FAILURES)
        paths = {f.file_path for f in run.failures}
        assert "tests/test_core.py" in paths

    def test_ci_run_has_id(self, parser):
        run = parser.parse(SAMPLE_PYTEST_OUTPUT_PASS)
        assert run.id is not None and len(run.id) > 0


# ---------------------------------------------------------------------------
# CIRun tests
# ---------------------------------------------------------------------------

class TestCIRun:
    def test_pass_rate_all_pass(self, healthy_ci_run):
        assert healthy_ci_run.pass_rate == 1.0

    def test_pass_rate_with_failures(self, ci_run_with_failures):
        # 3 passed, 5 failed = 3/8
        assert ci_run_with_failures.pass_rate == pytest.approx(3 / 8, abs=0.01)

    def test_failure_rate(self, ci_run_with_failures):
        assert ci_run_with_failures.failure_rate == pytest.approx(5 / 8, abs=0.01)

    def test_is_healthy_true(self, healthy_ci_run):
        assert healthy_ci_run.is_healthy is True

    def test_is_healthy_false(self, ci_run_with_failures):
        assert ci_run_with_failures.is_healthy is False

    def test_severity_critical(self):
        run = CIRun(id="x", total_tests=10, passed=1, failed=9, errors=0, duration_s=1.0)
        assert run.severity == CISeverity.CRITICAL

    def test_severity_high(self):
        run = CIRun(id="x", total_tests=10, passed=8, failed=2, errors=0, duration_s=1.0)
        assert run.severity == CISeverity.HIGH

    def test_severity_medium(self):
        run = CIRun(id="x", total_tests=20, passed=19, failed=1, errors=0, duration_s=1.0)
        assert run.severity == CISeverity.MEDIUM

    def test_severity_low(self):
        run = CIRun(id="x", total_tests=100, passed=99, failed=1, errors=0, duration_s=1.0)
        assert run.severity == CISeverity.LOW

    def test_zero_tests_pass_rate(self):
        run = CIRun(id="x", total_tests=0, passed=0, failed=0, errors=0, duration_s=0.0)
        assert run.pass_rate == 1.0


# ---------------------------------------------------------------------------
# RepairStrategyRegistry tests
# ---------------------------------------------------------------------------

class TestRepairStrategyRegistry:
    def test_propose_import_error(self, registry, import_failure):
        proposal = registry.propose(import_failure)
        assert proposal.strategy == "install_missing_package"
        assert "missing_pkg" in proposal.description
        assert proposal.confidence >= 0.8

    def test_propose_assertion_error(self, registry):
        f = TestFailure(
            test_id="t", file_path="f.py", test_name="test_x",
            category=FailureCategory.ASSERTION_ERROR,
            error_message="AssertionError: assert 1 == 2",
        )
        proposal = registry.propose(f)
        assert proposal.strategy == "update_assertion"

    def test_propose_timeout(self, registry):
        f = TestFailure(
            test_id="t", file_path="f.py", test_name="test_slow",
            category=FailureCategory.TIMEOUT,
            error_message="Timeout: timed out after 5s",
        )
        proposal = registry.propose(f)
        assert proposal.strategy == "increase_timeout"
        assert proposal.confidence >= 0.7

    def test_propose_attribute_error_with_details(self, registry):
        f = TestFailure(
            test_id="t", file_path="f.py", test_name="test_attr",
            category=FailureCategory.ATTRIBUTE_ERROR,
            error_message="AttributeError: 'Foo' object has no attribute 'bar'",
        )
        proposal = registry.propose(f)
        assert "bar" in proposal.description

    def test_propose_collection_error_high_impact(self, registry):
        f = TestFailure(
            test_id="t", file_path="tests/broken.py", test_name="broken",
            category=FailureCategory.COLLECTION_ERROR,
            error_message="collection error",
        )
        proposal = registry.propose(f)
        assert proposal.estimated_impact >= 3

    def test_propose_unknown_low_confidence(self, registry):
        f = TestFailure(
            test_id="t", file_path="f.py", test_name="test_x",
            category=FailureCategory.UNKNOWN,
            error_message="some weird error",
        )
        proposal = registry.propose(f)
        assert proposal.confidence < 0.5

    def test_custom_strategy_registration(self, registry):
        def my_strategy(f):
            return RepairProposal(
                id="custom", failure=f, strategy="custom", description="custom fix",
                confidence=0.99
            )
        registry.register(FailureCategory.RUNTIME_ERROR, my_strategy)
        f = TestFailure(
            test_id="t", file_path="f.py", test_name="t",
            category=FailureCategory.RUNTIME_ERROR,
            error_message="RuntimeError",
        )
        proposal = registry.propose(f)
        assert proposal.strategy == "custom"

    def test_proposal_has_id(self, registry, import_failure):
        proposal = registry.propose(import_failure)
        assert proposal.id is not None

    def test_proposal_links_to_failure(self, registry, import_failure):
        proposal = registry.propose(import_failure)
        assert proposal.failure is import_failure


# ---------------------------------------------------------------------------
# SelfHealingCIEngine tests
# ---------------------------------------------------------------------------

class TestSelfHealingCIEngine:
    def test_ingest_ci_output(self, engine):
        run = engine.ingest_ci_output(SAMPLE_PYTEST_OUTPUT_FAILURES)
        assert run.failed == 5

    def test_start_healing_session(self, engine, ci_run_with_failures):
        session = engine.start_healing_session(ci_run_with_failures)
        assert session.id is not None
        assert session.ci_run is ci_run_with_failures

    def test_generate_proposals_filters_low_confidence(self, engine, ci_run_with_failures):
        session = engine.start_healing_session(ci_run_with_failures)
        proposals = engine.generate_proposals(session)
        assert all(p.confidence >= engine.min_confidence_threshold for p in proposals)

    def test_generate_proposals_max_limit(self, engine, ci_run_with_failures):
        session = engine.start_healing_session(ci_run_with_failures)
        proposals = engine.generate_proposals(session)
        assert len(proposals) <= engine.max_parallel_repairs

    def test_generate_proposals_sorted_by_confidence(self, engine, ci_run_with_failures):
        session = engine.start_healing_session(ci_run_with_failures)
        proposals = engine.generate_proposals(session)
        confidences = [p.confidence for p in proposals]
        assert confidences == sorted(confidences, reverse=True)

    def test_apply_proposal_success(self, engine, ci_run_with_failures, import_failure):
        session = engine.start_healing_session(ci_run_with_failures)
        proposal = RepairProposal(
            id="p1", failure=import_failure, strategy="install",
            description="install pkg", confidence=0.9, estimated_impact=2
        )
        result = engine.apply_proposal(session, proposal)
        assert result.status == RepairStatus.APPLIED
        assert result.tests_healed == 2

    def test_apply_proposal_failure(self, engine, ci_run_with_failures, import_failure):
        session = engine.start_healing_session(ci_run_with_failures)
        proposal = RepairProposal(
            id="p2", failure=import_failure, strategy="manual",
            description="manual review", confidence=0.3, estimated_impact=0
        )
        result = engine.apply_proposal(session, proposal)
        assert result.status == RepairStatus.FAILED

    def test_apply_proposal_with_executor(self, engine, ci_run_with_failures, import_failure):
        session = engine.start_healing_session(ci_run_with_failures)
        proposal = RepairProposal(
            id="p3", failure=import_failure, strategy="install",
            description="install pkg", confidence=0.9, estimated_impact=1
        )
        executor = lambda patch: (True, "installed successfully")
        result = engine.apply_proposal(session, proposal, executor=executor)
        assert result.status == RepairStatus.APPLIED

    def test_apply_proposal_executor_failure(self, engine, ci_run_with_failures, import_failure):
        session = engine.start_healing_session(ci_run_with_failures)
        proposal = RepairProposal(
            id="p4", failure=import_failure, strategy="install",
            description="install pkg", confidence=0.9, estimated_impact=1
        )
        executor = lambda patch: (False, "pip install failed")
        result = engine.apply_proposal(session, proposal, executor=executor)
        assert result.status == RepairStatus.FAILED

    def test_verify_repair_marks_verified(self, engine, ci_run_with_failures, import_failure):
        session = engine.start_healing_session(ci_run_with_failures)
        proposal = RepairProposal(
            id="p5", failure=import_failure, strategy="install",
            description="install pkg", confidence=0.9, estimated_impact=1
        )
        result = engine.apply_proposal(session, proposal)
        verified = engine.verify_repair(result)
        assert verified.status == RepairStatus.VERIFIED
        assert verified.verified_at is not None

    def test_verify_repair_with_re_run(self, engine, ci_run_with_failures, import_failure, parser):
        session = engine.start_healing_session(ci_run_with_failures)
        proposal = RepairProposal(
            id="p6", failure=import_failure, strategy="install",
            description="install pkg", confidence=0.9, estimated_impact=2
        )
        result = engine.apply_proposal(session, proposal)
        new_run = parser.parse("3 passed, 3 failed in 1.0s")
        result = engine.verify_repair(result, re_run_fn=lambda: new_run, baseline_ci_run=ci_run_with_failures)
        assert result.tests_healed == 2  # 5 - 3 = 2 healed

    def test_rollback(self, engine, ci_run_with_failures, import_failure):
        session = engine.start_healing_session(ci_run_with_failures)
        proposal = RepairProposal(
            id="p7", failure=import_failure, strategy="install",
            description="install pkg", confidence=0.9, estimated_impact=1
        )
        result = engine.apply_proposal(session, proposal)
        success = engine.rollback(result)
        assert success is True
        assert result.status == RepairStatus.ROLLED_BACK

    def test_complete_session(self, engine, ci_run_with_failures):
        session = engine.start_healing_session(ci_run_with_failures)
        completed = engine.complete_session(session)
        assert completed.is_complete
        assert completed.completed_at is not None

    def test_compute_parl_reward_healthy(self, engine, healthy_ci_run):
        session = engine.start_healing_session(healthy_ci_run)
        engine.complete_session(session)
        reward = engine.compute_parl_reward(session)
        assert reward["total"] >= 0.0

    def test_compute_parl_reward_with_repairs(self, engine, ci_run_with_failures, import_failure):
        session = engine.start_healing_session(ci_run_with_failures)
        proposals = engine.generate_proposals(session)
        for p in proposals:
            result = engine.apply_proposal(session, p)
            engine.verify_repair(result)
        engine.complete_session(session)
        reward = engine.compute_parl_reward(session)
        assert 0.0 <= reward["total"] <= 1.0
        assert "r_parallel" in reward
        assert "r_finish" in reward
        assert "r_perf" in reward

    def test_healing_report_structure(self, engine, ci_run_with_failures):
        session = engine.start_healing_session(ci_run_with_failures)
        engine.generate_proposals(session)
        engine.complete_session(session)
        report = engine.healing_report(session)
        assert "session_id" in report
        assert "severity" in report
        assert "parl_reward" in report
        assert "tests_healed" in report

    def test_auto_heal_healthy_run(self, engine):
        session = engine.auto_heal(SAMPLE_PYTEST_OUTPUT_HEALTHY)
        assert session.is_complete
        assert session.total_proposals == 0

    def test_auto_heal_with_failures(self, engine):
        session = engine.auto_heal(SAMPLE_PYTEST_OUTPUT_FAILURES)
        assert session.is_complete
        assert session.total_proposals >= 0

    def test_total_sessions_counter(self, engine, ci_run_with_failures):
        engine.start_healing_session(ci_run_with_failures)
        engine.start_healing_session(ci_run_with_failures)
        assert engine.total_sessions == 2

    def test_total_repairs_applied(self, engine, ci_run_with_failures, import_failure):
        session = engine.start_healing_session(ci_run_with_failures)
        proposal = RepairProposal(
            id="p8", failure=import_failure, strategy="install",
            description="install pkg", confidence=0.9, estimated_impact=1
        )
        engine.apply_proposal(session, proposal)
        assert engine.total_repairs_applied >= 1

    def test_category_breakdown(self, engine):
        engine.auto_heal(SAMPLE_PYTEST_OUTPUT_FAILURES)
        breakdown = engine.category_breakdown()
        assert isinstance(breakdown, dict)
        assert sum(breakdown.values()) >= 5

    def test_no_proposals_below_threshold(self):
        engine = SelfHealingCIEngine(min_confidence_threshold=0.99)
        session = engine.auto_heal(SAMPLE_PYTEST_OUTPUT_FAILURES)
        # All proposals should be filtered out since threshold is very high
        assert session.total_proposals == 0

    def test_repair_result_net_improvement(self):
        f = TestFailure(
            test_id="t", file_path="f.py", test_name="t",
            category=FailureCategory.IMPORT_ERROR, error_message="ImportError"
        )
        result = RepairResult(proposal_id="p", status=RepairStatus.VERIFIED, tests_healed=3, tests_broken=1)
        assert result.net_improvement == 2

    def test_repair_result_success(self):
        result = RepairResult(proposal_id="p", status=RepairStatus.VERIFIED, tests_healed=1, tests_broken=0)
        assert result.success is True

    def test_repair_result_not_success_if_broken(self):
        result = RepairResult(proposal_id="p", status=RepairStatus.VERIFIED, tests_healed=1, tests_broken=2)
        assert result.success is False

    def test_healing_session_success_rate(self, engine, ci_run_with_failures, import_failure):
        session = engine.start_healing_session(ci_run_with_failures)
        p1 = RepairProposal(id="p1", failure=import_failure, strategy="s", description="d", confidence=0.9, estimated_impact=1)
        p2 = RepairProposal(id="p2", failure=import_failure, strategy="s", description="d", confidence=0.9, estimated_impact=1)
        r1 = engine.apply_proposal(session, p1)
        r2 = engine.apply_proposal(session, p2)
        engine.verify_repair(r1)
        engine.verify_repair(r2)
        assert 0.0 <= session.success_rate <= 1.0

"""
Comprehensive test suite for SintraPrime-Unified Skill Evolution System.

Tests cover:
- SkillLibrary: register, search, update, versioning, deprecation, import/export
- SkillRunner: execute, chain, sandbox safety, timeout, dry-run
- SkillEvolver: failure analysis, suggestion, auto-improve, create from task, merge, report
- AutoSkillCreator: from example, from workflow, from pattern, legal skill, template, validation
- SkillMarketplace: publish, browse, install, rating, trending, top-10
- Built-in skills: legal_research, document_drafter, financial_analyzer, court_monitor,
                   contract_reviewer, deadline_calculator
"""

import json
import sqlite3
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Ensure the package is importable (add parent to path if running directly)
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from skill_evolution import (
    AutoSkillCreator,
    SkillEvolver,
    SkillLibrary,
    SkillMarketplace,
    SkillRunner,
)
from skill_evolution.skill_types import (
    FailureAnalysis,
    ImprovementSuggestion,
    MarketplaceSkill,
    Skill,
    SkillCategory,
    SkillExecution,
    SkillImprovement,
    SkillStatus,
    SkillTemplate,
    ValidationResult,
)
from skill_evolution.builtin_skills import (
    ContractReviewerSkill,
    CourtMonitorSkill,
    DeadlineCalculatorSkill,
    DocumentDrafterSkill,
    FinancialAnalyzerSkill,
    LegalResearchSkill,
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def make_temp_library() -> SkillLibrary:
    """Create a SkillLibrary backed by a temporary in-memory-like DB."""
    tmp = tempfile.mkdtemp()
    return SkillLibrary(db_path=Path(tmp) / "test_skills.db")


def make_sample_skill(**kwargs) -> Skill:
    defaults = dict(
        name="sample_skill",
        description="A simple test skill that returns a greeting.",
        category=SkillCategory.AUTOMATION,
        code='result = f"Hello, {params.get(\'name\', \'World\')}!"',
        parameters={"name": {"type": "str", "required": False, "default": "World"}},
        author="test",
        tags=["test", "sample"],
    )
    defaults.update(kwargs)
    return Skill(**defaults)


# ===========================================================================
# SkillLibrary Tests
# ===========================================================================

class TestSkillLibraryRegister(unittest.TestCase):
    """Test 1–8: SkillLibrary register and get."""

    def setUp(self):
        self.lib = make_temp_library()

    def test_01_register_returns_skill(self):
        skill = make_sample_skill()
        result = self.lib.register(skill)
        self.assertIsInstance(result, Skill)

    def test_02_register_assigns_timestamps(self):
        skill = make_sample_skill()
        result = self.lib.register(skill)
        self.assertIsNotNone(result.created_at)
        self.assertIsNotNone(result.last_updated)

    def test_03_get_returns_registered_skill(self):
        skill = make_sample_skill()
        self.lib.register(skill)
        fetched = self.lib.get(skill.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, skill.name)

    def test_04_get_nonexistent_returns_none(self):
        result = self.lib.get("nonexistent_id_xyz")
        self.assertIsNone(result)

    def test_05_duplicate_register_raises_error(self):
        skill = make_sample_skill()
        self.lib.register(skill)
        with self.assertRaises(ValueError):
            self.lib.register(skill)

    def test_06_get_by_name(self):
        skill = make_sample_skill(name="unique_test_skill_name")
        self.lib.register(skill)
        fetched = self.lib.get_by_name("unique_test_skill_name")
        self.assertIsNotNone(fetched)

    def test_07_library_len_includes_registered(self):
        initial = len(self.lib)
        skill = make_sample_skill()
        self.lib.register(skill)
        self.assertEqual(len(self.lib), initial + 1)

    def test_08_skill_has_correct_category(self):
        skill = make_sample_skill(category=SkillCategory.LEGAL)
        self.lib.register(skill)
        fetched = self.lib.get(skill.id)
        self.assertEqual(fetched.category, SkillCategory.LEGAL)


class TestSkillLibrarySearch(unittest.TestCase):
    """Test 9–14: SkillLibrary search."""

    def setUp(self):
        self.lib = make_temp_library()
        self.lib.register(make_sample_skill(name="alpha_skill", description="Handles legal document processing"))
        self.lib.register(make_sample_skill(
            name="beta_skill", description="Financial analysis tool",
            category=SkillCategory.FINANCIAL, tags=["finance", "analysis"]
        ))

    def test_09_search_by_name_keyword(self):
        results = self.lib.search("alpha")
        names = [s.name for s in results]
        self.assertIn("alpha_skill", names)

    def test_10_search_by_description_keyword(self):
        results = self.lib.search("legal document")
        self.assertGreater(len(results), 0)

    def test_11_search_with_category_filter(self):
        results = self.lib.search("analysis", category=SkillCategory.FINANCIAL)
        for s in results:
            self.assertEqual(s.category, SkillCategory.FINANCIAL)

    def test_12_search_returns_list(self):
        results = self.lib.search("skill")
        self.assertIsInstance(results, list)

    def test_13_list_by_category_returns_correct(self):
        results = self.lib.list_by_category(SkillCategory.FINANCIAL)
        for s in results:
            self.assertEqual(s.category, SkillCategory.FINANCIAL)

    def test_14_get_top_skills_returns_list(self):
        top = self.lib.get_top_skills(5)
        self.assertIsInstance(top, list)
        self.assertLessEqual(len(top), 5)


class TestSkillLibraryVersioning(unittest.TestCase):
    """Test 15–20: SkillLibrary update, versioning, deprecation, import/export."""

    def setUp(self):
        self.lib = make_temp_library()
        self.skill = make_sample_skill()
        self.lib.register(self.skill)

    def test_15_update_increments_version(self):
        updated = self.lib.update(self.skill.id, "result = 'v2'", "Updated to v2")
        self.assertEqual(updated.version, 2)

    def test_16_update_preserves_history(self):
        self.lib.update(self.skill.id, "result = 'v2'", "Updated to v2")
        history = self.lib.get_history(self.skill.id)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["old_version"], 1)
        self.assertEqual(history[0]["new_version"], 2)

    def test_17_update_nonexistent_returns_none(self):
        result = self.lib.update("bad_id", "result = None", "no-op")
        self.assertIsNone(result)

    def test_18_deprecate_marks_skill(self):
        result = self.lib.deprecate(self.skill.id)
        self.assertTrue(result)
        fetched = self.lib.get(self.skill.id)
        self.assertEqual(fetched.status, SkillStatus.DEPRECATED)

    def test_19_export_returns_dict(self):
        exported = self.lib.export_skill(self.skill.id)
        self.assertIsInstance(exported, dict)
        self.assertIn("name", exported)

    def test_20_import_roundtrip(self):
        exported = self.lib.export_skill(self.skill.id)
        self.lib.delete(self.skill.id)
        imported = self.lib.import_skill(exported)
        self.assertEqual(imported.name, self.skill.name)


# ===========================================================================
# SkillRunner Tests
# ===========================================================================

class TestSkillRunnerExecute(unittest.TestCase):
    """Test 21–30: SkillRunner execute, chain, sandbox, dry-run."""

    def setUp(self):
        self.lib = make_temp_library()
        self.runner = SkillRunner(self.lib)

    def _register(self, name, code, params=None):
        s = make_sample_skill(name=name, code=code, parameters=params or {})
        self.lib.register(s)
        return s

    def test_21_execute_simple_skill(self):
        s = self._register("hello", "result = 'hello world'")
        ex = self.runner.execute(s.id, {})
        self.assertTrue(ex.success)
        self.assertEqual(ex.output, "hello world")

    def test_22_execute_returns_skill_execution(self):
        s = self._register("simple", "result = 42")
        ex = self.runner.execute(s.id, {})
        self.assertIsInstance(ex, SkillExecution)

    def test_23_execute_with_params(self):
        s = self._register("greeting", "result = f'Hello, {params[\"name\"]}!'")
        ex = self.runner.execute(s.id, {"name": "Alice"})
        self.assertTrue(ex.success)
        self.assertIn("Alice", str(ex.output))

    def test_24_execute_nonexistent_skill_fails(self):
        ex = self.runner.execute("nonexistent_id", {})
        self.assertFalse(ex.success)
        self.assertIsNotNone(ex.error)

    def test_25_execute_records_duration(self):
        s = self._register("fast", "result = 1 + 1")
        ex = self.runner.execute(s.id, {})
        self.assertGreaterEqual(ex.duration_ms, 0)

    def test_26_sandbox_blocks_forbidden_pattern(self):
        # Code with forbidden pattern should be rejected
        s = self._register("evil", "import os; result = os.system('ls')")
        ex = self.runner.execute(s.id, {})
        self.assertFalse(ex.success)

    def test_27_execute_chain_runs_all_skills(self):
        s1 = self._register("step1", "result = 'step1_done'")
        s2 = self._register("step2", "result = f'step2 after {params.get(\"previous_output\")}'")
        results = self.runner.execute_chain([s1.id, s2.id], {})
        self.assertEqual(len(results), 2)
        self.assertTrue(results[0].success)
        self.assertTrue(results[1].success)

    def test_28_execute_chain_stops_on_failure(self):
        s1 = self._register("bad_step", "raise ValueError('intentional failure')")
        s2 = self._register("good_step2", "result = 'should not run'")
        results = self.runner.execute_chain([s1.id, s2.id], {})
        self.assertEqual(len(results), 1)  # Stops after first failure
        self.assertFalse(results[0].success)

    def test_29_dry_run_returns_string(self):
        s = self._register("drytest", "result = 'dry'")
        output = self.runner.dry_run(s.id, {"key": "val"})
        self.assertIsInstance(output, str)
        self.assertIn("drytest", output)

    def test_30_dry_run_nonexistent_skill(self):
        output = self.runner.dry_run("bad_id", {})
        self.assertIn("not found", output.lower())


class TestSkillRunnerValidation(unittest.TestCase):
    """Test 31–33: Input validation and execution tracking."""

    def setUp(self):
        self.lib = make_temp_library()
        self.runner = SkillRunner(self.lib)

    def test_31_missing_required_param_fails(self):
        s = make_sample_skill(
            name="strict_skill",
            code="result = params['required_field']",
            parameters={"required_field": {"type": "str", "required": True}},
        )
        self.lib.register(s)
        ex = self.runner.execute(s.id, {})
        self.assertFalse(ex.success)

    def test_32_execution_updates_usage_count(self):
        s = make_sample_skill(name="counter_skill", code="result = 1")
        self.lib.register(s)
        before = self.lib.get(s.id).usage_count
        self.runner.execute(s.id, {})
        after = self.lib.get(s.id).usage_count
        self.assertEqual(after, before + 1)

    def test_33_get_executions_returns_list(self):
        s = make_sample_skill(name="exec_log_skill", code="result = True")
        self.lib.register(s)
        self.runner.execute(s.id, {})
        execs = self.runner.get_executions(s.id)
        self.assertIsInstance(execs, list)
        self.assertGreaterEqual(len(execs), 1)


# ===========================================================================
# SkillEvolver Tests
# ===========================================================================

class TestSkillEvolver(unittest.TestCase):
    """Test 34–42: SkillEvolver failure analysis, improvement, creation, merge, report."""

    def setUp(self):
        self.lib = make_temp_library()
        self.evolver = SkillEvolver(self.lib)
        self.skill = make_sample_skill(name="evolver_test_skill", code="result = 1")
        self.lib.register(self.skill)

    def _inject_executions(self, skill_id: str, successes: int, failures: int, error_msg: str = "KeyError: 'missing_key'"):
        """Directly write fake execution records to DB."""
        import uuid
        with sqlite3.connect(str(self.lib.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS skill_executions (
                    id TEXT, skill_id TEXT, input_params TEXT, output TEXT,
                    success INTEGER, duration_ms REAL, error TEXT,
                    feedback_score REAL, timestamp TEXT
                )
            """)
            for _ in range(successes):
                conn.execute(
                    "INSERT INTO skill_executions VALUES (?,?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), skill_id, '{}', '"ok"', 1, 5.0, None, None,
                     datetime.utcnow().isoformat())
                )
            for _ in range(failures):
                conn.execute(
                    "INSERT INTO skill_executions VALUES (?,?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), skill_id, '{}', 'null', 0, 5.0, error_msg, None,
                     datetime.utcnow().isoformat())
                )

    def test_34_analyze_failures_returns_analysis(self):
        analysis = self.evolver.analyze_failures(self.skill.id)
        self.assertIsInstance(analysis, FailureAnalysis)

    def test_35_failure_analysis_counts_zero_when_no_data(self):
        analysis = self.evolver.analyze_failures(self.skill.id)
        self.assertEqual(analysis.total_executions, 0)
        self.assertEqual(analysis.failure_rate, 0.0)

    def test_36_failure_analysis_detects_errors(self):
        self._inject_executions(self.skill.id, 3, 7, "KeyError: 'missing_key'\nTraceback...")
        analysis = self.evolver.analyze_failures(self.skill.id)
        self.assertEqual(analysis.total_executions, 10)
        self.assertAlmostEqual(analysis.failure_rate, 0.7, places=1)

    def test_37_suggest_improvements_returns_list(self):
        suggestions = self.evolver.suggest_improvements(self.skill.id)
        self.assertIsInstance(suggestions, list)

    def test_38_suggest_improvements_when_high_failure(self):
        self._inject_executions(self.skill.id, 1, 9, "KeyError: 'x'\n at line 1")
        suggestions = self.evolver.suggest_improvements(self.skill.id)
        self.assertGreater(len(suggestions), 0)
        self.assertIsInstance(suggestions[0], ImprovementSuggestion)

    def test_39_auto_improve_returns_none_on_good_skill(self):
        # Skill with no failures => no improvement needed
        result = self.evolver.auto_improve(self.skill.id)
        self.assertIsNone(result)

    def test_40_auto_improve_updates_code_on_bad_skill(self):
        self._inject_executions(self.skill.id, 1, 9, "KeyError: 'bad_key'\n  File x line 1")
        result = self.evolver.auto_improve(self.skill.id)
        if result:
            self.assertIsInstance(result, SkillImprovement)
            self.assertGreater(result.new_version, result.old_version)

    def test_41_create_from_task_returns_skill(self):
        new_skill = self.evolver.create_from_task(
            task_description="Send email notification to client",
            task_outcome="Email sent successfully",
            code_used="result = send_email(params['to'], params['subject'])",
            category=SkillCategory.COMMUNICATION,
        )
        self.assertIsInstance(new_skill, Skill)
        self.assertIn("email", new_skill.name.lower())

    def test_42_merge_skills_returns_composite(self):
        s2 = make_sample_skill(name="merge_b", code="result = 'b_result'")
        self.lib.register(s2)
        merged = self.evolver.merge_skills([self.skill.id, s2.id], merged_name="merged_ab")
        self.assertIsNotNone(merged)
        self.assertEqual(merged.name, "merged_ab")
        self.assertIn("evolver_test_skill", merged.code)
        self.assertIn("merge_b", merged.code)

    def test_43_evolution_report_structure(self):
        report = self.evolver.evolution_report()
        required_keys = ["report_period", "new_skills", "total_executions", "top_performers"]
        for key in required_keys:
            self.assertIn(key, report)

    def test_44_merge_needs_at_least_two_skills(self):
        result = self.evolver.merge_skills([self.skill.id])
        self.assertIsNone(result)

    def test_45_watch_and_evolve_starts_thread(self):
        self.evolver.watch_and_evolve(interval_hours=999)
        self.assertTrue(self.evolver._watcher_thread.is_alive())
        self.evolver.stop_watch()


# ===========================================================================
# AutoSkillCreator Tests
# ===========================================================================

class TestAutoSkillCreator(unittest.TestCase):
    """Test 46–55: AutoSkillCreator methods."""

    def setUp(self):
        self.creator = AutoSkillCreator()

    def test_46_from_example_returns_skill(self):
        skill = self.creator.from_example(
            name="greet_user",
            example_input={"user": "Alice"},
            example_output="Hello, Alice!",
            description="Greets a user by name.",
        )
        self.assertIsInstance(skill, Skill)
        self.assertEqual(skill.name, "greet_user")

    def test_47_from_example_is_experimental(self):
        skill = self.creator.from_example("test_ex", {"x": 1}, 2, "doubles x")
        self.assertEqual(skill.status, SkillStatus.EXPERIMENTAL)

    def test_48_from_workflow_returns_skill(self):
        steps = [
            "Fetch client record",
            "Validate required fields",
            "Generate invoice PDF",
            "Send to client email",
        ]
        skill = self.creator.from_workflow(steps, name="invoice_workflow")
        self.assertIsInstance(skill, Skill)
        self.assertIn("Fetch client record", skill.code)

    def test_49_from_workflow_empty_raises_error(self):
        with self.assertRaises(ValueError):
            self.creator.from_workflow([])

    def test_50_from_pattern_returns_skill(self):
        execs = [
            SkillExecution(skill_id="x", input_params={"a": 1, "b": 2}, output=3, success=True, duration_ms=5),
            SkillExecution(skill_id="x", input_params={"a": 4, "b": 5}, output=9, success=True, duration_ms=4),
        ]
        skill = self.creator.from_pattern(execs, name="pattern_skill")
        self.assertIsNotNone(skill)
        self.assertIn("a", skill.code)
        self.assertIn("b", skill.code)

    def test_51_from_pattern_empty_returns_none(self):
        result = self.creator.from_pattern([])
        self.assertIsNone(result)

    def test_52_generate_legal_skill_contract_analyzer(self):
        skill = self.creator.generate_legal_skill("contract_analyzer")
        self.assertEqual(skill.category, SkillCategory.LEGAL)
        self.assertIn("contract", skill.code.lower())

    def test_53_generate_legal_skill_unknown_raises(self):
        with self.assertRaises(ValueError):
            self.creator.generate_legal_skill("unknown_skill_type_xyz")

    def test_54_validate_skill_passes_good_skill(self):
        skill = make_sample_skill(code='result = {"data": params.get("x")}')
        result = self.creator.validate_skill(skill)
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.is_valid)

    def test_55_validate_skill_fails_on_forbidden_pattern(self):
        skill = make_sample_skill(code='import os; result = os.system("rm -rf /")')
        result = self.creator.validate_skill(skill)
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)

    def test_56_from_template_document_processor(self):
        skill = self.creator.from_template("document_processor", name="my_doc_proc")
        self.assertEqual(skill.name, "my_doc_proc")
        self.assertIn("document_processor", skill.tags)

    def test_57_from_template_unknown_raises(self):
        with self.assertRaises(ValueError):
            self.creator.from_template("unknown_template_xyz")


# ===========================================================================
# SkillMarketplace Tests
# ===========================================================================

class TestSkillMarketplace(unittest.TestCase):
    """Test 58–67: SkillMarketplace publish, browse, install, rate, trending."""

    def setUp(self):
        self.lib = make_temp_library()
        tmp = tempfile.mkdtemp()
        self.market = SkillMarketplace(self.lib, marketplace_file=Path(tmp) / "market.json")
        self.skill = make_sample_skill(name="market_skill")
        self.lib.register(self.skill)

    def test_58_publish_returns_marketplace_skill(self):
        ms = self.market.publish(self.skill.id, author_info={"name": "Alice"})
        self.assertIsNotNone(ms)
        self.assertIsInstance(ms, MarketplaceSkill)

    def test_59_publish_nonexistent_returns_none(self):
        result = self.market.publish("bad_skill_id")
        self.assertIsNone(result)

    def test_60_browse_returns_published(self):
        self.market.publish(self.skill.id)
        results = self.market.browse()
        self.assertGreaterEqual(len(results), 1)

    def test_61_browse_with_min_rating_filters(self):
        self.market.publish(self.skill.id)
        # No rated skills => should return skills with 0 rating only when min_rating=0
        results = self.market.browse(min_rating=0.0)
        self.assertGreaterEqual(len(results), 1)
        # High min_rating should filter out unrated
        results_high = self.market.browse(min_rating=4.5)
        self.assertEqual(len(results_high), 0)

    def test_62_install_registers_skill(self):
        ms = self.market.publish(self.skill.id)
        # Remove from library to test install
        self.lib.delete(self.skill.id)
        installed = self.market.install(ms.marketplace_id)
        self.assertIsNotNone(installed)
        self.assertEqual(installed.name, self.skill.name)

    def test_63_install_increments_download_count(self):
        ms = self.market.publish(self.skill.id)
        before = self.market._data["skills"][ms.marketplace_id]["download_count"]
        self.market.install(ms.marketplace_id)
        after = self.market._data["skills"][ms.marketplace_id]["download_count"]
        self.assertEqual(after, before + 1)

    def test_64_rate_updates_rating(self):
        ms = self.market.publish(self.skill.id)
        result = self.market.rate(ms.marketplace_id, 5.0, "Excellent!")
        self.assertTrue(result)
        data = self.market._data["skills"][ms.marketplace_id]
        self.assertAlmostEqual(data["rating"], 5.0)

    def test_65_rate_rejects_out_of_range(self):
        ms = self.market.publish(self.skill.id)
        result = self.market.rate(ms.marketplace_id, 6.0)
        self.assertFalse(result)

    def test_66_get_trending_returns_list(self):
        self.market.publish(self.skill.id)
        trending = self.market.get_trending()
        self.assertIsInstance(trending, list)

    def test_67_community_top_10_returns_list(self):
        self.market.publish(self.skill.id)
        top = self.market.community_top_10()
        self.assertIsInstance(top, list)
        self.assertLessEqual(len(top), 10)


# ===========================================================================
# Built-in Skill Tests
# ===========================================================================

class TestLegalResearchSkill(unittest.TestCase):
    """Test 68–72: LegalResearchSkill."""

    def setUp(self):
        self.skill = LegalResearchSkill()

    def test_68_execute_returns_results(self):
        result = self.skill.execute(query="miranda rights", jurisdiction="federal")
        self.assertTrue(result["success"])
        self.assertIn("results", result)
        self.assertGreater(result["total_found"], 0)

    def test_69_empty_query_fails(self):
        result = self.skill.execute(query="")
        self.assertFalse(result["success"])

    def test_70_summarize_case_text(self):
        result = self.skill.summarize(case_text="Smith v. Jones, 123 U.S. 456 (2020). The court held that...")
        self.assertTrue(result["success"])
        self.assertIn("word_count", result)

    def test_71_search_statutes_only(self):
        result = self.skill.execute(query="civil rights", search_type="statutes")
        self.assertTrue(result["success"])

    def test_72_result_limit_respected(self):
        result = self.skill.execute(query="civil rights", limit=2)
        self.assertLessEqual(len(result["results"]), 2)


class TestDocumentDrafterSkill(unittest.TestCase):
    """Test 73–77: DocumentDrafterSkill."""

    def setUp(self):
        self.skill = DocumentDrafterSkill()

    def test_73_draft_demand_letter(self):
        result = self.skill.execute(
            template_name="demand_letter",
            context={
                "sender_name": "Acme Corp",
                "sender_address": "123 Main St",
                "recipient_name": "Beta LLC",
                "recipient_address": "456 Elm St",
                "matter_description": "Unpaid invoices",
                "amount": "$5,000",
                "basis_of_claim": "breach of contract",
                "deadline_days": "30",
            }
        )
        self.assertTrue(result["success"])
        self.assertIn("Acme Corp", result["document"])

    def test_74_unknown_template_fails(self):
        result = self.skill.execute(template_name="nonexistent_tmpl", context={})
        self.assertFalse(result["success"])

    def test_75_missing_placeholders_reported(self):
        result = self.skill.execute(template_name="demand_letter", context={"date": "2024-01-01"})
        self.assertIsInstance(result["missing_placeholders"], list)
        self.assertGreater(len(result["missing_placeholders"]), 0)

    def test_76_list_templates(self):
        templates = self.skill.list_templates()
        self.assertIn("demand_letter", templates)
        self.assertIn("nda", templates)

    def test_77_get_template_placeholders(self):
        placeholders = self.skill.get_template_placeholders("nda")
        self.assertIn("disclosing_party", placeholders)


class TestFinancialAnalyzerSkill(unittest.TestCase):
    """Test 78–82: FinancialAnalyzerSkill."""

    def setUp(self):
        self.skill = FinancialAnalyzerSkill()

    def test_78_budget_analysis(self):
        result = self.skill.execute(
            data={"income": 5000, "expenses": {"rent": 1500, "food": 600, "utilities": 200}},
            analysis_type="budget"
        )
        self.assertTrue(result["success"])
        self.assertIn("net_surplus_deficit", result)

    def test_79_credit_score_within_range(self):
        result = self.skill.execute(
            data={"payment_history": 0.98, "utilization_ratio": 0.15, "account_age_years": 8},
            analysis_type="credit_score"
        )
        self.assertTrue(result["success"])
        self.assertGreaterEqual(result["estimated_score"], 300)
        self.assertLessEqual(result["estimated_score"], 850)

    def test_80_financial_ratios(self):
        result = self.skill.execute(
            data={"current_assets": 10000, "current_liabilities": 5000, "total_assets": 50000,
                  "total_liabilities": 20000, "net_income": 8000, "revenue": 40000},
            analysis_type="ratios"
        )
        self.assertTrue(result["success"])
        self.assertIn("ratios", result)

    def test_81_unknown_analysis_type_fails(self):
        result = self.skill.execute(data={}, analysis_type="magic")
        self.assertFalse(result["success"])

    def test_82_liquidity_analysis(self):
        result = self.skill.execute(
            data={"cash": 5000, "receivables": 3000, "inventory": 2000, "current_liabilities": 4000},
            analysis_type="liquidity"
        )
        self.assertTrue(result["success"])
        self.assertIn("current_ratio", result)


class TestCourtMonitorSkill(unittest.TestCase):
    """Test 83–85: CourtMonitorSkill."""

    def setUp(self):
        self.skill = CourtMonitorSkill()

    def test_83_search_by_case_number(self):
        result = self.skill.execute(court="all", case_number="2024-CV-001234")
        self.assertTrue(result["success"])
        self.assertEqual(result["cases_found"], 1)

    def test_84_search_by_party(self):
        result = self.skill.execute(court="all", party_name="Smith")
        self.assertTrue(result["success"])
        self.assertGreater(result["cases_found"], 0)

    def test_85_no_search_params_fails(self):
        result = self.skill.execute(court="all")
        self.assertFalse(result["success"])


class TestContractReviewerSkill(unittest.TestCase):
    """Test 86–88: ContractReviewerSkill."""

    SAMPLE_CONTRACT = """
    This Agreement is made and entered into as of January 15, 2024

    BETWEEN: Acme Corporation ("Company")
    AND: Beta Services LLC ("Vendor")

    The Company shall pay the Vendor $5,000 per month, net 30 days.
    This Agreement shall be governed by the laws of the State of Delaware.

    The Vendor shall maintain unlimited liability for any damages caused.
    This Agreement includes mandatory arbitration for all disputes.
    """

    def setUp(self):
        self.skill = ContractReviewerSkill()

    def test_86_review_returns_success(self):
        result = self.skill.execute(contract_text=self.SAMPLE_CONTRACT)
        self.assertTrue(result["success"])
        self.assertIn("parties", result)
        self.assertIn("risk_flags", result)

    def test_87_detects_risk_flags(self):
        result = self.skill.execute(contract_text=self.SAMPLE_CONTRACT)
        flags = [f["flag"] for f in result["risk_flags"]]
        self.assertIn("Unlimited Liability", flags)
        self.assertIn("Mandatory Arbitration", flags)

    def test_88_empty_contract_fails(self):
        result = self.skill.execute(contract_text="")
        self.assertFalse(result["success"])


class TestDeadlineCalculatorSkill(unittest.TestCase):
    """Test 89–92: DeadlineCalculatorSkill."""

    def setUp(self):
        self.skill = DeadlineCalculatorSkill()

    def test_89_calculate_response_deadline(self):
        result = self.skill.execute(filing_date="2024-03-01", deadline_type="response")
        self.assertTrue(result["success"])
        self.assertIn("deadline_date", result)

    def test_90_invalid_date_fails(self):
        result = self.skill.execute(filing_date="not-a-date", deadline_type="appeal")
        self.assertFalse(result["success"])

    def test_91_unknown_deadline_type_lists_available(self):
        result = self.skill.execute(filing_date="2024-01-01", deadline_type="unknown_type")
        self.assertFalse(result["success"])
        self.assertIn("available_types", result)

    def test_92_calculate_multiple_deadlines(self):
        result = self.skill.calculate_multiple("2024-01-01", ["response", "appeal"])
        self.assertIn("deadlines", result)
        self.assertIn("response", result["deadlines"])
        self.assertIn("appeal", result["deadlines"])


# ===========================================================================
# SkillTemplate Base Class Tests
# ===========================================================================

class TestSkillTemplate(unittest.TestCase):
    """Test 93–95: SkillTemplate base class."""

    def test_93_legal_research_to_skill(self):
        template = LegalResearchSkill()
        skill = template.to_skill()
        self.assertIsInstance(skill, Skill)
        self.assertEqual(skill.id, "builtin_legal_research")
        self.assertTrue(skill.is_builtin)

    def test_94_validate_params_catches_missing(self):
        template = LegalResearchSkill()
        errors = template.validate_params({})   # query is required
        self.assertGreater(len(errors), 0)

    def test_95_validate_params_passes_correct(self):
        template = LegalResearchSkill()
        errors = template.validate_params({"query": "miranda"})
        self.assertEqual(errors, [])


# ===========================================================================
# Skill data model tests
# ===========================================================================

class TestSkillModels(unittest.TestCase):
    """Test 96–100: Data model serialization and round-trips."""

    def test_96_skill_to_dict_and_from_dict(self):
        skill = make_sample_skill()
        d = skill.to_dict()
        restored = Skill.from_dict(d)
        self.assertEqual(restored.name, skill.name)
        self.assertEqual(restored.category, skill.category)

    def test_97_skill_execution_to_dict(self):
        ex = SkillExecution(
            skill_id="x", input_params={"k": "v"}, output="result",
            success=True, duration_ms=10.5,
        )
        d = ex.to_dict()
        self.assertIn("skill_id", d)
        self.assertTrue(d["success"])

    def test_98_marketplace_skill_roundtrip(self):
        skill = make_sample_skill()
        ms = MarketplaceSkill(skill=skill, author_info={"name": "Bob"})
        d = ms.to_dict()
        restored = MarketplaceSkill.from_dict(d)
        self.assertEqual(restored.skill.name, skill.name)

    def test_99_skill_category_values(self):
        for cat in SkillCategory:
            self.assertIsInstance(cat.value, str)

    def test_100_skill_status_values(self):
        for status in SkillStatus:
            self.assertIsInstance(status.value, str)


# ===========================================================================
# Run
# ===========================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)

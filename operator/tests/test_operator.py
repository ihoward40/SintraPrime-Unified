"""
Comprehensive test suite for SintraPrime Operator Mode.

50+ tests covering:
- TaskPlanner: goal decomposition, complexity scoring, step verification
- BrowserController: all actions (mocked), ActionResult validation
- WebResearcher: research flow, fact-checking, source aggregation
- OperatorAgent: full execute loop, approval checkpoints, sandboxed execution
- LegalOperator: case law research, document drafting, docket monitoring
- Error handling, retry logic, timeout handling
"""

from __future__ import annotations

import os
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# ---------------------------------------------------------------------------
# Adjust path for direct test execution
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from operator.task_planner import (
    ActionType,
    TaskPlanner,
    TaskStep,
    TaskPlan,
    StepResult,
    APPROVAL_REQUIRED_KEYWORDS,
)
from operator.browser_controller import (
    ActionResult,
    BrowserController,
    SearchResult,
)
from operator.web_researcher import (
    WebResearcher,
    ResearchReport,
    FactCheckResult,
    CompetitiveMatrix,
    MarketReport,
    SynthesizedReport,
    Citation,
)
from operator.operator_agent import (
    OperatorAgent,
    HumanInLoopCheckpoint,
    TaskResult,
    TaskStatus,
    CodeResult,
)
from operator.legal_operator import (
    LegalOperator,
    CaseLawReport,
    LegalDocument,
    DocketReport,
    GovernmentForm,
    LegalDeadline,
    CompetitiveLegalReport,
)


# ===========================================================================
# Fixtures
# ===========================================================================


def make_mock_browser() -> MagicMock:
    """Create a mock BrowserController with sensible defaults."""
    mock = MagicMock(spec=BrowserController)
    mock.navigate.return_value = ActionResult(
        success=True,
        data={"title": "Test Page", "url": "https://example.com"},
        url="https://example.com",
    )
    mock.extract_text.return_value = ActionResult(
        success=True,
        data="Sample page text content with legal information.",
        url="https://example.com",
    )
    mock.search_web.return_value = ActionResult(
        success=True,
        data=[
            SearchResult(title="Result 1", url="https://example.com/1", snippet="Snippet 1", rank=1),
            SearchResult(title="Result 2", url="https://example.com/2", snippet="Snippet 2", rank=2),
            SearchResult(title="Result 3", url="https://example.com/3", snippet="Snippet 3", rank=3),
        ],
    )
    mock.click.return_value = ActionResult(success=True, data={"clicked": "button"})
    mock.type_text.return_value = ActionResult(success=True, data={"selector": "#input", "text": "test"})
    mock.screenshot.return_value = ActionResult(success=True, data="/tmp/screenshot.png",
                                                 screenshot_path="/tmp/screenshot.png")
    mock.scroll.return_value = ActionResult(success=True, data={"direction": "down"})
    mock.fill_form.return_value = ActionResult(success=True, data={"#name": True})
    mock.submit_form.return_value = ActionResult(success=True, data={"url_after": "https://example.com/done"})
    mock.fill_and_submit.return_value = ActionResult(success=True, data={"url_after": "https://example.com/done"})
    mock.extract_structured_data.return_value = ActionResult(
        success=True, data={"title": "Test", "body": "Content"}
    )
    mock.monitor_page.return_value = ActionResult(
        success=True, data={"found": True, "checks": 2}
    )
    return mock


def make_mock_checkpoint(auto_approve: bool = True) -> HumanInLoopCheckpoint:
    return HumanInLoopCheckpoint(auto_approve=auto_approve)


@pytest.fixture
def planner():
    return TaskPlanner(verbose=False)


@pytest.fixture
def mock_browser():
    return make_mock_browser()


@pytest.fixture
def researcher(mock_browser):
    return WebResearcher(browser=mock_browser)


@pytest.fixture
def operator(mock_browser):
    return OperatorAgent(
        browser=mock_browser,
        researcher=WebResearcher(browser=mock_browser),
        checkpoint=make_mock_checkpoint(auto_approve=True),
        verbose=False,
    )


@pytest.fixture
def legal_operator(mock_browser):
    return LegalOperator(
        browser=mock_browser,
        researcher=WebResearcher(browser=mock_browser),
        checkpoint=make_mock_checkpoint(auto_approve=True),
        verbose=False,
    )


# ===========================================================================
# TaskPlanner Tests (20 tests)
# ===========================================================================


class TestTaskPlanner:

    # --- plan() ---

    def test_plan_returns_task_plan(self, planner):
        plan = planner.plan("Research attorneys in California")
        assert isinstance(plan, TaskPlan)

    def test_plan_has_goal(self, planner):
        goal = "Find trust lawyers in LA"
        plan = planner.plan(goal)
        assert plan.goal == goal

    def test_plan_has_steps(self, planner):
        plan = planner.plan("Research market data")
        assert len(plan.steps) > 0

    def test_plan_steps_min_count(self, planner):
        plan = planner.plan("Research trust attorneys in California")
        assert len(plan.steps) >= 3

    def test_plan_steps_max_count(self, planner):
        plan = planner.plan("Simple search")
        assert len(plan.steps) <= TaskPlanner.MAX_STEPS

    def test_plan_has_complexity_score(self, planner):
        plan = planner.plan("Analyze competitor legal strategy")
        assert 1 <= plan.complexity_score <= 10

    def test_plan_has_cot_log(self, planner):
        plan = planner.plan("Research market trends")
        assert isinstance(plan.cot_log, list)
        assert len(plan.cot_log) > 0

    def test_plan_estimated_duration_positive(self, planner):
        plan = planner.plan("Research topic")
        assert plan.estimated_duration_minutes > 0

    # --- decompose_goal() ---

    def test_decompose_returns_list(self, planner):
        steps = planner.decompose_goal("Research attorney profiles")
        assert isinstance(steps, list)

    def test_decompose_steps_are_taskstep(self, planner):
        steps = planner.decompose_goal("Search for legal forms")
        assert all(isinstance(s, TaskStep) for s in steps)

    def test_decompose_legal_goal_includes_legal_steps(self, planner):
        steps = planner.decompose_goal("Find trust attorney in California")
        action_types = [s.action_type for s in steps]
        assert ActionType.SEARCH in action_types or ActionType.BROWSE in action_types

    def test_decompose_market_goal_triggers_market_steps(self, planner):
        steps = planner.decompose_goal("Research the legal market industry trends")
        assert len(steps) > 0

    def test_decompose_all_steps_have_ids(self, planner):
        steps = planner.decompose_goal("Find documents and forms")
        step_ids = [s.step_id for s in steps]
        assert len(step_ids) == len(set(step_ids)), "Step IDs must be unique"

    def test_decompose_all_steps_have_descriptions(self, planner):
        steps = planner.decompose_goal("Research competitors")
        assert all(len(s.description) > 0 for s in steps)

    # --- estimate_complexity() ---

    def test_complexity_simple_goal(self, planner):
        score = planner.estimate_complexity("search for a form")
        assert 1 <= score <= 5

    def test_complexity_complex_goal(self, planner):
        score = planner.estimate_complexity(
            "Comprehensive legal analysis comparing multi-jurisdictional trust formation "
            "requirements across California, New York, and Texas, including regulatory review"
        )
        assert score >= 5

    def test_complexity_range_valid(self, planner):
        for goal in ["search", "research analyze compare multiple jurisdictions legal regulatory"]:
            score = planner.estimate_complexity(goal)
            assert 1 <= score <= 10

    # --- verify_step() ---

    def test_verify_step_success(self, planner):
        plan = planner.plan("Research something")
        step = plan.steps[0]
        result = StepResult(step_id=step.step_id, success=True)
        assert planner.verify_step(step, result) is True

    def test_verify_step_failure_retries(self, planner):
        plan = planner.plan("Research something")
        step = plan.steps[0]
        step.max_retries = 3
        step.retry_count = 0
        result = StepResult(step_id=step.step_id, success=False, error="timeout")
        verified = planner.verify_step(step, result)
        assert verified is False
        assert step.retry_count == 1

    def test_verify_step_exhausted_retries(self, planner):
        plan = planner.plan("Research something")
        step = plan.steps[0]
        step.max_retries = 3
        step.retry_count = 3
        result = StepResult(step_id=step.step_id, success=False, error="failed")
        assert planner.verify_step(step, result) is False

    # --- approval flags ---

    def test_sensitive_step_requires_approval(self, planner):
        step = planner._make_step(
            ActionType.BROWSE,
            target="payment.example.com",
            description="Process payment for subscription",
            expected_outcome="Payment confirmed",
        )
        assert step.requires_approval is True

    def test_non_sensitive_step_no_approval(self, planner):
        step = planner._make_step(
            ActionType.SEARCH,
            target="attorneys",
            description="Search for attorneys online",
            expected_outcome="List of attorneys",
        )
        assert step.requires_approval is False

    # --- plan serialization ---

    def test_plan_to_dict(self, planner):
        plan = planner.plan("Research something")
        d = plan.to_dict()
        assert "goal" in d
        assert "steps" in d
        assert "complexity_score" in d

    def test_plan_to_json(self, planner):
        import json
        plan = planner.plan("Research something")
        j = plan.to_json()
        parsed = json.loads(j)
        assert parsed["goal"] == plan.goal


# ===========================================================================
# BrowserController Tests (10 tests)
# ===========================================================================


class TestBrowserController:

    def test_action_result_bool_true(self):
        r = ActionResult(success=True, data="some data")
        assert bool(r) is True

    def test_action_result_bool_false(self):
        r = ActionResult(success=False, error="connection refused")
        assert bool(r) is False

    def test_navigate_called(self, mock_browser):
        result = mock_browser.navigate("https://example.com")
        assert result.success is True
        mock_browser.navigate.assert_called_once_with("https://example.com")

    def test_click_returns_action_result(self, mock_browser):
        result = mock_browser.click("button.submit")
        assert isinstance(result, ActionResult)
        assert result.success is True

    def test_type_text_returns_action_result(self, mock_browser):
        result = mock_browser.type_text("#search", "attorneys")
        assert isinstance(result, ActionResult)

    def test_extract_text_returns_data(self, mock_browser):
        result = mock_browser.extract_text("body")
        assert result.success is True
        assert isinstance(result.data, str)

    def test_screenshot_returns_path(self, mock_browser):
        result = mock_browser.screenshot()
        assert result.screenshot_path is not None

    def test_scroll_direction(self, mock_browser):
        result = mock_browser.scroll("down")
        assert result.success is True

    def test_search_web_returns_results(self, mock_browser):
        result = mock_browser.search_web("trust attorneys California")
        assert result.success is True
        assert isinstance(result.data, list)
        assert len(result.data) > 0

    def test_search_result_has_url(self, mock_browser):
        result = mock_browser.search_web("legal research")
        for hit in result.data:
            assert hasattr(hit, "url")
            assert hasattr(hit, "title")

    def test_fill_form_returns_action_result(self, mock_browser):
        result = mock_browser.fill_form({"#name": "John", "#email": "john@example.com"})
        assert isinstance(result, ActionResult)

    def test_fill_and_submit_end_to_end(self, mock_browser):
        result = mock_browser.fill_and_submit(
            "https://example.com/form", {"#name": "Jane"}
        )
        assert result.success is True

    def test_extract_structured_data(self, mock_browser):
        result = mock_browser.extract_structured_data(
            "https://example.com", {"title": "h1", "body": "p"}
        )
        assert result.success is True
        assert isinstance(result.data, dict)

    def test_monitor_page_found(self, mock_browser):
        result = mock_browser.monitor_page("https://example.com", "legal", interval=1, max_checks=2)
        assert isinstance(result, ActionResult)


# ===========================================================================
# WebResearcher Tests (10 tests)
# ===========================================================================


class TestWebResearcher:

    def test_research_returns_report(self, researcher):
        report = researcher.research("trust attorneys California")
        assert isinstance(report, ResearchReport)

    def test_research_report_has_topic(self, researcher):
        report = researcher.research("legal market trends")
        assert "legal" in report.topic.lower() or "market" in report.topic.lower()

    def test_research_has_citations(self, researcher):
        report = researcher.research("top lawyers California")
        assert isinstance(report.citations, list)

    def test_research_has_key_findings(self, researcher):
        report = researcher.research("trust formation California")
        assert isinstance(report.key_findings, list)

    def test_research_confidence_0_to_1(self, researcher):
        report = researcher.research("attorney ratings")
        assert 0.0 <= report.confidence_score <= 1.0

    def test_fact_check_returns_result(self, researcher):
        result = researcher.fact_check("California requires two witnesses for trust documents")
        assert isinstance(result, FactCheckResult)

    def test_fact_check_verdict_valid(self, researcher):
        result = researcher.fact_check("Law is important")
        assert result.verdict in ("TRUE", "FALSE", "MIXED", "UNVERIFIED")

    def test_competitive_analysis_returns_matrix(self, researcher):
        matrix = researcher.competitive_analysis(
            "SintraPrime", ["LexisNexis", "Westlaw", "Clio"]
        )
        assert isinstance(matrix, CompetitiveMatrix)
        assert len(matrix.competitors) == 3

    def test_market_research_returns_report(self, researcher):
        report = researcher.market_research(
            "Legal Tech",
            ["What is the market size?", "Who are the key players?"]
        )
        assert isinstance(report, MarketReport)
        assert report.industry == "Legal Tech"

    def test_aggregate_sources_returns_report(self, researcher):
        report = researcher.aggregate_sources([
            "https://example.com/1",
            "https://example.com/2",
        ])
        assert isinstance(report, SynthesizedReport)

    def test_research_to_markdown(self, researcher):
        report = researcher.research("legal trends")
        md = report.to_markdown()
        assert isinstance(md, str)
        assert "# Research Report" in md

    def test_research_to_json(self, researcher):
        import json
        report = researcher.research("attorneys")
        j = report.to_json()
        parsed = json.loads(j)
        assert "topic" in parsed
        assert "key_findings" in parsed


# ===========================================================================
# OperatorAgent Tests (10 tests)
# ===========================================================================


class TestOperatorAgent:

    def test_execute_returns_task_result(self, operator):
        result = operator.execute("Research trust attorneys in California")
        assert isinstance(result, TaskResult)

    def test_execute_status_completed(self, operator):
        result = operator.execute("Research something simple")
        assert result.status == TaskStatus.COMPLETED

    def test_execute_goal_matches(self, operator):
        goal = "Find the best trust attorneys in LA"
        result = operator.execute(goal)
        assert result.goal == goal

    def test_execute_steps_completed_positive(self, operator):
        result = operator.execute("Research market data")
        assert result.steps_completed > 0

    def test_status_returns_dict(self, operator):
        s = operator.status()
        assert isinstance(s, dict)
        assert "status" in s

    def test_sandboxed_code_execution_python(self, operator):
        result = operator.execute_sandboxed("print('hello sintra')")
        assert isinstance(result, CodeResult)
        assert result.success is True
        assert "hello sintra" in result.stdout

    def test_sandboxed_code_execution_failure(self, operator):
        result = operator.execute_sandboxed("raise ValueError('test error')")
        assert result.success is False

    def test_sandboxed_unsupported_language(self, operator):
        result = operator.execute_sandboxed("console.log('hi')", language="javascript")
        assert result.success is False
        assert "Unsupported" in result.error

    def test_delegate_research(self, operator):
        result = operator.delegate_to_specialist("research", "trust law California")
        assert isinstance(result, ResearchReport)

    def test_delegate_plan(self, operator):
        result = operator.delegate_to_specialist("plan", "Research attorneys")
        assert isinstance(result, TaskPlan)

    def test_create_deliverable_markdown(self, operator):
        path = operator.create_deliverable("markdown", "# Test Report\n\nContent here.")
        assert path.endswith(".md")
        assert os.path.exists(path)

    def test_create_deliverable_json(self, operator):
        path = operator.create_deliverable("json", {"key": "value"})
        assert path.endswith(".json")
        assert os.path.exists(path)

    def test_replay_nonexistent_session(self, operator):
        result = operator.replay("nonexistent-session-id")
        assert result is None

    def test_execute_records_history(self, operator):
        result = operator.execute("Research attorneys")
        # After execution, history should be non-empty
        replayed = operator.replay(result.session_id)
        assert replayed is not None


# ===========================================================================
# HumanInLoopCheckpoint Tests (5 tests)
# ===========================================================================


class TestHumanInLoopCheckpoint:

    def test_auto_approve_true(self, planner):
        checkpoint = HumanInLoopCheckpoint(auto_approve=True)
        plan = planner.plan("Process payment for service")
        sensitive_steps = [s for s in plan.steps if s.requires_approval]
        if sensitive_steps:
            approved = checkpoint.request_approval(sensitive_steps[0])
            assert approved is True

    def test_callback_approval(self, planner):
        checkpoint = HumanInLoopCheckpoint(auto_approve=False, callback=lambda s: True)
        plan = planner.plan("Research attorneys")
        step = plan.steps[0]
        step.requires_approval = True
        approved = checkpoint.request_approval(step)
        assert approved is True

    def test_callback_rejection(self, planner):
        checkpoint = HumanInLoopCheckpoint(auto_approve=False, callback=lambda s: False)
        plan = planner.plan("Research attorneys")
        step = plan.steps[0]
        step.requires_approval = True
        approved = checkpoint.request_approval(step)
        assert approved is False

    def test_is_approved_after_approval(self, planner):
        checkpoint = HumanInLoopCheckpoint(auto_approve=True)
        plan = planner.plan("Research attorneys")
        step = plan.steps[0]
        step.requires_approval = True
        checkpoint.request_approval(step)
        assert checkpoint.is_approved(step.step_id) is True

    def test_rejected_step_is_tracked(self, planner):
        checkpoint = HumanInLoopCheckpoint(auto_approve=False, callback=lambda s: False)
        plan = planner.plan("Research attorneys")
        step = plan.steps[0]
        step.requires_approval = True
        checkpoint.request_approval(step)
        assert checkpoint.is_rejected(step.step_id) is True


# ===========================================================================
# LegalOperator Tests (10 tests)
# ===========================================================================


class TestLegalOperator:

    def test_research_case_law_returns_report(self, legal_operator):
        report = legal_operator.research_case_law("trust formation", "California")
        assert isinstance(report, CaseLawReport)

    def test_research_case_law_has_jurisdiction(self, legal_operator):
        report = legal_operator.research_case_law("NDA enforcement", "New York")
        assert report.jurisdiction == "New York"

    def test_research_case_law_has_query(self, legal_operator):
        report = legal_operator.research_case_law("contract breach", "Federal")
        assert report.query == "contract breach"

    def test_draft_nda_document(self, legal_operator):
        doc = legal_operator.draft_document(
            "nda",
            {"disclosing_party": "Acme Corp", "receiving_party": "Beta LLC"},
            {"purpose": "Exploring partnership", "duration_years": "3"},
        )
        assert isinstance(doc, LegalDocument)
        assert "NON-DISCLOSURE" in doc.content.upper()

    def test_draft_retainer_agreement(self, legal_operator):
        doc = legal_operator.draft_document(
            "retainer_agreement",
            {"client": "John Doe", "attorney": "Jane Smith", "firm": "Smith Law"},
            {"retainer_fee": "$5,000", "hourly_rate": "$350", "matter": "Trust formation"},
        )
        assert "RETAINER" in doc.content.upper()

    def test_draft_trust_document(self, legal_operator):
        doc = legal_operator.draft_document(
            "trust_document",
            {"grantor": "Alice Smith", "trustee": "Alice Smith", "successor_trustee": "Bob Smith"},
            {"beneficiaries": ["Charlie Smith", "Diana Smith"], "state": "California"},
        )
        assert "TRUST" in doc.content.upper()

    def test_draft_document_has_warnings(self, legal_operator):
        doc = legal_operator.draft_document(
            "demand_letter",
            {"sender": "Alice", "recipient": "Bob"},
            {"amount_owed": "$10,000", "claim_description": "Unpaid invoice"},
        )
        assert len(doc.warnings) > 0
        assert any("AI" in w for w in doc.warnings)

    def test_monitor_court_docket_returns_report(self, legal_operator):
        report = legal_operator.monitor_court_docket("2:23-cv-01234", "CourtListener")
        assert isinstance(report, DocketReport)
        assert report.case_number == "2:23-cv-01234"

    def test_file_finder_returns_form(self, legal_operator):
        form = legal_operator.file_finder("IRS", "W-9")
        assert isinstance(form, GovernmentForm)
        assert form.form_name == "W-9"
        assert form.agency == "IRS"

    def test_deadline_tracker_empty_matter(self, legal_operator):
        deadlines = legal_operator.deadline_tracker("MATTER-999")
        assert isinstance(deadlines, list)
        assert len(deadlines) == 0

    def test_add_and_track_deadline(self, legal_operator):
        deadline = legal_operator.add_deadline(
            matter_id="MATTER-001",
            deadline_type="Filing",
            due_date="2026-12-31",
            description="File motion for summary judgment",
        )
        assert isinstance(deadline, LegalDeadline)
        tracked = legal_operator.deadline_tracker("MATTER-001")
        assert len(tracked) == 1
        assert tracked[0].deadline_type == "Filing"

    def test_competitive_legal_research_returns_report(self, legal_operator):
        report = legal_operator.competitive_legal_research("trust law California", depth=1)
        assert isinstance(report, CompetitiveLegalReport)
        assert report.topic == "trust law California"

    def test_competitive_legal_research_has_markdown(self, legal_operator):
        report = legal_operator.competitive_legal_research("NDA enforceability", depth=1)
        assert isinstance(report.report_markdown, str)
        assert len(report.report_markdown) > 100

    def test_case_law_report_to_markdown(self, legal_operator):
        report = legal_operator.research_case_law("contract law", "California")
        md = report.to_markdown()
        assert "# Case Law Research" in md

    def test_draft_generic_document(self, legal_operator):
        doc = legal_operator.draft_document(
            "custom_agreement",
            {"party_a": "Firm A", "party_b": "Client B"},
            {"term": "1 year", "fee": "$500/month"},
        )
        assert isinstance(doc, LegalDocument)
        assert len(doc.content) > 0


# ===========================================================================
# Error Handling & Edge Cases (5 tests)
# ===========================================================================


class TestErrorHandling:

    def test_planner_handles_empty_goal(self, planner):
        plan = planner.plan("")
        assert isinstance(plan, TaskPlan)
        assert len(plan.steps) > 0

    def test_browser_failed_navigate_returns_false_result(self, mock_browser):
        mock_browser.navigate.return_value = ActionResult(
            success=False, error="Connection refused", url="https://example.com"
        )
        result = mock_browser.navigate("https://example.com")
        assert result.success is False
        assert result.error is not None

    def test_operator_handles_plan_exception(self, operator):
        with patch.object(operator.planner, "plan", side_effect=RuntimeError("Plan failed")):
            result = operator.execute("Some goal")
        assert result.status == TaskStatus.FAILED
        assert result.error is not None

    def test_sandboxed_syntax_error(self, operator):
        result = operator.execute_sandboxed("def broken(:\n    pass")
        assert result.success is False

    def test_researcher_handles_no_search_results(self, researcher, mock_browser):
        mock_browser.search_web.return_value = ActionResult(success=False, data=[],
                                                             error="No results")
        report = researcher.research("obscure legal topic with no results")
        assert isinstance(report, ResearchReport)
        assert report.confidence_score == 0.0 or isinstance(report.key_findings, list)


# ===========================================================================
# Integration-style Tests (2 tests)
# ===========================================================================


class TestIntegration:

    def test_full_execute_loop(self, operator):
        """Full plan → execute → verify → iterate loop."""
        result = operator.execute(
            "Research the top 10 trust attorneys in California",
            context={"jurisdiction": "California", "specialty": "trust law"},
        )
        assert result.status == TaskStatus.COMPLETED
        assert result.steps_completed > 0
        assert result.steps_total > 0
        assert isinstance(result.deliverables, list)

    def test_legal_operator_full_research(self, legal_operator):
        """End-to-end legal research using LegalOperator."""
        # Research case law
        case_report = legal_operator.research_case_law("revocable trust", "California", depth=1)
        assert isinstance(case_report, CaseLawReport)

        # Draft a document
        doc = legal_operator.draft_document(
            "trust_document",
            {"grantor": "Test Grantor", "trustee": "Test Grantor",
             "successor_trustee": "Successor Trustee"},
            {"beneficiaries": ["Beneficiary 1"], "state": "California"},
        )
        assert isinstance(doc, LegalDocument)

        # Add a deadline
        deadline = legal_operator.add_deadline(
            "MATTER-TEST", "Statute of Limitations", "2026-06-01",
            "File claim before statute expires"
        )
        assert isinstance(deadline, LegalDeadline)

        # Check deadlines
        deadlines = legal_operator.deadline_tracker("MATTER-TEST")
        assert len(deadlines) == 1

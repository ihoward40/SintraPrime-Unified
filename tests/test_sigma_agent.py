"""Tests for Agent Sigma — Mandatory test gating guardian."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.sigma.sigma_agent import (
    SigmaAgent,
    TestResult,
    SecurityFinding,
    GateReport,
)
from agents.sigma.ci_enforcer import (
    CIEnforcer,
    SIGMA_GATE_WORKFLOW,
    PRE_COMMIT_HOOK,
    PRE_PUSH_HOOK,
)


@pytest.fixture
def tmp_repo(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_sample.py").write_text(
        "def test_pass(): assert True\ndef test_also_pass(): assert 1 == 1\n"
    )
    (tmp_path / "requirements.txt").write_text("flask\n")
    return tmp_path


@pytest.fixture
def sigma(tmp_repo):
    return SigmaAgent(repo_root=str(tmp_repo), coverage_minimum=0.80)


@pytest.fixture
def enforcer(tmp_repo):
    return CIEnforcer(repo_root=str(tmp_repo))


# ── SigmaAgent Init ──────────────────────────────────────────────


class TestSigmaInit:
    def test_default_init(self):
        agent = SigmaAgent()
        assert agent.coverage_minimum == 0.80

    def test_custom_coverage(self, tmp_repo):
        agent = SigmaAgent(repo_root=str(tmp_repo), coverage_minimum=0.90)
        assert agent.coverage_minimum == 0.90

    def test_github_token_from_env(self, tmp_repo, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "test-token-123")
        agent = SigmaAgent(repo_root=str(tmp_repo))
        assert agent.github_token == "test-token-123"

    def test_block_on_security(self, tmp_repo):
        agent = SigmaAgent(repo_root=str(tmp_repo), block_on_security_critical=False)
        assert agent.block_on_security_critical is False


# ── Test Suite Execution ──────────────────────────────────────────


class TestRunTestSuite:
    def test_returns_test_result(self, sigma):
        result = sigma.run_test_suite()
        assert isinstance(result, TestResult)

    def test_result_has_counts(self, sigma):
        result = sigma.run_test_suite()
        assert result.total >= 0
        assert result.passed >= 0
        assert result.failed >= 0

    def test_module_filter(self, sigma, tmp_repo):
        result = sigma.run_test_suite(module="tests")
        assert isinstance(result, TestResult)


class TestParseTestOutput:
    def test_parse_passing(self, sigma):
        output = "2 passed in 0.5s"
        result = sigma._parse_test_output(output)
        assert result.passed == 2
        assert result.total == 2

    def test_parse_failures(self, sigma):
        output = "FAILED tests/test_foo.py::test_bar\nAssertionError\n1 failed, 2 passed in 1.0s"
        result = sigma._parse_test_output(output)
        assert result.failed == 1
        assert result.passed == 2
        assert len(result.failures) == 1

    def test_parse_empty(self, sigma):
        result = sigma._parse_test_output("")
        assert result.total == 0


# ── Coverage Enforcement ──────────────────────────────────────────


class TestCoverageEnforcement:
    def test_enforce_no_data(self, sigma, tmp_path):
        # Remove any existing coverage file
        cov_path = Path("/tmp/sigma_coverage.json")
        if cov_path.exists():
            cov_path.unlink()
        passed, actual = sigma.enforce_coverage_threshold()
        assert isinstance(passed, bool)
        assert isinstance(actual, float)

    def test_custom_threshold(self, sigma):
        passed, actual = sigma.enforce_coverage_threshold(minimum=0.0)
        assert passed is True  # 0% threshold always passes


# ── Security Scanning ─────────────────────────────────────────────


class TestSecurityScan:
    def test_returns_list(self, sigma):
        findings = sigma.run_security_scan()
        assert isinstance(findings, list)

    def test_finding_structure(self):
        f = SecurityFinding(
            finding_id="f1", severity="HIGH", description="test",
            file_path="foo.py", line_number=1, rule_id="B101",
        )
        assert f.severity == "HIGH"


# ── Type Checking ─────────────────────────────────────────────────


class TestTypeChecking:
    def test_returns_tuple(self, sigma):
        passed, errors = sigma.enforce_type_checking()
        assert isinstance(passed, bool)
        assert isinstance(errors, list)


# ── Gate Report ───────────────────────────────────────────────────


class TestGateReport:
    def test_generate_passing_report(self, sigma):
        results = {
            "overall_passed": True, "total": 10, "passed": 10, "failed": 0,
            "skipped": 0, "coverage_pct": 85.0, "coverage_passed": True,
            "security_findings": 0, "critical_findings": 0, "security_passed": True,
            "type_errors": 0, "type_check_passed": True, "blocking_reasons": [],
        }
        md = sigma.generate_gate_report(results)
        assert "PASSED" in md
        assert "Coverage" in md

    def test_generate_blocking_report(self, sigma):
        results = {
            "overall_passed": False, "total": 10, "passed": 8, "failed": 2,
            "skipped": 0, "coverage_pct": 60.0, "coverage_passed": False,
            "security_findings": 1, "critical_findings": 1, "security_passed": False,
            "type_errors": 3, "type_check_passed": False,
            "blocking_reasons": ["2 test(s) failed", "Coverage below 80%"],
        }
        md = sigma.generate_gate_report(results)
        assert "BLOCKED" in md
        assert "Blocking Reasons" in md


# ── PR Gating ─────────────────────────────────────────────────────


class TestPRGating:
    def test_block_merge(self, sigma):
        result = sigma.block_merge(42, "tests failed")
        assert result["action"] == "block"
        assert result["pr_number"] == 42

    def test_approve_merge(self, sigma):
        result = sigma.approve_merge(42)
        assert result["action"] == "approve"

    def test_gate_history(self, sigma):
        assert sigma.gate_history == []

    def test_post_status_no_token(self, sigma):
        sigma.github_token = ""
        assert sigma.post_github_status("abc123", "success", "ok") is False


# ── CIEnforcer Tests ──────────────────────────────────────────────


class TestCIEnforcerInit:
    def test_init(self, enforcer, tmp_repo):
        assert enforcer.repo_root == tmp_repo


class TestHookInstall:
    def test_install_hooks(self, enforcer, tmp_repo):
        (tmp_repo / ".git" / "hooks").mkdir(parents=True)
        results = enforcer.install_hooks()
        assert results.get("pre-commit") is True
        assert results.get("pre-push") is True
        assert (tmp_repo / ".git" / "hooks" / "pre-commit").exists()

    def test_uninstall_hooks(self, enforcer, tmp_repo):
        hooks_dir = tmp_repo / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        (hooks_dir / "pre-commit").write_text("#!/bin/bash\n")
        results = enforcer.uninstall_hooks()
        assert results.get("pre-commit") is True

    def test_install_creates_dir(self, enforcer, tmp_repo):
        results = enforcer.install_hooks()
        assert (tmp_repo / ".git" / "hooks" / "pre-commit").exists()


class TestWorkflowGeneration:
    def test_generate_workflow(self, enforcer):
        yml = enforcer.generate_github_actions_workflow()
        assert "Sigma Gate" in yml
        assert "pytest" in yml

    def test_write_workflow(self, enforcer, tmp_repo):
        path = enforcer.write_github_actions_workflow()
        assert path.exists()
        assert "sigma-gate" in path.name


class TestPRChecklist:
    def test_valid_checklist(self, enforcer):
        body = "## Description\nFoo\n## Test Results\nAll pass\n## Changelog\nChanged x"
        result = enforcer.validate_pr_checklist(body)
        assert result["passed"] is True

    def test_missing_items(self, enforcer):
        result = enforcer.validate_pr_checklist("Just a PR")
        assert result["passed"] is False
        assert len(result["missing"]) > 0

    def test_empty_body(self, enforcer):
        result = enforcer.validate_pr_checklist("")
        assert result["passed"] is False


class TestEnforcementStatus:
    def test_status_dict(self, enforcer):
        status = enforcer.enforcement_status()
        assert "timestamp" in status
        assert "pre_commit_installed" in status


class TestWorkflowContent:
    def test_pre_commit_hook_content(self):
        assert "pre-commit" in PRE_COMMIT_HOOK.lower()

    def test_pre_push_hook_content(self):
        assert "pre-push" in PRE_PUSH_HOOK.lower()

    def test_workflow_triggers(self):
        assert "pull_request" in SIGMA_GATE_WORKFLOW

"""
Tests for phase18/verification/issue_verifier.py
=================================================
Pure-Python; no network, no filesystem writes.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock, patch

import pytest

from phase18.verification.issue_verifier import (
    Finding,
    HealthChecker,
    HealthResult,
    IssueRegistry,
    IssueVerifier,
    KNOWN_ISSUES,
    Severity,
    StaticAnalyzer,
    VerificationReport,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _verifier(source: str, path: str = "<test>") -> List[Finding]:
    """Run all static checks on a source string."""
    v = IssueVerifier()
    return v.verify_source(source, path)


def _has_issue(findings: List[Finding], issue_id: str) -> bool:
    return any(f.issue_id == issue_id for f in findings)


# ---------------------------------------------------------------------------
# IssueRegistry tests
# ---------------------------------------------------------------------------

class TestIssueRegistry:
    def test_count_is_32(self):
        reg = IssueRegistry()
        assert reg.count() == 32

    def test_all_ids_length(self):
        reg = IssueRegistry()
        assert len(reg.all_ids()) == 32

    def test_get_known_issue(self):
        reg = IssueRegistry()
        issue = reg.get("SEC-001")
        assert issue is not None
        assert issue["sev"] == Severity.CRITICAL

    def test_get_unknown_returns_none(self):
        reg = IssueRegistry()
        assert reg.get("UNKNOWN-999") is None

    def test_by_severity_critical(self):
        reg = IssueRegistry()
        crits = reg.by_severity(Severity.CRITICAL)
        assert len(crits) >= 2

    def test_by_category_security(self):
        reg = IssueRegistry()
        sec = reg.by_category("security")
        assert len(sec) >= 5

    def test_by_category_ikeos(self):
        reg = IssueRegistry()
        ike = reg.by_category("ikeos")
        assert len(ike) == 2

    def test_all_ids_unique(self):
        reg = IssueRegistry()
        ids = reg.all_ids()
        assert len(ids) == len(set(ids))

    def test_known_issues_list_length(self):
        assert len(KNOWN_ISSUES) == 32


# ---------------------------------------------------------------------------
# Finding / VerificationReport tests
# ---------------------------------------------------------------------------

class TestFinding:
    def test_critical_is_blocking(self):
        f = Finding("SEC-001", Severity.CRITICAL, "security", "test")
        assert f.is_blocking() is True

    def test_high_is_blocking(self):
        f = Finding("REL-001", Severity.HIGH, "reliability", "test")
        assert f.is_blocking() is True

    def test_medium_not_blocking(self):
        f = Finding("QUA-001", Severity.MEDIUM, "quality", "test")
        assert f.is_blocking() is False

    def test_low_not_blocking(self):
        f = Finding("QUA-003", Severity.LOW, "quality", "test")
        assert f.is_blocking() is False

    def test_info_not_blocking(self):
        f = Finding("QUA-007", Severity.INFO, "quality", "test")
        assert f.is_blocking() is False


class TestVerificationReport:
    def test_empty_report_passes(self):
        r = VerificationReport()
        assert r.passed is True
        assert r.blocking_count == 0

    def test_report_with_critical_fails(self):
        r = VerificationReport()
        r.add(Finding("SEC-001", Severity.CRITICAL, "security", "test"))
        assert r.passed is False
        assert r.blocking_count == 1

    def test_report_with_low_passes(self):
        r = VerificationReport()
        r.add(Finding("QUA-003", Severity.LOW, "quality", "test"))
        assert r.passed is True

    def test_summary_contains_result(self):
        r = VerificationReport()
        s = r.summary()
        assert "PASS" in s or "FAIL" in s

    def test_summary_shows_checks_run(self):
        r = VerificationReport(checks_run=5, checks_passed=4)
        s = r.summary()
        assert "5" in s


# ---------------------------------------------------------------------------
# StaticAnalyzer — individual check tests
# ---------------------------------------------------------------------------

class TestCheckShellTrue:
    def test_detects_shell_true(self):
        src = "subprocess.run(['ls'], shell=True)"
        findings = _verifier(src)
        assert _has_issue(findings, "SEC-001")

    def test_no_false_positive_shell_false(self):
        src = "subprocess.run(['ls'], shell=False)"
        findings = _verifier(src)
        assert not _has_issue(findings, "SEC-001")

    def test_no_false_positive_no_subprocess(self):
        src = "x = 1 + 1"
        findings = _verifier(src)
        assert not _has_issue(findings, "SEC-001")


class TestCheckHardcodedSecrets:
    def test_detects_api_key(self):
        src = 'api_key = "abcdefghijklmnopqrstuvwxyz123456"'
        findings = _verifier(src)
        assert _has_issue(findings, "SEC-002")

    def test_detects_password(self):
        src = 'password = "SuperSecret1234567890"'
        findings = _verifier(src)
        assert _has_issue(findings, "SEC-002")

    def test_no_false_positive_env_var(self):
        src = 'api_key = os.environ.get("API_KEY")'
        findings = _verifier(src)
        assert not _has_issue(findings, "SEC-002")

    def test_no_false_positive_short_string(self):
        src = 'token = "short"'
        findings = _verifier(src)
        assert not _has_issue(findings, "SEC-002")


class TestCheckEvalExec:
    def test_detects_eval(self):
        src = "result = eval(user_input)"
        findings = _verifier(src)
        assert _has_issue(findings, "SEC-003")

    def test_detects_exec(self):
        src = "exec(code_string)"
        findings = _verifier(src)
        assert _has_issue(findings, "SEC-003")

    def test_no_false_positive_eval_in_comment(self):
        # Comment lines still match regex — this is intentional (conservative)
        src = "x = 1  # no eval here"
        findings = _verifier(src)
        assert not _has_issue(findings, "SEC-003")


class TestCheckBareExcept:
    def test_detects_bare_except(self):
        src = textwrap.dedent("""\
            try:
                risky()
            except:
                pass
        """)
        findings = _verifier(src)
        assert _has_issue(findings, "REL-002")

    def test_no_false_positive_typed_except(self):
        src = textwrap.dedent("""\
            try:
                risky()
            except ValueError:
                pass
        """)
        findings = _verifier(src)
        assert not _has_issue(findings, "REL-002")


class TestCheckTodo:
    def test_detects_todo(self):
        src = "# TODO: fix this later"
        findings = _verifier(src)
        assert _has_issue(findings, "QUA-003")

    def test_detects_fixme(self):
        src = "# FIXME: broken"
        findings = _verifier(src)
        assert _has_issue(findings, "QUA-003")

    def test_no_false_positive_normal_comment(self):
        src = "# This is a regular comment"
        findings = _verifier(src)
        assert not _has_issue(findings, "QUA-003")


class TestCheckStarImports:
    def test_detects_star_import(self):
        src = "from os.path import *"
        findings = _verifier(src)
        assert _has_issue(findings, "QUA-005")

    def test_no_false_positive_named_import(self):
        src = "from os.path import join, exists"
        findings = _verifier(src)
        assert not _has_issue(findings, "QUA-005")


class TestCheckPickle:
    def test_detects_pickle_loads(self):
        src = "data = pickle.loads(raw_bytes)"
        findings = _verifier(src)
        assert _has_issue(findings, "SEC-008")

    def test_no_false_positive_pickle_dump(self):
        src = "pickle.dump(obj, f)"
        findings = _verifier(src)
        assert not _has_issue(findings, "SEC-008")


class TestCheckDebugTrue:
    def test_detects_debug_true(self):
        src = "DEBUG = True"
        findings = _verifier(src)
        assert _has_issue(findings, "CFG-002")

    def test_no_false_positive_debug_false(self):
        src = "DEBUG = False"
        findings = _verifier(src)
        assert not _has_issue(findings, "CFG-002")


class TestCheckMutableDefaults:
    def test_detects_list_default(self):
        src = textwrap.dedent("""\
            def foo(items=[]):
                return items
        """)
        findings = _verifier(src)
        assert _has_issue(findings, "QUA-002")

    def test_detects_dict_default(self):
        src = textwrap.dedent("""\
            def bar(opts={}):
                return opts
        """)
        findings = _verifier(src)
        assert _has_issue(findings, "QUA-002")

    def test_no_false_positive_none_default(self):
        src = textwrap.dedent("""\
            def baz(items=None):
                return items
        """)
        findings = _verifier(src)
        assert not _has_issue(findings, "QUA-002")


class TestCheckMissingDocstring:
    def test_detects_missing_docstring(self):
        src = "x = 1\n"
        findings = _verifier(src)
        assert _has_issue(findings, "QUA-007")

    def test_no_finding_when_docstring_present(self):
        src = '"""Module docstring."""\nx = 1\n'
        findings = _verifier(src)
        assert not _has_issue(findings, "QUA-007")


# ---------------------------------------------------------------------------
# HealthChecker tests
# ---------------------------------------------------------------------------

class TestHealthChecker:
    def test_gateway_healthy(self):
        def mock_get(url, headers):
            return 200, {"status": "ok"}

        hc = HealthChecker(http_get=mock_get)
        result = hc.probe_gateway()
        assert result.healthy is True
        assert result.probe == "gateway"

    def test_gateway_unhealthy_on_500(self):
        def mock_get(url, headers):
            return 500, {}

        hc = HealthChecker(http_get=mock_get)
        result = hc.probe_gateway()
        assert result.healthy is False

    def test_gateway_unhealthy_on_exception(self):
        def mock_get(url, headers):
            raise ConnectionError("refused")

        hc = HealthChecker(http_get=mock_get)
        result = hc.probe_gateway()
        assert result.healthy is False
        assert "refused" in result.message

    def test_gateway_no_client_unhealthy(self):
        hc = HealthChecker()
        result = hc.probe_gateway()
        assert result.healthy is False

    def test_redis_healthy(self):
        hc = HealthChecker(redis_ping=lambda h, p: True)
        result = hc.probe_redis()
        assert result.healthy is True

    def test_redis_unhealthy_false(self):
        hc = HealthChecker(redis_ping=lambda h, p: False)
        result = hc.probe_redis()
        assert result.healthy is False

    def test_redis_unhealthy_on_exception(self):
        def bad_ping(h, p):
            raise OSError("connection refused")

        hc = HealthChecker(redis_ping=bad_ping)
        result = hc.probe_redis()
        assert result.healthy is False

    def test_redis_no_client_unhealthy(self):
        hc = HealthChecker()
        result = hc.probe_redis()
        assert result.healthy is False

    def test_parl_orchestrator_healthy(self):
        factory = lambda: MagicMock()
        hc = HealthChecker()
        result = hc.probe_parl_orchestrator(factory)
        assert result.healthy is True

    def test_parl_orchestrator_no_factory(self):
        hc = HealthChecker()
        result = hc.probe_parl_orchestrator(None)
        assert result.healthy is False

    def test_parl_orchestrator_exception(self):
        def bad_factory():
            raise RuntimeError("import error")

        hc = HealthChecker()
        result = hc.probe_parl_orchestrator(bad_factory)
        assert result.healthy is False

    def test_run_all_returns_three_results(self):
        hc = HealthChecker(
            http_get=lambda u, h: (200, {}),
            redis_ping=lambda h, p: True,
        )
        results = hc.run_all(orchestrator_factory=lambda: MagicMock())
        assert len(results) == 3

    def test_run_all_latency_recorded(self):
        hc = HealthChecker(
            http_get=lambda u, h: (200, {}),
            redis_ping=lambda h, p: True,
        )
        results = hc.run_all()
        for r in results:
            assert r.latency_s >= 0.0


# ---------------------------------------------------------------------------
# IssueVerifier integration tests
# ---------------------------------------------------------------------------

class TestIssueVerifier:
    def test_verify_source_clean_code(self):
        src = '"""Clean module."""\nx = 1\n'
        v = IssueVerifier()
        findings = v.verify_source(src)
        blocking = [f for f in findings if f.is_blocking()]
        assert len(blocking) == 0

    def test_verify_source_detects_multiple_issues(self):
        src = textwrap.dedent("""\
            from os import *
            api_key = "abcdefghijklmnopqrstuvwxyz123456"
            subprocess.run(cmd, shell=True)
        """)
        v = IssueVerifier()
        findings = v.verify_source(src)
        issue_ids = {f.issue_id for f in findings}
        assert "SEC-001" in issue_ids
        assert "SEC-002" in issue_ids
        assert "QUA-005" in issue_ids

    def test_verify_no_scan_no_health(self):
        v = IssueVerifier()
        report = v.verify(scan_files=False, run_health=False)
        assert report.checks_run == 0
        assert report.passed is True

    def test_verify_health_with_healthy_checker(self):
        hc = HealthChecker(
            http_get=lambda u, h: (200, {}),
            redis_ping=lambda h, p: True,
        )
        v = IssueVerifier(health_checker=hc)
        report = v.verify(
            scan_files=False,
            run_health=True,
            orchestrator_factory=lambda: MagicMock(),
        )
        # All 3 health probes should pass
        assert report.checks_passed == 3

    def test_verify_health_with_failing_gateway(self):
        hc = HealthChecker(
            http_get=lambda u, h: (500, {}),
            redis_ping=lambda h, p: True,
        )
        v = IssueVerifier(health_checker=hc)
        report = v.verify(
            scan_files=False,
            run_health=True,
            orchestrator_factory=lambda: MagicMock(),
        )
        # Gateway failure adds a HIGH finding
        assert any(
            "gateway" in f.description.lower() for f in report.findings
        )

    def test_report_duration_positive(self):
        v = IssueVerifier()
        report = v.verify(scan_files=False, run_health=False)
        assert report.duration_s >= 0.0

    def test_verify_source_line_numbers_recorded(self):
        src = "subprocess.run(cmd, shell=True)\n"
        v = IssueVerifier()
        findings = v.verify_source(src)
        shell_findings = [f for f in findings if f.issue_id == "SEC-001"]
        assert shell_findings[0].line_number == 1

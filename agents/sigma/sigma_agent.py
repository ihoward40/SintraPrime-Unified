"""Agent Sigma — Mandatory test gating guardian.

Sigma enforces code quality gates on every pull request. It runs the full
test suite with coverage, performs security scanning, type checking, and
blocks merges when quality thresholds are not met.
"""

import json
import logging
import os
import subprocess
import sys
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("sigma_agent")
logger.setLevel(logging.INFO)


@dataclass
class TestResult:
    """Structured test suite result."""
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    coverage_pct: Optional[float] = None
    failures: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class SecurityFinding:
    """A finding from the security scanner."""
    finding_id: str
    severity: str
    description: str
    file_path: str
    line_number: int
    rule_id: str


@dataclass
class GateReport:
    """Complete gate check report for a PR."""
    report_id: str
    pr_number: int
    timestamp: str
    test_result: Dict[str, Any]
    coverage_passed: bool
    security_passed: bool
    type_check_passed: bool
    overall_passed: bool
    blocking_reasons: List[str]
    markdown: str = ""


class SigmaAgent:
    """Mandatory test gating guardian.

    Sigma enforces quality gates on PRs: tests must pass, coverage must
    meet minimum thresholds, security scans must be clean, and type
    checks must succeed before a PR can be merged.
    """

    def __init__(
        self,
        repo_root: Optional[str] = None,
        github_token: Optional[str] = None,
        coverage_minimum: float = 0.80,
        block_on_security_critical: bool = True,
    ):
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN", "")
        self.coverage_minimum = coverage_minimum
        self.block_on_security_critical = block_on_security_critical
        self._gate_history: List[GateReport] = []
        logger.info("SigmaAgent initialized — coverage min=%.0f%%", coverage_minimum * 100)

    def run_test_suite(self, module: Optional[str] = None) -> TestResult:
        """Run pytest with coverage and return structured results."""
        target = str(self.repo_root / module) if module else str(self.repo_root / "tests")
        cmd = [
            sys.executable, "-m", "pytest", target,
            "--tb=short", "-q", "--no-header",
            f"--cov={self.repo_root}",
            "--cov-report=json:/tmp/sigma_coverage.json",
        ]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=600,
                cwd=str(self.repo_root),
            )
        except FileNotFoundError:
            logger.error("pytest not found.")
            return TestResult()
        except subprocess.TimeoutExpired:
            logger.error("Test suite timed out.")
            return TestResult(errors=1, failures=[{"error": "timeout"}])

        result = self._parse_test_output(proc.stdout + "\n" + proc.stderr)

        cov_path = Path("/tmp/sigma_coverage.json")
        if cov_path.exists():
            try:
                cov_data = json.loads(cov_path.read_text())
                result.coverage_pct = cov_data.get("totals", {}).get("percent_covered", 0.0)
            except (json.JSONDecodeError, KeyError):
                pass

        return result

    def _parse_test_output(self, output: str) -> TestResult:
        """Parse pytest output into TestResult."""
        result = TestResult()
        failures: List[Dict[str, str]] = []
        current_failure: Optional[str] = None

        for line in output.splitlines():
            if line.startswith("FAILED "):
                test_id = line.replace("FAILED ", "").strip()
                failures.append({"test_id": test_id, "message": ""})
                current_failure = test_id
            elif current_failure and line.strip():
                failures[-1]["message"] = line.strip()
                current_failure = None

            lower = line.lower()
            if "passed" in lower or "failed" in lower:
                num = 0
                for token in line.replace(",", " ").split():
                    if token.isdigit():
                        num = int(token)
                    elif "passed" in token:
                        result.passed = num
                    elif "failed" in token:
                        result.failed = num
                    elif "skipped" in token:
                        result.skipped = num
                    elif "error" in token:
                        result.errors = num

        result.total = result.passed + result.failed + result.skipped + result.errors
        result.failures = failures
        return result

    def enforce_coverage_threshold(self, minimum: Optional[float] = None) -> Tuple[bool, float]:
        """Check if coverage meets the minimum threshold."""
        threshold = minimum if minimum is not None else self.coverage_minimum
        cov_path = Path("/tmp/sigma_coverage.json")
        if not cov_path.exists():
            logger.warning("No coverage data found — running tests first.")
            self.run_test_suite()

        actual = 0.0
        if cov_path.exists():
            try:
                cov_data = json.loads(cov_path.read_text())
                actual = cov_data.get("totals", {}).get("percent_covered", 0.0) / 100.0
            except (json.JSONDecodeError, KeyError):
                pass

        passed = actual >= threshold
        logger.info("Coverage: %.1f%% (threshold: %.1f%%) — %s",
                     actual * 100, threshold * 100, "PASS" if passed else "FAIL")
        return passed, actual

    def run_security_scan(self) -> List[SecurityFinding]:
        """Run bandit security scanner."""
        findings: List[SecurityFinding] = []
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "bandit", "-r", str(self.repo_root),
                 "-f", "json", "--exclude", ".venv,node_modules"],
                capture_output=True, text=True, timeout=180,
                cwd=str(self.repo_root),
            )
            data = json.loads(proc.stdout)
            for r in data.get("results", []):
                findings.append(SecurityFinding(
                    finding_id=str(uuid.uuid4()),
                    severity=r.get("issue_severity", "UNKNOWN"),
                    description=r.get("issue_text", ""),
                    file_path=r.get("filename", ""),
                    line_number=r.get("line_number", 0),
                    rule_id=r.get("test_id", ""),
                ))
        except (FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
            logger.warning("Security scan failed: %s", exc)

        logger.info("Security scan found %d issues.", len(findings))
        return findings

    def enforce_type_checking(self) -> Tuple[bool, List[str]]:
        """Run mypy and return (passed, error_lines)."""
        errors: List[str] = []
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "mypy", str(self.repo_root),
                 "--ignore-missing-imports", "--no-error-summary"],
                capture_output=True, text=True, timeout=180,
                cwd=str(self.repo_root),
            )
            for line in proc.stdout.splitlines():
                if ": error:" in line:
                    errors.append(line.strip())
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            logger.warning("Type check failed: %s", exc)

        passed = len(errors) == 0
        logger.info("Type check: %d errors — %s", len(errors), "PASS" if passed else "FAIL")
        return passed, errors

    def generate_gate_report(self, results: Dict[str, Any]) -> str:
        """Generate a markdown gate report."""
        lines = [
            "# Sigma Gate Report",
            "",
            f"**Timestamp:** {datetime.now(timezone.utc).isoformat()}",
            f"**Overall:** {'PASSED' if results.get('overall_passed') else 'BLOCKED'}",
            "",
            "## Test Results",
            f"- Total: {results.get('total', 0)}",
            f"- Passed: {results.get('passed', 0)}",
            f"- Failed: {results.get('failed', 0)}",
            f"- Skipped: {results.get('skipped', 0)}",
            "",
            "## Coverage",
            f"- Coverage: {results.get('coverage_pct', 0):.1f}%",
            f"- Threshold: {self.coverage_minimum * 100:.0f}%",
            f"- Status: {'PASS' if results.get('coverage_passed') else 'FAIL'}",
            "",
            "## Security",
            f"- Findings: {results.get('security_findings', 0)}",
            f"- Critical: {results.get('critical_findings', 0)}",
            f"- Status: {'PASS' if results.get('security_passed') else 'FAIL'}",
            "",
            "## Type Checking",
            f"- Errors: {results.get('type_errors', 0)}",
            f"- Status: {'PASS' if results.get('type_check_passed') else 'FAIL'}",
            "",
        ]

        blocking = results.get("blocking_reasons", [])
        if blocking:
            lines.append("## Blocking Reasons")
            for reason in blocking:
                lines.append(f"- {reason}")
            lines.append("")

        return "\n".join(lines)

    def post_github_status(self, commit_sha: str, state: str, description: str) -> bool:
        """Post a commit status check to GitHub."""
        if not self.github_token:
            logger.warning("No GitHub token; skipping status post.")
            return False

        import urllib.request
        url = f"https://api.github.com/repos/owner/repo/statuses/{commit_sha}"
        payload = json.dumps({
            "state": state,
            "description": description[:140],
            "context": "sigma/gate-check",
        }).encode()

        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("Authorization", f"token {self.github_token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("Content-Type", "application/json")

        try:
            urllib.request.urlopen(req, timeout=30)
            return True
        except Exception as exc:
            logger.error("Failed to post GitHub status: %s", exc)
            return False

    def block_merge(self, pr_number: int, reason: str) -> Dict[str, Any]:
        """Block a PR from being merged."""
        logger.warning("BLOCKING PR #%d: %s", pr_number, reason)
        return {
            "action": "block",
            "pr_number": pr_number,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "label_added": "sigma/blocked",
        }

    def approve_merge(self, pr_number: int) -> Dict[str, Any]:
        """Approve a PR for merging."""
        logger.info("APPROVING PR #%d", pr_number)
        return {
            "action": "approve",
            "pr_number": pr_number,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "label_removed": "sigma/blocked",
            "label_added": "sigma/approved",
        }

    def gate_pull_request(self, pr_number: int, repo: Optional[str] = None) -> GateReport:
        """Run all gate checks on a pull request."""
        blocking_reasons: List[str] = []

        test_result = self.run_test_suite()
        if test_result.failed > 0:
            blocking_reasons.append(f"{test_result.failed} test(s) failed")

        cov_passed, cov_actual = self.enforce_coverage_threshold()
        if not cov_passed:
            blocking_reasons.append(
                f"Coverage {cov_actual:.1%} below minimum {self.coverage_minimum:.0%}"
            )

        sec_findings = self.run_security_scan()
        critical = [f for f in sec_findings if f.severity == "HIGH"]
        sec_passed = len(critical) == 0 if self.block_on_security_critical else True
        if not sec_passed:
            blocking_reasons.append(f"{len(critical)} critical security finding(s)")

        type_passed, type_errors = self.enforce_type_checking()
        if not type_passed:
            blocking_reasons.append(f"{len(type_errors)} type error(s)")

        overall = len(blocking_reasons) == 0

        report = GateReport(
            report_id=str(uuid.uuid4()),
            pr_number=pr_number,
            timestamp=datetime.now(timezone.utc).isoformat(),
            test_result=asdict(test_result),
            coverage_passed=cov_passed,
            security_passed=sec_passed,
            type_check_passed=type_passed,
            overall_passed=overall,
            blocking_reasons=blocking_reasons,
        )

        results_dict = {
            "overall_passed": overall,
            "total": test_result.total,
            "passed": test_result.passed,
            "failed": test_result.failed,
            "skipped": test_result.skipped,
            "coverage_pct": (test_result.coverage_pct or 0),
            "coverage_passed": cov_passed,
            "security_findings": len(sec_findings),
            "critical_findings": len(critical),
            "security_passed": sec_passed,
            "type_errors": len(type_errors),
            "type_check_passed": type_passed,
            "blocking_reasons": blocking_reasons,
        }
        report.markdown = self.generate_gate_report(results_dict)

        if overall:
            self.approve_merge(pr_number)
        else:
            self.block_merge(pr_number, "; ".join(blocking_reasons))

        self._gate_history.append(report)
        return report

    @property
    def gate_history(self) -> List[GateReport]:
        """Return list of past gate reports."""
        return list(self._gate_history)

"""
phase18/verification/issue_verifier.py
=======================================
Static-analysis + integration verification framework for SintraPrime-Unified.

Addresses the 32 code-review findings catalogued during Phase 18 security
hardening.  The verifier is structured into four layers:

1. **StaticAnalyzer**   – AST / regex scans over Python source files
2. **IssueRegistry**    – Catalogue of the 32 known findings with severity
3. **IssueVerifier**    – Runs all checks and returns a ``VerificationReport``
4. **HealthChecker**    – Runtime integration health probes (app startup,
                          ToolGateway connectivity, PARL orchestrator)

All checks are pure-Python and do not require a live network or Redis.
"""

from __future__ import annotations

import ast
import os
import re
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Severity / finding types
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"
    INFO     = "info"


@dataclass
class Finding:
    issue_id: str
    severity: Severity
    category: str
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    evidence: Optional[str] = None

    def is_blocking(self) -> bool:
        return self.severity in (Severity.CRITICAL, Severity.HIGH)


@dataclass
class VerificationReport:
    findings: List[Finding] = field(default_factory=list)
    checks_run: int = 0
    checks_passed: int = 0
    duration_s: float = 0.0

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    @property
    def blocking_count(self) -> int:
        return sum(1 for f in self.findings if f.is_blocking())

    @property
    def passed(self) -> bool:
        return self.blocking_count == 0

    def summary(self) -> str:
        lines = [
            f"Checks run: {self.checks_run}  Passed: {self.checks_passed}",
            f"Findings: {len(self.findings)}  Blocking: {self.blocking_count}",
            f"Duration: {self.duration_s:.3f}s",
            f"Result: {'PASS' if self.passed else 'FAIL'}",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Issue Registry — 32 catalogued findings
# ---------------------------------------------------------------------------

KNOWN_ISSUES: List[Dict[str, Any]] = [
    # --- Security (critical) ---
    {"id": "SEC-001", "sev": Severity.CRITICAL, "cat": "security",
     "desc": "shell=True subprocess usage — command injection risk"},
    {"id": "SEC-002", "sev": Severity.CRITICAL, "cat": "security",
     "desc": "Hardcoded secret / API key in source file"},
    {"id": "SEC-003", "sev": Severity.HIGH, "cat": "security",
     "desc": "eval() / exec() on untrusted input"},
    {"id": "SEC-004", "sev": Severity.HIGH, "cat": "security",
     "desc": "Path traversal: user-controlled path not sanitised"},
    {"id": "SEC-005", "sev": Severity.HIGH, "cat": "security",
     "desc": "Prompt injection: unsanitised user text in LLM prompt"},
    {"id": "SEC-006", "sev": Severity.MEDIUM, "cat": "security",
     "desc": "Missing HMAC webhook signature validation"},
    {"id": "SEC-007", "sev": Severity.MEDIUM, "cat": "security",
     "desc": "Unbounded file upload — no size limit enforced"},
    {"id": "SEC-008", "sev": Severity.MEDIUM, "cat": "security",
     "desc": "Insecure pickle / marshal deserialisation"},
    # --- Reliability (high) ---
    {"id": "REL-001", "sev": Severity.HIGH, "cat": "reliability",
     "desc": "HTTP request without timeout parameter"},
    {"id": "REL-002", "sev": Severity.HIGH, "cat": "reliability",
     "desc": "Bare except clause swallows all exceptions silently"},
    {"id": "REL-003", "sev": Severity.HIGH, "cat": "reliability",
     "desc": "Missing retry logic on transient network errors"},
    {"id": "REL-004", "sev": Severity.MEDIUM, "cat": "reliability",
     "desc": "Thread-unsafe shared mutable state without lock"},
    {"id": "REL-005", "sev": Severity.MEDIUM, "cat": "reliability",
     "desc": "Unhandled None return from external API call"},
    {"id": "REL-006", "sev": Severity.MEDIUM, "cat": "reliability",
     "desc": "Missing circuit breaker on LLM gateway calls"},
    {"id": "REL-007", "sev": Severity.LOW, "cat": "reliability",
     "desc": "No health-check endpoint on FastAPI app"},
    # --- Code quality (medium/low) ---
    {"id": "QUA-001", "sev": Severity.MEDIUM, "cat": "quality",
     "desc": "Missing type annotations on public functions"},
    {"id": "QUA-002", "sev": Severity.MEDIUM, "cat": "quality",
     "desc": "Mutable default argument in function signature"},
    {"id": "QUA-003", "sev": Severity.LOW, "cat": "quality",
     "desc": "TODO / FIXME comment left in production code"},
    {"id": "QUA-004", "sev": Severity.LOW, "cat": "quality",
     "desc": "Dead code: unreachable statement after return"},
    {"id": "QUA-005", "sev": Severity.LOW, "cat": "quality",
     "desc": "Overly broad import (from module import *)"},
    {"id": "QUA-006", "sev": Severity.LOW, "cat": "quality",
     "desc": "Magic number without named constant"},
    {"id": "QUA-007", "sev": Severity.INFO, "cat": "quality",
     "desc": "Missing module-level docstring"},
    # --- Testing (medium) ---
    {"id": "TST-001", "sev": Severity.HIGH, "cat": "testing",
     "desc": "Test file imports production module that does not exist"},
    {"id": "TST-002", "sev": Severity.MEDIUM, "cat": "testing",
     "desc": "Test uses time.sleep without injected sleep_fn — slow CI"},
    {"id": "TST-003", "sev": Severity.MEDIUM, "cat": "testing",
     "desc": "Test makes real HTTP request — no mock"},
    {"id": "TST-004", "sev": Severity.LOW, "cat": "testing",
     "desc": "Test has no assertions — always passes vacuously"},
    # --- Configuration (medium) ---
    {"id": "CFG-001", "sev": Severity.HIGH, "cat": "config",
     "desc": "Required environment variable read without fallback or error"},
    {"id": "CFG-002", "sev": Severity.MEDIUM, "cat": "config",
     "desc": "DEBUG=True or equivalent left enabled in production path"},
    {"id": "CFG-003", "sev": Severity.MEDIUM, "cat": "config",
     "desc": "CORS wildcard (*) allowed in production API"},
    {"id": "CFG-004", "sev": Severity.LOW, "cat": "config",
     "desc": "Logging level set to DEBUG in production code"},
    # --- IkeOS integration ---
    {"id": "IKE-001", "sev": Severity.HIGH, "cat": "ikeos",
     "desc": "Agent tool call bypasses ToolGateway — no receipt generated"},
    {"id": "IKE-002", "sev": Severity.MEDIUM, "cat": "ikeos",
     "desc": "R3 action submitted without human-approval gate"},
]


class IssueRegistry:
    """Catalogue of the 32 known code-review findings."""

    def __init__(self) -> None:
        self._issues: Dict[str, Dict[str, Any]] = {
            i["id"]: i for i in KNOWN_ISSUES
        }

    def get(self, issue_id: str) -> Optional[Dict[str, Any]]:
        return self._issues.get(issue_id)

    def all_ids(self) -> List[str]:
        return list(self._issues.keys())

    def by_severity(self, sev: Severity) -> List[Dict[str, Any]]:
        return [i for i in self._issues.values() if i["sev"] == sev]

    def by_category(self, cat: str) -> List[Dict[str, Any]]:
        return [i for i in self._issues.values() if i["cat"] == cat]

    def count(self) -> int:
        return len(self._issues)


# ---------------------------------------------------------------------------
# Static analyser
# ---------------------------------------------------------------------------

# Regex patterns for quick text-based scans
_SHELL_TRUE_RE    = re.compile(r"\bsubprocess\b.*\bshell\s*=\s*True\b")
_HARDCODED_KEY_RE = re.compile(
    r'(?i)(api_key|secret|password|token)\s*=\s*["\'][a-zA-Z0-9_\-]{16,}["\']'
)
_EVAL_RE          = re.compile(r"\beval\s*\(")
_EXEC_RE          = re.compile(r"\bexec\s*\(")
_BARE_EXCEPT_RE   = re.compile(r"^\s*except\s*:", re.MULTILINE)
_TODO_RE          = re.compile(r"#\s*(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)
_STAR_IMPORT_RE   = re.compile(r"^from\s+\S+\s+import\s+\*", re.MULTILINE)
_PICKLE_RE        = re.compile(r"\bpickle\.loads?\s*\(")
_REQUESTS_NO_TO_RE = re.compile(
    r"\brequests\.(get|post|put|delete|patch)\s*\([^)]*\)"
)
_DEBUG_TRUE_RE    = re.compile(r"\bDEBUG\s*=\s*True\b")
_CORS_WILDCARD_RE = re.compile(r'allow_origins\s*=\s*\[?\s*["\*]\s*\]?')


class StaticAnalyzer:
    """
    Scan Python source files for known anti-patterns.

    Parameters
    ----------
    root_dir:
        Root directory to scan.  Defaults to the current working directory.
    exclude_dirs:
        Directory names to skip (e.g. ``.git``, ``__pycache__``).
    """

    def __init__(
        self,
        root_dir: Optional[str] = None,
        exclude_dirs: Optional[List[str]] = None,
    ) -> None:
        self.root_dir = Path(root_dir or ".").resolve()
        self.exclude_dirs = set(
            exclude_dirs or [".git", "__pycache__", ".venv", "node_modules"]
        )

    # ------------------------------------------------------------------
    # File collection
    # ------------------------------------------------------------------

    def _python_files(self) -> List[Path]:
        files: List[Path] = []
        for p in self.root_dir.rglob("*.py"):
            if any(part in self.exclude_dirs for part in p.parts):
                continue
            files.append(p)
        return files

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def check_shell_true(self, source: str, path: str) -> List[Finding]:
        findings = []
        for i, line in enumerate(source.splitlines(), 1):
            if _SHELL_TRUE_RE.search(line):
                findings.append(Finding(
                    issue_id="SEC-001",
                    severity=Severity.CRITICAL,
                    category="security",
                    description="shell=True subprocess usage",
                    file_path=path,
                    line_number=i,
                    evidence=line.strip(),
                ))
        return findings

    def check_hardcoded_secrets(self, source: str, path: str) -> List[Finding]:
        findings = []
        for i, line in enumerate(source.splitlines(), 1):
            if _HARDCODED_KEY_RE.search(line):
                findings.append(Finding(
                    issue_id="SEC-002",
                    severity=Severity.CRITICAL,
                    category="security",
                    description="Hardcoded secret detected",
                    file_path=path,
                    line_number=i,
                    evidence=line.strip()[:80],
                ))
        return findings

    def check_eval_exec(self, source: str, path: str) -> List[Finding]:
        findings = []
        for i, line in enumerate(source.splitlines(), 1):
            if _EVAL_RE.search(line) or _EXEC_RE.search(line):
                findings.append(Finding(
                    issue_id="SEC-003",
                    severity=Severity.HIGH,
                    category="security",
                    description="eval/exec usage detected",
                    file_path=path,
                    line_number=i,
                    evidence=line.strip(),
                ))
        return findings

    def check_bare_except(self, source: str, path: str) -> List[Finding]:
        findings = []
        for i, line in enumerate(source.splitlines(), 1):
            if re.match(r"^\s*except\s*:", line):
                findings.append(Finding(
                    issue_id="REL-002",
                    severity=Severity.HIGH,
                    category="reliability",
                    description="Bare except clause",
                    file_path=path,
                    line_number=i,
                    evidence=line.strip(),
                ))
        return findings

    def check_todo_comments(self, source: str, path: str) -> List[Finding]:
        findings = []
        for i, line in enumerate(source.splitlines(), 1):
            if _TODO_RE.search(line):
                findings.append(Finding(
                    issue_id="QUA-003",
                    severity=Severity.LOW,
                    category="quality",
                    description="TODO/FIXME comment",
                    file_path=path,
                    line_number=i,
                    evidence=line.strip(),
                ))
        return findings

    def check_star_imports(self, source: str, path: str) -> List[Finding]:
        findings = []
        for i, line in enumerate(source.splitlines(), 1):
            if re.match(r"^from\s+\S+\s+import\s+\*", line.strip()):
                findings.append(Finding(
                    issue_id="QUA-005",
                    severity=Severity.LOW,
                    category="quality",
                    description="Wildcard import",
                    file_path=path,
                    line_number=i,
                    evidence=line.strip(),
                ))
        return findings

    def check_pickle(self, source: str, path: str) -> List[Finding]:
        findings = []
        for i, line in enumerate(source.splitlines(), 1):
            if _PICKLE_RE.search(line):
                findings.append(Finding(
                    issue_id="SEC-008",
                    severity=Severity.MEDIUM,
                    category="security",
                    description="pickle.loads usage",
                    file_path=path,
                    line_number=i,
                    evidence=line.strip(),
                ))
        return findings

    def check_debug_true(self, source: str, path: str) -> List[Finding]:
        findings = []
        for i, line in enumerate(source.splitlines(), 1):
            if _DEBUG_TRUE_RE.search(line):
                findings.append(Finding(
                    issue_id="CFG-002",
                    severity=Severity.MEDIUM,
                    category="config",
                    description="DEBUG=True in source",
                    file_path=path,
                    line_number=i,
                    evidence=line.strip(),
                ))
        return findings

    def check_mutable_defaults(self, source: str, path: str) -> List[Finding]:
        """AST-based check for mutable default arguments."""
        findings = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return findings
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for default in node.args.defaults + node.args.kw_defaults:
                    if default is None:
                        continue
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        findings.append(Finding(
                            issue_id="QUA-002",
                            severity=Severity.MEDIUM,
                            category="quality",
                            description=f"Mutable default in {node.name}()",
                            file_path=path,
                            line_number=node.lineno,
                        ))
        return findings

    def check_missing_docstring(self, source: str, path: str) -> List[Finding]:
        """Check for missing module-level docstring."""
        findings = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return findings
        if not (
            tree.body
            and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)
            and isinstance(tree.body[0].value.value, str)
        ):
            findings.append(Finding(
                issue_id="QUA-007",
                severity=Severity.INFO,
                category="quality",
                description="Missing module docstring",
                file_path=path,
            ))
        return findings

    # ------------------------------------------------------------------
    # Scan a single file
    # ------------------------------------------------------------------

    def scan_file(self, path: Path) -> List[Finding]:
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []
        str_path = str(path)
        findings: List[Finding] = []
        findings += self.check_shell_true(source, str_path)
        findings += self.check_hardcoded_secrets(source, str_path)
        findings += self.check_eval_exec(source, str_path)
        findings += self.check_bare_except(source, str_path)
        findings += self.check_todo_comments(source, str_path)
        findings += self.check_star_imports(source, str_path)
        findings += self.check_pickle(source, str_path)
        findings += self.check_debug_true(source, str_path)
        findings += self.check_mutable_defaults(source, str_path)
        findings += self.check_missing_docstring(source, str_path)
        return findings

    # ------------------------------------------------------------------
    # Scan all files
    # ------------------------------------------------------------------

    def scan_all(self) -> List[Finding]:
        all_findings: List[Finding] = []
        for f in self._python_files():
            all_findings += self.scan_file(f)
        return all_findings


# ---------------------------------------------------------------------------
# Health checker (runtime integration probes)
# ---------------------------------------------------------------------------

@dataclass
class HealthResult:
    probe: str
    healthy: bool
    message: str
    latency_s: float = 0.0


class HealthChecker:
    """
    Runtime health probes for the SintraPrime + IkeOS integrated system.

    All probes accept injected callables so they can be tested without a live
    environment.
    """

    def __init__(
        self,
        gateway_url: str = "http://localhost:3000",
        redis_host: str = "localhost",
        redis_port: int = 6379,
        http_get: Optional[Callable] = None,
        redis_ping: Optional[Callable] = None,
    ) -> None:
        self.gateway_url = gateway_url.rstrip("/")
        self.redis_host = redis_host
        self.redis_port = redis_port
        self._http_get = http_get
        self._redis_ping = redis_ping

    def probe_gateway(self) -> HealthResult:
        """GET /health on the IkeOS gateway."""
        start = time.time()
        if self._http_get is None:
            return HealthResult("gateway", False, "No HTTP client configured", 0.0)
        try:
            status, body = self._http_get(
                f"{self.gateway_url}/health", {"Accept": "application/json"}
            )
            latency = time.time() - start
            if status == 200:
                return HealthResult("gateway", True, "OK", latency)
            return HealthResult("gateway", False, f"HTTP {status}", latency)
        except Exception as exc:
            return HealthResult("gateway", False, str(exc), time.time() - start)

    def probe_redis(self) -> HealthResult:
        """PING the Redis instance."""
        start = time.time()
        if self._redis_ping is None:
            return HealthResult("redis", False, "No Redis client configured", 0.0)
        try:
            ok = self._redis_ping(self.redis_host, self.redis_port)
            latency = time.time() - start
            if ok:
                return HealthResult("redis", True, "PONG", latency)
            return HealthResult("redis", False, "No PONG", latency)
        except Exception as exc:
            return HealthResult("redis", False, str(exc), time.time() - start)

    def probe_parl_orchestrator(
        self, orchestrator_factory: Optional[Callable] = None
    ) -> HealthResult:
        """Instantiate the PARL Orchestrator and verify it initialises cleanly."""
        start = time.time()
        if orchestrator_factory is None:
            return HealthResult(
                "parl_orchestrator", False, "No factory provided", 0.0
            )
        try:
            orch = orchestrator_factory()
            latency = time.time() - start
            if orch is not None:
                return HealthResult("parl_orchestrator", True, "OK", latency)
            return HealthResult("parl_orchestrator", False, "Factory returned None", latency)
        except Exception as exc:
            return HealthResult("parl_orchestrator", False, str(exc), time.time() - start)

    def run_all(
        self, orchestrator_factory: Optional[Callable] = None
    ) -> List[HealthResult]:
        return [
            self.probe_gateway(),
            self.probe_redis(),
            self.probe_parl_orchestrator(orchestrator_factory),
        ]


# ---------------------------------------------------------------------------
# IssueVerifier — orchestrates all checks
# ---------------------------------------------------------------------------

class IssueVerifier:
    """
    Runs static analysis + health probes and returns a ``VerificationReport``.

    Parameters
    ----------
    root_dir:
        Root of the SintraPrime monorepo to scan.
    health_checker:
        Optional ``HealthChecker`` instance; if omitted, health probes are
        skipped.
    """

    def __init__(
        self,
        root_dir: Optional[str] = None,
        health_checker: Optional[HealthChecker] = None,
    ) -> None:
        self.analyzer = StaticAnalyzer(root_dir)
        self.registry = IssueRegistry()
        self.health_checker = health_checker

    def verify(
        self,
        scan_files: bool = True,
        run_health: bool = True,
        orchestrator_factory: Optional[Callable] = None,
    ) -> VerificationReport:
        start = time.time()
        report = VerificationReport()

        if scan_files:
            findings = self.analyzer.scan_all()
            for f in findings:
                report.add(f)
            report.checks_run += 1
            report.checks_passed += 1  # static scan always completes

        if run_health and self.health_checker is not None:
            results = self.health_checker.run_all(orchestrator_factory)
            report.checks_run += len(results)
            for r in results:
                if r.healthy:
                    report.checks_passed += 1
                else:
                    report.add(Finding(
                        issue_id=f"HEALTH-{r.probe.upper()}",
                        severity=Severity.HIGH,
                        category="health",
                        description=f"Health probe '{r.probe}' failed: {r.message}",
                    ))

        report.duration_s = time.time() - start
        return report

    def verify_source(self, source: str, path: str = "<string>") -> List[Finding]:
        """Convenience: scan a single source string (useful in tests)."""
        findings: List[Finding] = []
        findings += self.analyzer.check_shell_true(source, path)
        findings += self.analyzer.check_hardcoded_secrets(source, path)
        findings += self.analyzer.check_eval_exec(source, path)
        findings += self.analyzer.check_bare_except(source, path)
        findings += self.analyzer.check_todo_comments(source, path)
        findings += self.analyzer.check_star_imports(source, path)
        findings += self.analyzer.check_pickle(source, path)
        findings += self.analyzer.check_debug_true(source, path)
        findings += self.analyzer.check_mutable_defaults(source, path)
        findings += self.analyzer.check_missing_docstring(source, path)
        return findings

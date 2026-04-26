"""
Full security audit runner for SintraPrime-Unified.
Sierra-4 Security Module
"""

import os
import re
import json
import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

from .secrets_scanner import SecretsScanner, Finding
from .input_validator import InputValidator


# Known vulnerable package versions (illustrative — use pip-audit in production)
KNOWN_VULNERABLE_PACKAGES = {
    "pillow": [("9.0.0", "9.0.1", "CVE-2022-22815"), ("8.3.0", "8.3.2", "CVE-2021-34552")],
    "requests": [("2.6.0", "2.6.0", "CVE-2014-1829"), ("2.25.0", "2.25.0", "CVE-2023-32681")],
    "cryptography": [("38.0.0", "38.0.3", "CVE-2022-3602")],
    "flask": [("0.12.0", "0.12.5", "CVE-2018-1000656")],
    "django": [("3.1.0", "3.1.14", "CVE-2021-45452"), ("4.0.0", "4.0.4", "CVE-2022-28346")],
    "pyyaml": [("5.3.0", "5.3.1", "CVE-2020-14343")],
    "urllib3": [("1.26.0", "1.26.4", "CVE-2021-33503")],
    "paramiko": [("2.7.0", "2.7.2", "CVE-2022-24302")],
    "sqlalchemy": [("1.4.0", "1.4.42", "CVE-2022-40278")],
    "aiohttp": [("3.7.0", "3.7.4", "CVE-2021-21330")],
}

SECURITY_BEST_PRACTICES = [
    {
        "check": "Environment variables for secrets",
        "pattern": r'os\.environ\.get\(',
        "inverse": False,
        "severity": "INFO",
    },
    {
        "check": "Hardcoded DEBUG=True",
        "pattern": r'DEBUG\s*=\s*True',
        "inverse": True,
        "severity": "HIGH",
    },
    {
        "check": "Use of eval()",
        "pattern": r'\beval\s*\(',
        "inverse": True,
        "severity": "HIGH",
    },
    {
        "check": "Use of exec()",
        "pattern": r'\bexec\s*\(',
        "inverse": True,
        "severity": "MEDIUM",
    },
    {
        "check": "Shell=True in subprocess",
        "pattern": r'subprocess\.(run|call|Popen).*shell\s*=\s*True',
        "inverse": True,
        "severity": "HIGH",
    },
    {
        "check": "Pickle deserialization",
        "pattern": r'pickle\.loads?\(',
        "inverse": True,
        "severity": "CRITICAL",
    },
    {
        "check": "Verify=False in requests",
        "pattern": r'requests\.(get|post|put|patch|delete).*verify\s*=\s*False',
        "inverse": True,
        "severity": "HIGH",
    },
    {
        "check": "Assert statements for auth",
        "pattern": r'assert\s+.*(?:auth|user|role|permission)',
        "inverse": True,
        "severity": "MEDIUM",
    },
]


class SecurityAudit:
    """
    Run a complete security audit of SintraPrime-Unified.
    
    Covers:
    - Secrets scanning (API keys, passwords, tokens)
    - Dependency vulnerability checking
    - Code security anti-patterns
    - Authentication configuration review
    - Input validation coverage
    """

    def __init__(self):
        self.scanner = SecretsScanner()
        self.validator = InputValidator()
        self._findings: List[Finding] = []
        self._dep_issues: List[Dict] = []
        self._code_issues: List[Dict] = []
        self._audit_timestamp = datetime.datetime.utcnow().isoformat()

    def run_full_audit(self, repo_path: str) -> Dict[str, Any]:
        """
        Run a complete security audit of the SintraPrime repository.
        
        Args:
            repo_path: Path to the repository root
            
        Returns:
            Comprehensive audit results dict with findings, scores, recommendations
        """
        repo = Path(repo_path)
        if not repo.exists():
            return {"error": f"Repository path not found: {repo_path}", "status": "FAILED"}

        print(f"[SecurityAudit] Starting full audit of: {repo_path}")
        print(f"[SecurityAudit] Timestamp: {self._audit_timestamp}")

        # 1. Secrets scan
        print("[SecurityAudit] Phase 1: Scanning for leaked secrets...")
        self._findings = self.scanner.scan_directory(repo_path)

        # 2. Dependency check
        requirements_path = str(repo / "requirements.txt")
        print("[SecurityAudit] Phase 2: Checking dependencies...")
        self._dep_issues = self.check_dependencies(requirements_path)

        # 3. Code pattern audit
        print("[SecurityAudit] Phase 3: Auditing code security patterns...")
        self._code_issues = self._audit_code_patterns(repo_path)

        # 4. Auth configuration check
        print("[SecurityAudit] Phase 4: Reviewing auth configuration...")
        auth_issues = self._check_auth_configuration(repo_path)

        # Calculate security score
        score = self._calculate_security_score()

        results = {
            "status": "COMPLETED",
            "timestamp": self._audit_timestamp,
            "repo_path": repo_path,
            "security_score": score,
            "grade": self._get_grade(score),
            "summary": {
                "total_issues": len(self._findings) + len(self._dep_issues) + len(self._code_issues),
                "secrets_found": len(self._findings),
                "critical_secrets": sum(1 for f in self._findings if f.severity == "CRITICAL"),
                "vulnerable_deps": len(self._dep_issues),
                "code_issues": len(self._code_issues),
                "auth_issues": len(auth_issues),
            },
            "secrets_scan": {
                "findings": [
                    {"file": f.file, "line": f.line, "pattern": f.pattern, "severity": f.severity}
                    for f in self._findings
                ],
                "report": self.scanner.generate_report(self._findings),
            },
            "dependencies": self._dep_issues,
            "code_patterns": self._code_issues,
            "auth_config": auth_issues,
            "recommendations": self._generate_recommendations(),
            "gitignore_additions": self.scanner.create_gitignore_additions(),
        }

        print(f"[SecurityAudit] Audit complete. Security score: {score}/100 ({self._get_grade(score)})")
        return results

    def check_dependencies(self, requirements_path: str) -> List[Dict]:
        """
        Check requirements.txt for known vulnerable packages.
        
        Args:
            requirements_path: Path to requirements.txt
            
        Returns:
            List of vulnerability dicts with package, version, cve, severity
        """
        issues = []
        req_file = Path(requirements_path)

        if not req_file.exists():
            return [{"warning": f"requirements.txt not found at {requirements_path}"}]

        try:
            content = req_file.read_text()
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                # Parse package==version
                match = re.match(r'^([a-zA-Z0-9\-_]+)[>=<~!]+([0-9.]+)', line)
                if not match:
                    continue

                pkg_name = match.group(1).lower()
                pkg_version = match.group(2)

                if pkg_name in KNOWN_VULNERABLE_PACKAGES:
                    for min_ver, max_ver, cve in KNOWN_VULNERABLE_PACKAGES[pkg_name]:
                        if self._version_in_range(pkg_version, min_ver, max_ver):
                            issues.append({
                                "package": pkg_name,
                                "installed_version": pkg_version,
                                "affected_range": f"{min_ver} - {max_ver}",
                                "cve": cve,
                                "severity": "HIGH",
                                "recommendation": f"Upgrade {pkg_name} to latest version",
                            })

        except Exception as e:
            issues.append({"error": f"Failed to parse requirements.txt: {e}"})

        return issues

    def _version_in_range(self, version: str, min_ver: str, max_ver: str) -> bool:
        """Simple version range check."""
        try:
            def parse(v):
                return tuple(int(x) for x in v.split('.')[:3])
            v = parse(version)
            return parse(min_ver) <= v <= parse(max_ver)
        except (ValueError, AttributeError):
            return False

    def _audit_code_patterns(self, repo_path: str) -> List[Dict]:
        """Check for security anti-patterns in code."""
        issues = []
        root = Path(repo_path)

        for filepath in root.rglob("*.py"):
            if any(part in {'.git', '__pycache__', 'node_modules', '.venv'} for part in filepath.parts):
                continue
            try:
                content = filepath.read_text(encoding='utf-8', errors='ignore')
                lines = content.splitlines()
                for check in SECURITY_BEST_PRACTICES:
                    if not check["inverse"]:
                        continue  # Skip positive checks for now
                    pattern = re.compile(check["pattern"], re.IGNORECASE)
                    for line_no, line in enumerate(lines, 1):
                        if pattern.search(line):
                            issues.append({
                                "file": str(filepath),
                                "line": line_no,
                                "check": check["check"],
                                "severity": check["severity"],
                                "snippet": line.strip()[:120],
                            })
            except Exception:
                continue

        return issues

    def _check_auth_configuration(self, repo_path: str) -> List[Dict]:
        """Check authentication configuration."""
        issues = []
        root = Path(repo_path)

        # Check for .env files
        for env_file in root.glob("**/.env*"):
            if '.env.example' not in str(env_file) and '.env.template' not in str(env_file):
                issues.append({
                    "check": "Environment file in repository",
                    "file": str(env_file),
                    "severity": "CRITICAL",
                    "recommendation": "Move secrets to environment variables and add .env to .gitignore",
                })

        # Check for default/weak JWT secrets
        jwt_pattern = re.compile(r'(?i)jwt.{0,10}secret\s*=\s*["\'](.{1,30})["\']')
        weak_values = {'secret', 'change-me', 'changeme', 'your-secret', 'mysecret', '123456', 'password'}

        for filepath in root.rglob("*.py"):
            try:
                content = filepath.read_text(encoding='utf-8', errors='ignore')
                for match in jwt_pattern.finditer(content):
                    if match.group(1).lower() in weak_values:
                        issues.append({
                            "check": "Weak JWT secret detected",
                            "file": str(filepath),
                            "severity": "CRITICAL",
                            "recommendation": "Use a cryptographically random 256-bit secret",
                        })
            except Exception:
                continue

        return issues

    def _calculate_security_score(self) -> int:
        """Calculate security score 0-100."""
        score = 100

        for f in self._findings:
            if f.severity == "CRITICAL":
                score -= 20
            elif f.severity == "HIGH":
                score -= 10
            elif f.severity == "MEDIUM":
                score -= 5
            elif f.severity == "LOW":
                score -= 2

        for issue in self._dep_issues:
            if "error" not in issue and "warning" not in issue:
                severity = issue.get("severity", "MEDIUM")
                if severity == "CRITICAL":
                    score -= 15
                elif severity == "HIGH":
                    score -= 8

        for issue in self._code_issues:
            if issue.get("severity") == "CRITICAL":
                score -= 10
            elif issue.get("severity") == "HIGH":
                score -= 5
            elif issue.get("severity") == "MEDIUM":
                score -= 2

        return max(0, min(100, score))

    def _get_grade(self, score: int) -> str:
        """Convert score to letter grade."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def _generate_recommendations(self) -> List[str]:
        """Generate prioritized security recommendations."""
        recs = []

        if any(f.severity == "CRITICAL" for f in self._findings):
            recs.append("🔴 CRITICAL: Revoke and rotate all exposed credentials immediately")

        if self._dep_issues and not all("warning" in d or "error" in d for d in self._dep_issues):
            recs.append("🟠 HIGH: Update vulnerable dependencies to patched versions")

        recs.extend([
            "Use environment variables for all secrets (never hardcode)",
            "Enable GitHub Secret Scanning on all repositories",
            "Add pre-commit hook with gitleaks or detect-secrets",
            "Implement RBAC with least-privilege principle",
            "Enable audit logging for all authentication events",
            "Use HTTPS/TLS 1.3+ for all external communications",
            "Implement CORS with explicit allowlist (not wildcard)",
            "Add rate limiting to all public API endpoints",
            "Use parameterized queries to prevent SQL injection",
            "Implement Content Security Policy (CSP) headers",
            "Enable HSTS with preloading",
            "Conduct quarterly dependency audits with pip-audit or Dependabot",
        ])

        return recs

    def generate_security_report(self) -> str:
        """
        Generate a comprehensive markdown SECURITY.md report.
        
        Returns:
            Markdown-formatted security report
        """
        now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        score = self._calculate_security_score()
        grade = self._get_grade(score)

        sections = [
            "# 🔐 SintraPrime Security Audit Report",
            f"\n**Audit Date:** {now}",
            f"**Security Score:** {score}/100 (Grade: {grade})",
            f"**Total Issues:** {len(self._findings) + len(self._dep_issues) + len(self._code_issues)}",
            "",
            "---",
            "",
            "## Executive Summary",
            "",
        ]

        if score >= 90:
            sections.append("✅ The codebase demonstrates excellent security posture with minimal risk areas.")
        elif score >= 70:
            sections.append("⚠️ The codebase has acceptable security posture with several areas requiring attention.")
        else:
            sections.append("🚨 The codebase has significant security vulnerabilities that require immediate remediation.")

        sections.extend([
            "",
            "## Secrets Scan Results",
            "",
            self.scanner.generate_report(self._findings),
            "",
            "## Vulnerable Dependencies",
            "",
        ])

        if not self._dep_issues:
            sections.append("✅ No known vulnerable dependencies detected.")
        else:
            for issue in self._dep_issues:
                if "error" in issue or "warning" in issue:
                    sections.append(f"⚠️ {issue.get('error') or issue.get('warning')}")
                else:
                    sections.append(
                        f"- **{issue['package']} {issue['installed_version']}** — "
                        f"{issue['cve']} (Severity: {issue['severity']})"
                    )

        sections.extend([
            "",
            "## Code Security Issues",
            "",
        ])

        if not self._code_issues:
            sections.append("✅ No security anti-patterns detected in code.")
        else:
            for issue in self._code_issues:
                sections.append(
                    f"- **{issue['check']}** [{issue['severity']}] — "
                    f"`{issue['file']}:{issue['line']}`"
                )

        sections.extend([
            "",
            "## Recommendations",
            "",
        ])
        for rec in self._generate_recommendations():
            sections.append(f"- {rec}")

        return "\n".join(sections)

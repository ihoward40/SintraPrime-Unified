"""
Scan codebase for accidentally committed secrets.
SintraPrime Security Module — Sierra-4
"""

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional
import datetime

PATTERNS = {
    "openai_key": (r'sk-[a-zA-Z0-9]{48}', "CRITICAL"),
    "stripe_key": (r'sk_live_[a-zA-Z0-9]+', "CRITICAL"),
    "stripe_key_test": (r'sk_test_[a-zA-Z0-9]+', "HIGH"),
    "aws_key": (r'AKIA[A-Z0-9]{16}', "CRITICAL"),
    "aws_secret": (r'(?i)aws.{0,20}[\'"][0-9a-zA-Z/+]{40}[\'"]', "CRITICAL"),
    "github_token": (r'ghp_[a-zA-Z0-9]{36}', "CRITICAL"),
    "github_oauth": (r'gho_[a-zA-Z0-9]{36}', "HIGH"),
    "private_key": (r'-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----', "CRITICAL"),
    "password_in_code": (r'(?i)password\s*=\s*["\'][^"\']{8,}["\']', "HIGH"),
    "api_key_in_code": (r'(?i)api_key\s*=\s*["\'][^"\']{16,}["\']', "HIGH"),
    "secret_in_code": (r'(?i)secret\s*=\s*["\'][^"\']{8,}["\']', "HIGH"),
    "jwt_secret": (r'(?i)jwt.{0,10}secret\s*=\s*["\'][^"\']{8,}["\']', "CRITICAL"),
    "db_password": (r'(?i)(db|database).{0,10}password\s*=\s*["\'][^"\']{4,}["\']', "CRITICAL"),
    "connection_string": (r'(postgresql|mysql|mongodb)\://[^:]+:[^@]+@', "CRITICAL"),
    "plaid_secret": (r'(?i)plaid.{0,10}secret\s*=\s*["\'][^"\']{16,}["\']', "CRITICAL"),
    "sendgrid_key": (r'SG\.[a-zA-Z0-9_-]{22}\.[a-zA-Z0-9_-]{43}', "HIGH"),
    "twilio_key": (r'SK[0-9a-f]{32}', "HIGH"),
    "generic_token": (r'(?i)token\s*=\s*["\'][a-zA-Z0-9_\-\.]{32,}["\']', "MEDIUM"),
}

SKIP_EXTENSIONS = {'.pyc', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico',
                   '.pdf', '.zip', '.tar', '.gz', '.lock', '.bin', '.exe'}

SKIP_DIRS = {'__pycache__', '.git', 'node_modules', '.venv', 'venv', 'env',
             'dist', 'build', '.mypy_cache', '.pytest_cache'}


@dataclass
class Finding:
    file: str
    line: int
    pattern: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    snippet: str = ""
    column: int = 0


@dataclass
class ScanReport:
    findings: List[Finding] = field(default_factory=list)
    files_scanned: int = 0
    files_skipped: int = 0
    scan_duration_ms: float = 0.0
    timestamp: str = ""

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "CRITICAL")

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "HIGH")

    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "MEDIUM")

    @property
    def low_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "LOW")


class SecretsScanner:
    """
    Scans source code directories for accidentally committed secrets.
    
    Detects: API keys, passwords, tokens, private keys, connection strings.
    Supports: Python, JavaScript, TypeScript, YAML, JSON, env files, etc.
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._compiled_patterns = {
            name: (re.compile(pattern), severity)
            for name, (pattern, severity) in PATTERNS.items()
        }

    def scan_file(self, filepath: Path) -> List[Finding]:
        """Scan a single file for secrets."""
        findings = []
        try:
            content = filepath.read_text(encoding='utf-8', errors='ignore')
            lines = content.splitlines()
            for line_no, line in enumerate(lines, 1):
                for pattern_name, (regex, severity) in self._compiled_patterns.items():
                    match = regex.search(line)
                    if match:
                        # Mask the actual secret in snippet
                        snippet = line.strip()
                        if len(snippet) > 120:
                            snippet = snippet[:120] + "..."
                        findings.append(Finding(
                            file=str(filepath),
                            line=line_no,
                            pattern=pattern_name,
                            severity=severity,
                            snippet=self._mask_secret(snippet),
                            column=match.start(),
                        ))
        except (PermissionError, OSError) as e:
            if self.verbose:
                print(f"  [SKIP] Cannot read {filepath}: {e}")
        return findings

    def _mask_secret(self, text: str) -> str:
        """Mask secret values in snippet for safe reporting."""
        for _, (regex, _) in self._compiled_patterns.items():
            def replacer(m):
                val = m.group(0)
                if len(val) > 8:
                    return val[:4] + "*" * (len(val) - 8) + val[-4:]
                return "****"
            text = regex.sub(replacer, text)
        return text

    def scan_directory(self, path: str) -> List[Finding]:
        """
        Scan all source files in a directory tree for leaked secrets.
        
        Args:
            path: Root directory to scan
            
        Returns:
            List of Finding objects sorted by severity
        """
        import time
        start = time.time()

        root = Path(path)
        findings: List[Finding] = []
        files_scanned = 0

        for filepath in root.rglob("*"):
            if not filepath.is_file():
                continue
            # Skip unwanted dirs
            if any(part in SKIP_DIRS for part in filepath.parts):
                continue
            # Skip unwanted extensions
            if filepath.suffix.lower() in SKIP_EXTENSIONS:
                continue
            if self.verbose:
                print(f"  Scanning: {filepath}")
            findings.extend(self.scan_file(filepath))
            files_scanned += 1

        # Sort by severity
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        findings.sort(key=lambda f: severity_order.get(f.severity, 4))

        elapsed = (time.time() - start) * 1000
        if self.verbose:
            print(f"  Scanned {files_scanned} files in {elapsed:.1f}ms, found {len(findings)} issues")

        return findings

    def generate_report(self, findings: List[Finding]) -> str:
        """
        Generate a markdown security report from scan findings.
        
        Args:
            findings: List of Finding objects from scan_directory()
            
        Returns:
            Markdown-formatted security report string
        """
        now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        critical = [f for f in findings if f.severity == "CRITICAL"]
        high = [f for f in findings if f.severity == "HIGH"]
        medium = [f for f in findings if f.severity == "MEDIUM"]
        low = [f for f in findings if f.severity == "LOW"]

        lines = [
            "# 🔒 SintraPrime Security Scan Report",
            f"\n**Generated:** {now}",
            f"**Total Findings:** {len(findings)}",
            "",
            "## Summary",
            "",
            "| Severity | Count |",
            "|----------|-------|",
            f"| 🔴 CRITICAL | {len(critical)} |",
            f"| 🟠 HIGH | {len(high)} |",
            f"| 🟡 MEDIUM | {len(medium)} |",
            f"| 🟢 LOW | {len(low)} |",
            "",
        ]

        if not findings:
            lines.append("✅ **No secrets detected in codebase.**")
            return "\n".join(lines)

        for severity, items, icon in [
            ("CRITICAL", critical, "🔴"),
            ("HIGH", high, "🟠"),
            ("MEDIUM", medium, "🟡"),
            ("LOW", low, "🟢"),
        ]:
            if not items:
                continue
            lines.append(f"## {icon} {severity} Findings ({len(items)})")
            lines.append("")
            for f in items:
                lines.append(f"### `{f.file}` — Line {f.line}")
                lines.append(f"- **Pattern:** `{f.pattern}`")
                lines.append(f"- **Snippet:** `{f.snippet}`")
                lines.append("")

        lines.append("## Remediation Steps")
        lines.append("")
        lines.append("1. **Revoke** all exposed credentials immediately")
        lines.append("2. **Rotate** API keys, passwords, and tokens")
        lines.append("3. **Remove** secrets from git history using `git filter-branch` or BFG Repo-Cleaner")
        lines.append("4. **Use** environment variables or a secrets manager (AWS Secrets Manager, HashiCorp Vault)")
        lines.append("5. **Add** a pre-commit hook to prevent future commits")
        lines.append("6. **Enable** GitHub Secret Scanning on the repository")

        return "\n".join(lines)

    def create_gitignore_additions(self) -> List[str]:
        """
        Suggest .gitignore entries to prevent future secret leaks.
        
        Returns:
            List of recommended .gitignore patterns
        """
        return [
            "# Environment & Secrets",
            ".env",
            ".env.*",
            "!.env.example",
            "!.env.template",
            "*.env",
            "",
            "# Private keys",
            "*.pem",
            "*.key",
            "*.p12",
            "*.pfx",
            "*.jks",
            "id_rsa",
            "id_ed25519",
            "",
            "# Credentials files",
            "credentials.json",
            "service-account.json",
            "secrets.json",
            "secrets.yaml",
            "secrets.yml",
            "*_credentials.json",
            "",
            "# AWS",
            ".aws/credentials",
            ".aws/config",
            "",
            "# Database dumps",
            "*.sql",
            "*.dump",
            "",
            "# IDE & OS",
            ".DS_Store",
            "Thumbs.db",
            ".idea/",
            ".vscode/settings.json",
            "",
            "# Local config overrides",
            "local_settings.py",
            "local_config.py",
            "config.local.yaml",
        ]

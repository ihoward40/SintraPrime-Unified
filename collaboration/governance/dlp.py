"""Outbound DLP — prevent secret/tenant/matter leakage (§111)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class DLPVerdict:
    safe: bool = True
    violations: list[str] = field(default_factory=list)
    secret_found: bool = False
    wrong_tenant: bool = False
    wrong_matter: bool = False


class DLPScanner:
    """Inspect payloads before external transmission (§111)."""

    SECRET_PATTERNS: ClassVar[list] = [
        re.compile(r"[A-Za-z0-9+/]{40,}"),  # base64 long strings
        re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*\S+"),
        re.compile(r"(?i)bearer\s+[A-Za-z0-9\._\-]+"),
        re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----"),
    ]

    def scan(
        self,
        text: str,
        *,
        expected_tenant: str = "",
        expected_matter: str = "",
        actual_tenant: str = "",
        actual_matter: str = "",
    ) -> DLPVerdict:
        verdict = DLPVerdict()
        for pat in self.SECRET_PATTERNS:
            if pat.search(text):
                verdict.secret_found = True
                verdict.violations.append(f"secret_pattern: {pat.pattern[:40]}")
        if expected_tenant and actual_tenant and expected_tenant != actual_tenant:
            verdict.wrong_tenant = True
            verdict.violations.append(f"wrong_tenant: {actual_tenant} (expected {expected_tenant})")
        if expected_matter and actual_matter and expected_matter != actual_matter:
            verdict.wrong_matter = True
            verdict.violations.append(f"wrong_matter: {actual_matter} (expected {expected_matter})")
        verdict.safe = not verdict.violations
        return verdict

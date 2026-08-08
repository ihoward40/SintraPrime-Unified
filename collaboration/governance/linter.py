"""Governance linter and architecture linter (§86-87, §144-145)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar


class LintSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class LintIssue:
    rule: str
    severity: LintSeverity
    message: str
    location: str = ""


@dataclass
class LintResult:
    issues: list[LintIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(i.severity == LintSeverity.ERROR for i in self.issues)

    def errors(self) -> list[LintIssue]:
        return [i for i in self.issues if i.severity == LintSeverity.ERROR]


class GovernanceLinter:
    """Static inspection of workflow definitions, agent contracts, bindings (§86)."""

    def lint_workflow(self, definition: dict) -> LintResult:
        issues: list[LintIssue] = []
        # UNBOUNDED_LOOP
        if "max_iterations" not in definition and "max_hops" not in definition:
            issues.append(
                LintIssue(
                    "UNBOUNDED_LOOP", LintSeverity.ERROR, "workflow lacks max_iterations / max_hops"
                )
            )
        # MISSING_BUDGET
        if "budget" not in definition:
            issues.append(LintIssue("MISSING_BUDGET", LintSeverity.ERROR, "workflow lacks budget"))
        # MISSING_HASH
        if "hash" not in definition:
            issues.append(LintIssue("MISSING_HASH", LintSeverity.WARNING, "workflow lacks hash"))
        # MISSING_VERSION
        if "version" not in definition:
            issues.append(
                LintIssue("MISSING_VERSION", LintSeverity.WARNING, "workflow lacks version")
            )
        # MISSING_TENANT
        if "tenant_id" not in definition and "tenant_scope" not in definition:
            issues.append(
                LintIssue("MISSING_TENANT", LintSeverity.WARNING, "workflow lacks tenant scope")
            )
        # HIGH_AUTHORITY_NO_APPROVAL
        ac = definition.get("authority_class", "A0")
        if ac in ("A3", "A4") and "approval" not in definition:
            issues.append(
                LintIssue(
                    "HIGH_AUTHORITY_NO_APPROVAL",
                    LintSeverity.ERROR,
                    f"authority {ac} without approval gate",
                )
            )
        # SELF_CERTIFICATION
        if (
            definition.get("certifier_id")
            and definition.get("implementer_id")
            and definition["certifier_id"] == definition["implementer_id"]
        ):
            issues.append(
                LintIssue("SELF_CERTIFICATION", LintSeverity.ERROR, "implementer is certifier")
            )
        return LintResult(issues=issues)

    def lint_agent_contract(self, contract: dict) -> LintResult:
        issues: list[LintIssue] = []
        ac = contract.get("authority_class", "A0")
        public = contract.get("public_agent", False)
        if public and ac in ("A2", "A3", "A4"):
            issues.append(
                LintIssue(
                    "PRIVILEGED_PUBLIC_AGENT",
                    LintSeverity.ERROR,
                    f"public agent with authority {ac}",
                )
            )
        if not contract.get("forbidden_capabilities"):
            issues.append(
                LintIssue(
                    "NO_FORBIDDEN_CAPS",
                    LintSeverity.WARNING,
                    "agent contract missing forbidden capabilities",
                )
            )
        if not contract.get("behavior_contract_version"):
            issues.append(
                LintIssue("UNVERSIONED_CONTRACT", LintSeverity.WARNING, "contract missing version")
            )
        if not contract.get("behavior_contract_hash"):
            issues.append(
                LintIssue("UNHASHED_CONTRACT", LintSeverity.WARNING, "contract missing hash")
            )
        return LintResult(issues=issues)

    def lint_binding(self, binding: dict) -> LintResult:
        issues: list[LintIssue] = []
        if binding.get("response_mode") == "all_messages" and not binding.get(
            "all_messages_authorized"
        ):
            issues.append(
                LintIssue(
                    "UNAUTHORIZED_ALL_MESSAGES",
                    LintSeverity.ERROR,
                    "all_messages response mode without authorization",
                )
            )
        if not binding.get("allowed_event_types"):
            issues.append(
                LintIssue(
                    "NO_EVENT_TYPES",
                    LintSeverity.WARNING,
                    "binding without event type subscription",
                )
            )
        if binding.get("trust_zone") in ("T0_public",) and binding.get("authority_class") in (
            "A2",
            "A3",
            "A4",
        ):
            issues.append(
                LintIssue(
                    "PUBLIC_TRUST_HIGH_AUTH",
                    LintSeverity.ERROR,
                    "public trust zone with high authority",
                )
            )
        return LintResult(issues=issues)


class ArchitectureLinter:
    """Targeted anti-pattern detection (§87, §145). Only where reliable."""

    PROHIBITED_CALL_PATTERNS: ClassVar[list] = [
        "import openai",
        "requests.post(",
        "httpx.post(",
        "provider.call(",
        "direct_api_call",
    ]

    def scan_file(self, content: str, path: str = "") -> LintResult:
        issues: list[LintIssue] = []
        for i, line in enumerate(content.splitlines(), 1):
            for pat in self.PROHIBITED_CALL_PATTERNS:
                if pat in line and "# noqa:arch-lint" not in line:
                    issues.append(
                        LintIssue(
                            "DIRECT_PROVIDER_CALL",
                            LintSeverity.ERROR,
                            f"possible direct provider call pattern '{pat}'",
                            f"{path}:{i}",
                        )
                    )
        return LintResult(issues=issues)

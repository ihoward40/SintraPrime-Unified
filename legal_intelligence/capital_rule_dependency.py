"""Governed rule dependency mapping for the SintraPrime private-capital stack.

SP-CAPITAL-RULE-DEPENDENCY-001 maps operational-rule dependencies across policy,
alerts, underwriting, stress testing, committee reporting, and downstream actions.
It prevents silent orphaning when a rule is changed, superseded, or retired.
"""

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class RuleDependency:
    rule_id: str
    rule_version: str
    dependent_type: str
    dependent_id: str
    dependency_kind: str
    criticality: str = "MEDIUM"
    notes: str = ""


@dataclass(frozen=True)
class RuleDependencyReport:
    module_id: str
    rule_id: str
    rule_version: str
    dependency_count: int
    blocking_dependencies: tuple[str, ...]
    findings: tuple[str, ...]
    status: str
    beneficial_suggestions: tuple[str, ...]


class CapitalRuleDependencyEngine:
    MODULE_ID = "SP-CAPITAL-RULE-DEPENDENCY-001"
    VALID_DEPENDENT_TYPES = {
        "POLICY",
        "ALERT",
        "UNDERWRITING",
        "STRESS_SCENARIO",
        "COMMITTEE_REPORT",
        "DOWNSTREAM_ACTION",
        "SERVICING",
        "COLLATERAL",
        "ESCALATION",
        "DASHBOARD",
        "OTHER",
    }
    VALID_KINDS = {"READS", "TRIGGERS", "SETS_THRESHOLD", "REFERENCES", "BLOCKS", "ROUTES", "CALCULATES"}
    VALID_CRITICALITY = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

    def validate_dependency(self, dependency: RuleDependency) -> tuple[str, ...]:
        findings: list[str] = []
        if not dependency.rule_id.strip():
            findings.append("RULE_ID_REQUIRED")
        if not dependency.rule_version.strip():
            findings.append("RULE_VERSION_REQUIRED")
        if dependency.dependent_type not in self.VALID_DEPENDENT_TYPES:
            findings.append("INVALID_DEPENDENT_TYPE")
        if not dependency.dependent_id.strip():
            findings.append("DEPENDENT_ID_REQUIRED")
        if dependency.dependency_kind not in self.VALID_KINDS:
            findings.append("INVALID_DEPENDENCY_KIND")
        if dependency.criticality not in self.VALID_CRITICALITY:
            findings.append("INVALID_CRITICALITY")
        return tuple(findings)

    def impact_report(
        self,
        rule_id: str,
        rule_version: str,
        dependencies: Iterable[RuleDependency],
        *,
        resolved_dependents: Iterable[str] = (),
    ) -> RuleDependencyReport:
        rows = [
            dep for dep in dependencies
            if dep.rule_id == rule_id and dep.rule_version == rule_version
        ]
        resolved = {str(item).strip() for item in resolved_dependents if str(item).strip()}
        findings: list[str] = []

        if not rule_id.strip():
            findings.append("RULE_ID_REQUIRED")
        if not rule_version.strip():
            findings.append("RULE_VERSION_REQUIRED")

        for dep in rows:
            findings.extend(self.validate_dependency(dep))

        blocking = sorted({
            dep.dependent_id
            for dep in rows
            if dep.criticality in {"HIGH", "CRITICAL"}
            and dep.dependent_id not in resolved
        })
        if blocking:
            findings.append("UNRESOLVED_HIGH_CRITICAL_DEPENDENCIES")

        status = "BLOCK_CHANGE" if blocking else "READY_FOR_GOVERNED_CHANGE"
        if not rows:
            status = "NO_DEPENDENCIES_RECORDED"
            findings.append("DEPENDENCY_COVERAGE_NOT_PROVEN")

        suggestions = [
            "Persist dependencies against exact rule versions, not rule names alone.",
            "Re-run dependency discovery before promotion, supersession, or retirement because downstream consumers can change over time.",
            "Require explicit migration or replacement for HIGH/CRITICAL dependents before a rule change becomes effective.",
            "Include the impact report in SP-POLICY-CHANGE-CONTROL-001 or the governed rule-retirement decision record.",
        ]
        if not rows:
            suggestions.append("Treat missing dependency records as unknown impact, not proof that the rule is isolated.")

        return RuleDependencyReport(
            module_id=self.MODULE_ID,
            rule_id=rule_id,
            rule_version=rule_version,
            dependency_count=len(rows),
            blocking_dependencies=tuple(blocking),
            findings=tuple(dict.fromkeys(findings)),
            status=status,
            beneficial_suggestions=tuple(suggestions),
        )

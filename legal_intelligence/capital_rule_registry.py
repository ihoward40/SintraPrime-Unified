"""Governed operational-rule registry for the SintraPrime private-capital stack.

SP-CAPITAL-RULE-REGISTRY-001 assigns every operational rule a governed identity,
version lineage, owner, rationale, source, review history, performance evidence,
and explicit retirement criteria.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Iterable


@dataclass
class CapitalRuleRecord:
    rule_id: str
    version: str
    owner: str
    category: str
    rationale: str
    source: str
    effective_date: date
    review_due_date: date
    status: str = "ACTIVE"
    supersedes_version: str | None = None
    replacement_rule_id: str | None = None
    retirement_criteria: list[str] = field(default_factory=list)
    test_history: list[str] = field(default_factory=list)
    false_positive_rate: float | None = None
    false_negative_incidents: int = 0
    validation_classification: str | None = None
    policy_id: str | None = None
    policy_version: str | None = None


@dataclass(frozen=True)
class RuleRegistryDecision:
    module_id: str
    rule_id: str
    version: str
    status: str
    valid: bool
    findings: tuple[str, ...]
    beneficial_suggestions: tuple[str, ...]


class CapitalRuleRegistryEngine:
    MODULE_ID = "SP-CAPITAL-RULE-REGISTRY-001"
    VALID_CATEGORIES = {
        "EARLY_WARNING",
        "STRESS_ASSUMPTION",
        "UNDERWRITING_THRESHOLD",
        "POLICY_LIMIT",
        "SERVICING_RULE",
        "COLLATERAL_RULE",
        "ESCALATION_RULE",
        "OTHER",
    }
    VALID_STATUSES = {"DRAFT", "ACTIVE", "UNDER_REVIEW", "RETIRED", "SUPERSEDED"}

    def validate(self, rule: CapitalRuleRecord, *, as_of: date | None = None) -> RuleRegistryDecision:
        findings: list[str] = []
        now = as_of or date.today()

        required = {
            "RULE_ID_REQUIRED": rule.rule_id,
            "VERSION_REQUIRED": rule.version,
            "OWNER_REQUIRED": rule.owner,
            "RATIONALE_REQUIRED": rule.rationale,
            "SOURCE_REQUIRED": rule.source,
        }
        for code, value in required.items():
            if not str(value).strip():
                findings.append(code)

        if rule.category not in self.VALID_CATEGORIES:
            findings.append("INVALID_RULE_CATEGORY")
        if rule.status not in self.VALID_STATUSES:
            findings.append("INVALID_RULE_STATUS")
        if rule.review_due_date < rule.effective_date:
            findings.append("REVIEW_DATE_PRECEDES_EFFECTIVE_DATE")
        if rule.status == "ACTIVE" and now > rule.review_due_date:
            findings.append("RULE_REVIEW_OVERDUE")
        if rule.status in {"RETIRED", "SUPERSEDED"} and not rule.retirement_criteria:
            findings.append("RETIREMENT_CRITERIA_REQUIRED")
        if rule.status == "SUPERSEDED" and not rule.replacement_rule_id:
            findings.append("REPLACEMENT_RULE_REQUIRED")
        if rule.false_positive_rate is not None and not 0 <= rule.false_positive_rate <= 1:
            findings.append("FALSE_POSITIVE_RATE_OUT_OF_RANGE")
        if rule.false_negative_incidents < 0:
            findings.append("FALSE_NEGATIVE_INCIDENTS_INVALID")

        suggestions = [
            "Persist each rule version as immutable history; create a new version rather than overwriting an approved rule.",
            "Link validation evidence and test history to the exact rule version used in production decisions.",
            "Require explicit retirement or supersession instead of allowing stale rules to remain active indefinitely.",
            "Route material threshold changes through SP-POLICY-CHANGE-CONTROL-001 and preserve rollback lineage.",
        ]
        if "RULE_REVIEW_OVERDUE" in findings:
            suggestions.append("Move the rule to UNDER_REVIEW or complete validation before expanding reliance on it.")
        if rule.false_negative_incidents > 0:
            suggestions.append("Review every false-negative incident for severity, root cause, and whether immediate control redesign is required.")

        hard_fail = [
            code for code in findings
            if code not in {"RULE_REVIEW_OVERDUE"}
        ]
        return RuleRegistryDecision(
            module_id=self.MODULE_ID,
            rule_id=rule.rule_id,
            version=rule.version,
            status=rule.status,
            valid=not hard_fail,
            findings=tuple(findings),
            beneficial_suggestions=tuple(suggestions),
        )

    def retirement_ready(self, rule: CapitalRuleRecord, evidence: Iterable[str]) -> RuleRegistryDecision:
        evidence_refs = [str(item).strip() for item in evidence if str(item).strip()]
        findings: list[str] = []
        if not rule.retirement_criteria:
            findings.append("RETIREMENT_CRITERIA_REQUIRED")
        if not evidence_refs:
            findings.append("RETIREMENT_EVIDENCE_REQUIRED")
        if not rule.replacement_rule_id and rule.status != "RETIRED":
            findings.append("REPLACEMENT_OR_EXPLICIT_NO_REPLACEMENT_DECISION_REQUIRED")

        return RuleRegistryDecision(
            module_id=self.MODULE_ID,
            rule_id=rule.rule_id,
            version=rule.version,
            status="RETIREMENT_READY" if not findings else "BLOCK_RETIREMENT",
            valid=not findings,
            findings=tuple(findings),
            beneficial_suggestions=(
                "Document why the rule is no longer useful and what control, if any, replaces it.",
                "Preserve historical decisions made under the retired rule version for reproducibility.",
                "Re-run affected monitoring and policy dependency checks before retirement becomes effective.",
            ),
        )

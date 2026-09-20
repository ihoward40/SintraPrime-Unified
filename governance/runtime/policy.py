"""Fail-closed runtime policy for SintraPrime executive officers.

This module contains no network, subprocess, filesystem-write, legal, tax, or
financial execution capability. It only evaluates whether a requested action
may proceed automatically or requires Principal approval.
"""

from dataclasses import dataclass

PRINCIPAL = "Isiah T. Howard"

OFFICER_ALLOWED = {
    "viktor_magnus": {
        "inventory", "architecture", "code_proposal", "staging_test",
        "security_assessment", "rollback_plan",
    },
    "tasklet_commander": {
        "planning", "task_breakdown", "routing", "tracking", "receipts",
        "blocker_detection",
    },
    "legacy_engine": {
        "read", "retrieve", "classify", "summarize", "cross_reference", "route",
    },
    "lex_aeternum": {
        "research", "issue_spotting", "draft_support", "compliance_checklist",
    },
    "justice_scribe": {"evidence_index", "chronology", "record_organization"},
    "hermes_prime": {"drafting", "research", "communication_planning"},
    "oracle_sentinel": {"analysis", "source_validation", "forecasting"},
}

ALWAYS_GATED = {
    "commit", "push", "production_change", "production_deploy",
    "tunnel_activation", "external_send", "publication", "legal_filing",
    "legal_strategy", "tax_strategy", "financial_action", "financial_decision",
    "trust_amendment", "persistent_memory", "automatic_memory_injection",
    "encryption_initialization", "key_generation", "permission_expansion",
    "confidential_ingestion",
}


@dataclass(frozen=True)
class Decision:
    allowed: bool
    requires_principal_approval: bool
    reason: str


class GovernancePolicy:
    """Pure evaluator. Unknown officers/actions fail closed."""

    def evaluate(
        self,
        officer: str,
        action: str,
        *,
        principal_approved: bool = False,
        confidential: bool = False,
        public_repository: bool = False,
    ) -> Decision:
        officer = officer.strip().lower()
        action = action.strip().lower()

        if officer not in OFFICER_ALLOWED:
            return Decision(False, False, "unknown officer: fail closed")

        if confidential and public_repository:
            return Decision(False, False, "confidential data cannot enter a public repository")

        if action in ALWAYS_GATED:
            if principal_approved:
                return Decision(True, True, f"approved by Principal: {PRINCIPAL}")
            return Decision(False, True, "explicit Principal approval required")

        if action not in OFFICER_ALLOWED[officer]:
            return Decision(False, False, "action is outside officer charter")

        return Decision(True, False, "allowed within bounded officer charter")

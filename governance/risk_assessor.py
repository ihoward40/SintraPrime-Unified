"""
risk_assessor.py — Automatic risk scoring for agent actions.

Evaluates the risk level of any agent action based on pre-configured
rules, domain policies, and organizational thresholds.
"""

from __future__ import annotations

import fnmatch
from typing import Dict, List, Optional, Tuple

from governance.risk_types import (
    ActionRisk,
    GovernancePolicy,
    RiskLevel,
    Rule,
)


# ---------------------------------------------------------------------------
# Built-in risk classification table
# ---------------------------------------------------------------------------

_DEFAULT_RISK_RULES: List[Tuple[str, RiskLevel, str, bool, bool, str, str]] = [
    # (action_pattern, risk_level, reason, requires_approval, reversible, estimated_impact, domain)

    # CRITICAL
    ("send_payment",          RiskLevel.CRITICAL, "Irreversible financial transaction",       True,  False, "Potential financial loss",          "financial"),
    ("wire_transfer",         RiskLevel.CRITICAL, "Irreversible high-value transfer",          True,  False, "Major financial exposure",          "financial"),
    ("delete_all_data",       RiskLevel.CRITICAL, "Permanent data destruction",                True,  False, "Complete data loss",                "data"),
    ("file_legal_document",   RiskLevel.CRITICAL, "Legally binding filing",                   True,  False, "Legal liability / deadlines",       "legal"),
    ("sign_contract",         RiskLevel.CRITICAL, "Binding contractual obligation",           True,  False, "Legal and financial commitment",    "legal"),
    ("execute_*_contract",    RiskLevel.CRITICAL, "Contract execution",                       True,  False, "Legal and financial commitment",    "legal"),
    ("initiate_bankruptcy",   RiskLevel.CRITICAL, "Major legal proceeding",                   True,  False, "Corporate insolvency filing",       "legal"),

    # HIGH
    ("send_email_to_client",      RiskLevel.HIGH, "Client-facing communication",              True,  True,  "Reputational / legal exposure",     "communication"),
    ("update_financial_record",   RiskLevel.HIGH, "Modifies financial data",                  True,  True,  "Financial record integrity",        "financial"),
    ("publish_document",          RiskLevel.HIGH, "Public-facing content",                    True,  True,  "Reputational / regulatory risk",    "communication"),
    ("schedule_court_filing",     RiskLevel.HIGH, "Legal deadline scheduling",               True,  True,  "Missed deadline = malpractice",     "legal"),
    ("send_bulk_email",           RiskLevel.HIGH, "Mass communication",                       True,  True,  "Reputational / GDPR risk",          "communication"),
    ("delete_records",            RiskLevel.HIGH, "Data deletion",                            True,  False, "Potential data loss",               "data"),
    ("modify_permissions",        RiskLevel.HIGH, "Access control change",                    True,  True,  "Security risk",                     "security"),
    ("create_invoice",            RiskLevel.HIGH, "Financial document creation",              True,  True,  "Financial exposure",                "financial"),
    ("access_pii_data",           RiskLevel.HIGH, "Personal data access",                    True,  True,  "Privacy / GDPR risk",               "compliance"),

    # MEDIUM
    ("draft_document",        RiskLevel.MEDIUM, "Document creation (not published)",         False, True,  "Low – internal draft",              "document"),
    ("search_external_api",   RiskLevel.MEDIUM, "External API call",                        False, True,  "Data exposure / rate limits",       "data"),
    ("update_case_notes",     RiskLevel.MEDIUM, "Case record modification",                 False, True,  "Case management accuracy",          "legal"),
    ("generate_report",       RiskLevel.MEDIUM, "Report generation",                        False, True,  "Information accuracy",              "document"),
    ("send_internal_email",   RiskLevel.MEDIUM, "Internal communication",                   False, True,  "Internal only",                     "communication"),
    ("schedule_meeting",      RiskLevel.MEDIUM, "Calendar scheduling",                      False, True,  "Scheduling conflict risk",          "general"),
    ("export_data",           RiskLevel.MEDIUM, "Data export",                              False, True,  "Data portability risk",             "data"),
    ("update_contact_info",   RiskLevel.MEDIUM, "Contact record update",                    False, True,  "Data accuracy",                     "data"),

    # LOW
    ("read_data",             RiskLevel.LOW,    "Read-only data access",                    False, True,  "Minimal – read only",               "data"),
    ("internal_calculation",  RiskLevel.LOW,    "Internal computation",                     False, True,  "None",                              "general"),
    ("search_database",       RiskLevel.LOW,    "Database query (read-only)",               False, True,  "None",                              "data"),
    ("format_document",       RiskLevel.LOW,    "Document formatting",                      False, True,  "None",                              "document"),
    ("list_records",          RiskLevel.LOW,    "Listing records",                          False, True,  "None",                              "data"),
    ("get_status",            RiskLevel.LOW,    "Status check",                             False, True,  "None",                              "general"),
    ("validate_data",         RiskLevel.LOW,    "Data validation",                          False, True,  "None",                              "data"),
    ("log_event",             RiskLevel.LOW,    "Audit logging",                            False, True,  "None",                              "general"),
]


class RiskAssessor:
    """
    Automatically evaluates the risk level of agent actions.

    Supports custom risk thresholds per organization and domain-specific
    governance policies for legal, financial, and communication actions.
    """

    def __init__(self, org_risk_threshold: RiskLevel = RiskLevel.HIGH) -> None:
        """
        Args:
            org_risk_threshold: Minimum risk level that requires approval
                                 for this organization. Defaults to HIGH.
        """
        self.org_risk_threshold = org_risk_threshold
        self._custom_rules: List[Tuple[str, RiskLevel, str, bool, bool, str, str]] = []
        self._policies: Dict[str, GovernancePolicy] = self._build_default_policies()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def assess(self, action_type: str, payload: Optional[Dict] = None) -> ActionRisk:
        """
        Assess the risk of a single action.

        Args:
            action_type: The action identifier (e.g. 'send_payment').
            payload: Optional action payload for context-sensitive scoring.

        Returns:
            ActionRisk with full assessment details.
        """
        payload = payload or {}
        all_rules = self._custom_rules + _DEFAULT_RISK_RULES

        for pattern, risk_level, reason, req_approval, reversible, impact, domain in all_rules:
            if fnmatch.fnmatch(action_type, pattern) or action_type == pattern:
                # Allow org threshold to override requires_approval
                effective_requires_approval = (
                    req_approval or risk_level >= self.org_risk_threshold
                )
                return ActionRisk(
                    action_type=action_type,
                    risk_level=risk_level,
                    reason=reason,
                    requires_approval=effective_requires_approval,
                    reversible=reversible,
                    estimated_impact=self._enrich_impact(impact, payload),
                    domain=domain,
                    metadata={"payload_keys": list(payload.keys())},
                )

        # Default: unknown action = MEDIUM risk
        return ActionRisk(
            action_type=action_type,
            risk_level=RiskLevel.MEDIUM,
            reason="Unknown action type — defaulting to MEDIUM risk",
            requires_approval=RiskLevel.MEDIUM >= self.org_risk_threshold,
            reversible=True,
            estimated_impact="Unknown — manual review recommended",
            domain="general",
            metadata={"payload_keys": list(payload.keys())},
        )

    def assess_sequence(self, actions: List[str]) -> List[ActionRisk]:
        """
        Assess an ordered chain of actions.

        Returns a list of ActionRisk objects, one per action.
        High-risk sequences (e.g. read → send_payment) are flagged with
        escalated metadata.
        """
        results: List[ActionRisk] = []
        max_level = RiskLevel.LOW

        for i, action in enumerate(actions):
            risk = self.assess(action)
            if risk.risk_level > max_level:
                max_level = risk.risk_level
            risk.metadata["sequence_index"] = i
            risk.metadata["sequence_length"] = len(actions)
            results.append(risk)

        # If sequence contains CRITICAL, escalate all HIGH to CRITICAL
        if max_level == RiskLevel.CRITICAL:
            for r in results:
                if r.risk_level == RiskLevel.HIGH:
                    r.metadata["escalated"] = True

        return results

    def get_policy(self, domain: str) -> GovernancePolicy:
        """
        Retrieve governance policy for a domain.

        Supported domains: legal, financial, communication, data, security, general.
        """
        return self._policies.get(domain, self._policies["general"])

    def add_custom_rule(
        self,
        pattern: str,
        risk_level: RiskLevel,
        reason: str,
        requires_approval: bool,
        reversible: bool,
        estimated_impact: str,
        domain: str = "custom",
    ) -> None:
        """Register a custom risk rule (prepended, so it takes priority)."""
        self._custom_rules.insert(0, (
            pattern, risk_level, reason,
            requires_approval, reversible, estimated_impact, domain
        ))

    def set_org_threshold(self, threshold: RiskLevel) -> None:
        """Update the organization-wide risk threshold for approval requirements."""
        self.org_risk_threshold = threshold

    def get_all_rules_summary(self) -> List[Dict]:
        """Return a summary of all registered risk rules."""
        all_rules = self._custom_rules + _DEFAULT_RISK_RULES
        return [
            {
                "pattern": pattern,
                "risk_level": rl.value,
                "reason": reason,
                "requires_approval": req,
                "reversible": rev,
                "domain": domain,
            }
            for pattern, rl, reason, req, rev, _, domain in all_rules
        ]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _enrich_impact(self, base_impact: str, payload: Dict) -> str:
        """Add context-specific details to impact description."""
        if "amount" in payload:
            return f"{base_impact} — Amount: {payload['amount']}"
        if "recipient_count" in payload:
            return f"{base_impact} — Recipients: {payload['recipient_count']}"
        return base_impact

    def _build_default_policies(self) -> Dict[str, GovernancePolicy]:
        """Build default governance policies for each domain."""
        return {
            "legal": GovernancePolicy(
                name="Legal Domain Policy",
                description="Governs all legal actions including filings, contracts, and court matters",
                applies_to=["file_*", "sign_*", "schedule_court_*", "execute_*_contract"],
                rules=[
                    Rule(
                        name="Legal Filing Approval",
                        description="All legal filings require partner approval",
                        action_pattern="file_*",
                        risk_threshold=RiskLevel.HIGH,
                        requires_approval=True,
                        notify_roles=["partner", "compliance_officer"],
                    ),
                    Rule(
                        name="Contract Signing",
                        description="Contracts above threshold require senior approval",
                        action_pattern="sign_*",
                        risk_threshold=RiskLevel.CRITICAL,
                        requires_approval=True,
                        notify_roles=["partner", "legal_ops"],
                    ),
                ],
            ),
            "financial": GovernancePolicy(
                name="Financial Domain Policy",
                description="Governs payments, transfers, and financial record modifications",
                applies_to=["send_payment", "wire_transfer", "update_financial_*", "create_invoice"],
                rules=[
                    Rule(
                        name="Payment Approval",
                        description="All payments require CFO or designated approver",
                        action_pattern="send_payment",
                        risk_threshold=RiskLevel.CRITICAL,
                        requires_approval=True,
                        notify_roles=["cfo", "finance_ops"],
                    ),
                    Rule(
                        name="Wire Transfer",
                        description="Wire transfers require dual approval",
                        action_pattern="wire_transfer",
                        risk_threshold=RiskLevel.CRITICAL,
                        requires_approval=True,
                        notify_roles=["cfo", "ceo"],
                    ),
                ],
            ),
            "communication": GovernancePolicy(
                name="Communication Domain Policy",
                description="Governs client-facing and bulk communications",
                applies_to=["send_email_to_client", "publish_document", "send_bulk_email"],
                rules=[
                    Rule(
                        name="Client Communication Review",
                        description="All client emails require legal review",
                        action_pattern="send_email_to_client",
                        risk_threshold=RiskLevel.HIGH,
                        requires_approval=True,
                        notify_roles=["legal_review", "account_manager"],
                    ),
                ],
            ),
            "data": GovernancePolicy(
                name="Data Domain Policy",
                description="Governs data access, deletion, and export",
                applies_to=["delete_*", "export_*", "access_pii_*"],
                rules=[
                    Rule(
                        name="Data Deletion",
                        description="Data deletion requires data governance approval",
                        action_pattern="delete_*",
                        risk_threshold=RiskLevel.HIGH,
                        requires_approval=True,
                        notify_roles=["data_steward", "dpo"],
                    ),
                ],
            ),
            "security": GovernancePolicy(
                name="Security Domain Policy",
                description="Governs permission changes and security-sensitive actions",
                applies_to=["modify_permissions", "grant_access", "revoke_access"],
                rules=[
                    Rule(
                        name="Permission Modification",
                        description="Access control changes require CISO approval",
                        action_pattern="modify_permissions",
                        risk_threshold=RiskLevel.HIGH,
                        requires_approval=True,
                        notify_roles=["ciso", "security_team"],
                    ),
                ],
            ),
            "general": GovernancePolicy(
                name="General Policy",
                description="Default policy for uncategorized actions",
                applies_to=["*"],
                rules=[
                    Rule(
                        name="Default Rule",
                        description="High and critical actions require approval",
                        action_pattern="*",
                        risk_threshold=RiskLevel.HIGH,
                        requires_approval=True,
                        notify_roles=["supervisor"],
                    ),
                ],
            ),
        }

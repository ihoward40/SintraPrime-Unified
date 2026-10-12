"""
risk_assessor.py — Automatic risk scoring for agent actions.

Evaluates the risk level of any agent action based on pre-configured
rules, domain policies, and organizational thresholds.
"""

from __future__ import annotations

import fnmatch
import hashlib
import math
import time
from contextlib import suppress
from enum import Enum
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
    (
        "send_payment",
        RiskLevel.CRITICAL,
        "Irreversible financial transaction",
        True,
        False,
        "Potential financial loss",
        "financial",
    ),
    (
        "wire_transfer",
        RiskLevel.CRITICAL,
        "Irreversible high-value transfer",
        True,
        False,
        "Major financial exposure",
        "financial",
    ),
    (
        "delete_all_data",
        RiskLevel.CRITICAL,
        "Permanent data destruction",
        True,
        False,
        "Complete data loss",
        "data",
    ),
    (
        "file_legal_document",
        RiskLevel.CRITICAL,
        "Legally binding filing",
        True,
        False,
        "Legal liability / deadlines",
        "legal",
    ),
    (
        "sign_contract",
        RiskLevel.CRITICAL,
        "Binding contractual obligation",
        True,
        False,
        "Legal and financial commitment",
        "legal",
    ),
    (
        "execute_*_contract",
        RiskLevel.CRITICAL,
        "Contract execution",
        True,
        False,
        "Legal and financial commitment",
        "legal",
    ),
    (
        "initiate_bankruptcy",
        RiskLevel.CRITICAL,
        "Major legal proceeding",
        True,
        False,
        "Corporate insolvency filing",
        "legal",
    ),
    # HIGH
    (
        "send_email_to_client",
        RiskLevel.HIGH,
        "Client-facing communication",
        True,
        True,
        "Reputational / legal exposure",
        "communication",
    ),
    (
        "update_financial_record",
        RiskLevel.HIGH,
        "Modifies financial data",
        True,
        True,
        "Financial record integrity",
        "financial",
    ),
    (
        "publish_document",
        RiskLevel.HIGH,
        "Public-facing content",
        True,
        True,
        "Reputational / regulatory risk",
        "communication",
    ),
    (
        "schedule_court_filing",
        RiskLevel.HIGH,
        "Legal deadline scheduling",
        True,
        True,
        "Missed deadline = malpractice",
        "legal",
    ),
    (
        "send_bulk_email",
        RiskLevel.HIGH,
        "Mass communication",
        True,
        True,
        "Reputational / GDPR risk",
        "communication",
    ),
    ("delete_records", RiskLevel.HIGH, "Data deletion", True, False, "Potential data loss", "data"),
    (
        "modify_permissions",
        RiskLevel.HIGH,
        "Access control change",
        True,
        True,
        "Security risk",
        "security",
    ),
    (
        "create_invoice",
        RiskLevel.HIGH,
        "Financial document creation",
        True,
        True,
        "Financial exposure",
        "financial",
    ),
    (
        "access_pii_data",
        RiskLevel.HIGH,
        "Personal data access",
        True,
        True,
        "Privacy / GDPR risk",
        "compliance",
    ),
    # MEDIUM
    (
        "draft_document",
        RiskLevel.MEDIUM,
        "Document creation (not published)",
        False,
        True,
        "Low – internal draft",
        "document",
    ),
    (
        "search_external_api",
        RiskLevel.MEDIUM,
        "External API call",
        False,
        True,
        "Data exposure / rate limits",
        "data",
    ),
    (
        "update_case_notes",
        RiskLevel.MEDIUM,
        "Case record modification",
        False,
        True,
        "Case management accuracy",
        "legal",
    ),
    (
        "generate_report",
        RiskLevel.MEDIUM,
        "Report generation",
        False,
        True,
        "Information accuracy",
        "document",
    ),
    (
        "send_internal_email",
        RiskLevel.MEDIUM,
        "Internal communication",
        False,
        True,
        "Internal only",
        "communication",
    ),
    (
        "schedule_meeting",
        RiskLevel.MEDIUM,
        "Calendar scheduling",
        False,
        True,
        "Scheduling conflict risk",
        "general",
    ),
    ("export_data", RiskLevel.MEDIUM, "Data export", False, True, "Data portability risk", "data"),
    (
        "update_contact_info",
        RiskLevel.MEDIUM,
        "Contact record update",
        False,
        True,
        "Data accuracy",
        "data",
    ),
    # LOW
    (
        "read_data",
        RiskLevel.LOW,
        "Read-only data access",
        False,
        True,
        "Minimal – read only",
        "data",
    ),
    ("internal_calculation", RiskLevel.LOW, "Internal computation", False, True, "None", "general"),
    ("search_database", RiskLevel.LOW, "Database query (read-only)", False, True, "None", "data"),
    ("format_document", RiskLevel.LOW, "Document formatting", False, True, "None", "document"),
    ("list_records", RiskLevel.LOW, "Listing records", False, True, "None", "data"),
    ("get_status", RiskLevel.LOW, "Status check", False, True, "None", "general"),
    ("validate_data", RiskLevel.LOW, "Data validation", False, True, "None", "data"),
    ("log_event", RiskLevel.LOW, "Audit logging", False, True, "None", "general"),
]


class UnknownActionPolicy(str, Enum):
    """SP-AGENT-PARLIAMENT-001 B1: policy for actions matching no risk rule.

    FAIL_CLOSED (default): unknown actions require human approval, are treated
    as irreversible, and never execute silently.
    AUDITED_EXCEPTION: governed, time-limited opt-in restoring legacy MEDIUM
    behavior; requires ``exception_reference`` and a future
    ``exception_expires_at`` at construction and auto-reverts to FAIL_CLOSED
    on expiry. An agent can never grant this exception to itself.
    """

    FAIL_CLOSED = "fail_closed"
    AUDITED_EXCEPTION = "audited_exception"


_LEGACY_UNKNOWN_REASON = (
    "Unknown action type — legacy MEDIUM policy (audited exception active)"
)


def _authority_signature(
    unknown_action_policy: "UnknownActionPolicy",
    exception_reference: str,
    exception_expires_at: float,
    org_risk_threshold: "RiskLevel",
) -> str:
    """Deterministic integrity signature over the authority-relevant config.

    A-FIX (SP-PARLIAMENT-C-REVIEW-001): captured at construction and re-checked
    by RiskAssessor.assess() to detect post-construction tampering that would
    expand authority (e.g. flipping the unknown-action policy to
    AUDITED_EXCEPTION, forging an exception reference/expiry, or altering the
    risk threshold outside the audited set_org_threshold API).
    """

    def _norm(value: object) -> str:
        if value is None:
            return "<none>"
        return str(getattr(value, "value", value))

    expiry = (
        repr(float(exception_expires_at))
        if isinstance(exception_expires_at, (int, float))
        and not isinstance(exception_expires_at, bool)
        else str(exception_expires_at)
    )
    material = "|".join(
        (
            _norm(unknown_action_policy),
            _norm(exception_reference),
            expiry,
            _norm(org_risk_threshold),
        )
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


class RiskAssessor:
    """
    Automatically evaluates the risk level of agent actions.

    Supports custom risk thresholds per organization and domain-specific
    governance policies for legal, financial, and communication actions.
    """

    def __init__(
        self,
        org_risk_threshold: RiskLevel = RiskLevel.HIGH,
        unknown_action_policy: UnknownActionPolicy = UnknownActionPolicy.FAIL_CLOSED,
        exception_reference: str = "",
        exception_expires_at: float = 0.0,
    ) -> None:
        """
        Args:
            org_risk_threshold: Minimum risk level that requires approval
                                 for this organization. Defaults to HIGH.
            unknown_action_policy: B1 policy for unknown actions.
                                 Defaults to FAIL_CLOSED.
            exception_reference: Required (non-empty) when AUDITED_EXCEPTION;
                                 auditable authority reference. Construction
                                 is governance-only — agents never pass this.
            exception_expires_at: Required future epoch seconds when
                                 AUDITED_EXCEPTION; the policy auto-reverts to
                                 FAIL_CLOSED after this instant.
        """
        self.org_risk_threshold = org_risk_threshold
        if unknown_action_policy is UnknownActionPolicy.AUDITED_EXCEPTION:
            if not exception_reference:
                raise ValueError(
                    "AUDITED_EXCEPTION requires exception_reference "
                    "(B1: no ungoverned legacy behavior)"
                )
            if not (
                math.isfinite(exception_expires_at)
                and exception_expires_at > time.time()
            ):
                raise ValueError(
                    "AUDITED_EXCEPTION requires a finite future exception_expires_at"
                )
            self._exception_audit: List[Dict[str, object]] = [
                {
                    "event": "UNKNOWN_ACTION_EXCEPTION_GRANTED",
                    "exception_reference": exception_reference,
                    "exception_expires_at": exception_expires_at,
                    "granted_at": time.time(),
                }
            ]
        else:
            self._exception_audit = []
        self.unknown_action_policy = unknown_action_policy
        self.exception_reference = exception_reference
        self.exception_expires_at = exception_expires_at
        self._custom_rules: List[Tuple[str, RiskLevel, str, bool, bool, str, str]] = []
        self._policies: Dict[str, GovernancePolicy] = self._build_default_policies()
        # A-FIX: seal the authority-relevant configuration captured at
        # construction, then enable post-construction mutation auditing. The
        # seal is validated at use-time in assess(); reassignment alone cannot
        # restore the legacy unknown-action approval bypass.
        self._authority_signature = _authority_signature(
            self.unknown_action_policy,
            self.exception_reference,
            self.exception_expires_at,
            self.org_risk_threshold,
        )
        self._authority_sealed = True

    # A-FIX (SP-PARLIAMENT-C-REVIEW-001): authority-relevant fields that must
    # not be reconfigured by ordinary application code after construction.
    _PROTECTED_AUTHORITY_FIELDS = (
        "unknown_action_policy",
        "exception_reference",
        "exception_expires_at",
        "org_risk_threshold",
    )

    def __setattr__(self, name: str, value: object) -> None:
        """A-FIX: audit post-construction mutation of authority fields.

        Defense-in-depth audit only — enforcement is the use-time integrity
        check in assess(). The audited set_org_threshold API bypasses this log
        (it records its own AUTHORITY_THRESHOLD_UPDATED event and re-seals).
        """
        if name in RiskAssessor._PROTECTED_AUTHORITY_FIELDS and object.__getattribute__(
            self, "__dict__"
        ).get("_authority_sealed", False):
            with suppress(Exception):
                object.__getattribute__(self, "_exception_audit").append(
                    {
                        "event": "AUTHORITY_CONFIG_MUTATION_DETECTED",
                        "field": name,
                        "at": time.time(),
                    }
                )
        object.__setattr__(self, name, value)

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

        # A-FIX + R2 (SP-PARLIAMENT-A-FIX-R2R3-001): authorization snapshot
        # integrity. Capture the authority-relevant configuration into a SINGLE
        # coherent local snapshot, then validate that snapshot against the
        # construction seal. The authorization decision is derived EXCLUSIVELY
        # from this validated snapshot; no authority attribute is re-read after
        # validation, so a concurrent post-construction mutation (the
        # validation-to-decision race) cannot influence the decision. A snapshot
        # that is torn or inconsistent with the seal (missing/corrupt seal, or a
        # mix of pre- and post-mutation values) fails the signature comparison
        # and fails closed. Replacing the signature together with the config is a
        # distinct, privileged threat (R1) outside this fix's scope.
        snapshot_policy = self.unknown_action_policy
        snapshot_reference = self.exception_reference
        snapshot_expires_at = self.exception_expires_at
        snapshot_threshold = self.org_risk_threshold
        try:
            sealed = object.__getattribute__(self, "_authority_signature")
            live = _authority_signature(
                snapshot_policy,
                snapshot_reference,
                snapshot_expires_at,
                snapshot_threshold,
            )
        except Exception:
            sealed, live = None, None
        if not sealed or sealed != live:
            with suppress(Exception):
                self._record_audit(
                    "AUTHORITY_INTEGRITY_VIOLATION", action_type=action_type
                )
            return self._fail_closed_unknown(
                action_type, payload, "authority-config-integrity"
            )

        for pattern, risk_level, reason, req_approval, reversible, impact, domain in all_rules:
            if fnmatch.fnmatch(action_type, pattern) or action_type == pattern:
                # Allow org threshold to override requires_approval. The
                # threshold comes from the validated snapshot, never a re-read.
                effective_requires_approval = req_approval or risk_level >= snapshot_threshold
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

        # B1 (SP-AGENT-PARLIAMENT-001): unknown actions fail closed by default.
        # An AUDITED_EXCEPTION restores legacy MEDIUM behavior only while the
        # audited, time-limited exception is unexpired; expiry reverts to
        # FAIL_CLOSED automatically on the next assess() call. The exception
        # decision is derived from the validated snapshot (R2), so a concurrent
        # mutation between validation and decision cannot downgrade the result.
        exception_active = (
            snapshot_policy is UnknownActionPolicy.AUDITED_EXCEPTION
            and snapshot_expires_at > time.time()
        )
        if not exception_active:
            return ActionRisk(
                action_type=action_type,
                risk_level=RiskLevel.CRITICAL,
                reason="Unknown action type — fail-closed default (human approval required)",
                requires_approval=True,
                reversible=False,
                estimated_impact="Unclassified — manual review required",
                domain="general",
                metadata={
                    "payload_keys": list(payload.keys()),
                    "unknown_action_policy": snapshot_policy.value,
                },
            )
        try:
            self._record_audit(
                "UNKNOWN_ACTION_LEGACY_PATH_USED",
                exception_reference=snapshot_reference,
                action_type=action_type,
            )
        except Exception:
            # A-FIX: audit persistence unavailable — legacy authority must not
            # be granted. Fail closed rather than silently using the legacy path.
            return self._fail_closed_unknown(action_type, payload, "audit-unavailable")
        return ActionRisk(
            action_type=action_type,
            risk_level=RiskLevel.MEDIUM,
            reason=_LEGACY_UNKNOWN_REASON,
            requires_approval=RiskLevel.MEDIUM >= snapshot_threshold,
            reversible=True,
            estimated_impact="Unknown — manual review recommended",
            domain="general",
            metadata={
                "payload_keys": list(payload.keys()),
                "unknown_action_policy": "audited_exception",
                "exception_reference": snapshot_reference,
            },
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
        self._custom_rules.insert(
            0,
            (pattern, risk_level, reason, requires_approval, reversible, estimated_impact, domain),
        )

    def set_org_threshold(self, threshold: RiskLevel) -> None:
        """Update the organization-wide risk threshold for approval requirements.

        A-FIX + F-HIGH-2/F-HIGH-3: the audited path for changing the threshold.
        Validates the CURRENT authority seal before re-sealing (so tampered
        state is never legitimized), and records the audit BEFORE committing
        (so an audit failure rolls back the change instead of persisting it).
        The new seal is derived only from the validated snapshot plus the
        requested threshold.
        """
        # F-HIGH-2: validate the current seal BEFORE any re-seal.
        sealed = object.__getattribute__(self, "_authority_signature")
        snapshot_policy = self.unknown_action_policy
        snapshot_reference = self.exception_reference
        snapshot_expires_at = self.exception_expires_at
        snapshot_threshold = self.org_risk_threshold
        live = _authority_signature(
            snapshot_policy,
            snapshot_reference,
            snapshot_expires_at,
            snapshot_threshold,
        )
        if not sealed or sealed != live:
            with suppress(Exception):
                self._record_audit("AUTHORITY_INTEGRITY_VIOLATION")
            raise ValueError(
                "authority-config-integrity: cannot change threshold over tampered state"
            )
        # F-HIGH-3: record the audit BEFORE committing; commit only after the
        # audit succeeds. On audit failure the exception propagates and the
        # threshold/seal are left unchanged (rollback).
        new_seal = _authority_signature(
            snapshot_policy,
            snapshot_reference,
            snapshot_expires_at,
            threshold,
        )
        self._record_audit(
            "AUTHORITY_THRESHOLD_UPDATED",
            threshold=getattr(threshold, "value", threshold),
        )
        object.__setattr__(self, "org_risk_threshold", threshold)
        object.__setattr__(self, "_authority_signature", new_seal)

    def _record_audit(self, event: str, **fields: object) -> None:
        """A-FIX: append an authority event to the audit log.

        Callers on the authority-granting path treat a failure here as
        fail-closed (see the legacy-path handling in assess()).
        """
        self._exception_audit.append({"event": event, "at": time.time(), **fields})

    def _fail_closed_unknown(
        self, action_type: str, payload: Dict, reason: str
    ) -> ActionRisk:
        """A-FIX: canonical fail-closed result for an unknown/untrusted action."""
        return ActionRisk(
            action_type=action_type,
            risk_level=RiskLevel.CRITICAL,
            reason=f"Unknown action type — fail-closed ({reason})",
            requires_approval=True,
            reversible=False,
            estimated_impact="Unclassified — manual review required",
            domain="general",
            metadata={
                "payload_keys": list(payload.keys()),
                "fail_closed_reason": reason,
            },
        )

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
                applies_to=[
                    "send_payment",
                    "wire_transfer",
                    "update_financial_*",
                    "create_invoice",
                ],
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

"""
compliance_monitor.py — Regulatory compliance checking for AI agent actions.

Provides compliance verification for:
- Attorney-client privilege (legal domain)
- GDPR data handling and data residency
- HIPAA (if medical data involved)
- SEC regulations (financial communications)
- Unauthorized practice of law (UPL) detection
- SOC2, ISO 27001, HIPAA compliance audits
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from governance.risk_types import (
    ComplianceReport,
    ComplianceResult,
    EthicsResult,
    RiskLevel,
    Violation,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Jurisdiction-to-GDPR-region mapping
# ---------------------------------------------------------------------------

GDPR_REGIONS = {
    "EU", "EEA", "UK", "DE", "FR", "ES", "IT", "NL", "BE", "SE",
    "PL", "AT", "DK", "FI", "NO", "IS", "LI",
}

# Actions that require attorney-client privilege protection
PRIVILEGED_ACTIONS = {
    "send_legal_advice", "share_case_strategy", "disclose_privileged_info",
    "forward_attorney_communication", "publish_legal_memo",
}

# Actions potentially constituting unauthorized practice of law
UPL_ACTIONS = {
    "give_legal_advice_without_supervision", "represent_client_in_court",
    "sign_legal_document_as_attorney", "file_legal_document",
}

# SEC-regulated communication actions
SEC_ACTIONS = {
    "publish_financial_forecast", "send_investor_communication",
    "disclose_material_information", "send_earnings_guidance",
}

# HIPAA-sensitive action patterns
HIPAA_PATTERNS = ["phi", "patient", "medical", "health_record", "prescription"]


class ComplianceMonitor:
    """
    Regulatory compliance checker for agent actions.

    Integrates with governance workflows to ensure all agent actions
    comply with applicable laws and regulations before execution.

    Example::

        monitor = ComplianceMonitor()
        result = monitor.check_action("send_email_to_client", domain="legal")
        if not result.compliant:
            for v in result.violations:
                print(f"Violation: {v}")
    """

    def __init__(self) -> None:
        self._violations: List[Violation] = []
        self._custom_rules: Dict[str, List[str]] = {}  # domain → restricted actions

    # ------------------------------------------------------------------
    # Primary compliance check
    # ------------------------------------------------------------------

    def check_action(
        self,
        action: str,
        domain: str = "general",
        payload: Optional[Dict[str, Any]] = None,
        jurisdiction: Optional[str] = None,
    ) -> ComplianceResult:
        """
        Check whether an action complies with applicable regulations.

        Args:
            action: The action type (e.g. 'send_email_to_client').
            domain: Domain context (legal, financial, medical, general).
            payload: Action payload for context-sensitive checks.
            jurisdiction: User/data jurisdiction (e.g. 'EU', 'US', 'UK').

        Returns:
            ComplianceResult indicating whether the action is compliant.
        """
        payload = payload or {}
        violations: List[str] = []
        warnings: List[str] = []
        recommendations: List[str] = []

        # Attorney-client privilege
        if action in PRIVILEGED_ACTIONS and domain == "legal":
            violations.append(
                f"Action '{action}' may breach attorney-client privilege. "
                "Requires attorney review before execution."
            )

        # GDPR data residency
        if jurisdiction and self._is_gdpr_jurisdiction(jurisdiction):
            if action in ("export_data", "send_data_to_external", "store_data"):
                dest = payload.get("destination_region", "")
                if dest and dest not in GDPR_REGIONS:
                    violations.append(
                        f"GDPR violation: data transfer to '{dest}' not permitted "
                        "without adequate safeguards (Art. 44-49 GDPR)."
                    )
                else:
                    warnings.append("GDPR: ensure data transfer agreements are in place.")

        # HIPAA
        if domain == "medical" or any(p in action.lower() for p in HIPAA_PATTERNS):
            if action not in ("read_data", "list_records", "get_status"):
                warnings.append(
                    "HIPAA: this action involves PHI/health data. "
                    "Ensure minimum necessary standard is applied (§164.502)."
                )
                if "encryption" not in payload.get("security_measures", []):
                    violations.append(
                        "HIPAA §164.312(a)(2)(iv): encryption required for PHI transmission."
                    )

        # SEC regulations
        if action in SEC_ACTIONS and domain == "financial":
            violations.append(
                f"SEC: action '{action}' constitutes regulated financial communication. "
                "Requires compliance officer review (Reg FD, Rule 10b-5)."
            )

        # Custom domain rules
        for blocked_action in self._custom_rules.get(domain, []):
            if action == blocked_action:
                violations.append(f"Custom rule violation: '{action}' is blocked in domain '{domain}'.")

        # General recommendations
        if not violations:
            recommendations.append("Action appears compliant. Log and proceed.")

        compliant = len(violations) == 0
        result = ComplianceResult(
            compliant=compliant,
            standard="MULTI",
            action=action,
            violations=violations,
            warnings=warnings,
            recommendations=recommendations,
        )

        if not compliant:
            for v in violations:
                self.flag_violation(action, v, severity="high" if domain in ("legal", "financial") else "medium")

        return result

    # ------------------------------------------------------------------
    # Violation management
    # ------------------------------------------------------------------

    def flag_violation(
        self,
        action: str,
        rule: str,
        severity: str = "medium",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Violation:
        """
        Record and alert on a compliance violation.

        Args:
            action: The action that triggered the violation.
            rule: The rule or regulation violated.
            severity: low, medium, high, critical.
            metadata: Additional context.

        Returns:
            The recorded Violation object.
        """
        violation = Violation(
            action=action,
            rule=rule,
            severity=severity,
            description=f"Compliance violation: {rule}",
            metadata=metadata or {},
        )
        self._violations.append(violation)
        logger.warning(
            "Compliance violation [%s]: action='%s', rule='%s'",
            severity.upper(), action, rule
        )
        return violation

    def get_violations(
        self,
        date_range: Optional[tuple] = None,
        severity: Optional[str] = None,
        resolved: Optional[bool] = None,
    ) -> List[Violation]:
        """
        Retrieve recorded violations with optional filters.

        Args:
            date_range: (start, end) tuple of datetimes.
            severity: Filter by severity level.
            resolved: Filter by resolution status.
        """
        results = list(self._violations)

        if date_range:
            start, end = date_range
            results = [
                v for v in results
                if start <= v.detected_at <= end
            ]
        if severity:
            results = [v for v in results if v.severity == severity]
        if resolved is not None:
            results = [v for v in results if v.resolved == resolved]

        return results

    def resolve_violation(self, violation_id: str, notes: str = "") -> bool:
        """Mark a violation as resolved."""
        for v in self._violations:
            if v.id == violation_id:
                v.resolved = True
                v.metadata["resolution_notes"] = notes
                v.metadata["resolved_at"] = datetime.now(timezone.utc).isoformat()
                return True
        return False

    # ------------------------------------------------------------------
    # Compliance audit reports
    # ------------------------------------------------------------------

    def audit_for_standard(
        self,
        standard: str,
        audit_data: Optional[Dict[str, Any]] = None,
    ) -> ComplianceReport:
        """
        Generate a compliance audit report for a specific standard.

        Supported standards: SOC2, ISO27001, HIPAA, GDPR, SOX.

        Args:
            standard: The compliance standard to audit against.
            audit_data: Optional supplementary audit data.

        Returns:
            ComplianceReport with score, findings, and recommendations.
        """
        standard = standard.upper()
        audit_data = audit_data or {}
        report = ComplianceReport(standard=standard)

        if standard == "SOC2":
            controls = self._soc2_controls(audit_data)
        elif standard == "ISO27001":
            controls = self._iso27001_controls(audit_data)
        elif standard == "HIPAA":
            controls = self._hipaa_controls(audit_data)
        elif standard == "GDPR":
            controls = self._gdpr_controls(audit_data)
        elif standard == "SOX":
            controls = self._sox_controls(audit_data)
        else:
            controls = {"unsupported": (False, f"Standard '{standard}' not supported")}

        passed = sum(1 for ok, _ in controls.values() if ok)
        total = len(controls)
        failed_controls = [(k, msg) for k, (ok, msg) in controls.items() if not ok]

        report.controls_checked = total
        report.controls_passed = passed
        report.score = (passed / total * 100) if total else 0
        report.compliant = len(failed_controls) == 0
        report.violations = [
            Violation(action="audit", rule=ctrl, description=msg, severity="high")
            for ctrl, msg in failed_controls
        ]
        report.recommendations = [
            f"Address control '{ctrl}': {msg}" for ctrl, msg in failed_controls
        ]
        report.summary = (
            f"{standard} audit: {passed}/{total} controls passed "
            f"(score: {report.score:.1f}%)"
        )

        return report

    # ------------------------------------------------------------------
    # Ethical and legal checks
    # ------------------------------------------------------------------

    def legal_ethical_check(
        self,
        action: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> EthicsResult:
        """
        Check for unauthorized practice of law (UPL) and ethical issues.

        Args:
            action: The action to evaluate.
            payload: Optional payload for context.

        Returns:
            EthicsResult with flags and recommendations.
        """
        payload = payload or {}
        flags: List[str] = []
        unauthorized_practice = False
        bias_detected = False
        recommendations: List[str] = []

        # UPL detection
        if action in UPL_ACTIONS:
            unauthorized_practice = True
            flags.append(
                f"UNAUTHORIZED PRACTICE OF LAW: action '{action}' constitutes "
                "legal representation without attorney supervision."
            )
            recommendations.append("Escalate to licensed attorney before proceeding.")

        # Supervised AI legal advice
        if action in ("draft_legal_advice", "generate_legal_opinion"):
            flags.append(
                "AI-generated legal advice must be reviewed by a licensed attorney "
                "before delivery to clients."
            )
            recommendations.append("Route output through attorney review workflow.")

        # Bias detection placeholder
        if payload.get("demographic_data") and action in ("make_decision", "score_applicant"):
            bias_detected = True
            flags.append(
                "Potential algorithmic bias: decision involves demographic data. "
                "Apply fairness audit before execution."
            )

        # Confidentiality
        if payload.get("confidential") and action in ("publish_document", "share_with_third_party"):
            flags.append("Confidentiality breach risk: document marked confidential.")
            recommendations.append("Verify disclosure authorization before sharing.")

        return EthicsResult(
            passes=len(flags) == 0,
            flags=flags,
            unauthorized_practice=unauthorized_practice,
            bias_detected=bias_detected,
            recommendations=recommendations,
        )

    def data_residency_check(
        self,
        data: Dict[str, Any],
        user_jurisdiction: str,
    ) -> bool:
        """
        Verify that data handling complies with data residency requirements.

        Returns True if compliant (data stays in correct region).
        """
        if not self._is_gdpr_jurisdiction(user_jurisdiction):
            return True  # No residency restriction outside GDPR regions

        processing_region = data.get("processing_region", "")
        storage_region = data.get("storage_region", "")

        if processing_region and processing_region not in GDPR_REGIONS:
            logger.warning(
                "GDPR data residency: processing in '%s' not permitted for jurisdiction '%s'",
                processing_region, user_jurisdiction
            )
            return False

        if storage_region and storage_region not in GDPR_REGIONS:
            logger.warning(
                "GDPR data residency: storage in '%s' not permitted for jurisdiction '%s'",
                storage_region, user_jurisdiction
            )
            return False

        return True

    # ------------------------------------------------------------------
    # Custom rules
    # ------------------------------------------------------------------

    def add_domain_restriction(self, domain: str, action: str) -> None:
        """Block a specific action in a specific domain."""
        self._custom_rules.setdefault(domain, []).append(action)

    # ------------------------------------------------------------------
    # Private: control checklists
    # ------------------------------------------------------------------

    def _is_gdpr_jurisdiction(self, jurisdiction: str) -> bool:
        return jurisdiction.upper() in GDPR_REGIONS

    def _soc2_controls(self, data: Dict) -> Dict[str, tuple]:
        return {
            "CC6.1 — Logical Access": (True, "Access controls implemented"),
            "CC6.2 — Authentication": (True, "MFA enabled"),
            "CC7.1 — Threat Detection": (True, "Anomaly detection active"),
            "CC7.2 — Incident Response": (data.get("incident_response_plan", False), "Incident response plan required"),
            "CC9.2 — Vendor Risk": (data.get("vendor_assessments", False), "Vendor risk assessments required"),
            "A1.1 — Availability": (True, "System availability monitored"),
        }

    def _iso27001_controls(self, data: Dict) -> Dict[str, tuple]:
        return {
            "A.9 — Access Control": (True, "Access controls in place"),
            "A.10 — Cryptography": (data.get("encryption_at_rest", False), "Encryption at rest required"),
            "A.12 — Operations Security": (True, "Audit logging active"),
            "A.16 — Incident Management": (data.get("incident_management", False), "Incident management required"),
            "A.18 — Compliance": (True, "Compliance monitoring active"),
        }

    def _hipaa_controls(self, data: Dict) -> Dict[str, tuple]:
        return {
            "§164.308 — Admin Safeguards": (True, "Security officer designated"),
            "§164.310 — Physical Safeguards": (data.get("physical_controls", False), "Physical controls required"),
            "§164.312 — Technical Safeguards": (data.get("encryption", False), "Technical encryption required"),
            "§164.314 — Org Requirements": (True, "BAA agreements in place"),
            "§164.316 — Policies": (data.get("security_policies", False), "Written security policies required"),
        }

    def _gdpr_controls(self, data: Dict) -> Dict[str, tuple]:
        return {
            "Art. 5 — Data Principles": (True, "Data minimization applied"),
            "Art. 13 — Transparency": (data.get("privacy_notice", False), "Privacy notice required"),
            "Art. 17 — Right to Erasure": (True, "Deletion workflows in place"),
            "Art. 25 — Privacy by Design": (True, "Privacy-by-design implemented"),
            "Art. 30 — Records of Processing": (data.get("ropa", False), "ROPA (Record of Processing) required"),
            "Art. 32 — Security": (True, "Encryption and audit logging active"),
            "Art. 37 — DPO": (data.get("dpo_appointed", False), "Data Protection Officer required"),
        }

    def _sox_controls(self, data: Dict) -> Dict[str, tuple]:
        return {
            "§302 — CEO/CFO Certification": (data.get("executive_certification", False), "Executive certification required"),
            "§404 — Internal Controls": (data.get("internal_controls", False), "Internal control assessment required"),
            "§409 — Real-time Disclosure": (True, "Material event logging active"),
            "§802 — Record Retention": (True, "7-year audit log retention active"),
        }

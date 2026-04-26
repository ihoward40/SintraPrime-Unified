"""
compliance_checker.py — Automated AI Compliance Checker for SintraPrime-Unified
Checks operations against applicable laws and generates structured compliance findings.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import re

from ai_compliance.ai_law_db import (
    AILaw,
    ALL_LAWS,
    ComplianceArea,
    Jurisdiction,
    RiskTier,
    get_applicable_laws,
    get_laws_by_area,
)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class CheckStatus(str, Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class ComplianceCheck:
    """Result of a single compliance check against a specific law."""
    check_id: str
    law: AILaw
    area: ComplianceArea
    status: CheckStatus
    findings: List[str]
    remediation: List[str]
    severity: Severity
    timestamp: datetime = field(default_factory=datetime.utcnow)
    evidence: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_passing(self) -> bool:
        return self.status in (CheckStatus.COMPLIANT, CheckStatus.NOT_APPLICABLE)

    @property
    def requires_action(self) -> bool:
        return self.status in (CheckStatus.NON_COMPLIANT, CheckStatus.NEEDS_REVIEW)


@dataclass
class OperationContext:
    """
    Describes a SintraPrime operation to be checked for compliance.
    """
    operation_id: str
    operation_type: str          # e.g., "legal_advice", "document_drafting", "chat"
    description: str
    jurisdictions: List[Jurisdiction]
    risk_tier: RiskTier
    involves_legal_advice: bool = False
    involves_personal_data: bool = False
    involves_financial_advice: bool = False
    involves_employment_decision: bool = False
    involves_healthcare: bool = False
    ai_identifies_as_ai: bool = True
    provides_explanation: bool = True
    allows_human_review: bool = True
    data_fields_collected: List[str] = field(default_factory=list)
    output_text: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceSummary:
    """Aggregated results of all compliance checks for an operation."""
    operation_id: str
    operation_context: OperationContext
    checks: List[ComplianceCheck]
    overall_status: CheckStatus
    risk_score: int                  # 0–100, higher = more risk
    generated_at: datetime = field(default_factory=datetime.utcnow)
    applicable_laws: List[AILaw] = field(default_factory=list)

    @property
    def compliant_count(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.COMPLIANT)

    @property
    def non_compliant_count(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.NON_COMPLIANT)

    @property
    def needs_review_count(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.NEEDS_REVIEW)

    @property
    def critical_findings(self) -> List[ComplianceCheck]:
        return [c for c in self.checks if c.severity == Severity.CRITICAL]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "overall_status": self.overall_status.value,
            "risk_score": self.risk_score,
            "generated_at": self.generated_at.isoformat(),
            "compliant": self.compliant_count,
            "non_compliant": self.non_compliant_count,
            "needs_review": self.needs_review_count,
            "checks": [
                {
                    "check_id": c.check_id,
                    "law": c.law.short_name,
                    "area": c.area.value,
                    "status": c.status.value,
                    "severity": c.severity.value,
                    "findings": c.findings,
                    "remediation": c.remediation,
                }
                for c in self.checks
            ],
        }


# ---------------------------------------------------------------------------
# Individual Check Implementations
# ---------------------------------------------------------------------------

class TransparencyChecker:
    """Verify AI identifies itself as AI (EU AI Act, FTC, ABA)."""

    @staticmethod
    def check(ctx: OperationContext) -> Tuple[CheckStatus, List[str], List[str], Severity]:
        findings: List[str] = []
        remediation: List[str] = []

        if not ctx.ai_identifies_as_ai:
            findings.append(
                "AI system does not identify itself as an AI. This violates transparency "
                "obligations under EU AI Act Article 52, FTC guidelines, and ABA Opinion 512."
            )
            remediation.append(
                "Ensure all user-facing communications include a clear AI disclosure statement "
                "at the start of the interaction (e.g., 'I am SintraPrime, an AI legal assistant')."
            )
            remediation.append(
                "Never impersonate a human attorney or claim to be a licensed legal professional."
            )
            return CheckStatus.NON_COMPLIANT, findings, remediation, Severity.CRITICAL

        if ctx.involves_legal_advice and not ctx.ai_identifies_as_ai:
            findings.append(
                "AI-generated legal advice provided without clear AI disclosure, "
                "violating ABA competence and communication rules."
            )
            remediation.append(
                "Add explicit disclosure for all legal-advice interactions: "
                "'This response was generated by an AI and is not legal advice from a licensed attorney.'"
            )
            return CheckStatus.NON_COMPLIANT, findings, remediation, Severity.CRITICAL

        findings.append("AI correctly identifies itself as an AI system.")
        return CheckStatus.COMPLIANT, findings, remediation, Severity.INFO


class ExplainabilityChecker:
    """Verify AI decisions can be explained (EU AI Act, CO SB 205, WA)."""

    @staticmethod
    def check(ctx: OperationContext) -> Tuple[CheckStatus, List[str], List[str], Severity]:
        findings: List[str] = []
        remediation: List[str] = []

        high_stakes = (
            ctx.involves_legal_advice
            or ctx.involves_financial_advice
            or ctx.involves_employment_decision
            or ctx.involves_healthcare
        )

        if high_stakes and not ctx.provides_explanation:
            findings.append(
                "High-stakes AI decision provided without explanation. "
                "CO SB 205, WA AI Act, and TX HB 149 require explanations for consequential decisions."
            )
            remediation.append(
                "Implement explanation generation for all high-stakes decisions: "
                "include key factors, reasoning steps, and confidence indicators."
            )
            remediation.append(
                "Document the explanation capability in the system's technical documentation."
            )
            return CheckStatus.NON_COMPLIANT, findings, remediation, Severity.HIGH

        if high_stakes and ctx.provides_explanation:
            findings.append(
                "AI provides explanations for high-stakes decisions as required by applicable laws."
            )
            return CheckStatus.COMPLIANT, findings, remediation, Severity.INFO

        if not high_stakes and ctx.provides_explanation:
            findings.append("Explanation capability present (not required for this operation type).")
            return CheckStatus.COMPLIANT, findings, remediation, Severity.INFO

        findings.append(
            "Operation does not involve high-stakes decisions; "
            "explainability requirements are not triggered."
        )
        return CheckStatus.NOT_APPLICABLE, findings, remediation, Severity.INFO


class BiasDetectionChecker:
    """Check that bias screening processes are in place (NY LL144, CO SB 205, TX HB 149)."""

    BIAS_INDICATOR_PATTERNS = [
        r"\b(always|never)\s+(blacks?|whites?|males?|females?|women|men|latinos?|asians?)\b",
        r"\b(inferior|superior)\s+(race|gender|sex|ethnicity)\b",
        r"\b(typical|usually)\s+(for\s+their\s+(kind|type|group))\b",
    ]

    @classmethod
    def check(cls, ctx: OperationContext) -> Tuple[CheckStatus, List[str], List[str], Severity]:
        findings: List[str] = []
        remediation: List[str] = []

        # Check output text for obvious bias indicators
        if ctx.output_text:
            detected = []
            for pattern in cls.BIAS_INDICATOR_PATTERNS:
                if re.search(pattern, ctx.output_text, re.IGNORECASE):
                    detected.append(pattern)

            if detected:
                findings.append(
                    f"Potential bias language detected in output ({len(detected)} pattern(s) matched). "
                    "Review and remediate before delivery."
                )
                remediation.append(
                    "Run output through bias screening pipeline before returning to user."
                )
                remediation.append(
                    "If bias confirmed, regenerate response with explicit fairness constraints."
                )
                return CheckStatus.NON_COMPLIANT, findings, remediation, Severity.CRITICAL

        if ctx.involves_employment_decision:
            findings.append(
                "Employment decision context detected. Annual bias audit required under NYC LL144 "
                "and impact assessment required under CO SB 205 / TX HB 149."
            )
            remediation.append(
                "Ensure employment AI system has current bias audit report (within 12 months). "
                "Publish audit summary on public-facing website."
            )
            return CheckStatus.NEEDS_REVIEW, findings, remediation, Severity.HIGH

        findings.append("No bias indicators detected in output; bias screening processes active.")
        return CheckStatus.COMPLIANT, findings, remediation, Severity.INFO


class DataMinimizationChecker:
    """Verify only necessary data is collected (GDPR, VA CDPA, CA CCPA)."""

    SENSITIVE_FIELD_PATTERNS = {
        "ssn": Severity.CRITICAL,
        "social_security": Severity.CRITICAL,
        "tax_id": Severity.HIGH,
        "credit_card": Severity.CRITICAL,
        "bank_account": Severity.HIGH,
        "medical_record": Severity.HIGH,
        "health_data": Severity.HIGH,
        "biometric": Severity.HIGH,
        "password": Severity.CRITICAL,
        "genetic": Severity.HIGH,
        "immigration_status": Severity.HIGH,
        "precise_location": Severity.MEDIUM,
        "browsing_history": Severity.MEDIUM,
    }

    @classmethod
    def check(cls, ctx: OperationContext) -> Tuple[CheckStatus, List[str], List[str], Severity]:
        findings: List[str] = []
        remediation: List[str] = []
        max_severity = Severity.INFO

        unnecessary_fields: List[str] = []
        for field_name in ctx.data_fields_collected:
            field_lower = field_name.lower().replace(" ", "_").replace("-", "_")
            for sensitive, severity in cls.SENSITIVE_FIELD_PATTERNS.items():
                if sensitive in field_lower:
                    unnecessary_fields.append(field_name)
                    if list(Severity).index(severity) < list(Severity).index(max_severity):
                        max_severity = severity
                    break

        if unnecessary_fields and not (ctx.involves_healthcare or ctx.involves_financial_advice):
            findings.append(
                f"Potentially unnecessary sensitive data fields collected: {unnecessary_fields}. "
                "Data minimization principles require collecting only data adequate for the stated purpose."
            )
            remediation.append(
                "Review data collection scope and eliminate fields not strictly required for the operation."
            )
            remediation.append(
                "Document legitimate purpose for each sensitive data field in privacy policy."
            )
            return CheckStatus.NEEDS_REVIEW, findings, remediation, max_severity

        if not ctx.data_fields_collected:
            findings.append("No personal data fields collected in this operation.")
            return CheckStatus.COMPLIANT, findings, remediation, Severity.INFO

        findings.append(
            f"Data collection scope appears proportionate. Fields: {ctx.data_fields_collected}"
        )
        return CheckStatus.COMPLIANT, findings, remediation, Severity.INFO


class HumanReviewChecker:
    """Verify right to human review is available (EU AI Act, TX HB 149, WA, CO SB 205)."""

    @staticmethod
    def check(ctx: OperationContext) -> Tuple[CheckStatus, List[str], List[str], Severity]:
        findings: List[str] = []
        remediation: List[str] = []

        high_stakes = (
            ctx.involves_legal_advice
            or ctx.involves_financial_advice
            or ctx.involves_employment_decision
            or ctx.involves_healthcare
            or ctx.risk_tier in (RiskTier.HIGH, RiskTier.UNACCEPTABLE)
        )

        if high_stakes and not ctx.allows_human_review:
            findings.append(
                "High-stakes AI operation does not provide right to human review. "
                "TX HB 149, CO SB 205, WA AI Act, and EU AI Act require human review option "
                "for consequential decisions."
            )
            remediation.append(
                "Implement a 'Request Human Review' feature allowing users to escalate "
                "AI decisions to a qualified human professional."
            )
            remediation.append(
                "Establish SLA for human review responses (recommended: within 2 business days)."
            )
            remediation.append(
                "Document human review process in privacy notice and terms of service."
            )
            return CheckStatus.NON_COMPLIANT, findings, remediation, Severity.HIGH

        if high_stakes and ctx.allows_human_review:
            findings.append(
                "Right to human review is available for high-stakes operations — compliant with "
                "TX HB 149, CO SB 205, WA AI Act, and EU AI Act requirements."
            )
            return CheckStatus.COMPLIANT, findings, remediation, Severity.INFO

        findings.append("Human review not required for this operation type.")
        return CheckStatus.NOT_APPLICABLE, findings, remediation, Severity.INFO


class UPLChecker:
    """Check for unauthorized practice of law risks (ABA, state bar rules)."""

    UPL_RISK_PHRASES = [
        r"\byou\s+(should|must|need\s+to)\s+(file|sue|sign|execute|plead)\b",
        r"\bI\s+advise\s+you\s+to\b",
        r"\bmy\s+(legal\s+)?opinion\s+is\b",
        r"\bas\s+your\s+(lawyer|attorney|counsel)\b",
        r"\bI\s+represent\s+you\b",
        r"\bour\s+(legal\s+)?team\s+will\b",
        r"\bguarantee[sd]?\s+(outcome|result|win|success)\b",
    ]

    @classmethod
    def check(cls, ctx: OperationContext) -> Tuple[CheckStatus, List[str], List[str], Severity]:
        findings: List[str] = []
        remediation: List[str] = []

        if not ctx.involves_legal_advice:
            findings.append("Operation does not involve legal advice; UPL check not triggered.")
            return CheckStatus.NOT_APPLICABLE, findings, remediation, Severity.INFO

        if ctx.output_text:
            detected_phrases: List[str] = []
            for pattern in cls.UPL_RISK_PHRASES:
                matches = re.findall(pattern, ctx.output_text, re.IGNORECASE)
                if matches:
                    detected_phrases.extend(matches)

            if detected_phrases:
                findings.append(
                    f"Potential UPL-risk language detected in output: {detected_phrases[:3]}. "
                    "AI must not create attorney-client relationship or practice law."
                )
                remediation.append(
                    "Replace directive legal language with informational framing: "
                    "'A common approach is...' rather than 'You should...'"
                )
                remediation.append(
                    "Add disclaimer: 'This is general legal information, not legal advice. "
                    "Consult a licensed attorney for advice specific to your situation.'"
                )
                remediation.append(
                    "Review output for any representations of attorney-client relationship."
                )
                return CheckStatus.NON_COMPLIANT, findings, remediation, Severity.HIGH

        findings.append(
            "Legal advice operation complies with UPL boundaries — "
            "output provides legal information without practicing law."
        )
        return CheckStatus.COMPLIANT, findings, remediation, Severity.INFO


class ConsentChecker:
    """Verify appropriate consent mechanisms are in place (IL, FL, VA CDPA)."""

    @staticmethod
    def check(ctx: OperationContext) -> Tuple[CheckStatus, List[str], List[str], Severity]:
        findings: List[str] = []
        remediation: List[str] = []

        requires_explicit_consent = (
            ctx.involves_personal_data
            and (ctx.involves_employment_decision or ctx.involves_healthcare)
        )

        consent_obtained = ctx.metadata.get("consent_obtained", None)

        if requires_explicit_consent and consent_obtained is False:
            findings.append(
                "Explicit consent not obtained for processing personal data in high-risk context. "
                "IL AI Video Interview Act, VA CDPA, and CO SB 205 require explicit consent."
            )
            remediation.append(
                "Implement consent collection workflow before processing sensitive personal data."
            )
            remediation.append(
                "Store consent records with timestamp and version of consent language shown."
            )
            return CheckStatus.NON_COMPLIANT, findings, remediation, Severity.HIGH

        if requires_explicit_consent and consent_obtained is None:
            findings.append(
                "Consent status unknown for high-risk personal data processing context."
            )
            remediation.append(
                "Verify consent collection and record-keeping processes are operational."
            )
            return CheckStatus.NEEDS_REVIEW, findings, remediation, Severity.MEDIUM

        if consent_obtained is True or not requires_explicit_consent:
            findings.append("Consent requirements satisfied for this operation.")
            return CheckStatus.COMPLIANT, findings, remediation, Severity.INFO

        findings.append("Consent requirements not triggered for this operation type.")
        return CheckStatus.NOT_APPLICABLE, findings, remediation, Severity.INFO


class DocumentationChecker:
    """Verify AI system documentation is maintained (EU AI Act, NIST RMF, TX HB 149)."""

    REQUIRED_DOCS = [
        "system_purpose",
        "training_data_sources",
        "limitations",
        "bias_testing_results",
        "performance_metrics",
        "incident_response_plan",
        "human_oversight_procedures",
    ]

    @classmethod
    def check(cls, ctx: OperationContext) -> Tuple[CheckStatus, List[str], List[str], Severity]:
        findings: List[str] = []
        remediation: List[str] = []

        available_docs = ctx.metadata.get("documentation", [])

        if not available_docs:
            findings.append(
                "No documentation metadata provided. Cannot verify compliance with documentation "
                "requirements under EU AI Act Article 11, NIST AI RMF GOVERN, and TX HB 149."
            )
            remediation.append(
                "Maintain technical documentation covering: system purpose, training data sources, "
                "performance metrics, limitations, and incident response procedures."
            )
            return CheckStatus.NEEDS_REVIEW, findings, remediation, Severity.MEDIUM

        missing = [doc for doc in cls.REQUIRED_DOCS if doc not in available_docs]
        if missing:
            findings.append(
                f"Missing documentation components: {missing}. "
                "Complete documentation is required for high-risk AI compliance."
            )
            remediation.extend([
                f"Create/update documentation section: {doc}" for doc in missing
            ])
            return CheckStatus.NEEDS_REVIEW, findings, remediation, Severity.MEDIUM

        findings.append(
            f"Documentation is comprehensive and covers all required areas: {available_docs[:5]}..."
        )
        return CheckStatus.COMPLIANT, findings, remediation, Severity.INFO


# ---------------------------------------------------------------------------
# Main Compliance Checker
# ---------------------------------------------------------------------------

class ComplianceChecker:
    """
    Orchestrates compliance checks across all applicable laws for a given operation.
    """

    def __init__(self, laws: Optional[List[AILaw]] = None):
        self._laws = laws or ALL_LAWS
        self._checkers = {
            ComplianceArea.TRANSPARENCY: TransparencyChecker(),
            ComplianceArea.EXPLAINABILITY: ExplainabilityChecker(),
            ComplianceArea.BIAS_FAIRNESS: BiasDetectionChecker(),
            ComplianceArea.DATA_MINIMIZATION: DataMinimizationChecker(),
            ComplianceArea.HUMAN_OVERSIGHT: HumanReviewChecker(),
            ComplianceArea.UPL: UPLChecker(),
            ComplianceArea.CONSENT: ConsentChecker(),
            ComplianceArea.DOCUMENTATION: DocumentationChecker(),
        }

    def run_full_check(self, ctx: OperationContext) -> ComplianceSummary:
        """
        Run all applicable compliance checks for an operation context.
        Returns a ComplianceSummary with all findings.
        """
        applicable_laws = get_applicable_laws(
            jurisdictions=ctx.jurisdictions,
            risk_tier=ctx.risk_tier,
            legal_profession=ctx.involves_legal_advice,
        )

        checks: List[ComplianceCheck] = []
        check_counter = 0

        for area, checker in self._checkers.items():
            relevant_laws = [l for l in applicable_laws if l.matches_area(area)]
            if not relevant_laws:
                continue

            # Run the area-specific check once, associate with all relevant laws
            status, findings, remediation, severity = checker.check(ctx)

            for law in relevant_laws:
                check_counter += 1
                check_id = f"{ctx.operation_id}-{area.value}-{law.law_id}-{check_counter:04d}"
                checks.append(ComplianceCheck(
                    check_id=check_id,
                    law=law,
                    area=area,
                    status=status,
                    findings=list(findings),
                    remediation=list(remediation),
                    severity=severity,
                    evidence={"operation_type": ctx.operation_type},
                ))

        overall_status = self._compute_overall_status(checks)
        risk_score = self._compute_risk_score(checks, ctx)

        return ComplianceSummary(
            operation_id=ctx.operation_id,
            operation_context=ctx,
            checks=checks,
            overall_status=overall_status,
            risk_score=risk_score,
            applicable_laws=applicable_laws,
        )

    def check_single_area(
        self,
        ctx: OperationContext,
        area: ComplianceArea,
    ) -> List[ComplianceCheck]:
        """Run compliance check for a single area only."""
        checker = self._checkers.get(area)
        if not checker:
            return []

        status, findings, remediation, severity = checker.check(ctx)
        applicable_laws = get_applicable_laws(
            jurisdictions=ctx.jurisdictions,
            risk_tier=ctx.risk_tier,
        )
        relevant_laws = [l for l in applicable_laws if l.matches_area(area)]

        return [
            ComplianceCheck(
                check_id=f"{ctx.operation_id}-{area.value}-{law.law_id}",
                law=law,
                area=area,
                status=status,
                findings=list(findings),
                remediation=list(remediation),
                severity=severity,
            )
            for law in relevant_laws
        ]

    @staticmethod
    def _compute_overall_status(checks: List[ComplianceCheck]) -> CheckStatus:
        if not checks:
            return CheckStatus.UNKNOWN
        statuses = {c.status for c in checks}
        if CheckStatus.NON_COMPLIANT in statuses:
            return CheckStatus.NON_COMPLIANT
        if CheckStatus.NEEDS_REVIEW in statuses:
            return CheckStatus.NEEDS_REVIEW
        if all(c.status in (CheckStatus.COMPLIANT, CheckStatus.NOT_APPLICABLE) for c in checks):
            return CheckStatus.COMPLIANT
        return CheckStatus.UNKNOWN

    @staticmethod
    def _compute_risk_score(checks: List[ComplianceCheck], ctx: OperationContext) -> int:
        """
        Compute a 0–100 risk score. Higher = more risk.
        """
        if not checks:
            return 0

        score = 0
        severity_weights = {
            Severity.CRITICAL: 25,
            Severity.HIGH: 15,
            Severity.MEDIUM: 8,
            Severity.LOW: 3,
            Severity.INFO: 0,
        }

        for check in checks:
            if check.status == CheckStatus.NON_COMPLIANT:
                score += severity_weights.get(check.severity, 0)
            elif check.status == CheckStatus.NEEDS_REVIEW:
                score += severity_weights.get(check.severity, 0) // 2

        # Context multipliers
        if ctx.risk_tier == RiskTier.HIGH:
            score = int(score * 1.2)
        if ctx.involves_legal_advice:
            score += 5
        if ctx.involves_healthcare:
            score += 5
        if not ctx.ai_identifies_as_ai:
            score += 20

        return min(score, 100)

    def get_remediation_roadmap(self, summary: ComplianceSummary) -> List[Dict[str, Any]]:
        """
        Generate a prioritized remediation roadmap from a compliance summary.
        """
        severity_order = [
            Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO
        ]
        roadmap: List[Dict[str, Any]] = []

        for severity in severity_order:
            relevant = [c for c in summary.checks if c.severity == severity and c.requires_action]
            for check in relevant:
                for i, step in enumerate(check.remediation, 1):
                    roadmap.append({
                        "priority": severity.value,
                        "law": check.law.short_name,
                        "area": check.area.value,
                        "step": i,
                        "action": step,
                        "deadline": "Immediate" if severity == Severity.CRITICAL else "30 days",
                    })

        return roadmap


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------

def quick_check(
    operation_type: str,
    jurisdictions: List[Jurisdiction],
    risk_tier: RiskTier = RiskTier.HIGH,
    **kwargs: Any,
) -> ComplianceSummary:
    """
    Quick compliance check with minimal setup.

    Args:
        operation_type: Type of operation being performed
        jurisdictions: List of relevant jurisdictions
        risk_tier: Risk tier of the AI system
        **kwargs: Additional OperationContext fields

    Returns:
        ComplianceSummary
    """
    import uuid
    ctx = OperationContext(
        operation_id=str(uuid.uuid4())[:8],
        operation_type=operation_type,
        description=kwargs.get("description", operation_type),
        jurisdictions=jurisdictions,
        risk_tier=risk_tier,
        involves_legal_advice=kwargs.get("involves_legal_advice", False),
        involves_personal_data=kwargs.get("involves_personal_data", False),
        involves_financial_advice=kwargs.get("involves_financial_advice", False),
        involves_employment_decision=kwargs.get("involves_employment_decision", False),
        involves_healthcare=kwargs.get("involves_healthcare", False),
        ai_identifies_as_ai=kwargs.get("ai_identifies_as_ai", True),
        provides_explanation=kwargs.get("provides_explanation", True),
        allows_human_review=kwargs.get("allows_human_review", True),
        data_fields_collected=kwargs.get("data_fields_collected", []),
        output_text=kwargs.get("output_text", None),
        metadata=kwargs.get("metadata", {}),
    )
    checker = ComplianceChecker()
    return checker.run_full_check(ctx)


if __name__ == "__main__":
    summary = quick_check(
        operation_type="legal_advice",
        jurisdictions=[Jurisdiction.US_CA, Jurisdiction.EU],
        risk_tier=RiskTier.HIGH,
        involves_legal_advice=True,
        involves_personal_data=True,
        ai_identifies_as_ai=True,
        provides_explanation=True,
        allows_human_review=True,
    )
    print(f"Overall Status: {summary.overall_status.value}")
    print(f"Risk Score: {summary.risk_score}/100")
    print(f"Checks run: {len(summary.checks)}")
    print(f"Non-compliant: {summary.non_compliant_count}")

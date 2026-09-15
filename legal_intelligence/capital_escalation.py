"""SP-CAPITAL-ESCALATION-001 — controlled routing of capital-risk signals.

Transforms policy/early-warning/stress/collateral/servicing signals into governed
response lanes. Routing is operational only and does not itself create a legal default,
accelerate debt, authorize enforcement, or waive Principal approval requirements.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass(frozen=True)
class EscalationSignal:
    signal_id: str
    source_module: str
    subject_id: str
    severity: str
    signal_type: str
    policy_id: str
    policy_version: str
    facts: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EscalationDecision:
    module_id: str
    signal_id: str
    routes: list[str] = field(default_factory=list)
    controls: list[str] = field(default_factory=list)
    funding_status: str = "NO_AUTOMATIC_FREEZE"
    principal_review_required: bool = False
    workout_review_required: bool = False
    beneficial_suggestions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class CapitalEscalationEngine:
    MODULE_ID = "SP-CAPITAL-ESCALATION-001"

    SERVICING_TYPES = {
        "DELINQUENCY_EMERGING",
        "COLLECTIONS_DECLINING",
        "DSCR_PRESSURE",
        "REPEATED_COVENANT_WAIVER",
    }
    COLLATERAL_TYPES = {
        "COLLATERAL_COVERAGE_EROSION",
        "VALUATION_STALE",
        "INSURANCE_LAPSE",
        "PERFECTION_EXPIRING",
        "TITLE_OR_OWNERSHIP_EXCEPTION",
    }
    CREDIT_TYPES = {
        "CONCENTRATION_DRIFT",
        "LIQUIDITY_COMPRESSION",
        "RESERVE_BUFFER_COMPRESSION",
        "BORROWING_BASE_DETERIORATION",
        "STRESS_LIMIT_PRESSURE",
    }
    WORKOUT_TYPES = {
        "DEFAULT_RISK_HIGH",
        "DELINQUENCY_SEVERE",
        "NEGATIVE_EXPECTED_HEADROOM",
        "COLLATERAL_SHORTFALL_MATERIAL",
    }
    FREEZE_TYPES = {
        "RESERVE_BREACH",
        "LIQUIDITY_BREACH",
        "CONCENTRATION_BREACH",
        "PERFECTION_FAILURE",
        "INSURANCE_LAPSE",
        "CONTROL_FAILURE",
        "POLICY_EXCEPTION_RECURRING",
    }

    def route(self, signal: EscalationSignal) -> EscalationDecision:
        severity = signal.severity.strip().upper()
        signal_type = signal.signal_type.strip().upper()
        routes: list[str] = []
        controls: list[str] = []
        principal = False
        workout = False
        funding_status = "NO_AUTOMATIC_FREEZE"

        if signal_type in self.SERVICING_TYPES:
            routes.append("SERVICING_REVIEW")
        if signal_type in self.COLLATERAL_TYPES:
            routes.append("COLLATERAL_REFRESH")
        if signal_type in self.CREDIT_TYPES:
            routes.append("CREDIT_COMMITTEE_REVIEW")
        if signal_type in self.WORKOUT_TYPES:
            routes.extend(["SERVICING_REVIEW", "WORKOUT_RECOVERY_ANALYSIS"])
            workout = True
        if signal_type in self.FREEZE_TYPES:
            funding_status = "FREEZE_NEW_ADVANCES_PENDING_REVIEW"
            routes.append("FUNDING_FREEZE_CONTROL")

        if severity in {"HIGH", "CRITICAL"}:
            principal = True
            routes.append("PRINCIPAL_REVIEW")
        if severity == "CRITICAL":
            routes.append("AUDIT_EXCEPTION")
            funding_status = "FREEZE_NEW_ADVANCES_PENDING_REVIEW"

        if not signal.policy_id or not signal.policy_version:
            controls.append("POLICY_VERSION_TRACE_REQUIRED")
        if not signal.evidence_refs:
            controls.append("EVIDENCE_REFERENCE_REQUIRED_BEFORE_CLOSURE")
        if signal.source_module == "":
            controls.append("SOURCE_MODULE_REQUIRED")

        routes = list(dict.fromkeys(routes or ["MONITOR_ONLY"]))
        controls.extend([
            "Internal escalation does not itself establish contractual or legal default.",
            "No acceleration, repossession, collection notice, disposition, or other enforcement action without separate contract/current-law review and required approval.",
            "Record routing outcome, owner, due date, and closure evidence in the decision journal.",
        ])

        suggestions = [
            "Assign service-level deadlines by severity so WATCH/HIGH/CRITICAL signals cannot age without ownership.",
            "Escalate unresolved HIGH or CRITICAL signals automatically one governance level after the policy-defined cure period.",
            "Require an explicit documented release before removing a funding freeze.",
            "Feed resolved signals back into underwriting and policy-change analysis to improve future thresholds.",
        ]
        return EscalationDecision(
            module_id=self.MODULE_ID,
            signal_id=signal.signal_id,
            routes=routes,
            controls=list(dict.fromkeys(controls)),
            funding_status=funding_status,
            principal_review_required=principal,
            workout_review_required=workout,
            beneficial_suggestions=suggestions,
        )

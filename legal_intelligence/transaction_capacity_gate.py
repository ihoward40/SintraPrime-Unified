"""SP-TRANSACTION-CAPACITY-001 — mandatory legal generation gate.

This module classifies the real transaction, legal capacity, obligation, evidence,
and theory support before SintraPrime may generate or execute a high-stakes legal
artifact.  It is intentionally fail-closed: missing transaction context or reliance on
unsupported/contradicted theories blocks generation before Principal approval.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TheoryClassification(str, Enum):
    PROVEN = "PROVEN"
    SUPPORTED_FACT_DEPENDENT = "SUPPORTED_BUT_FACT_DEPENDENT"
    PLAUSIBLE_NEEDS_AUTHORITY = "PLAUSIBLE_NEEDS_AUTHORITY"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"


class GateDecision(str, Enum):
    PASS = "PASS"
    PASS_WITH_LIMITS = "PASS_WITH_LIMITS"
    BLOCK = "BLOCK"


class TransactionCapacityGateError(ValueError):
    """Raised when a governed action fails SP-TRANSACTION-CAPACITY-001."""

    def __init__(self, report: "GateReport") -> None:
        self.report = report
        super().__init__(report.summary())


@dataclass(frozen=True)
class GateFinding:
    code: str
    message: str
    blocking: bool = True


@dataclass
class GateReport:
    gate_id: str
    decision: GateDecision
    findings: list[GateFinding] = field(default_factory=list)
    transaction_type: str | None = None
    capacities: list[str] = field(default_factory=list)
    permitted_theories: list[str] = field(default_factory=list)
    quarantined_theories: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.decision in {GateDecision.PASS, GateDecision.PASS_WITH_LIMITS}

    def summary(self) -> str:
        blockers = [f"{f.code}: {f.message}" for f in self.findings if f.blocking]
        if blockers:
            return f"{self.gate_id} BLOCKED — " + "; ".join(blockers)
        return f"{self.gate_id} {self.decision.value}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "decision": self.decision.value,
            "transaction_type": self.transaction_type,
            "capacities": self.capacities,
            "permitted_theories": self.permitted_theories,
            "quarantined_theories": self.quarantined_theories,
            "missing_evidence": self.missing_evidence,
            "findings": [
                {"code": f.code, "message": f.message, "blocking": f.blocking}
                for f in self.findings
            ],
        }


class TransactionCapacityGate:
    """Fail-closed pre-generation gate for high-stakes legal outputs.

    Expected ``transaction_context`` shape::

        {
            "transaction_type": "secured_auto_finance",
            "parties": [{"name": "...", "capacity": "consumer_obligor"}],
            "obligations": [{"obligor": "...", "basis": "retail_installment_contract"}],
            "evidence": ["signed_contract", "payment_history"],
            "governing_law": ["UCC Article 9", "state retail installment law"],
            "theories": [
                {
                    "name": "commercial_reasonableness",
                    "classification": "SUPPORTED_BUT_FACT_DEPENDENT",
                    "evidence": ["sale_notice", "sale_accounting"],
                }
            ],
            "output_purpose": "records_demand",
        }

    The gate does not decide the merits of a legal claim.  It verifies that the system
    has classified the transaction/capacities and that outbound artifacts are not based
    on theories already marked unsupported or contradicted.
    """

    GATE_ID = "SP-TRANSACTION-CAPACITY-001"

    GOVERNED_ACTIONS = {
        "GENERATE_AFFIDAVIT",
        "SEND_DEMAND_LETTER",
        "SEND_DISPUTE_LETTER",
        "SUBMIT_CREDIT_DISPUTE",
        "DRAFT_TRUST_AMENDMENT",
        "FILE_COURT_MOTION",
        "NOTIFY_CREDITOR",
        "UCC_STRATEGY",
    }

    HIGH_STAKES_PURPOSES = {
        "affidavit",
        "demand",
        "ucc_strategy",
        "credit_dispute",
        "trust_communication",
        "court_filing",
        "outbound_notice",
    }

    def evaluate(self, action_type: str, params: dict[str, Any]) -> GateReport:
        if action_type not in self.GOVERNED_ACTIONS:
            return GateReport(gate_id=self.GATE_ID, decision=GateDecision.PASS)

        ctx = params.get("transaction_context")
        if not isinstance(ctx, dict):
            return GateReport(
                gate_id=self.GATE_ID,
                decision=GateDecision.BLOCK,
                findings=[
                    GateFinding(
                        "TC001_CONTEXT_REQUIRED",
                        "transaction_context is required before this legal action may be generated or approved",
                    )
                ],
            )

        findings: list[GateFinding] = []
        missing_evidence: list[str] = []
        permitted: list[str] = []
        quarantined: list[str] = []

        transaction_type = self._text(ctx.get("transaction_type"))
        if not transaction_type:
            findings.append(GateFinding("TC002_TRANSACTION_TYPE", "transaction_type is required"))

        parties = ctx.get("parties") or []
        capacities = [
            self._text(p.get("capacity"))
            for p in parties
            if isinstance(p, dict) and self._text(p.get("capacity"))
        ]
        if not parties or not capacities:
            findings.append(
                GateFinding(
                    "TC003_CAPACITY_MAP",
                    "at least one actual party with an identified legal capacity is required",
                )
            )

        obligations = ctx.get("obligations") or []
        if not obligations:
            findings.append(
                GateFinding(
                    "TC004_OBLIGATION_MAP",
                    "at least one actual obligation and its basis/instrument must be identified",
                )
            )

        governing_law = ctx.get("governing_law") or []
        if action_type in {"FILE_COURT_MOTION", "UCC_STRATEGY", "SEND_DEMAND_LETTER"} and not governing_law:
            findings.append(
                GateFinding(
                    "TC005_GOVERNING_LAW",
                    "governing law/authority must be identified for this action",
                )
            )

        evidence = {self._text(e) for e in (ctx.get("evidence") or []) if self._text(e)}
        theories = ctx.get("theories") or []

        for raw in theories:
            if not isinstance(raw, dict):
                findings.append(GateFinding("TC006_THEORY_FORMAT", "theory entries must be objects"))
                continue

            name = self._text(raw.get("name")) or "unnamed_theory"
            try:
                classification = TheoryClassification(self._text(raw.get("classification")))
            except ValueError:
                findings.append(
                    GateFinding(
                        "TC007_THEORY_CLASSIFICATION",
                        f"{name} has no recognized support classification",
                    )
                )
                continue

            theory_evidence = {
                self._text(item) for item in (raw.get("evidence") or []) if self._text(item)
            }
            required_evidence = {
                self._text(item) for item in (raw.get("required_evidence") or []) if self._text(item)
            }
            available = evidence | theory_evidence
            missing = sorted(required_evidence - available)

            if classification in {TheoryClassification.UNSUPPORTED, TheoryClassification.CONTRADICTED}:
                quarantined.append(name)
                findings.append(
                    GateFinding(
                        "TC008_QUARANTINED_THEORY",
                        f"{name} is classified {classification.value} and cannot support an outbound legal artifact",
                    )
                )
                continue

            if classification == TheoryClassification.PLAUSIBLE_NEEDS_AUTHORITY:
                authorities = raw.get("authorities") or []
                if not authorities:
                    quarantined.append(name)
                    findings.append(
                        GateFinding(
                            "TC009_AUTHORITY_REQUIRED",
                            f"{name} requires supporting authority before use",
                        )
                    )
                    continue

            if missing:
                missing_evidence.extend(f"{name}: {item}" for item in missing)
                # Records/preservation demands may ask for missing evidence; merits assertions may not.
                output_purpose = self._text(ctx.get("output_purpose"))
                if output_purpose not in {"records_demand", "preservation_demand", "evidence_request"}:
                    findings.append(
                        GateFinding(
                            "TC010_EVIDENCE_REQUIRED",
                            f"{name} is missing required evidence: {', '.join(missing)}",
                        )
                    )
                    continue

            permitted.append(name)

        self._apply_special_tests(ctx, findings, evidence, permitted)

        blockers = [finding for finding in findings if finding.blocking]
        if blockers:
            decision = GateDecision.BLOCK
        elif missing_evidence:
            decision = GateDecision.PASS_WITH_LIMITS
        else:
            decision = GateDecision.PASS

        return GateReport(
            gate_id=self.GATE_ID,
            decision=decision,
            findings=findings,
            transaction_type=transaction_type,
            capacities=capacities,
            permitted_theories=permitted,
            quarantined_theories=quarantined,
            missing_evidence=sorted(set(missing_evidence)),
        )

    def enforce(self, action_type: str, params: dict[str, Any]) -> GateReport:
        report = self.evaluate(action_type, params)
        if not report.passed:
            raise TransactionCapacityGateError(report)
        return report

    def _apply_special_tests(
        self,
        ctx: dict[str, Any],
        findings: list[GateFinding],
        evidence: set[str],
        permitted: list[str],
    ) -> None:
        """Apply element-sensitive safeguards for commonly overstated legal theories."""
        theory_names = {name.lower() for name in permitted}

        if {"suretyship", "accommodation_party", "secondary_obligor"} & theory_names:
            required = {"principal_obligation", "secondary_liability_instrument"}
            missing = sorted(required - evidence)
            if missing:
                findings.append(
                    GateFinding(
                        "TC011_SURETY_ELEMENTS",
                        "surety/accommodation theory requires evidence of a principal obligation and a separate secondary-liability instrument: "
                        + ", ".join(missing),
                    )
                )

        if {"deposit_account_control", "article_9_control"} & theory_names:
            if "authenticated_bank_control_agreement" not in evidence and "secured_party_is_bank" not in evidence:
                findings.append(
                    GateFinding(
                        "TC012_DEPOSIT_CONTROL",
                        "deposit-account control may not be asserted without an authenticated bank control agreement or evidence the secured party is the bank",
                    )
                )

        if {"article_9_attachment", "ucc_security_interest", "secured_transaction"} & theory_names:
            required = {"security_agreement", "debtor_rights_in_collateral", "value_given"}
            missing = sorted(required - evidence)
            if missing:
                findings.append(
                    GateFinding(
                        "TC013_ATTACHMENT_ELEMENTS",
                        "Article 9 attachment must be grounded in security agreement, debtor rights in collateral, and value: "
                        + ", ".join(missing),
                    )
                )

    @staticmethod
    def _text(value: Any) -> str:
        return value.strip() if isinstance(value, str) else ""

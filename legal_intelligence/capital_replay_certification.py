"""Independent replay certification for the SintraPrime private-capital stack.

SP-CAPITAL-REPLAY-CERTIFICATION-001 verifies that a material metric or validation
result can be regenerated from retained source evidence and the exact recorded
contract, transformation, policy, and rule versions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from math import isclose
from typing import Any


@dataclass(frozen=True)
class ReplayInputRef:
    source_ref: str
    contract_id: str
    contract_version: str
    lineage_ref: str
    transformation_spec_ref: str
    evidence_ref: str


@dataclass
class ReplayCertificationRequest:
    replay_id: str
    subject_id: str
    result_type: str
    certified_value: Any
    replayed_value: Any
    inputs: list[ReplayInputRef]
    replayed_at: datetime
    replay_actor: str
    original_actor: str | None = None
    tolerance: float = 0.0
    policy_id: str | None = None
    policy_version: str | None = None
    rule_id: str | None = None
    rule_version: str | None = None
    execution_environment_ref: str | None = None
    code_or_formula_ref: str | None = None
    evidence_refs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ReplayCertificationReport:
    module_id: str
    replay_id: str
    subject_id: str
    status: str
    reproducible: bool
    findings: tuple[str, ...]
    variance: float | None
    beneficial_suggestions: tuple[str, ...]


class CapitalReplayCertificationEngine:
    MODULE_ID = "SP-CAPITAL-REPLAY-CERTIFICATION-001"
    MATERIAL_RESULT_TYPES = {
        "COMMITTEE_METRIC",
        "RISK_METRIC",
        "STRESS_RESULT",
        "VALIDATION_RESULT",
        "UNDERWRITING_METRIC",
        "POLICY_METRIC",
        "RULE_PERFORMANCE",
    }

    def certify(self, request: ReplayCertificationRequest) -> ReplayCertificationReport:
        findings: list[str] = []
        required = {
            "REPLAY_ID_REQUIRED": request.replay_id,
            "SUBJECT_ID_REQUIRED": request.subject_id,
            "RESULT_TYPE_REQUIRED": request.result_type,
            "REPLAY_ACTOR_REQUIRED": request.replay_actor,
            "EXECUTION_ENVIRONMENT_REF_REQUIRED": request.execution_environment_ref,
            "CODE_OR_FORMULA_REF_REQUIRED": request.code_or_formula_ref,
        }
        for code, value in required.items():
            if not str(value or "").strip():
                findings.append(code)

        if request.result_type not in self.MATERIAL_RESULT_TYPES:
            findings.append("UNRECOGNIZED_RESULT_TYPE")
        if request.tolerance < 0:
            findings.append("TOLERANCE_INVALID")
        if not request.inputs:
            findings.append("REPLAY_INPUTS_REQUIRED")
        if not request.evidence_refs:
            findings.append("REPLAY_EVIDENCE_REQUIRED")
        if request.original_actor and request.original_actor == request.replay_actor:
            findings.append("INDEPENDENT_REPLAY_ACTOR_REQUIRED")

        for item in request.inputs:
            fields = {
                "SOURCE_REF_REQUIRED": item.source_ref,
                "CONTRACT_ID_REQUIRED": item.contract_id,
                "CONTRACT_VERSION_REQUIRED": item.contract_version,
                "LINEAGE_REF_REQUIRED": item.lineage_ref,
                "TRANSFORMATION_SPEC_REF_REQUIRED": item.transformation_spec_ref,
                "INPUT_EVIDENCE_REF_REQUIRED": item.evidence_ref,
            }
            for code, value in fields.items():
                if not str(value).strip():
                    findings.append(code)

        matched, variance = self._compare(request.certified_value, request.replayed_value, request.tolerance)
        if not matched:
            findings.append("REPLAY_RESULT_MISMATCH")

        hard = {
            "REPLAY_ID_REQUIRED",
            "SUBJECT_ID_REQUIRED",
            "RESULT_TYPE_REQUIRED",
            "REPLAY_ACTOR_REQUIRED",
            "EXECUTION_ENVIRONMENT_REF_REQUIRED",
            "CODE_OR_FORMULA_REF_REQUIRED",
            "UNRECOGNIZED_RESULT_TYPE",
            "TOLERANCE_INVALID",
            "REPLAY_INPUTS_REQUIRED",
            "REPLAY_EVIDENCE_REQUIRED",
            "INDEPENDENT_REPLAY_ACTOR_REQUIRED",
            "SOURCE_REF_REQUIRED",
            "CONTRACT_ID_REQUIRED",
            "CONTRACT_VERSION_REQUIRED",
            "LINEAGE_REF_REQUIRED",
            "TRANSFORMATION_SPEC_REF_REQUIRED",
            "INPUT_EVIDENCE_REF_REQUIRED",
            "REPLAY_RESULT_MISMATCH",
        }
        reproducible = not any(code in hard for code in findings)
        return ReplayCertificationReport(
            module_id=self.MODULE_ID,
            replay_id=request.replay_id,
            subject_id=request.subject_id,
            status="CERTIFIED_REPRODUCIBLE" if reproducible else "REPLAY_FAILED",
            reproducible=reproducible,
            findings=tuple(findings),
            variance=variance,
            beneficial_suggestions=(
                "Retain the exact source evidence, contract version, lineage record, transformation specification, code/formula reference, and execution-environment reference used by the replay.",
                "Use an independent replay actor for material committee, stress, underwriting, and validation outputs.",
                "Treat replay mismatch as a data, transformation, versioning, or execution-integrity incident and route it to SP-CAPITAL-DATA-REMEDIATION-001.",
                "Do not certify reproducibility from narrative agreement alone; the retained inputs must regenerate the certified result within the approved tolerance.",
            ),
        )

    @staticmethod
    def _compare(certified: Any, replayed: Any, tolerance: float) -> tuple[bool, float | None]:
        numeric = (int, float)
        if isinstance(certified, numeric) and isinstance(replayed, numeric) and not isinstance(certified, bool) and not isinstance(replayed, bool):
            variance = abs(float(certified) - float(replayed))
            return isclose(float(certified), float(replayed), rel_tol=0.0, abs_tol=tolerance), round(variance, 12)
        return certified == replayed, None

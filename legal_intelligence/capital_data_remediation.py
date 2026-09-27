"""Controlled data remediation for the SintraPrime private-capital stack.

SP-CAPITAL-DATA-REMEDIATION-001 turns failed data-quality checks into owned,
SLA-bound remediation cases and requires independent recertification before
corrected data is trusted for material downstream use.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Iterable


@dataclass
class DataRemediationCase:
    case_id: str
    dataset_id: str
    severity: str
    owner: str
    opened_date: date
    source_quality_status: str
    failed_findings: list[str]
    due_date: date | None = None
    status: str = "OPEN"
    remediation_plan: list[str] = field(default_factory=list)
    corrected_dataset_ref: str | None = None
    corrected_lineage_ref: str | None = None
    recertifier: str | None = None
    recertification_evidence_refs: list[str] = field(default_factory=list)
    downstream_consumers: list[str] = field(default_factory=list)
    downstream_rerun_refs: list[str] = field(default_factory=list)
    closure_authority: str | None = None
    closed_date: date | None = None


@dataclass(frozen=True)
class DataRemediationDecision:
    module_id: str
    case_id: str
    status: str
    findings: tuple[str, ...]
    downstream_reliance_restored: bool
    beneficial_suggestions: tuple[str, ...]


class CapitalDataRemediationEngine:
    MODULE_ID = "SP-CAPITAL-DATA-REMEDIATION-001"
    SLA_DAYS = {"CRITICAL": 1, "HIGH": 3, "MEDIUM": 7, "LOW": 14}

    def open_case(self, case: DataRemediationCase) -> DataRemediationDecision:
        findings: list[str] = []
        if not case.case_id.strip():
            findings.append("CASE_ID_REQUIRED")
        if not case.dataset_id.strip():
            findings.append("DATASET_ID_REQUIRED")
        if case.severity not in self.SLA_DAYS:
            findings.append("INVALID_SEVERITY")
        if not case.owner.strip():
            findings.append("OWNER_REQUIRED")
        if not case.failed_findings:
            findings.append("FAILED_FINDINGS_REQUIRED")
        if case.source_quality_status == "PASS":
            findings.append("SOURCE_DATA_NOT_FAILED")
        if case.due_date is None and case.severity in self.SLA_DAYS:
            case.due_date = case.opened_date + timedelta(days=self.SLA_DAYS[case.severity])
        return DataRemediationDecision(
            module_id=self.MODULE_ID,
            case_id=case.case_id,
            status="BLOCKED" if findings else "OPEN",
            findings=tuple(findings),
            downstream_reliance_restored=False,
            beneficial_suggestions=(
                "Attach the failed SP-CAPITAL-DATA-QUALITY-001 report and affected lineage records to the remediation case.",
                "Freeze material downstream reliance when data quality is blocked until corrected data is independently recertified.",
                "Use SP-CAPITAL-DATA-LINEAGE-001 to identify every affected downstream consumer before closure.",
            ),
        )

    def evaluate(self, case: DataRemediationCase, *, as_of: date) -> DataRemediationDecision:
        findings: list[str] = []
        status = case.status.upper()
        if case.due_date and status not in {"CLOSED", "RECERTIFIED"} and as_of > case.due_date:
            status = "OVERDUE"
            findings.append("REMEDIATION_SLA_BREACH")
        if not case.remediation_plan:
            findings.append("REMEDIATION_PLAN_REQUIRED")
        if status in {"RECERTIFIED", "CLOSED"}:
            if not case.corrected_dataset_ref:
                findings.append("CORRECTED_DATASET_REFERENCE_REQUIRED")
            if not case.corrected_lineage_ref:
                findings.append("CORRECTED_LINEAGE_REFERENCE_REQUIRED")
            if not case.recertifier:
                findings.append("INDEPENDENT_RECERTIFIER_REQUIRED")
            if case.recertifier == case.owner:
                findings.append("RECERTIFIER_MUST_BE_INDEPENDENT")
            if not case.recertification_evidence_refs:
                findings.append("RECERTIFICATION_EVIDENCE_REQUIRED")
            if case.downstream_consumers and not case.downstream_rerun_refs:
                findings.append("DOWNSTREAM_IMPACT_RERUN_REQUIRED")
            if not case.closure_authority:
                findings.append("CLOSURE_AUTHORITY_REQUIRED")
        restored = status in {"RECERTIFIED", "CLOSED"} and not findings
        if not restored and status == "CLOSED":
            status = "BLOCK_CLOSURE"
        return DataRemediationDecision(
            module_id=self.MODULE_ID,
            case_id=case.case_id,
            status=status,
            findings=tuple(findings),
            downstream_reliance_restored=restored,
            beneficial_suggestions=(
                "Do not restore trust solely because a corrected file exists; require an independent recertifier and evidence-backed quality rerun.",
                "Re-run affected underwriting, stress, validation, drift, dashboard, and committee outputs when lineage shows material dependency.",
                "Journal remediation opening, extensions, recertification, downstream reruns, and closure instead of overwriting prior history.",
            ),
        )

    def impacted_rerun_required(self, case: DataRemediationCase, consumers: Iterable[str]) -> DataRemediationCase:
        case.downstream_consumers = sorted({str(c).strip() for c in consumers if str(c).strip()})
        return case

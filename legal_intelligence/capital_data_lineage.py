"""Governed data-lineage tracing for the SintraPrime private-capital stack.

SP-CAPITAL-DATA-LINEAGE-001 traces material metrics and rule inputs back to
source systems, extraction time, transformations, reconciliation, and evidence.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable


@dataclass(frozen=True)
class LineageStep:
    step_id: str
    step_type: str
    description: str
    actor_or_system: str
    timestamp: datetime
    evidence_ref: str | None = None


@dataclass
class DataLineageRecord:
    lineage_id: str
    dataset_id: str
    metric_or_field: str
    source_system: str
    source_record_ref: str
    extracted_at: datetime
    extraction_actor: str
    transformations: list[LineageStep] = field(default_factory=list)
    reconciliation_ref: str | None = None
    evidence_refs: list[str] = field(default_factory=list)
    downstream_consumers: list[str] = field(default_factory=list)
    policy_id: str | None = None
    policy_version: str | None = None
    rule_id: str | None = None
    rule_version: str | None = None


@dataclass(frozen=True)
class DataLineageReport:
    module_id: str
    lineage_id: str
    status: str
    findings: tuple[str, ...]
    trace_summary: tuple[str, ...]
    beneficial_suggestions: tuple[str, ...]


class CapitalDataLineageEngine:
    MODULE_ID = "SP-CAPITAL-DATA-LINEAGE-001"
    VALID_STEP_TYPES = {"EXTRACT", "TRANSFORM", "JOIN", "AGGREGATE", "RECONCILE", "VALIDATE", "PUBLISH"}

    def validate(self, record: DataLineageRecord) -> DataLineageReport:
        findings: list[str] = []
        required = {
            "LINEAGE_ID_REQUIRED": record.lineage_id,
            "DATASET_ID_REQUIRED": record.dataset_id,
            "METRIC_OR_FIELD_REQUIRED": record.metric_or_field,
            "SOURCE_SYSTEM_REQUIRED": record.source_system,
            "SOURCE_RECORD_REF_REQUIRED": record.source_record_ref,
            "EXTRACTION_ACTOR_REQUIRED": record.extraction_actor,
        }
        for code, value in required.items():
            if not str(value).strip():
                findings.append(code)
        if not record.evidence_refs:
            findings.append("EVIDENCE_REFERENCES_REQUIRED")
        if not record.reconciliation_ref:
            findings.append("RECONCILIATION_REFERENCE_REQUIRED")
        if not record.downstream_consumers:
            findings.append("DOWNSTREAM_CONSUMERS_NOT_RECORDED")

        prior = record.extracted_at
        seen: set[str] = set()
        for step in record.transformations:
            if not step.step_id.strip():
                findings.append("LINEAGE_STEP_ID_REQUIRED")
            if step.step_id in seen:
                findings.append("DUPLICATE_LINEAGE_STEP_ID")
            seen.add(step.step_id)
            if step.step_type not in self.VALID_STEP_TYPES:
                findings.append("INVALID_LINEAGE_STEP_TYPE")
            if not step.description.strip() or not step.actor_or_system.strip():
                findings.append("LINEAGE_STEP_DETAIL_REQUIRED")
            if step.timestamp < prior:
                findings.append("NON_MONOTONIC_LINEAGE_TIMESTAMP")
            prior = max(prior, step.timestamp)

        hard = {code for code in findings if code != "DOWNSTREAM_CONSUMERS_NOT_RECORDED"}
        status = "COMPLETE" if not findings else ("WATCH" if not hard else "INCOMPLETE")
        trace = (
            f"source={record.source_system}:{record.source_record_ref}",
            f"extracted_at={record.extracted_at.isoformat()}",
            f"transform_steps={len(record.transformations)}",
            f"downstream_consumers={len(record.downstream_consumers)}",
        )
        return DataLineageReport(
            module_id=self.MODULE_ID,
            lineage_id=record.lineage_id,
            status=status,
            findings=tuple(findings),
            trace_summary=trace,
            beneficial_suggestions=(
                "Persist immutable source references and extraction timestamps for every material metric used in committee, stress, underwriting, or rule validation.",
                "Hash or otherwise preserve transformation specifications so later reviewers can reproduce the same metric from the same source data.",
                "Record every downstream consumer so a source correction can trigger targeted reruns instead of relying on manual memory.",
                "Link lineage records to the decision journal when metrics support a material approval or policy decision.",
            ),
        )

    def impacted_consumers(self, records: Iterable[DataLineageRecord], dataset_id: str) -> tuple[str, ...]:
        consumers = {c for r in records if r.dataset_id == dataset_id for c in r.downstream_consumers if c.strip()}
        return tuple(sorted(consumers))

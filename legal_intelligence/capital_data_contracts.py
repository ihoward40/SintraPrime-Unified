"""Governed source-data contracts for the SintraPrime private-capital stack.

SP-CAPITAL-DATA-CONTRACTS-001 defines the approved interface for source datasets:
schema, required fields, units, freshness, reconciliation, ownership, allowed
transformations, and breaking-change procedure.

These are internal governance controls, not regulatory data standards.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable


@dataclass(frozen=True)
class DataContractField:
    name: str
    data_type: str
    required: bool = True
    unit: str | None = None
    nullable: bool = False
    description: str = ""


@dataclass
class DataContract:
    contract_id: str
    version: str
    dataset_id: str
    owner: str
    source_system: str
    fields: list[DataContractField]
    freshness_sla_hours: int
    reconciliation_rule: str
    allowed_transformations: list[str]
    breaking_change_protocol: str
    status: str = "ACTIVE"
    effective_at: datetime | None = None
    supersedes_version: str | None = None
    policy_id: str | None = None
    policy_version: str | None = None
    evidence_refs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DataContractValidation:
    module_id: str
    contract_id: str
    version: str
    dataset_id: str
    status: str
    valid: bool
    findings: tuple[str, ...]
    beneficial_suggestions: tuple[str, ...]


@dataclass(frozen=True)
class DatasetConformanceReport:
    module_id: str
    contract_id: str
    version: str
    dataset_id: str
    status: str
    findings: tuple[str, ...]
    breaking_change_detected: bool
    beneficial_suggestions: tuple[str, ...]


class CapitalDataContractsEngine:
    MODULE_ID = "SP-CAPITAL-DATA-CONTRACTS-001"
    VALID_STATUSES = {"DRAFT", "ACTIVE", "UNDER_REVIEW", "SUPERSEDED", "RETIRED"}
    VALID_TYPES = {"STRING", "INTEGER", "DECIMAL", "BOOLEAN", "DATE", "DATETIME", "JSON"}

    def validate_contract(self, contract: DataContract) -> DataContractValidation:
        findings: list[str] = []
        required = {
            "CONTRACT_ID_REQUIRED": contract.contract_id,
            "VERSION_REQUIRED": contract.version,
            "DATASET_ID_REQUIRED": contract.dataset_id,
            "OWNER_REQUIRED": contract.owner,
            "SOURCE_SYSTEM_REQUIRED": contract.source_system,
            "RECONCILIATION_RULE_REQUIRED": contract.reconciliation_rule,
            "BREAKING_CHANGE_PROTOCOL_REQUIRED": contract.breaking_change_protocol,
        }
        for code, value in required.items():
            if not str(value).strip():
                findings.append(code)
        if contract.status not in self.VALID_STATUSES:
            findings.append("INVALID_CONTRACT_STATUS")
        if contract.freshness_sla_hours <= 0:
            findings.append("FRESHNESS_SLA_INVALID")
        if not contract.fields:
            findings.append("SCHEMA_FIELDS_REQUIRED")
        if not contract.allowed_transformations:
            findings.append("ALLOWED_TRANSFORMATIONS_REQUIRED")

        seen: set[str] = set()
        for field_def in contract.fields:
            name = field_def.name.strip()
            if not name:
                findings.append("FIELD_NAME_REQUIRED")
            if name in seen:
                findings.append("DUPLICATE_FIELD_NAME")
            seen.add(name)
            if field_def.data_type.upper() not in self.VALID_TYPES:
                findings.append(f"INVALID_FIELD_TYPE:{name}")
            if field_def.required and field_def.nullable:
                findings.append(f"REQUIRED_FIELD_NULLABLE:{name}")

        if contract.status == "ACTIVE" and contract.effective_at is None:
            findings.append("ACTIVE_CONTRACT_EFFECTIVE_AT_REQUIRED")
        if contract.status in {"SUPERSEDED", "RETIRED"} and not contract.evidence_refs:
            findings.append("RETIREMENT_OR_SUPERSESSION_EVIDENCE_REQUIRED")

        valid = not findings
        return DataContractValidation(
            module_id=self.MODULE_ID,
            contract_id=contract.contract_id,
            version=contract.version,
            dataset_id=contract.dataset_id,
            status="VALID" if valid else "INVALID",
            valid=valid,
            findings=tuple(findings),
            beneficial_suggestions=(
                "Version source-data contracts immutably; never overwrite the active schema definition in place.",
                "Link every material downstream metric and rule input to the exact contract version under which its source data was accepted.",
                "Require producer and consumer impact review before approving a breaking schema, unit, freshness, or reconciliation change.",
                "Preserve sample payloads and conformance evidence so contract behavior can be independently tested later.",
            ),
        )

    def check_dataset(
        self,
        contract: DataContract,
        *,
        observed_fields: Iterable[str],
        observed_types: dict[str, str],
        observed_units: dict[str, str | None] | None = None,
        extracted_at: datetime,
        reconciled: bool,
        transformations_used: Iterable[str] = (),
        as_of: datetime | None = None,
    ) -> DatasetConformanceReport:
        findings: list[str] = []
        observed = {str(name).strip() for name in observed_fields if str(name).strip()}
        units = observed_units or {}
        now = as_of or datetime.now(timezone.utc)
        breaking = False

        validation = self.validate_contract(contract)
        if not validation.valid:
            findings.append("CONTRACT_INVALID")

        for field_def in contract.fields:
            name = field_def.name
            if field_def.required and name not in observed:
                findings.append(f"REQUIRED_FIELD_MISSING:{name}")
                breaking = True
            if name in observed:
                observed_type = str(observed_types.get(name, "")).upper()
                if observed_type and observed_type != field_def.data_type.upper():
                    findings.append(f"FIELD_TYPE_MISMATCH:{name}")
                    breaking = True
                if field_def.unit is not None and units.get(name) != field_def.unit:
                    findings.append(f"FIELD_UNIT_MISMATCH:{name}")
                    breaking = True

        known = {field.name for field in contract.fields}
        unexpected = sorted(observed - known)
        if unexpected:
            findings.extend(f"UNDECLARED_FIELD:{name}" for name in unexpected)

        if extracted_at.tzinfo is None:
            findings.append("EXTRACTION_TIMESTAMP_TIMEZONE_REQUIRED")
        else:
            age = now - extracted_at.astimezone(timezone.utc)
            if age > timedelta(hours=contract.freshness_sla_hours):
                findings.append("DATASET_FRESHNESS_SLA_BREACHED")
        if not reconciled:
            findings.append("RECONCILIATION_NOT_SATISFIED")

        allowed = {item.strip() for item in contract.allowed_transformations if item.strip()}
        used = {str(item).strip() for item in transformations_used if str(item).strip()}
        disallowed = sorted(used - allowed)
        if disallowed:
            findings.extend(f"TRANSFORMATION_NOT_ALLOWED:{item}" for item in disallowed)
            breaking = True

        blockers = {
            "CONTRACT_INVALID",
            "EXTRACTION_TIMESTAMP_TIMEZONE_REQUIRED",
            "DATASET_FRESHNESS_SLA_BREACHED",
            "RECONCILIATION_NOT_SATISFIED",
        }
        block = breaking or any(item in blockers for item in findings)
        return DatasetConformanceReport(
            module_id=self.MODULE_ID,
            contract_id=contract.contract_id,
            version=contract.version,
            dataset_id=contract.dataset_id,
            status="BLOCK_USE" if block else ("WATCH" if findings else "PASS"),
            findings=tuple(findings),
            breaking_change_detected=breaking,
            beneficial_suggestions=(
                "Reject material downstream reliance when the producer payload violates the approved contract.",
                "Route breaking changes through explicit contract versioning and downstream dependency review before activation.",
                "Tie freshness and reconciliation evidence to SP-CAPITAL-DATA-LINEAGE-001 so conformance can be replayed later.",
            ),
        )

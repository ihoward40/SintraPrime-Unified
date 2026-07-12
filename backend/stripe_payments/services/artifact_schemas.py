"""Strict local schema checks for generated case artifacts.

This module intentionally avoids a jsonschema dependency so the verifier can
run in the current repo environment.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class SchemaValidationError(ValueError):
    """Raised when a generated artifact violates its expected shape."""


def _require_keys(obj: dict[str, Any], required: set[str], allowed: set[str], name: str) -> None:
    missing = sorted(required - obj.keys())
    extra = sorted(obj.keys() - allowed)
    if missing:
        raise SchemaValidationError(f"{name} missing required fields: {', '.join(missing)}")
    if extra:
        raise SchemaValidationError(f"{name} has unknown fields: {', '.join(extra)}")


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise SchemaValidationError(f"{path} must contain a JSON object")
    return data


def _require_schema_version(data: dict[str, Any], expected: str, name: str) -> None:
    actual = data.get("schema_version")
    if actual != expected:
        raise SchemaValidationError(f"{name} has unsupported schema_version: {actual!r}")


def _require_iso_datetime(value: Any, field: str, name: str) -> None:
    if not isinstance(value, str):
        raise SchemaValidationError(f"{name} {field} must be an ISO datetime string")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError as exc:
        raise SchemaValidationError(f"{name} {field} must be an ISO datetime string") from exc


def validate_case_file(path: Path) -> None:
    data = _load(path)
    required = {
        "schema_version",
        "case_id",
        "case_type",
        "case_summary",
        "court",
        "creditor",
        "jurisdiction",
        "matter_type",
        "opened_date",
        "venue",
    }
    _require_keys(data, required, required | {"client_id"}, "case.json")
    _require_schema_version(data, "case.v1", "case.json")
    _require_iso_datetime(data["opened_date"], "opened_date", "case.json")
    for field in ("court", "jurisdiction", "venue", "case_type"):
        if not data.get(field):
            raise SchemaValidationError(f"case.json {field} is required and must not be empty")


def validate_evidence_manifest(path: Path) -> None:
    data = _load(path)
    _require_keys(data, {"schema_version", "verification_summary", "evidence_items"}, {"schema_version", "verification_summary", "evidence_items"}, "evidence_manifest.json")
    _require_schema_version(data, "evidence_manifest.v1", "evidence_manifest.json")
    if not isinstance(data["evidence_items"], list):
        raise SchemaValidationError("evidence_manifest.json evidence_items must be a list")


def validate_readiness_report(path: Path) -> None:
    data = _load(path)
    allowed = {"schema_version", "status", "overall_readiness_score", "blocked_reasons"}
    _require_keys(data, {"schema_version", "status", "overall_readiness_score"}, allowed, "readiness_report.json")
    _require_schema_version(data, "readiness_report.v1", "readiness_report.json")
    if data["status"] not in {"INITIATED", "BLOCKED", "READY"}:
        raise SchemaValidationError("readiness_report.json has invalid status")
    if data["status"] == "READY" and data.get("blocked_reasons"):
        raise SchemaValidationError("readiness_report.json cannot be READY with blocked_reasons")


def validate_violation_candidates(path: Path) -> None:
    data = _load(path)
    _require_keys(data, {"schema_version", "violation_candidates"}, {"schema_version", "violation_candidates"}, "violation_candidates.json")
    _require_schema_version(data, "violation_candidates.v1", "violation_candidates.json")
    if not isinstance(data["violation_candidates"], list):
        raise SchemaValidationError("violation_candidates.json violation_candidates must be a list")


def validate_complaint_draft(path: Path) -> None:
    data = _load(path)
    required = {
        "schema_version",
        "case_id",
        "court",
        "creditor",
        "draft_notes",
        "filing_ready",
        "generated_at",
        "jurisdiction",
        "missing_required_fields",
        "prayer_for_relief",
        "venue",
        "violations",
    }
    _require_keys(data, required, required, "complaint_draft.json")
    _require_schema_version(data, "complaint_draft.v1", "complaint_draft.json")
    _require_iso_datetime(data["generated_at"], "generated_at", "complaint_draft.json")
    if data["filing_ready"] and data["missing_required_fields"]:
        raise SchemaValidationError("complaint_draft.json cannot be filing_ready with missing fields")


def validate_court_bundle(path: Path) -> None:
    data = _load(path)
    required = {
        "schema_version",
        "case_id",
        "draft_recommendation",
        "draft_status",
        "evidence",
        "generated_at",
        "missing_evidence",
        "readiness",
        "source",
        "violation_candidates",
    }
    _require_keys(data, required, required, "court_bundle_draft.json")
    _require_schema_version(data, "court_bundle_draft.v1", "court_bundle_draft.json")
    _require_iso_datetime(data["generated_at"], "generated_at", "court_bundle_draft.json")




def validate_command_center(path: Path) -> None:
    data = _load(path)
    _require_keys(data, {"schema_version", "dashboard_mode", "generated_at", "run_id", "cases"}, {"schema_version", "dashboard_mode", "generated_at", "run_id", "cases"}, "command_center.json")
    _require_schema_version(data, "command_center.v2", "command_center.json")
    if data["dashboard_mode"] not in {"aggregate", "run-scoped"}:
        raise SchemaValidationError("command_center.json has invalid dashboard_mode")
    _require_iso_datetime(data["generated_at"], "generated_at", "command_center.json")
    if not isinstance(data["run_id"], str) or not data["run_id"]:
        raise SchemaValidationError("command_center.json run_id must be a non-empty string")
    if not isinstance(data["cases"], list):
        raise SchemaValidationError("command_center.json cases must be a list")

def validate_response_analysis(path: Path) -> None:
    data = _load(path)
    required = {"schema_version", "analysis", "case_id", "generated_at", "has_creditor_response" }
    _require_keys(data, required, required, "response_analysis.json")
    _require_schema_version(data, "response_analysis.v1", "response_analysis.json")
    _require_iso_datetime(data["generated_at"], "generated_at", "response_analysis.json")


VALIDATORS = {
    "case.json": validate_case_file,
    "evidence_manifest.json": validate_evidence_manifest,
    "readiness_report.json": validate_readiness_report,
    "violation_candidates.json": validate_violation_candidates,
    "complaint_draft.json": validate_complaint_draft,
    "court_bundle_draft.json": validate_court_bundle,
    "response_analysis.json": validate_response_analysis,
    "command_center_local.json": validate_command_center,
    "command_center.json": validate_command_center,
}


def validate_artifact(path: Path) -> None:
    validator = VALIDATORS.get(path.name)
    if validator:
        validator(path)


def validate_artifact_tree(root: Path) -> None:
    files = {path.name: path for path in root.rglob("*.json")}
    for path in sorted(files.values()):
        validate_artifact(path)
    case_path = files.get("case.json")
    readiness_path = files.get("readiness_report.json")
    evidence_path = files.get("evidence_manifest.json")
    if case_path and readiness_path:
        case_data = _load(case_path)
        readiness = _load(readiness_path)
        missing_case_fields = [field for field in ("court", "jurisdiction", "venue", "case_type") if not case_data.get(field)]
        if readiness.get("status") == "READY" and missing_case_fields:
            raise SchemaValidationError("readiness_report.json cannot be READY when court/jurisdiction/venue/case_type is missing")
    if readiness_path and evidence_path:
        readiness = _load(readiness_path)
        evidence = _load(evidence_path)
        summary = evidence.get("verification_summary", {})
        if readiness.get("status") == "READY" and isinstance(summary, dict) and summary.get("missing", 0):
            raise SchemaValidationError("readiness_report.json cannot be READY when evidence is missing")

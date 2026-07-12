from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import shutil
import sys
import uuid
from pathlib import Path

import pytest


def load_module(name: str, rel_path: str):
    spec = importlib.util.spec_from_file_location(name, Path(rel_path))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


artifact_schemas = load_module("artifact_schemas", "backend/stripe_payments/services/artifact_schemas.py")
case_security = load_module("case_security", "backend/stripe_payments/services/case_security.py")
court_generator = load_module("court_filing_draft_center", "orchestration/enforcement/court_filing_draft_center.py")

SchemaValidationError = artifact_schemas.SchemaValidationError
validate_case_file = artifact_schemas.validate_case_file
CaseSecurityError = case_security.CaseSecurityError
contained_child = case_security.contained_child
validate_case_id = case_security.validate_case_id
verify_hmac_signature = case_security.verify_hmac_signature
CaseInput = court_generator.CaseInput
build_complaint_draft_text = court_generator.build_complaint_draft_text


def extract_last_json(stdout_text: str) -> dict:
    decoder = json.JSONDecoder()
    matches = []
    for index, char in enumerate(stdout_text):
        if char != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(stdout_text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            matches.append(obj)
    if not matches:
        raise ValueError("No valid JSON found in generator stdout")
    return matches[-1]


def sign(secret: str, event_id: str, body: bytes) -> str:
    return hmac.new(secret.encode(), event_id.encode() + b"." + body, hashlib.sha256).hexdigest()


@pytest.mark.parametrize("case_id", ["../BAD", "BAD/ID", "BAD\\ID", "C:BAD", "CON", "BAD.", "ab"])
def test_invalid_case_ids_rejected(case_id: str) -> None:
    with pytest.raises(CaseSecurityError):
        validate_case_id(case_id)


def test_case_path_must_remain_under_clients() -> None:
    root = Path.cwd() / ".case_runs" / "pytest" / uuid.uuid4().hex
    try:
        target = contained_child(root / "clients", "CASE_OK-001")
        assert target.parent == (root / "clients").resolve()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_extract_last_json_returns_final_object() -> None:
    stdout = '{"progress": 1}\nnoise\n{"ok": true, "generated_cases": 1}'
    assert extract_last_json(stdout) == {"ok": True, "generated_cases": 1}


def test_missing_jurisdiction_blocks_complaint() -> None:
    case = CaseInput(
        case_dir=Path("clients/CASE-001"),
        case_id="CASE-001",
        case_json={"case_id": "CASE-001", "case_type": "credit_dispute", "creditor": "Creditor"},
        evidence_manifest=None,
        violation_candidates={"violation_candidates": []},
        readiness_report=None,
    )
    md, payload = build_complaint_draft_text(case)
    assert payload["filing_ready"] is False
    assert "jurisdiction" in payload["missing_required_fields"]
    assert "credit_dispute" not in (payload.get("jurisdiction") or "")
    assert "BLOCKED" in md


def test_case_schema_rejects_unknown_fields() -> None:
    root = Path.cwd() / ".case_runs" / "pytest" / uuid.uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    path = root / "case.json"
    path.write_text(json.dumps({
        "case_id": "CASE-001",
        "case_type": "credit_dispute",
        "case_summary": "summary",
        "court": "Court",
        "creditor": "Creditor",
        "jurisdiction": "Jurisdiction",
        "matter_type": "FCRA",
        "opened_date": "2026-07-10T00:00:00+00:00",
        "venue": "Venue",
        "unexpected": True,
    }), encoding="utf-8")
    try:
        with pytest.raises(SchemaValidationError):
            validate_case_file(path)
    finally:
        shutil.rmtree(root, ignore_errors=True)



def test_hmac_signature_rejects_missing_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MONETIZATION_START_CASE_WEBHOOK_SECRET", raising=False)
    with pytest.raises(CaseSecurityError):
        verify_hmac_signature(body=b"{}", event_id="evt_123", signature="bad")


def test_hmac_signature_rejects_bad_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MONETIZATION_START_CASE_WEBHOOK_SECRET", "secret")
    with pytest.raises(CaseSecurityError):
        verify_hmac_signature(body=b"{}", event_id="evt_123", signature="bad")


def test_hmac_signature_accepts_valid_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MONETIZATION_START_CASE_WEBHOOK_SECRET", "secret")
    body = b'{"payment_session_id":"evt_123"}'
    signature = sign("secret", "evt_123", body)
    verify_hmac_signature(body=body, event_id="evt_123", signature=signature)

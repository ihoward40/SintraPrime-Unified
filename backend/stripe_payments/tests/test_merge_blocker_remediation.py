from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import shutil
import sys
import types
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest


def load_module(name: str, rel_path: str):
    parts = name.split(".")
    for i in range(1, len(parts)):
        pkg = ".".join(parts[:i])
        if pkg not in sys.modules:
            module = types.ModuleType(pkg)
            module.__path__ = []
            sys.modules[pkg] = module
    spec = importlib.util.spec_from_file_location(name, Path(rel_path))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


load_module("backend.stripe_payments.config", "backend/stripe_payments/config.py")
case_security_mod = load_module("backend.stripe_payments.services.case_security", "backend/stripe_payments/services/case_security.py")
case_idem_mod = load_module("backend.stripe_payments.services.case_idempotency", "backend/stripe_payments/services/case_idempotency.py")
artifact_schemas_mod = load_module("backend.stripe_payments.services.artifact_schemas", "backend/stripe_payments/services/artifact_schemas.py")

SQLiteIdempotencyStore = case_idem_mod.SQLiteIdempotencyStore
IdempotencyConflictError = case_idem_mod.IdempotencyConflictError
CaseSecurityError = case_security_mod.CaseSecurityError
canonical_signature_input = case_security_mod.canonical_signature_input
verify_signed_internal_event = case_security_mod.verify_signed_internal_event
SchemaValidationError = artifact_schemas_mod.SchemaValidationError
validate_artifact_tree = artifact_schemas_mod.validate_artifact_tree



def now_iso(offset_seconds: int = 0) -> str:
    return (datetime.now(UTC) + timedelta(seconds=offset_seconds)).isoformat()


def event_payload(**overrides):
    payload = {
        "schema_version": "internal_payment_event.v1",
        "event_id": "evt_case_123",
        "event_type": "checkout.session.completed",
        "payment_session_id": "cs_paid_123",
        "payment_status": "paid",
        "session_status": "complete",
        "amount_total": 9900,
        "currency": "usd",
        "tier": "starter",
        "case_id": "CASE-PAID-123",
        "stripe_created_at": now_iso(-20),
        "verified_at": now_iso(-10),
        "key_id": "current",
        "email": "client@example.com",
        "case_type": "credit_dispute",
        "matter_type": "FCRA",
        "creditor_name": "Creditor",
        "court": "County Court",
        "jurisdiction": "State",
        "venue": "County",
    }
    payload.update(overrides)
    return payload


def signed_headers(secret: str, body: bytes, *, key_id="current", event_id="evt_case_123", timestamp=None):
    timestamp = timestamp or now_iso()
    digest = hashlib.sha256(body).hexdigest()
    sig = hmac.new(
        secret.encode(),
        canonical_signature_input(key_id=key_id, timestamp=timestamp, event_id=event_id, raw_body_sha256=digest),
        hashlib.sha256,
    ).hexdigest()
    return {
        "X-Start-Case-Key-Id": key_id,
        "X-Start-Case-Timestamp": timestamp,
        "X-Start-Case-Event-Id": event_id,
        "X-Start-Case-Signature": sig,
    }


def configure_keys(monkeypatch):
    monkeypatch.setenv("MONETIZATION_START_CASE_CURRENT_KEY_ID", "current")
    monkeypatch.setenv("MONETIZATION_START_CASE_CURRENT_SECRET", "secret-current")
    monkeypatch.setenv("MONETIZATION_START_CASE_PREVIOUS_KEY_ID", "previous")
    monkeypatch.setenv("MONETIZATION_START_CASE_PREVIOUS_SECRET", "secret-previous")
    monkeypatch.setenv("MONETIZATION_START_CASE_MAX_AGE_SECONDS", "300")
    monkeypatch.setenv("MONETIZATION_START_CASE_CLOCK_SKEW_SECONDS", "60")


def test_signed_event_accepts_current_and_previous_keys(monkeypatch):
    configure_keys(monkeypatch)
    body = json.dumps(event_payload(), separators=(",", ":")).encode()
    headers = signed_headers("secret-current", body)
    assert verify_signed_internal_event(body=body, key_id=headers["X-Start-Case-Key-Id"], timestamp=headers["X-Start-Case-Timestamp"], event_id=headers["X-Start-Case-Event-Id"], signature=headers["X-Start-Case-Signature"]).case_id == "CASE-PAID-123"

    body2 = json.dumps(event_payload(key_id="previous"), separators=(",", ":")).encode()
    headers2 = signed_headers("secret-previous", body2, key_id="previous")
    assert verify_signed_internal_event(body=body2, key_id="previous", timestamp=headers2["X-Start-Case-Timestamp"], event_id="evt_case_123", signature=headers2["X-Start-Case-Signature"]).key_id == "previous"


@pytest.mark.parametrize(("override", "error"), [
    ({"event_type": "checkout.session.expired"}, "event type"),
    ({"payment_status": "unpaid"}, "payment_status"),
    ({"session_status": "open"}, "session_status"),
    ({"amount_total": 1}, "amount_total"),
    ({"currency": "eur"}, "currency"),
    ({"case_id": "../BAD"}, "case_id"),
    ({"unknown_field": True}, "unknown"),
])
def test_signed_event_rejects_invalid_payment_contract(monkeypatch, override, error):
    configure_keys(monkeypatch)
    body = json.dumps(event_payload(**override), separators=(",", ":")).encode()
    headers = signed_headers("secret-current", body)
    with pytest.raises(CaseSecurityError, match=error):
        verify_signed_internal_event(body=body, key_id="current", timestamp=headers["X-Start-Case-Timestamp"], event_id="evt_case_123", signature=headers["X-Start-Case-Signature"])


def test_signed_event_rejects_expired_future_altered_and_unknown_key(monkeypatch):
    configure_keys(monkeypatch)
    body = json.dumps(event_payload(), separators=(",", ":")).encode()
    expired = signed_headers("secret-current", body, timestamp=now_iso(-1000))
    with pytest.raises(CaseSecurityError, match="expired"):
        verify_signed_internal_event(body=body, key_id="current", timestamp=expired["X-Start-Case-Timestamp"], event_id="evt_case_123", signature=expired["X-Start-Case-Signature"])
    future = signed_headers("secret-current", body, timestamp=now_iso(1000))
    with pytest.raises(CaseSecurityError, match="future"):
        verify_signed_internal_event(body=body, key_id="current", timestamp=future["X-Start-Case-Timestamp"], event_id="evt_case_123", signature=future["X-Start-Case-Signature"])
    valid = signed_headers("secret-current", body)
    with pytest.raises(CaseSecurityError, match="unknown"):
        verify_signed_internal_event(body=body, key_id="missing", timestamp=valid["X-Start-Case-Timestamp"], event_id="evt_case_123", signature=valid["X-Start-Case-Signature"])
    altered = json.dumps(event_payload(case_id="CASE-PAID-999"), separators=(",", ":")).encode()
    with pytest.raises(CaseSecurityError, match="signature"):
        verify_signed_internal_event(body=altered, key_id="current", timestamp=valid["X-Start-Case-Timestamp"], event_id="evt_case_123", signature=valid["X-Start-Case-Signature"])


def test_route_level_auth_and_binding(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from backend.stripe_payments.api.routes import router
    from backend.stripe_payments.models.monetization import StartCaseResponse

    configure_keys(monkeypatch)
    app = FastAPI()
    app.include_router(router)

    async def fake_start_case(payload, *, verified_event):
        return StartCaseResponse(ok=True, case_id=payload.case_id, initialization_ledgers=[], draft_generation={"verified_event": verified_event.event_id}, errors=None)

    monkeypatch.setattr("backend.stripe_payments.api.routes.case_starter_service.start_case", fake_start_case)
    client = TestClient(app)
    payload = event_payload()
    body = json.dumps(payload, separators=(",", ":")).encode()
    response = client.post("/api/monetization/start-case", content=body, headers=signed_headers("secret-current", body))
    assert response.status_code == 200
    assert response.json()["case_id"] == "CASE-PAID-123"

    bad = client.post("/api/monetization/start-case", content=body)
    assert bad.status_code == 422

    altered_payload = dict(payload)
    altered_payload["tier"] = "pro"
    altered_body = json.dumps(altered_payload, separators=(",", ":")).encode()
    altered = client.post("/api/monetization/start-case", content=altered_body, headers=signed_headers("secret-current", altered_body))
    assert altered.status_code == 401


def scratch_dir() -> Path:
    path = Path.cwd() / ".case_runs" / "pytest-manual" / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_sqlite_idempotency_claims_and_replays():
    tmp_path = scratch_dir()
    try:
        store = SQLiteIdempotencyStore(tmp_path / "events.sqlite3")
        claim = store.claim(event_id="evt_1", body_digest="abc", case_id="CASE-001", payment_session_id="cs_1")
        assert claim.action == "claimed"
        with pytest.raises(IdempotencyConflictError):
            store.claim(event_id="evt_1", body_digest="def", case_id="CASE-001", payment_session_id="cs_1")
        store.mark_succeeded("evt_1", {"ok": True, "case_id": "CASE-001"})
        replay = store.claim(event_id="evt_1", body_digest="abc", case_id="CASE-001", payment_session_id="cs_1")
        assert replay.action == "replay"
        assert replay.response_json["case_id"] == "CASE-001"
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_schema_downgrade_policy_rejects_new_unversioned_file():
    tmp_path = scratch_dir()
    case_dir = tmp_path / "CASE-SCHEMA-001"
    case_dir.mkdir()
    (case_dir / "case.json").write_text(json.dumps({"case_id": "CASE-SCHEMA-001"}), encoding="utf-8")
    try:
        with pytest.raises(SchemaValidationError):
            validate_artifact_tree(case_dir)
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_readiness_ready_conflicts_with_missing_evidence():
    tmp_path = scratch_dir()
    case_dir = tmp_path / "CASE-SCHEMA-002"
    case_dir.mkdir()
    (case_dir / "case.json").write_text(json.dumps({
        "schema_version": "case.v1",
        "case_id": "CASE-SCHEMA-002",
        "case_type": "credit_dispute",
        "case_summary": "summary",
        "court": "Court",
        "creditor": "Creditor",
        "jurisdiction": "State",
        "matter_type": "FCRA",
        "opened_date": now_iso(),
        "venue": "County",
    }), encoding="utf-8")
    (case_dir / "evidence_manifest.json").write_text(json.dumps({"schema_version": "evidence_manifest.v1", "verification_summary": {"missing": 1}, "evidence_items": []}), encoding="utf-8")
    (case_dir / "readiness_report.json").write_text(json.dumps({"schema_version": "readiness_report.v1", "status": "READY", "overall_readiness_score": 100}), encoding="utf-8")
    try:
        with pytest.raises(SchemaValidationError, match="evidence"):
            validate_artifact_tree(case_dir)
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)

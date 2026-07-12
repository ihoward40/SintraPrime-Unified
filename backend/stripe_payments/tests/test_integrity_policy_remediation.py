import hashlib
import importlib.util
import io
import json
import shutil
import sys
import types
from contextlib import redirect_stdout
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest


def load_module(name: str, rel_path: str):
    parts = name.split('.')
    for i in range(1, len(parts)):
        pkg = '.'.join(parts[:i])
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


verify_mod = load_module('verify_ledger', 'ledger/verify_ledger.py')
load_module('backend.stripe_payments.models', 'backend/stripe_payments/models/__init__.py')
load_module('backend.stripe_payments.models.monetization', 'backend/stripe_payments/models/monetization.py')
load_module('backend.stripe_payments.services.case_security', 'backend/stripe_payments/services/case_security.py')
load_module('backend.stripe_payments.services.case_idempotency', 'backend/stripe_payments/services/case_idempotency.py')
artifact_schemas_mod = load_module('backend.stripe_payments.services.artifact_schemas', 'backend/stripe_payments/services/artifact_schemas.py')
case_starter_mod = load_module('backend.stripe_payments.services.case_starter_service', 'backend/stripe_payments/services/case_starter_service.py')
validate_json_mod = load_module('validate_generated_json', 'scripts/validate_generated_json.py')
confidential_guard_mod = load_module('check_confidential_artifacts', 'scripts/check_confidential_artifacts.py')

CaseLock = case_starter_mod.CaseLock
CaseStartConflictError = case_starter_mod.CaseStartConflictError
validate_command_center = artifact_schemas_mod.validate_command_center
SchemaValidationError = artifact_schemas_mod.SchemaValidationError


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, obj: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, sort_keys=True, indent=2)
    path.write_text(text, encoding='utf-8')
    return sha_bytes(path.read_bytes())


def make_index_repo(tmp_path: Path) -> Path:
    root = tmp_path / 'repo'
    (root / 'ledger' / 'logs').mkdir(parents=True)
    (root / 'ledger' / 'hashes').mkdir(parents=True)
    (root / 'ledger' / 'snapshots').mkdir(parents=True)
    snap1 = root / 'ledger' / 'snapshots' / 'one.json'
    snap2 = root / 'ledger' / 'snapshots' / 'two.json'
    snap1_digest = write_json(snap1, {'case_id': 'CASE-INDEX-1'})
    snap2_digest = write_json(snap2, {'case_id': 'CASE-INDEX-2'})
    legacy_log = root / 'ledger' / 'logs' / '000-legacy.json'
    legacy_hash = root / 'ledger' / 'hashes' / 'LEDGER-LEGACY.sha256'
    current1 = root / 'ledger' / 'logs' / '001-current.json'
    current2 = root / 'ledger' / 'logs' / '002-current.json'
    write_json(legacy_log, {'id': 'LEDGER-LEGACY', 'snapshot': {'path': 'ledger/snapshots/one.json'}})
    write_json(legacy_hash, {'sha256': snap1_digest, 'snapshot_path': 'ledger/snapshots/one.json'})
    current1_digest = write_json(current1, {
        'schema_version': 'ledger-entry.v1',
        'entry_id': 'LEDGER-CHAIN-1',
        'snapshot_path': 'ledger/snapshots/two.json',
        'snapshot_sha256': snap2_digest,
        'previous_entry_sha256': 'legacy:LEDGER-LEGACY',
    })
    write_json(root / 'ledger' / 'hashes' / 'LEDGER-CHAIN-1.sha256', {'snapshot_sha256': snap2_digest, 'snapshot_path': 'ledger/snapshots/two.json'})
    current2_digest = write_json(current2, {
        'schema_version': 'ledger-entry.v1',
        'entry_id': 'LEDGER-CHAIN-2',
        'snapshot_path': 'ledger/snapshots/two.json',
        'snapshot_sha256': snap2_digest,
        'previous_entry_sha256': current1_digest,
    })
    write_json(root / 'ledger' / 'hashes' / 'LEDGER-CHAIN-2.sha256', {'snapshot_sha256': snap2_digest, 'snapshot_path': 'ledger/snapshots/two.json'})
    write_json(root / 'ledger' / 'ledger_index.json', {
        'schema_version': 'ledger-index.v1',
        'total_entries': 3,
        'last_entry': 'LEDGER-CHAIN-2',
        'last_entry_sha256': current2_digest,
        'operations': {},
    })
    return root


def test_ledger_index_verification_and_tamper_detection(tmp_path):
    root = make_index_repo(tmp_path)
    try:
        result = verify_mod.verify(root)
        assert result['ok'] is True
        assert result['index_status'] == 'current verified index'
        assert result['ledger_entries'] == 3
        assert result['legacy_unchained_entries'] == 1
        assert result['chained_entries'] == 2

        index_path = root / 'ledger' / 'ledger_index.json'
        base = json.loads(index_path.read_text(encoding='utf-8'))

        cases = [
            ({'total_entries': 4}, 'total_entries mismatch'),
            ({'operations': {'write_file': 1}}, 'operation counters mismatch'),
            ({'last_entry': 'LEDGER-NOT-TAIL'}, 'does not point to tail record'),
            ({'last_entry_sha256': '0' * 64}, 'last_entry_sha256 mismatch'),
            ({'total_entries': 2, 'last_entry': 'LEDGER-CHAIN-1'}, 'does not point to tail record'),
            ({'schema_version': 'ledger-index.v9'}, 'unsupported schema_version'),
        ]
        for patch, expected in cases:
            index_path.write_text(json.dumps({**base, **patch}, indent=2, sort_keys=True), encoding='utf-8')
            result = verify_mod.verify(root)
            assert result['ok'] is False
            assert any(expected in error for error in result['errors'])

        index_path.unlink()
        result = verify_mod.verify(root)
        assert result['ok'] is False
        assert any('missing ledger index' in error for error in result['errors'])

        index_path.write_text('{', encoding='utf-8')
        result = verify_mod.verify(root)
        assert result['ok'] is False
        assert any('malformed ledger index' in error for error in result['errors'])
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_legacy_manifest_and_generated_json_grandfathering(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    manifest_path = tmp_path / 'schemas' / 'artifacts' / 'legacy_artifacts_manifest.json'
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    file_path = tmp_path / 'clients' / 'CASE-LEGACY-001' / 'case.json'
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text('{"hello":"world"}', encoding='utf-8')
    digest = sha_bytes(file_path.read_bytes())
    write_json(manifest_path, {
        'schema_version': 'legacy_artifacts_manifest.v1',
        'generated_at': '2026-07-11T00:00:00+00:00',
        'policy': 'test',
        'grandfathered_files': [
            {
                'path': 'clients/CASE-LEGACY-001/case.json',
                'sha256': digest,
                'grandfathered_at': '2026-07-11T00:00:00+00:00',
                'reason': 'fixture',
            }
        ],
    })
    allowlist = validate_json_mod.load_legacy_manifest()
    assert 'clients/CASE-LEGACY-001/case.json' in allowlist

    monkeypatch.setattr(sys, 'argv', ['validate_generated_json.py'])
    with redirect_stdout(io.StringIO()) as captured:
        assert validate_json_mod.main() == 0
    assert 'grandfathered legacy unversioned skipped=1' in captured.getvalue()

    file_path.write_text('{"hello":"world!"}', encoding='utf-8')
    monkeypatch.setattr(sys, 'argv', ['validate_generated_json.py'])
    with redirect_stdout(io.StringIO()) as captured:
        assert validate_json_mod.main() == 1
    assert 'grandfathered file digest mismatch' in captured.getvalue()

    file_path.write_text('{"hello":"world"}', encoding='utf-8')
    other_path = tmp_path / 'clients' / 'CASE-NEW-001' / 'case.json'
    other_path.parent.mkdir(parents=True, exist_ok=True)
    other_path.write_text('{"hello":"world"}', encoding='utf-8')
    monkeypatch.setattr(sys, 'argv', ['validate_generated_json.py'])
    with redirect_stdout(io.StringIO()) as captured:
        assert validate_json_mod.main() == 1
    assert 'missing schema_version and not present in legacy_artifacts_manifest.json' in captured.getvalue()


def test_command_center_validation_accepts_current_format(tmp_path):
    path = tmp_path / 'command_center.json'
    path.write_text(json.dumps({
        'schema_version': 'command_center.v2',
        'dashboard_mode': 'aggregate',
        'generated_at': datetime.now(UTC).isoformat(),
        'run_id': 'aggregate',
        'cases': [],
    }), encoding='utf-8')
    validate_command_center(path)
    path.write_text(json.dumps({
        'dashboard_mode': 'aggregate',
        'generated_at': datetime.now(UTC).isoformat(),
        'run_id': 'aggregate',
        'cases': [],
    }), encoding='utf-8')
    with pytest.raises(SchemaValidationError):
        validate_command_center(path)


def test_case_lock_stale_dead_active_and_malformed(monkeypatch, tmp_path):
    lock_path = tmp_path / 'case.lock'
    stale_payload = {
        'schema_version': 'case_lock.v1',
        'case_id': 'CASE-LOCK-001',
        'pid': 999999,
        'hostname': 'host',
        'created_at': (datetime.now(UTC) - timedelta(hours=2)).isoformat(),
        'process_start_marker': '999999:1',
    }
    lock_path.write_text(json.dumps(stale_payload), encoding='utf-8')
    lock = CaseLock(lock_path, case_id='CASE-LOCK-001', timeout_seconds=1)
    monkeypatch.setattr(lock, '_pid_is_alive', lambda _pid: False)
    with lock:
        assert lock_path.exists()
    assert not lock_path.exists()

    lock_path.write_text(json.dumps(stale_payload), encoding='utf-8')
    lock = CaseLock(lock_path, case_id='CASE-LOCK-001', timeout_seconds=1)
    monkeypatch.setattr(lock, '_pid_is_alive', lambda _pid: True)
    with pytest.raises(CaseStartConflictError, match='active process'), lock:
        pass

    lock_path.write_text('{', encoding='utf-8')
    lock = CaseLock(lock_path, case_id='CASE-LOCK-001', timeout_seconds=1)
    with pytest.raises(CaseStartConflictError, match='malformed case lock file'), lock:
        pass


def test_confidential_guard_blocks_policy_paths_and_allowlisted_grandfathered_file(tmp_path, monkeypatch):
    manifest_path = tmp_path / 'schemas' / 'artifacts' / 'legacy_artifacts_manifest.json'
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    allowed_path = tmp_path / 'allowed.json'
    allowed_path.write_text('{"ok":true}', encoding='utf-8')
    allowed_digest = sha_bytes(allowed_path.read_bytes())
    write_json(manifest_path, {
        'schema_version': 'legacy_artifacts_manifest.v1',
        'generated_at': '2026-07-11T00:00:00+00:00',
        'policy': 'test',
        'grandfathered_files': [
            {
                'path': 'allowed.json',
                'sha256': allowed_digest,
                'grandfathered_at': '2026-07-11T00:00:00+00:00',
                'reason': 'fixture',
            }
        ],
    })
    monkeypatch.setattr(confidential_guard_mod, 'LEGACY_MANIFEST', manifest_path)
    allowlist = confidential_guard_mod.load_legacy_allowlist()
    assert allowlist['allowed.json']['sha256'] == allowed_digest
    assert confidential_guard_mod.blocked_reason('clients/CASE-123/case.json')
    assert confidential_guard_mod.blocked_reason('artifacts/court/CASE-123/complaint_draft.json')
    assert confidential_guard_mod.blocked_reason('artifacts/notion/runs/run-123/command_center.json')
    assert confidential_guard_mod.blocked_reason('clients/CASE-123/case.json') is not None
    assert confidential_guard_mod.blocked_reason('docs/readme.md') is None

"""Tests for Gate 3 evidence manifest freeze and amendment workflow."""
import json
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


def isolated_env(tmp_base: Path) -> dict:
    """Build env vars that redirect all Gate 3 paths under a temp directory."""
    gate3 = tmp_base / "gate-3"
    evidence = gate3 / "evidence"
    evidence.mkdir(parents=True)

    # Create a fake acceptance report
    (gate3 / "GATE3_ACCEPTANCE_REPORT.md").write_text("# Report\n")

    # Create a fake migrations dir with one file
    versions = tmp_base / "versions"
    versions.mkdir()
    (versions / "000000000000_fake.py").write_text("# fake\n")

    env = os.environ.copy()
    env["GATE3_EVIDENCE_ROOT"] = str(evidence)
    env["GATE3_REPORT_PATH"] = str(gate3 / "GATE3_ACCEPTANCE_REPORT.md")
    env["GATE3_MANIFEST_PATH"] = str(gate3 / "gate-3-evidence-manifest.json")
    env["GATE3_FREEZE_RECORD_PATH"] = str(gate3 / "GATE3_FREEZE_RECORD.json")
    env["GATE3_AMENDMENTS_DIR"] = str(gate3 / "amendments")
    env["GATE3_MIGRATIONS_DIR"] = str(versions)
    return env, gate3


@pytest.fixture
def isolated_gate3_dir():
    """Create an isolated fake Gate 3 directory structure for freeze/amendment tests."""
    base_tmp = Path(".gate3-test-tmp")
    base_tmp.mkdir(exist_ok=True)
    tmp_path = Path(tempfile.mkdtemp(dir=str(base_tmp)))
    env, gate3 = isolated_env(tmp_path)
    yield tmp_path, env, gate3
    shutil.rmtree(tmp_path, ignore_errors=True)


def run_script(env: dict, args: list) -> tuple:
    script = Path("scripts/generate_gate3_manifest.py").resolve()
    result = subprocess.run(
        [sys.executable, str(script)] + args,
        capture_output=True,
        text=True,
        cwd=str(Path(".").resolve()),
        env=env,
    )
    return result.returncode, result.stdout, result.stderr


def test_initial_generation_succeeds(isolated_gate3_dir):
    tmp_path, env, gate3 = isolated_gate3_dir
    freeze = gate3 / "GATE3_FREEZE_RECORD.json"
    manifest = gate3 / "gate-3-evidence-manifest.json"

    assert not freeze.exists()
    rc, stdout, stderr = run_script(env, [])
    assert rc == 0, f"stdout={stdout}\nstderr={stderr}"
    assert freeze.exists()
    assert manifest.exists()
    freeze_data = json.loads(freeze.read_text())
    assert freeze_data["regeneration_prohibited"] is True
    assert freeze_data["amendment"] is None


def test_second_normal_generation_fails(isolated_gate3_dir):
    tmp_path, env, gate3 = isolated_gate3_dir
    run_script(env, [])

    rc, stdout, stderr = run_script(env, [])
    assert rc == 1
    assert "freeze record already exists" in stderr.lower()
    assert "Regeneration is prohibited" in stderr


def test_amendment_generation_succeeds_with_identifier_and_reason(isolated_gate3_dir):
    tmp_path, env, gate3 = isolated_gate3_dir
    run_script(env, [])
    freeze_data = json.loads((gate3 / "GATE3_FREEZE_RECORD.json").read_text())
    hash1 = freeze_data["authoritative_manifest_sha256"]

    rc, stdout, stderr = run_script(env, ["--amendment", "GATE3-AMENDMENT-002", "--reason", "Add new evidence"])
    assert rc == 0, f"stdout={stdout}\nstderr={stderr}"

    freeze_data = json.loads((gate3 / "GATE3_FREEZE_RECORD.json").read_text())
    assert freeze_data["supersedes_manifest_sha256"] == hash1
    assert freeze_data["amendment"] == "GATE3-AMENDMENT-002"
    assert freeze_data["authoritative_manifest_sha256"] != hash1
    assert (gate3 / "amendments" / "GATE3-AMENDMENT-002.json").exists()


def test_amendment_without_reason_fails(isolated_gate3_dir):
    tmp_path, env, gate3 = isolated_gate3_dir
    run_script(env, [])

    rc, stdout, stderr = run_script(env, ["--amendment", "GATE3-AMENDMENT-002"])
    assert rc == 1
    assert "--reason is required" in stderr


def test_amendment_preserves_prior_digest(isolated_gate3_dir):
    tmp_path, env, gate3 = isolated_gate3_dir
    run_script(env, [])
    freeze_data = json.loads((gate3 / "GATE3_FREEZE_RECORD.json").read_text())
    prior_digest = freeze_data["authoritative_manifest_sha256"]

    rc, stdout, stderr = run_script(env, ["--amendment", "GATE3-AMENDMENT-002", "--reason", "Test"])
    assert rc == 0, f"stdout={stdout}\nstderr={stderr}"
    freeze_data = json.loads((gate3 / "GATE3_FREEZE_RECORD.json").read_text())
    assert freeze_data["supersedes_manifest_sha256"] == prior_digest
    amendment = json.loads((gate3 / "amendments" / "GATE3-AMENDMENT-002.json").read_text())
    assert amendment["previous_manifest_hash"] == prior_digest


def test_authoritative_freeze_record_updates_only_through_amendment(isolated_gate3_dir):
    tmp_path, env, gate3 = isolated_gate3_dir
    run_script(env, [])

    # Direct ordinary regeneration fails
    rc, _, _ = run_script(env, [])
    assert rc == 1

    # Amendment succeeds and updates freeze record
    rc, _, _ = run_script(env, ["--amendment", "GATE3-AMENDMENT-002", "--reason", "Update"])
    assert rc == 0
    freeze_data = json.loads((gate3 / "GATE3_FREEZE_RECORD.json").read_text())
    assert freeze_data["amendment"] == "GATE3-AMENDMENT-002"


def test_amendment_without_identifier_fails_after_freeze(isolated_gate3_dir):
    """--reason without --amendment must fail after freeze."""
    tmp_path, env, gate3 = isolated_gate3_dir
    run_script(env, [])

    sentinel = gate3 / "gate-3-evidence-manifest.json"
    digest_before = hashlib.sha256(sentinel.read_bytes()).hexdigest()

    rc, stdout, stderr = run_script(env, ["--reason", "test reason without amendment id"])
    assert rc == 1
    assert "--amendment is required" in stderr

    digest_after = hashlib.sha256(sentinel.read_bytes()).hexdigest()
    assert digest_after == digest_before, "manifest must not be modified when amendment id is missing"


def test_existing_evidence_not_silently_overwritten(isolated_gate3_dir):
    """Amendment mode must not overwrite raw evidence files that already exist."""
    tmp_path, env, gate3 = isolated_gate3_dir
    run_script(env, [])

    evidence = gate3 / "evidence"
    raw = evidence / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    sentinel = raw / "sentinel.txt"
    sentinel.write_text("DO NOT OVERWRITE")

    # Capture the initial manifest digest
    manifest_before = hashlib.sha256((gate3 / "gate-3-evidence-manifest.json").read_bytes()).hexdigest()

    # Run a controlled amendment; raw evidence should be untouched
    rc, stdout, stderr = run_script(env, ["--amendment", "GATE3-AMENDMENT-002", "--reason", "Prove evidence preservation"])
    assert rc == 0, f"stdout={stdout}\nstderr={stderr}"

    # Sentinel must survive
    assert sentinel.exists()
    assert sentinel.read_text() == "DO NOT OVERWRITE"

    # Manifest must change (it is the manifest being amended), but prior digest retained
    freeze = json.loads((gate3 / "GATE3_FREEZE_RECORD.json").read_text())
    assert freeze["supersedes_manifest_sha256"] == manifest_before
    assert freeze["authoritative_manifest_sha256"] != manifest_before

    # Unexpected file replacement should not happen: no file named like the sentinel was overwritten
    assert (gate3 / "amendments" / "GATE3-AMENDMENT-002.json").exists()

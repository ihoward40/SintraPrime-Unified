"""GOD-1X execution boundary tests: environment, filesystem, redaction, tree kill.

Phases 4 (env boundary / no secret inheritance), 5 (fs scope, traversal,
escape rejection), 8 (process-tree termination), 10 (output redaction).
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from swarm_runtime.governed_execution import (
    ExecutionRequest,
    build_governed_environment,
    check_filesystem_scope,
    normalize_path,
    path_within_scopes,
    redact_secrets,
    terminate_process_tree,
)


def test_env_no_secret_inheritance_by_default() -> None:
    parent = {
        "PATH": "/usr/bin",
        "GITHUB_TOKEN": "ghp_fake_token_12345",
        "OPENAI_API_KEY": "sk-fake",
        "AWS_SECRET_ACCESS_KEY": "fake_secret",
        "DATABASE_URL": "postgresql://u:p@h/db",
    }
    req = ExecutionRequest(
        execution_request_id="R1", mission_id="M1", swarm_id="S1", task_id="T1",
        agent_id="A1", authority_id="AUTH1", context_package_id="CTX1",
        role_id="code_search", working_directory=".", timeout_seconds=30,
        effect_class="read_only_inspection",
    )
    env, check = build_governed_environment(req, parent_env=parent)
    assert check["clean"], check
    for secret in ("GITHUB_TOKEN", "OPENAI_API_KEY", "AWS_SECRET_ACCESS_KEY", "DATABASE_URL"):
        assert secret not in env, f"{secret} leaked into worker env"


def test_env_leased_secret_propagated() -> None:
    parent = {
        "PATH": "/usr/bin",
        "GITHUB_TOKEN": "ghp_fake_token_12345",
        "OPENAI_API_KEY": "sk-fake",
    }
    req = ExecutionRequest(
        execution_request_id="R1", mission_id="M1", swarm_id="S1", task_id="T1",
        agent_id="A1", authority_id="AUTH1", context_package_id="CTX1",
        role_id="code_search", working_directory=".", timeout_seconds=30,
        effect_class="read_only_inspection", leased_env_vars=["GITHUB_TOKEN"],
    )
    env, check = build_governed_environment(req, parent_env=parent)
    assert "GITHUB_TOKEN" in env
    assert "OPENAI_API_KEY" not in env
    assert check["clean"], check


def test_fs_scope_inside_workdir_allowed(tmp_path: Path) -> None:
    req = ExecutionRequest(
        execution_request_id="R1", mission_id="M1", swarm_id="S1", task_id="T1",
        agent_id="A1", authority_id="AUTH1", context_package_id="CTX1",
        role_id="builder", working_directory=str(tmp_path), timeout_seconds=30,
        effect_class="build_execution",
        write_paths=[str(tmp_path / "out")], owned_files=[str(tmp_path / "out" / "a.txt")],
        read_paths=[str(tmp_path)],
    )
    ok, reason = check_filesystem_scope(req, str(tmp_path))
    assert ok, reason


def test_fs_scope_path_escape_denied(tmp_path: Path) -> None:
    outside = tmp_path.parent
    req = ExecutionRequest(
        execution_request_id="R1", mission_id="M1", swarm_id="S1", task_id="T1",
        agent_id="A1", authority_id="AUTH1", context_package_id="CTX1",
        role_id="builder", working_directory=str(tmp_path), timeout_seconds=30,
        effect_class="build_execution",
        read_paths=[str(tmp_path)],
        write_paths=[str(tmp_path / "out"), str(outside / "escape.txt")],
        owned_files=[str(outside / "escape.txt")],
    )
    ok, reason = check_filesystem_scope(req, str(tmp_path))
    assert not ok
    assert reason.startswith("PATH_ESCAPE"), reason


def test_fs_scope_prohibited_path_denied(tmp_path: Path) -> None:
    secret_dir = tmp_path / "secrets"
    secret_dir.mkdir()
    target = tmp_path / "out"
    req = ExecutionRequest(
        execution_request_id="R1", mission_id="M1", swarm_id="S1", task_id="T1",
        agent_id="A1", authority_id="AUTH1", context_package_id="CTX1",
        role_id="builder", working_directory=str(tmp_path), timeout_seconds=30,
        effect_class="build_execution",
        read_paths=[str(tmp_path)],
        write_paths=[str(target)],
        owned_files=[str(secret_dir / "leak.txt")],
        prohibited_paths=[str(secret_dir)],
    )
    ok, reason = check_filesystem_scope(req, str(tmp_path))
    assert not ok
    assert reason.startswith("PROHIBITED_PATH"), reason


def test_redact_secrets_scrubs_output() -> None:
    raw = "connect using ghp_abcdefghijklmnopqrstuvwxyz and AKIA1234567890ABCDEF"
    out = redact_secrets(raw)
    assert "ghp_" not in out
    assert "AKIA" not in out
    assert "[REDACTED]" in out


def test_redact_secrets_preserves_ordinary_text() -> None:
    raw = "worker completed 42 files in 3.1s"
    assert redact_secrets(raw) == raw


def test_process_tree_termination_kills_descendants(tmp_path: Path) -> None:
    hb = tmp_path / "hb.txt"
    script = tmp_path / "child.py"
    script.write_text(
        "import time, pathlib\n"
        "p = pathlib.Path(__file__).parent / 'hb.txt'\n"
        "while True:\n"
        "    p.write_text(str(time.time()))\n"
        "    time.sleep(0.3)\n"
    )
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    proc = subprocess.Popen(
        [sys.executable, str(script)],
        cwd=str(tmp_path),
        start_new_session=(os.name != "nt"),
        creationflags=flags,
    )
    time.sleep(1.0)
    reason = terminate_process_tree(proc)
    assert reason  # non-empty disposition
    # Parent must have exited
    assert proc.poll() is not None
    # Heartbeat must freeze (child killed, not just parent)
    m1 = float(hb.read_text())
    time.sleep(1.2)
    m2 = float(hb.read_text())
    assert m1 == m2, "child process survived termination — tree kill failed"


def test_path_within_scopes_basic() -> None:
    base = Path("/repo")
    assert path_within_scopes("/repo/a/b.txt", ["/repo/a"], str(base))
    assert not path_within_scopes("/repo/c/b.txt", ["/repo/a"], str(base))


def test_normalize_path_is_absolute() -> None:
    p = normalize_path("rel/file.txt", base="/repo")
    assert p.is_absolute()

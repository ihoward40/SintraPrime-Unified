"""SP-GOD1X-OS-NETWORK-SANDBOX-001 enforcement tests.

Proves:
  * networked execution class is denied (policy layer intact)
  * shell-based network escape is denied (shell requires explicit authority)
  * env-based proxy escape is denied (proxy vars stripped from worker env)
  * sandbox unavailable fails closed (os_enforced w/o capability => DENY)
  * CI fallback (default) does NOT claim OS enforcement
  * receipts distinguish policy-enforced vs OS-enforced/unavailable denial
  * container network=none asserts OS-level containment
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from swarm_runtime.controller import SwarmController
from swarm_runtime.governed_execution import (
    AuthorityEnvelope,
    ExecutionAdmissionGate,
    ExecutionClass,
    ExecutionRequest,
)
from swarm_runtime.network_sandbox import (
    PROXY_ENV_VARS,
    NetworkSandbox,
    NetworkSandboxMode,
)

REPO = Path(__file__).resolve().parents[2]
WORKBASE = REPO / ".gov_integration_tmp"

WORKDIR: Path = REPO  # set per-test-run by the autouse fixture below


@pytest.fixture(autouse=True)
def _gov_workdir_fixture() -> None:
    global WORKDIR
    WORKBASE.mkdir(parents=True, exist_ok=True)
    d = Path(tempfile.mkdtemp(prefix="netsb_", dir=str(WORKBASE)))
    WORKDIR = d
    yield
    shutil.rmtree(d, ignore_errors=True)


def _env() -> AuthorityEnvelope:
    return AuthorityEnvelope(
        mission_id="M1", swarm_id="S1", task_id="T1", agent_id="cs1",
        authority_id="A1", role_id="R1", context_package_id="C1",
        mission_active=True, swarm_authorized=True,
        task_ready=True, agent_authorized=True,
        authority_valid=True, context_valid=True,
        role_allowed=True, resource_allowed=True, revoked=False,
    )


def _safe_request(work: Path, effect_class: str = "read_only_inspection") -> ExecutionRequest:
    return ExecutionRequest(
        execution_request_id="req-1", mission_id="M1", swarm_id="S1",
        task_id="T1", agent_id="cs1", authority_id="A1",
        context_package_id="C1", role_id="R1",
        working_directory=str(work), timeout_seconds=120,
        effect_class=effect_class, worker_class="CodeSearchWorker",
        task_params={"target": "swarm_runtime"}, artifact_path="findings.json",
        owned_files=[str(work / "findings.json")],
        read_paths=[str(work)], write_paths=[str(work / "findings.json")],
    )


def _set_env(**kw):
    saved = {}
    for k, v in kw.items():
        key = "SWARM_NETWORK_" + k
        saved[key] = os.environ.get(key)
        os.environ[key] = v
    return saved


def _restore_env(saved) -> None:
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def test_policy_only_default_enforcement() -> None:
    sb = NetworkSandbox.from_config()
    assert sb.mode is NetworkSandboxMode.POLICY_ONLY
    r = sb.resolve()
    assert r["fail_closed"] is False
    assert r["enforcement_level"] == "policy_enforced"
    assert r["available"] is True
    assert sb.certification_status(r) == "policy_only"


def test_proxy_env_strip_removes_known_vars() -> None:
    sb = NetworkSandbox.from_config()
    dirty = {
        "PATH": "/usr/bin", "HTTP_PROXY": "http://evil:8080",
        "HTTPS_PROXY": "https://evil:8443", "ALL_PROXY": "socks://evil:1080",
        "no_proxy": "localhost", "GIT_PROXY_COMMAND": "nc -X",
        "PIP_INDEX_URL": "http://evil/simple",
    }
    clean = sb.strip_proxy_env(dirty)
    for var in PROXY_ENV_VARS:
        assert var not in clean, f"{var} was not stripped"
    assert clean["PATH"] == "/usr/bin"


def test_os_enforced_unavailable_fails_closed() -> None:
    saved = _set_env(ENFORCEMENT="os_enforced")
    try:
        sb = NetworkSandbox.from_config()
        assert sb.mode is NetworkSandboxMode.OS_ENFORCED
        r = sb.resolve()
        # On Windows and unprivileged Linux CI the OS capability is absent.
        assert r["fail_closed"] is True
        assert r["enforcement_level"] == "unavailable_fail_closed"
        assert r["available"] is False
    finally:
        _restore_env(saved)


def test_container_network_none_asserts_os() -> None:
    saved = _set_env(ENFORCEMENT="container_network_none", CONTAINER="none")
    try:
        sb = NetworkSandbox.from_config()
        r = sb.resolve()
        assert r["effective_level"] == "os"
        assert r["enforcement_level"] == "os_enforced"
        assert r["available"] is True
        assert sb.certification_status(r) == "certified"
    finally:
        _restore_env(saved)


def test_unknown_enforcement_fails_closed() -> None:
    saved = _set_env(ENFORCEMENT="not_a_real_mode")
    try:
        sb = NetworkSandbox.from_config()
        assert sb.mode is NetworkSandboxMode.UNAVAILABLE_FAIL_CLOSED
        r = sb.resolve()
        assert r["fail_closed"] is True
    finally:
        _restore_env(saved)


def test_networked_execution_class_denied_with_sandbox() -> None:
    gate = ExecutionAdmissionGate()
    req = _safe_request(WORKDIR, effect_class=ExecutionClass.NETWORKED_EXECUTION.value)
    decision = gate.admit(req, _env())
    assert decision.allowed is False
    assert any(c.startswith("EXECUTION_CLASS_DENIED") for c in decision.reasons)


def test_shell_network_escape_denied() -> None:
    gate = ExecutionAdmissionGate()
    req = _safe_request(WORKDIR)
    req.shell = True  # would allow a `curl` network escape
    req.environment_policy = {}  # no explicit shell authority
    decision = gate.admit(req, _env())
    assert decision.allowed is False
    assert "SHELL_EXECUTION_REQUIRES_EXPLICIT_AUTHORITY" in decision.reasons


def test_launch_governed_policy_receipt_level() -> None:
    ctrl = SwarmController(swarm_id="net1", repo_path=str(REPO), run_dir=str(WORKDIR / "run"))
    req = _safe_request(WORKDIR)
    res = ctrl.launch_governed(req, _env())
    assert res.status == "RUNNING"
    assert res.network_enforcement_level == "policy_enforced"
    ctrl.wait()
    receipt_path = ctrl.store.worker_dir("cs1") / "governed_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["result"]["network_enforcement_level"] == "policy_enforced"


def test_launch_governed_os_unavailable_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("swarm_runtime.network_sandbox._probe_os_netns", lambda: False)
    saved = _set_env(ENFORCEMENT="os_enforced")
    try:
        ctrl = SwarmController(swarm_id="net2", repo_path=str(REPO), run_dir=str(WORKDIR / "run"))
        req = _safe_request(WORKDIR)
        res = ctrl.launch_governed(req, _env())
        assert res.status == "DENIED"
        assert "NETWORK_SANDBOX_UNAVAILABLE" in res.rejection_reasons
        assert res.network_enforcement_level == "unavailable_fail_closed"
    finally:
        _restore_env(saved)


def test_receipt_distinguishes_levels() -> None:
    c1 = SwarmController(swarm_id="net3a", repo_path=str(REPO), run_dir=str(WORKDIR / "run_a"))
    r1 = c1.launch_governed(_safe_request(WORKDIR / "a"), _env())
    c1.wait()

    saved = _set_env(ENFORCEMENT="os_enforced")
    try:
        c2 = SwarmController(swarm_id="net3b", repo_path=str(REPO), run_dir=str(WORKDIR / "run_b"))
        r2 = c2.launch_governed(_safe_request(WORKDIR / "b"), _env())
    finally:
        _restore_env(saved)

    assert r1.network_enforcement_level == "policy_enforced"
    assert r2.network_enforcement_level == "unavailable_fail_closed"
    assert r1.network_enforcement_level != r2.network_enforcement_level
    # Neither case may falsely claim OS enforcement.
    assert r1.network_enforcement_level != "os_enforced"
    assert r2.network_enforcement_level != "os_enforced"

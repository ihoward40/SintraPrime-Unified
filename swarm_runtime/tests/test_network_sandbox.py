"""SP-GOD1X-OS-NETWORK-SANDBOX-001 enforcement tests."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

import swarm_runtime.network_sandbox as network_sandbox
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


def _env(agent_id: str = "cs1", **overrides: bool) -> AuthorityEnvelope:
    base = {
        "mission_id": "M1",
        "swarm_id": "S1",
        "task_id": "T1",
        "agent_id": agent_id,
        "authority_id": "A1",
        "role_id": "R1",
        "context_package_id": "C1",
        "mission_active": True,
        "swarm_authorized": True,
        "task_ready": True,
        "agent_authorized": True,
        "authority_valid": True,
        "context_valid": True,
        "role_allowed": True,
        "resource_allowed": True,
        "revoked": False,
    }
    base.update(overrides)
    return AuthorityEnvelope(**base)


def _safe_request(work: Path, agent_id: str = "cs1", effect_class: str = "read_only_inspection") -> ExecutionRequest:
    return ExecutionRequest(
        execution_request_id=f"req-{agent_id}",
        mission_id="M1",
        swarm_id="S1",
        task_id="T1",
        agent_id=agent_id,
        authority_id="A1",
        context_package_id="C1",
        role_id="R1",
        working_directory=str(work),
        timeout_seconds=120,
        effect_class=effect_class,
        worker_class="CodeSearchWorker",
        task_params={"target": "swarm_runtime"},
        artifact_path="findings.json",
        owned_files=[str(work / "findings.json")],
        read_paths=[str(work)],
        write_paths=[str(work / "findings.json")],
    )


def _set_env(**kw):
    saved = {}
    for k, v in kw.items():
        key = "SWARM_NETWORK_" + k
        saved[key] = os.environ.get(key)
        if v is None:
            os.environ.pop(key, None)
        else:
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


@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        ("policy", NetworkSandboxMode.POLICY_ONLY),
        ("policy_only", NetworkSandboxMode.POLICY_ONLY),
        ("os", NetworkSandboxMode.OS_ENFORCED),
        ("os_enforced", NetworkSandboxMode.OS_ENFORCED),
        ("container", NetworkSandboxMode.CONTAINER_NETWORK_NONE),
        ("container_network_none", NetworkSandboxMode.CONTAINER_NETWORK_NONE),
    ],
)
def test_documented_aliases_are_accepted(configured: str, expected: NetworkSandboxMode) -> None:
    saved = _set_env(ENFORCEMENT=configured)
    try:
        assert NetworkSandbox.from_config().mode is expected
    finally:
        _restore_env(saved)


def test_proxy_env_strip_removes_known_vars() -> None:
    sb = NetworkSandbox.from_config()
    dirty = {
        "PATH": "/usr/bin",
        "HTTP_PROXY": "http://evil:8080",
        "HTTPS_PROXY": "https://evil:8443",
        "ALL_PROXY": "socks://evil:1080",
        "NO_PROXY": "localhost",
        "GIT_PROXY_COMMAND": "nc -X",
        "PIP_INDEX_URL": "http://evil/simple",
        "npm_config_https_proxy": "https://evil/npm",
    }
    clean = sb.strip_proxy_env(dirty)
    for var in PROXY_ENV_VARS:
        assert var not in clean, f"{var} was not stripped"
    assert clean["PATH"] == "/usr/bin"


def test_probe_uses_isolated_python_and_sanitized_env(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = kwargs["env"]

        class _Result:
            returncode = 0

        return _Result()

    monkeypatch.setattr(network_sandbox.platform, "system", lambda: "Linux")
    monkeypatch.setattr(network_sandbox.subprocess, "run", _fake_run)
    monkeypatch.setenv("PYTHONPATH", "/tmp/evil")
    monkeypatch.setenv("LD_PRELOAD", "/tmp/malice.so")
    monkeypatch.setenv("HOME", "/home/copilot")
    assert network_sandbox._probe_os_netns() is True
    assert captured["cmd"][1:3] == ["-I", "-S"]
    env = captured["env"]
    assert "PYTHONPATH" not in env
    assert "LD_PRELOAD" not in env
    assert env["HOME"] == "/home/copilot"


def test_os_enforced_unavailable_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    saved = _set_env(ENFORCEMENT="os_enforced")
    monkeypatch.setattr(network_sandbox, "_probe_os_netns", lambda: False)
    try:
        sb = NetworkSandbox.from_config()
        assert sb.mode is NetworkSandboxMode.OS_ENFORCED
        r = sb.resolve()
        assert r["fail_closed"] is True
        assert r["enforcement_level"] == "unavailable_fail_closed"
        assert r["available"] is False
    finally:
        _restore_env(saved)


@pytest.mark.parametrize("system_name", ["Windows", "Darwin"])
def test_non_linux_os_enforced_fails_closed(system_name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    saved = _set_env(ENFORCEMENT="os_enforced")
    monkeypatch.setattr(network_sandbox.platform, "system", lambda: system_name)
    try:
        r = NetworkSandbox.from_config().resolve()
        assert r["fail_closed"] is True
        assert r["available"] is False
    finally:
        _restore_env(saved)


def test_python311_without_os_unshare_still_uses_shared_hook(monkeypatch: pytest.MonkeyPatch) -> None:
    saved = _set_env(ENFORCEMENT="os_enforced")
    monkeypatch.setattr(network_sandbox.platform, "system", lambda: "Linux")
    monkeypatch.setattr(network_sandbox, "_probe_os_netns", lambda: True)
    monkeypatch.delattr(network_sandbox.os, "unshare", raising=False)
    try:
        sb = NetworkSandbox.from_config()
        kwargs = sb.popen_kwargs(sb.resolve())
        assert kwargs["preexec_fn"] is network_sandbox._apply_linux_os_sandbox
    finally:
        _restore_env(saved)


def test_container_network_none_requires_verified_boundary() -> None:
    saved = _set_env(ENFORCEMENT="container_network_none", CONTAINER="none", CONTAINER_VERIFIED_BY=None)
    try:
        r = NetworkSandbox.from_config().resolve()
        assert r["fail_closed"] is True
        assert r["verification_component"] == "unverified_container_declaration"
    finally:
        _restore_env(saved)


def test_container_network_none_skips_preexec(monkeypatch: pytest.MonkeyPatch) -> None:
    saved = _set_env(
        ENFORCEMENT="container_network_none",
        CONTAINER="none",
        CONTAINER_VERIFIED_BY="orchestrator",
    )
    monkeypatch.setattr(network_sandbox.platform, "system", lambda: "Linux")
    try:
        sb = NetworkSandbox.from_config()
        resolved = sb.resolve()
        assert resolved["available"] is True
        assert resolved["enforcement_level"] == "os_enforced"
        assert sb.popen_kwargs(resolved) == {}
    finally:
        _restore_env(saved)


def test_namespace_escape_hardening_runs_after_unshare(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    sentinel = object()
    monkeypatch.setattr(network_sandbox.platform, "system", lambda: "Linux")
    monkeypatch.setattr(network_sandbox, "_load_libc", lambda: sentinel)
    monkeypatch.setattr(network_sandbox, "_linux_unshare_netns", lambda libc: calls.append(f"unshare:{libc is sentinel}"))
    monkeypatch.setattr(
        network_sandbox,
        "_linux_drop_namespace_escape_capabilities",
        lambda libc: calls.append(f"drop:{libc is sentinel}"),
    )
    network_sandbox._apply_linux_os_sandbox()
    assert calls == ["unshare:True", "drop:True"]


def test_networked_execution_class_denied_with_sandbox() -> None:
    gate = ExecutionAdmissionGate()
    req = _safe_request(WORKDIR, effect_class=ExecutionClass.NETWORKED_EXECUTION.value)
    decision = gate.admit(req, _env())
    assert decision.allowed is False
    assert any(c.startswith("EXECUTION_CLASS_DENIED") for c in decision.reasons)


def test_shell_network_escape_denied() -> None:
    gate = ExecutionAdmissionGate()
    req = _safe_request(WORKDIR)
    req.shell = True
    req.environment_policy = {}
    decision = gate.admit(req, _env())
    assert decision.allowed is False
    assert "SHELL_EXECUTION_REQUIRES_EXPLICIT_AUTHORITY" in decision.reasons


def test_denied_authority_does_not_probe_before_admission(monkeypatch: pytest.MonkeyPatch) -> None:
    saved = _set_env(ENFORCEMENT="os_enforced")

    def _probe() -> bool:
        raise AssertionError("probe should not run before admission denial")

    monkeypatch.setattr(network_sandbox, "_probe_os_netns", _probe)
    try:
        ctrl = SwarmController(swarm_id="net-deny", repo_path=str(REPO), run_dir=str(WORKDIR / "run"))
        req = _safe_request(WORKDIR)
        res = ctrl.launch_governed(req, _env(revoked=True))
        assert res.status == "DENIED"
        assert "AUTHORITY_REVOKED" in res.rejection_reasons
        assert res.network_enforcement_level == "unobserved"
    finally:
        _restore_env(saved)


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
    saved = _set_env(ENFORCEMENT="os_enforced")
    monkeypatch.setattr(network_sandbox, "_probe_os_netns", lambda: False)
    try:
        ctrl = SwarmController(swarm_id="net2", repo_path=str(REPO), run_dir=str(WORKDIR / "run"))
        req = _safe_request(WORKDIR)
        res = ctrl.launch_governed(req, _env())
        assert res.status == "DENIED"
        assert "NETWORK_SANDBOX_UNAVAILABLE" in res.rejection_reasons
        assert res.network_enforcement_level == "unavailable_fail_closed"
    finally:
        _restore_env(saved)


def test_worker_spawn_failure_becomes_terminal_receipt(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*_args, **_kwargs):
        raise RuntimeError("spawn failed")

    monkeypatch.setattr("swarm_runtime.controller.subprocess.Popen", _boom)
    ctrl = SwarmController(swarm_id="net-fail", repo_path=str(REPO), run_dir=str(WORKDIR / "run"))
    req = _safe_request(WORKDIR, agent_id="boom1")
    res = ctrl.launch_governed(req, _env(agent_id="boom1"))
    assert res.status == "FAILED"
    assert res.termination_reason == "WORKER_LAUNCH_FAILED"
    assert res.rejection_reasons == ["WORKER_LAUNCH_FAILED:spawn failed"]
    assert "boom1" not in ctrl._governed_contexts
    receipt = json.loads((ctrl.store.worker_dir("boom1") / "governed_receipt.json").read_text(encoding="utf-8"))
    assert receipt["result"]["status"] == "FAILED"
    assert receipt["result"]["termination_reason"] == "WORKER_LAUNCH_FAILED"


def test_post_probe_preexec_failure_does_not_claim_os_enforcement(monkeypatch: pytest.MonkeyPatch) -> None:
    saved = _set_env(ENFORCEMENT="os_enforced")
    monkeypatch.setattr(network_sandbox, "_probe_os_netns", lambda: True)

    def _boom(*_args, **_kwargs):
        raise subprocess.SubprocessError("Exception occurred in preexec_fn.")

    monkeypatch.setattr("swarm_runtime.controller.subprocess.Popen", _boom)
    try:
        ctrl = SwarmController(swarm_id="net-preexec", repo_path=str(REPO), run_dir=str(WORKDIR / "run"))
        req = _safe_request(WORKDIR, agent_id="preexec1")
        res = ctrl.launch_governed(req, _env(agent_id="preexec1"))
        assert res.status == "FAILED"
        assert res.network_enforcement_level == "unavailable_fail_closed"
        assert res.rejection_reasons == ["WORKER_LAUNCH_FAILED:Exception occurred in preexec_fn."]
    finally:
        _restore_env(saved)


def test_receipt_distinguishes_levels(monkeypatch: pytest.MonkeyPatch) -> None:
    c1 = SwarmController(swarm_id="net3a", repo_path=str(REPO), run_dir=str(WORKDIR / "run_a"))
    r1 = c1.launch_governed(_safe_request(WORKDIR / "a"), _env())
    c1.wait()

    saved = _set_env(ENFORCEMENT="os_enforced")
    monkeypatch.setattr(network_sandbox, "_probe_os_netns", lambda: False)
    try:
        c2 = SwarmController(swarm_id="net3b", repo_path=str(REPO), run_dir=str(WORKDIR / "run_b"))
        r2 = c2.launch_governed(_safe_request(WORKDIR / "b"), _env())
    finally:
        _restore_env(saved)

    assert r1.network_enforcement_level == "policy_enforced"
    assert r2.network_enforcement_level == "unavailable_fail_closed"
    assert r1.network_enforcement_level != r2.network_enforcement_level


@pytest.mark.skipif(
    os.environ.get("SINTRAPRIME_RUN_NETNS_INTEGRATION") != "1",
    reason="set SINTRAPRIME_RUN_NETNS_INTEGRATION=1 to run host-dependent netns integration",
)
def test_guarded_live_probe_matches_resolution() -> None:
    saved = _set_env(ENFORCEMENT="os_enforced")
    try:
        sandbox = NetworkSandbox.from_config()
        resolved = sandbox.resolve()
        assert resolved["available"] is network_sandbox._probe_os_netns()
    finally:
        _restore_env(saved)

"""Focused tests for the fail-closed applicability helper."""

import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "applicability_gate.py")
spec = importlib.util.spec_from_file_location("applicability_gate", SCRIPT)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def test_recursive_scope_and_dot_prefixed_paths_are_preserved():
    assert gate._matches("portal/services/orders.py", "portal/**") is True
    assert gate._matches(".dockerignore", ".dockerignore") is True
    assert gate._matches(
        ".github/workflows/docker-build.yml",
        ".github/workflows/docker-build.yml",
    ) is True


def test_manual_dispatch_has_a_conservative_subject(monkeypatch):
    sha = "a" * 40
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    monkeypatch.setenv("GITHUB_SHA", sha)
    assert gate._subjects({}) == (sha, sha)


def test_pull_request_uses_three_dot_diff(monkeypatch):
    calls = []

    class Result:
        returncode = 0
        stdout = "portal/services/orders.py\n"
        stderr = ""

    def fake_run(command, **_kwargs):
        calls.append(command)
        return Result()

    monkeypatch.setattr(gate.subprocess, "run", fake_run)
    changed = gate._changed_files("a" * 40, "b" * 40, "pull_request")
    assert changed == ["portal/services/orders.py"]
    assert calls[0][-1] == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa...bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"


def test_push_uses_exact_before_after_endpoints(monkeypatch):
    calls = []

    class Result:
        returncode = 0
        stdout = ".dockerignore\n"
        stderr = ""

    def fake_run(command, **_kwargs):
        calls.append(command)
        return Result()

    monkeypatch.setattr(gate.subprocess, "run", fake_run)
    changed = gate._changed_files("a" * 40, "b" * 40, "push")
    assert changed == [".dockerignore"]
    assert calls[0][-2:] == ["a" * 40, "b" * 40]

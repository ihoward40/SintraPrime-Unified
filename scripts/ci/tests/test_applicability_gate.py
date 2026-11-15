"""Focused tests for the fail-closed applicability helper."""

import importlib.util
import json
import os
import subprocess
import sys

import pytest

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
        stdout = b"portal/services/orders.py\0"
        stderr = b""

    def fake_run(command, **_kwargs):
        calls.append(command)
        return Result()

    monkeypatch.setattr(gate.subprocess, "run", fake_run)
    changed = gate._changed_files("a" * 40, "b" * 40, "pull_request")
    assert changed == ["portal/services/orders.py"]
    assert "-z" in calls[0]
    assert calls[0][-1] == "--"
    assert calls[0][-2] == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa...bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"


def test_push_uses_exact_before_after_endpoints(monkeypatch):
    calls = []

    class Result:
        returncode = 0
        stdout = b".dockerignore\0"
        stderr = b""

    def fake_run(command, **_kwargs):
        calls.append(command)
        return Result()

    monkeypatch.setattr(gate.subprocess, "run", fake_run)
    changed = gate._changed_files("a" * 40, "b" * 40, "push")
    assert changed == [".dockerignore"]
    assert "-z" in calls[0]
    assert calls[0][-1] == "--"
    assert calls[0][-3:-1] == ["a" * 40, "b" * 40]


@pytest.fixture
def git_diff_fixture(tmp_path):
    repo = tmp_path / "repository"
    repo.mkdir()

    def git(*args):
        result = subprocess.run(
            ["git", *args], cwd=repo, check=True, capture_output=True,
        )
        return result.stdout.decode("utf-8").strip()

    git("init", "--quiet")
    git("config", "user.name", "CI regression fixture")
    git("config", "user.email", "ci-fixture@example.invalid")
    git("config", "core.quotePath", "true")
    (repo / "README.md").write_text("fixture\n", encoding="utf-8")
    git("add", "--all")
    git("commit", "--quiet", "-m", "fixture baseline")
    base = git("rev-parse", "HEAD")

    def change(path):
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("changed\n", encoding="utf-8")
        git("add", "--all")
        git("commit", "--quiet", "-m", "fixture change")
        return git("rev-parse", "HEAD")

    return repo, base, change


def _invoke_fixture_gate(tmp_path, repo, base, head, event_name):
    payload = {}
    if event_name == "pull_request":
        payload = {"pull_request": {"base": {"sha": base}, "head": {"sha": head}}}
    elif event_name == "push":
        payload = {"before": base, "after": head}
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(payload), encoding="utf-8")
    receipt_path = tmp_path / "receipt.json"
    env = os.environ.copy()
    env.update(
        GITHUB_EVENT_NAME=event_name,
        GITHUB_EVENT_PATH=str(event_path),
        GITHUB_SHA=head,
        GITHUB_OUTPUT=str(tmp_path / "outputs.txt"),
    )
    result = subprocess.run(
        [
            sys.executable, SCRIPT, "--area", "portal", "--paths", "portal/**",
            "--receipt", str(receipt_path),
        ],
        cwd=repo, env=env, capture_output=True, text=True, encoding="utf-8",
    )
    return result, json.loads(receipt_path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("event_name", ["pull_request", "push"])
@pytest.mark.parametrize("path", ["portal/orders.py", "portal/café.py", "portal/日本語.py"])
def test_real_git_paths_keep_relevant_lane_applicable(tmp_path, git_diff_fixture, event_name, path):
    repo, base, change = git_diff_fixture
    head = change(path)
    result, receipt = _invoke_fixture_gate(tmp_path, repo, base, head, event_name)
    assert result.returncode == 0
    assert receipt["state"] == "applicable"
    assert receipt["changed_files"] == [path]
    assert receipt["matched_files"] == [path]


def test_real_scheduler_only_diff_has_non_applicability_proof(tmp_path, git_diff_fixture):
    repo, base, change = git_diff_fixture
    path = "tests/test_scheduler_executor.py"
    head = change(path)
    result, receipt = _invoke_fixture_gate(tmp_path, repo, base, head, "pull_request")
    assert result.returncode == 0
    assert receipt["state"] == "not_applicable_with_proof"
    assert receipt["base"] == base
    assert receipt["head"] == head
    assert receipt["changed_files"] == [path]
    assert receipt["matched_files"] == []


def test_missing_git_subject_fails_closed(tmp_path, git_diff_fixture):
    repo, _base, change = git_diff_fixture
    head = change("portal/orders.py")
    result, receipt = _invoke_fixture_gate(
        tmp_path, repo, "missing-base-ref", head, "pull_request",
    )
    assert result.returncode != 0
    assert receipt["state"] == "unknown"


def test_unsupported_event_fails_closed(tmp_path, git_diff_fixture):
    repo, base, change = git_diff_fixture
    head = change("portal/orders.py")
    result, receipt = _invoke_fixture_gate(tmp_path, repo, base, head, "schedule")
    assert result.returncode != 0
    assert receipt["state"] == "unknown"


def test_real_manual_dispatch_is_applicable(tmp_path, git_diff_fixture):
    repo, base, change = git_diff_fixture
    head = change("README.md")
    result, receipt = _invoke_fixture_gate(tmp_path, repo, base, head, "workflow_dispatch")
    assert result.returncode == 0
    assert receipt["state"] == "applicable"


def test_nul_records_preserve_whitespace_quotes_and_backslashes(monkeypatch):
    paths = ["portal/with\ttab.py", "portal/with\nnewline.py", 'portal/with"quote.py',
             "portal/with\\backslash.py", "portal/ leading and trailing "]

    class Result:
        returncode = 0
        stdout = ("\0".join(paths) + "\0").encode("utf-8")
        stderr = b""

    monkeypatch.setattr(gate.subprocess, "run", lambda *_args, **_kwargs: Result())
    assert gate._changed_files("a" * 40, "b" * 40, "pull_request") == sorted(paths)


@pytest.mark.parametrize("output", [b"portal/incomplete.py", b"portal/empty.py\0\0", b"portal/\xff.py\0"])
def test_malformed_path_records_fail_closed(monkeypatch, output):
    class Result:
        returncode = 0
        stdout = output
        stderr = b""

    monkeypatch.setattr(gate.subprocess, "run", lambda *_args, **_kwargs: Result())
    with pytest.raises((RuntimeError, UnicodeError)):
        gate._changed_files("a" * 40, "b" * 40, "pull_request")

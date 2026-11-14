"""Regression tests: the smoke runner must not report PASS after a failed pytest run."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

RUNNER_PATH = Path(__file__).resolve().parents[2] / "scripts" / "smoke" / "e2e_skills_smoke.py"


@pytest.fixture
def runner(monkeypatch):
    name = "e2e_skills_smoke_under_test"
    spec = importlib.util.spec_from_file_location(name, RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves string annotations through sys.modules, so register first.
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("pytest_code", "pytest_failed", "repo_truth_passed", "expected"),
    [
        (0, 0, True, "PASS"),
        (0, 1, True, "FAIL"),
        (0, 0, False, "FAIL"),
        (2, 0, True, "FAIL"),  # collection error: nonzero exit, passed tests, no parsed failures
        (1, 0, True, "FAIL"),
        (5, 0, True, "FAIL"),  # pytest "no tests collected"
    ],
    ids=["all-ok", "failed-test", "repo-truth-fail", "collection-error", "exit-1", "no-tests"],
)
def test_overall_requires_zero_exit_code(
    runner, pytest_code, pytest_failed, repo_truth_passed, expected
):
    assert runner._overall(pytest_code, pytest_failed, repo_truth_passed) == expected


def _fake_pytest_run(returncode: int, stdout: str):
    def fake_run(cmd, **_kwargs):
        return subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr="")

    return fake_run


def test_nonzero_pytest_exit_with_passed_tests_fails_the_lane(runner, monkeypatch, tmp_path):
    """Passed tests plus a collection error must exit nonzero and write FAIL."""
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        _fake_pytest_run(2, "3 passed, 1 error in 0.5s\n"),
    )
    monkeypatch.setattr(runner, "_run_repo_truth", lambda: (True, []))
    monkeypatch.setattr(runner, "ARTIFACTS", tmp_path)
    monkeypatch.setattr(runner, "SUMMARY_PATH", tmp_path / "summary.json")
    monkeypatch.setattr(runner, "RECEIPT_PATH", tmp_path / "receipt.txt")
    monkeypatch.setattr(runner, "TIMESTAMP_PATH", tmp_path / "timestamp.txt")
    monkeypatch.setattr(runner, "_short_ref", lambda: "testref")

    assert runner.main() == 1

    summary = (tmp_path / "summary.json").read_text(encoding="utf-8")
    assert '"overall": "FAIL"' in summary
    assert '"pytest_exit_code": 2' in summary
    assert '"pytest_failed": 0' in summary


def test_unwritable_artifacts_fail_the_lane(runner, monkeypatch, tmp_path):
    """If artifacts cannot be written the lane must exit nonzero, not crash or pass."""
    monkeypatch.setattr(runner.subprocess, "run", _fake_pytest_run(0, "3 passed in 0.5s\n"))
    monkeypatch.setattr(runner, "_run_repo_truth", lambda: (True, []))
    monkeypatch.setattr(runner, "ARTIFACTS", tmp_path)
    monkeypatch.setattr(runner, "SUMMARY_PATH", tmp_path / "missing_dir" / "summary.json")
    monkeypatch.setattr(runner, "RECEIPT_PATH", tmp_path / "receipt.txt")
    monkeypatch.setattr(runner, "TIMESTAMP_PATH", tmp_path / "timestamp.txt")
    monkeypatch.setattr(runner, "_short_ref", lambda: "testref")

    assert runner.main() == 1
    assert not (tmp_path / "receipt.txt").exists()


def test_unusable_artifacts_dir_fails_the_lane(runner, monkeypatch, tmp_path):
    """If the artifacts directory cannot be created the lane exits nonzero, no traceback."""
    blocker = tmp_path / "artifacts"
    blocker.write_text("a file where the directory should be", encoding="utf-8")
    monkeypatch.setattr(runner.subprocess, "run", _fake_pytest_run(0, "3 passed in 0.5s\n"))
    monkeypatch.setattr(runner, "_run_repo_truth", lambda: (True, []))
    monkeypatch.setattr(runner, "ARTIFACTS", blocker)
    monkeypatch.setattr(runner, "SUMMARY_PATH", blocker / "summary.json")
    monkeypatch.setattr(runner, "RECEIPT_PATH", blocker / "receipt.txt")
    monkeypatch.setattr(runner, "TIMESTAMP_PATH", blocker / "timestamp.txt")
    monkeypatch.setattr(runner, "_short_ref", lambda: "testref")

    assert runner.main() == 1


def test_unlaunchable_subprocesses_fail_the_lane(runner, monkeypatch, tmp_path):
    """If no subprocess can start, every step degrades to FAIL instead of crashing."""

    def boom(*_args, **_kwargs):
        raise FileNotFoundError("no such executable")

    monkeypatch.setattr(runner.subprocess, "run", boom)
    monkeypatch.setattr(runner, "ARTIFACTS", tmp_path)
    monkeypatch.setattr(runner, "SUMMARY_PATH", tmp_path / "summary.json")
    monkeypatch.setattr(runner, "RECEIPT_PATH", tmp_path / "receipt.txt")
    monkeypatch.setattr(runner, "TIMESTAMP_PATH", tmp_path / "timestamp.txt")

    assert runner._short_ref() == "unknown"
    assert runner.main() == 1

    summary = (tmp_path / "summary.json").read_text(encoding="utf-8")
    assert '"overall": "FAIL"' in summary
    assert '"pytest_exit_code": -1' in summary
    assert '"repo_truth_passed": false' in summary


def test_unreadable_paths_degrade_instead_of_raising(runner, monkeypatch):
    """Filesystem errors from exists()/resolve() must not escape the helpers."""

    def deny(*_args, **_kwargs):
        raise PermissionError("denied")

    with monkeypatch.context() as patched:
        patched.setattr(runner.Path, "exists", deny)
        passed, details = runner._run_repo_truth()
    assert passed is False
    assert details[0]["status"] == "FAIL"
    assert details[0]["detail"] == "PermissionError"

    with monkeypatch.context() as patched:
        patched.setattr(runner.Path, "resolve", deny)
        assert runner._python_executable() == sys.executable


def _seed_pass_artifacts(runner, monkeypatch, tmp_path):
    """Point the runner at tmp_path and leave an earlier PASS run's artifacts there."""
    paths = {
        "SUMMARY_PATH": tmp_path / "summary.json",
        "RECEIPT_PATH": tmp_path / "receipt.txt",
        "TIMESTAMP_PATH": tmp_path / "timestamp.txt",
    }
    monkeypatch.setattr(runner, "ARTIFACTS", tmp_path)
    for attr, path in paths.items():
        monkeypatch.setattr(runner, attr, path)
        path.write_text('{"overall": "PASS"}', encoding="utf-8")
    monkeypatch.setattr(runner.subprocess, "run", _fake_pytest_run(0, "3 passed in 0.5s\n"))
    monkeypatch.setattr(runner, "_run_repo_truth", lambda: (True, []))
    monkeypatch.setattr(runner, "_short_ref", lambda: "testref")
    return list(paths.values())


def _fail_write_for(runner, monkeypatch, filename):
    original = runner.Path.write_text

    def fake_write_text(self, *args, **kwargs):
        if self.name == filename:
            raise OSError("disk full")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(runner.Path, "write_text", fake_write_text)


@pytest.mark.parametrize("failing_file", ["summary.json", "timestamp.txt"])
def test_failed_publish_leaves_no_earlier_pass_artifacts(
    runner, monkeypatch, tmp_path, failing_file
):
    """A write failure must not leave a prior PASS (or a half-written new run) behind."""
    paths = _seed_pass_artifacts(runner, monkeypatch, tmp_path)
    _fail_write_for(runner, monkeypatch, failing_file)

    assert runner.main() == 1
    assert [p.exists() for p in paths] == [False, False, False]


def test_uncleared_artifacts_fail_before_any_check_runs(runner, monkeypatch, tmp_path):
    """If prior evidence cannot be invalidated, no check runs and the lane fails."""
    _seed_pass_artifacts(runner, monkeypatch, tmp_path)
    stuck = tmp_path / "receipt.txt"
    stuck.unlink()
    stuck.mkdir()  # a directory cannot be unlinked as a file
    (stuck / "keep").write_text("x", encoding="utf-8")
    calls = []
    monkeypatch.setattr(runner.subprocess, "run", lambda *args, **_kwargs: calls.append(args))

    assert runner.main() == 1
    assert calls == []


def test_clean_pytest_run_still_passes_the_lane(runner, monkeypatch, tmp_path):
    monkeypatch.setattr(runner.subprocess, "run", _fake_pytest_run(0, "3 passed in 0.5s\n"))
    monkeypatch.setattr(runner, "_run_repo_truth", lambda: (True, []))
    monkeypatch.setattr(runner, "ARTIFACTS", tmp_path)
    monkeypatch.setattr(runner, "SUMMARY_PATH", tmp_path / "summary.json")
    monkeypatch.setattr(runner, "RECEIPT_PATH", tmp_path / "receipt.txt")
    monkeypatch.setattr(runner, "TIMESTAMP_PATH", tmp_path / "timestamp.txt")
    monkeypatch.setattr(runner, "_short_ref", lambda: "testref")

    assert runner.main() == 0

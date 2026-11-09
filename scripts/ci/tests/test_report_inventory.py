"""Unit tests for scripts/ci/report_test_inventory.py parser.

Tests are deterministic and do not require a real pytest collection run.
"""

import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "report_test_inventory.py")
spec = importlib.util.spec_from_file_location("report_test_inventory", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_parse_per_file_normal():
    out = "tests/test_a.py: 10\ntests/test_b.py: 20\n"
    r = mod.parse_collect_output(out)
    assert r["per_file_collected"] == 30
    assert r["collected"] == 30
    assert r["has_summary"] is False
    assert r["errors"] == []


def test_parse_summary_line():
    out = "collected 147 items\n\nno tests ran\n"
    r = mod.parse_collect_output(out)
    assert r["summary_collected"] == 147
    assert r["collected"] == 147
    assert r["has_summary"] is True
    assert r["per_file_collected"] == 0


def test_parse_windows_paths():
    out = "tests\\test_a.py: 5\ntests\\sub\\test_b.py: 7\n"
    r = mod.parse_collect_output(out)
    assert r["per_file_collected"] == 12
    assert r["collected"] == 12


def test_parse_duplicate_lines():
    out = "tests/test_a.py: 10\ntests/test_a.py: 10\n"
    r = mod.parse_collect_output(out)
    # duplicates are summed literally as they appear in output (pytest does not
    # emit duplicates, but the parser must not crash or undercount unpredictably)
    assert r["per_file_collected"] == 20


def test_parse_zero_legitimate():
    out = "no tests ran in 0.01s\n"
    r = mod.parse_collect_output(out)
    assert r["collected"] == 0
    assert r["per_file_collected"] == 0
    assert r["has_summary"] is False


def test_parse_malformed_output():
    out = "lorem ipsum dolor\nsome random text without counts\n"
    r = mod.parse_collect_output(out)
    assert r["collected"] == 0
    assert r["per_file_collected"] == 0
    assert r["has_summary"] is False


def test_parse_collection_ignores_pytest_warning_frames():
    out = "tests/test_a.py: 10\n_pytest/config/__init__.py:1434\n"
    r = mod.parse_collect_output(out)
    assert r["per_file_collected"] == 10
    assert r["collected"] == 10


def test_parse_collection_errors_detected():
    out = "ERROR: error collecting tests/test_broken.py\ncollected 5 items / 1 error\n"
    r = mod.parse_collect_output(out)
    assert r["errors"]
    assert any("error" in e.lower() for e in r["errors"])


def test_run_collect_marks_incomplete_on_error(monkeypatch):
    class FakeProc:
        returncode = 1
        stdout = ""
        stderr = "ERROR: error collecting tests/test_x.py\n"

    monkeypatch.setattr(mod.subprocess, "run", lambda *_, **__: FakeProc())
    res = mod.run_collect()
    assert res["collection_return_code"] == 1
    assert res["incomplete"] is True
    assert res["authoritative"] is False
    assert res["collection_errors"]


def test_run_collect_clean_summary(monkeypatch):
    class FakeProc:
        returncode = 0
        stdout = "collected 42 items\n"
        stderr = ""

    monkeypatch.setattr(mod.subprocess, "run", lambda *_, **__: FakeProc())
    res = mod.run_collect()
    assert res["collection_return_code"] == 0
    assert res["incomplete"] is False
    assert res["collected_count"] == 42
    assert res["parse_method"] == "summary-line"
    assert res["authoritative"] is True


def test_run_collect_never_silent_zero_on_subprocess_failure(monkeypatch):
    class FakeProc:
        returncode = 2
        stdout = ""
        stderr = "ImportError: cannot import name 'foo'"

    monkeypatch.setattr(mod.subprocess, "run", lambda *_, **__: FakeProc())
    res = mod.run_collect()
    # Must NOT report a clean authoritative 0; must flag incomplete.
    assert res["incomplete"] is True
    assert res["authoritative"] is False
    assert res["collection_return_code"] == 2


def test_outcome_recorder_counts_each_final_category_and_deselections():
    from types import SimpleNamespace

    recorder = mod.OutcomeRecorder()
    recorder.pytest_deselected([object(), object()])
    reports = [
        SimpleNamespace(nodeid="pass", when="call", passed=True, failed=False, skipped=False),
        SimpleNamespace(nodeid="fail", when="call", passed=False, failed=True, skipped=False),
        SimpleNamespace(nodeid="skip", when="call", passed=False, failed=False, skipped=True),
        SimpleNamespace(nodeid="xfail", when="call", passed=False, failed=False, skipped=True, wasxfail="expected"),
        SimpleNamespace(nodeid="xpass", when="call", passed=True, failed=False, skipped=False, wasxfail="expected"),
        SimpleNamespace(nodeid="xpass-empty-reason", when="call", passed=True, failed=False, skipped=False, wasxfail=""),
    ]
    for report in reports:
        recorder.pytest_runtest_logreport(report)
    assert recorder.counts() == {
        "passed": 1,
        "failed": 1,
        "skipped": 1,
        "xfailed": 1,
        "xpassed": 2,
        "deselected": 2,
    }


def test_teardown_failure_overrides_passed_call():
    from types import SimpleNamespace

    recorder = mod.OutcomeRecorder()
    recorder.pytest_runtest_logreport(
        SimpleNamespace(nodeid="case", when="call", passed=True, failed=False, skipped=False)
    )
    recorder.pytest_runtest_logreport(
        SimpleNamespace(nodeid="case", when="teardown", passed=False, failed=True, skipped=False)
    )
    assert recorder.counts()["passed"] == 0
    assert recorder.counts()["failed"] == 1


def test_main_execute_records_outcomes_and_returns_for_policy_step(monkeypatch, tmp_path):
    monkeypatch.setattr(mod, "run_collect", lambda _: {
        "collection_status": "ok",
        "collection_command": "pytest --collect-only",
        "collection_return_code": 0,
        "collected_count": 3,
        "parse_method": "summary-line",
        "collection_errors": [],
        "incomplete": False,
        "authoritative": True,
    })
    monkeypatch.setattr(mod, "run_execution", lambda _: {
        "execution_status": "failed",
        "execution_return_code": 1,
        "execution_complete": True,
        "execution_errors": [],
        "passed": 2,
        "failed": 1,
        "skipped": 0,
        "xfailed": 0,
        "xpassed": 0,
        "deselected": 0,
    })
    monkeypatch.setattr(mod, "_git", lambda *_args: "f" * 40)
    out = tmp_path / "receipt.json"
    assert mod.main(["--out", str(out), "--execute"]) == 0
    receipt = json.loads(out.read_text(encoding="utf-8"))
    assert receipt["collected"] == 3
    assert receipt["passed"] == 2
    assert receipt["failed"] == 1
    assert receipt["execution_return_code"] == 1
    assert receipt["execution_complete"] is True


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-q"]))

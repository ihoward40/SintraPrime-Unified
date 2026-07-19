"""Unit tests for scripts/ci/report_test_inventory.py parser.

Tests are deterministic and do not require a real pytest collection run.
"""
import importlib.util
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


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-q"]))

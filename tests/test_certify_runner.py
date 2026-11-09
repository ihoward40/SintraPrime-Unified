"""Receipt-correctness tests for scripts/certify.py (SP-CERT-COLLECTION-RECEIPTS-001).

Real tiny temporary pytest collections plus controlled subprocess faults. Nothing here
runs a repository lane, touches a service or database, or writes inside the repo: every
test points certify at a throwaway repo root under ``tmp_path``.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import textwrap
import types
from pathlib import Path

import pytest

CERTIFY_PATH = Path(__file__).resolve().parents[1] / "scripts" / "certify.py"

# Fingerprints of the seven TARGETS / LANE_ENV definitions at the baseline commit.
TARGETS_SHA256 = "0867d229cef371c0b316f472caab744c4dbb76cc8e314eaadb319d16be2604e1"
LANE_ENV_SHA256 = "02f9e239e1941feb6a48abc916a77d75fce321368d6c4d05872a9a9a587233ca"
EXPECTED_LANE_ENV = {
    "default": "default",
    "portal": "default,portal",
    "swarm": "default,swarm",
    "auth_identity": "default,portal,release",
    "tenant_data": "default,portal,release",
    "execution_correctness": "default,release",
    "release_cert": "default",
}
LEGACY_RECEIPT_KEYS = [
    "run_id", "name", "target", "command", "git_sha", "branch", "python", "host", "basetemp",
    "tmp_policy", "started_at", "finished_at", "duration_seconds", "passed", "failed",
    "skipped", "exit_code", "summary_line", "stdout_log",
]

# The root conftest of a throwaway repo. certify always passes --timeout/--timeout-method;
# CI has pytest-timeout (requirements.txt) but a bare dev env may not, so accept the flags
# here only when no real plugin already registered them.
TIMEOUT_STUB_CONFTEST = '''
def pytest_addoption(parser):
    for name in ("--timeout", "--timeout-method"):
        try:
            parser.addoption(name, action="store", default=None)
        except ValueError:
            pass
'''

# Every test body appends to a sentinel file, so "the body ran" is directly observable.
SENTINEL_HEADER = """
import os
import pathlib

import pytest

SENTINEL = pathlib.Path(os.environ["CERT_TEST_SENTINEL"])


def mark(name):
    with SENTINEL.open("a", encoding="utf-8") as fh:
        fh.write(name + "\\n")
"""
MODULE_A = SENTINEL_HEADER + """
def test_a1():
    mark("a1")


def test_a2():
    mark("a2")


@pytest.mark.experimental
def test_a_experimental():
    mark("a_experimental")
"""
MODULE_B = SENTINEL_HEADER + """
def test_b1():
    mark("b1")


def test_b2():
    mark("b2")
"""
NO_TESTS_MODULE = "def helper():\n    return 1\n"
ONLY_EXPERIMENTAL_MODULE = SENTINEL_HEADER + """
@pytest.mark.experimental
def test_only_experimental():
    mark("only_experimental")
"""


@pytest.fixture(scope="module")
def certify():
    spec = importlib.util.spec_from_file_location("sp_certify_under_test", CERTIFY_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Sandbox:
    """A throwaway repo root that certify is pointed at."""

    def __init__(self, certify, root: Path, sentinel: Path, monkeypatch, capsys):
        self.certify, self.root, self.sentinel = certify, root, sentinel
        self._monkeypatch, self._capsys = monkeypatch, capsys

    def add(self, relpath: str, source: str = "") -> None:
        path = self.root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(source) if source.strip() else source, encoding="utf-8")

    def targets(self, *paths: str) -> None:
        self._monkeypatch.setattr(self.certify, "TARGETS", {"default": list(paths)})

    def run(self, *argv: str) -> tuple[int, dict, str]:
        """Run certify.main; return (exit code, parsed receipt, printed output)."""
        exit_code = self.certify.main(["--target", "default", *argv])
        out = self._capsys.readouterr().out
        match = re.search(r"^\[certify\] receipt: (.+)$", out, re.MULTILINE)
        assert match, out
        receipt = json.loads(Path(match.group(1)).read_text(encoding="utf-8"))
        assert receipt["exit_code"] == exit_code
        return exit_code, receipt, out

    def executed_bodies(self) -> list[str]:
        if not self.sentinel.exists():
            return []
        return self.sentinel.read_text(encoding="utf-8").split()

    def fake_pytest(self, behavior):
        """Replace certify's subprocess so the pytest launch is fully controlled.

        ``behavior(cmd, kwargs)`` returns a CompletedProcess or raises. git calls pass
        through to the real thing so the receipt's git fields keep working.
        """
        real_run, calls = subprocess.run, []

        def fake_run(cmd, *args, **kwargs):
            if cmd and cmd[0] == "git":
                return real_run(cmd, *args, **kwargs)
            calls.append((cmd, kwargs))
            return behavior(cmd, kwargs)

        fake = types.SimpleNamespace(
            run=fake_run,
            TimeoutExpired=subprocess.TimeoutExpired,
            SubprocessError=subprocess.SubprocessError,
        )
        self._monkeypatch.setattr(self.certify, "subprocess", fake)
        return calls


@pytest.fixture
def sandbox(tmp_path, monkeypatch, capsys, certify):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "pytest.ini").write_text(
        "[pytest]\naddopts = -q --import-mode=importlib\nmarkers =\n    experimental: excluded\n",
        encoding="utf-8",
    )
    (root / "conftest.py").write_text(TIMEOUT_STUB_CONFTEST, encoding="utf-8")
    sentinel = tmp_path / "sentinel.txt"
    monkeypatch.setenv("CERT_TEST_SENTINEL", str(sentinel))
    monkeypatch.setattr(certify, "ROOT", root)
    monkeypatch.setattr(certify, "ARTIFACTS", root / "artifacts")
    return Sandbox(certify, root, sentinel, monkeypatch, capsys)


def completed(cmd, returncode, stdout="", stderr=""):
    return subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr=stderr)


# --------------------------------------------------------------------------------------
# Collection mode: real pytest, real tiny collections
# --------------------------------------------------------------------------------------


def test_positive_collection_is_labeled_collection_pass_and_executes_nothing(sandbox):
    sandbox.add("pkg_a/test_a.py", MODULE_A)
    sandbox.add("pkg_b/test_b.py", MODULE_B)
    sandbox.targets("pkg_a/", "pkg_b")

    exit_code, receipt, out = sandbox.run("--collect-only")

    assert exit_code == 0
    assert receipt["mode"] == "collection"
    assert receipt["status"] == "completed"
    assert receipt["gate_result"] == "COLLECTION PASS"
    assert receipt["gate_passed"] is True
    assert receipt["gate_reasons"] == []
    assert receipt["pytest_returncode"] == 0
    # Executed count is 0 and the outcome counters carry no executed-test success.
    assert receipt["executed_count"] == 0
    assert (receipt["passed"], receipt["failed"], receipt["skipped"]) == (0, 0, 0)
    # Collected vs selected: the experimental marker is deselected by the lane filter.
    assert (receipt["collected_count"], receipt["selected_count"]) == (5, 4)
    assert receipt["deselected_count"] == 1
    assert receipt["collection_errors"] == 0
    by_path = {row["path"]: row for row in receipt["path_evidence"]}
    assert by_path["pkg_a/"] | {"exists": True} == {
        "path": "pkg_a/", "exists": True, "collected": 3, "selected": 2, "deselected": 1,
    }
    assert (by_path["pkg_b"]["collected"], by_path["pkg_b"]["selected"]) == (2, 2)
    # Node ids are preserved in a separate evidence file, not bloating the receipt.
    evidence = json.loads(Path(receipt["collection_evidence_file"]).read_text("utf-8"))
    assert sorted(evidence["selected"]) == [
        "pkg_a/test_a.py::test_a1", "pkg_a/test_a.py::test_a2",
        "pkg_b/test_b.py::test_b1", "pkg_b/test_b.py::test_b2",
    ]
    assert evidence["deselected"] == ["pkg_a/test_a.py::test_a_experimental"]
    # Command and console never imply runtime certification.
    assert "--collect-only" in receipt["command"]
    assert "COLLECTION PASS" in out
    assert "executed=0" in out
    assert "NOT runtime certification" in out
    assert not re.search(r"^\[certify\] PASS", out, re.MULTILINE)
    # Pass cleans the temp dir; receipt, logs and evidence stay.
    assert not (sandbox.root / "artifacts" / "test-temp" / receipt["run_id"]).exists()
    assert Path(receipt["stdout_log"]).exists()
    assert Path(receipt["stderr_log"]).exists()


def test_positive_collection_does_not_execute_test_bodies(sandbox):
    sandbox.add("pkg_a/test_a.py", MODULE_A)
    sandbox.add("pkg_b/test_b.py", MODULE_B)
    sandbox.targets("pkg_a", "pkg_b")

    collect_exit, _, _ = sandbox.run("--collect-only")
    assert collect_exit == 0
    assert sandbox.executed_bodies() == []  # sentinel: no body ran during collection

    exec_exit, _, _ = sandbox.run()  # same tree, execution mode: the sentinel does fire
    assert exec_exit == 0
    assert sorted(sandbox.executed_bodies()) == ["a1", "a2", "b1", "b2"]  # experimental excluded


def test_execution_mode_keeps_legacy_receipt_and_command(sandbox):
    sandbox.add("pkg_a/test_a.py", MODULE_A)
    sandbox.add("pkg_b/test_b.py", MODULE_B)
    sandbox.targets("pkg_a", "pkg_b")

    exit_code, receipt, out = sandbox.run()

    assert exit_code == 0
    assert all(key in receipt for key in LEGACY_RECEIPT_KEYS)
    assert receipt["mode"] == "execution"
    assert receipt["gate_result"] == "PASS"
    assert (receipt["passed"], receipt["failed"], receipt["skipped"]) == (4, 0, 0)
    assert receipt["executed_count"] == 4
    assert receipt["exit_code"] == receipt["pytest_returncode"] == 0
    assert receipt["summary_line"].startswith("4 passed")
    # Collected/selected are not fabricated in execution mode.
    assert receipt["collected_count"] is None
    assert receipt["selected_count"] is None
    assert receipt["collection_evidence_file"] is None
    # The execution command is unchanged: no collect flag, no helper plugin.
    assert "--collect-only" not in receipt["command"]
    assert "_certify_collect_plugin" not in " ".join(receipt["command"])
    assert re.search(r"^\[certify\] PASS: 4 passed", out, re.MULTILINE)


def test_execution_failure_preserves_temp_and_counts_failures(sandbox):
    sandbox.add("pkg_a/test_f.py", "def test_ok():\n    pass\n\n\ndef test_bad():\n    assert 0\n")
    sandbox.targets("pkg_a")

    exit_code, receipt, _ = sandbox.run()

    assert exit_code == 1
    assert receipt["gate_result"] == "FAIL"
    assert (receipt["passed"], receipt["failed"], receipt["pytest_returncode"]) == (1, 1, 1)
    assert receipt["executed_count"] == 2
    assert (sandbox.root / "artifacts" / "test-temp" / receipt["run_id"] / "basetemp").is_dir()
    assert "FAILED pkg_a/test_f.py::test_bad" in Path(receipt["stdout_log"]).read_text("utf-8")


def test_execution_mode_zero_tests_fails_and_preserves_exit_5(sandbox):
    sandbox.add("pkg_a/test_none.py", NO_TESTS_MODULE)
    sandbox.targets("pkg_a")

    exit_code, receipt, _ = sandbox.run()

    assert exit_code == 5
    assert receipt["pytest_returncode"] == 5
    assert receipt["gate_result"] == "FAIL"
    assert receipt["gate_passed"] is False
    assert any("exit code 5" in reason for reason in receipt["gate_reasons"])
    # Exit 5 establishes zero executions, not quiet-mode outcome counters.
    assert (receipt["passed"], receipt["failed"], receipt["executed_count"]) == (None, None, 0)
    assert receipt["skipped"] is None
    assert (sandbox.root / "artifacts" / "test-temp" / receipt["run_id"]).exists()


def test_exit_5_with_module_skip_keeps_unobserved_outcomes_unknown(sandbox):
    sandbox.add(
        "pkg_a/test_module_skip.py",
        SENTINEL_HEADER
        + """
pytest.skip("cert_review_module_skip", allow_module_level=True)


def test_never_runs():
    mark("never")
""",
    )
    sandbox.targets("pkg_a")

    exit_code, receipt, _ = sandbox.run("--", "-rs")

    assert exit_code == 5
    assert receipt["pytest_returncode"] == 5
    assert receipt["gate_result"] == "FAIL"
    assert receipt["gate_passed"] is False
    assert receipt["count_source"] == "pytest_exit_code_5"
    assert receipt["executed_count"] == 0
    for key in ("passed", "failed", "skipped", "errors"):
        assert receipt[key] is None, key
    stdout = Path(receipt["stdout_log"]).read_text("utf-8")
    assert "SKIPPED [1]" in stdout
    assert "cert_review_module_skip" in stdout
    assert sandbox.executed_bodies() == []


def test_empty_collection_fails_and_preserves_raw_exit_5(sandbox):
    sandbox.add("pkg_a/test_none.py", NO_TESTS_MODULE)
    sandbox.targets("pkg_a")

    exit_code, receipt, out = sandbox.run("--collect-only")

    assert exit_code == 5
    assert receipt["pytest_returncode"] == 5
    assert receipt["gate_result"] == "COLLECTION FAIL"
    assert receipt["gate_passed"] is False
    assert (receipt["collected_count"], receipt["selected_count"]) == (0, 0)  # known zero
    assert any("exit code 5" in reason for reason in receipt["gate_reasons"])
    assert "COLLECTION PASS" not in out
    assert (sandbox.root / "artifacts" / "test-temp" / receipt["run_id"]).exists()


def test_empty_path_fails_gate_even_when_another_path_supplies_tests(sandbox):
    sandbox.add("pkg_a/test_a.py", MODULE_A)
    sandbox.add("empty_dir/test_none.py", NO_TESTS_MODULE)
    sandbox.add("only_exp/test_exp.py", ONLY_EXPERIMENTAL_MODULE)
    sandbox.targets("pkg_a", "empty_dir", "only_exp")

    exit_code, receipt, out = sandbox.run("--collect-only")

    # pytest itself is happy (exit 0); the evidence gate is not, and says why.
    assert receipt["pytest_returncode"] == 0
    assert exit_code == sandbox.certify.EXIT_EVIDENCE_GATE == 6
    assert receipt["gate_result"] == "COLLECTION FAIL"
    assert receipt["selected_count"] == 2
    reasons = "\n".join(receipt["gate_reasons"])
    assert "configured path selected zero tests: empty_dir (collected 0, deselected 0)" in reasons
    assert "configured path selected zero tests: only_exp (collected 1, deselected 1)" in reasons
    assert "pkg_a" not in reasons
    assert "COLLECTION FAIL" in out
    assert "COLLECTION PASS" not in out
    by_path = {row["path"]: row for row in receipt["path_evidence"]}
    assert by_path["empty_dir"]["selected"] == 0
    assert by_path["pkg_a"]["selected"] == 2


def test_nested_empty_path_under_a_positive_parent_still_fails(sandbox):
    sandbox.add("pkg_a/test_a.py", MODULE_A)
    (sandbox.root / "pkg_a" / "emptysub").mkdir()
    sandbox.targets("pkg_a", "pkg_a/emptysub")

    exit_code, receipt, _ = sandbox.run("--collect-only")

    assert exit_code == 6
    assert receipt["gate_result"] == "COLLECTION FAIL"
    assert any("pkg_a/emptysub" in reason for reason in receipt["gate_reasons"])


def test_overlapping_directories_are_not_double_counted(sandbox):
    sandbox.add("pkg_a/test_a.py", MODULE_A)
    sandbox.add("pkg_a/sub/test_sub.py", "def test_s1():\n    pass\n\n\ndef test_s2():\n    pass\n")
    sandbox.targets("pkg_a", "pkg_a/sub")

    exit_code, receipt, _ = sandbox.run("--collect-only")

    assert exit_code == 0
    assert receipt["gate_result"] == "COLLECTION PASS"
    # 2 selected in pkg_a + 2 in pkg_a/sub = 4 unique tests, not 6 and not 8.
    assert receipt["selected_count"] == 4
    assert receipt["path_overlaps"] == [["pkg_a", "pkg_a/sub"]]
    by_path = {row["path"]: row for row in receipt["path_evidence"]}
    assert by_path["pkg_a"]["selected"] == 4  # inclusive of the nested path
    assert by_path["pkg_a/sub"]["selected"] == 2
    evidence = json.loads(Path(receipt["collection_evidence_file"]).read_text("utf-8"))
    assert len(evidence["selected"]) == len(set(evidence["selected"])) == 4
    assert sandbox.executed_bodies() == []


def test_missing_path_is_visible_and_counts_are_unknown_not_zero(sandbox):
    sandbox.add("pkg_a/test_a.py", MODULE_A)
    sandbox.targets("pkg_a", "does_not_exist")

    exit_code, receipt, _ = sandbox.run("--collect-only")

    assert exit_code == 4  # raw pytest usage error preserved
    assert receipt["pytest_returncode"] == 4
    assert receipt["gate_result"] == "COLLECTION FAIL"
    assert any("configured path missing: does_not_exist" in r for r in receipt["gate_reasons"])
    # pytest aborted before collecting, so nothing is claimed about pkg_a either.
    assert receipt["selected_count"] is None
    assert receipt["collected_count"] is None
    by_path = {row["path"]: row for row in receipt["path_evidence"]}
    assert by_path["does_not_exist"]["exists"] is False
    assert by_path["pkg_a"]["exists"] is True
    assert by_path["pkg_a"]["selected"] is None


@pytest.mark.parametrize(
    ("label", "source", "needle"),
    [
        ("import failure", "import module_that_does_not_exist_for_cert_test\n\n\ndef test_x():\n    pass\n",
         "module_that_does_not_exist_for_cert_test"),
        ("syntax error", "def test_x(:\n    pass\n", "SyntaxError"),
    ],
)
def test_collection_failure_is_recorded_not_reported_as_success(sandbox, label, source, needle):
    sandbox.add("pkg_a/test_a.py", MODULE_A)
    sandbox.add("pkg_bad/test_bad.py", source)
    sandbox.targets("pkg_a", "pkg_bad")

    exit_code, receipt, out = sandbox.run("--collect-only")

    assert exit_code == 2, label  # raw pytest "interrupted" exit preserved
    assert receipt["pytest_returncode"] == 2
    assert receipt["gate_result"] == "COLLECTION FAIL"
    assert receipt["collection_errors"] == 1
    assert receipt["executed_count"] == 0
    reasons = "\n".join(receipt["gate_reasons"])
    assert "1 collection error(s)" in reasons
    assert "pkg_bad" in reasons  # its path contributed zero tests
    evidence = json.loads(Path(receipt["collection_evidence_file"]).read_text("utf-8"))
    assert [e["nodeid"] for e in evidence["errors"]] == ["pkg_bad/test_bad.py"]
    assert needle in evidence["errors"][0]["detail"] or needle in Path(
        receipt["stdout_log"]
    ).read_text("utf-8")
    assert "COLLECTION PASS" not in out
    assert (sandbox.root / "artifacts" / "test-temp" / receipt["run_id"]).exists()


def test_collect_flag_passed_as_extra_pytest_arg_is_still_collection_mode(sandbox):
    calls = sandbox.fake_pytest(lambda cmd, _kw: completed(cmd, 0, "3 passed in 0.01s"))
    sandbox.targets("pkg_a")

    # argparse would abbreviate a bare --co to --collect-only; after '--' it is passed through.
    _, receipt, _ = sandbox.run("--", "--co")

    cmd = calls[0][0]
    assert receipt["mode"] == "collection"
    assert "--co" in cmd
    assert "--collect-only" not in cmd  # not duplicated
    assert "_certify_collect_plugin" in cmd


# --------------------------------------------------------------------------------------
# Unknown evidence is never a fabricated zero or PASS
# --------------------------------------------------------------------------------------


def _evidence(**override):
    base = {"schema": 2, "complete": True, "collection_completed": True, "selected": [],
            "deselected": [], "error_count": 0, "errors": []}
    return base | override


def _write_evidence(kw, text):
    Path(kw["env"]["SINTRAPRIME_CERT_COLLECT_JSON"]).write_text(text, encoding="utf-8")


@pytest.mark.parametrize(
    "evidence_text",
    [
        None,  # helper never wrote anything
        "{not json",
        json.dumps(_evidence(complete=False)),
        json.dumps(_evidence(schema=99)),
        json.dumps(_evidence(selected=[1])),
        json.dumps(_evidence(collection_completed=False)),  # file written, collection not
        json.dumps({k: v for k, v in _evidence().items() if k != "collection_completed"}),
    ],
    ids=["missing", "corrupt", "incomplete", "wrong-schema", "bad-types",
         "collection-not-completed", "no-completion-flag"],
)
def test_unavailable_collection_evidence_is_unknown_and_fails_the_gate(sandbox, evidence_text):
    def behavior(cmd, kw):
        if evidence_text is not None:
            _write_evidence(kw, evidence_text)
        return completed(cmd, 0, "4 tests collected in 0.01s")

    sandbox.fake_pytest(behavior)
    sandbox.targets("pkg_a")

    exit_code, receipt, out = sandbox.run("--collect-only")

    assert exit_code == 6
    assert receipt["pytest_returncode"] == 0
    assert receipt["gate_result"] == "COLLECTION UNKNOWN"
    assert receipt["gate_passed"] is False
    # Unknown, not a fabricated zero.
    assert receipt["collected_count"] is None
    assert receipt["selected_count"] is None
    assert receipt["deselected_count"] is None
    assert "COLLECTION PASS" not in out
    reasons = "\n".join(receipt["gate_reasons"])
    assert "unavailable" in reasons or "did not complete" in reasons
    assert receipt["collection_evidence_file"] is None


def test_unparseable_execution_output_is_unknown_not_pass_or_zero(sandbox):
    sandbox.fake_pytest(lambda cmd, _kw: completed(cmd, 0, "completely unrecognisable output"))
    sandbox.targets("pkg_a")

    exit_code, receipt, out = sandbox.run()

    assert exit_code == 6
    assert receipt["gate_result"] == "UNKNOWN"
    assert (receipt["passed"], receipt["failed"], receipt["skipped"]) == (None, None, None)
    assert receipt["executed_count"] is None
    assert not re.search(r"^\[certify\] PASS", out, re.MULTILINE)


def test_unparseable_output_with_failing_exit_keeps_raw_code_and_null_counts(sandbox):
    sandbox.fake_pytest(lambda cmd, _kw: completed(cmd, 1, "no summary here"))
    sandbox.targets("pkg_a")

    exit_code, receipt, _ = sandbox.run()

    assert exit_code == 1
    assert receipt["pytest_returncode"] == 1
    assert receipt["gate_result"] == "FAIL"
    assert receipt["failed"] is None  # not 0, and not an invented count


def test_summary_is_read_from_the_final_line_not_an_earlier_failure_message(sandbox):
    stdout = "FAILED t.py::x - AssertionError: 99 passed in 1s was claimed\n1 failed, 2 passed in 0.03s\n"
    sandbox.fake_pytest(lambda cmd, _kw: completed(cmd, 1, stdout))
    sandbox.targets("pkg_a")

    _, receipt, _ = sandbox.run()

    assert (receipt["passed"], receipt["failed"]) == (2, 1)


# --------------------------------------------------------------------------------------
# Terminal receipts for failures before/without a pytest result
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("collect", [False, True], ids=["execution", "collection"])
@pytest.mark.parametrize(
    ("partial_out", "partial_err", "expect_out", "expect_err"),
    [
        (b"abc\xff", "err text", "abc", "err text"),  # bytes stdout (CPython quirk), str stderr
        ("out text", b"e\xfe", "out text", "e"),  # str stdout, bytes stderr
        (None, None, "", ""),  # nothing captured
        (b"", b"", "", ""),
    ],
)
def test_wall_clock_timeout_writes_terminal_receipt_with_partial_output(
    sandbox, collect, partial_out, partial_err, expect_out, expect_err
):
    def behavior(cmd, kw):
        raise subprocess.TimeoutExpired(cmd, kw["timeout"], output=partial_out, stderr=partial_err)

    calls = sandbox.fake_pytest(behavior)
    sandbox.targets("pkg_a")

    exit_code, receipt, out = sandbox.run(*(["--collect-only"] if collect else []))

    assert calls[0][1]["timeout"] == 1800
    assert exit_code == 3 == sandbox.certify.EXIT_WALL_CLOCK_TIMEOUT
    assert receipt["status"] == "wall_clock_timeout"
    assert receipt["gate_result"] == ("COLLECTION FAIL" if collect else "FAIL")
    assert receipt["gate_passed"] is False
    assert receipt["pytest_returncode"] is None
    # No fabricated counts for a run that never produced a result.
    for key in ("passed", "failed", "skipped", "executed_count", "collected_count",
                "selected_count", "summary_line"):
        assert receipt[key] is None, key
    assert Path(receipt["stdout_log"]).read_text("utf-8").startswith(expect_out)
    assert Path(receipt["stderr_log"]).read_text("utf-8").startswith(expect_err)
    assert "LANE WALL-CLOCK TIMEOUT (1800s)" in out
    assert "CERTIFICATION FAILURE" in out
    assert (sandbox.root / "artifacts" / "test-temp" / receipt["run_id"]).exists()


def test_real_wall_clock_timeout_kills_the_child_and_still_writes_a_receipt(sandbox, monkeypatch):
    # Importing this module hangs collection, so the real subprocess hits the real cap.
    sandbox.add("pkg_a/test_hang.py", "import time\n\ntime.sleep(120)\n\n\ndef test_x():\n    pass\n")
    sandbox.targets("pkg_a")
    monkeypatch.setattr(sandbox.certify, "WALL_CLOCK_TIMEOUT_SECONDS", 3)

    exit_code, receipt, _ = sandbox.run("--collect-only")

    assert exit_code == 3
    assert receipt["status"] == "wall_clock_timeout"
    assert receipt["wall_clock_timeout_seconds"] == 3
    assert receipt["duration_seconds"] < 60  # killed at the cap, not after the 120s sleep
    assert Path(receipt["stdout_log"]).exists()
    assert Path(receipt["stderr_log"]).exists()
    assert (sandbox.root / "artifacts" / "test-temp" / receipt["run_id"]).exists()


@pytest.mark.parametrize("collect", [False, True], ids=["execution", "collection"])
def test_launch_failure_of_a_missing_interpreter_writes_terminal_receipt(
    sandbox, monkeypatch, collect
):
    monkeypatch.setattr(
        sandbox.certify, "_python_exe", lambda: str(sandbox.root / "no-such-python.exe")
    )
    sandbox.targets("pkg_a")

    exit_code, receipt, out = sandbox.run(*(["--collect-only"] if collect else []))

    assert exit_code == 7 == sandbox.certify.EXIT_LAUNCH_ERROR
    assert receipt["status"] == "launch_error"
    assert "Error" in receipt["launch_error"]
    assert receipt["gate_passed"] is False
    assert receipt["pytest_returncode"] is None
    for key in ("passed", "failed", "skipped", "executed_count", "collected_count"):
        assert receipt[key] is None, key
    assert Path(receipt["stdout_log"]).read_text("utf-8") == ""
    assert Path(receipt["stderr_log"]).read_text("utf-8") == ""
    assert "SUBPROCESS LAUNCH ERROR" in out
    assert (sandbox.root / "artifacts" / "test-temp" / receipt["run_id"]).exists()


def test_launch_failure_from_the_subprocess_layer_is_caught(sandbox):
    def behavior(_cmd, _kw):
        raise PermissionError("access denied by test")

    sandbox.fake_pytest(behavior)
    sandbox.targets("pkg_a")

    exit_code, receipt, _ = sandbox.run()

    assert exit_code == 7
    assert receipt["launch_error"] == "PermissionError: access denied by test"
    assert receipt["failed"] is None


def test_failure_keeps_stdout_stderr_and_temp_across_unique_runs(sandbox):
    def behavior(cmd, _kw):
        return completed(cmd, 1, "1 failed in 0.10s", "stderr line from child")

    sandbox.fake_pytest(behavior)
    sandbox.targets("pkg_a")

    receipts = [sandbox.run()[1] for _ in range(3)]

    # Same-second runs still get unique ids, receipts, logs and temp roots ...
    assert len({r["run_id"] for r in receipts}) == 3
    assert len({r["basetemp"] for r in receipts}) == 3
    assert len({r["stdout_log"] for r in receipts}) == 3
    # ... and a later run never clobbers earlier failure evidence.
    for r in receipts:
        assert Path(r["basetemp"]).is_dir()
        assert Path(r["stdout_log"]).read_text("utf-8") == "1 failed in 0.10s"
        assert Path(r["stderr_log"]).read_text("utf-8") == "stderr line from child"


# --------------------------------------------------------------------------------------
# Compatibility: the pinned certification contract is unchanged
# --------------------------------------------------------------------------------------


def _fingerprint(value) -> str:
    blob = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def test_targets_and_lane_env_definitions_are_unchanged(certify):
    assert sorted(certify.TARGETS) == sorted(EXPECTED_LANE_ENV)
    assert len(certify.TARGETS) == 7
    assert _fingerprint(certify.TARGETS) == TARGETS_SHA256
    assert certify.LANE_ENV == EXPECTED_LANE_ENV
    assert _fingerprint(certify.LANE_ENV) == LANE_ENV_SHA256
    assert certify.WALL_CLOCK_TIMEOUT_SECONDS == 1800
    assert certify.PER_TEST_TIMEOUT_SECONDS == 120


@pytest.mark.parametrize("target", sorted(EXPECTED_LANE_ENV))
def test_launch_contract_per_target_is_preserved(sandbox, certify, target):
    calls = sandbox.fake_pytest(lambda cmd, _kw: completed(cmd, 0, "3 passed in 0.01s"))

    exit_code = certify.main(["--target", target])

    assert exit_code == 0
    cmd, kwargs = calls[0]
    assert cmd[1:3] == ["-m", "pytest"]
    assert cmd[3 : 3 + len(certify.TARGETS[target])] == certify.TARGETS[target]
    for flag in ("not experimental", "--tb=short", "-q", "no:cacheprovider",
                 "--timeout=120", "--timeout-method=thread"):
        assert flag in cmd, flag
    marker_at = 3 + len(certify.TARGETS[target])
    assert cmd[marker_at : marker_at + 2] == ["-m", "not experimental"]  # marker exclusion
    assert "-n" not in cmd  # PARALLELISM = 1: serial, no xdist
    assert "--dist" not in cmd
    assert "--collect-only" not in cmd
    assert kwargs["timeout"] == 1800
    assert kwargs["cwd"] == sandbox.root
    env = kwargs["env"]
    assert env["SINTRAPRIME_TEST_LANES"] == EXPECTED_LANE_ENV[target]
    assert env["SINTRAPRIME_CERT_NET_GUARD"] == "1"  # default-deny network guard
    assert env["PYTHONPATH"] == str(sandbox.root)
    assert "SINTRAPRIME_CERT_COLLECT_JSON" not in env  # execution env is unchanged
    assert Path(env["TMP"]).name == "child-tmp"  # repo-owned per-run temp policy
    assert env["TMP"] == env["TEMP"] == env["TMPDIR"]


def test_collection_mode_keeps_guard_lane_env_and_adds_only_the_helper(sandbox, certify):
    calls = sandbox.fake_pytest(lambda cmd, _kw: completed(cmd, 0, ""))

    certify.main(["--target", "portal", "--collect-only"])

    cmd, kwargs = calls[0]
    env = kwargs["env"]
    assert env["SINTRAPRIME_TEST_LANES"] == "default,portal"
    assert env["SINTRAPRIME_CERT_NET_GUARD"] == "1"
    assert cmd.count("--collect-only") == 1
    assert "--timeout=120" in cmd
    assert env["PYTHONPATH"].split(sandbox.certify.os.pathsep)[0] == str(sandbox.root)
    helper_dir = Path(env["PYTHONPATH"].split(sandbox.certify.os.pathsep)[1])
    assert (helper_dir / "_certify_collect_plugin.py").is_file()  # staged per run, in temp
    assert sandbox.root in helper_dir.parents


# --------------------------------------------------------------------------------------
# Reviewer corrections: unknown collection is not zero; executed_count only when established
# --------------------------------------------------------------------------------------

ABORT_HOOKS = {
    "early-collection-hook": (
        "import pytest\n\n\n@pytest.hookimpl(tryfirst=True)\n"
        "def pytest_collection():\n    raise RuntimeError('early abort before collection')\n"
    ),
    "modifyitems-hook": (
        "def pytest_collection_modifyitems():\n    raise RuntimeError('modifyitems abort')\n"
    ),
}


@pytest.mark.parametrize("hook", sorted(ABORT_HOOKS))
def test_collection_aborted_by_a_hook_keeps_counts_unknown_not_zero(sandbox, hook):
    sandbox.add("pkg_a/test_a.py", MODULE_A)
    sandbox.targets("pkg_a")
    conftest = sandbox.root / "conftest.py"
    conftest.write_text(
        conftest.read_text(encoding="utf-8") + "\n" + ABORT_HOOKS[hook], encoding="utf-8"
    )

    exit_code, receipt, out = sandbox.run("--collect-only")

    assert receipt["status"] == "completed"  # pytest ran and exited; it just did not collect
    assert receipt["pytest_returncode"] not in (0, None)
    assert exit_code == receipt["pytest_returncode"]  # raw code preserved
    assert receipt["gate_passed"] is False
    assert receipt["gate_result"] == "COLLECTION FAIL"
    # No collection was observed: nothing may be reported as a measured zero.
    for key in ("collected_count", "selected_count", "deselected_count", "collection_errors"):
        assert receipt[key] is None, key
    assert all(row["selected"] is None and row["collected"] is None
               for row in receipt["path_evidence"])
    assert receipt["collection_evidence_file"] is None
    assert "COLLECTION PASS" not in out
    assert sandbox.executed_bodies() == []


def test_setup_only_errors_do_not_count_as_executed_tests(sandbox):
    sandbox.add(
        "pkg_a/test_setup_fail.py",
        SENTINEL_HEADER + """
@pytest.fixture
def boom():
    raise RuntimeError("fixture fails before the body")


def test_s1(boom):
    mark("s1")


def test_s2(boom):
    mark("s2")
""",
    )
    sandbox.targets("pkg_a")

    exit_code, receipt, _ = sandbox.run()

    assert sandbox.executed_bodies() == []  # no body ever ran
    assert exit_code == 1
    assert receipt["gate_result"] == "FAIL"
    # Real -qq output is "EE [100%]": must not become executed_count == 2.
    assert receipt["executed_count"] in (None, 0)
    assert receipt["executed_count"] != 2


@pytest.mark.parametrize(
    ("body", "bodies", "skipped"),
    [
        ("@pytest.mark.xfail(run=False)\ndef test_x():\n    mark('x')\n", [], 0),
        ("def test_x():\n    mark('x')\n    pytest.xfail('declared inside the body')\n", ["x"], 0),
        ("@pytest.mark.skip(reason='before')\ndef test_x():\n    mark('x')\n", [], 1),
        ("def test_x():\n    mark('x')\n    pytest.skip('inside the body')\n", ["x"], 1),
    ],
    ids=["xfail-before-body", "xfail-inside-body", "skip-before-body", "skip-inside-body"],
)
def test_summary_xfail_and_skip_cannot_establish_executed_count(sandbox, body, bodies, skipped):
    sandbox.add("pkg_a/test_x.py", SENTINEL_HEADER + "\n" + body)
    sandbox.targets("pkg_a")

    # '-vv' after '--' restores pytest's timed summary line under the double-quiet config.
    exit_code, receipt, _ = sandbox.run("--", "-vv")

    assert sandbox.executed_bodies() == bodies  # ground truth: the body did/didn't run
    assert exit_code == 0
    assert receipt["count_source"] == "summary_line"
    assert receipt["executed_count"] is None  # same summary either way: unknown
    assert receipt["skipped"] == skipped
    assert receipt["gate_result"] == "PASS"  # legacy gate behavior unchanged


def test_summary_passed_and_failed_still_establish_executed_count(sandbox):
    sandbox.add("pkg_a/test_f.py", "def test_ok():\n    pass\n\n\ndef test_bad():\n    assert 0\n")
    sandbox.targets("pkg_a")

    _, receipt, _ = sandbox.run("--", "-vv")

    assert receipt["count_source"] == "summary_line"
    assert (receipt["passed"], receipt["failed"], receipt["executed_count"]) == (1, 1, 2)


@pytest.mark.parametrize(
    ("stdout", "rc", "executed", "errors"),
    [
        ("..F [100%]\n", 1, 3, None),  # only '.'/'F' marks: bodies certainly ran
        (".s. [100%]\n", 0, None, None),  # 's' may be before or inside a body
        (".E [100%]\n", 1, None, None),  # 'E' may be setup or teardown
        ("x. [100%]\n", 0, None, None),  # 'x' may be before or inside a body
        ("1 skipped, 2 passed in 0.10s\n", 0, None, 0),
        ("1 xfailed, 2 passed in 0.10s\n", 0, None, 0),
        ("2 passed, 1 xpassed in 0.10s\n", 0, 3, 0),
    ],
    ids=["dots-and-F", "skip-mark", "error-mark", "xfail-mark", "skipped-summary",
         "xfailed-summary", "xpassed-summary"],
)
def test_executed_count_is_null_whenever_the_evidence_is_ambiguous(
    sandbox, stdout, rc, executed, errors
):
    sandbox.fake_pytest(lambda cmd, _kw: completed(cmd, rc, stdout))
    sandbox.targets("pkg_a")

    _, receipt, _ = sandbox.run()

    assert receipt["executed_count"] == executed
    assert receipt["errors"] == errors

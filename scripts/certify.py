"""Deterministic certification runner for SintraPrime-Unified.

SP-CONVERGE-001 / 2A-0 — repository-owned temp policy.

Guarantees deterministic temporary storage for certification pytest runs so
host-level temp ACL problems (WinError 5 on the default pytest temp base)
can never poison a certification run. Every run gets a unique repo-local
temp root; pytest cache provider is disabled; a receipt is always written.

Usage:
  python scripts/certify.py --target default
  python scripts/certify.py --target portal --name portal-after-fix
  python scripts/certify.py --target swarm -- -k artifact_store

Targets (G0-R3 RC lanes added):
  default  tests/ + voice_concierge/governed/tests/   (Tier 1)
  portal   portal/tests/                              (Tier 2)
  swarm    swarm_runtime/tests/                       (Tier 3)
  auth_identity  tests/ + portal/tests/ + portal/sso/tests/   (RC lane A)
  tenant_data     portal/tests/                             (RC lane B)
  execution_correctness  all release-bearing module test dirs (RC lane C)
  release_cert    tests/ + scripts/ci/tests/                  (RC lane D)

Temp policy:
  artifacts/test-temp/<run_id>/       pytest --basetemp + child-process TMP
  - unique per run (never shared across concurrent runs)
  - removed only when the gate passes; preserved otherwise (failure evidence)
  - recorded in the receipt
  - pytest cache writes disabled (deterministic; no host .pytest_cache)

Modes (receipt "mode"):
  execution   default. Runs the tests. Gate label PASS / FAIL / UNKNOWN.
  collection  --collect-only. Runs NO test body, so executed_count is always 0 and the
              success label is COLLECTION PASS, never PASS: it is not runtime
              certification. Node ids come from a private pytest plugin
              (scripts/_certify_collect_plugin.py), not from pytest's text output.
              Every configured target path must exist and select >= 1 test, or the
              gate fails (per-path counts are inclusive and must not be summed).

Collection counts are reported only when the helper observed collection complete
(count_source "collection_helper"); if pytest aborted earlier (exit 3/4, a raising
hook) they are null even though the evidence file exists. Collection-mode skipped
counts remain null because the helper does not measure skipped collection reports.

Execution-mode executed_count = tests whose body is known to have run (passed +
failed + xpassed). It requires an ordinary completed pytest outcome (exit 0 or 1).
It is taken from pytest's summary line, or from progress marks only when every mark
is '.' or 'F' and the final progress record reached 100%. Partial progress and
interrupted/internal-error outcomes leave the total unknown. Setup errors ('E'), skips and xfails can occur before
or inside a body, so if the summary reports any xfailed/skipped, or any mark is not
'.'/'F', executed_count (and, for marks, errors) is null. Legacy passed/failed/skipped keep their old
mark-derived values. If quiet output contains no outcome counts, pytest exit 5
establishes executed_count=0 only; other outcome counters remain null because
collection-time skips can still have occurred.

Counts that cannot be established (timeout, launch error, unparseable output) are
null, never a fabricated 0. gate_result UNKNOWN means pytest exited 0 but its
evidence could not be verified; it fails the gate.

Exit codes: any nonzero pytest return code is passed through raw (receipt
"pytest_returncode"; 5 = no tests); 3 = lane wall-clock timeout; 6 = pytest exited 0
but the evidence gate failed; 7 = the pytest subprocess could not be launched.
Receipt "exit_code" is certify's own exit code; "gate_reasons" explains it.
Extra pytest args that narrow selection (-k, --deselect) can legitimately trip the
per-path gate; they are recorded in the receipt.

Receipts: artifacts/cert-receipts/<run_id>.json (+ .stdout.txt, .stderr.txt, and
.collection.json with node ids in collection mode). Always written once an
invocation is valid, including subprocess launch failure, collection failure and
wall-clock timeout. Serial only: lanes are never run concurrently.
"""
from __future__ import annotations

import argparse
import json
import locale
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"

TARGETS: dict[str, list[str]] = {
    "default": ["tests/", "voice_concierge/governed/tests/"],
    "portal": ["portal/tests/"],
    "swarm": ["swarm_runtime/tests/"],
    # G0-R3 RC certification lanes (SP-RC-RUNTIME-COLLECTION-VERIFY-001)
    "auth_identity": ["tests/", "portal/tests/", "portal/sso/tests/"],
    "tenant_data": ["portal/tests/"],
    "execution_correctness": [
        "tests/",
        "agent_runtime/tests",
        "agents/chat/tests",
        "agents/sigma/tests",
        "agents/tests",
        "agents/zero/tests",
        "app_builder/tests",
        "backend/lead-router/tests",
        "backend/stripe-payments/tests",
        "blackstone/bra/tests",
        "blackstone/tests",
        "channels/tests",
        "core/tests",
        "core/universe",
        "core/universe/ml",
        "core/universe/tests",
        "cross_platform/tests",
        "governance/tests",
        "integrations/airtable_crm/tests",
        "integrations/banking/tests",
        "integrations/case_law/tests",
        "local_llm/tests",
        "local_models/tests",
        "mcp_server/tests",
        "mission_wiring/tests",
        "observability/tests",
        "operator/tests",
        "orchestration/tests",
        "performance/tests",
        "phase15/competitor_intel/tests",
        "phase15/cpa_partnership/tests",
        "phase15/lead_nurture/tests",
        "phase15/realtime_alerts/tests",
        "phase15/windows_exe/tests",
        "phase16/advanced_analytics/tests",
        "phase16/confidential_computing/tests",
        "phase16/contract_redline/tests",
        "phase16/hierarchical_orchestration/tests",
        "phase16/jurisdiction_engine/tests",
        "phase16/mobile_app/tests",
        "phase16/moe_router/tests",
        "phase16/multi_tenant/tests",
        "phase16/multimodal_court/tests",
        "phase16/parl_core/tests",
        "phase16/precedent_ai/tests",
        "phase16/stripe_billing/tests",
        "phase17/benchmarks/tests",
        "phase17/integration_tests/tests",
        "phase17/llm_wiring/tests",
        "phase17/windows_deploy/tests",
        "phase18/ikeos_integration/tests",
        "phase18/legal_simulation/tests",
        "phase18/mobile_app/tests",
        "phase18/security/tests",
        "phase18/self_healing_ci/tests",
        "phase18/stripe_webhooks/tests",
        "phase18/verification/tests",
        "phase19/revenue_smoke_test",
        "phase19/revenue_smoke_test/tests",
        "phase19/trust_compliance_gateway/tests",
        "portal/routers/tests",
        "portal/sso/tests",
        "portal/tests",
        "predictive/tests",
        "scheduler/tests",
        "secure_execution/tests",
        "security/tests",
        "swarm_runtime/tests",
        "trust_law/tests",
        "voice_concierge/governed/tests",
        "workflow_builder/tests",
    ],
    "release_cert": ["tests/", "scripts/ci/tests/"],
}

# Visible-lane mapping (Wave 2B): the root conftest only un-ignores a Tier-2/3
# directory when its lane name is listed in SINTRAPRIME_TEST_LANES.
LANE_ENV: dict[str, str] = {
    "default": "default",
    "portal": "default,portal",
    "swarm": "default,swarm",
    "auth_identity": "default,portal,release",
    "tenant_data": "default,portal,release",
    "execution_correctness": "default,release",
    "release_cert": "default",
}

# Receipt contract (SP-CERT-COLLECTION-RECEIPTS-001).
WALL_CLOCK_TIMEOUT_SECONDS = 1800
PER_TEST_TIMEOUT_SECONDS = 120
RECEIPT_VERSION = 2

# certify's own exit codes. Any nonzero pytest return code is passed through raw
# (1 failed, 2 interrupted/collection error, 4 usage, 5 no tests); pytest's own 3
# (internal error) is indistinguishable by exit code alone, so read the receipt.
EXIT_WALL_CLOCK_TIMEOUT = 3
EXIT_EVIDENCE_GATE = 6  # pytest exited 0 but the evidence gate did not pass
EXIT_LAUNCH_ERROR = 7  # the pytest subprocess could not be started

_COLLECT_FLAGS = frozenset({"--collect-only", "--co", "--collectonly"})
_COLLECT_PLUGIN_FILE = Path(__file__).with_name("_certify_collect_plugin.py")
_COLLECT_PLUGIN_MODULE = _COLLECT_PLUGIN_FILE.stem
_COLLECT_EVIDENCE_ENV = "SINTRAPRIME_CERT_COLLECT_JSON"
_COLLECT_SCHEMA = 2

_TIMED_LINE_RE = re.compile(r"^[=\s]*(?P<body>.*?)\s+in\s+\d+(?:\.\d+)?s\b")
_COUNT_RE = re.compile(r"(\d+) (passed|failed|skipped|errors?|xfailed|xpassed|deselected|warnings?)")
_COUNT_KEYS = ("passed", "failed", "skipped", "errors", "xfailed", "xpassed")


def _git(args: list[str]) -> str:
    out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else "unknown"


def _python_exe() -> str:
    win = ROOT / ".venv" / "Scripts" / "python.exe"
    posix = ROOT / ".venv" / "bin" / "python"
    if win.exists():
        return str(win)
    if posix.exists():
        return str(posix)
    return sys.executable


def _as_text(value: str | bytes | None) -> str:
    """Partial output of a timed-out child can be bytes, str or None."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(locale.getpreferredencoding(False), errors="replace")
    return value


def _norm(path: str) -> str:
    return path.replace("\\", "/").strip("/")


def _under(nodeid: str, path: str) -> bool:
    file_part = nodeid.split("::", 1)[0]
    return file_part == path or file_part.startswith(path + "/")


def _last_timed_line(stdout: str) -> str | None:
    for line in reversed(stdout.splitlines()):
        if _TIMED_LINE_RE.match(line.strip()):
            return line.strip()
    return None


def _count_progress_marks(stdout: str) -> dict[str, int] | None:
    """Count pytest progress marks. 'E' (setup/teardown error), 's', 'x' and 'X' cannot be
    told apart from call-phase outcomes by the mark alone, so they make the run ambiguous."""
    dots = skips = legacy_failed = ambiguous = 0
    complete = False
    for line in stdout.splitlines():
        stripped = line.strip()
        if re.fullmatch(r"[.sFXxXE]+(\s+\[\s*\d+%\])?", stripped):
            marks = stripped.split("[")[0].strip()
            complete = bool(re.search(r"\[\s*100%\]$", stripped))
            dots += marks.count(".")
            skips += marks.count("s")
            other = marks.count("X") + marks.count("x") + marks.count("E")
            ambiguous += other + marks.count("s")
            legacy_failed += marks.count("F") + other
    if not (dots or skips or legacy_failed):
        return None
    return {
        "dots": dots, "skips": skips, "legacy_failed": legacy_failed,
        "ambiguous": ambiguous, "complete": complete,
    }


def _blank_analysis() -> dict[str, object]:
    return {
        "reasons": [],
        "summary_line": None,
        "count_source": "unavailable",
        "passed": None,
        "failed": None,
        "skipped": None,
        "errors": None,
        "executed_count": None,
        "collected_count": None,
        "selected_count": None,
        "deselected_count": None,
        "collection_errors": None,
        "path_evidence": None,
        "pytest_version": None,
        "evidence": None,
    }


def _analyze_execution(stdout: str, rc: int) -> tuple[str, dict[str, object]]:
    """Execution-mode evidence: counts come from pytest's own summary line."""
    a = _blank_analysis()
    summary = _last_timed_line(stdout)
    counts: dict[str, int] | None = None
    marks_unambiguous = False
    marks_complete = False
    if summary is not None:
        body = _TIMED_LINE_RE.match(summary).group("body")  # type: ignore[union-attr]
        found = {
            ("errors" if k.startswith("error") else k): int(n) for n, k in _COUNT_RE.findall(body)
        }
        if found or "no tests ran" in body:
            counts = {k: found.get(k, 0) for k in _COUNT_KEYS}
            a["count_source"] = "summary_line"
    if counts is None:
        summary = None
        marks = _count_progress_marks(stdout)
        if marks is not None:
            passed, skipped, failed = marks["dots"], marks["skips"], marks["legacy_failed"]
            marks_unambiguous = marks["ambiguous"] == 0
            marks_complete = bool(marks["complete"])
            counts = dict.fromkeys(_COUNT_KEYS, 0) | {
                "passed": passed,
                "skipped": skipped,
                "failed": failed,
            }
            summary = f"{passed} passed, {failed} failed, {skipped} skipped (counted from progress marks)"
            a["count_source"] = "progress_marks"
    # Evidence-integrity guard: a nonzero exit other than "no tests" with zero parsed
    # failures means the parser missed something; never report failed=0 for it.
    if counts is not None and rc not in (0, 5) and counts["failed"] == 0:
        counts["failed"] = -1  # explicit "uncounted failures" sentinel
        summary = (summary or "") + " [FAILURES PRESENT BUT UNCOUNTED]"
    a["summary_line"] = summary

    reasons: list[str] = a["reasons"]  # type: ignore[assignment]
    if rc != 0:
        reasons.append(f"pytest exit code {rc}" + (" (no tests collected/selected)" if rc == 5 else ""))
    if counts is None:
        if rc == 5:
            # No selected tests means no bodies ran, but collection-time skips can
            # still exist. The exit code cannot establish the outcome counters.
            a["executed_count"] = 0
            a["count_source"] = "pytest_exit_code_5"
        elif rc == 0:
            reasons.append("test outcome counts unavailable (pytest summary not parseable)")
        return ("UNKNOWN" if rc == 0 else "FAIL"), a
    a.update({k: counts[k] for k in _COUNT_KEYS})
    from_marks = a["count_source"] == "progress_marks"
    if from_marks:
        a["errors"] = None  # marks cannot separate setup/teardown errors: unknown, not 0
    # executed_count = tests whose body is known to have run. Summary passed/failed/xpassed
    # imply a body ran (setup/teardown problems are "error"). Summary xfailed and skipped
    # do not: both can happen before the body (xfail(run=False), skip marks) or inside it
    # (pytest.xfail()/pytest.skip()), so any of them makes the count unknown. From progress
    # marks it additionally needs a terminal 100% record: an aborted body can enter
    # without emitting a mark. Interruptions/internal errors and uncounted failures
    # cannot establish a total, even if some outcomes were printed.
    summary_ok = (
        rc in (0, 1) and counts["failed"] >= 0
        and counts["xfailed"] == 0 and counts["skipped"] == 0
    )
    if summary_ok and (not from_marks or (marks_unambiguous and marks_complete)):
        a["executed_count"] = (
            counts["passed"] + max(counts["failed"], 0) + counts["xfailed"] + counts["xpassed"]
        )
    outcomes = counts["passed"] + max(counts["failed"], 0) + counts["skipped"]
    outcomes += counts["xfailed"] + counts["xpassed"] + (0 if from_marks else counts["errors"])
    if outcomes == 0 and rc != 5:
        reasons.append("zero tests selected")
    return ("PASS" if not reasons else "FAIL"), a


def _read_collection_evidence(path: Path) -> dict | None:
    """Return the helper's evidence, or None if missing/unreadable/incomplete."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("schema") != _COLLECT_SCHEMA:
        return None
    if data.get("complete") is not True or not isinstance(data.get("error_count"), int):
        return None
    if not isinstance(data.get("collection_completed"), bool):
        return None
    for key in ("selected", "deselected"):
        values = data.get(key)
        if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
            return None
    if not isinstance(data.get("errors"), list):
        return None
    return data


def _path_overlaps(paths: list[str]) -> list[list[str]]:
    """Pairs [outer, inner] of configured paths where one contains (or equals) the other."""
    return [
        [a, b]
        for a in paths
        for b in paths
        if a != b and (_norm(b) == _norm(a) or _norm(b).startswith(_norm(a) + "/"))
    ]


def _path_rows(
    paths: list[str], selected: list[str] | None, deselected: list[str] | None
) -> list[dict]:
    """Per configured path. Counts are inclusive (a nested path also counts toward its
    parent), so they must never be summed; the unique total is selected_count.
    selected/deselected of None means pytest never collected: counts are unknown (null)."""
    rows = []
    for raw in paths:
        p = _norm(raw)
        row: dict[str, object] = {"path": raw, "exists": (ROOT / p).exists()}
        if selected is None or deselected is None:
            row.update(collected=None, selected=None, deselected=None)
        else:
            sel = sum(1 for n in selected if _under(n, p))
            des = sum(1 for n in deselected if _under(n, p))
            row.update(collected=sel + des, selected=sel, deselected=des)
        rows.append(row)
    return rows


def _analyze_collection(
    evidence_file: Path, rc: int, paths: list[str]
) -> tuple[str, dict[str, object]]:
    """Collection-mode evidence: node ids come from the private helper plugin, never text."""
    a = _blank_analysis()
    reasons: list[str] = a["reasons"]  # type: ignore[assignment]
    # Collection never runs a test body. Modules can still be skipped on import,
    # and the helper does not measure those reports, so skipped remains unknown.
    a.update(passed=0, failed=0, errors=0, executed_count=0)
    if rc != 0:
        reasons.append(f"pytest exit code {rc}" + (" (no tests collected/selected)" if rc == 5 else ""))
    data = _read_collection_evidence(evidence_file)
    # Exit 4 is a usage error (e.g. a missing path): pytest aborted before collecting,
    # so any zero it reports is an artifact and the counts are unknown, not zero.
    # Counts are trusted only with positive evidence that collection finished: the file
    # being written (complete) proves nothing, e.g. an early hook can abort with exit 3.
    collected_ok = data is not None and data["collection_completed"] and rc != 4
    selected = list(dict.fromkeys(data["selected"])) if collected_ok else None  # type: ignore[index]
    deselected = list(dict.fromkeys(data["deselected"])) if collected_ok else None  # type: ignore[index]
    rows = _path_rows(paths, selected, deselected)
    a["path_evidence"] = rows
    for row in rows:
        if not row["exists"]:
            reasons.append(f"configured path missing: {row['path']}")
    if data is None:
        reasons.append("collection evidence unavailable (helper output missing, unreadable or incomplete)")
        return ("COLLECTION UNKNOWN" if rc == 0 else "COLLECTION FAIL"), a
    if selected is None or deselected is None:
        if rc != 4 and not data["collection_completed"]:
            reasons.append("collection did not complete; counts unknown")
        return ("COLLECTION UNKNOWN" if rc == 0 else "COLLECTION FAIL"), a

    a.update(
        collected_count=len(selected) + len(deselected),
        selected_count=len(selected),
        deselected_count=len(deselected),
        collection_errors=data["error_count"],
        pytest_version=data.get("pytest_version"),
        count_source="collection_helper",
        summary_line=(
            f"{len(selected)} selected / {len(selected) + len(deselected)} collected "
            f"({len(deselected)} deselected); executed=0 (collection only)"
        ),
        evidence={
            "selected": selected,
            "deselected": deselected,
            "errors": data["errors"],
            "error_count": data["error_count"],
            "path_evidence": rows,
        },
    )
    if data["error_count"]:
        reasons.append(f"{data['error_count']} collection error(s)")
    if not selected and rc != 5:
        reasons.append("zero tests selected")
    for row in rows:
        if row["exists"] and row["selected"] == 0:
            reasons.append(
                f"configured path selected zero tests: {row['path']} "
                f"(collected {row['collected']}, deselected {row['deselected']})"
            )
    return ("COLLECTION PASS" if not reasons else "COLLECTION FAIL"), a


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--target", choices=sorted(TARGETS), default="default")
    ap.add_argument("--name", default=None, help="optional human run name for the receipt")
    ap.add_argument("--collect-only", action="store_true", help="pass --collect-only to pytest (collection verification only)")
    ap.add_argument("pytest_args", nargs="*", help="extra pytest args appended verbatim")
    args = ap.parse_args(argv)

    collect_mode = args.collect_only or bool(_COLLECT_FLAGS & set(args.pytest_args))
    mode = "collection" if collect_mode else "execution"

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"cert_{stamp}_{uuid.uuid4().hex[:8]}"
    label = args.name or run_id
    temp_dir = ARTIFACTS / "test-temp" / run_id
    tmp_for_children = temp_dir / "child-tmp"
    basetemp = temp_dir / "basetemp"
    basetemp.mkdir(parents=True, exist_ok=True)
    tmp_for_children.mkdir(parents=True, exist_ok=True)

    receipt_dir = ARTIFACTS / "cert-receipts"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_dir / f"{run_id}.json"
    log_path = receipt_path.with_suffix(".stdout.txt")
    err_path = receipt_path.with_suffix(".stderr.txt")

    python_exe = _python_exe()
    paths = list(TARGETS[args.target])
    plugin_dir = temp_dir / "plugin"
    evidence_file = temp_dir / "collection-evidence.json"
    cmd = [
        python_exe,
        "-m",
        "pytest",
        *paths,
        "-m",
        "not experimental",
        "--tb=short",
        "-q",
        f"--basetemp={basetemp}",
        "-p",
        "no:cacheprovider",
        *(["--collect-only"] if args.collect_only else []),
        *(["-p", _COLLECT_PLUGIN_MODULE] if collect_mode else []),
        *args.pytest_args,
    ]

    env = os.environ.copy()
    env["TMPDIR"] = env["TEMP"] = env["TMP"] = str(tmp_for_children)
    env["PYTHONPATH"] = str(ROOT)
    env["SINTRAPRIME_TEST_LANES"] = LANE_ENV[args.target]
    # G0-R4.1: default-deny outbound network for certification execution (loopback allowed).
    env["SINTRAPRIME_CERT_NET_GUARD"] = "1"
    if collect_mode:
        env["PYTHONPATH"] = os.pathsep.join([str(ROOT), str(plugin_dir)])
        env[_COLLECT_EVIDENCE_ENV] = str(evidence_file)

    started = datetime.now(UTC).isoformat()
    t0 = time.monotonic()
    # G0-R4.1 ER-003: per-test timeout (pytest-timeout) + lane wall-clock cap.
    # A timeout is a clear certification failure, never a silent cancellation.
    cmd = [*cmd, f"--timeout={PER_TEST_TIMEOUT_SECONDS}", "--timeout-method=thread"]
    status = "completed"
    proc = None
    launch_error = None
    out_text = err_text = ""
    try:
        if collect_mode:
            plugin_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(_COLLECT_PLUGIN_FILE, plugin_dir / _COLLECT_PLUGIN_FILE.name)
        proc = subprocess.run(
            cmd, cwd=ROOT, capture_output=True, text=True, errors="replace", env=env,
            timeout=WALL_CLOCK_TIMEOUT_SECONDS,
        )
        out_text, err_text = _as_text(proc.stdout), _as_text(proc.stderr)
    except subprocess.TimeoutExpired as exc:
        status = "wall_clock_timeout"
        out_text, err_text = _as_text(exc.stdout), _as_text(exc.stderr)
    except (OSError, subprocess.SubprocessError) as exc:
        status = "launch_error"
        launch_error = f"{type(exc).__name__}: {exc}"
    duration = time.monotonic() - t0
    finished = datetime.now(UTC).isoformat()

    # Always keep whatever output exists, whatever happened to the child.
    log_path.write_text(out_text, encoding="utf-8")
    err_path.write_text(err_text, encoding="utf-8")

    pass_label = "COLLECTION PASS" if collect_mode else "PASS"
    rc = proc.returncode if proc is not None else None
    if status == "wall_clock_timeout":
        gate_result, a = ("COLLECTION FAIL" if collect_mode else "FAIL"), _blank_analysis()
        a["reasons"] = [f"lane wall-clock timeout ({WALL_CLOCK_TIMEOUT_SECONDS}s); outcome unknown"]
        exit_code = EXIT_WALL_CLOCK_TIMEOUT
    elif status == "launch_error":
        gate_result, a = ("COLLECTION FAIL" if collect_mode else "FAIL"), _blank_analysis()
        a["reasons"] = [f"pytest subprocess could not be launched ({launch_error}); outcome unknown"]
        exit_code = EXIT_LAUNCH_ERROR
    else:
        if collect_mode:
            gate_result, a = _analyze_collection(evidence_file, rc, paths)
        else:
            gate_result, a = _analyze_execution(out_text, rc)
        exit_code = rc if rc != 0 else (EXIT_EVIDENCE_GATE if a["reasons"] else 0)
    gate_passed = gate_result == pass_label

    evidence_out = None
    if a["evidence"] is not None:
        evidence_out = receipt_dir / f"{run_id}.collection.json"
        evidence_out.write_text(
            json.dumps(
                {"run_id": run_id, "target": args.target, "target_paths": paths,
                 "path_overlaps": _path_overlaps(paths), **a["evidence"]},  # type: ignore[arg-type]
                indent=2,
            ),
            encoding="utf-8",
        )

    receipt = {
        "receipt_version": RECEIPT_VERSION,
        "run_id": run_id,
        "name": label,
        "target": args.target,
        "mode": mode,
        "status": status,
        "command": cmd,
        "git_sha": _git(["rev-parse", "HEAD"]),
        "branch": _git(["branch", "--show-current"]),
        "python": python_exe,
        "host": platform.platform(),
        "basetemp": str(basetemp),
        "tmp_policy": "repo-owned, per-run unique, cache provider disabled",
        "started_at": started,
        "finished_at": finished,
        "duration_seconds": round(duration, 2),
        "passed": a["passed"],
        "failed": a["failed"],
        "skipped": a["skipped"],
        "errors": a["errors"],
        "executed_count": a["executed_count"],
        "collected_count": a["collected_count"],
        "selected_count": a["selected_count"],
        "deselected_count": a["deselected_count"],
        "collection_errors": a["collection_errors"],
        "exit_code": exit_code,
        "pytest_returncode": rc,
        "gate_result": gate_result,
        "gate_passed": gate_passed,
        "gate_reasons": a["reasons"],
        "launch_error": launch_error,
        "summary_line": a["summary_line"],
        "count_source": a["count_source"],
        "stdout_log": str(log_path),
        "stderr_log": str(err_path),
        "target_paths": paths,
        "path_overlaps": _path_overlaps(paths),
        "path_evidence": a["path_evidence"],
        "collection_evidence_file": str(evidence_out) if evidence_out else None,
        "pytest_version": a["pytest_version"],
        "pytest_args": list(args.pytest_args),
        "wall_clock_timeout_seconds": WALL_CLOCK_TIMEOUT_SECONDS,
        "per_test_timeout_seconds": PER_TEST_TIMEOUT_SECONDS,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

    cleaned = False
    if gate_passed:
        shutil.rmtree(temp_dir, ignore_errors=True)
        cleaned = True

    print(f"[certify] target={args.target} run={run_id} name={label} mode={mode}")
    if status == "wall_clock_timeout":
        print(f"[certify] LANE WALL-CLOCK TIMEOUT ({WALL_CLOCK_TIMEOUT_SECONDS}s) on target {args.target!r}: CERTIFICATION FAILURE")
    elif status == "launch_error":
        print(f"[certify] SUBPROCESS LAUNCH ERROR on target {args.target!r}: {launch_error}")
    if collect_mode and a["selected_count"] is not None:
        headline = (
            f"selected={a['selected_count']} collected={a['collected_count']} "
            f"deselected={a['deselected_count']} executed=0 "
            "(collection only: no test was run; this is NOT runtime certification)"
        )
    elif collect_mode:
        headline = "collection evidence unavailable; counts unknown (no test was run)"
    else:
        headline = a["summary_line"] or "no summary parsed"
    print(f"[certify] {gate_result}: {headline}")
    for reason in a["reasons"]:  # type: ignore[attr-defined]
        print(f"[certify]   - {reason}")
    print(f"[certify] temp={'cleaned' if cleaned else 'PRESERVED (failure evidence)'}: {temp_dir}")
    print(f"[certify] receipt: {receipt_path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

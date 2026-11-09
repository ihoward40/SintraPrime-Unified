"""Private pytest plugin for ``scripts/certify.py --collect-only`` (not a runner).

``certify.py`` stages a copy of this file into the per-run temp directory and
loads it with ``-p``. It records, as JSON, exactly what pytest collected so the
receipt does not depend on pytest's verbosity-sensitive text output (the repo's
``addopts`` already contains ``-q``, which turns node ids into per-file counts).

It never runs, selects or deselects tests. It only observes. The evidence file
is written at session finish with ``complete: true``; a missing, unreadable or
incomplete file means the evidence is unavailable and must be treated as unknown.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

SCHEMA = 2
_phase = {"hook_returned": False, "modify_done": False, "finish_called": False}
EVIDENCE_ENV = "SINTRAPRIME_CERT_COLLECT_JSON"
_MAX_ERRORS = 100

_selected: list[str] = []
_deselected: list[str] = []
_errors: list[dict[str, str]] = []
_error_total = 0


@pytest.hookimpl(wrapper=True)
def pytest_collection():
    """Positive evidence that the collection hook returned without raising."""
    result = yield
    _phase["hook_returned"] = True
    return result


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems():
    # Reached only if every earlier modifyitems impl (incl. -m/-k deselection) returned.
    _phase["modify_done"] = True


def pytest_collectreport(report):
    global _error_total
    if not report.failed:
        return
    _error_total += 1
    if len(_errors) < _MAX_ERRORS:
        lines = [ln for ln in str(report.longreprtext).splitlines() if ln.strip()]
        _errors.append({"nodeid": report.nodeid, "detail": (lines[-1] if lines else "")[:500]})


def pytest_deselected(items):
    _deselected.extend(item.nodeid for item in items)


def pytest_collection_finish(session):
    # May be called from a finally block after a failure, so on its own it proves nothing.
    _phase["finish_called"] = True
    _selected[:] = [item.nodeid for item in session.items]


def pytest_sessionfinish(exitstatus):
    target = os.environ.get(EVIDENCE_ENV)
    if not target:
        return
    payload = {
        "schema": SCHEMA,
        "complete": True,  # this file was fully written; says nothing about collection
        "collection_completed": all(_phase.values()),
        "collection_phases": dict(_phase),
        "pytest_version": pytest.__version__,
        "exitstatus": int(exitstatus),
        "selected": list(_selected),
        "deselected": list(_deselected),
        "error_count": _error_total,
        "errors": list(_errors),
    }
    out = Path(target)
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    os.replace(tmp, out)

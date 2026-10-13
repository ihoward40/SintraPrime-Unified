#!/usr/bin/env python3
"""Validate collected and executed pytest outcomes against subject and floors.

This policy consumer never runs pytest. It validates the receipt emitted by
report_test_inventory.py. Collection and execution remain separate facts:
``collected`` is the collection-only total, while the execution outcomes are
reported independently and must reconcile to that total (including deselected
items) for a complete run.

For each lane, the same configured floor applies independently to both the
collected count and passed count. Failures, skips, xfails, xpasses, and
 deselections are prohibited by default; any exception requires explicit
policy changes and separate authorization.

Evaluation precedence: receipt structure, subject binding, collection
completeness, test failures, execution completeness/exit status, collection
floor, passing floor, excluded outcomes, then PASS.
"""

from __future__ import annotations

import argparse
import json

COUNT_FIELDS = (
    "collected",
    "passed",
    "failed",
    "skipped",
    "xfailed",
    "xpassed",
    "deselected",
)
EXCLUDED_FIELDS = ("skipped", "xfailed", "xpassed", "deselected")
REQUIRED_FIELDS = (
    "commit",
    "tree",
    "collected",
    "incomplete",
    "collection_return_code",
    "passed",
    "failed",
    "skipped",
    "xfailed",
    "xpassed",
    "deselected",
    "execution_return_code",
    "execution_complete",
    "execution_errors",
)


class Verdict:
    """Plain value object compatible with importlib test loading."""

    __slots__ = ("detail", "passed", "reason")

    def __init__(self, passed: bool, reason: str, detail: str):
        self.passed = passed
        self.reason = reason
        self.detail = detail

    def __repr__(self) -> str:
        return f"Verdict(passed={self.passed!r}, reason={self.reason!r}, detail={self.detail!r})"


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_receipt(receipt) -> Verdict | None:
    """Return a failure verdict for malformed/internally inconsistent data."""
    if not isinstance(receipt, dict):
        return Verdict(False, "INVALID_RECEIPT", "receipt is not a JSON object")
    missing = [field for field in REQUIRED_FIELDS if field not in receipt]
    if missing:
        return Verdict(False, "INVALID_RECEIPT", f"missing fields: {', '.join(missing)}")
    for field in ("commit", "tree"):
        if not isinstance(receipt[field], str) or not receipt[field]:
            return Verdict(False, "INVALID_RECEIPT", f"{field} must be a non-empty string")
    for field in COUNT_FIELDS:
        if not _is_int(receipt[field]) or receipt[field] < 0:
            return Verdict(False, "INVALID_RECEIPT", f"{field} must be a non-negative integer")
    for field in ("collection_return_code", "execution_return_code"):
        if not _is_int(receipt[field]):
            return Verdict(False, "INVALID_RECEIPT", f"{field} must be an integer")
    for field in ("incomplete", "execution_complete"):
        if not isinstance(receipt[field], bool):
            return Verdict(False, "INVALID_RECEIPT", f"{field} must be a boolean")
    if not isinstance(receipt["execution_errors"], list) or any(
        not isinstance(error, str) for error in receipt["execution_errors"]
    ):
        return Verdict(False, "INVALID_RECEIPT", "execution_errors must be a list of strings")

    # Partial or interrupted runs are rejected later as incomplete. For a
    # complete collection and execution, every collected item must have exactly
    # one final execution disposition or be explicitly recorded as deselected.
    if not receipt["incomplete"] and receipt["execution_complete"]:
        outcomes = sum(receipt[field] for field in ("passed", "failed", "skipped", "xfailed", "xpassed", "deselected"))
        if outcomes != receipt["collected"]:
            return Verdict(
                False,
                "INVALID_RECEIPT",
                f"outcome total={outcomes} does not equal collected={receipt['collected']}",
            )
    return None


def evaluate(receipt, expect_commit: str, expect_tree: str, minimum_floor: int) -> Verdict:
    """Pure policy evaluation; does not access files, processes, or services."""
    if not _is_int(minimum_floor) or minimum_floor < 0:
        return Verdict(False, "INVALID_FLOOR", "minimum_floor must be a non-negative integer")

    invalid = validate_receipt(receipt)
    if invalid is not None:
        return invalid

    if receipt["commit"] != expect_commit or receipt["tree"] != expect_tree:
        return Verdict(False, "STALE_SUBJECT", "receipt commit/tree do not match expected subject")
    if receipt["incomplete"] or receipt["collection_return_code"] != 0:
        return Verdict(
            False,
            "INCOMPLETE_COLLECTION",
            f"incomplete={receipt['incomplete']} collection_return_code={receipt['collection_return_code']}",
        )
    if receipt["failed"]:
        return Verdict(False, "TEST_FAILURES", f"failed={receipt['failed']} (required 0)")
    if (
        not receipt["execution_complete"]
        or receipt["execution_return_code"] != 0
        or receipt["execution_errors"]
    ):
        return Verdict(
            False,
            "INCOMPLETE_EXECUTION",
            f"complete={receipt['execution_complete']} return_code={receipt['execution_return_code']} "
            f"errors={len(receipt['execution_errors'])}",
        )
    if receipt["collected"] < minimum_floor:
        return Verdict(
            False,
            "COLLECTION_FLOOR_VIOLATION",
            f"collected={receipt['collected']} < minimum_floor={minimum_floor}",
        )
    if receipt["passed"] < minimum_floor:
        return Verdict(
            False,
            "PASSING_FLOOR_VIOLATION",
            f"passed={receipt['passed']} < minimum_passed={minimum_floor}",
        )
    excluded = {field: receipt[field] for field in EXCLUDED_FIELDS if receipt[field]}
    if excluded:
        return Verdict(False, "EXCLUDED_TESTS", f"nonzero skipped/xfail/xpass/deselected outcomes: {excluded}")
    return Verdict(
        True,
        "PASS",
        f"collected={receipt['collected']} passed={receipt['passed']} "
        f"minimum_floor={minimum_floor}; failures and exclusions are zero",
    )


def load_receipt(path: str):
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)


def _report(name: str | None, verdict: Verdict) -> None:
    label = f"[{name}] " if name else ""
    status = "PASS" if verdict.passed else "FAIL"
    print(f"{label}{status} / {verdict.reason}: {verdict.detail}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--receipt", required=True, help="Path to the inventory/execution JSON receipt")
    parser.add_argument("--expect-commit", required=True)
    parser.add_argument("--expect-tree", required=True)
    parser.add_argument("--floor", required=True, type=int, dest="minimum_floor")
    parser.add_argument("--name", default=None, help="Label for log output only")
    args = parser.parse_args(argv)

    try:
        receipt = load_receipt(args.receipt)
    except FileNotFoundError:
        _report(args.name, Verdict(False, "MISSING_RECEIPT", f"receipt file not found: {args.receipt}"))
        return 1
    except (json.JSONDecodeError, OSError) as exc:
        _report(args.name, Verdict(False, "INVALID_RECEIPT", f"receipt cannot be read: {exc}"))
        return 1

    verdict = evaluate(receipt, args.expect_commit, args.expect_tree, args.minimum_floor)
    _report(args.name, verdict)
    return 0 if verdict.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

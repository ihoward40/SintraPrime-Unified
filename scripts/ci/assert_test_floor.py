#!/usr/bin/env python3
"""Evaluate a report_test_inventory.py receipt against a subject binding and a
minimum collection floor.

This is a POLICY CONSUMER ONLY. It never invokes pytest and never performs
its own collection; it reads the JSON receipt already produced by
scripts/ci/report_test_inventory.py and applies a fixed evaluation
precedence. Keeping measurement (report_test_inventory.py) and policy
(this script) in separate tools avoids a second, divergent pytest-counting
implementation.

Required receipt fields (as emitted by report_test_inventory.py):
    commit                  (str)  subject commit this receipt was measured on
    tree                    (str)  subject tree this receipt was measured on
    collected               (int)  observed collection count
    incomplete              (bool) True if collection did not complete cleanly
    collection_return_code  (int)  pytest --collect-only return code

Evaluation precedence (first match wins):
    0. SUBJECT_BINDING
         receipt commit/tree != expected           -> FAIL / STALE_SUBJECT
    1. RECEIPT_VALIDITY
         malformed/missing/mistyped fields          -> FAIL / INVALID_RECEIPT
    2. COLLECTION_COMPLETENESS
         incomplete is True OR
         collection_return_code != 0                -> FAIL / INCOMPLETE_COLLECTION
         (an incomplete collection produces no admissible count)
    3. FLOOR
         collected < minimum_floor                  -> FAIL / COLLECTION_FLOOR_VIOLATION
         collected >= minimum_floor                  -> PASS

Wave 1 deliberately does NOT implement expected_count, PASS_WITH_DRIFT, drift
obligations/events, or exact_count_required. Those belong to a future
Wave 1B and must not be added here without separate authorization.

Usage:
    python scripts/ci/assert_test_floor.py \
        --receipt artifacts/ci/governance-inventory.json \
        --expect-commit <sha> --expect-tree <sha> \
        --floor 137 [--name governance]
"""

from __future__ import annotations

import argparse
import json

REQUIRED_FIELDS = ("commit", "tree", "collected", "incomplete", "collection_return_code")


class Verdict:
    """Plain value object (not a dataclass: this module may be exec'd via
    importlib.util.module_from_spec by test harnesses before it is inserted
    into sys.modules, which breaks dataclasses' PEP 563 type-resolution)."""

    __slots__ = ("detail", "passed", "reason")

    def __init__(self, passed: bool, reason: str, detail: str):
        self.passed = passed
        self.reason = reason
        self.detail = detail

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"Verdict(passed={self.passed!r}, reason={self.reason!r}, detail={self.detail!r})"


def _is_int_like(value) -> bool:
    """True for a real int, excluding bool (bool is an int subclass in Python)."""
    return isinstance(value, int) and not isinstance(value, bool)


def validate_receipt(receipt) -> Verdict | None:
    """Return a FAIL Verdict if the receipt is structurally invalid, else None."""
    if not isinstance(receipt, dict):
        return Verdict(False, "INVALID_RECEIPT", "receipt is not a JSON object")
    missing = [f for f in REQUIRED_FIELDS if f not in receipt]
    if missing:
        return Verdict(
            False, "INVALID_RECEIPT", f"missing required field(s): {', '.join(missing)}"
        )
    if not isinstance(receipt["commit"], str) or not receipt["commit"]:
        return Verdict(False, "INVALID_RECEIPT", "commit must be a non-empty string")
    if not isinstance(receipt["tree"], str) or not receipt["tree"]:
        return Verdict(False, "INVALID_RECEIPT", "tree must be a non-empty string")
    if not _is_int_like(receipt["collected"]):
        return Verdict(False, "INVALID_RECEIPT", "collected must be an integer")
    if receipt["collected"] < 0:
        return Verdict(False, "INVALID_RECEIPT", "collected must not be negative")
    if not isinstance(receipt["incomplete"], bool):
        return Verdict(False, "INVALID_RECEIPT", "incomplete must be a boolean")
    if not _is_int_like(receipt["collection_return_code"]):
        return Verdict(False, "INVALID_RECEIPT", "collection_return_code must be an integer")
    return None


def evaluate(receipt, expect_commit: str, expect_tree: str, minimum_floor: int) -> Verdict:
    """Pure policy evaluation. Never touches the filesystem or a subprocess."""
    if not _is_int_like(minimum_floor) or minimum_floor < 0:
        return Verdict(False, "INVALID_FLOOR", "minimum_floor must be a non-negative integer")

    invalid = validate_receipt(receipt)
    if invalid is not None:
        # A structurally invalid receipt has nothing meaningful to bind
        # against, so INVALID_RECEIPT takes priority over SUBJECT_BINDING.
        return invalid

    if receipt["commit"] != expect_commit or receipt["tree"] != expect_tree:
        return Verdict(
            False,
            "STALE_SUBJECT",
            f"receipt subject commit={receipt['commit']!r} tree={receipt['tree']!r} "
            f"!= expected commit={expect_commit!r} tree={expect_tree!r}",
        )

    if receipt["incomplete"] or receipt["collection_return_code"] != 0:
        return Verdict(
            False,
            "INCOMPLETE_COLLECTION",
            f"incomplete={receipt['incomplete']} "
            f"collection_return_code={receipt['collection_return_code']}; "
            "an incomplete collection produces no admissible count",
        )

    collected = receipt["collected"]
    if collected < minimum_floor:
        return Verdict(
            False,
            "COLLECTION_FLOOR_VIOLATION",
            f"collected={collected} < minimum_floor={minimum_floor}",
        )

    return Verdict(True, "PASS", f"collected={collected} >= minimum_floor={minimum_floor}")


def load_receipt(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _report(name: str | None, verdict: Verdict) -> None:
    label = f"[{name}] " if name else ""
    status = "PASS" if verdict.passed else "FAIL"
    print(f"{label}{status} / {verdict.reason}: {verdict.detail}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--receipt", required=True, help="Path to a report_test_inventory.py JSON receipt")
    ap.add_argument("--expect-commit", required=True, help="Expected subject commit SHA")
    ap.add_argument("--expect-tree", required=True, help="Expected subject tree SHA")
    ap.add_argument("--floor", required=True, type=int, dest="minimum_floor", help="Minimum admissible collected count")
    ap.add_argument("--name", default=None, help="Label for log output only")
    args = ap.parse_args(argv)

    try:
        receipt = load_receipt(args.receipt)
    except FileNotFoundError:
        _report(args.name, Verdict(False, "MISSING_RECEIPT", f"receipt file not found: {args.receipt}"))
        return 1
    except json.JSONDecodeError as exc:
        _report(args.name, Verdict(False, "INVALID_RECEIPT", f"malformed JSON: {exc}"))
        return 1

    verdict = evaluate(receipt, args.expect_commit, args.expect_tree, args.minimum_floor)
    _report(args.name, verdict)
    return 0 if verdict.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

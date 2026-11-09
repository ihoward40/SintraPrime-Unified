"""Deterministic unit and CLI tests for the test-floor policy consumer."""

import importlib.util
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "assert_test_floor.py")
spec = importlib.util.spec_from_file_location("assert_test_floor", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


COMMIT = "a" * 40
TREE = "b" * 40
FLOOR = 58


def receipt(**updates):
    result = {
        "commit": COMMIT,
        "tree": TREE,
        "collected": FLOOR,
        "incomplete": False,
        "collection_return_code": 0,
        "passed": FLOOR,
        "failed": 0,
        "skipped": 0,
        "xfailed": 0,
        "xpassed": 0,
        "deselected": 0,
        "execution_return_code": 0,
        "execution_complete": True,
        "execution_errors": [],
    }
    result.update(updates)
    return result


def test_exact_floor_and_passed_floor_pass():
    verdict = mod.evaluate(receipt(), COMMIT, TREE, FLOOR)
    assert verdict.passed is True
    assert verdict.reason == "PASS"


def test_collected_count_is_not_passed_count():
    verdict = mod.evaluate(receipt(passed=FLOOR - 1, failed=1, execution_return_code=1), COMMIT, TREE, FLOOR)
    assert verdict.passed is False
    assert verdict.reason == "TEST_FAILURES"


def test_fails_below_collection_floor():
    verdict = mod.evaluate(receipt(collected=FLOOR - 1, passed=FLOOR - 1), COMMIT, TREE, FLOOR)
    assert verdict.reason == "COLLECTION_FLOOR_VIOLATION"


def test_fails_below_passed_floor_even_when_collection_is_high():
    verdict = mod.evaluate(
        receipt(collected=FLOOR + 1, passed=FLOOR - 1, skipped=2), COMMIT, TREE, FLOOR
    )
    assert verdict.reason == "PASSING_FLOOR_VIOLATION"


def test_stale_commit_or_tree_fails():
    assert mod.evaluate(receipt(), "c" * 40, TREE, FLOOR).reason == "STALE_SUBJECT"
    assert mod.evaluate(receipt(), COMMIT, "d" * 40, FLOOR).reason == "STALE_SUBJECT"


def test_malformed_receipt_takes_precedence_over_stale_subject():
    value = receipt()
    del value["passed"]
    assert mod.evaluate(value, "c" * 40, TREE, FLOOR).reason == "INVALID_RECEIPT"


def test_missing_or_wrongly_typed_fields_fail_closed():
    assert mod.validate_receipt([]).reason == "INVALID_RECEIPT"
    value = receipt()
    del value["execution_return_code"]
    assert mod.validate_receipt(value).reason == "INVALID_RECEIPT"
    assert mod.validate_receipt(receipt(passed=True)).reason == "INVALID_RECEIPT"
    assert mod.validate_receipt(receipt(collected=-1, passed=-1)).reason == "INVALID_RECEIPT"
    assert mod.validate_receipt(receipt(incomplete=1)).reason == "INVALID_RECEIPT"
    assert mod.validate_receipt(receipt(execution_errors="none")).reason == "INVALID_RECEIPT"


def test_incomplete_collection_fails():
    value = receipt(incomplete=True, collection_return_code=1, collected=40, passed=0)
    assert mod.evaluate(value, COMMIT, TREE, FLOOR).reason == "INCOMPLETE_COLLECTION"


def test_nonzero_collection_exit_fails_even_if_not_marked_incomplete():
    value = receipt(collection_return_code=2)
    assert mod.evaluate(value, COMMIT, TREE, FLOOR).reason == "INCOMPLETE_COLLECTION"


def test_execution_nonzero_or_incomplete_fails():
    assert mod.evaluate(receipt(execution_return_code=2, execution_complete=False), COMMIT, TREE, FLOOR).reason == "INCOMPLETE_EXECUTION"
    assert mod.evaluate(receipt(execution_errors=["runner error"]), COMMIT, TREE, FLOOR).reason == "INCOMPLETE_EXECUTION"


def test_skipped_xfailed_xpassed_and_deselected_each_fail():
    for field in ("skipped", "xfailed", "xpassed", "deselected"):
        value = receipt(collected=FLOOR + 1, passed=FLOOR, **{field: 1})
        assert mod.evaluate(value, COMMIT, TREE, FLOOR).reason == "EXCLUDED_TESTS"


def test_impossible_outcome_total_fails():
    value = receipt(passed=FLOOR - 1)
    assert mod.validate_receipt(value).reason == "INVALID_RECEIPT"


def test_invalid_floor_fails():
    assert mod.evaluate(receipt(), COMMIT, TREE, -1).reason == "INVALID_FLOOR"
    assert mod.evaluate(receipt(), COMMIT, TREE, True).reason == "INVALID_FLOOR"


def test_cli_missing_and_malformed_receipts_fail(tmp_path):
    missing = tmp_path / "missing.json"
    args = ["--receipt", str(missing), "--expect-commit", COMMIT, "--expect-tree", TREE, "--floor", str(FLOOR)]
    assert mod.main(args) == 1
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{bad", encoding="utf-8")
    args[1] = str(malformed)
    assert mod.main(args) == 1


def test_cli_valid_receipt_passes(tmp_path):
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(receipt()), encoding="utf-8")
    args = ["--receipt", str(path), "--expect-commit", COMMIT, "--expect-tree", TREE, "--floor", str(FLOOR)]
    assert mod.main(args) == 0

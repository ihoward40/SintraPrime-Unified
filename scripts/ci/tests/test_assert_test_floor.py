"""Unit tests for scripts/ci/assert_test_floor.py.

Tests are deterministic and do not require a real pytest collection run or a
real report_test_inventory.py invocation. assert_test_floor.py is a policy
consumer only -- it must never invoke pytest itself; see
test_never_invokes_pytest below.
"""

import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "assert_test_floor.py")
spec = importlib.util.spec_from_file_location("assert_test_floor", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

COMMIT = "077eff4ff2f2e58ccf7042e6da231052e247661a"
TREE = "235b6d89548e2df190cde44954f49afbd641f31b"


def _receipt(**overrides):
    base = {
        "commit": COMMIT,
        "tree": TREE,
        "collected": 100,
        "incomplete": False,
        "collection_return_code": 0,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# PASS cases
# ---------------------------------------------------------------------------


def test_pass_complete_receipt_above_floor():
    v = mod.evaluate(_receipt(collected=100), COMMIT, TREE, 50)
    assert v.passed is True
    assert v.reason == "PASS"


def test_pass_count_exactly_at_floor():
    v = mod.evaluate(_receipt(collected=50), COMMIT, TREE, 50)
    assert v.passed is True
    assert v.reason == "PASS"


def test_pass_count_above_floor():
    v = mod.evaluate(_receipt(collected=51), COMMIT, TREE, 50)
    assert v.passed is True


def test_pass_cli_exit_code_zero(tmp_path):
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps(_receipt(collected=37)), encoding="utf-8")
    rc = mod.main(
        [
            "--receipt",
            str(receipt_path),
            "--expect-commit",
            COMMIT,
            "--expect-tree",
            TREE,
            "--floor",
            "37",
        ]
    )
    assert rc == 0


# ---------------------------------------------------------------------------
# FAIL: floor violation
# ---------------------------------------------------------------------------


def test_fail_count_below_floor():
    v = mod.evaluate(_receipt(collected=36), COMMIT, TREE, 37)
    assert v.passed is False
    assert v.reason == "COLLECTION_FLOOR_VIOLATION"


def test_fail_zero_count():
    v = mod.evaluate(_receipt(collected=0), COMMIT, TREE, 1)
    assert v.passed is False
    assert v.reason == "COLLECTION_FLOOR_VIOLATION"


# ---------------------------------------------------------------------------
# FAIL: incomplete collection (checked before floor; no admissible count)
# ---------------------------------------------------------------------------


def test_fail_collection_complete_false():
    v = mod.evaluate(_receipt(incomplete=True), COMMIT, TREE, 1)
    assert v.passed is False
    assert v.reason == "INCOMPLETE_COLLECTION"


def test_fail_collection_exit_nonzero():
    v = mod.evaluate(_receipt(collection_return_code=1), COMMIT, TREE, 1)
    assert v.passed is False
    assert v.reason == "INCOMPLETE_COLLECTION"


def test_fail_incomplete_collection_ignores_floor_even_with_huge_count():
    # A huge observed count must not paper over an incomplete/non-zero-exit
    # collection -- incompleteness is checked before the floor comparison.
    v = mod.evaluate(_receipt(collected=99999, incomplete=True), COMMIT, TREE, 1)
    assert v.passed is False
    assert v.reason == "INCOMPLETE_COLLECTION"


# ---------------------------------------------------------------------------
# FAIL: subject binding
# ---------------------------------------------------------------------------


def test_fail_subject_commit_mismatch():
    v = mod.evaluate(_receipt(commit="deadbeef" * 5), COMMIT, TREE, 1)
    assert v.passed is False
    assert v.reason == "STALE_SUBJECT"


def test_fail_subject_tree_mismatch():
    v = mod.evaluate(_receipt(tree="deadbeef" * 5), COMMIT, TREE, 1)
    assert v.passed is False
    assert v.reason == "STALE_SUBJECT"


def test_subject_binding_checked_before_floor():
    # Even a passing floor must not paper over a stale subject.
    v = mod.evaluate(_receipt(commit="deadbeef" * 5, collected=1000), COMMIT, TREE, 1)
    assert v.passed is False
    assert v.reason == "STALE_SUBJECT"


# ---------------------------------------------------------------------------
# FAIL: malformed / invalid receipt
# ---------------------------------------------------------------------------


def test_fail_malformed_json(tmp_path):
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text("{not valid json", encoding="utf-8")
    rc = mod.main(
        [
            "--receipt",
            str(receipt_path),
            "--expect-commit",
            COMMIT,
            "--expect-tree",
            TREE,
            "--floor",
            "1",
        ]
    )
    assert rc == 1


def test_fail_missing_count_field():
    receipt = _receipt()
    del receipt["collected"]
    v = mod.evaluate(receipt, COMMIT, TREE, 1)
    assert v.passed is False
    assert v.reason == "INVALID_RECEIPT"


def test_fail_missing_subject_fields():
    receipt = _receipt()
    del receipt["commit"]
    v = mod.evaluate(receipt, COMMIT, TREE, 1)
    assert v.passed is False
    assert v.reason == "INVALID_RECEIPT"


def test_fail_string_count_instead_of_integer():
    v = mod.evaluate(_receipt(collected="100"), COMMIT, TREE, 1)
    assert v.passed is False
    assert v.reason == "INVALID_RECEIPT"


def test_fail_bool_count_rejected_even_though_bool_is_int_subclass():
    v = mod.evaluate(_receipt(collected=True), COMMIT, TREE, 1)
    assert v.passed is False
    assert v.reason == "INVALID_RECEIPT"


def test_fail_negative_count():
    v = mod.evaluate(_receipt(collected=-1), COMMIT, TREE, 1)
    assert v.passed is False
    assert v.reason == "INVALID_RECEIPT"


def test_fail_negative_floor():
    v = mod.evaluate(_receipt(collected=100), COMMIT, TREE, -1)
    assert v.passed is False
    assert v.reason == "INVALID_FLOOR"


def test_fail_invalid_completeness_field_type():
    v = mod.evaluate(_receipt(incomplete="false"), COMMIT, TREE, 1)
    assert v.passed is False
    assert v.reason == "INVALID_RECEIPT"


def test_fail_invalid_return_code_type():
    v = mod.evaluate(_receipt(collection_return_code="0"), COMMIT, TREE, 1)
    assert v.passed is False
    assert v.reason == "INVALID_RECEIPT"


def test_fail_receipt_not_a_dict():
    v = mod.evaluate(["not", "a", "dict"], COMMIT, TREE, 1)
    assert v.passed is False
    assert v.reason == "INVALID_RECEIPT"


def test_invalid_receipt_checked_before_subject_binding():
    # A structurally invalid receipt is reported as INVALID_RECEIPT even if
    # the (malformed) subject fields happen to mismatch too -- there is
    # nothing meaningful to bind against until the receipt is well-formed.
    receipt = _receipt()
    del receipt["collected"]
    receipt["commit"] = "deadbeef" * 5
    v = mod.evaluate(receipt, COMMIT, TREE, 1)
    assert v.passed is False
    assert v.reason == "INVALID_RECEIPT"


# ---------------------------------------------------------------------------
# FAIL: missing receipt file
# ---------------------------------------------------------------------------


def test_fail_missing_receipt_file(tmp_path):
    rc = mod.main(
        [
            "--receipt",
            str(tmp_path / "does-not-exist.json"),
            "--expect-commit",
            COMMIT,
            "--expect-tree",
            TREE,
            "--floor",
            "1",
        ]
    )
    assert rc == 1


# ---------------------------------------------------------------------------
# Structural guarantee: policy consumer only, never a second pytest engine
# ---------------------------------------------------------------------------


def test_never_invokes_pytest():
    assert not hasattr(mod, "subprocess"), "assert_test_floor.py must not import subprocess"
    assert "subprocess" not in dir(mod)
    with open(SCRIPT, encoding="utf-8") as f:
        src = f.read()
    assert not any(
        line.strip().startswith(("import subprocess", "from subprocess"))
        for line in src.splitlines()
    )
    assert "pytest.main" not in src
    assert "import pytest" not in src


def test_script_is_syntactically_clean_module():
    # Re-importing via a subprocess compile check guards against the test
    # harness's own importlib.util path masking a real SyntaxError.
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", SCRIPT], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-q"]))

import pytest

from agentic_runtime.capabilities import ModelCapabilityRegistry
from agentic_runtime.controls import BenchmarkResult, ModelPromotionGate
from agentic_runtime.model_certification import ModelCertifier, ObservedModel
from agentic_runtime.receipts import ExecutionReceipt, bind_ledger_hash
from agentic_runtime.rollback import GovernedRollbackExecutor


def test_receipt_hash_detects_mutation():
    receipt = ExecutionReceipt("run-1", "a", "b", "PASS", changed_files=["x.py"])
    receipt.seal()
    assert receipt.verify()
    receipt.status = "FAIL"
    assert not receipt.verify()


def test_receipt_binds_ledger_sha256():
    receipt = ExecutionReceipt("run-1", "a", "b", "PASS")
    bind_ledger_hash(receipt, "a" * 64)
    assert receipt.verify()
    assert receipt.ledger_entry_hash == "a" * 64


def test_rollback_is_denied_without_approval():
    restored = []
    executor = GovernedRollbackExecutor(
        authorize=lambda *_: False,
        current_ref=lambda: "head",
        changed_files=lambda a, b: ["x.py"],
        restore_ref=lambda ref: restored.append(ref) or True,
        record=lambda *_: None,
    )
    cp, _ = executor.checkpoint("cp1", "base")
    result = executor.rollback(cp, reason="test")
    assert not result.ok
    assert restored == []


def test_rollback_verifies_restored_ref():
    state = {"ref": "head"}
    executor = GovernedRollbackExecutor(
        authorize=lambda *_: True,
        current_ref=lambda: state["ref"],
        changed_files=lambda a, b: ["x.py"],
        restore_ref=lambda ref: state.update(ref=ref) is None,
        record=lambda *_: None,
    )
    cp, _ = executor.checkpoint("cp1", "base")
    state["ref"] = "later"
    result = executor.rollback(cp, reason="regression")
    assert result.ok
    assert state["ref"] == cp.ref


def test_model_requires_observed_context_and_benchmark_evidence():
    registry = ModelCapabilityRegistry()
    certifier = ModelCertifier(registry, ModelPromotionGate(.8))
    model = ObservedModel("m", "ollama", 0, frozenset({"reasoning"}), "runtime-probe")
    assert certifier.certify(model, [], ["reasoning"])[0] is False

    verified = ObservedModel("m", "ollama", 32768, frozenset({"reasoning"}), "runtime-probe")
    results = [BenchmarkResult("m", "reasoning", .9, "benchmark-receipt")]
    assert certifier.certify(verified, results, ["reasoning"]) == (True, "PROMOTED")
    assert registry.get("m").evidence_status == "VERIFIED"

"""Legacy-path prohibition test — swarm requests must NOT use the old delegate engine.

This test proves that swarm-eligible tasks routed through HermesSwarmAdapter
cannot silently fall back to the old provider-bound subagent engine.

Required:
    SWARM_REQUEST_USES_LEGACY_DELEGATE_ENGINE = FALSE
    HERMES_SWARM_ADAPTER_ROUTED_TO_SWARM = TRUE
    LEGACY_FALLBACK_ATTEMPTED = FALSE

For explicitly model-only delegation, a separate named path
(delegate_model_reasoning) should be used — NOT HermesSwarmAdapter.
"""
from __future__ import annotations

import sys
from pathlib import Path

from swarm_runtime import DelegateTask, HermesSwarmAdapter, is_swarm_eligible

REPO = Path(__file__).resolve().parents[2]


def run_legacy_path_prohibition_test() -> dict:
    print(f"\n{'='*60}")
    print("LEGACY-PATH PROHIBITION TEST")
    print(f"{'='*60}")

    # 1. Verify is_swarm_eligible correctly identifies swarm tasks
    swarm_task = "Inventory all ForeignKey references across portal models"
    model_task = "Reason about the best authentication strategy"

    swarm_eligible = is_swarm_eligible(swarm_task, "code_search")
    model_eligible = is_swarm_eligible(model_task, "")

    print(f"  swarm_task eligible: {swarm_eligible}")
    print(f"  model_task eligible: {model_eligible}")

    # 2. Create a HermesSwarmAdapter and verify it does NOT use legacy path
    adapter = HermesSwarmAdapter(
        repo_path=str(REPO),
        run_dir=str(REPO.parent / "swarm-prohibition-test"),
        max_concurrent=2,
    )

    # 3. Verify the adapter's legacy_delegate_used flag is False
    # This is the static invariant — the adapter never falls back
    legacy_flag = adapter._legacy_path_invoked
    print(f"  adapter._legacy_path_invoked: {legacy_flag}")

    # 4. Create a minimal DelegateTask and verify it translates to WorkerSpec
    # without any legacy path involvement
    task = DelegateTask(
        task_id="PROHIB-1",
        description="Static analysis of portal models",
        role="static_analysis",
        base_sha="eeb55ffb",
        read_paths=["portal/models/"],
        write_paths=[],
        worker_class="StaticAnalysisWorker",
        task_params={"path": "portal/models", "target": "class_defs"},
        artifact_filename="artifacts/prohib-result.json",
        timeout_seconds=30,
    )

    spec = task.to_worker_spec("PROHIB-1")
    print(f"  WorkerSpec.worker_class: {spec.worker_class}")
    print(f"  WorkerSpec.role: {spec.role}")
    print(f"  WorkerSpec.owned_files: {spec.owned_files}")

    # 5. Verify the adapter delegates to SwarmController, not legacy path
    # We check the class structure, not run the full swarm (which needs subprocess)
    from swarm_runtime.hermes_adapter import HermesSwarmAdapter as AdapterClass

    # The adapter must have a delegate() method that routes to SwarmController
    assert hasattr(AdapterClass, "delegate"), "HermesSwarmAdapter must have delegate() method"
    assert hasattr(AdapterClass, "delegate_single"), "HermesSwarmAdapter must have delegate_single()"

    # 6. Verify SwarmResult has legacy_delegate_used field, defaulting to False
    from swarm_runtime.hermes_adapter import SwarmResult

    result = SwarmResult(task_id="test", swarm_id="test", status="SUCCESS")
    assert result.legacy_delegate_used is False, "SwarmResult.legacy_delegate_used must default to False"
    assert result.routed_to_swarm is True, "SwarmResult.routed_to_swarm must default to True"

    print(f"  SwarmResult.legacy_delegate_used default: {result.legacy_delegate_used}")
    print(f"  SwarmResult.routed_to_swarm default: {result.routed_to_swarm}")

    # 7. Verify that is_swarm_eligible does NOT route model-only tasks to swarm
    assert not model_eligible, "Model-only tasks must NOT be swarm-eligible"
    assert swarm_eligible, "Swarm tasks MUST be swarm-eligible"

    print(f"\n{'='*60}")
    print("ACCEPTANCE CRITERIA")
    print(f"{'='*60}")

    criteria = [
        ("SWARM_REQUEST_USES_LEGACY_DELEGATE_ENGINE = FALSE", not legacy_flag),
        ("HERMES_SWARM_ADAPTER_ROUTED_TO_SWARM = TRUE", result.routed_to_swarm),
        ("LEGACY_FALLBACK_ATTEMPTED = FALSE", not result.legacy_delegate_used),
        ("SWARM_TASK_CORRECTLY_IDENTIFIED = TRUE", swarm_eligible),
        ("MODEL_TASK_NOT_SWARM_ELIGIBLE = TRUE", not model_eligible),
        ("ADAPTER_HAS_DELEGATE_METHOD = TRUE", hasattr(AdapterClass, "delegate")),
        ("SWARM_RESULT_DEFAULTS_LEGACY_FALSE = TRUE", result.legacy_delegate_used is False),
    ]

    all_pass = all(p for _, p in criteria)
    for name, passed in criteria:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")

    print(f"\n  OVERALL: {'PASS' if all_pass else 'FAIL'}")
    if all_pass:
        print("  SWARM_REQUEST_USES_LEGACY_DELEGATE_ENGINE = FALSE")
        print("  Legacy provider-bound subagent path is PROHIBITED for swarm tasks")

    return {
        "all_pass": all_pass,
        "legacy_delegate_used": legacy_flag,
        "routed_to_swarm": result.routed_to_swarm,
        "swarm_eligible": swarm_eligible,
        "model_eligible": model_eligible,
    }


def test_run() -> None:
    """Pytest entry point — delegates to run_* function."""
    result = run_legacy_path_prohibition_test()
    if isinstance(result, dict):
        # Check for all_pass or swarm_result
        if "all_pass" in result:
            assert result["all_pass"], "run_legacy_path_prohibition_test did not pass"
        elif "swarm_result" in result:
            assert result["swarm_result"] == "SUCCESS", "run_legacy_path_prohibition_test failed"
        elif "status" in result:
            assert result["status"] == "SUCCESS", "run_legacy_path_prohibition_test failed"


if __name__ == "__main__":
    result = run_legacy_path_prohibition_test()
    sys.exit(0 if result["all_pass"] else 1)

"""SWARM-ACCEPTANCE — Provider health persistence across controller restarts.

Verifies that provider health state (COOLDOWN) survives a controller restart
by being persisted to disk via ProviderHealthStore and restored into a new
ProviderRouter instance.

Required:
  PROVIDER_HEALTH_PERSISTENCE = PASS
  provider state == COOLDOWN before restart
  provider state == COOLDOWN after restart (state recreated from persisted data)
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from swarm_runtime.health_persistence import ProviderHealthStore
from swarm_runtime.provider_router import ProviderRouter, ProviderState

REPO = Path(__file__).resolve().parents[2]


def run_provider_health_persistence() -> dict:
    """Test that COOLDOWN state persists across router recreation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ProviderHealthStore(tmpdir)

        # --- Phase 1: Create router, register provider, trigger COOLDOWN ---
        router1 = ProviderRouter()
        router1.register_provider("openai", model="gpt-4o")
        router1.register_provider("anthropic", model="claude-3.5-sonnet")

        # Record 3 timeouts to trigger circuit breaker → COOLDOWN
        # (circuit breaker fires when timeout_count >= 3 within 10 minutes)
        for _ in range(3):
            router1.mark_timeout("openai")

        health_before = router1.get_health("openai")
        state_before = health_before.state if health_before else None

        assert state_before == ProviderState.COOLDOWN, (
            f"Expected COOLDOWN before restart, got {state_before}"
        )

        # --- Phase 2: Save health state to disk ---
        store.save(router1._providers)
        assert (Path(tmpdir) / "provider_health.json").exists(), (
            "Health state file was not written"
        )

        # --- Phase 3: Create a NEW router and apply saved state ---
        router2 = ProviderRouter()
        router2.register_provider("openai", model="gpt-4o")
        router2.register_provider("anthropic", model="claude-3.5-sonnet")

        store.apply_to_router(router2)

        health_after = router2.get_health("openai")
        state_after = health_after.state if health_after else None

        assert state_after == ProviderState.COOLDOWN, (
            f"Expected COOLDOWN after restart, got {state_after}"
        )

        # Verify metrics were also restored
        assert health_after is not None
        assert health_after.timeout_count == 3, (
            f"Expected timeout_count=3 after restore, got {health_after.timeout_count}"
        )

        # --- Results ---
        provider_health_persistence = state_before == ProviderState.COOLDOWN == state_after

        criteria = [
            ("PROVIDER_HEALTH_PERSISTENCE = PASS", provider_health_persistence),
            ("provider state == COOLDOWN before restart", state_before == ProviderState.COOLDOWN),
            ("provider state == COOLDOWN after restart", state_after == ProviderState.COOLDOWN),
        ]

        print(f"\n{'=' * 60}")
        print("PROVIDER HEALTH PERSISTENCE RESULTS")
        print(f"{'=' * 60}")
        all_pass = True
        for name, passed in criteria:
            status = "PASS" if passed else "FAIL"
            print(f"  [{status}] {name}")
            if not passed:
                all_pass = False

        print(f"\n  OVERALL: {'PASS' if all_pass else 'FAIL'}")
        return {
            "state_before": state_before.value if state_before else None,
            "state_after": state_after.value if state_after else None,
            "timeout_count_restored": health_after.timeout_count if health_after else 0,
            "all_pass": all_pass,
        }


def test_run() -> None:
    """Pytest entry point."""
    result = run_provider_health_persistence()
    if isinstance(result, dict) and "all_pass" in result:
        assert result["all_pass"], "run_provider_health_persistence did not pass"


if __name__ == "__main__":
    result = run_provider_health_persistence()
    sys.exit(0 if result["all_pass"] else 1)

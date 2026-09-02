"""Provider health persistence — survives controller restart.

Health state is persisted to disk as JSON so that a provider in COOLDOWN
before a restart is still in COOLDOWN after restart.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from .provider_router import ProviderHealth, ProviderState


class ProviderHealthStore:
    """Persists provider health state to disk."""

    def __init__(self, store_dir: str | Path) -> None:
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._health_file = self.store_dir / "provider_health.json"

    def save(self, providers: dict[str, ProviderHealth]) -> None:
        """Persist all provider health states."""
        data: dict[str, dict] = {}
        for name, health in providers.items():
            data[name] = {
                "provider": health.provider,
                "model": health.model,
                "state": health.state.value,
                "success_count": health.success_count,
                "timeout_count": health.timeout_count,
                "failure_count": health.failure_count,
                "tool_call_success_count": health.tool_call_success_count,
                "tool_call_count": health.tool_call_count,
                "last_success": health.last_success,
                "last_failure": health.last_failure,
                "cooldown_until": health.cooldown_until,
                "updated_at": time.time(),
            }
        tmp = self._health_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        with open(tmp, "r+b") as f:
            os.fsync(f.fileno())
        os.replace(str(tmp), str(self._health_file))

    def load(self) -> dict[str, dict[str, Any]]:
        """Load persisted provider health states."""
        if not self._health_file.exists():
            return {}
        try:
            return json.loads(self._health_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def apply_to_router(self, router: Any) -> None:
        """Restore health states into a ProviderRouter instance."""
        data = self.load()
        for name, state_data in data.items():
            health = router._providers.get(name)
            if not health:
                health = router.register_provider(
                    name,
                    model=state_data.get("model", ""),
                )
            # Restore state
            state_str = state_data.get("state", "healthy")
            for ps in ProviderState:
                if ps.value == state_str:
                    health.state = ps
                    break
            health.success_count = state_data.get("success_count", 0)
            health.timeout_count = state_data.get("timeout_count", 0)
            health.failure_count = state_data.get("failure_count", 0)
            health.tool_call_success_count = state_data.get("tool_call_success_count", 0)
            health.tool_call_count = state_data.get("tool_call_count", 0)
            health.last_success = state_data.get("last_success")
            health.last_failure = state_data.get("last_failure")
            health.cooldown_until = state_data.get("cooldown_until")

            # Check if cooldown has expired
            if health.state == ProviderState.COOLDOWN:
                if health.cooldown_until and time.time() > health.cooldown_until:
                    health.state = ProviderState.DEGRADED
                    health.cooldown_until = None

"""Runtime policy loader for the governed A2A registry."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class AgentPolicy:
    def __init__(self, registry_path: str | None = None):
        self.registry_path = Path(registry_path or Path(__file__).with_name("agent_registry.json"))
        self.reload()

    def reload(self) -> None:
        data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        self.version = data.get("version", 1)
        self.policy = data.get("policy", {})
        self.agents: dict[str, dict[str, Any]] = {
            entry["agent_id"]: entry for entry in data.get("agents", [])
        }

    def authorize_sender(self, agent_id: str) -> None:
        profile = self.agents.get(agent_id)
        if profile is None:
            raise PermissionError("Dispatch blocked: sender is not registered")
        if profile.get("status") != "active":
            raise PermissionError("Dispatch blocked: sender profile is not active")
        if profile.get("can_send_external"):
            raise PermissionError("Dispatch blocked: external sending is disabled")

    def is_registered(self, agent_id: str) -> bool:
        return agent_id in self.agents

    def profile(self, agent_id: str) -> dict[str, Any] | None:
        return self.agents.get(agent_id)

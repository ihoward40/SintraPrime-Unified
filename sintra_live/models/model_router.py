"""Model routing for offline integration."""

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ModelDecision:
    """Immutable model routing decision."""
    mission_id: str
    task: str
    candidate_models: List[Dict[str, Any]]
    selected_model: str
    selected_version: str
    rationale: str
    fallback_chain: List[str]
    privacy_level: str
    data_policy: str
    cost_budget: int
    latency_budget_ms: int
    decision_hash: str = ""

    def __post_init__(self):
        if not self.decision_hash:
            content = f"{self.mission_id}|{self.task}|{self.selected_model}|{self.selected_version}|{self.rationale}"
            object.__setattr__(self, 'decision_hash', hashlib.sha256(content.encode()).hexdigest())


class ModelRouter:
    """Routes tasks to models per frozen D1 policy."""

    MODEL_CATALOG = {
        "synthetic-summarizer": {
            "version": "1.0.0-synthetic",
            "capabilities": ["summarize", "extract"],
            "privacy": "full",
            "data_policy": "no_persistence",
            "cost_per_1k": 0,
            "latency_ms": 10
        },
        "synthetic-reasoner": {
            "version": "1.0.0-synthetic",
            "capabilities": ["reason", "verify"],
            "privacy": "full",
            "data_policy": "no_persistence",
            "cost_per_1k": 0,
            "latency_ms": 15
        },
        "synthetic-brief-generator": {
            "version": "1.0.0-synthetic",
            "capabilities": ["generate_brief", "speech_synthesis"],
            "privacy": "full",
            "data_policy": "no_persistence",
            "cost_per_1k": 0,
            "latency_ms": 20
        }
    }

    ROUTING_POLICY = {
        "status_summary": "synthetic-summarizer",
        "authority_review": "synthetic-reasoner",
        "brief_generation": "synthetic-brief-generator",
        "fallback": "synthetic-summarizer"
    }

    def __init__(self, mission_id: str):
        self.mission_id = mission_id
        self.decisions: List[ModelDecision] = []

    def route(self, task: str, required_capabilities: List[str], privacy: str = "full", data_policy: str = "no_persistence", cost_budget: int = 1000, latency_budget_ms: int = 500) -> ModelDecision:
        """Select model for a task."""
        selected_model = self.ROUTING_POLICY.get(task, self.ROUTING_POLICY["fallback"])
        catalog_entry = self.MODEL_CATALOG[selected_model]
        
        # Verify capabilities
        available = set(catalog_entry["capabilities"])
        required = set(required_capabilities)
        if not required.issubset(available):
            raise ValueError(f"Model {selected_model} lacks required capabilities: {required - available}")

        decision = ModelDecision(
            mission_id=self.mission_id,
            task=task,
            candidate_models=[{"model": k, "version": v["version"]} for k, v in self.MODEL_CATALOG.items()],
            selected_model=selected_model,
            selected_version=catalog_entry["version"],
            rationale=f"Task '{task}' mapped to {selected_model} per routing policy",
            fallback_chain=[self.ROUTING_POLICY["fallback"]] if selected_model != self.ROUTING_POLICY["fallback"] else [],
            privacy_level=privacy,
            data_policy=data_policy,
            cost_budget=cost_budget,
            latency_budget_ms=latency_budget_ms
        )
        
        self.decisions.append(decision)
        return decision

    def get_decisions(self) -> List[ModelDecision]:
        return list(self.decisions)
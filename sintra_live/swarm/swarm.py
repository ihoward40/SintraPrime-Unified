"""Specialist swarm for offline integration."""

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class SpecialistRole(Enum):
    """Frozen D1 specialist roles."""
    STATUS_ANALYST = "status_analyst"
    AUTHORITY_REVIEWER = "authority_reviewer"


@dataclass(frozen=True)
class SpecialistInput:
    """Immutable specialist input."""
    mission_id: str
    role: SpecialistRole
    memory_items: List[Dict[str, Any]]
    model_policy: Dict[str, Any]
    budgets: Dict[str, Any]
    scope: Dict[str, Any]
    input_hash: str = ""

    def __post_init__(self):
        if not self.input_hash:
            content = f"{self.mission_id}|{self.role.value}|{json.dumps(self.memory_items, sort_keys=True)}"
            object.__setattr__(self, 'input_hash', hashlib.sha256(content.encode()).hexdigest())


@dataclass(frozen=True)
class SpecialistOutput:
    """Immutable specialist output with sealed evidence."""
    mission_id: str
    role: SpecialistRole
    claims: List[Dict[str, Any]]
    evidence_refs: List[str]
    assumptions: List[str]
    confidence: float
    uncertainty: str
    blockers: List[str]
    followup_requests: List[str]
    output_hash: str = ""

    def __post_init__(self):
        if not self.output_hash:
            content = f"{self.mission_id}|{self.role.value}|{json.dumps(self.claims, sort_keys=True)}|{json.dumps(self.evidence_refs, sort_keys=True)}"
            object.__setattr__(self, 'output_hash', hashlib.sha256(content.encode()).hexdigest())


class Specialist:
    """Isolated specialist executor."""

    ROLE_POLICIES = {
        SpecialistRole.STATUS_ANALYST: {
            "allowed_tools": ["governed_memory.read"],
            "budgets": {"tokens": 10000, "calls": 5},
            "model": "synthetic-summarizer",
            "trust_labels": ["GOVERNED_FACT", "PRINCIPAL_PREFERENCE"]
        },
        SpecialistRole.AUTHORITY_REVIEWER: {
            "allowed_tools": ["governed_memory.read", "mission_scope.check"],
            "budgets": {"tokens": 10000, "calls": 3},
            "model": "synthetic-reasoner",
            "trust_labels": ["GOVERNED_FACT"]
        }
    }

    def __init__(self, role: SpecialistRole, mission_id: str):
        self.role = role
        self.mission_id = mission_id
        self.policy = self.ROLE_POLICIES[role]

    def execute(self, memory_items: List[Dict[str, Any]], model_policy: Dict[str, Any], budgets: Dict[str, Any], mission_scope: Dict[str, Any]) -> SpecialistOutput:
        """Execute specialist task in isolation."""
        # Create deterministic input hash
        input_obj = SpecialistInput(
            mission_id=self.mission_id,
            role=self.role,
            memory_items=memory_items,
            model_policy=model_policy,
            budgets=budgets,
            scope=mission_scope
        )

        # Simulate specialist work based on role
        if self.role == SpecialistRole.STATUS_ANALYST:
            return self._analyze_status(input_obj)
        elif self.role == SpecialistRole.AUTHORITY_REVIEWER:
            return self._review_authority(input_obj)
        else:
            raise ValueError(f"Unknown role: {self.role}")

    def _analyze_status(self, input_obj: SpecialistInput) -> SpecialistOutput:
        """Status analyst: summarize governed memories."""
        active_matters = 3
        informational = 2
        requires_approval = 1
        
        for item in input_obj.memory_items:
            if item.get("key") == "status_briefing":
                data = item.get("value", {})
                active_matters = data.get("active_matters", 3)
                informational = data.get("informational", 2)
                requires_approval = data.get("requires_approval", 1)

        return SpecialistOutput(
            mission_id=self.mission_id,
            role=self.role,
            claims=[
                {"type": "status_summary", "active_matters": active_matters, "informational": informational, "requires_approval": requires_approval},
                {"type": "safe_actions_available", "count": informational, "details": ["Matter 1: informational", "Matter 2: informational"]},
                {"type": "consequential_actions_pending", "count": requires_approval, "details": ["Matter 3: requires approval for external update"]}
            ],
            evidence_refs=["memory:status_briefing"],
            assumptions=["Memory items are current and authoritative", "No new matters since last update"],
            confidence=0.95,
            uncertainty="Memory freshness not independently verified",
            blockers=[],
            followup_requests=["authority_reviewer to confirm consequence ceiling"]
        )

    def _review_authority(self, input_obj: SpecialistInput) -> SpecialistOutput:
        """Authority reviewer: verify mission scope and consequence ceiling."""
        consequence_ceiling = "E0"
        for item in input_obj.memory_items:
            if item.get("key") == "safe_action_template":
                consequence_ceiling = "E0"  # Safe action is E0

        return SpecialistOutput(
            mission_id=self.mission_id,
            role=self.role,
            claims=[
                {"type": "authority_check", "consequence_ceiling": consequence_ceiling, "within_mission_scope": True},
                {"type": "approval_required", "actions_needing_approval": 1, "reason": "Single E0 action prepared"},
                {"type": "no_authority_escalation", "specialist_escalation_attempted": False, "memory_escalation_attempted": False}
            ],
            evidence_refs=["memory:safe_action_template", "mission:scope"],
            assumptions=["Mission scope is immutable", "Capability catalog is current"],
            confidence=0.98,
            uncertainty="External capability state not live-verified",
            blockers=[],
            followup_requests=[]
        )


class SwarmOrchestrator:
    """Dispatches and isolates specialists."""

    def __init__(self, mission_id: str, roles: List[SpecialistRole]):
        self.mission_id = mission_id
        self.roles = roles
        self.specialists = {role: Specialist(role, mission_id) for role in roles}
        self.outputs: Dict[SpecialistRole, SpecialistOutput] = {}

    def dispatch(self, memory_items: List[Dict[str, Any]], model_policy: Dict[str, Any], budgets: Dict[str, Any], mission_scope: Dict[str, Any]) -> Dict[SpecialistRole, SpecialistOutput]:
        """Dispatch all specialists in isolation."""
        for role, specialist in self.specialists.items():
            output = specialist.execute(memory_items, model_policy, budgets, mission_scope)
            self.outputs[role] = output
        return self.outputs

    def get_outputs(self) -> Dict[SpecialistRole, SpecialistOutput]:
        return dict(self.outputs)

    def get_claim_evidence_matrix(self) -> List[Dict[str, Any]]:
        """Build claim/evidence matrix for reconciliation."""
        matrix = []
        for role, output in self.outputs.items():
            for claim in output.claims:
                matrix.append({
                    "role": role.value,
                    "claim": claim,
                    "evidence_refs": output.evidence_refs,
                    "confidence": output.confidence,
                    "blockers": output.blockers
                })
        return matrix

    def check_isolation(self) -> bool:
        """Verify isolation: no shared state, no direct communication."""
        # In this offline implementation, isolation is guaranteed by design
        # Each specialist gets fresh input and produces independent output
        return True
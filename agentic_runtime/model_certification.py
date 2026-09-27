"""Evidence-first model capability certification."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Mapping, Sequence

from .capabilities import CapabilityProfile, ModelCapabilityRegistry
from .controls import BenchmarkResult, ModelPromotionGate


@dataclass(frozen=True)
class ObservedModel:
    model_id: str
    provider: str
    context_tokens: int
    capabilities: frozenset[str]
    evidence_ref: str
    local_capable: bool = True
    commercial_use: bool = False
    license_id: str = "UNKNOWN"


class ModelCertifier:
    """Promotes models only from observed facts + benchmark receipts."""
    def __init__(self, registry: ModelCapabilityRegistry, gate: ModelPromotionGate):
        self.registry = registry
        self.gate = gate

    def certify(self, observed: ObservedModel, results: Iterable[BenchmarkResult], required_suites: Sequence[str]) -> tuple[bool, str]:
        if observed.context_tokens <= 0:
            return False, "CONTEXT_NOT_VERIFIED"
        if not observed.evidence_ref:
            return False, "MODEL_EVIDENCE_MISSING"
        ok, reason = self.gate.admit(results, required_suites=required_suites)
        if not ok:
            return False, reason
        self.registry.register(CapabilityProfile(
            model_id=observed.model_id,
            provider=observed.provider,
            context_tokens=observed.context_tokens,
            capabilities=observed.capabilities,
            local_capable=observed.local_capable,
            commercial_use=observed.commercial_use,
            license_id=observed.license_id,
            evidence_status="VERIFIED",
        ))
        return True, "PROMOTED"

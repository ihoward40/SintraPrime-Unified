"""Provider-neutral capability registry.

Keeps routing based on verified capabilities rather than model hype or vendor
names. Profiles are metadata only; availability and policy remain the job of
SintraPrime's governed inference router.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CapabilityProfile:
    model_id: str
    provider: str
    context_tokens: int
    capabilities: frozenset[str] = field(default_factory=frozenset)
    local_capable: bool = False
    commercial_use: bool | None = None
    license_id: str | None = None
    evidence_status: str = "UNVERIFIED"

    def supports(self, required: Iterable[str], min_context: int = 0) -> bool:
        return self.context_tokens >= min_context and set(required).issubset(self.capabilities)


class ModelCapabilityRegistry:
    def __init__(self) -> None:
        self._profiles: dict[str, CapabilityProfile] = {}

    def register(self, profile: CapabilityProfile) -> None:
        if profile.context_tokens <= 0:
            raise ValueError("context_tokens must be positive")
        self._profiles[profile.model_id] = profile

    def get(self, model_id: str) -> CapabilityProfile | None:
        return self._profiles.get(model_id)

    def candidates(self, required: Iterable[str], min_context: int = 0, *, verified_only: bool = True):
        matches = [
            p for p in self._profiles.values()
            if p.supports(required, min_context)
            and (not verified_only or p.evidence_status == "VERIFIED")
        ]
        return sorted(matches, key=lambda p: (not p.local_capable, -p.context_tokens, p.model_id))

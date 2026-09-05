"""B2-B11 machine-readable legacy mutation containment inventory."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class LegacyDisposition(StrEnum):
    REWIRE = "REWIRE"
    QUARANTINE = "QUARANTINE"
    REMOVE = "REMOVE"
    READ_ONLY = "READ_ONLY"
    ALREADY_GOVERNED = "ALREADY_GOVERNED"
    NOT_PRESENT = "NOT_PRESENT"


@dataclass(frozen=True)
class LegacySurface:
    surface_id: str
    module: str
    mutation_capable: bool
    governed: bool
    disposition: LegacyDisposition
    test_id: str
    status: str
    remaining_risk: str


LEGACY_CONTAINMENT_MAP = (
    LegacySurface("nova-approval-gateway", "agents/nova/nova_agent.py", True, False, LegacyDisposition.REWIRE, "B2B11-NOVA", "INVENTORY_ONLY", "requires canonical executor review"),
    LegacySurface("chat-autonomous", "agents/chat/chat_agent.py", True, False, LegacyDisposition.QUARANTINE, "B2B11-CHAT", "INVENTORY_ONLY", "legacy mutation surface"),
    LegacySurface("chat-god-mode", "agents/chat/chat_agent.py", True, False, LegacyDisposition.QUARANTINE, "B2B11-GOD", "INVENTORY_ONLY", "legacy mutation surface"),
    LegacySurface("sigma-direct-github", "agents/sigma/sigma_agent.py", True, False, LegacyDisposition.REWIRE, "B2B11-SIGMA", "INVENTORY_ONLY", "direct mutation requires canonical seam"),
    LegacySurface("shell-browser", "operator/browser_controller.py", True, False, LegacyDisposition.QUARANTINE, "B2B11-SHELL", "INVENTORY_ONLY", "consequential surface"),
    LegacySurface("future-google-mutation", "NOT_PRESENT", False, False, LegacyDisposition.NOT_PRESENT, "B2B11-GOOGLE", "NOT_PRESENT", "no repository surface found"),
)


def legacy_containment_map() -> tuple[LegacySurface, ...]:
    return LEGACY_CONTAINMENT_MAP


def deny_legacy_mutation(*, surface: LegacySurface, provider_calls: int = 0) -> None:
    if surface.mutation_capable and surface.disposition not in {LegacyDisposition.ALREADY_GOVERNED, LegacyDisposition.REWIRE}:
        raise PermissionError("LEGACY_MUTATION_DENIED")
    if provider_calls:
        raise PermissionError("LEGACY_PROVIDER_CALL_DETECTED")

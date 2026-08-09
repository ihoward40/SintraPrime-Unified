"""Deterministic speech-capability router.

Routes a requested capability to the highest-priority currently-usable
registered provider, and returns full routing evidence (considered
providers, rejected providers with reasons, and the final selection) rather
than silently picking a provider. Routing never downgrades a governance
requirement — this module only ever selects among providers that already
declared the requested capability; it has no authority of its own.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .capabilities import SpeechCapability
from .errors import ProviderUnavailableError, UnsupportedCapabilityError
from .provenance import RoutingDecisionRef
from .providers.base import SpeechProvider
from .registry import ProviderRegistry


@dataclass(frozen=True)
class RejectedProvider:
    """A provider that was considered but not selected, and why."""

    provider_id: str
    reason: str


@dataclass(frozen=True)
class RoutingDecision:
    """Full evidence for a single routing decision."""

    requested_capability: SpeechCapability
    selected_provider_id: str | None
    considered_provider_ids: tuple[str, ...]
    rejected: tuple[RejectedProvider, ...] = field(default_factory=tuple)

    def to_provenance_ref(self) -> RoutingDecisionRef:
        return RoutingDecisionRef(
            requested_capability=self.requested_capability.value,
            selected_provider_id=self.selected_provider_id,
            considered_provider_ids=self.considered_provider_ids,
        )


def route(
    registry: ProviderRegistry,
    capability: SpeechCapability,
    *,
    preferred_provider_id: str | None = None,
) -> tuple[SpeechProvider, RoutingDecision]:
    """Select a provider for ``capability``.

    Raises ``UnsupportedCapabilityError`` if no *registered* provider
    declares the capability at all, or ``ProviderUnavailableError`` if one
    or more providers declare it but none are currently usable (disabled,
    dependency missing, etc.) — these are distinct, typed outcomes so
    callers can react differently (e.g. "this will never work here" vs.
    "this might work once a dependency is installed").

    If ``preferred_provider_id`` is given and that provider both declares
    the capability and is currently usable, it is selected regardless of
    its configured priority (an explicit caller preference always wins over
    the default priority ordering).
    """

    candidates = registry.providers_for_capability(capability)
    if not candidates:
        raise UnsupportedCapabilityError(capability)

    preflights = registry.preflight_map()
    considered: list[str] = []
    rejected: list[RejectedProvider] = []

    if preferred_provider_id is not None:
        preferred = next((p for p in candidates if p.provider_id == preferred_provider_id), None)
        if preferred is not None:
            considered.append(preferred.provider_id)
            result = preflights.get(preferred.provider_id)
            if result is not None and result.usable:
                decision = RoutingDecision(
                    requested_capability=capability,
                    selected_provider_id=preferred.provider_id,
                    considered_provider_ids=tuple(considered),
                    rejected=tuple(rejected),
                )
                return preferred, decision
            rejected.append(
                RejectedProvider(
                    provider_id=preferred.provider_id,
                    reason=f"explicitly preferred but unusable: {result.state.value if result else 'unknown'}",
                )
            )

    for provider in candidates:
        if provider.provider_id in considered:
            continue
        considered.append(provider.provider_id)
        result = preflights.get(provider.provider_id)
        if result is not None and result.usable:
            decision = RoutingDecision(
                requested_capability=capability,
                selected_provider_id=provider.provider_id,
                considered_provider_ids=tuple(considered),
                rejected=tuple(rejected),
            )
            return provider, decision
        rejected.append(
            RejectedProvider(
                provider_id=provider.provider_id,
                reason=(result.detail or result.state.value) if result else "no preflight result",
            )
        )

    raise ProviderUnavailableError(
        capability,
        {r.provider_id: r.reason for r in rejected},
    )

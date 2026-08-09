"""Deterministic provider registry.

Registers providers by ID, rejects ambiguous duplicate registrations,
exposes capability maps and availability/preflight state, and supports
retrieving providers by capability in a deterministic (insertion-ordered,
then explicit-priority-ordered) manner. Performs no autonomous discovery —
providers must be explicitly constructed and registered by calling code.
No plugin auto-install of any kind.
"""

from __future__ import annotations

from dataclasses import dataclass

from .capabilities import SpeechCapability
from .errors import DuplicateProviderError, UnknownProviderError
from .preflight import PreflightResult
from .providers.base import SpeechProvider


@dataclass
class _RegistryEntry:
    provider: SpeechProvider
    priority: int
    enabled: bool = True


class ProviderRegistry:
    """Holds a deterministic set of registered speech providers."""

    def __init__(self) -> None:
        self._entries: dict[str, _RegistryEntry] = {}
        self._registration_order: list[str] = []

    def register(
        self,
        provider: SpeechProvider,
        *,
        priority: int = 100,
        enabled: bool = True,
    ) -> None:
        """Register ``provider``. Raises ``DuplicateProviderError`` on ID collision.

        Lower ``priority`` values are preferred during routing (priority 0
        is tried before priority 100). Providers registered with the same
        priority are considered in registration order, which keeps routing
        fully deterministic.
        """

        provider_id = provider.provider_id
        if provider_id in self._entries:
            raise DuplicateProviderError(provider_id)
        self._entries[provider_id] = _RegistryEntry(provider=provider, priority=priority, enabled=enabled)
        self._registration_order.append(provider_id)

    def unregister(self, provider_id: str) -> None:
        """Remove a provider from the registry. No-op if not registered."""

        self._entries.pop(provider_id, None)
        if provider_id in self._registration_order:
            self._registration_order.remove(provider_id)

    def set_enabled(self, provider_id: str, enabled: bool) -> None:
        """Enable or disable a registered provider without unregistering it."""

        entry = self._require_entry(provider_id)
        entry.enabled = enabled

    def get(self, provider_id: str) -> SpeechProvider:
        """Retrieve a provider by ID. Raises ``UnknownProviderError`` if absent."""

        return self._require_entry(provider_id).provider

    def is_enabled(self, provider_id: str) -> bool:
        return self._require_entry(provider_id).enabled

    def provider_ids(self) -> tuple[str, ...]:
        """All registered provider IDs, in registration order."""

        return tuple(self._registration_order)

    def capability_map(self) -> dict[str, frozenset[SpeechCapability]]:
        """Provider ID -> declared capabilities, for every registered provider."""

        return {
            provider_id: entry.provider.capabilities
            for provider_id, entry in self._entries.items()
        }

    def preflight_map(self) -> dict[str, PreflightResult]:
        """Provider ID -> current preflight result, for every registered provider.

        Disabled providers are reported with a synthetic ``DISABLED`` result
        regardless of what the provider's own ``preflight()`` would say,
        since administrative disablement always takes precedence.
        """

        results: dict[str, PreflightResult] = {}
        for provider_id, entry in self._entries.items():
            if not entry.enabled:
                results[provider_id] = PreflightResult.disabled()
            else:
                results[provider_id] = entry.provider.preflight()
        return results

    def providers_for_capability(self, capability: SpeechCapability) -> tuple[SpeechProvider, ...]:
        """All *registered* providers declaring ``capability``, in priority order.

        Includes disabled/unavailable providers — callers wanting only
        currently-usable providers should combine this with
        ``preflight_map()``. Kept separate so routing evidence can report
        *why* a provider was rejected (disabled vs. unavailable vs. simply
        not supporting the capability).
        """

        matching = [
            (entry.priority, order_index, entry.provider)
            for order_index, provider_id in enumerate(self._registration_order)
            for entry in (self._entries[provider_id],)
            if capability in entry.provider.capabilities
        ]
        matching.sort(key=lambda item: (item[0], item[1]))
        return tuple(provider for _, _, provider in matching)

    def _require_entry(self, provider_id: str) -> _RegistryEntry:
        entry = self._entries.get(provider_id)
        if entry is None:
            raise UnknownProviderError(provider_id)
        return entry


def build_default_registry() -> ProviderRegistry:
    """Construct the default registry with the Phase-1 provider set.

    Priority order (lower = preferred): mock (0, dev/test default) is not
    included by default in production-shaped registries — callers assemble
    their own registry explicitly. This helper exists mainly for tests and
    documentation of the intended default priority ordering:

        1. local/native providers (none in Phase 1 — reserved for a future
           VibeVoice adapter, priority ~10)
        2. legacy audio adapter (AUDIO_NORMALIZATION only, priority ~50)
        3. browser/native fallback (ASR/TTS, priority ~90)
        4. mock (priority ~100, always last so it never masks a real
           provider in an environment where both are registered)
    """

    from .providers.browser import BrowserSpeechProvider
    from .providers.legacy import LegacyAudioAdapterProvider
    from .providers.mock import MockSpeechProvider

    registry = ProviderRegistry()
    registry.register(LegacyAudioAdapterProvider(), priority=50)
    registry.register(BrowserSpeechProvider(), priority=90)
    registry.register(MockSpeechProvider(), priority=100)
    return registry

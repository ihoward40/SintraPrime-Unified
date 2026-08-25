"""L2-I8 exact capability registry — immutable entries, exact lookup only.

No alias expansion, no fuzzy matching, no deprecated reuse.
"""
from __future__ import annotations

from typing import Dict, Tuple

from sintra_live.l2.capability_registry_contract import (
    CapabilityRegistryEntry,
    CapabilityLookupRequest,
    SCHEMA_VERSION,
)


class CapabilityRegistryError(Exception):
    """Base registry error."""


class DuplicateRegistryKey(CapabilityRegistryError):
    """Duplicate (capability_id, capability_version) already registered."""


class AmbiguousMatch(CapabilityRegistryError):
    """More than one exact match found."""


class CapabilityRegistry:
    """Immutable exact-lookup capability registry.

    Key = (capability_id, capability_version)
    Entries are added at construction and cannot be modified or removed.
    """

    def __init__(self, entries: Tuple[CapabilityRegistryEntry, ...] = ()) -> None:
        self._entries: Dict[Tuple[str, str], CapabilityRegistryEntry] = {}
        for e in entries:
            key = (e.capability_id, e.capability_version)
            if key in self._entries:
                raise DuplicateRegistryKey(f"duplicate {key}")
            self._entries[key] = e

    def lookup(self, req: CapabilityLookupRequest) -> CapabilityRegistryEntry:
        """Exact lookup: (capability_id, capability_version) must match exactly."""
        key = (req.capability_id, req.capability_version)
        entry = self._entries.get(key)
        if entry is None:
            raise CapabilityRegistryError(f"UNKNOWN_CAPABILITY: {key}")
        if entry.deprecated:
            raise CapabilityRegistryError(f"DEPRECATED_CAPABILITY: {key}")
        return entry

    def lookup_exact(
        self,
        capability_id: str,
        capability_version: str,
        adapter_id: str,
        adapter_version: str,
        canonical_entrypoint: str,
    ) -> CapabilityRegistryEntry:
        """Full exact lookup matching capability, adapter, and entrypoint."""
        key = (capability_id, capability_version)
        entry = self._entries.get(key)
        if entry is None:
            raise CapabilityRegistryError(f"UNKNOWN_CAPABILITY: {key}")
        if entry.deprecated:
            raise CapabilityRegistryError(f"DEPRECATED_CAPABILITY: {key}")
        if entry.adapter_id != adapter_id:
            raise CapabilityRegistryError(
                f"ADAPTER_MISMATCH: {entry.adapter_id} != {adapter_id}")
        if entry.adapter_version != adapter_version:
            raise CapabilityRegistryError(
                f"ADAPTER_VERSION_MISMATCH: {entry.adapter_version} != {adapter_version}")
        if entry.canonical_entrypoint != canonical_entrypoint:
            raise CapabilityRegistryError(
                f"ENTRYPOINT_MISMATCH: {entry.canonical_entrypoint} != {canonical_entrypoint}")
        return entry

    @property
    def entries(self) -> Tuple[CapabilityRegistryEntry, ...]:
        return tuple(self._entries.values())

    @property
    def size(self) -> int:
        return len(self._entries)


__all__ = [
    "CapabilityRegistry",
    "CapabilityRegistryError",
    "DuplicateRegistryKey",
    "AmbiguousMatch",
]
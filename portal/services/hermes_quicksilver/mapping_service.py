"""Deterministic specialist-to-Hermes-profile mapping service.

Fail-closed resolution of SintraPrime specialist + tenant to a Hermes profile.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from packaging.version import Version

from portal.models.hermes_quicksilver import (
    Decision,
    DelegationRequest,
    HermesProfileDescriptor,
    ResolvedMapping,
    SpecialistProfileMapping,
)
from portal.services.hermes_quicksilver.profile_registry import (
    HermesProfileRegistry,
)


class MappingServiceError(Exception):
    """Base class for mapping service errors."""


class SpecialistMappingService:
    """In-memory deterministic mapping registry.

    Increment One does not require a database. A persistent store can be
    introduced later without changing the public interface.
    """

    def __init__(
        self,
        mappings: Dict[str, SpecialistProfileMapping] | None = None,
        registry: HermesProfileRegistry | None = None,
        hermes_version: str = "0.18.2",
    ):
        self._mappings: Dict[str, SpecialistProfileMapping] = dict(mappings or {})
        self._registry = registry or HermesProfileRegistry()
        self._hermes_version = Version(hermes_version)

    def set_registry(self, registry: HermesProfileRegistry) -> None:
        """Replace the underlying registry (used by tests to spy on access)."""
        self._registry = registry

    def register(self, mapping: SpecialistProfileMapping) -> None:
        """Register a mapping. Duplicate specialist IDs are rejected."""
        if mapping.specialist_id in self._mappings:
            raise MappingServiceError(f"duplicate specialist_id: {mapping.specialist_id}")
        self._mappings[mapping.specialist_id] = mapping

    def resolve(
        self,
        request: DelegationRequest,
    ) -> ResolvedMapping:
        """Resolve a specialist + tenant to a Hermes profile. Fail-closed."""
        start = time.perf_counter()
        mapping = self._mappings.get(request.specialist_id)

        if mapping is None:
            return self._deny(request, "unknown_specialist", start)

        if not mapping.enabled:
            return self._deny(request, "disabled_mapping", start)

        if request.tenant_id not in mapping.tenant_scope:
            return self._deny(request, "tenant_mismatch", start)

        if not self._version_compatible(mapping):
            return self._deny(request, "unsupported_version", start)

        try:
            profile = self._registry.get_profile(mapping.hermes_profile_id)
        except Exception:
            profile = None

        if profile is None:
            return self._deny(request, "missing_hermes_profile", start)

        duration_ms = int((time.perf_counter() - start) * 1000)
        return ResolvedMapping(
            specialist_id=request.specialist_id,
            tenant_id=request.tenant_id,
            hermes_profile_id=mapping.hermes_profile_id,
            hermes_profile=profile,
            decision=Decision.ALLOW,
            reason_code=None,
            duration_ms=duration_ms,
        )

    def _version_compatible(self, mapping: SpecialistProfileMapping) -> bool:
        min_version = Version(mapping.minimum_hermes_version)
        if self._hermes_version < min_version:
            return False
        if mapping.maximum_hermes_version:
            max_version = Version(mapping.maximum_hermes_version)
            if self._hermes_version > max_version:
                return False
        return True

    def _deny(
        self,
        request: DelegationRequest,
        reason_code: str,
        start: float,
    ) -> ResolvedMapping:
        duration_ms = int((time.perf_counter() - start) * 1000)
        mapping = self._mappings.get(request.specialist_id)
        return ResolvedMapping(
            specialist_id=request.specialist_id,
            tenant_id=request.tenant_id,
            hermes_profile_id=mapping.hermes_profile_id if mapping else "",
            hermes_profile=None,
            decision=Decision.DENY,
            reason_code=reason_code,
            duration_ms=duration_ms,
        )

    def list_mappings(self) -> List[SpecialistProfileMapping]:
        return list(self._mappings.values())

    def get_contract(self, specialist_id: str) -> SpecialistProfileMapping | None:
        """Return the raw mapping contract for policy inspection, if any."""
        return self._mappings.get(specialist_id)

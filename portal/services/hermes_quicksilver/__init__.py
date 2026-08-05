"""Hermes Quicksilver governed-fleet service package.

Increment One exports the internal service surface only. No HTTP router is
exposed; callers must supply a trusted caller context and an explicit
permission grant from the existing SintraPrime authorization layer.
"""

from __future__ import annotations

from portal.services.hermes_quicksilver.delegation_audit import (
    EVENT_COMPATIBILITY_REJECTED,
    EVENT_POLICY_HARD_DENIED,
    EVENT_PROFILE_DISCOVERY_COMPLETED,
    EVENT_PROFILE_DISCOVERY_FAILED,
    EVENT_PROFILE_DISCOVERY_REQUESTED,
    EVENT_SPECIALIST_MAPPING_DENIED,
    EVENT_SPECIALIST_MAPPING_VALIDATED,
    AuditRedactionError,
    DelegationAuditBuilder,
)
from portal.services.hermes_quicksilver.hard_deny_policy import HermesHardDenyPolicy
from portal.services.hermes_quicksilver.mapping_service import (
    MappingServiceError,
    SpecialistMappingService,
)
from portal.services.hermes_quicksilver.profile_registry import (
    HermesProfileInvalidError,
    HermesProfileRegistry,
    HermesProfileRegistryError,
    HermesRootUnavailableError,
)
from portal.services.hermes_quicksilver.service import (
    AuthorizationError,
    HermesQuicksilverService,
    TrustedCaller,
)

__all__ = [
    "EVENT_COMPATIBILITY_REJECTED",
    "EVENT_POLICY_HARD_DENIED",
    "EVENT_PROFILE_DISCOVERY_COMPLETED",
    "EVENT_PROFILE_DISCOVERY_FAILED",
    "EVENT_PROFILE_DISCOVERY_REQUESTED",
    "EVENT_SPECIALIST_MAPPING_DENIED",
    "EVENT_SPECIALIST_MAPPING_VALIDATED",
    "AuditRedactionError",
    "AuthorizationError",
    "DelegationAuditBuilder",
    "HermesHardDenyPolicy",
    "HermesProfileInvalidError",
    "HermesProfileRegistry",
    "HermesProfileRegistryError",
    "HermesQuicksilverService",
    "HermesRootUnavailableError",
    "MappingServiceError",
    "SpecialistMappingService",
    "TrustedCaller",
]

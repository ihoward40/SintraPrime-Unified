"""Orchestration service for Hermes Quicksilver Increment One.

Enforces a single, strict authorization gate sequence:

1. Feature flag
2. Request validation
3. Trusted caller validation
4. Operation allowlist
5. Unconditional hard-deny policy
6. Tenant authorization
7. Specialist mapping when required
8. Profile registry access
9. Result normalization
10. Audit persistence

Administrative discovery operations (list_profiles, get_profile_metadata) do not
require a specialist mapping but still require a trusted SintraPrime caller with
explicit internal administration permission.
"""

from __future__ import annotations

import time
from typing import Any

from portal.config import Settings, get_settings
from portal.models.hermes_quicksilver import (
    Decision,
    DelegationRequest,
    DelegationResult,
    HermesDelegationAuditEvent,
    ResolvedMapping,
)
from portal.services.hermes_quicksilver.delegation_audit import (
    EVENT_POLICY_HARD_DENIED,
    EVENT_PROFILE_DISCOVERY_COMPLETED,
    EVENT_PROFILE_DISCOVERY_FAILED,
    EVENT_SPECIALIST_MAPPING_DENIED,
    DelegationAuditBuilder,
)
from portal.services.hermes_quicksilver.hard_deny_policy import HermesHardDenyPolicy
from portal.services.hermes_quicksilver.mapping_service import (
    MappingServiceError,
    SpecialistMappingService,
)
from portal.services.hermes_quicksilver.profile_registry import (
    HermesProfileRegistry,
    HermesProfileRegistryError,
)

# Increment One allowlist.
_ADMIN_OPERATIONS = {"list_profiles", "get_profile_metadata"}
_ALLOWED_OPERATIONS = _ADMIN_OPERATIONS | {"validate_profile_mapping", "check_runtime_compatibility"}


class AuthorizationError(Exception):
    """Raised when caller identity or permission does not satisfy the trust contract."""


class TrustedCaller:
    """Internal caller identity contract used by the Quicksilver service.

    This is not a placeholder identity. Callers must supply a verified user_id
    and tenant_id from the existing SintraPrime authentication/authorization
    layer, plus the explicit internal administration permission. A caller may be
    an end user or a service account, but never a literal such as ``internal_admin``
    or ``system``.
    """

    def __init__(
        self,
        user_id: str,
        tenant_id: str,
        permission: str,
    ):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.permission = permission

    def is_valid(self) -> bool:
        """Reject literal/fabricated identities and empty values."""
        for value in (self.user_id, self.tenant_id, self.permission):
            if not isinstance(value, str) or not value.strip():
                return False
        for forbidden in ("internal_admin", "system", "root", "default"):
            if self.user_id.lower() == forbidden or self.tenant_id.lower() == forbidden:
                return False
        return True


class HermesQuicksilverService:
    """Read-only, fail-closed Quicksilver orchestrator."""

    def __init__(
        self,
        mapping_service: SpecialistMappingService | None = None,
        registry: HermesProfileRegistry | None = None,
        policy: HermesHardDenyPolicy | None = None,
        audit_builder: DelegationAuditBuilder | None = None,
        source_version: str = "0.18.2",
        settings: Settings | None = None,
        internal_admin_permission: str = "hermes_quicksilver:admin",
    ):
        self._settings = settings if settings is not None else get_settings()
        self._mapping_service = mapping_service or SpecialistMappingService()
        self._registry = registry or HermesProfileRegistry()
        self._policy = policy or HermesHardDenyPolicy()
        self._audit = audit_builder or DelegationAuditBuilder(source_version=source_version)
        self._internal_admin_permission = internal_admin_permission

    def execute(
        self,
        request: DelegationRequest,
        caller: TrustedCaller | None = None,
    ) -> tuple[DelegationResult, HermesDelegationAuditEvent]:
        """Execute an Increment One read-only operation. Fail-closed."""
        start = time.perf_counter()

        # 1. Feature flag
        if not self._settings.is_hermes_quicksilver_enabled:
            return self._deny(request, "feature_disabled", start)

        # 2. Request validation
        validation_error = self._validate_request(request)
        if validation_error:
            return self._deny(request, validation_error, start)

        # 3. Trusted caller validation
        if caller is None or not caller.is_valid():
            return self._deny(request, "untrusted_caller", start)

        # 5. Unconditional hard-deny policy (evaluated before mapping/registry access)
        requires_mapping = request.operation not in _ADMIN_OPERATIONS
        specialist_contract = None
        deny_result = self._policy.evaluate(request, specialist_contract)
        if deny_result.denied:
            return self._deny(
                request,
                "hard_denied",
                start,
                event_type_override=EVENT_POLICY_HARD_DENIED,
            )

        # 6. Tenant authorization
        if request.tenant_id != caller.tenant_id:
            return self._deny(request, "tenant_unauthorized", start)

        # 7. Specialist mapping when required
        mapping: ResolvedMapping | None = None
        if requires_mapping:
            try:
                mapping = self._mapping_service.resolve(request)
            except MappingServiceError as exc:
                return self._deny(request, f"mapping_error:{type(exc).__name__}", start)
            if mapping.decision == Decision.DENY:
                return self._deny(
                    request,
                    mapping.reason_code or "mapping_denied",
                    start,
                )

        # 8. Profile registry access
        # 9. Result normalization
        try:
            if request.operation == "list_profiles":
                data = self._list_profiles(request)
            elif request.operation == "get_profile_metadata":
                data = self._get_profile_metadata(request)
            elif request.operation == "validate_profile_mapping":
                data = self._validate_mapping(request, mapping)
            elif request.operation == "check_runtime_compatibility":
                data = self._check_compatibility(request, mapping)
            else:
                return self._deny(request, "unknown_operation", start)
        except HermesProfileRegistryError as exc:
            return self._deny(request, f"registry_error:{type(exc).__name__}", start)

        duration_ms = int((time.perf_counter() - start) * 1000)
        result = DelegationResult(
            operation=request.operation,
            decision=Decision.ALLOW,
            reason_code=None,
            data=data,
            duration_ms=duration_ms,
        )
        event = self._audit.build(
            event_type=EVENT_PROFILE_DISCOVERY_COMPLETED,
            request=request,
            result=result,
            mapping=mapping,
        )

        # 10. Audit persistence (caller-provided permission is checked above)
        return result, event

    def _validate_request(self, request: DelegationRequest) -> str | None:
        if not isinstance(request.operation, str) or not request.operation.strip():
            return "invalid_operation"
        if not isinstance(request.tenant_id, str) or not request.tenant_id.strip():
            return "invalid_tenant"
        if not isinstance(request.actor_id, str) or not request.actor_id.strip():
            return "invalid_actor"
        if not isinstance(request.specialist_id, str) or not request.specialist_id.strip():
            return "invalid_specialist"
        return None

    def _list_profiles(self, request: DelegationRequest) -> dict[str, Any]:
        profiles = self._registry.list_profiles()
        return {
            "count": len(profiles),
            "profiles": [p.model_dump() for p in profiles],
        }

    def _get_profile_metadata(self, request: DelegationRequest) -> dict[str, Any]:
        profile_id = request.context.get("profile_id")
        if not isinstance(profile_id, str):
            raise HermesProfileRegistryError("profile_id required in context")
        profile = self._registry.get_profile(profile_id)
        if profile is None:
            raise HermesProfileRegistryError(f"profile not found: {profile_id}")
        return {"profile": profile.model_dump()}

    def _validate_mapping(
        self,
        request: DelegationRequest,
        mapping: ResolvedMapping | None,
    ) -> dict[str, Any]:
        if mapping is None:
            raise HermesProfileRegistryError("mapping required for validate_profile_mapping")
        return {
            "valid": True,
            "specialist_id": mapping.specialist_id,
            "hermes_profile_id": mapping.hermes_profile_id,
        }

    def _check_compatibility(
        self,
        request: DelegationRequest,
        mapping: ResolvedMapping | None,
    ) -> dict[str, Any]:
        if mapping is None:
            raise HermesProfileRegistryError("mapping required for check_runtime_compatibility")
        return {
            "compatible": True,
            "specialist_id": mapping.specialist_id,
            "hermes_profile_id": mapping.hermes_profile_id,
        }

    def _deny(
        self,
        request: DelegationRequest,
        reason_code: str,
        start: float,
        event_type_override: str | None = None,
    ) -> tuple[DelegationResult, HermesDelegationAuditEvent]:
        duration_ms = int((time.perf_counter() - start) * 1000)
        result = DelegationResult(
            operation=request.operation,
            decision=Decision.DENY,
            reason_code=reason_code,
            data=None,
            duration_ms=duration_ms,
        )
        if event_type_override:
            event_type = event_type_override
        elif reason_code in ("hard_denied", "unknown_operation", "feature_disabled"):
            event_type = EVENT_POLICY_HARD_DENIED
        else:
            event_type = EVENT_SPECIALIST_MAPPING_DENIED
        event = self._audit.build_denial(
            event_type=event_type,
            request=request,
            reason_code=reason_code,
            duration_ms=duration_ms,
        )
        return result, event

    @property
    def mapping_service(self) -> SpecialistMappingService:
        return self._mapping_service

    @property
    def registry(self) -> HermesProfileRegistry:
        return self._registry

    async def persist_event(
        self,
        db,
        event: HermesDelegationAuditEvent,
    ) -> dict[str, Any]:
        """Persist a redacted audit event to the repository-native AuditLog ledger.

        The persistence destination is the existing SintraPrime ``AuditLog``
        model, written through ``portal.services.audit_service.audit``. That
        table is append-only and hash-chained. This adapter prepares a
        deterministic, redacted details dict and delegates insertion.

        Returns the inserted AuditLog row as a dict. Raises on persistence failure
        so callers fail closed.
        """
        from portal.services.audit_service import audit

        details = {
            "event_type": event.event_type,
            "operation": event.operation,
            "decision": event.decision.value,
            "policy_reason_code": event.policy_reason_code,
            "specialist_id": event.specialist_id,
            "hermes_profile_id": event.hermes_profile_id,
            "duration_ms": event.duration_ms,
            "source_version": event.source_version,
            "redaction_version": event.redaction_version,
            "redacted_metadata": event.metadata,
            "serialized_event": self._audit.serialize(event),
        }
        return await audit(
            db,
            action=event.event_type,
            user_id=event.actor_id,
            tenant_id=event.tenant_id,
            resource_type="hermes_quicksilver",
            resource_id=event.correlation_id,
            resource_name=event.operation,
            status="success" if event.decision.value == "allow" else "denied",
            details=details,
            actor_email=None,
            actor_role=None,
            actor_ip=None,
            actor_user_agent=None,
            http_method=None,
            http_path=None,
            http_status_code=None,
            error_message=event.policy_reason_code,
        )

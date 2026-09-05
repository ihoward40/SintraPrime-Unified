"""B2-B6 scoped credential broker with fake-only secret material."""
from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass, fields
from datetime import UTC, datetime, timedelta
from typing import Any

from .jarvis_authority_lease import AuthorityLease, LeaseDeniedError, LeaseState


class CredentialDeniedError(Exception):
    """Fail-closed broker denial; credential material is never included."""

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


class _SecretMaterial:
    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        self._value = value

    def reveal_for_adapter(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return "<REDACTED_SECRET>"

    __str__ = __repr__

    def __reduce__(self):
        raise TypeError("secret material is not serializable")


@dataclass(frozen=True)
class CredentialRequest:
    broker_request_id: str
    tenant_id: str
    principal_id: str
    capability_id: str
    capability_version: str
    capability_contract_hash: str
    action_id: str
    approval_id: str
    lease_id: str
    lease_revision: int
    provider_id: str
    resource_scope: str
    operation: str
    target: str
    issued_at: datetime
    expires_at: datetime
    nonce: str


@dataclass(frozen=True)
class CredentialGrant:
    grant_id: str
    provider_id: str
    tenant_id: str
    action_id: str
    capability_contract_hash: str
    lease_id: str
    resource_scope: str
    operation: str
    expires_at: datetime
    single_use_nonce: str
    _secret_material: _SecretMaterial

    @property
    def secret_material(self) -> _SecretMaterial:
        return self._secret_material

    def __repr__(self) -> str:
        return (
            f"CredentialGrant(grant_id={self.grant_id!r}, provider_id={self.provider_id!r}, "
            f"tenant_id={self.tenant_id!r}, action_id={self.action_id!r}, "
            f"capability_contract_hash={self.capability_contract_hash!r}, lease_id={self.lease_id!r}, "
            f"resource_scope={self.resource_scope!r}, operation={self.operation!r}, "
            f"expires_at={self.expires_at!r}, single_use_nonce={self.single_use_nonce!r}, "
            "secret_material=<REDACTED>)"
        )

    __str__ = __repr__

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "grant_id": self.grant_id,
            "provider_id": self.provider_id,
            "tenant_id": self.tenant_id,
            "action_id": self.action_id,
            "capability_contract_hash": self.capability_contract_hash,
            "lease_id": self.lease_id,
            "resource_scope": self.resource_scope,
            "operation": self.operation,
            "expires_at": self.expires_at.isoformat(),
            "single_use_nonce": self.single_use_nonce,
            "secret_material": "REDACTED",
        }


@dataclass(frozen=True)
class CredentialUseDecision:
    allowed: bool
    reason_code: str
    provider_calls: int = 0


class CredentialBroker:
    """Materializes fake credentials only after exact authority revalidation."""

    def __init__(self, fake_secret: str = "FAKE_B2_SECRET") -> None:
        if not fake_secret.startswith("FAKE_"):
            raise ValueError("only obviously fake credential material is accepted")
        self._fake_secret = fake_secret
        self._used_nonces: set[str] = set()
        self._grants: dict[str, CredentialGrant] = {}

    def issue_scoped_grant(
        self,
        *,
        request: CredentialRequest,
        lease: AuthorityLease,
        now: datetime | None = None,
        effective_executable: bool = True,
        effective_state: str = "TRUSTED",
        attestation_valid: bool = True,
        resource_scope: str | None = None,
    ) -> CredentialGrant:
        moment = now or datetime.now(UTC)
        self._validate_request(request, lease, moment, effective_executable, effective_state, attestation_valid, resource_scope)
        if request.nonce in self._used_nonces:
            raise CredentialDeniedError("NONCE_REPLAY")
        self._used_nonces.add(request.nonce)
        grant = CredentialGrant(
            grant_id=str(uuid.uuid4()), provider_id=request.provider_id,
            tenant_id=request.tenant_id, action_id=request.action_id,
            capability_contract_hash=request.capability_contract_hash,
            lease_id=request.lease_id, resource_scope=request.resource_scope,
            operation=request.operation, expires_at=request.expires_at,
            single_use_nonce=request.nonce,
            _secret_material=_SecretMaterial(self._fake_secret),
        )
        self._grants[grant.grant_id] = grant
        return grant

    def validate_grant_use(
        self,
        *,
        grant: CredentialGrant,
        lease: AuthorityLease,
        request: CredentialRequest,
        now: datetime | None = None,
        effective_executable: bool = True,
        effective_state: str = "TRUSTED",
    ) -> CredentialUseDecision:
        try:
            self._validate_request(request, lease, now or datetime.now(UTC), effective_executable, effective_state, True, grant.resource_scope)
            if self._grants.get(grant.grant_id) is not grant:
                raise CredentialDeniedError("UNKNOWN_GRANT")
            if (now or datetime.now(UTC)) >= grant.expires_at:
                raise CredentialDeniedError("GRANT_EXPIRED")
            if request.nonce != grant.single_use_nonce:
                raise CredentialDeniedError("GRANT_NONCE_MISMATCH")
            self._grants.pop(grant.grant_id)
            return CredentialUseDecision(True, "GRANT_USE_VALID")
        except (CredentialDeniedError, LeaseDeniedError) as exc:
            return CredentialUseDecision(False, str(exc))

    @staticmethod
    def _validate_request(request, lease, now, effective_executable, effective_state, attestation_valid, resource_scope):
        if lease.lease_state != LeaseState.CLAIMED:
            raise CredentialDeniedError("LEASE_NOT_CLAIMED")
        if now >= request.expires_at or now >= lease.expires_at:
            raise CredentialDeniedError("AUTHORITY_EXPIRED")
        if not effective_executable or effective_state in {"REVOKED", "QUARANTINED_BY_DEPENDENCY", "REVALIDATION_REQUIRED"}:
            raise CredentialDeniedError("REGISTRY_NOT_ELIGIBLE")
        if not attestation_valid:
            raise CredentialDeniedError("ATTESTATION_MISMATCH")
        if resource_scope is not None and resource_scope != request.resource_scope:
            raise CredentialDeniedError("RESOURCE_SCOPE_MISMATCH")
        bindings = (
            (request.tenant_id == lease.tenant_id, "TENANT_MISMATCH"),
            (request.principal_id == lease.principal_id, "PRINCIPAL_MISMATCH"),
            (request.capability_id == lease.capability_id, "CAPABILITY_MISMATCH"),
            (request.capability_version == lease.capability_version, "VERSION_MISMATCH"),
            (request.capability_contract_hash == lease.capability_contract_hash, "CONTRACT_HASH_MISMATCH"),
            (request.action_id == lease.action_id, "ACTION_MISMATCH"),
            (request.approval_id == lease.approval_id, "APPROVAL_MISMATCH"),
            (request.lease_id == lease.lease_id, "LEASE_MISMATCH"),
            (request.lease_revision == lease.revision, "LEASE_REVISION_MISMATCH"),
            (request.operation == lease.operation, "OPERATION_MISMATCH"),
            (request.target == lease.target, "TARGET_MISMATCH"),
        )
        for valid, reason in bindings:
            if not valid:
                raise CredentialDeniedError(reason)

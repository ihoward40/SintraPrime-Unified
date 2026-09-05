"""JARVIS-001-B2-B4 exact-action authority leases."""
from __future__ import annotations

import enum
import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


class LeaseState(enum.StrEnum):
    ISSUED = "ISSUED"
    CLAIMED = "CLAIMED"
    CONSUMED = "CONSUMED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class LeaseDeniedError(Exception):
    """Fail-closed lease denial; no provider call is permitted."""


@dataclass(frozen=True)
class AuthorityLease:
    lease_id: str
    tenant_id: str
    principal_id: str
    capability_id: str
    capability_version: str
    capability_contract_hash: str
    registry_revision: int
    action_id: str
    approval_id: str
    operation: str
    target: str
    params_hash: str
    issued_at: datetime
    expires_at: datetime
    lease_state: LeaseState = LeaseState.ISSUED
    revision: int = 0

    @classmethod
    def issue(
        cls,
        *,
        tenant_id: str,
        principal_id: str,
        capability_id: str,
        capability_version: str,
        capability_contract_hash: str,
        registry_revision: int,
        action_id: str,
        approval_id: str,
        operation: str,
        target: str,
        params_hash: str,
        ttl: timedelta,
        now: datetime | None = None,
    ) -> AuthorityLease:
        issued_at = now or datetime.now(UTC)
        if ttl <= timedelta(0):
            raise LeaseDeniedError("LEASE_TTL_INVALID")
        return cls(
            lease_id=str(uuid.uuid4()), tenant_id=tenant_id, principal_id=principal_id,
            capability_id=capability_id, capability_version=capability_version,
            capability_contract_hash=capability_contract_hash, registry_revision=registry_revision,
            action_id=action_id, approval_id=approval_id, operation=operation, target=target,
            params_hash=params_hash, issued_at=issued_at, expires_at=issued_at + ttl,
        )

    def validate(
        self,
        *,
        tenant_id: str,
        principal_id: str,
        capability_id: str,
        capability_version: str,
        capability_contract_hash: str,
        registry_revision: int,
        action_id: str,
        approval_id: str,
        operation: str,
        target: str,
        params_hash: str,
        now: datetime | None = None,
        effective_executable: bool = True,
        effective_state: str = "TRUSTED",
    ) -> None:
        checks = (
            (self.tenant_id == tenant_id, "TENANT_MISMATCH"),
            (self.principal_id == principal_id, "PRINCIPAL_MISMATCH"),
            (self.capability_id == capability_id, "CAPABILITY_MISMATCH"),
            (self.capability_version == capability_version, "CAPABILITY_VERSION_MISMATCH"),
            (self.capability_contract_hash == capability_contract_hash, "CONTRACT_HASH_MISMATCH"),
            (self.registry_revision == registry_revision, "REGISTRY_REVISION_MISMATCH"),
            (self.action_id == action_id, "ACTION_MISMATCH"),
            (self.approval_id == approval_id, "APPROVAL_MISMATCH"),
            (self.operation == operation, "OPERATION_MISMATCH"),
            (self.target == target, "TARGET_MISMATCH"),
            (self.params_hash == params_hash, "PARAMS_HASH_MISMATCH"),
            (effective_executable, "REGISTRY_NOT_EXECUTABLE"),
            (effective_state not in {"REVOKED", "QUARANTINED_BY_DEPENDENCY", "REVALIDATION_REQUIRED"}, "REGISTRY_STATE_INVALID"),
        )
        for valid, reason in checks:
            if not valid:
                raise LeaseDeniedError(reason)
        moment = now or datetime.now(UTC)
        if moment >= self.expires_at:
            raise LeaseDeniedError("LEASE_EXPIRED")
        if self.lease_state not in {LeaseState.ISSUED, LeaseState.CLAIMED}:
            raise LeaseDeniedError(f"LEASE_NOT_EXECUTABLE:{self.lease_state.value}")

    def claim(self, **context: Any) -> AuthorityLease:
        if self.lease_state != LeaseState.ISSUED:
            raise LeaseDeniedError(f"LEASE_NOT_ISSUED:{self.lease_state.value}")
        self.validate(**context)
        return AuthorityLease(**{**self.__dict__, "lease_state": LeaseState.CLAIMED, "revision": self.revision + 1})

    def consume(self, **context: Any) -> AuthorityLease:
        if self.lease_state != LeaseState.CLAIMED:
            raise LeaseDeniedError("LEASE_NOT_CLAIMED")
        self.validate(**context)
        return AuthorityLease(**{**self.__dict__, "lease_state": LeaseState.CONSUMED, "revision": self.revision + 1})

    def revoke(self) -> AuthorityLease:
        if self.lease_state in {LeaseState.CONSUMED, LeaseState.EXPIRED}:
            raise LeaseDeniedError("LEASE_TERMINAL")
        return AuthorityLease(**{**self.__dict__, "lease_state": LeaseState.REVOKED, "revision": self.revision + 1})

    def expire(self, now: datetime | None = None) -> AuthorityLease:
        if (now or datetime.now(UTC)) < self.expires_at:
            raise LeaseDeniedError("LEASE_NOT_EXPIRED")
        if self.lease_state in {LeaseState.CONSUMED, LeaseState.REVOKED}:
            return self
        return AuthorityLease(**{**self.__dict__, "lease_state": LeaseState.EXPIRED, "revision": self.revision + 1})


def params_hash(params: Any) -> str:
    return hashlib.sha256(repr(params).encode("utf-8")).hexdigest()

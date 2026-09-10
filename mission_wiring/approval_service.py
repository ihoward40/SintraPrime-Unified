"""SP-CONVERGE-ZD-001 §6 — AuthorityApprovalService.

The envelope can NEVER self-declare approval. Approval references are issued
by the authority system, validated for full binding (mission, actor, tenant,
capability, resource), expiry, and unused state, and consumed exactly once.

Semantic rule (Principal directive):
  CONSEQUENTIAL_REQUEST_WITHOUT_APPROVAL      = REPRESENTABLE  (PENDING posture)
  CONSEQUENTIAL_EXECUTION_WITHOUT_VALID_APPROVAL = IMPOSSIBLE
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

__all__ = ["ApprovalBinding", "ApprovalInvalidError", "AuthorityApprovalService"]


class ApprovalInvalidError(Exception):
    """Raised when an approval reference fails independent validation."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class ApprovalBinding:
    """An authority-issued approval: full binding to one pending mission."""
    approval_id: str
    mission_id: str
    actor_id: str
    tenant_id: str
    capabilities: frozenset[str]
    resource_urls: frozenset[str]
    issued_by: str
    issued_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        if self.expires_at <= self.issued_at:
            raise ApprovalInvalidError("INVALID_EXPIRY", "approval expiry must be after issue")


@dataclass
class AuthorityApprovalService:
    """Issues, validates, and exactly-once consumes approval bindings."""

    clock: Any = field(default=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        self._issued: dict[str, ApprovalBinding] = {}
        self._consumed: dict[str, str] = {}
        self._guard = threading.Lock()

    # ---- issuance (authority-only entry point) ----
    def issue(self, *, approval_id: str, mission_id: str, actor_id: str, tenant_id: str,
              capabilities: frozenset[str], resource_urls: frozenset[str],
              issued_by: str, ttl_seconds: int = 3600) -> ApprovalBinding:
        if ttl_seconds <= 0:
            raise ApprovalInvalidError("INVALID_EXPIRY", "ttl must be positive")
        now = self.clock()
        binding = ApprovalBinding(
            approval_id=approval_id, mission_id=mission_id, actor_id=actor_id,
            tenant_id=tenant_id, capabilities=frozenset(capabilities),
            resource_urls=frozenset(resource_urls), issued_by=issued_by,
            issued_at=now, expires_at=now + __import__("datetime").timedelta(seconds=ttl_seconds),
        )
        with self._guard:
            if approval_id in self._issued:
                raise ApprovalInvalidError("DUPLICATE_APPROVAL_ID", approval_id)
            self._issued[approval_id] = binding
        return binding

    # ---- independent validation (never trusts the envelope's own state) ----
    def validate(self, approval_id: str, *, mission_id: str, actor_id: str, tenant_id: str,
                 capabilities: frozenset[str], resource_urls: frozenset[str]) -> ApprovalBinding:
        with self._guard:
            binding = self._issued.get(approval_id)
        if binding is None:
            raise ApprovalInvalidError("UNKNOWN_APPROVAL", f"{approval_id} was never issued by authority")
        if binding.mission_id != mission_id:
            raise ApprovalInvalidError("MISSION_MISMATCH", f"approval binds {binding.mission_id}, envelope claims {mission_id}")
        if binding.actor_id != actor_id:
            raise ApprovalInvalidError("ACTOR_MISMATCH", f"approval binds {binding.actor_id}, envelope claims {actor_id}")
        if binding.tenant_id != tenant_id:
            raise ApprovalInvalidError("TENANT_MISMATCH", f"approval binds {binding.tenant_id}, envelope claims {tenant_id}")
        unbound_caps = frozenset(capabilities) - binding.capabilities
        if unbound_caps:
            raise ApprovalInvalidError("CAPABILITY_NOT_APPROVED", f"{sorted(unbound_caps)} not in approval scope")
        unbound_urls = frozenset(resource_urls) - binding.resource_urls
        if unbound_urls:
            raise ApprovalInvalidError("RESOURCE_NOT_APPROVED", f"{sorted(unbound_urls)} not in approval scope")
        if self.clock() > binding.expires_at:
            raise ApprovalInvalidError("APPROVAL_EXPIRED", f"expired {binding.expires_at.isoformat()}")
        return binding

    # ---- exactly-once consumption (validate + consume is the execution gate) ----
    def consume(self, approval_id: str, *, mission_id: str, actor_id: str, tenant_id: str,
                capabilities: frozenset[str], resource_urls: frozenset[str]) -> ApprovalBinding:
        binding = self.validate(approval_id, mission_id=mission_id, actor_id=actor_id,
                                tenant_id=tenant_id, capabilities=capabilities,
                                resource_urls=resource_urls)
        with self._guard:
            if approval_id in self._consumed:
                raise ApprovalInvalidError("APPROVAL_ALREADY_CONSUMED",
                                      f"consumed at {self._consumed[approval_id]} by mission {self._consumed[approval_id]}")
            self._consumed[approval_id] = f"{self.clock().isoformat()} mission={mission_id}"
        return binding

    def status(self, approval_id: str) -> str:
        with self._guard:
            if approval_id in self._consumed:
                return "CONSUMED"
            if approval_id in self._issued:
                return "ISSUED"
        return "UNKNOWN"

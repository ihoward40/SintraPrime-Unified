"""SP-CONVERGE-ZD-001 §6 — AuthorityApprovalService.

The envelope can NEVER self-declare approval. Approval references are issued
by the authority system, validated for full binding (mission, actor, tenant,
capability, resource, role, worker class, execution class, context hash), expiry,
and unused state, and consumed exactly once.
"""
from __future__ import annotations

import hashlib
import hmac
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from .approval_ledger import ApprovalLedger, LedgerError, LedgerRecord

__all__ = [
    "ApprovalBinding",
    "ApprovalInvalidError",
    "AuthorityApprovalService",
    "PrincipalAuthToken",
]


class ApprovalInvalidError(Exception):
    """Raised when an approval reference fails independent validation."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class PrincipalAuthToken:
    """Cryptographically verifiable token proving authentic Principal approval for a specific task."""

    principal_id: str
    tenant_id: str
    mission_id: str
    actor_id: str
    capabilities_hash: str
    resource_urls_hash: str
    context_hash: str
    role: str
    worker_class: str
    effect_class: str
    issued_at: datetime
    expires_at: datetime
    nonce: str
    signature: str

    def canonical_payload(self) -> bytes:
        elements = [
            self.principal_id,
            self.tenant_id,
            self.mission_id,
            self.actor_id,
            self.capabilities_hash,
            self.resource_urls_hash,
            self.context_hash,
            self.role,
            self.worker_class,
            self.effect_class,
            self.issued_at.isoformat(),
            self.expires_at.isoformat(),
            self.nonce,
        ]
        return "|".join(elements).encode("utf-8")

    def verify(self, secret_key: bytes, now: datetime | None = None) -> bool:
        now_dt = now or datetime.now(UTC)
        if now_dt >= self.expires_at:
            return False
        expected_sig = hmac.new(secret_key, self.canonical_payload(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(self.signature, expected_sig)


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
    permitted_roles: frozenset[str] = field(default_factory=frozenset)
    permitted_workers: frozenset[str] = field(default_factory=frozenset)
    permitted_execution_classes: frozenset[str] = field(default_factory=frozenset)
    context_hash: str = ""

    def __post_init__(self) -> None:
        if self.expires_at <= self.issued_at:
            raise ApprovalInvalidError("INVALID_EXPIRY", "approval expiry must be after issue")
        if not self.mission_id.strip():
            raise ApprovalInvalidError("MISSION_REQUIRED", "mission_id cannot be empty")
        if not self.tenant_id.strip():
            raise ApprovalInvalidError("TENANT_REQUIRED", "tenant_id cannot be empty")
        if not self.actor_id.strip():
            raise ApprovalInvalidError("ACTOR_REQUIRED", "actor_id cannot be empty")


@dataclass
class AuthorityApprovalService:
    """Issues, validates, and exactly-once consumes approval bindings."""

    clock: Any = field(default=lambda: datetime.now(UTC))
    ledger: ApprovalLedger | None = None
    principal_signing_key: bytes = b"sintraprime-default-principal-secret"

    def __post_init__(self) -> None:
        self._issued: dict[str, ApprovalBinding] = {}
        self._consumed: dict[str, str] = {}
        self._guard = threading.RLock()

    def issue(
        self,
        *,
        approval_id: str,
        mission_id: str,
        actor_id: str,
        tenant_id: str,
        capabilities: frozenset[str],
        resource_urls: frozenset[str],
        issued_by: str,
        ttl_seconds: int = 3600,
        permitted_roles: frozenset[str] = frozenset(),
        permitted_workers: frozenset[str] = frozenset(),
        permitted_execution_classes: frozenset[str] = frozenset(),
        context_hash: str = "",
        principal_token: PrincipalAuthToken | None = None,
    ) -> ApprovalBinding:
        if ttl_seconds <= 0:
            raise ApprovalInvalidError("INVALID_EXPIRY", "ttl must be positive")

        now = self.clock()
        expires_at = now + timedelta(seconds=ttl_seconds)

        # Authenticated Principal Token Verification
        if principal_token is not None:
            if not principal_token.verify(self.principal_signing_key, now=now):
                raise ApprovalInvalidError("UNAUTHENTICATED_PRINCIPAL", "Principal token signature invalid or expired")
            if principal_token.mission_id != mission_id:
                raise ApprovalInvalidError("TOKEN_SCOPE_MISMATCH", "Token mission_id does not match approval")
            if principal_token.tenant_id != tenant_id:
                raise ApprovalInvalidError("TOKEN_SCOPE_MISMATCH", "Token tenant_id does not match approval")
            if principal_token.actor_id != actor_id:
                raise ApprovalInvalidError("TOKEN_SCOPE_MISMATCH", "Token actor_id does not match approval")

        binding = ApprovalBinding(
            approval_id=approval_id,
            mission_id=mission_id,
            actor_id=actor_id,
            tenant_id=tenant_id,
            capabilities=frozenset(capabilities),
            resource_urls=frozenset(resource_urls),
            issued_by=issued_by,
            issued_at=now,
            expires_at=expires_at,
            permitted_roles=frozenset(permitted_roles),
            permitted_workers=frozenset(permitted_workers),
            permitted_execution_classes=frozenset(permitted_execution_classes),
            context_hash=context_hash,
        )

        if self.ledger is not None:
            try:
                self.ledger.issue(
                    approval_id=approval_id,
                    mission_id=mission_id,
                    actor_id=actor_id,
                    tenant_id=tenant_id,
                    capabilities=frozenset(capabilities),
                    resource_urls=frozenset(resource_urls),
                    issued_by=issued_by,
                    issued_at=now,
                    expires_at=expires_at,
                    permitted_roles=frozenset(permitted_roles),
                    permitted_workers=frozenset(permitted_workers),
                    permitted_execution_classes=frozenset(permitted_execution_classes),
                    context_hash=context_hash,
                )
            except LedgerError as exc:
                raise ApprovalInvalidError(exc.code, exc.detail) from exc

        with self._guard:
            if approval_id in self._issued:
                raise ApprovalInvalidError("DUPLICATE_APPROVAL_ID", approval_id)
            self._issued[approval_id] = binding

        return binding

    def _assert_binding_matches(
        self,
        binding: ApprovalBinding | LedgerRecord,
        *,
        mission_id: str,
        actor_id: str,
        tenant_id: str,
        capabilities: frozenset[str],
        resource_urls: frozenset[str],
        role: str | None = None,
        worker_class: str | None = None,
        effect_class: str | None = None,
        context_hash: str | None = None,
    ) -> None:
        if binding.mission_id != mission_id:
            raise ApprovalInvalidError("MISSION_MISMATCH", f"approval binds {binding.mission_id}, requested {mission_id}")
        if binding.actor_id != actor_id:
            raise ApprovalInvalidError("ACTOR_MISMATCH", f"approval binds {binding.actor_id}, requested {actor_id}")
        if binding.tenant_id != tenant_id:
            raise ApprovalInvalidError("TENANT_MISMATCH", f"approval binds {binding.tenant_id}, requested {tenant_id}")

        if worker_class is not None:
            if not binding.permitted_workers or worker_class not in binding.permitted_workers:
                raise ApprovalInvalidError("WORKER_CLASS_DENIED", f"worker_class '{worker_class}' not in permitted_workers")

        if role is not None:
            if not binding.permitted_roles or role not in binding.permitted_roles:
                raise ApprovalInvalidError("ROLE_NOT_ALLOWED", f"role '{role}' not in permitted_roles")

        if effect_class is not None:
            if not binding.permitted_execution_classes or effect_class not in binding.permitted_execution_classes:
                raise ApprovalInvalidError("EXECUTION_CLASS_DENIED", f"effect_class '{effect_class}' not in permitted_execution_classes")

        unbound_caps = frozenset(capabilities) - binding.capabilities
        if unbound_caps:
            raise ApprovalInvalidError("CAPABILITY_NOT_APPROVED", f"{sorted(unbound_caps)} not in approval scope")

        unbound_urls = frozenset(resource_urls) - binding.resource_urls
        if unbound_urls:
            raise ApprovalInvalidError("RESOURCE_NOT_APPROVED", f"{sorted(unbound_urls)} not in approval scope")

        if context_hash is not None and binding.context_hash:
            if not context_hash or context_hash.strip() != binding.context_hash.strip():
                raise ApprovalInvalidError("CONTEXT_MISMATCH", f"context '{context_hash}' does not match approved '{binding.context_hash}'")

    def validate(
        self,
        approval_id: str,
        *,
        mission_id: str,
        actor_id: str,
        tenant_id: str,
        capabilities: frozenset[str],
        resource_urls: frozenset[str],
        role: str | None = None,
        worker_class: str | None = None,
        effect_class: str | None = None,
        context_hash: str | None = None,
    ) -> ApprovalBinding:
        """Non-consuming validation. Validates all scope points against ledger or memory."""
        binding: ApprovalBinding | LedgerRecord | None = None

        if self.ledger is not None:
            record = self.ledger.load(approval_id)
            if record is None:
                raise ApprovalInvalidError("UNKNOWN_APPROVAL", f"{approval_id} never issued")
            if record.status == "REVOKED":
                raise ApprovalInvalidError("APPROVAL_REVOKED", f"{approval_id} was revoked")
            if record.status == "CONSUMED":
                raise ApprovalInvalidError("APPROVAL_ALREADY_CONSUMED", f"{approval_id} already consumed")
            binding = record
        else:
            with self._guard:
                binding = self._issued.get(approval_id)
            if binding is None:
                raise ApprovalInvalidError("UNKNOWN_APPROVAL", f"{approval_id} was never issued by authority")
            with self._guard:
                if approval_id in self._consumed:
                    raise ApprovalInvalidError("APPROVAL_ALREADY_CONSUMED", f"{approval_id} already consumed")

        self._assert_binding_matches(
            binding,
            mission_id=mission_id,
            actor_id=actor_id,
            tenant_id=tenant_id,
            capabilities=capabilities,
            resource_urls=resource_urls,
            role=role,
            worker_class=worker_class,
            effect_class=effect_class,
            context_hash=context_hash,
        )

        now = self.clock()
        if now >= binding.expires_at:
            raise ApprovalInvalidError("APPROVAL_EXPIRED", f"expired at {binding.expires_at.isoformat()}")

        if isinstance(binding, LedgerRecord):
            return ApprovalBinding(
                approval_id=binding.approval_id,
                mission_id=binding.mission_id,
                actor_id=binding.actor_id,
                tenant_id=binding.tenant_id,
                capabilities=binding.capabilities,
                resource_urls=binding.resource_urls,
                issued_by=binding.issued_by,
                issued_at=binding.issued_at,
                expires_at=binding.expires_at,
                permitted_roles=binding.permitted_roles,
                permitted_workers=binding.permitted_workers,
                permitted_execution_classes=binding.permitted_execution_classes,
                context_hash=binding.context_hash,
            )
        return binding

    def consume(
        self,
        approval_id: str,
        *,
        mission_id: str,
        actor_id: str,
        tenant_id: str,
        capabilities: frozenset[str],
        resource_urls: frozenset[str],
        role: str | None = None,
        worker_class: str | None = None,
        effect_class: str | None = None,
        context_hash: str | None = None,
    ) -> ApprovalBinding:
        """Atomic consumption: validates scope under write lock and transitions status to CONSUMED."""
        if self.ledger is not None:
            try:
                rec = self.ledger.validate_and_consume(
                    approval_id,
                    mission_id=mission_id,
                    actor_id=actor_id,
                    tenant_id=tenant_id,
                    capabilities=capabilities,
                    resource_urls=resource_urls,
                    role=role or "",
                    worker_class=worker_class or "",
                    effect_class=effect_class or "",
                    context_hash=context_hash or "",
                    now=self.clock(),
                )
                with self._guard:
                    self._consumed[approval_id] = f"{self.clock().isoformat()} mission={mission_id}"
                return ApprovalBinding(
                    approval_id=rec.approval_id,
                    mission_id=rec.mission_id,
                    actor_id=rec.actor_id,
                    tenant_id=rec.tenant_id,
                    capabilities=rec.capabilities,
                    resource_urls=rec.resource_urls,
                    issued_by=rec.issued_by,
                    issued_at=rec.issued_at,
                    expires_at=rec.expires_at,
                    permitted_roles=rec.permitted_roles,
                    permitted_workers=rec.permitted_workers,
                    permitted_execution_classes=rec.permitted_execution_classes,
                    context_hash=rec.context_hash,
                )
            except LedgerError as exc:
                raise ApprovalInvalidError(exc.code, exc.detail) from exc

        # In-memory path with mutex lock
        with self._guard:
            binding = self.validate(
                approval_id,
                mission_id=mission_id,
                actor_id=actor_id,
                tenant_id=tenant_id,
                capabilities=capabilities,
                resource_urls=resource_urls,
                role=role,
                worker_class=worker_class,
                effect_class=effect_class,
                context_hash=context_hash,
            )
            if approval_id in self._consumed:
                raise ApprovalInvalidError("APPROVAL_ALREADY_CONSUMED", f"{approval_id} already consumed")
            self._consumed[approval_id] = f"{self.clock().isoformat()} mission={mission_id}"
            return binding

    def revoke(self, approval_id: str, *, by: str, reason: str) -> None:
        if self.ledger is not None:
            try:
                self.ledger.revoke(approval_id, by=by, reason=reason, now=self.clock())
            except LedgerError as exc:
                raise ApprovalInvalidError(exc.code, exc.detail) from exc
        else:
            with self._guard:
                if approval_id in self._consumed:
                    raise ApprovalInvalidError("APPROVAL_ALREADY_CONSUMED", approval_id)
                self._consumed[approval_id] = f"REVOKED by {by}: {reason}"

    def status(self, approval_id: str) -> str:
        if self.ledger is not None:
            return self.ledger.status(approval_id)
        with self._guard:
            if approval_id in self._consumed:
                if "REVOKED" in self._consumed[approval_id]:
                    return "REVOKED"
                return "CONSUMED"
            if approval_id in self._issued:
                return "ISSUED"
        return "UNKNOWN"

"""Typed delegation + subset invariant (Wave 3, §16-§17).

Mechanical invariant: CHILD_AUTHORITY ⊆ PARENT_DELEGATABLE_AUTHORITY.
Delegations are capability-, mission-, tenant-bound and time-limited.
Explicit deny overrides allow at every layer. Refusal is policy denial
(REFUSED), never a system failure (§44).
"""
from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from .manifest import KNOWN_CAPABILITIES

GOVERNANCE_ROOT_ACTOR = "governance"
MAX_PROVENANCE_DEPTH = 16

if TYPE_CHECKING:
    from .manifest import AgentManifest


class DelegationRefusedError(PermissionError):
    """REFUSED: policy/authority intentionally denied (§44)."""


class Delegation(BaseModel):
    """§16 typed delegation object."""

    model_config = ConfigDict(frozen=True)

    delegation_id: str
    parent_agent: str
    child_agent: str
    mission_id: str
    capabilities: frozenset[str]
    resource_scope: tuple[str, ...] = ()
    tenant: str = ""
    issued_at: datetime
    expires_at: datetime
    approval_reference: str = ""
    evidence_reference: str = ""

    def is_expired(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(UTC)
        return now >= self.expires_at


class DelegationAuthority:
    """Grants child delegations strictly within parent authority.

    §17 subset invariant: CHILD_AUTHORITY ⊆ PARENT_DELEGATABLE_AUTHORITY.
    §10 no self-grant: an agent can never grant or extend its own authority.
    """

    def __init__(self) -> None:
        self._delegatable: dict[str, frozenset[str]] = {}
        # §10+: authority provenance — agent_id -> agent that granted its
        # delegatable authority. Root = GOVERNANCE_ROOT_ACTOR (§6: resolved
        # structurally, not by string acceptance of arbitrary names).
        self._grantor_of: dict[str, str] = {}
        # §6: registered trusted authority actors (structural root set)
        self._trusted_roots: set[str] = {GOVERNANCE_ROOT_ACTOR}
        # §9 replay protection: approval references are single-use
        self._consumed_approvals: set[str] = set()
        # §7 concurrency: per-approval locks (thread-level exactly-once)
        self._approval_locks_guard = threading.Lock()
        self._approval_locks: dict[str, threading.Lock] = {}
        # §10 payload binding: delegation_id -> hash at issue time
        self._issued_hashes: dict[str, str] = {}

    # -- §6 structural root --------------------------------------------------

    def register_trusted_root(self, actor: str) -> None:
        """Register an actor as a trusted authority root. Only roots may
        grant delegatable authority without themselves being granted."""
        self._trusted_roots.add(actor)

    def _has_governance_root(self, agent_id: str, seen: set[str] | None = None) -> bool:
        """§5 (Checkpoint 2): bounded, cycle-safe provenance walk.

        Defends against A→B→C→A cycles, excessive chain depth, missing
        ancestors, and unknown/untrusted roots. Iterative traversal with a
        visited set — never unbounded recursion."""
        seen = seen or set()
        current = agent_id
        depth = 0
        while current in self._grantor_of:
            if current in seen:
                return False  # cycle (covers A↔B and A→B→C→A)
            seen.add(current)
            depth += 1
            if depth > MAX_PROVENANCE_DEPTH:
                return False  # excessive chain depth
            grantor = self._grantor_of[current]
            if grantor in self._trusted_roots:
                return True
            if grantor not in self._grantor_of:
                return False  # missing ancestor: grantor has no provenance of its own
            current = grantor
        return False

    def provenance_reason(self, agent_id: str) -> str:
        """Diagnostic: why provenance failed (cycle/depth/missing/root)."""
        seen: set[str] = set()
        current = agent_id
        depth = 0
        while current in self._grantor_of:
            if current in seen:
                return f"CYCLE at {current}"
            seen.add(current)
            depth += 1
            if depth > MAX_PROVENANCE_DEPTH:
                return f"DEPTH_EXCEEDED at {current}"
            grantor = self._grantor_of[current]
            if grantor in self._trusted_roots:
                return "ROOTED"
            if grantor not in self._grantor_of:
                return f"MISSING_ANCESTOR: {grantor} has no provenance"
            current = grantor
        return "UNROOTED"

    def set_delegatable(
        self, parent_agent_id: str, capabilities: set[str] | frozenset[str], *, actor: str
    ) -> None:
        """Governance-only: an agent may never extend its own delegatable
        authority (§10 AGENT_SELF_GRANT = DENIED)."""
        if actor == parent_agent_id:
            raise DelegationRefusedError("AGENT_SELF_GRANT = DENIED: agents cannot modify their own authority")
        unknown = sorted(c for c in capabilities if c not in KNOWN_CAPABILITIES)
        if unknown:
            raise ValueError(f"unknown capabilities cannot be made delegatable: {unknown}")
        self._grantor_of[parent_agent_id] = actor
        self._delegatable[parent_agent_id] = frozenset(capabilities)

    def delegatable(self, parent_agent_id: str) -> frozenset[str]:
        return self._delegatable.get(parent_agent_id, frozenset())

    def consume_approval(self, approval_reference: str) -> bool:
        """§7/§9: exactly-once approval consumption. Returns True when this
        call is the FIRST consumer; False if already consumed. Thread-safe
        via per-approval lock: two concurrent consumers of the same
        approval → exactly one success, exactly one refusal.

        NOTE (§7 Directive): this in-process lock is authoritative only for
        the in-process runtime; the real persistence-backend proof (Wave 5)
        must extend this to cross-process exactly-once."""
        with self._approval_locks_guard:
            lock = self._approval_locks.setdefault(approval_reference, threading.Lock())
        with lock:
            if approval_reference in self._consumed_approvals:
                return False
            self._consumed_approvals.add(approval_reference)
            return True

    def issue(
        self,
        *,
        parent_agent: str,
        child_manifest: AgentManifest,
        delegation_id: str,
        mission_id: str,
        capabilities: list[str],
        tenant: str = "",
        resource_scope: tuple[str, ...] = (),
        ttl_seconds: int = 3600,
        issued_at: datetime | None = None,
        approval_reference: str = "",
        require_approval: bool = False,
    ) -> Delegation:
        """Issue or REFUSE. The subset invariant is mechanical (§17):
        child capabilities ⊆ parent delegatable; parent-forbidden and
        child-forbidden capabilities can never flow through. §9: when
        require_approval is set (consequential capabilities), a missing
        approval reference REFUSES the delegation."""
        if ttl_seconds <= 0:
            raise DelegationRefusedError("delegation TTL must be positive")
        if child_manifest.agent_id == parent_agent:
            raise DelegationRefusedError("AGENT_SELF_GRANT = DENIED: an agent cannot delegate to itself")
        now = issued_at or datetime.now(UTC)
        if not self._has_governance_root(parent_agent):
            raise DelegationRefusedError(
                "delegation refused: grantor authority has no chain to the governance root (§10 provenance)"
            )
        delegatable = self._delegatable.get(parent_agent, frozenset())
        for cap in capabilities:
            if cap not in delegatable:
                raise DelegationRefusedError(f"capability not delegable by parent: {cap}")
            if cap in child_manifest.forbidden_capabilities:
                raise DelegationRefusedError(f"capability forbidden for child: {cap}")
        if require_approval and not approval_reference:
            raise DelegationRefusedError("MISSING_APPROVAL: consequential delegation requires approval_reference")
        if approval_reference and not self.consume_approval(approval_reference):
            raise DelegationRefusedError(f"APPROVAL_REPLAYED: approval {approval_reference} already consumed")
        if delegation_id in self._issued_hashes:
            raise DelegationRefusedError(f"DELEGATION_ID_REUSED: {delegation_id} already issued")
        delegation = Delegation(
            delegation_id=delegation_id,
            parent_agent=parent_agent,
            child_agent=child_manifest.agent_id,
            mission_id=mission_id,
            capabilities=frozenset(capabilities),
            resource_scope=resource_scope,
            tenant=tenant,
            issued_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
            approval_reference=approval_reference,
        )
        self._issued_hashes[delegation_id] = self.delegation_payload_hash(delegation)
        return delegation

    def delegation_payload_hash(self, delegation: Delegation) -> str:
        """§4 (Checkpoint 2): binds EVERY authority-bearing field via
        canonical_hash — delegation_id, grantor, grantee, mission, tenant,
        capabilities, resource_scope, issued/expires, approval_reference.
        Mutation of any authority-bearing field is detected."""
        from agent_runtime.canonical import canonical_hash

        return canonical_hash(delegation.model_dump(mode="json"))

    def check_use(
        self,
        delegation: Delegation,
        *,
        capability: str,
        mission_id: str,
        tenant: str,
        resource: str | None = None,
        now: datetime | None = None,
    ) -> None:
        """Validate a capability use against its delegation. Raises
        DelegationRefusedError on any mismatch (fail closed)."""
        # §10 payload binding: the delegation object must be byte-identical
        # (semantically) to what was issued — a mutated/copied object is refused.
        issued_hash = self._issued_hashes.get(delegation.delegation_id)
        if issued_hash is not None and issued_hash != self.delegation_payload_hash(delegation):
            raise DelegationRefusedError(
                "DELEGATION_PAYLOAD_MUTATED: delegation does not match its issued form"
            )
        if delegation.is_expired(now):
            raise DelegationRefusedError("delegation expired")
        if delegation.mission_id != mission_id:
            raise DelegationRefusedError(f"mission mismatch: delegation bound to {delegation.mission_id}")
        if delegation.tenant and delegation.tenant != tenant:
            raise DelegationRefusedError(f"tenant mismatch: delegation bound to {delegation.tenant}")
        if capability not in delegation.capabilities:
            raise DelegationRefusedError(f"capability not delegated: {capability}")
        if resource is not None and delegation.resource_scope:
            allowed = any(
                resource == s or resource.startswith(s.rstrip("*"))
                for s in delegation.resource_scope
            )
            if not allowed:
                raise DelegationRefusedError(f"resource outside delegation scope: {resource[:64]}")

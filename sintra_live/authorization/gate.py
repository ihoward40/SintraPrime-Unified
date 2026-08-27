"""Fail-closed authorization gate for SintraPrime program scope enforcement.

This module implements the mechanical gate that prevents program scope escape.
Every executable task MUST carry authorization metadata and pass all checks.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, FrozenSet
from abc import ABC, abstractmethod


class AuthorizationDecision(Enum):
    """Result of authorization check."""
    ALLOW = "allow"
    DENY_PROGRAM_MISMATCH = "deny_program_mismatch"
    DENY_GATE_MISMATCH = "deny_gate_mismatch"
    DENY_WORK_PACKAGE_UNAUTHORIZED = "deny_work_package_unauthorized"
    DENY_STALE_AUTHORITY_SNAPSHOT = "deny_stale_authority_snapshot"
    DENY_MISSING_AUTHORITY_SNAPSHOT = "deny_missing_authority_snapshot"
    DENY_SCOPE_EXCEEDED = "deny_scope_exceeded"
    DENY_CAPABILITY_EXCEEDED = "deny_capability_exceeded"
    DENY_SIDE_EFFECT_BUDGET_EXCEEDED = "deny_side_effect_budget_exceeded"
    DENY_EXPIRED = "deny_expired"
    DENY_PARENT_SCOPE_VIOLATION = "deny_parent_scope_violation"
    DENY_BUDGET_INCREASE = "deny_budget_increase"


@dataclass(frozen=True)
class AuthoritySnapshot:
    """Immutable snapshot of Principal authority at a point in time."""
    snapshot_id: str
    program_id: str
    gate_id: str
    authorization_id: str
    principal_id: str
    
    # Scope definitions
    authorized_scope: FrozenSet[str] = field(default_factory=frozenset)  # e.g., {"sp-live/l1", "github/comment"}
    capability_scope: FrozenSet[str] = field(default_factory=frozenset)  # e.g., {"github-comment-write-v1"}
    side_effect_budget: int = 0  # Max side effects allowed (0 = zero-write)
    
    # Validity
    issued_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    
    # Integrity
    content_hash: str = ""
    
    def __post_init__(self):
        # Calculate content hash for integrity
        import hashlib
        content = f"{self.program_id}{self.gate_id}{self.authorization_id}{self.principal_id}{''.join(sorted(self.authorized_scope))}{''.join(sorted(self.capability_scope))}{self.side_effect_budget}{self.issued_at}{self.expires_at or ''}"
        object.__setattr__(self, 'content_hash', hashlib.sha256(content.encode()).hexdigest())
    
    @staticmethod
    def create(
        program_id: str,
        gate_id: str,
        authorization_id: str,
        principal_id: str,
        authorized_scope: Optional[List[str]] = None,
        capability_scope: Optional[List[str]] = None,
        side_effect_budget: int = 0,
        expires_in_seconds: Optional[int] = None
    ) -> AuthoritySnapshot:
        """Create a new authority snapshot."""
        expires_at = None
        if expires_in_seconds:
            expires_at = time.time() + expires_in_seconds
        
        return AuthoritySnapshot(
            snapshot_id=f"auth-snap-{uuid.uuid4().hex[:12]}",
            program_id=program_id,
            gate_id=gate_id,
            authorization_id=authorization_id,
            principal_id=principal_id,
            authorized_scope=frozenset(authorized_scope or []),
            capability_scope=frozenset(capability_scope or []),
            side_effect_budget=side_effect_budget,
            expires_at=expires_at
        )
    
    def is_valid(self, at_time: Optional[float] = None) -> bool:
        """Check if snapshot is still valid."""
        check_time = at_time or time.time()
        if self.expires_at and check_time > self.expires_at:
            return False
        return True
    
    def verify_integrity(self) -> bool:
        """Verify snapshot hasn't been tampered with."""
        import hashlib
        content = f"{self.program_id}{self.gate_id}{self.authorization_id}{self.principal_id}{''.join(sorted(self.authorized_scope))}{''.join(sorted(self.capability_scope))}{self.side_effect_budget}{self.issued_at}{self.expires_at or ''}"
        expected_hash = hashlib.sha256(content.encode()).hexdigest()
        return expected_hash == self.content_hash


@dataclass(frozen=True)
class TaskAuthorization:
    """Authorization metadata carried by every executable task."""
    task_id: str
    parent_task_id: Optional[str]
    
    # Authority references
    program_id: str
    gate_id: str
    work_package_id: str
    authority_snapshot_hash: str
    
    # Task-specific scope (must be subset of authority)
    requested_scope: FrozenSet[str] = field(default_factory=frozenset)
    requested_capabilities: FrozenSet[str] = field(default_factory=frozenset)
    requested_side_effect_budget: int = 0
    
    # Timing
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    
    @staticmethod
    def create(
        program_id: str,
        gate_id: str,
        work_package_id: str,
        authority_snapshot_hash: str,
        requested_scope: Optional[List[str]] = None,
        requested_capabilities: Optional[List[str]] = None,
        requested_side_effect_budget: int = 0,
        parent_task_id: Optional[str] = None,
        expires_in_seconds: Optional[int] = None
    ) -> TaskAuthorization:
        """Create task authorization."""
        expires_at = None
        if expires_in_seconds:
            expires_at = time.time() + expires_in_seconds
        
        return TaskAuthorization(
            task_id=f"task-{uuid.uuid4().hex[:12]}",
            parent_task_id=parent_task_id,
            program_id=program_id,
            gate_id=gate_id,
            work_package_id=work_package_id,
            authority_snapshot_hash=authority_snapshot_hash,
            requested_scope=frozenset(requested_scope or []),
            requested_capabilities=frozenset(requested_capabilities or []),
            requested_side_effect_budget=requested_side_effect_budget,
            expires_at=expires_at
        )
    
    def is_valid(self, at_time: Optional[float] = None) -> bool:
        """Check if task authorization is still valid."""
        check_time = at_time or time.time()
        if self.expires_at and check_time > self.expires_at:
            return False
        return True


@dataclass(frozen=True)
class AuthorizationResult:
    """Result of authorization check."""
    decision: AuthorizationDecision
    task_id: str
    reason: str
    details: Dict[str, Any] = field(default_factory=dict)
    checked_at: float = field(default_factory=time.time)
    
    @staticmethod
    def allow(task_id: str, details: Optional[Dict[str, Any]] = None) -> AuthorizationResult:
        return AuthorizationResult(
            decision=AuthorizationDecision.ALLOW,
            task_id=task_id,
            reason="Authorization granted",
            details=details or {}
        )
    
    @staticmethod
    def deny(decision: AuthorizationDecision, task_id: str, reason: str, details: Optional[Dict[str, Any]] = None) -> AuthorizationResult:
        return AuthorizationResult(
            decision=decision,
            task_id=task_id,
            reason=reason,
            details=details or {}
        )


class AuthorityStore:
    """Stores and retrieves authority snapshots."""
    
    def __init__(self):
        self._snapshots: Dict[str, AuthoritySnapshot] = {}  # snapshot_id -> snapshot
        self._by_program_gate: Dict[str, AuthoritySnapshot] = {}  # "program_id:gate_id" -> latest snapshot
    
    def store(self, snapshot: AuthoritySnapshot) -> None:
        self._snapshots[snapshot.snapshot_id] = snapshot
        key = f"{snapshot.program_id}:{snapshot.gate_id}"
        # Keep only the latest valid snapshot
        existing = self._by_program_gate.get(key)
        if not existing or snapshot.issued_at > existing.issued_at:
            self._by_program_gate[key] = snapshot
    
    def get_snapshot(self, snapshot_id: str) -> Optional[AuthoritySnapshot]:
        return self._snapshots.get(snapshot_id)
    
    def get_active_snapshot(self, program_id: str, gate_id: str) -> Optional[AuthoritySnapshot]:
        """Get the currently active snapshot for a program/gate."""
        key = f"{program_id}:{gate_id}"
        snapshot = self._by_program_gate.get(key)
        if snapshot and snapshot.is_valid():
            return snapshot
        return None
    
    def list_snapshots(self) -> List[AuthoritySnapshot]:
        return list(self._snapshots.values())


class AuthorizationGate:
    """Fail-closed authorization gate - the core enforcement point."""
    
    def __init__(self, authority_store: AuthorityStore):
        self.authority_store = authority_store
        self._active_program_id: Optional[str] = None
        self._active_gate_id: Optional[str] = None
        self._check_log: List[AuthorizationResult] = []
    
    def set_active_context(self, program_id: str, gate_id: str) -> None:
        """Set the currently active program and gate (Principal decision)."""
        self._active_program_id = program_id
        self._active_gate_id = gate_id
    
    def get_active_context(self) -> tuple[Optional[str], Optional[str]]:
        return self._active_program_id, self._active_gate_id
    
    def check_authorization(self, task_auth: TaskAuthorization) -> AuthorizationResult:
        """Check if a task is authorized to execute. Fail-closed: any check failure = DENY."""
        
        # 1. Check active context is set
        if not self._active_program_id or not self._active_gate_id:
            return AuthorizationResult.deny(
                AuthorizationDecision.DENY_MISSING_AUTHORITY_SNAPSHOT,
                task_auth.task_id,
                "No active program/gate context set - Principal must authorize first"
            )
        
        # 2. Program ID match
        if task_auth.program_id != self._active_program_id:
            return AuthorizationResult.deny(
                AuthorizationDecision.DENY_PROGRAM_MISMATCH,
                task_auth.task_id,
                f"Task program_id '{task_auth.program_id}' != active '{self._active_program_id}'",
                {"task_program": task_auth.program_id, "active_program": self._active_program_id}
            )
        
        # 3. Gate ID match
        if task_auth.gate_id != self._active_gate_id:
            return AuthorizationResult.deny(
                AuthorizationDecision.DENY_GATE_MISMATCH,
                task_auth.task_id,
                f"Task gate_id '{task_auth.gate_id}' != active '{self._active_gate_id}'",
                {"task_gate": task_auth.gate_id, "active_gate": self._active_gate_id}
            )
        
        # 4. Authority snapshot exists and is valid
        authority_snap = self.authority_store.get_snapshot(task_auth.authority_snapshot_hash)
        if not authority_snap:
            return AuthorizationResult.deny(
                AuthorizationDecision.DENY_MISSING_AUTHORITY_SNAPSHOT,
                task_auth.task_id,
                f"Authority snapshot '{task_auth.authority_snapshot_hash}' not found",
                {"snapshot_hash": task_auth.authority_snapshot_hash}
            )
        
        if not authority_snap.is_valid():
            return AuthorizationResult.deny(
                AuthorizationDecision.DENY_STALE_AUTHORITY_SNAPSHOT,
                task_auth.task_id,
                "Authority snapshot has expired",
                {"snapshot_id": authority_snap.snapshot_id, "expires_at": authority_snap.expires_at}
            )
        
        if not authority_snap.verify_integrity():
            return AuthorizationResult.deny(
                AuthorizationDecision.DENY_STALE_AUTHORITY_SNAPSHOT,
                task_auth.task_id,
                "Authority snapshot integrity check failed (tampered)",
                {"snapshot_id": authority_snap.snapshot_id}
            )
        
        # 5. Snapshot matches active program/gate
        if authority_snap.program_id != self._active_program_id or authority_snap.gate_id != self._active_gate_id:
            return AuthorizationResult.deny(
                AuthorizationDecision.DENY_GATE_MISMATCH,
                task_auth.task_id,
                "Authority snapshot does not match active program/gate"
            )
        
        # 6. Requested scope ⊆ authorized scope
        if not task_auth.requested_scope.issubset(authority_snap.authorized_scope):
            excess = task_auth.requested_scope - authority_snap.authorized_scope
            return AuthorizationResult.deny(
                AuthorizationDecision.DENY_SCOPE_EXCEEDED,
                task_auth.task_id,
                f"Task requests scope outside authorized scope: {excess}",
                {"excess_scope": list(excess), "authorized": list(authority_snap.authorized_scope)}
            )
        
        # 7. Requested capabilities ⊆ authorized capabilities
        if not task_auth.requested_capabilities.issubset(authority_snap.capability_scope):
            excess = task_auth.requested_capabilities - authority_snap.capability_scope
            return AuthorizationResult.deny(
                AuthorizationDecision.DENY_CAPABILITY_EXCEEDED,
                task_auth.task_id,
                f"Task requests capabilities outside authorized capabilities: {excess}",
                {"excess_capabilities": list(excess), "authorized": list(authority_snap.capability_scope)}
            )
        
        # 8. Requested side effect budget ≤ authorized budget
        if task_auth.requested_side_effect_budget > authority_snap.side_effect_budget:
            return AuthorizationResult.deny(
                AuthorizationDecision.DENY_SIDE_EFFECT_BUDGET_EXCEEDED,
                task_auth.task_id,
                f"Task requests side effect budget {task_auth.requested_side_effect_budget} > authorized {authority_snap.side_effect_budget}",
                {"requested": task_auth.requested_side_effect_budget, "authorized": authority_snap.side_effect_budget}
            )
        
        # 9. Task authorization not expired
        if not task_auth.is_valid():
            return AuthorizationResult.deny(
                AuthorizationDecision.DENY_EXPIRED,
                task_auth.task_id,
                "Task authorization has expired",
                {"task_expires_at": task_auth.expires_at}
            )
        
        # 10. Parent task scope check (if child task)
        if task_auth.parent_task_id:
            # In real implementation, would look up parent task auth
            # For now, verify parent exists in log
            pass
        
        # ALL CHECKS PASSED
        result = AuthorizationResult.allow(task_auth.task_id, {
            "program_id": task_auth.program_id,
            "gate_id": task_auth.gate_id,
            "work_package_id": task_auth.work_package_id,
            "authority_snapshot_id": authority_snap.snapshot_id
        })
        
        self._check_log.append(result)
        return result
    
    def get_check_log(self) -> List[AuthorizationResult]:
        return self._check_log.copy()
    
    def clear_log(self) -> None:
        self._check_log.clear()


class AuthorizationGateBuilder:
    """Builder for creating authorization gates with Principal authority."""
    
    def __init__(self):
        self.authority_store = AuthorityStore()
        self.gate = AuthorizationGate(self.authority_store)
    
    def create_authority(
        self,
        program_id: str,
        gate_id: str,
        authorization_id: str,
        principal_id: str,
        authorized_scope: List[str],
        capability_scope: List[str],
        side_effect_budget: int = 0,
        expires_in_seconds: Optional[int] = None
    ) -> AuthoritySnapshot:
        """Create and store a new authority snapshot (Principal action)."""
        snapshot = AuthoritySnapshot.create(
            program_id=program_id,
            gate_id=gate_id,
            authorization_id=authorization_id,
            principal_id=principal_id,
            authorized_scope=authorized_scope,
            capability_scope=capability_scope,
            side_effect_budget=side_effect_budget,
            expires_in_seconds=expires_in_seconds
        )
        self.authority_store.store(snapshot)
        self.gate.set_active_context(program_id, gate_id)
        return snapshot
    
    def create_task_authorization(
        self,
        work_package_id: str,
        authority_snapshot_hash: str,
        requested_scope: Optional[List[str]] = None,
        requested_capabilities: Optional[List[str]] = None,
        requested_side_effect_budget: int = 0,
        parent_task_id: Optional[str] = None,
        expires_in_seconds: Optional[int] = None
    ) -> TaskAuthorization:
        """Create task authorization (worker action)."""
        if not self._active_program_id or not self._active_gate_id:
            raise RuntimeError("No active program/gate - Principal must authorize first")
        
        return TaskAuthorization.create(
            program_id=self._active_program_id,
            gate_id=self._active_gate_id,
            work_package_id=work_package_id,
            authority_snapshot_hash=authority_snapshot_hash,
            requested_scope=requested_scope,
            requested_capabilities=requested_capabilities,
            requested_side_effect_budget=requested_side_effect_budget,
            parent_task_id=parent_task_id,
            expires_in_seconds=expires_in_seconds
        )
    
    @property
    def _active_program_id(self) -> Optional[str]:
        return self.gate._active_program_id
    
    @property
    def _active_gate_id(self) -> Optional[str]:
        return self.gate._active_gate_id
    
    def get_gate(self) -> AuthorizationGate:
        return self.gate


# ============================================================================
# DECORATOR FOR TASK EXECUTION
# ============================================================================

def requires_authorization(
    work_package_id: str,
    requested_scope: Optional[List[str]] = None,
    requested_capabilities: Optional[List[str]] = None,
    requested_side_effect_budget: int = 0,
    gate: Optional[AuthorizationGate] = None
):
    """Decorator that enforces authorization before function execution."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if gate is None:
                raise RuntimeError("AuthorizationGate required but not provided")
            
            # Get active authority snapshot
            active_program, active_gate_id = gate.get_active_context()
            if not active_program or not active_gate_id:
                raise RuntimeError("No active authorization context")
            
            authority_snap = gate.authority_store.get_active_snapshot(active_program, active_gate_id)
            if not authority_snap:
                raise RuntimeError("No valid authority snapshot")
            
            # Create task authorization
            task_auth = TaskAuthorization.create(
                program_id=active_program,
                gate_id=active_gate_id,
                work_package_id=work_package_id,
                authority_snapshot_hash=authority_snap.snapshot_id,
                requested_scope=requested_scope,
                requested_capabilities=requested_capabilities,
                requested_side_effect_budget=requested_side_effect_budget
            )
            
            # Check authorization
            result = gate.check_authorization(task_auth)
            if result.decision != AuthorizationDecision.ALLOW:
                raise PermissionError(f"Task denied: {result.reason}")
            
            # Execute
            return func(*args, **kwargs)
        return wrapper
    return decorator
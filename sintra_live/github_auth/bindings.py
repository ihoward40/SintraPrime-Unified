"""GitHub Account Binding Records and Schema for M2-A.

This module defines the data structures for GitHub identity/account binding
without performing any live authentication or token issuance.
All credentials are synthetic/mock for offline certification only.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class GitHubAccountBindingStatus(Enum):
    """Status of GitHub account binding."""
    UNBOUND = "UNBOUND"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    BOUND = "BOUND"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class CredentialLeaseStatus(Enum):
    """Status of credential lease."""
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    NEVER_ISSUED = "NEVER_ISSUED"


@dataclass(frozen=True)
class GitHubAccountIdentity:
    """Immutable GitHub account identity for binding."""
    account_id: str
    login: str
    account_type: str  # "User" or "Organization"
    avatar_url: str
    html_url: str
    created_at: str  # ISO timestamp

    def to_digest(self) -> str:
        """Generate SHA-256 digest of account identity for binding."""
        content = f"{self.account_id}|{self.login}|{self.account_type}|{self.avatar_url}|{self.html_url}|{self.created_at}"
        return hashlib.sha256(content.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "account_id": self.account_id,
            "login": self.login,
            "account_type": self.account_type,
            "avatar_url": self.avatar_url,
            "html_url": self.html_url,
            "created_at": self.created_at,
            "digest": self.to_digest()
        }


@dataclass(frozen=True)
class GitHubAccountBinding:
    """Immutable GitHub account binding record."""
    binding_id: str
    principal_id: str
    github_account: GitHubAccountIdentity
    approved_by_principal: bool
    approval_hash: str
    approval_timestamp: float
    created_at: float
    revoked_at: Optional[float] = None
    revocation_reason: Optional[str] = None

    @property
    def status(self) -> GitHubAccountBindingStatus:
        if self.revoked_at is not None:
            return GitHubAccountBindingStatus.REVOKED
        if not self.approved_by_principal:
            return GitHubAccountBindingStatus.PENDING_APPROVAL
        return GitHubAccountBindingStatus.BOUND

    def to_dict(self) -> Dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "principal_id": self.principal_id,
            "github_account": self.github_account.to_dict(),
            "approved_by_principal": self.approved_by_principal,
            "approval_hash": self.approval_hash,
            "approval_timestamp": self.approval_timestamp,
            "created_at": self.created_at,
            "revoked_at": self.revoked_at,
            "revocation_reason": self.revocation_reason,
            "status": self.status.value
        }


@dataclass(frozen=True)
class GitHubCredentialLease:
    """Immutable credential lease (synthetic/mock only - never real tokens)."""
    lease_id: str
    binding_id: str
    scope: List[str]  # e.g., ["repo", "public_repo"]
    issued_at: float
    expires_at: float
    access_token_redacted: str  # Always redacted for synthetic
    refresh_token_redacted: Optional[str] = None
    status: CredentialLeaseStatus = CredentialLeaseStatus.NEVER_ISSUED
    revoked_at: Optional[float] = None

    def is_valid(self, now: float = None) -> bool:
        if now is None:
            now = time.time()
        return (
            self.status == CredentialLeaseStatus.ACTIVE and
            self.issued_at <= now < self.expires_at and
            self.revoked_at is None
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lease_id": self.lease_id,
            "binding_id": self.binding_id,
            "scope": self.scope,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "access_token": self.access_token_redacted,  # Always redacted
            "refresh_token": self.refresh_token_redacted,  # Always redacted
            "status": self.status.value,
            "revoked_at": self.revoked_at,
            "is_valid_now": self.is_valid()
        }


@dataclass(frozen=True)
class GitHubAuthenticationState:
    """Fail-closed authentication state machine."""
    binding_id: str
    state: str = "UNINITIALIZED"  # UNINITIALIZED, PENDING_APPROVAL, AUTHENTICATED, REVOKED, ERROR
    last_transition: float = field(default_factory=time.time)
    failure_count: int = 0
    last_error: Optional[str] = None

    # Valid transitions
    VALID_TRANSITIONS = {
        "UNINITIALIZED": ["PENDING_APPROVAL", "ERROR"],
        "PENDING_APPROVAL": ["AUTHENTICATED", "ERROR", "REVOKED"],
        "AUTHENTICATED": ["REVOKED", "ERROR"],
        "REVOKED": [],
        "ERROR": ["PENDING_APPROVAL", "REVOKED"]
    }

    def can_transition(self, new_state: str) -> bool:
        return new_state in self.VALID_TRANSITIONS.get(self.state, [])

    def transition(self, new_state: str, error: str = None) -> 'GitHubAuthenticationState':
        if not self.can_transition(new_state):
            raise ValueError(f"Invalid transition from {self.state} to {new_state}")

        return GitHubAuthenticationState(
            binding_id=self.binding_id,
            state=new_state,
            last_transition=time.time(),
            failure_count=self.failure_count + (1 if new_state == "ERROR" else 0),
            last_error=error
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "state": self.state,
            "last_transition": self.last_transition,
            "failure_count": self.failure_count,
            "last_error": self.last_error
        }


@dataclass(frozen=True)
class GitHubAuthApprovalRequest:
    """Request for Principal approval of GitHub account binding."""
    request_id: str
    principal_id: str
    github_account: GitHubAccountIdentity
    requested_scope: List[str]
    request_timestamp: float
    action_hash: str  # Hash of the binding action

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "principal_id": self.principal_id,
            "github_account": self.github_account.to_dict(),
            "requested_scope": self.requested_scope,
            "request_timestamp": self.request_timestamp,
            "action_hash": self.action_hash
        }


def create_binding_request(
    principal_id: str,
    github_account: GitHubAccountIdentity,
    requested_scope: List[str]
) -> GitHubAuthApprovalRequest:
    """Create a new binding approval request."""
    request_id = str(uuid.uuid4())
    timestamp = time.time()
    action_content = f"{principal_id}|{github_account.to_digest()}|{json.dumps(requested_scope, sort_keys=True)}|{timestamp}"
    action_hash = hashlib.sha256(action_content.encode()).hexdigest()

    return GitHubAuthApprovalRequest(
        request_id=request_id,
        principal_id=principal_id,
        github_account=github_account,
        requested_scope=requested_scope,
        request_timestamp=timestamp,
        action_hash=action_hash
    )


def create_binding(
    principal_id: str,
    github_account: GitHubAccountIdentity,
    approval_request: GitHubAuthApprovalRequest,
    principal_approval: bool
) -> GitHubAccountBinding:
    """Create a binding record from approved request."""
    return GitHubAccountBinding(
        binding_id=str(uuid.uuid4()),
        principal_id=principal_id,
        github_account=github_account,
        approved_by_principal=principal_approval,
        approval_hash=approval_request.action_hash,
        approval_timestamp=time.time(),
        created_at=time.time()
    )


def create_credential_lease(
    binding_id: str,
    scope: List[str],
    lease_duration_seconds: int = 3600
) -> GitHubCredentialLease:
    """Create a synthetic credential lease (MOCK ONLY - never real tokens)."""
    now = time.time()
    return GitHubCredentialLease(
        lease_id=str(uuid.uuid4()),
        binding_id=binding_id,
        scope=scope,
        issued_at=now,
        expires_at=now + lease_duration_seconds,
        access_token_redacted="ghs_**REDACTED_SYNTHETIC**",
        refresh_token_redacted="ghr_**REDACTED_SYNTHETIC**",
        status=CredentialLeaseStatus.ACTIVE
    )
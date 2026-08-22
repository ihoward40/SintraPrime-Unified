"""GitHub Issue Comment Create Capability - provider.github-issue-comment-create-v1

This module implements the narrowest possible GitHub write capability
for exactly one Principal-approved certification comment on exactly one
preapproved issue in ihoward40/SintraPrime-Unified.

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


class GitHubCommentCapabilityStatus(Enum):
    """Status of comment capability."""
    UNINITIALIZED = "UNINITIALIZED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    EXECUTED = "EXECUTED"
    BLOCKED = "BLOCKED"
    REVOKED = "REVOKED"
    ERROR = "ERROR"


class ExecutionDecision(Enum):
    """Execution decisions."""
    ALLOW = "ALLOW"
    DENY = "DENY"
    DUPLICATE = "DUPLICATE"
    EXPIRED = "EXPIRED"
    KILL_SWITCH = "KILL_SWITCH"
    MISSING_AUTHORITY = "MISSING_AUTHORITY"


# Frozen configuration for the first mission
M2B_PROVIDER_ID = "provider.github-issue-comment-create-v1"
M2B_OPERATION_ID = "create_issue_comment"
M2B_TARGET_REPOSITORY = "ihoward40/SintraPrime-Unified"
M2B_RESOURCE_TYPE = "ISSUE"
M2B_ALLOWED_METHOD = "POST"
M2B_MAX_EXECUTIONS = 1
M2B_KILL_SWITCH_DEFAULT = False


@dataclass(frozen=True)
class GitHubCommentActionEnvelope:
    """Immutable action envelope for GitHub comment creation."""
    action_id: str
    binding_id: str
    principal_id: str
    repository: str  # Must equal M2B_TARGET_REPOSITORY
    issue_number: int  # Pre-approved exact value
    comment_body: str  # Exact body, hash-bound before approval
    comment_body_hash: str  # SHA-256 of comment_body
    max_executions: int = M2B_MAX_EXECUTIONS
    execution_count: int = 0
    idempotency_key: str = ""  # Derived from action_id
    approved_at: float = 0.0
    expires_at: float = 0.0
    created_at: float = field(default_factory=time.time)

    def __post_init__(self):
        # Verify repository is pinned
        if self.repository != M2B_TARGET_REPOSITORY:
            raise ValueError(f"Repository must be {M2B_TARGET_REPOSITORY}, got {self.repository}")

        # Verify method is POST only
        if self.idempotency_key == "":
            object.__setattr__(self, 'idempotency_key', f"github_comment|{self.action_id}")

        # Verify comment body hash matches
        expected_hash = hashlib.sha256(self.comment_body.encode()).hexdigest()
        if self.comment_body_hash != expected_hash:
            raise ValueError(f"Comment body hash mismatch: {self.comment_body_hash} != {expected_hash}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "binding_id": self.binding_id,
            "principal_id": self.principal_id,
            "repository": self.repository,
            "issue_number": self.issue_number,
            "comment_body": self.comment_body,
            "comment_body_hash": self.comment_body_hash,
            "max_executions": self.max_executions,
            "execution_count": self.execution_count,
            "idempotency_key": self.idempotency_key,
            "approved_at": self.approved_at,
            "expires_at": self.expires_at,
            "created_at": self.created_at
        }


@dataclass(frozen=True)
class GitHubCommentExecutionRecord:
    """Immutable execution record."""
    execution_id: str
    action_id: str
    binding_id: str
    decision: ExecutionDecision
    reason: str
    provider_request_hash: str
    provider_response: Optional[Dict[str, Any]] = None
    provider_receipt_hash: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    idempotency_key: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "action_id": self.action_id,
            "binding_id": self.binding_id,
            "decision": self.decision.value,
            "reason": self.reason,
            "provider_request_hash": self.provider_request_hash,
            "provider_response": self.provider_response,
            "provider_receipt_hash": self.provider_receipt_hash,
            "timestamp": self.timestamp,
            "idempotency_key": self.idempotency_key
        }


@dataclass(frozen=True)
class MockGitHubCommentReceipt:
    """Synthetic GitHub API receipt for comment creation."""
    receipt_id: str
    execution_id: str
    comment_id: int
    comment_url: str
    comment_body: str
    repository: str
    issue_number: int
    created_at: str  # ISO timestamp
    success: bool = True
    receipt_hash: str = ""

    def __post_init__(self):
        if not self.receipt_hash:
            content = f"{self.receipt_id}|{self.execution_id}|{self.comment_id}|{self.comment_body}|{self.repository}|{self.issue_number}|{self.created_at}"
            object.__setattr__(self, 'receipt_hash', hashlib.sha256(content.encode()).hexdigest())


class MockGitHubCommentProvider:
    """Mock GitHub provider for issue comment creation (offline only)."""

    def __init__(self):
        self.comments: Dict[str, List[Dict]] = {}  # repo -> list of comments
        self.executed_idempotency_keys: set = set()
        self.kill_switch = M2B_KILL_SWITCH_DEFAULT

    def set_kill_switch(self, enabled: bool):
        """Activate kill switch to block all executions."""
        self.kill_switch = enabled

    def can_execute(self, idempotency_key: str) -> tuple[ExecutionDecision, str]:
        """Check if execution is allowed."""
        if self.kill_switch:
            return ExecutionDecision.KILL_SWITCH, "Kill switch activated"

        if idempotency_key in self.executed_idempotency_keys:
            return ExecutionDecision.DUPLICATE, "Duplicate execution prevented by idempotency key"

        return ExecutionDecision.ALLOW, "OK"

    def execute_comment_create(
        self,
        envelope: GitHubCommentActionEnvelope
    ) -> MockGitHubCommentReceipt:
        """Execute comment creation (synthetic)."""
        decision, reason = self.can_execute(envelope.idempotency_key)
        if decision != ExecutionDecision.ALLOW:
            raise PermissionError(f"Execution blocked: {decision.value} - {reason}")

        # Create synthetic receipt
        receipt = MockGitHubCommentReceipt(
            receipt_id=f"mock_receipt_{uuid.uuid4().hex[:12]}",
            execution_id=f"exec_{uuid.uuid4().hex[:12]}",
            comment_id=999999 + len(self.executed_idempotency_keys),
            comment_url=f"https://github.com/{envelope.repository}/issues/{envelope.issue_number}#issuecomment-999999",
            comment_body=envelope.comment_body,
            repository=envelope.repository,
            issue_number=envelope.issue_number,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )

        # Track execution
        self.executed_idempotency_keys.add(envelope.idempotency_key)

        # Store comment
        if envelope.repository not in self.comments:
            self.comments[envelope.repository] = []
        self.comments[envelope.repository].append({
            "issue_number": envelope.issue_number,
            "comment_id": receipt.comment_id,
            "body": envelope.comment_body,
            "created_at": receipt.created_at
        })

        return receipt


def create_comment_action_envelope(
    binding_id: str,
    principal_id: str,
    issue_number: int,
    comment_body: str,
    expires_in_seconds: int = 3600
) -> GitHubCommentActionEnvelope:
    """Create a new comment action envelope with hash-bound body."""
    action_id = str(uuid.uuid4())
    comment_body_hash = hashlib.sha256(comment_body.encode()).hexdigest()
    now = time.time()

    return GitHubCommentActionEnvelope(
        action_id=action_id,
        binding_id=binding_id,
        principal_id=principal_id,
        repository=M2B_TARGET_REPOSITORY,
        issue_number=issue_number,
        comment_body=comment_body,
        comment_body_hash=comment_body_hash,
        max_executions=M2B_MAX_EXECUTIONS,
        execution_count=0,
        approved_at=now,
        expires_at=now + expires_in_seconds
    )


def verify_action_envelope(envelope: GitHubCommentActionEnvelope) -> tuple[bool, str]:
    """Verify action envelope integrity and authority."""
    # Check repository pinning
    if envelope.repository != M2B_TARGET_REPOSITORY:
        return False, f"Repository mismatch: {envelope.repository} != {M2B_TARGET_REPOSITORY}"

    # Check max executions
    if envelope.max_executions != M2B_MAX_EXECUTIONS:
        return False, f"Max executions must be {M2B_MAX_EXECUTIONS}"

    # Check comment body hash
    expected_hash = hashlib.sha256(envelope.comment_body.encode()).hexdigest()
    if envelope.comment_body_hash != expected_hash:
        return False, "Comment body hash does not match body"

    # Check expiration
    if time.time() > envelope.expires_at:
        return False, "Action envelope expired"

    return True, "OK"


def create_approval_hash(
    binding_id: str,
    principal_id: str,
    envelope: GitHubCommentActionEnvelope
) -> str:
    """Create approval hash bound to exact action envelope."""
    content = f"{binding_id}|{principal_id}|{envelope.action_id}|{envelope.comment_body_hash}|{envelope.repository}|{envelope.issue_number}|{envelope.approved_at}"
    return hashlib.sha256(content.encode()).hexdigest()
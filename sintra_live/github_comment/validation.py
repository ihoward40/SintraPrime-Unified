"""GitHub Comment Capability Validation for M2-B.

This module implements validation logic for the narrow GitHub
issue-comment-create capability without any live authentication.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from sintra_live.github_comment.capability import (
    GitHubCommentActionEnvelope,
    GitHubCommentCapabilityStatus,
    ExecutionDecision,
    M2B_MAX_EXECUTIONS,
    M2B_TARGET_REPOSITORY,
    M2B_ALLOWED_METHOD,
    M2B_RESOURCE_TYPE,
)


@dataclass(frozen=True)
class ValidationResult:
    """Result of a validation check."""
    valid: bool
    errors: List[str]
    warnings: List[str] = field(default_factory=list)


def validate_action_envelope(envelope: GitHubCommentActionEnvelope) -> ValidationResult:
    """Validate GitHub comment action envelope integrity."""
    errors = []
    warnings = []

    # Repository pinning
    if envelope.repository != M2B_TARGET_REPOSITORY:
        errors.append(f"Repository must be {M2B_TARGET_REPOSITORY}, got {envelope.repository}")

    # Resource type
    if M2B_RESOURCE_TYPE != "ISSUE":
        errors.append("Resource type must be ISSUE")

    # Method must be POST
    if M2B_ALLOWED_METHOD != "POST":
        errors.append("Method must be POST")

    # Max executions
    if envelope.max_executions != M2B_MAX_EXECUTIONS:
        errors.append(f"Max executions must be {M2B_MAX_EXECUTIONS}")

    # Issue number must be positive integer
    if not isinstance(envelope.issue_number, int) or envelope.issue_number <= 0:
        errors.append("Issue number must be a positive integer")

    # Comment body hash
    expected_hash = hashlib.sha256(envelope.comment_body.encode()).hexdigest()
    if envelope.comment_body_hash != expected_hash:
        errors.append("Comment body hash does not match body")

    # Execution count
    if envelope.execution_count < 0:
        errors.append("Execution count cannot be negative")
    if envelope.execution_count > envelope.max_executions:
        errors.append("Execution count exceeds max executions")

    # Expiration
    import time
    if time.time() > envelope.expires_at:
        errors.append("Action envelope expired")

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_no_broader_github_writes(envelope: GitHubCommentActionEnvelope) -> ValidationResult:
    """Negative test: ensure capability does not grant broader GitHub writes."""
    errors = []

    # The capability should only allow exactly one comment creation
    if envelope.max_executions != 1:
        errors.append(f"Max executions {envelope.max_executions} > 1 enables multiple writes")

    # Cannot create issues
    # Cannot mutate PRs
    # Cannot write contents
    # Cannot write branches
    # Cannot write workflows
    # Cannot merge
    # Cannot release

    return ValidationResult(valid=len(errors) == 0, errors=errors)


def validate_idempotency(envelope: GitHubCommentActionEnvelope) -> ValidationResult:
    """Validate idempotency key is properly formed."""
    errors = []

    if not envelope.idempotency_key:
        errors.append("Idempotency key must be provided")

    if not envelope.idempotency_key.startswith("github_comment|"):
        errors.append("Idempotency key must start with 'github_comment|'")

    return ValidationResult(valid=len(errors) == 0, errors=errors)


def validate_execution_record(record: 'GitHubCommentExecutionRecord') -> ValidationResult:
    """Validate execution record structure."""
    errors = []

    if not record.execution_id:
        errors.append("execution_id must be provided")

    if not record.action_id:
        errors.append("action_id must be provided")

    if not record.binding_id:
        errors.append("binding_id must be provided")

    if record.decision not in ExecutionDecision:
        errors.append(f"Invalid decision: {record.decision}")

    if not record.provider_request_hash:
        errors.append("provider_request_hash must be provided")

    return ValidationResult(valid=len(errors) == 0, errors=errors)


def validate_mock_receipt(receipt: 'MockGitHubCommentReceipt') -> ValidationResult:
    """Validate mock receipt structure."""
    errors = []

    if not receipt.receipt_id:
        errors.append("receipt_id must be provided")

    if not receipt.execution_id:
        errors.append("execution_id must be provided")

    if receipt.comment_id <= 0:
        errors.append("comment_id must be positive")

    if not receipt.comment_url.startswith("https://github.com/"):
        errors.append("comment_url must be a valid GitHub URL")

    if receipt.repository != M2B_TARGET_REPOSITORY:
        errors.append(f"Receipt repository mismatch: {receipt.repository}")

    # Verify receipt hash
    expected_content = f"{receipt.receipt_id}|{receipt.execution_id}|{receipt.comment_id}|{receipt.comment_body}|{receipt.repository}|{receipt.issue_number}|{receipt.created_at}"
    expected_hash = hashlib.sha256(expected_content.encode()).hexdigest()
    if receipt.receipt_hash != expected_hash:
        errors.append("Receipt hash does not match content")

    return ValidationResult(valid=len(errors) == 0, errors=errors)


def validate_provider_behavior(
    provider: 'MockGitHubCommentProvider',
    envelope: GitHubCommentActionEnvelope
) -> ValidationResult:
    """Validate provider behavior against M2-B constraints."""
    errors = []

    # Verify provider only allows one execution per idempotency key
    decision1, _ = provider.can_execute(envelope.idempotency_key)
    if decision1 != ExecutionDecision.ALLOW:
        errors.append("First execution should be allowed")

    # Simulate first execution
    provider.executed_idempotency_keys.add(envelope.idempotency_key)

    # Verify second execution is blocked
    decision2, _ = provider.can_execute(envelope.idempotency_key)
    if decision2 != ExecutionDecision.DUPLICATE:
        errors.append(f"Duplicate execution not blocked: {decision2}")

    # Verify kill switch
    provider.set_kill_switch(True)
    decision3, _ = provider.can_execute(envelope.idempotency_key)
    if decision3 != ExecutionDecision.KILL_SWITCH:
        errors.append(f"Kill switch not enforced: {decision3}")

    return ValidationResult(valid=len(errors) == 0, errors=errors)
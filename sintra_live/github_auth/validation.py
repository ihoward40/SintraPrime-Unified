"""GitHub Authentication Validation Logic for M2-A.

This module implements issuer/client/subject/scope validation logic
for GitHub account binding without any live authentication.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from sintra_live.github_auth.bindings import (
    GitHubAccountIdentity,
    GitHubAuthApprovalRequest,
    GitHubCredentialLease,
)


# Approved GitHub OAuth scopes for M2-A (minimal set)
ALLOWED_GITHUB_SCOPES: Set[str] = {
    "repo",           # Full repo access (for private repos)
    "public_repo",    # Public repo access only
    "repo:status",    # Commit status access
    "read:org",       # Read org membership
    "user:email",     # User email access
}

# For the specific first mission, only these scopes are allowed
FIRST_MISSION_ALLOWED_SCOPES: Set[str] = {
    "public_repo",    # Only public repo access needed for comment
}

# Pre-approved GitHub account for first mission
PREAPPROVED_GITHUB_ACCOUNT = "ihoward40"

# Approved repository for first mission
PREAPPROVED_REPOSITORY = "ihoward40/SintraPrime-Unified"


@dataclass(frozen=True)
class ValidationResult:
    """Result of a validation check."""
    valid: bool
    errors: List[str]
    warnings: List[str] = field(default_factory=list)

    def __post_init__(self):
        # No need for post_init with field(default_factory=list)
        pass


def validate_github_account_identity(account: GitHubAccountIdentity) -> ValidationResult:
    """Validate GitHub account identity structure."""
    errors = []
    warnings = []

    if not account.account_id or not account.account_id.isdigit():
        errors.append("account_id must be a non-empty numeric string")

    if not account.login or not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-])*[a-zA-Z0-9]$', account.login):
        errors.append("login must be valid GitHub username format")

    if account.account_type not in ("User", "Organization"):
        errors.append("account_type must be 'User' or 'Organization'")

    if not account.avatar_url.startswith("https://avatars.githubusercontent.com/"):
        warnings.append("avatar_url does not match expected GitHub avatar domain")

    if not account.html_url.startswith("https://github.com/"):
        errors.append("html_url must be a valid GitHub profile URL")

    if not account.created_at:
        errors.append("created_at must be provided")

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_scope(scope: List[str], allowed: Set[str] = None) -> ValidationResult:
    """Validate requested OAuth scopes against allowed list."""
    if allowed is None:
        allowed = ALLOWED_GITHUB_SCOPES

    errors = []
    warnings = []

    if not scope:
        errors.append("At least one scope must be requested")
    else:
        for s in scope:
            if s not in allowed:
                errors.append(f"Scope '{s}' is not in allowed list: {sorted(allowed)}")

    # Check for overly broad scopes
    if "repo" in scope and "public_repo" in scope:
        warnings.append("Both 'repo' and 'public_repo' requested; 'repo' supersedes 'public_repo'")

    # Check for dangerous scopes
    dangerous = {"admin:repo_hook", "admin:org", "delete_repo", "workflow"}
    for s in scope:
        if s in dangerous:
            warnings.append(f"Dangerous scope requested: {s}")

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_first_mission_scope(scope: List[str]) -> ValidationResult:
    """Validate scope specifically for the first mission (comment only)."""
    return validate_scope(scope, FIRST_MISSION_ALLOWED_SCOPES)


def validate_approval_binding(
    request: GitHubAuthApprovalRequest,
    principal_id: str,
    approval_hash: str
) -> ValidationResult:
    """Validate that approval is bound to the exact request."""
    errors = []

    if request.principal_id != principal_id:
        errors.append(f"Principal ID mismatch: {request.principal_id} != {principal_id}")

    # Verify action hash matches request content
    # Use same serialization as create_binding_request
    expected_content = f"{principal_id}|{request.github_account.to_digest()}|{json.dumps(request.requested_scope, sort_keys=True)}|{request.request_timestamp}"
    expected_hash = hashlib.sha256(expected_content.encode()).hexdigest()
    if expected_hash != request.action_hash:
        errors.append("Action hash does not match request content")

    if expected_hash != approval_hash:
        errors.append("Approval hash does not match request action hash")

    return ValidationResult(valid=len(errors) == 0, errors=errors)


def validate_credential_lease(lease: GitHubCredentialLease) -> ValidationResult:
    """Validate credential lease structure and non-leakage."""
    errors = []
    warnings = []

    if not lease.lease_id:
        errors.append("lease_id must be provided")

    if not lease.binding_id:
        errors.append("binding_id must be provided")

    if not lease.scope:
        errors.append("At least one scope required")

    if lease.issued_at >= lease.expires_at:
        errors.append("issued_at must be before expires_at")

    # Verify tokens are redacted
    if "REDACTED" not in lease.access_token_redacted:
        errors.append("access_token_redacted must contain 'REDACTED' marker")

    if lease.refresh_token_redacted and "REDACTED" not in lease.refresh_token_redacted:
        errors.append("refresh_token_redacted must contain 'REDACTED' marker")

    # Check lease duration is reasonable (not too long)
    max_duration = 24 * 3600  # 24 hours
    if lease.expires_at - lease.issued_at > max_duration:
        warnings.append(f"Lease duration exceeds {max_duration}s")

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_account_digest_binding(
    binding: 'GitHubAccountBinding',
    expected_principal: str,
    expected_account_digest: str
) -> ValidationResult:
    """Validate that binding matches expected principal and account digest."""
    errors = []

    if binding.principal_id != expected_principal:
        errors.append(f"Binding principal mismatch: {binding.principal_id} != {expected_principal}")

    actual_digest = binding.github_account.to_digest()
    if actual_digest != expected_account_digest:
        errors.append(f"Account digest mismatch: {actual_digest} != {expected_account_digest}")

    if not binding.approved_by_principal:
        errors.append("Binding not approved by principal")

    return ValidationResult(valid=len(errors) == 0, errors=errors)


def validate_no_write_authority(scope: List[str]) -> ValidationResult:
    """Negative test: ensure scope does not grant write authority beyond comment."""
    errors = []

    # Scopes that grant write authority beyond comment
    write_scopes = {"repo", "admin:repo_hook", "admin:org", "delete_repo", "workflow"}

    for s in scope:
        if s in write_scopes:
            errors.append(f"Scope '{s}' grants write authority beyond comment")

    return ValidationResult(valid=len(errors) == 0, errors=errors)


import hashlib
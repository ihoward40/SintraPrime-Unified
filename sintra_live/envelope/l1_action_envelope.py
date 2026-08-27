"""L1 Immutable Action Envelope - Preparation for SP-LIVE-001 First Real Governed Mission."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

# Exact certified values
CAPABILITY_ID = "provider.github-issue-comment-create-v1"
ACTION_TYPE = "CREATE_GITHUB_PR_COMMENT"
PROVIDER = "GitHub"
ACCOUNT = "ihoward40"
REPOSITORY = "ihoward40/SintraPrime-Unified"
RESOURCE_TYPE = "PULL_REQUEST"
RESOURCE_NUMBER = 285
HTTP_METHOD = "POST"
EXACT_ENDPOINT = "/repos/ihoward40/SintraPrime-Unified/issues/285/comments"
COMMENT_BODY = "SintraPrime SP-LIVE-001 governed-action certification: Principal-approved external action successfully executed and verified."
COMMENT_BODY_SHA256 = "9fac685186ee96aa62ff60eb818fe65857530f69e188c74997a035e5b5f842b1"
MAX_EXECUTIONS = 1
CONSEQUENCE_CLASS = "EXTERNAL_COMMUNICATION"

# Program context
ACTIVE_PROGRAM = "SP-LIVE-001"
ACTIVE_GATE = "SP_LIVE_001_L1_FIRST_REAL_GOVERNED_MISSION_001"

# Timezone for display (EDT = UTC-4)
EDT = timezone(timedelta(hours=-4))


@dataclass
class L1ActionEnvelope:
    """Immutable L1 action envelope - one-time execution authority."""
    
    # Program binding
    program_id: str
    gate_id: str
    authorization_id: str
    
    # Principal identity
    principal_id: str
    authenticated_provider_account: str  # Must match GitHub OAuth identity
    
    # Target binding
    repository: str
    resource_type: str
    resource_number: int
    
    # Capability binding (EXACT - no alias/substitution)
    capability: str
    operation: str
    http_method: str
    endpoint: str
    
    # Payload binding
    comment_body: str
    comment_body_sha256: str
    
    # Execution constraints
    consequence_class: str
    max_executions: int
    
    # One-time execution identity
    execution_id: str
    execution_nonce: str
    
    # Execution adapter / provider identity binding
    execution_adapter: str  # e.g., "github-app-live-comment-v1"
    execution_entrypoint_id: str  # e.g., "sintra-live-l1-comment-runner-v1"
    provider_mode: str  # "LIVE" or "MOCK"
    provider_class: str  # "GitHubAppLiveProvider"
    
    # Code baseline identity - frozen at envelope creation
    baseline_commit: str
    baseline_tree: str
    baseline_manifest_sha256: str
    
    # Temporal - ISO 8601 with explicit timezone (UTC)
    created_at_iso: str  # e.g., "2026-08-23T21:05:00+00:00" or "2026-08-23T17:05:00-04:00"
    expires_at_iso: str
    
    # Authority chain
    authority_snapshot_hash: str
    approval_requirement_hash: str
    
    # Envelope integrity
    envelope_hash: str = ""
    
    def __post_init__(self):
        # Calculate envelope hash - include timezone-bearing timestamps and baseline identity
        envelope_content = {
            "program_id": self.program_id,
            "gate_id": self.gate_id,
            "authorization_id": self.authorization_id,
            "principal_id": self.principal_id,
            "authenticated_provider_account": self.authenticated_provider_account,
            "repository": self.repository,
            "resource_type": self.resource_type,
            "resource_number": self.resource_number,
            "capability": self.capability,
            "operation": self.operation,
            "http_method": self.http_method,
            "endpoint": self.endpoint,
            "comment_body": self.comment_body,
            "comment_body_sha256": self.comment_body_sha256,
            "consequence_class": self.consequence_class,
            "max_executions": self.max_executions,
            "execution_id": self.execution_id,
            "execution_nonce": self.execution_nonce,
            "execution_adapter": self.execution_adapter,
            "execution_entrypoint_id": self.execution_entrypoint_id,
            "provider_mode": self.provider_mode,
            "provider_class": self.provider_class,
            "baseline_commit": self.baseline_commit,
            "baseline_tree": self.baseline_tree,
            "baseline_manifest_sha256": self.baseline_manifest_sha256,
            "created_at_iso": self.created_at_iso,
            "expires_at_iso": self.expires_at_iso,
            "authority_snapshot_hash": self.authority_snapshot_hash,
            "approval_requirement_hash": self.approval_requirement_hash,
        }
        
        content_json = json.dumps(envelope_content, sort_keys=True, separators=(",", ":"))
        computed_hash = hashlib.sha256(content_json.encode()).hexdigest()
        object.__setattr__(self, 'envelope_hash', computed_hash)
    
    @property
    def created_at(self) -> float:
        """Unix timestamp for backwards compatibility and comparisons."""
        return datetime.fromisoformat(self.created_at_iso).timestamp()
    
    @property
    def expires_at(self) -> float:
        """Unix timestamp for backwards compatibility and comparisons."""
        return datetime.fromisoformat(self.expires_at_iso).timestamp()
    
    def verify_integrity(self) -> bool:
        """Verify envelope hasn't been tampered with."""
        return self.envelope_hash == self._compute_hash()
    
    def _compute_hash(self) -> str:
        envelope_content = {
            "program_id": self.program_id,
            "gate_id": self.gate_id,
            "authorization_id": self.authorization_id,
            "principal_id": self.principal_id,
            "authenticated_provider_account": self.authenticated_provider_account,
            "repository": self.repository,
            "resource_type": self.resource_type,
            "resource_number": self.resource_number,
            "capability": self.capability,
            "operation": self.operation,
            "http_method": self.http_method,
            "endpoint": self.endpoint,
            "comment_body": self.comment_body,
            "comment_body_sha256": self.comment_body_sha256,
            "consequence_class": self.consequence_class,
            "max_executions": self.max_executions,
            "execution_id": self.execution_id,
            "execution_nonce": self.execution_nonce,
            "execution_adapter": self.execution_adapter,
            "execution_entrypoint_id": self.execution_entrypoint_id,
            "provider_mode": self.provider_mode,
            "provider_class": self.provider_class,
            "baseline_commit": self.baseline_commit,
            "baseline_tree": self.baseline_tree,
            "baseline_manifest_sha256": self.baseline_manifest_sha256,
            "created_at_iso": self.created_at_iso,
            "expires_at_iso": self.expires_at_iso,
            "authority_snapshot_hash": self.authority_snapshot_hash,
            "approval_requirement_hash": self.approval_requirement_hash,
        }
        content_json = json.dumps(envelope_content, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(content_json.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "program_id": self.program_id,
            "gate_id": self.gate_id,
            "authorization_id": self.authorization_id,
            "principal_id": self.principal_id,
            "authenticated_provider_account": self.authenticated_provider_account,
            "repository": self.repository,
            "resource_type": self.resource_type,
            "resource_number": self.resource_number,
            "capability": self.capability,
            "operation": self.operation,
            "http_method": self.http_method,
            "endpoint": self.endpoint,
            "comment_body": self.comment_body,
            "comment_body_sha256": self.comment_body_sha256,
            "consequence_class": self.consequence_class,
            "max_executions": self.max_executions,
            "execution_id": self.execution_id,
            "execution_nonce": self.execution_nonce,
            "execution_adapter": self.execution_adapter,
            "execution_entrypoint_id": self.execution_entrypoint_id,
            "provider_mode": self.provider_mode,
            "provider_class": self.provider_class,
            "baseline_commit": self.baseline_commit,
            "baseline_tree": self.baseline_tree,
            "baseline_manifest_sha256": self.baseline_manifest_sha256,
            "created_at_iso": self.created_at_iso,
            "expires_at_iso": self.expires_at_iso,
            "authority_snapshot_hash": self.authority_snapshot_hash,
            "approval_requirement_hash": self.approval_requirement_hash,
            "envelope_hash": self.envelope_hash,
        }
    
    def display_for_approval(self) -> str:
        """Generate human-readable display for Principal review with explicit timezone."""
        created_dt = datetime.fromisoformat(self.created_at_iso)
        expires_dt = datetime.fromisoformat(self.expires_at_iso)
        
        return f"""======================================================================
L1 ACTION COMMITMENT - PRINCIPAL REVIEW REQUIRED
======================================================================

Program:          {self.program_id}
Gate:             {self.gate_id}
Authorization ID: {self.authorization_id}

Account:          {self.authenticated_provider_account}
Repository:       {self.repository}
Target:           {self.resource_type} #{self.resource_number}

Capability:       {self.capability}
Operation:        {self.operation}
HTTP Method:      {self.http_method}
Endpoint:         {self.endpoint}

Execution Adapter:    {self.execution_adapter}
Execution Entrypoint: {self.execution_entrypoint_id}
Provider Mode:        {self.provider_mode}
Provider Class:       {self.provider_class}

Baseline Commit:  {self.baseline_commit}
Baseline Tree:    {self.baseline_tree}
Baseline Manifest: {self.baseline_manifest_sha256}

Max Executions:   {self.max_executions}
Consequence:      {self.consequence_class}

EXACT BODY:
{self.comment_body}

Body SHA256:      {self.comment_body_sha256}

Execution ID:     {self.execution_id}
Execution Nonce:  {self.execution_nonce}
Envelope SHA256:  {self.envelope_hash}

Created:          {created_dt.isoformat()}
Expires:          {expires_dt.isoformat()}

Authority Snapshot: {self.authority_snapshot_hash[:16]}...
Approval Requirement: {self.approval_requirement_hash[:16]}...

======================================================================
FRESH PRINCIPAL APPROVAL: REQUIRED
POST ENABLED: FALSE
======================================================================"""


@dataclass
class EnvelopeValidator:
    """Validates L1 action envelopes - fail-closed."""
    
    CERTIFIED_CAPABILITY = CAPABILITY_ID
    
    def validate(self, envelope: L1ActionEnvelope) -> tuple[bool, list[str]]:
        """Fail-closed validation - all checks must pass."""
        errors = []
        
        # Program binding
        if envelope.program_id != ACTIVE_PROGRAM:
            errors.append(f"PROGRAM_MISMATCH: expected {ACTIVE_PROGRAM}, got {envelope.program_id}")
        
        # Gate binding
        if envelope.gate_id != ACTIVE_GATE:
            errors.append(f"GATE_MISMATCH: expected {ACTIVE_GATE}, got {envelope.gate_id}")
        
        # Account binding
        if envelope.authenticated_provider_account != ACCOUNT:
            errors.append(f"ACCOUNT_MISMATCH: expected {ACCOUNT}, got {envelope.authenticated_provider_account}")
        
        # Repository pinning
        if envelope.repository != REPOSITORY:
            errors.append(f"REPOSITORY_MISMATCH: expected {REPOSITORY}, got {envelope.repository}")
        
        # Target pinning
        if envelope.resource_type != RESOURCE_TYPE:
            errors.append(f"RESOURCE_TYPE_MISMATCH: expected {RESOURCE_TYPE}, got {envelope.resource_type}")
        if envelope.resource_number != RESOURCE_NUMBER:
            errors.append(f"RESOURCE_NUMBER_MISMATCH: expected {RESOURCE_NUMBER}, got {envelope.resource_number}")
        
        # Capability binding - EXACT match required
        if envelope.capability != self.CERTIFIED_CAPABILITY:
            errors.append(f"CAPABILITY_MISMATCH: expected {self.CERTIFIED_CAPABILITY}, got {envelope.capability}")
        
        # Operation
        if envelope.operation != ACTION_TYPE:
            errors.append(f"OPERATION_MISMATCH: expected {ACTION_TYPE}, got {envelope.operation}")
        
        # HTTP method
        if envelope.http_method != HTTP_METHOD:
            errors.append(f"HTTP_METHOD_MISMATCH: expected {HTTP_METHOD}, got {envelope.http_method}")
        
        # Endpoint
        if envelope.endpoint != EXACT_ENDPOINT:
            errors.append(f"ENDPOINT_MISMATCH: expected {EXACT_ENDPOINT}, got {envelope.endpoint}")
        
        # Body hash binding
        expected_body_hash = hashlib.sha256(envelope.comment_body.encode()).hexdigest()
        if envelope.comment_body_sha256 != expected_body_hash:
            errors.append(f"BODY_HASH_MISMATCH: expected {expected_body_hash}, got {envelope.comment_body_sha256}")
        if envelope.comment_body_sha256 != COMMENT_BODY_SHA256:
            errors.append(f"BODY_HASH_DRIFT: expected certified {COMMENT_BODY_SHA256}, got {envelope.comment_body_sha256}")
        
        # Max executions binding
        if envelope.max_executions != MAX_EXECUTIONS:
            errors.append(f"MAX_EXECUTIONS_MISMATCH: expected {MAX_EXECUTIONS}, got {envelope.max_executions}")
        
        # Execution adapter binding
        from sintra_live.github_comment.capability import (
            M2B_LIVE_EXECUTION_ADAPTER,
            M2B_LIVE_ENTRYPOINT_ID,
            M2B_LIVE_PROVIDER_MODE,
            M2B_LIVE_PROVIDER_CLASS,
        )
        if envelope.execution_adapter != M2B_LIVE_EXECUTION_ADAPTER:
            errors.append(f"EXECUTION_ADAPTER_MISMATCH: expected {M2B_LIVE_EXECUTION_ADAPTER}, got {envelope.execution_adapter}")
        if envelope.execution_entrypoint_id != M2B_LIVE_ENTRYPOINT_ID:
            errors.append(f"EXECUTION_ENTRYPOINT_MISMATCH: expected {M2B_LIVE_ENTRYPOINT_ID}, got {envelope.execution_entrypoint_id}")
        if envelope.provider_mode != M2B_LIVE_PROVIDER_MODE:
            errors.append(f"PROVIDER_MODE_MISMATCH: expected {M2B_LIVE_PROVIDER_MODE}, got {envelope.provider_mode}")
        if envelope.provider_class != M2B_LIVE_PROVIDER_CLASS:
            errors.append(f"PROVIDER_CLASS_MISMATCH: expected {M2B_LIVE_PROVIDER_CLASS}, got {envelope.provider_class}")
        
        # Baseline identity
        if not envelope.baseline_commit:
            errors.append("MISSING_BASELINE_COMMIT")
        if not envelope.baseline_tree:
            errors.append("MISSING_BASELINE_TREE")
        if not envelope.baseline_manifest_sha256:
            errors.append("MISSING_BASELINE_MANIFEST_SHA256")
        
        # Nonce freshness
        if not envelope.execution_nonce:
            errors.append("MISSING_EXECUTION_NONCE")
        
        # Envelope integrity
        if not envelope.verify_integrity():
            errors.append("ENVELOPE_INTEGRITY_FAILURE: envelope_hash mismatch")
        
        # Expiry
        if time.time() > envelope.expires_at:
            errors.append("ENVELOPE_EXPIRED")
        
        # Authority snapshot hash
        if not envelope.authority_snapshot_hash:
            errors.append("MISSING_AUTHORITY_SNAPSHOT_HASH")
        
        # Approval requirement hash
        if not envelope.approval_requirement_hash:
            errors.append("MISSING_APPROVAL_REQUIREMENT_HASH")
        
        return len(errors) == 0, errors


def create_l1_action_envelope(
    authority_snapshot_hash: str,
    approval_requirement_hash: str,
    principal_id: str = "principal-001",
    authenticated_provider_account: str = ACCOUNT,
    expires_in_seconds: int = 3600,  # 1 hour
    execution_nonce: Optional[str] = None,
    baseline_commit: str = "",
    baseline_tree: str = "",
    baseline_manifest_sha256: str = "",
) -> L1ActionEnvelope:
    """Create the L1 action envelope with exact certified values."""
    
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=expires_in_seconds)
    nonce = execution_nonce or uuid.uuid4().hex[:16]
    
    from sintra_live.github_comment.capability import (
        M2B_LIVE_EXECUTION_ADAPTER,
        M2B_LIVE_ENTRYPOINT_ID,
        M2B_LIVE_PROVIDER_MODE,
        M2B_LIVE_PROVIDER_CLASS,
    )
    
    envelope = L1ActionEnvelope(
        program_id=ACTIVE_PROGRAM,
        gate_id=ACTIVE_GATE,
        authorization_id=f"auth-{uuid.uuid4().hex[:12]}",
        principal_id=principal_id,
        authenticated_provider_account=authenticated_provider_account,
        repository=REPOSITORY,
        resource_type=RESOURCE_TYPE,
        resource_number=RESOURCE_NUMBER,
        capability=CAPABILITY_ID,  # EXACT - provider.github-issue-comment-create-v1
        operation=ACTION_TYPE,
        http_method=HTTP_METHOD,
        endpoint=EXACT_ENDPOINT,
        comment_body=COMMENT_BODY,
        comment_body_sha256=COMMENT_BODY_SHA256,
        consequence_class=CONSEQUENCE_CLASS,
        max_executions=MAX_EXECUTIONS,
        execution_id=f"exec-{uuid.uuid4().hex[:12]}",
        execution_nonce=nonce,
        execution_adapter=M2B_LIVE_EXECUTION_ADAPTER,
        execution_entrypoint_id=M2B_LIVE_ENTRYPOINT_ID,
        provider_mode=M2B_LIVE_PROVIDER_MODE,
        provider_class=M2B_LIVE_PROVIDER_CLASS,
        baseline_commit=baseline_commit,
        baseline_tree=baseline_tree,
        baseline_manifest_sha256=baseline_manifest_sha256,
        created_at_iso=now.isoformat(),
        expires_at_iso=expires_at.isoformat(),
        authority_snapshot_hash=authority_snapshot_hash,
        approval_requirement_hash=approval_requirement_hash,
    )
    
    return envelope
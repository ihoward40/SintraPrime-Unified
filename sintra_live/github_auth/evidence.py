"""GitHub Authentication Evidence Chain Generation for M2-A.

This module implements evidence-chain generation for GitHub account binding
certification without any live authentication.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sintra_live.github_auth.bindings import (
    GitHubAccountBinding,
    GitHubAuthApprovalRequest,
    GitHubCredentialLease,
    GitHubAuthenticationState,
)


@dataclass(frozen=True)
class GitHubAuthEvidenceRecord:
    """Immutable evidence record for GitHub authentication events."""
    record_id: str
    event_type: str  # binding_requested, binding_approved, lease_issued, lease_revoked, state_transition
    binding_id: str
    principal_id: str
    payload_hash: str
    timestamp: float
    previous_record_hash: Optional[str] = None
    record_hash: str = ""

    def __post_init__(self):
        if not self.record_hash:
            content = f"{self.record_id}|{self.event_type}|{self.binding_id}|{self.principal_id}|{self.payload_hash}|{self.timestamp}|{self.previous_record_hash or ''}"
            object.__setattr__(self, 'record_hash', hashlib.sha256(content.encode()).hexdigest())


@dataclass
class GitHubAuthEvidenceChain:
    """Append-only evidence chain for GitHub authentication."""
    chain_id: str
    records: List[GitHubAuthEvidenceRecord] = field(default_factory=list)

    def append(self, event_type: str, binding_id: str, principal_id: str, payload: Dict[str, Any]) -> GitHubAuthEvidenceRecord:
        """Append a new evidence record."""
        payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        previous_hash = self.records[-1].record_hash if self.records else None

        record = GitHubAuthEvidenceRecord(
            record_id=str(uuid.uuid4()),
            event_type=event_type,
            binding_id=binding_id,
            principal_id=principal_id,
            payload_hash=payload_hash,
            timestamp=time.time(),
            previous_record_hash=previous_hash
        )
        self.records.append(record)
        return record

    def get_chain_root(self) -> str:
        """Get the root hash of the evidence chain."""
        if not self.records:
            return hashlib.sha256(b"empty").hexdigest()
        return self.records[-1].record_hash

    def verify_chain(self) -> bool:
        """Verify the integrity of the evidence chain."""
        if not self.records:
            return True

        for i, record in enumerate(self.records):
            # Verify record hash
            expected_content = f"{record.record_id}|{record.event_type}|{record.binding_id}|{record.principal_id}|{record.payload_hash}|{record.timestamp}|{record.previous_record_hash or ''}"
            expected_hash = hashlib.sha256(expected_content.encode()).hexdigest()
            if record.record_hash != expected_hash:
                return False

            # Verify chain linkage
            if i > 0:
                if record.previous_record_hash != self.records[i - 1].record_hash:
                    return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "total_records": len(self.records),
            "chain_root": self.get_chain_root(),
            "chain_valid": self.verify_chain(),
            "records": [
                {
                    "record_id": r.record_id,
                    "event_type": r.event_type,
                    "binding_id": r.binding_id,
                    "principal_id": r.principal_id,
                    "payload_hash": r.payload_hash,
                    "timestamp": r.timestamp,
                    "previous_record_hash": r.previous_record_hash,
                    "record_hash": r.record_hash
                }
                for r in self.records
            ]
        }


def create_binding_request_evidence(
    chain: GitHubAuthEvidenceChain,
    request: GitHubAuthApprovalRequest
) -> GitHubAuthEvidenceRecord:
    """Create evidence for binding request."""
    payload = {
        "request_id": request.request_id,
        "principal_id": request.principal_id,
        "github_account": request.github_account.to_dict(),
        "requested_scope": request.requested_scope,
        "request_timestamp": request.request_timestamp,
        "action_hash": request.action_hash
    }
    return chain.append("binding_requested", request.request_id, request.principal_id, payload)


def create_binding_approval_evidence(
    chain: GitHubAuthEvidenceChain,
    binding: GitHubAccountBinding,
    approval_request: GitHubAuthApprovalRequest
) -> GitHubAuthEvidenceRecord:
    """Create evidence for binding approval."""
    payload = {
        "binding_id": binding.binding_id,
        "principal_id": binding.principal_id,
        "github_account": binding.github_account.to_dict(),
        "approved_by_principal": binding.approved_by_principal,
        "approval_hash": binding.approval_hash,
        "approval_timestamp": binding.approval_timestamp,
        "created_at": binding.created_at,
        "request_action_hash": approval_request.action_hash
    }
    return chain.append("binding_approved", binding.binding_id, binding.principal_id, payload)


def create_lease_issued_evidence(
    chain: GitHubAuthEvidenceChain,
    lease: GitHubCredentialLease
) -> GitHubAuthEvidenceRecord:
    """Create evidence for credential lease issuance."""
    payload = lease.to_dict()
    return chain.append("lease_issued", lease.binding_id, lease.binding_id, payload)


def create_lease_revoked_evidence(
    chain: GitHubAuthEvidenceChain,
    binding_id: str,
    principal_id: str,
    lease_id: str,
    reason: str
) -> GitHubAuthEvidenceRecord:
    """Create evidence for credential lease revocation."""
    payload = {
        "lease_id": lease_id,
        "reason": reason,
        "revoked_at": time.time()
    }
    return chain.append("lease_revoked", binding_id, principal_id, payload)


def create_state_transition_evidence(
    chain: GitHubAuthEvidenceChain,
    state: GitHubAuthenticationState
) -> GitHubAuthEvidenceRecord:
    """Create evidence for authentication state transition."""
    payload = state.to_dict()
    return chain.append("state_transition", state.binding_id, state.binding_id, payload)
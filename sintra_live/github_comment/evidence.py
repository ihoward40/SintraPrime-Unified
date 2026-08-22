"""GitHub Comment Capability Evidence Chain Generation for M2-B.

This module implements evidence-chain generation for GitHub comment creation
capability without any live authentication.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sintra_live.github_comment.capability import (
    GitHubCommentActionEnvelope,
    GitHubCommentExecutionRecord,
    MockGitHubCommentReceipt,
)


@dataclass(frozen=True)
class GitHubCommentEvidenceRecord:
    """Immutable evidence record for GitHub comment events."""
    record_id: str
    event_type: str  # action_created, action_approved, execution_attempted, execution_completed, execution_blocked
    action_id: str
    binding_id: str
    principal_id: str
    payload_hash: str
    timestamp: float
    previous_record_hash: Optional[str] = None
    record_hash: str = ""

    def __post_init__(self):
        if not self.record_hash:
            content = f"{self.record_id}|{self.event_type}|{self.action_id}|{self.binding_id}|{self.principal_id}|{self.payload_hash}|{self.timestamp}|{self.previous_record_hash or ''}"
            object.__setattr__(self, 'record_hash', hashlib.sha256(content.encode()).hexdigest())


@dataclass
class GitHubCommentEvidenceChain:
    """Append-only evidence chain for GitHub comment capability."""
    chain_id: str
    records: List[GitHubCommentEvidenceRecord] = field(default_factory=list)

    def append(self, event_type: str, action_id: str, binding_id: str, principal_id: str, payload: Dict[str, Any]) -> GitHubCommentEvidenceRecord:
        """Append a new evidence record."""
        payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        previous_hash = self.records[-1].record_hash if self.records else None

        record = GitHubCommentEvidenceRecord(
            record_id=str(uuid.uuid4()),
            event_type=event_type,
            action_id=action_id,
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
            expected_content = f"{record.record_id}|{record.event_type}|{record.action_id}|{record.binding_id}|{record.principal_id}|{record.payload_hash}|{record.timestamp}|{record.previous_record_hash or ''}"
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
                    "action_id": r.action_id,
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


def create_action_created_evidence(
    chain: GitHubCommentEvidenceChain,
    envelope: GitHubCommentActionEnvelope
) -> GitHubCommentEvidenceRecord:
    """Create evidence for action envelope creation."""
    payload = envelope.to_dict()
    return chain.append("action_created", envelope.action_id, envelope.binding_id, envelope.principal_id, payload)


def create_action_approved_evidence(
    chain: GitHubCommentEvidenceChain,
    envelope: GitHubCommentActionEnvelope,
    approval_hash: str
) -> GitHubCommentEvidenceRecord:
    """Create evidence for action approval."""
    payload = envelope.to_dict()
    payload["approval_hash"] = approval_hash
    return chain.append("action_approved", envelope.action_id, envelope.binding_id, envelope.principal_id, payload)


def create_execution_attempted_evidence(
    chain: GitHubCommentEvidenceChain,
    envelope: GitHubCommentActionEnvelope
) -> GitHubCommentEvidenceRecord:
    """Create evidence for execution attempt."""
    payload = {
        "action_id": envelope.action_id,
        "binding_id": envelope.binding_id,
        "repository": envelope.repository,
        "issue_number": envelope.issue_number,
        "comment_body_hash": envelope.comment_body_hash,
        "idempotency_key": envelope.idempotency_key
    }
    return chain.append("execution_attempted", envelope.action_id, envelope.binding_id, envelope.principal_id, payload)


def create_execution_completed_evidence(
    chain: GitHubCommentEvidenceChain,
    envelope: GitHubCommentActionEnvelope,
    execution_record: GitHubCommentExecutionRecord,
    receipt: MockGitHubCommentReceipt
) -> GitHubCommentEvidenceRecord:
    """Create evidence for successful execution."""
    payload = {
        "execution_id": execution_record.execution_id,
        "action_id": envelope.action_id,
        "binding_id": envelope.binding_id,
        "decision": execution_record.decision.value,
        "provider_receipt_hash": receipt.receipt_hash,
        "comment_id": receipt.comment_id,
        "comment_url": receipt.comment_url
    }
    return chain.append("execution_completed", envelope.action_id, envelope.binding_id, envelope.principal_id, payload)


def create_execution_blocked_evidence(
    chain: GitHubCommentEvidenceChain,
    envelope: GitHubCommentActionEnvelope,
    decision: 'ExecutionDecision',
    reason: str
) -> GitHubCommentEvidenceRecord:
    """Create evidence for blocked execution."""
    payload = {
        "action_id": envelope.action_id,
        "binding_id": envelope.binding_id,
        "decision": decision.value,
        "reason": reason
    }
    return chain.append("execution_blocked", envelope.action_id, envelope.binding_id, envelope.principal_id, payload)
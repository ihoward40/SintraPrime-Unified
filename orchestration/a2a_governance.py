"""Governance gates for agent-to-agent dispatch.

This module deliberately enforces the safe default: internal collaboration may
be sent without approval, while messages representing external actions require
an approval receipt, evidence references, and an unchanged content hash.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ClaimStatus(str, Enum):
    PROVEN = "PROVEN"
    USER_STATED = "USER-STATED"
    INFERRED = "INFERRED"
    UNVERIFIED = "UNVERIFIED"
    UNSUPPORTED = "UNSUPPORTED"
    RISKY = "RISKY"


@dataclass(frozen=True)
class ApprovalReceipt:
    approved_by: str
    approved_output_id: str
    recipient: str
    final_content_hash: str
    attachment_hashes: tuple[str, ...] = ()
    approved_at: float = field(default_factory=time.time)
    delivery_method: str = "agent-message"
    receipt_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    sender_agent_id: str = ""
    expires_at: float = 0.0
    signature: str = ""


@dataclass(frozen=True)
class EvidenceClaim:
    claim: str
    status: ClaimStatus
    source_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class DispatchAudit:
    mission_id: str
    objective: str
    agents_used: tuple[str, ...]
    sources_used: tuple[str, ...]
    claims_verified: tuple[str, ...]
    risks_flagged: tuple[str, ...]
    user_approval: str
    external_action_taken: bool
    final_output_hash: str
    status: str
    payload_hash: str = ""
    reason_code: str | None = None
    reason_detail: str | None = None
    timestamp: float = field(default_factory=time.time)
    audit_id: str = field(default_factory=lambda: uuid.uuid4().hex)


def content_hash(payload: dict[str, Any]) -> str:
    """Create a stable SHA-256 hash for the exact payload being dispatched."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _approval_secret() -> bytes:
    secret = os.getenv("A2A_APPROVAL_HMAC_SECRET")
    if not secret:
        raise PermissionError("Dispatch blocked: approval signing key is not configured")
    return secret.encode("utf-8")


def _approval_material(receipt: ApprovalReceipt) -> str:
    return json.dumps({
        "approved_by": receipt.approved_by,
        "approved_output_id": receipt.approved_output_id,
        "recipient": receipt.recipient,
        "final_content_hash": receipt.final_content_hash,
        "attachment_hashes": list(receipt.attachment_hashes),
        "approved_at": receipt.approved_at,
        "delivery_method": receipt.delivery_method,
        "receipt_id": receipt.receipt_id,
        "sender_agent_id": receipt.sender_agent_id,
        "expires_at": receipt.expires_at,
    }, sort_keys=True, separators=(",", ":"))


def issue_approval(
    *,
    approved_by: str,
    approved_output_id: str,
    sender_agent_id: str,
    recipient: str,
    final_content_hash: str,
    attachment_hashes: tuple[str, ...] = (),
    delivery_method: str = "agent-message",
    expires_at: float,
) -> ApprovalReceipt:
    """Issue a signed approval; callers cannot forge a valid receipt without the server key."""
    receipt = ApprovalReceipt(
        approved_by=approved_by,
        approved_output_id=approved_output_id,
        recipient=recipient,
        final_content_hash=final_content_hash,
        attachment_hashes=tuple(attachment_hashes),
        delivery_method=delivery_method,
        sender_agent_id=sender_agent_id,
        expires_at=expires_at,
    )
    signature = hmac.new(_approval_secret(), _approval_material(receipt).encode(), hashlib.sha256).hexdigest()
    return ApprovalReceipt(**{**asdict(receipt), "signature": signature})


def verify_approval(receipt: ApprovalReceipt, *, sender_agent_id: str) -> None:
    if not receipt.signature:
        raise PermissionError("Dispatch blocked: unsigned approval receipt")
    if not receipt.approved_by or not receipt.approved_output_id:
        raise PermissionError("Dispatch blocked: approval identity is incomplete")
    if not receipt.sender_agent_id or receipt.sender_agent_id != sender_agent_id:
        raise PermissionError("Dispatch blocked: approved sender does not match")
    if not receipt.delivery_method:
        raise PermissionError("Dispatch blocked: approval delivery method is required")
    if not receipt.expires_at or receipt.expires_at <= time.time():
        raise PermissionError("Dispatch blocked: approval receipt is expired")
    expected = hmac.new(_approval_secret(), _approval_material(receipt).encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, receipt.signature):
        raise PermissionError("Dispatch blocked: approval signature is invalid")


def validate_dispatch(
    *,
    payload: dict[str, Any],
    recipient: str,
    external_action: bool,
    sender_agent_id: str | None = None,
    approval: ApprovalReceipt | None = None,
    claims: list[EvidenceClaim] | None = None,
    attachment_hashes: list[str] | None = None,
) -> str:
    """Validate a dispatch and return the exact payload hash.

    Raises ``PermissionError`` or ``ValueError`` rather than silently degrading
    when a gate is missing. This function is intended to run immediately before
    queueing/sending a message.
    """
    output_hash = content_hash(payload)
    attachment_hashes = attachment_hashes or []
    claims = claims or []

    if any(claim.status in {ClaimStatus.UNSUPPORTED, ClaimStatus.RISKY} for claim in claims):
        raise PermissionError("Dispatch blocked: unsupported or risky claim requires review")

    if not external_action:
        return output_hash

    if approval is None:
        raise PermissionError("Dispatch blocked: user approval receipt required")
    if sender_agent_id is None:
        raise PermissionError("Dispatch blocked: sender identity is required")
    verify_approval(approval, sender_agent_id=sender_agent_id)
    if approval.recipient != recipient:
        raise PermissionError("Dispatch blocked: approved recipient does not match")
    if approval.final_content_hash != output_hash:
        raise PermissionError("Dispatch blocked: final content hash does not match approval")
    if tuple(attachment_hashes) != approval.attachment_hashes:
        raise PermissionError("Dispatch blocked: attachment hashes do not match approval")
    if not approval.approved_output_id:
        raise ValueError("Dispatch blocked: approved_output_id is required")

    return output_hash


def audit_dict(audit: DispatchAudit) -> dict[str, Any]:
    """Serialize an audit record for durable JSON/event storage."""
    return asdict(audit)

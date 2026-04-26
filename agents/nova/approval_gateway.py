"""Approval Gateway — Human-in-the-loop approval system for Nova actions.

Manages approval workflows for high-stakes actions, ensuring human oversight
before irreversible operations are executed.
"""

import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("approval_gateway")
logger.setLevel(logging.INFO)


class ApprovalStatus(str, Enum):
    """Status of an approval request."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"
    EXPIRED = "EXPIRED"
    AUTO_APPROVED = "AUTO_APPROVED"


class ApprovalTier(str, Enum):
    """Tiers of approval authority."""
    STANDARD = "STANDARD"
    SENIOR = "SENIOR"
    LEGAL = "LEGAL"
    EXECUTIVE = "EXECUTIVE"


@dataclass
class ApprovalRequest:
    """A request for human approval of an action."""
    request_id: str
    action_type: str
    action_description: str
    params: Dict[str, Any]
    requested_by: str
    tier: str = ApprovalTier.STANDARD.value
    status: str = ApprovalStatus.PENDING.value
    approver_id: Optional[str] = None
    rejection_reason: Optional[str] = None
    escalated_to: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# Actions that can be auto-approved
AUTO_APPROVE_ACTIONS = {
    "NOTIFY_CREDITOR",
    "SCHEDULE_COURT_DATE",
}

# Actions requiring legal review
LEGAL_REVIEW_ACTIONS = {
    "FILE_COURT_MOTION",
    "DRAFT_TRUST_AMENDMENT",
    "GENERATE_AFFIDAVIT",
}


class ApprovalGateway:
    """Human-in-the-loop approval system.

    Manages the lifecycle of approval requests: submission, review,
    approval/rejection, escalation, and auto-approval for low-risk actions.
    """

    def __init__(
        self,
        auto_approve_enabled: bool = True,
        notification_callback: Optional[Callable] = None,
        expiry_hours: int = 72,
    ):
        self.auto_approve_enabled = auto_approve_enabled
        self.notification_callback = notification_callback
        self.expiry_hours = expiry_hours
        self._requests: Dict[str, ApprovalRequest] = {}
        self._history: List[ApprovalRequest] = []
        logger.info("ApprovalGateway initialized — auto_approve=%s", auto_approve_enabled)

    def submit_for_approval(
        self,
        action: str,
        metadata: Dict[str, Any],
        requested_by: str = "system",
    ) -> ApprovalRequest:
        """Create an approval request for an action.

        Low-risk actions may be auto-approved if enabled.
        """
        request_id = str(uuid.uuid4())

        # Determine tier
        if action in LEGAL_REVIEW_ACTIONS:
            tier = ApprovalTier.LEGAL.value
        elif action in AUTO_APPROVE_ACTIONS:
            tier = ApprovalTier.STANDARD.value
        else:
            tier = ApprovalTier.SENIOR.value

        request = ApprovalRequest(
            request_id=request_id,
            action_type=action,
            action_description=metadata.get("description", f"Execute {action}"),
            params=metadata.get("params", {}),
            requested_by=requested_by,
            tier=tier,
            metadata=metadata,
        )

        # Auto-approve low-risk actions
        if self.auto_approve_enabled and action in AUTO_APPROVE_ACTIONS:
            return self.auto_approve(request)

        self._requests[request_id] = request
        self._notify(request, "new_request")
        logger.info("Approval request %s created for %s (tier: %s)",
                     request_id, action, tier)
        return request

    def approve(self, request_id: str, approver_id: str) -> ApprovalRequest:
        """Approve an action request.

        Args:
            request_id: The request to approve.
            approver_id: ID of the human approving.

        Returns:
            Updated ApprovalRequest.

        Raises:
            ValueError: If request not found or not in PENDING state.
        """
        request = self._get_request(request_id)
        if request.status != ApprovalStatus.PENDING.value:
            raise ValueError(
                f"Cannot approve request {request_id} — status is {request.status}"
            )

        request.status = ApprovalStatus.APPROVED.value
        request.approver_id = approver_id
        request.resolved_at = datetime.now(timezone.utc).isoformat()

        self._history.append(request)
        self._notify(request, "approved")
        logger.info("Request %s approved by %s", request_id, approver_id)
        return request

    def reject(self, request_id: str, reason: str, rejector_id: Optional[str] = None) -> ApprovalRequest:
        """Reject an action request.

        Args:
            request_id: The request to reject.
            reason: Reason for rejection.
            rejector_id: ID of the human rejecting.

        Returns:
            Updated ApprovalRequest.
        """
        request = self._get_request(request_id)
        if request.status != ApprovalStatus.PENDING.value:
            raise ValueError(
                f"Cannot reject request {request_id} — status is {request.status}"
            )

        request.status = ApprovalStatus.REJECTED.value
        request.rejection_reason = reason
        request.approver_id = rejector_id
        request.resolved_at = datetime.now(timezone.utc).isoformat()

        self._history.append(request)
        self._notify(request, "rejected")
        logger.info("Request %s rejected: %s", request_id, reason)
        return request

    def auto_approve(self, request: ApprovalRequest) -> ApprovalRequest:
        """Auto-approve a low-risk action."""
        request.status = ApprovalStatus.AUTO_APPROVED.value
        request.approver_id = "system/auto"
        request.resolved_at = datetime.now(timezone.utc).isoformat()

        self._requests[request.request_id] = request
        self._history.append(request)
        logger.info("Request %s auto-approved for %s", request.request_id, request.action_type)
        return request

    def escalate(self, request_id: str, escalate_to: Optional[str] = None) -> ApprovalRequest:
        """Escalate a request to a higher approval tier.

        Args:
            request_id: The request to escalate.
            escalate_to: Target approver or tier.
        """
        request = self._get_request(request_id)
        if request.status != ApprovalStatus.PENDING.value:
            raise ValueError(
                f"Cannot escalate request {request_id} — status is {request.status}"
            )

        # Determine escalation tier
        tier_order = [
            ApprovalTier.STANDARD.value,
            ApprovalTier.SENIOR.value,
            ApprovalTier.LEGAL.value,
            ApprovalTier.EXECUTIVE.value,
        ]
        current_idx = tier_order.index(request.tier) if request.tier in tier_order else 0
        next_tier = tier_order[min(current_idx + 1, len(tier_order) - 1)]

        request.status = ApprovalStatus.ESCALATED.value
        request.tier = next_tier
        request.escalated_to = escalate_to or next_tier
        # Reset to pending at new tier
        request.status = ApprovalStatus.PENDING.value

        self._notify(request, "escalated")
        logger.info("Request %s escalated to tier: %s", request_id, next_tier)
        return request

    def get_pending_requests(self, tier: Optional[str] = None) -> List[ApprovalRequest]:
        """Get all pending approval requests, optionally filtered by tier."""
        pending = [
            r for r in self._requests.values()
            if r.status == ApprovalStatus.PENDING.value
        ]
        if tier:
            pending = [r for r in pending if r.tier == tier]
        return pending

    def get_request_status(self, request_id: str) -> Dict[str, Any]:
        """Get the current status of an approval request."""
        request = self._get_request(request_id)
        return asdict(request)

    def get_history(
        self,
        action_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get approval history with optional filters."""
        results = self._history
        if action_type:
            results = [r for r in results if r.action_type == action_type]
        if status:
            results = [r for r in results if r.status == status]
        return [asdict(r) for r in results[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        """Return gateway statistics."""
        all_requests = list(self._requests.values())
        return {
            "total_requests": len(all_requests),
            "pending": sum(1 for r in all_requests if r.status == ApprovalStatus.PENDING.value),
            "approved": sum(1 for r in all_requests if r.status == ApprovalStatus.APPROVED.value),
            "rejected": sum(1 for r in all_requests if r.status == ApprovalStatus.REJECTED.value),
            "auto_approved": sum(1 for r in all_requests if r.status == ApprovalStatus.AUTO_APPROVED.value),
            "escalated": sum(1 for r in all_requests if r.status == ApprovalStatus.ESCALATED.value),
        }

    def _get_request(self, request_id: str) -> ApprovalRequest:
        """Retrieve a request or raise ValueError."""
        if request_id not in self._requests:
            raise ValueError(f"Approval request '{request_id}' not found.")
        return self._requests[request_id]

    def _notify(self, request: ApprovalRequest, event: str) -> None:
        """Send notification about an approval event."""
        if self.notification_callback:
            try:
                self.notification_callback({
                    "event": event,
                    "request_id": request.request_id,
                    "action_type": request.action_type,
                    "tier": request.tier,
                    "status": request.status,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            except Exception:
                logger.exception("Notification callback failed for request %s", request.request_id)

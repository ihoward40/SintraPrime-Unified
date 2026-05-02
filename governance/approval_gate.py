"""
approval_gate.py — Approval workflow engine (OpenAI Operator-inspired).

Implements human-in-the-loop approval gates that pause agent execution
until a human approves, rejects, or the request expires.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, List, Optional, Set

from governance.risk_types import (
    ActionRisk,
    ApprovalRequest,
    ApprovalStatus,
    RiskLevel,
)

logger = logging.getLogger(__name__)


class ApprovalGate:
    """
    Human-in-the-Loop approval gate.

    Inspired by OpenAI Operator's approval mechanism. When a high-risk
    action is initiated, the gate:
      1. Creates an ApprovalRequest
      2. Notifies designated approvers
      3. Pauses execution until approved/rejected/expired
      4. Returns the final status to the caller

    Usage::

        gate = ApprovalGate(base_url="https://app.sintraprime.com")
        request = gate.request_approval("send_payment", risk, {"amount": 5000})
        status = gate.wait_for_approval(request.id, timeout_seconds=300)
        if status == ApprovalStatus.APPROVED:
            proceed_with_payment()
    """

    DEFAULT_TIMEOUT_SECONDS = 300   # 5 minutes
    DEFAULT_EXPIRY_HOURS = 24       # Requests expire after 24 hours if not acted on

    def __init__(
        self,
        base_url: str = "https://app.sintraprime.com",
        notification_callback: Optional[Callable[[ApprovalRequest], None]] = None,
        auto_approve_threshold: Optional[RiskLevel] = RiskLevel.LOW,
    ) -> None:
        self._requests: Dict[str, ApprovalRequest] = {}
        self._auto_approve_actions: Set[str] = set()
        self._lock = threading.Lock()
        self.base_url = base_url
        self._notification_callback = notification_callback
        self.auto_approve_threshold = auto_approve_threshold

    # ------------------------------------------------------------------
    # Core workflow
    # ------------------------------------------------------------------

    def request_approval(
        self,
        action: str,
        risk: ActionRisk,
        context: Optional[Dict] = None,
        requestor: str = "agent",
        timeout_hours: float = DEFAULT_EXPIRY_HOURS,
    ) -> ApprovalRequest:
        """
        Create and register an approval request.

        If the action is in the auto-approve list or below the threshold,
        returns an AUTO_APPROVED request immediately.
        """
        context = context or {}
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=timeout_hours)

        req = ApprovalRequest(
            id=str(uuid.uuid4()),
            action=action,
            risk=risk,
            requestor=requestor,
            requested_at=now,
            expires_at=expires,
            status=ApprovalStatus.PENDING,
            context=context,
        )
        req.approval_link = self.create_approval_link(req.id)

        # Auto-approve if action is whitelisted or risk is below threshold
        if action in self._auto_approve_actions:
            req.status = ApprovalStatus.AUTO_APPROVED
            req.approved_at = now
            req.notes = "Auto-approved: action is in the trusted whitelist"
            logger.info("Auto-approved action '%s' (whitelist)", action)
        elif (
            self.auto_approve_threshold is not None
            and risk.risk_level <= self.auto_approve_threshold
        ):
            req.status = ApprovalStatus.AUTO_APPROVED
            req.approved_at = now
            req.notes = f"Auto-approved: risk level {risk.risk_level.value} is below threshold"
            logger.info("Auto-approved action '%s' (below threshold)", action)

        with self._lock:
            self._requests[req.id] = req

        if req.status == ApprovalStatus.PENDING and self._notification_callback:
            try:
                self._notification_callback(req)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Notification callback failed: %s", exc)

        logger.info(
            "Approval request %s created for action '%s' (status=%s)",
            req.id, action, req.status.value
        )
        return req

    def approve(
        self,
        request_id: str,
        approver_id: str,
        notes: str = "",
    ) -> bool:
        """
        Approve a pending request.

        Returns True on success, False if not found or already decided.
        """
        with self._lock:
            req = self._requests.get(request_id)
            if not req or req.status != ApprovalStatus.PENDING:
                logger.warning("Cannot approve request %s (status=%s)",
                               request_id, req.status.value if req else "NOT_FOUND")
                return False
            if req.is_expired:
                req.status = ApprovalStatus.EXPIRED
                logger.info("Request %s expired", request_id)
                return False

            req.status = ApprovalStatus.APPROVED
            req.approver = approver_id
            req.approved_at = datetime.now(timezone.utc)
            req.notes = notes

        logger.info("Request %s APPROVED by %s", request_id, approver_id)
        return True

    def reject(
        self,
        request_id: str,
        approver_id: str,
        reason: str,
    ) -> bool:
        """
        Reject a pending request.

        Returns True on success, False if not found or already decided.
        """
        with self._lock:
            req = self._requests.get(request_id)
            if not req or req.status != ApprovalStatus.PENDING:
                return False

            req.status = ApprovalStatus.REJECTED
            req.approver = approver_id
            req.approved_at = datetime.now(timezone.utc)
            req.notes = reason

        logger.info("Request %s REJECTED by %s: %s", request_id, approver_id, reason)
        return True

    def is_approved(self, request_id: str) -> ApprovalStatus:
        """Return the current status of a request."""
        with self._lock:
            req = self._requests.get(request_id)
        if not req:
            return ApprovalStatus.EXPIRED
        if req.status == ApprovalStatus.PENDING and req.is_expired:
            with self._lock:
                req.status = ApprovalStatus.EXPIRED
        return req.status

    def wait_for_approval(
        self,
        request_id: str,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        poll_interval: float = 1.0,
    ) -> ApprovalStatus:
        """
        Block until the request is decided or timeout is reached.

        Args:
            request_id: The ApprovalRequest ID.
            timeout_seconds: Maximum wait time in seconds.
            poll_interval: Polling frequency in seconds.

        Returns:
            Final ApprovalStatus.
        """
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            status = self.is_approved(request_id)
            if status != ApprovalStatus.PENDING:
                return status
            time.sleep(poll_interval)

        # Expired
        with self._lock:
            req = self._requests.get(request_id)
            if req and req.status == ApprovalStatus.PENDING:
                req.status = ApprovalStatus.EXPIRED
        logger.info("Request %s expired after waiting %ss", request_id, timeout_seconds)
        return ApprovalStatus.EXPIRED

    async def wait_for_approval_async(
        self,
        request_id: str,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        poll_interval: float = 1.0,
    ) -> ApprovalStatus:
        """Async variant of wait_for_approval."""
        deadline = asyncio.get_event_loop().time() + timeout_seconds
        while asyncio.get_event_loop().time() < deadline:
            status = self.is_approved(request_id)
            if status != ApprovalStatus.PENDING:
                return status
            await asyncio.sleep(poll_interval)

        with self._lock:
            req = self._requests.get(request_id)
            if req and req.status == ApprovalStatus.PENDING:
                req.status = ApprovalStatus.EXPIRED
        return ApprovalStatus.EXPIRED

    # ------------------------------------------------------------------
    # Management
    # ------------------------------------------------------------------

    def auto_approve(self, action_type: str) -> None:
        """Whitelist an action type for automatic approval (trusted context)."""
        self._auto_approve_actions.add(action_type)
        logger.info("Action '%s' added to auto-approve whitelist", action_type)

    def remove_auto_approve(self, action_type: str) -> None:
        """Remove an action from the auto-approve whitelist."""
        self._auto_approve_actions.discard(action_type)

    def get_pending(self) -> List[ApprovalRequest]:
        """Return all currently pending approval requests."""
        self.expire_old_requests()
        with self._lock:
            return [r for r in self._requests.values() if r.status == ApprovalStatus.PENDING]

    def get_all(self) -> List[ApprovalRequest]:
        """Return all approval requests (all statuses)."""
        with self._lock:
            return list(self._requests.values())

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Retrieve a specific request by ID."""
        with self._lock:
            return self._requests.get(request_id)

    def expire_old_requests(self) -> int:
        """
        Check all PENDING requests and mark expired ones.

        Returns the number of requests that were expired.
        """
        expired_count = 0
        with self._lock:
            for req in self._requests.values():
                if req.status == ApprovalStatus.PENDING and req.is_expired:
                    req.status = ApprovalStatus.EXPIRED
                    expired_count += 1
        if expired_count:
            logger.info("Expired %d stale approval requests", expired_count)
        return expired_count

    def create_approval_link(self, request_id: str) -> str:
        """
        Generate a one-click approve/reject URL for email notifications.

        The URL is handled by the governance API router.
        """
        return f"{self.base_url}/governance/review/{request_id}"

    def stats(self) -> Dict[str, int]:
        """Return summary statistics for all requests."""
        with self._lock:
            requests = list(self._requests.values())
        return {
            "total": len(requests),
            "pending": sum(1 for r in requests if r.status == ApprovalStatus.PENDING),
            "approved": sum(1 for r in requests if r.status == ApprovalStatus.APPROVED),
            "rejected": sum(1 for r in requests if r.status == ApprovalStatus.REJECTED),
            "expired": sum(1 for r in requests if r.status == ApprovalStatus.EXPIRED),
            "auto_approved": sum(1 for r in requests if r.status == ApprovalStatus.AUTO_APPROVED),
        }

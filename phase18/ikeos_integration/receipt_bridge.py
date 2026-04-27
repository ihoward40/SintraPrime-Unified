"""
phase18/ikeos_integration/receipt_bridge.py
============================================
IkeOS ToolGateway Receipt Pattern bridge for SintraPrime agents.

Architecture
------------
Every tool call made by a SintraPrime agent (Chat, Zero, Sigma, Nova) is
routed through this bridge:

    Agent  →  ToolGatewayClient.submit()  →  IkeOS /tool-requests  →  Receipt
    Agent  ←  ToolGatewayClient.poll()   ←  IkeOS /receipts/{id}   ←  Result

The bridge is intentionally HTTP-transport-agnostic: the ``http_post`` and
``http_get`` callables are injected at construction time so that tests can
swap them for mocks without any network activity.

Policy risk levels (mirroring IkeOS PolicyEngine)
--------------------------------------------------
    R0 – read-only / safe
    R1 – low-risk write
    R2 – medium-risk, requires audit
    R3 – high-risk, requires human-in-the-loop approval

Security
--------
Every outbound request carries an ``X-Api-Key`` header sourced from the
``SecurityLayer`` (phase18/security/security_hardening.py).
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------

class RiskLevel(str, Enum):
    R0 = "R0"  # read-only / safe
    R1 = "R1"  # low-risk write
    R2 = "R2"  # medium-risk, requires audit
    R3 = "R3"  # high-risk, requires human approval


class ReceiptStatus(str, Enum):
    PENDING    = "pending"
    QUEUED     = "queued"
    PROCESSING = "processing"
    COMPLETED  = "completed"
    FAILED     = "failed"
    REJECTED   = "rejected"


@dataclass
class ToolRequest:
    """Mirrors the IkeOS ToolRequest schema."""
    tool_name: str
    payload: Dict[str, Any]
    risk_level: RiskLevel = RiskLevel.R0
    agent_id: str = ""
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "payload": self.payload,
            "risk_level": self.risk_level.value,
            "agent_id": self.agent_id,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
        }


@dataclass
class Receipt:
    """Mirrors the IkeOS Receipt schema."""
    receipt_id: str
    status: ReceiptStatus
    tool_name: str
    agent_id: str
    correlation_id: str
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Receipt":
        return cls(
            receipt_id=data["receipt_id"],
            status=ReceiptStatus(data.get("status", "pending")),
            tool_name=data.get("tool_name", ""),
            agent_id=data.get("agent_id", ""),
            correlation_id=data.get("correlation_id", ""),
            result=data.get("result"),
            error=data.get("error"),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            audit_trail=data.get("audit_trail", []),
        )

    def is_terminal(self) -> bool:
        return self.status in (
            ReceiptStatus.COMPLETED,
            ReceiptStatus.FAILED,
            ReceiptStatus.REJECTED,
        )


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------

class AuditTrail:
    """In-memory audit trail for all tool requests in this process."""

    def __init__(self) -> None:
        self._entries: List[Dict[str, Any]] = []

    def record(
        self,
        event: str,
        receipt_id: str,
        agent_id: str,
        tool_name: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        entry = {
            "event": event,
            "receipt_id": receipt_id,
            "agent_id": agent_id,
            "tool_name": tool_name,
            "timestamp": time.time(),
        }
        if extra:
            entry.update(extra)
        self._entries.append(entry)

    def entries_for(self, receipt_id: str) -> List[Dict[str, Any]]:
        return [e for e in self._entries if e["receipt_id"] == receipt_id]

    def all_entries(self) -> List[Dict[str, Any]]:
        return list(self._entries)

    def clear(self) -> None:
        self._entries.clear()


# ---------------------------------------------------------------------------
# ToolGateway HTTP client
# ---------------------------------------------------------------------------

class GatewayError(Exception):
    """Raised when the IkeOS gateway returns a non-2xx response."""


class ToolGatewayClient:
    """
    Thin Python client for the IkeOS Fastify ToolGateway.

    Parameters
    ----------
    base_url:
        Base URL of the running IkeOS gateway, e.g. ``http://localhost:3000``.
    api_key:
        API key sent in the ``X-Api-Key`` header.
    http_post:
        Callable ``(url, headers, body_dict) -> (status_code, response_dict)``.
        Defaults to a ``requests``-based implementation; swap for a mock in tests.
    http_get:
        Callable ``(url, headers) -> (status_code, response_dict)``.
    poll_interval_s:
        Seconds to wait between polling attempts (default 0.5).
    max_poll_attempts:
        Maximum number of polling attempts before raising ``TimeoutError``
        (default 20).
    audit_trail:
        Optional shared ``AuditTrail`` instance; a new one is created if not
        provided.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:3000",
        api_key: str = "",
        http_post: Optional[Callable] = None,
        http_get: Optional[Callable] = None,
        poll_interval_s: float = 0.5,
        max_poll_attempts: int = 20,
        audit_trail: Optional[AuditTrail] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._http_post = http_post or self._default_post
        self._http_get = http_get or self._default_get
        self.poll_interval_s = poll_interval_s
        self.max_poll_attempts = max_poll_attempts
        self.audit = audit_trail or AuditTrail()

    # ------------------------------------------------------------------
    # Default HTTP implementations (real network; replaced in tests)
    # ------------------------------------------------------------------

    def _default_post(
        self, url: str, headers: Dict[str, str], body: Dict[str, Any]
    ) -> Tuple[int, Dict[str, Any]]:
        try:
            import requests  # type: ignore
            resp = requests.post(url, json=body, headers=headers, timeout=10)
            return resp.status_code, resp.json()
        except Exception as exc:
            raise GatewayError(f"POST {url} failed: {exc}") from exc

    def _default_get(
        self, url: str, headers: Dict[str, str]
    ) -> Tuple[int, Dict[str, Any]]:
        try:
            import requests  # type: ignore
            resp = requests.get(url, headers=headers, timeout=10)
            return resp.status_code, resp.json()
        except Exception as exc:
            raise GatewayError(f"GET {url} failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Api-Key": self.api_key,
        }

    def submit(self, request: ToolRequest) -> Receipt:
        """
        POST a ToolRequest to ``/tool-requests`` and return the initial Receipt.

        Raises
        ------
        GatewayError
            If the gateway returns a non-2xx status code.
        """
        url = f"{self.base_url}/tool-requests"
        status_code, body = self._http_post(url, self._headers(), request.to_dict())
        if status_code not in (200, 201, 202):
            raise GatewayError(
                f"Gateway rejected request: HTTP {status_code} — {body}"
            )
        receipt = Receipt.from_dict(body)
        self.audit.record(
            "submitted",
            receipt.receipt_id,
            request.agent_id,
            request.tool_name,
            {"risk_level": request.risk_level.value},
        )
        return receipt

    def get_receipt(self, receipt_id: str) -> Receipt:
        """
        GET ``/receipts/{receipt_id}`` and return the current Receipt state.
        """
        url = f"{self.base_url}/receipts/{receipt_id}"
        status_code, body = self._http_get(url, self._headers())
        if status_code == 404:
            raise GatewayError(f"Receipt not found: {receipt_id}")
        if status_code != 200:
            raise GatewayError(
                f"Failed to fetch receipt {receipt_id}: HTTP {status_code}"
            )
        return Receipt.from_dict(body)

    def wait_for_result(
        self,
        receipt_id: str,
        sleep_fn: Optional[Callable[[float], None]] = None,
    ) -> Receipt:
        """
        Poll ``/receipts/{receipt_id}`` until the receipt reaches a terminal
        state (completed / failed / rejected) or ``max_poll_attempts`` is
        exceeded.

        Parameters
        ----------
        receipt_id:
            The receipt ID returned by ``submit()``.
        sleep_fn:
            Callable used for sleeping between polls.  Defaults to
            ``time.sleep``; inject a no-op in tests to avoid delays.

        Raises
        ------
        TimeoutError
            If the receipt is still non-terminal after ``max_poll_attempts``.
        """
        _sleep = sleep_fn or time.sleep
        for attempt in range(self.max_poll_attempts):
            receipt = self.get_receipt(receipt_id)
            self.audit.record(
                "polled",
                receipt_id,
                receipt.agent_id,
                receipt.tool_name,
                {"attempt": attempt, "status": receipt.status.value},
            )
            if receipt.is_terminal():
                return receipt
            _sleep(self.poll_interval_s)
        raise TimeoutError(
            f"Receipt {receipt_id} did not complete after "
            f"{self.max_poll_attempts} attempts."
        )

    def submit_and_wait(
        self,
        request: ToolRequest,
        sleep_fn: Optional[Callable[[float], None]] = None,
    ) -> Receipt:
        """Convenience: submit + poll until terminal."""
        receipt = self.submit(request)
        return self.wait_for_result(receipt.receipt_id, sleep_fn=sleep_fn)


# ---------------------------------------------------------------------------
# Risk-level policy mapper
# ---------------------------------------------------------------------------

# Default mapping from SintraPrime tool names to IkeOS risk levels
_DEFAULT_RISK_MAP: Dict[str, RiskLevel] = {
    # Read-only / safe
    "search_case_law":      RiskLevel.R0,
    "get_client_profile":   RiskLevel.R0,
    "list_documents":       RiskLevel.R0,
    "fetch_contract":       RiskLevel.R0,
    # Low-risk writes
    "create_draft":         RiskLevel.R1,
    "update_notes":         RiskLevel.R1,
    "send_email_draft":     RiskLevel.R1,
    "schedule_reminder":    RiskLevel.R1,
    # Medium-risk
    "send_email":           RiskLevel.R2,
    "create_invoice":       RiskLevel.R2,
    "update_contract":      RiskLevel.R2,
    "upload_document":      RiskLevel.R2,
    # High-risk (human-in-the-loop)
    "sign_contract":        RiskLevel.R3,
    "delete_client":        RiskLevel.R3,
    "process_payment":      RiskLevel.R3,
    "bulk_delete":          RiskLevel.R3,
}


class PolicyMapper:
    """Maps SintraPrime tool names to IkeOS risk levels."""

    def __init__(
        self, risk_map: Optional[Dict[str, RiskLevel]] = None
    ) -> None:
        self._map: Dict[str, RiskLevel] = dict(_DEFAULT_RISK_MAP)
        if risk_map:
            self._map.update(risk_map)

    def risk_for(self, tool_name: str) -> RiskLevel:
        """Return the risk level for a tool, defaulting to R1 if unknown."""
        return self._map.get(tool_name, RiskLevel.R1)

    def register(self, tool_name: str, risk_level: RiskLevel) -> None:
        self._map[tool_name] = risk_level

    def all_mappings(self) -> Dict[str, RiskLevel]:
        return dict(self._map)


# ---------------------------------------------------------------------------
# Agent wrapper
# ---------------------------------------------------------------------------

class AgentToolGatewayWrapper:
    """
    Wraps a SintraPrime agent so that every ``execute_tool`` call is routed
    through the IkeOS ToolGateway and produces a Receipt + audit trail.

    Parameters
    ----------
    agent_id:
        Unique identifier for this agent instance (e.g. ``"zero-1"``).
    gateway:
        A configured ``ToolGatewayClient``.
    policy_mapper:
        Maps tool names to risk levels.
    r3_approver:
        Optional callable invoked for R3 requests before submission.
        Signature: ``(request: ToolRequest) -> bool``.
        Return ``True`` to allow, ``False`` to reject.
    sleep_fn:
        Injected sleep function (no-op in tests).
    """

    def __init__(
        self,
        agent_id: str,
        gateway: ToolGatewayClient,
        policy_mapper: Optional[PolicyMapper] = None,
        r3_approver: Optional[Callable[[ToolRequest], bool]] = None,
        sleep_fn: Optional[Callable[[float], None]] = None,
    ) -> None:
        self.agent_id = agent_id
        self.gateway = gateway
        self.policy_mapper = policy_mapper or PolicyMapper()
        self.r3_approver = r3_approver
        self._sleep_fn = sleep_fn or time.sleep

    def execute_tool(
        self,
        tool_name: str,
        payload: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Receipt:
        """
        Execute a tool via the IkeOS ToolGateway.

        1. Determine risk level via PolicyMapper.
        2. For R3 requests, invoke the approver; reject if not approved.
        3. Submit ToolRequest to the gateway.
        4. Poll until terminal.
        5. Return the final Receipt.
        """
        risk = self.policy_mapper.risk_for(tool_name)
        request = ToolRequest(
            tool_name=tool_name,
            payload=payload,
            risk_level=risk,
            agent_id=self.agent_id,
            metadata=metadata or {},
        )

        # Human-in-the-loop gate for R3
        if risk == RiskLevel.R3:
            if self.r3_approver is None or not self.r3_approver(request):
                rejected_receipt = Receipt(
                    receipt_id=str(uuid.uuid4()),
                    status=ReceiptStatus.REJECTED,
                    tool_name=tool_name,
                    agent_id=self.agent_id,
                    correlation_id=request.correlation_id,
                    error="R3 action rejected: no approver or approval denied",
                )
                self.gateway.audit.record(
                    "r3_rejected",
                    rejected_receipt.receipt_id,
                    self.agent_id,
                    tool_name,
                )
                return rejected_receipt

        return self.gateway.submit_and_wait(request, sleep_fn=self._sleep_fn)

    def execute_tool_async(
        self,
        tool_name: str,
        payload: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Receipt:
        """
        Submit a tool request and return the initial Receipt immediately
        (non-blocking).  The caller is responsible for polling via
        ``gateway.wait_for_result(receipt.receipt_id)``.
        """
        risk = self.policy_mapper.risk_for(tool_name)
        request = ToolRequest(
            tool_name=tool_name,
            payload=payload,
            risk_level=risk,
            agent_id=self.agent_id,
            metadata=metadata or {},
        )
        return self.gateway.submit(request)


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def make_zero_wrapper(
    gateway: ToolGatewayClient,
    extra_risk_map: Optional[Dict[str, RiskLevel]] = None,
    **kwargs: Any,
) -> AgentToolGatewayWrapper:
    """Return an ``AgentToolGatewayWrapper`` pre-configured for the Zero agent."""
    pm = PolicyMapper(extra_risk_map)
    return AgentToolGatewayWrapper("zero", gateway, pm, **kwargs)


def make_sigma_wrapper(
    gateway: ToolGatewayClient,
    extra_risk_map: Optional[Dict[str, RiskLevel]] = None,
    **kwargs: Any,
) -> AgentToolGatewayWrapper:
    """Return an ``AgentToolGatewayWrapper`` pre-configured for the Sigma agent."""
    pm = PolicyMapper(extra_risk_map)
    return AgentToolGatewayWrapper("sigma", gateway, pm, **kwargs)


def make_nova_wrapper(
    gateway: ToolGatewayClient,
    extra_risk_map: Optional[Dict[str, RiskLevel]] = None,
    **kwargs: Any,
) -> AgentToolGatewayWrapper:
    """Return an ``AgentToolGatewayWrapper`` pre-configured for the Nova agent."""
    pm = PolicyMapper(extra_risk_map)
    return AgentToolGatewayWrapper("nova", gateway, pm, **kwargs)


def make_chat_wrapper(
    gateway: ToolGatewayClient,
    extra_risk_map: Optional[Dict[str, RiskLevel]] = None,
    **kwargs: Any,
) -> AgentToolGatewayWrapper:
    """Return an ``AgentToolGatewayWrapper`` pre-configured for the Chat agent."""
    pm = PolicyMapper(extra_risk_map)
    return AgentToolGatewayWrapper("chat", gateway, pm, **kwargs)

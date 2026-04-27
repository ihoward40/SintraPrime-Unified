"""
Tests for phase18/ikeos_integration/receipt_bridge.py
======================================================
All HTTP calls are mocked; no network activity required.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock, patch

import pytest

from phase18.ikeos_integration.receipt_bridge import (
    AgentToolGatewayWrapper,
    AuditTrail,
    GatewayError,
    PolicyMapper,
    Receipt,
    ReceiptStatus,
    RiskLevel,
    ToolGatewayClient,
    ToolRequest,
    make_chat_wrapper,
    make_nova_wrapper,
    make_sigma_wrapper,
    make_zero_wrapper,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_receipt_dict(
    receipt_id: str = "rcpt-001",
    status: str = "pending",
    tool_name: str = "search_case_law",
    agent_id: str = "zero",
) -> Dict[str, Any]:
    return {
        "receipt_id": receipt_id,
        "status": status,
        "tool_name": tool_name,
        "agent_id": agent_id,
        "correlation_id": str(uuid.uuid4()),
        "result": None,
        "error": None,
        "created_at": time.time(),
        "updated_at": time.time(),
        "audit_trail": [],
    }


def _make_completed_receipt_dict(**kwargs) -> Dict[str, Any]:
    d = _make_receipt_dict(**kwargs)
    d["status"] = "completed"
    d["result"] = {"data": "case_result"}
    return d


def _make_failed_receipt_dict(**kwargs) -> Dict[str, Any]:
    d = _make_receipt_dict(**kwargs)
    d["status"] = "failed"
    d["error"] = "Worker timeout"
    return d


def _instant_sleep(seconds: float) -> None:
    """No-op sleep for tests."""


def _make_gateway(
    post_responses: Optional[List[Tuple[int, Dict]]] = None,
    get_responses: Optional[List[Tuple[int, Dict]]] = None,
) -> ToolGatewayClient:
    """Build a ToolGatewayClient with pre-canned HTTP responses."""
    post_iter = iter(post_responses or [])
    get_iter = iter(get_responses or [])

    def mock_post(url, headers, body):
        return next(post_iter)

    def mock_get(url, headers):
        return next(get_iter)

    return ToolGatewayClient(
        base_url="http://test-gateway",
        api_key="test-key",
        http_post=mock_post,
        http_get=mock_get,
        poll_interval_s=0,
        max_poll_attempts=5,
    )


# ---------------------------------------------------------------------------
# ToolRequest tests
# ---------------------------------------------------------------------------

class TestToolRequest:
    def test_to_dict_contains_all_fields(self):
        req = ToolRequest(
            tool_name="search_case_law",
            payload={"query": "contract breach"},
            risk_level=RiskLevel.R0,
            agent_id="zero",
        )
        d = req.to_dict()
        assert d["tool_name"] == "search_case_law"
        assert d["payload"] == {"query": "contract breach"}
        assert d["risk_level"] == "R0"
        assert d["agent_id"] == "zero"
        assert "correlation_id" in d

    def test_correlation_id_is_unique(self):
        r1 = ToolRequest("t", {})
        r2 = ToolRequest("t", {})
        assert r1.correlation_id != r2.correlation_id

    def test_default_risk_level_is_r0(self):
        req = ToolRequest("t", {})
        assert req.risk_level == RiskLevel.R0

    def test_metadata_included_in_dict(self):
        req = ToolRequest("t", {}, metadata={"session": "abc"})
        assert req.to_dict()["metadata"]["session"] == "abc"


# ---------------------------------------------------------------------------
# Receipt tests
# ---------------------------------------------------------------------------

class TestReceipt:
    def test_from_dict_round_trip(self):
        d = _make_receipt_dict(receipt_id="r1", status="completed")
        r = Receipt.from_dict(d)
        assert r.receipt_id == "r1"
        assert r.status == ReceiptStatus.COMPLETED

    def test_is_terminal_completed(self):
        r = Receipt.from_dict(_make_completed_receipt_dict())
        assert r.is_terminal() is True

    def test_is_terminal_failed(self):
        r = Receipt.from_dict(_make_failed_receipt_dict())
        assert r.is_terminal() is True

    def test_is_terminal_rejected(self):
        d = _make_receipt_dict(status="rejected")
        r = Receipt.from_dict(d)
        assert r.is_terminal() is True

    def test_is_not_terminal_pending(self):
        r = Receipt.from_dict(_make_receipt_dict(status="pending"))
        assert r.is_terminal() is False

    def test_is_not_terminal_queued(self):
        r = Receipt.from_dict(_make_receipt_dict(status="queued"))
        assert r.is_terminal() is False

    def test_is_not_terminal_processing(self):
        r = Receipt.from_dict(_make_receipt_dict(status="processing"))
        assert r.is_terminal() is False

    def test_result_preserved(self):
        d = _make_completed_receipt_dict()
        d["result"] = {"answer": 42}
        r = Receipt.from_dict(d)
        assert r.result["answer"] == 42

    def test_error_preserved(self):
        d = _make_failed_receipt_dict()
        r = Receipt.from_dict(d)
        assert "timeout" in r.error.lower()


# ---------------------------------------------------------------------------
# AuditTrail tests
# ---------------------------------------------------------------------------

class TestAuditTrail:
    def test_record_and_retrieve(self):
        at = AuditTrail()
        at.record("submitted", "r1", "zero", "search_case_law")
        entries = at.entries_for("r1")
        assert len(entries) == 1
        assert entries[0]["event"] == "submitted"

    def test_entries_for_filters_by_receipt(self):
        at = AuditTrail()
        at.record("submitted", "r1", "zero", "t1")
        at.record("submitted", "r2", "sigma", "t2")
        assert len(at.entries_for("r1")) == 1
        assert len(at.entries_for("r2")) == 1

    def test_all_entries(self):
        at = AuditTrail()
        at.record("e1", "r1", "a", "t")
        at.record("e2", "r2", "b", "t")
        assert len(at.all_entries()) == 2

    def test_clear(self):
        at = AuditTrail()
        at.record("e", "r", "a", "t")
        at.clear()
        assert len(at.all_entries()) == 0

    def test_extra_fields_stored(self):
        at = AuditTrail()
        at.record("polled", "r1", "zero", "t", {"attempt": 3})
        assert at.entries_for("r1")[0]["attempt"] == 3

    def test_timestamp_recorded(self):
        at = AuditTrail()
        before = time.time()
        at.record("e", "r", "a", "t")
        after = time.time()
        ts = at.entries_for("r")[0]["timestamp"]
        assert before <= ts <= after


# ---------------------------------------------------------------------------
# ToolGatewayClient tests
# ---------------------------------------------------------------------------

class TestToolGatewayClientSubmit:
    def test_submit_returns_receipt(self):
        gw = _make_gateway(
            post_responses=[(201, _make_receipt_dict(receipt_id="r99"))],
        )
        req = ToolRequest("search_case_law", {"q": "test"}, agent_id="zero")
        receipt = gw.submit(req)
        assert receipt.receipt_id == "r99"
        assert receipt.status == ReceiptStatus.PENDING

    def test_submit_records_audit(self):
        gw = _make_gateway(
            post_responses=[(201, _make_receipt_dict(receipt_id="r1"))],
        )
        req = ToolRequest("search_case_law", {}, agent_id="zero")
        gw.submit(req)
        entries = gw.audit.entries_for("r1")
        assert any(e["event"] == "submitted" for e in entries)

    def test_submit_raises_on_4xx(self):
        gw = _make_gateway(
            post_responses=[(400, {"error": "bad request"})],
        )
        req = ToolRequest("t", {})
        with pytest.raises(GatewayError, match="400"):
            gw.submit(req)

    def test_submit_raises_on_5xx(self):
        gw = _make_gateway(
            post_responses=[(500, {"error": "server error"})],
        )
        req = ToolRequest("t", {})
        with pytest.raises(GatewayError, match="500"):
            gw.submit(req)

    def test_submit_accepts_200(self):
        gw = _make_gateway(
            post_responses=[(200, _make_receipt_dict())],
        )
        receipt = gw.submit(ToolRequest("t", {}))
        assert receipt is not None

    def test_submit_accepts_202(self):
        gw = _make_gateway(
            post_responses=[(202, _make_receipt_dict())],
        )
        receipt = gw.submit(ToolRequest("t", {}))
        assert receipt is not None

    def test_api_key_in_headers(self):
        captured_headers = {}

        def mock_post(url, headers, body):
            captured_headers.update(headers)
            return 201, _make_receipt_dict()

        gw = ToolGatewayClient(
            base_url="http://gw",
            api_key="secret-key",
            http_post=mock_post,
        )
        gw.submit(ToolRequest("t", {}))
        assert captured_headers.get("X-Api-Key") == "secret-key"


class TestToolGatewayClientGetReceipt:
    def test_get_receipt_returns_receipt(self):
        gw = _make_gateway(
            get_responses=[(200, _make_completed_receipt_dict(receipt_id="r5"))],
        )
        receipt = gw.get_receipt("r5")
        assert receipt.receipt_id == "r5"
        assert receipt.status == ReceiptStatus.COMPLETED

    def test_get_receipt_raises_on_404(self):
        gw = _make_gateway(
            get_responses=[(404, {"error": "not found"})],
        )
        with pytest.raises(GatewayError, match="not found"):
            gw.get_receipt("missing")

    def test_get_receipt_raises_on_500(self):
        gw = _make_gateway(
            get_responses=[(500, {})],
        )
        with pytest.raises(GatewayError):
            gw.get_receipt("r1")


class TestToolGatewayClientWaitForResult:
    def test_wait_returns_on_first_completed(self):
        gw = _make_gateway(
            get_responses=[(200, _make_completed_receipt_dict(receipt_id="r1"))],
        )
        receipt = gw.wait_for_result("r1", sleep_fn=_instant_sleep)
        assert receipt.status == ReceiptStatus.COMPLETED

    def test_wait_polls_until_completed(self):
        responses = [
            (200, _make_receipt_dict(status="pending")),
            (200, _make_receipt_dict(status="queued")),
            (200, _make_receipt_dict(status="processing")),
            (200, _make_completed_receipt_dict()),
        ]
        gw = _make_gateway(get_responses=responses)
        receipt = gw.wait_for_result("r1", sleep_fn=_instant_sleep)
        assert receipt.status == ReceiptStatus.COMPLETED

    def test_wait_raises_timeout(self):
        gw = _make_gateway(
            get_responses=[(200, _make_receipt_dict(status="pending"))] * 10,
        )
        gw.max_poll_attempts = 3
        with pytest.raises(TimeoutError):
            gw.wait_for_result("r1", sleep_fn=_instant_sleep)

    def test_wait_records_poll_audit(self):
        gw = _make_gateway(
            get_responses=[(200, _make_completed_receipt_dict(receipt_id="r1"))],
        )
        gw.wait_for_result("r1", sleep_fn=_instant_sleep)
        entries = gw.audit.entries_for("r1")
        assert any(e["event"] == "polled" for e in entries)

    def test_wait_returns_failed_receipt(self):
        gw = _make_gateway(
            get_responses=[(200, _make_failed_receipt_dict(receipt_id="r1"))],
        )
        receipt = gw.wait_for_result("r1", sleep_fn=_instant_sleep)
        assert receipt.status == ReceiptStatus.FAILED


class TestSubmitAndWait:
    def test_submit_and_wait_end_to_end(self):
        gw = _make_gateway(
            post_responses=[(201, _make_receipt_dict(receipt_id="r1"))],
            get_responses=[(200, _make_completed_receipt_dict(receipt_id="r1"))],
        )
        req = ToolRequest("search_case_law", {}, agent_id="zero")
        receipt = gw.submit_and_wait(req, sleep_fn=_instant_sleep)
        assert receipt.status == ReceiptStatus.COMPLETED


# ---------------------------------------------------------------------------
# PolicyMapper tests
# ---------------------------------------------------------------------------

class TestPolicyMapper:
    def test_known_r0_tool(self):
        pm = PolicyMapper()
        assert pm.risk_for("search_case_law") == RiskLevel.R0

    def test_known_r1_tool(self):
        pm = PolicyMapper()
        assert pm.risk_for("create_draft") == RiskLevel.R1

    def test_known_r2_tool(self):
        pm = PolicyMapper()
        assert pm.risk_for("send_email") == RiskLevel.R2

    def test_known_r3_tool(self):
        pm = PolicyMapper()
        assert pm.risk_for("sign_contract") == RiskLevel.R3

    def test_unknown_tool_defaults_to_r1(self):
        pm = PolicyMapper()
        assert pm.risk_for("unknown_tool_xyz") == RiskLevel.R1

    def test_register_custom_tool(self):
        pm = PolicyMapper()
        pm.register("custom_tool", RiskLevel.R2)
        assert pm.risk_for("custom_tool") == RiskLevel.R2

    def test_override_existing_tool(self):
        pm = PolicyMapper()
        pm.register("search_case_law", RiskLevel.R2)
        assert pm.risk_for("search_case_law") == RiskLevel.R2

    def test_extra_risk_map_in_constructor(self):
        pm = PolicyMapper({"my_tool": RiskLevel.R3})
        assert pm.risk_for("my_tool") == RiskLevel.R3

    def test_all_mappings_returns_dict(self):
        pm = PolicyMapper()
        mappings = pm.all_mappings()
        assert isinstance(mappings, dict)
        assert len(mappings) >= 12


# ---------------------------------------------------------------------------
# AgentToolGatewayWrapper tests
# ---------------------------------------------------------------------------

class TestAgentWrapper:
    def _make_wrapper(
        self,
        post_responses=None,
        get_responses=None,
        agent_id="zero",
        r3_approver=None,
    ) -> AgentToolGatewayWrapper:
        gw = _make_gateway(
            post_responses=post_responses or [(201, _make_receipt_dict())],
            get_responses=get_responses or [(200, _make_completed_receipt_dict())],
        )
        return AgentToolGatewayWrapper(
            agent_id=agent_id,
            gateway=gw,
            r3_approver=r3_approver,
            sleep_fn=_instant_sleep,
        )

    def test_execute_tool_returns_receipt(self):
        wrapper = self._make_wrapper()
        receipt = wrapper.execute_tool("search_case_law", {"q": "test"})
        assert receipt.status == ReceiptStatus.COMPLETED

    def test_execute_tool_r3_rejected_without_approver(self):
        wrapper = self._make_wrapper(r3_approver=None)
        receipt = wrapper.execute_tool("sign_contract", {"doc": "x"})
        assert receipt.status == ReceiptStatus.REJECTED
        assert "R3" in receipt.error

    def test_execute_tool_r3_rejected_by_approver(self):
        wrapper = self._make_wrapper(r3_approver=lambda req: False)
        receipt = wrapper.execute_tool("sign_contract", {"doc": "x"})
        assert receipt.status == ReceiptStatus.REJECTED

    def test_execute_tool_r3_approved(self):
        wrapper = self._make_wrapper(r3_approver=lambda req: True)
        receipt = wrapper.execute_tool("sign_contract", {"doc": "x"})
        assert receipt.status == ReceiptStatus.COMPLETED

    def test_execute_tool_r3_audit_recorded_on_rejection(self):
        wrapper = self._make_wrapper(r3_approver=None)
        receipt = wrapper.execute_tool("sign_contract", {})
        entries = wrapper.gateway.audit.all_entries()
        assert any(e["event"] == "r3_rejected" for e in entries)

    def test_execute_tool_async_returns_initial_receipt(self):
        gw = _make_gateway(
            post_responses=[(201, _make_receipt_dict(receipt_id="async-1"))],
        )
        wrapper = AgentToolGatewayWrapper("zero", gw, sleep_fn=_instant_sleep)
        receipt = wrapper.execute_tool_async("search_case_law", {})
        assert receipt.receipt_id == "async-1"
        assert receipt.status == ReceiptStatus.PENDING

    def test_agent_id_propagated(self):
        captured_body = {}

        def mock_post(url, headers, body):
            captured_body.update(body)
            return 201, _make_receipt_dict()

        gw = ToolGatewayClient(
            base_url="http://gw",
            api_key="k",
            http_post=mock_post,
            http_get=lambda u, h: (200, _make_completed_receipt_dict()),
            poll_interval_s=0,
        )
        wrapper = AgentToolGatewayWrapper("sigma-007", gw, sleep_fn=_instant_sleep)
        wrapper.execute_tool("search_case_law", {})
        assert captured_body["agent_id"] == "sigma-007"

    def test_metadata_propagated(self):
        captured_body = {}

        def mock_post(url, headers, body):
            captured_body.update(body)
            return 201, _make_receipt_dict()

        gw = ToolGatewayClient(
            base_url="http://gw",
            api_key="k",
            http_post=mock_post,
            http_get=lambda u, h: (200, _make_completed_receipt_dict()),
            poll_interval_s=0,
        )
        wrapper = AgentToolGatewayWrapper("zero", gw, sleep_fn=_instant_sleep)
        wrapper.execute_tool("search_case_law", {}, metadata={"session": "s1"})
        assert captured_body["metadata"]["session"] == "s1"


# ---------------------------------------------------------------------------
# Factory function tests
# ---------------------------------------------------------------------------

class TestFactories:
    def _simple_gw(self) -> ToolGatewayClient:
        return _make_gateway(
            post_responses=[(201, _make_receipt_dict())],
            get_responses=[(200, _make_completed_receipt_dict())],
        )

    def test_make_zero_wrapper(self):
        w = make_zero_wrapper(self._simple_gw(), sleep_fn=_instant_sleep)
        assert w.agent_id == "zero"

    def test_make_sigma_wrapper(self):
        w = make_sigma_wrapper(self._simple_gw(), sleep_fn=_instant_sleep)
        assert w.agent_id == "sigma"

    def test_make_nova_wrapper(self):
        w = make_nova_wrapper(self._simple_gw(), sleep_fn=_instant_sleep)
        assert w.agent_id == "nova"

    def test_make_chat_wrapper(self):
        w = make_chat_wrapper(self._simple_gw(), sleep_fn=_instant_sleep)
        assert w.agent_id == "chat"

    def test_factory_accepts_extra_risk_map(self):
        w = make_zero_wrapper(
            self._simple_gw(),
            extra_risk_map={"custom_tool": RiskLevel.R3},
            sleep_fn=_instant_sleep,
        )
        assert w.policy_mapper.risk_for("custom_tool") == RiskLevel.R3

    def test_factory_wrapper_executes_tool(self):
        w = make_zero_wrapper(self._simple_gw(), sleep_fn=_instant_sleep)
        receipt = w.execute_tool("search_case_law", {"q": "test"})
        assert receipt.status == ReceiptStatus.COMPLETED


# ---------------------------------------------------------------------------
# Risk level enum tests
# ---------------------------------------------------------------------------

class TestRiskLevel:
    def test_r0_value(self):
        assert RiskLevel.R0.value == "R0"

    def test_r3_value(self):
        assert RiskLevel.R3.value == "R3"

    def test_all_levels_present(self):
        levels = {r.value for r in RiskLevel}
        assert levels == {"R0", "R1", "R2", "R3"}


# ---------------------------------------------------------------------------
# ReceiptStatus enum tests
# ---------------------------------------------------------------------------

class TestReceiptStatus:
    def test_all_statuses(self):
        statuses = {s.value for s in ReceiptStatus}
        assert "pending" in statuses
        assert "completed" in statuses
        assert "failed" in statuses
        assert "rejected" in statuses

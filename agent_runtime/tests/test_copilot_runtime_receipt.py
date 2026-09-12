from __future__ import annotations

import pytest

from agent_runtime.receipts import AgentRuntimeReceipt, RuntimeOutcome


def _receipt(**overrides):
    base = {
        "agent_id": "agent.copilot.engineering.01",
        "agent_version": "1.0.0",
        "mission_id": "M-1",
        "result": RuntimeOutcome.COMPLETED,
        "task_id": "T-1",
        "work_order_id": "WO-1",
        "actor_id": "copilot.engineering.01",
        "files_read": ("a",),
        "files_written": ("b",),
        "implementer": "copilot.engineering.01",
        "reviewer": "qa.agent.01",
        "certifier": "governance.certifier.01",
    }
    base.update(overrides)
    return AgentRuntimeReceipt(**base)


def test_structured_handoff_fields_present():
    r = _receipt()
    assert r.task_id == "T-1"
    assert r.work_order_id == "WO-1"
    assert r.files_written == ("b",)


def test_self_certification_blocked():
    with pytest.raises(ValueError, match="SOLE_CERTIFIER"):
        _receipt(certifier="copilot.engineering.01", reviewer="")

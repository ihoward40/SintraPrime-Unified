from __future__ import annotations

import pytest
from fastapi import HTTPException

from orchestration.orchestration_api import StartWorkflowRequest, start_workflow


class _EngineStub:
    async def start_workflow(self, workflow_type, input_data, workflow_id=None, metadata=None):
        return workflow_id or "wf-test-1"


@pytest.mark.asyncio
async def test_generic_start_route_disabled_by_default(monkeypatch):
    monkeypatch.delenv("SINTRAPRIME_ENABLE_GENERIC_WORKFLOW_START", raising=False)

    with pytest.raises(HTTPException) as exc_info:
        await start_workflow(
            StartWorkflowRequest(workflow_type="wf", input_data={"a": 1}),
            engine=_EngineStub(),
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "GENERIC_WORKFLOW_START_DISABLED_USE_DURABLE_ORCHESTRATION_AUTHORITY"


@pytest.mark.asyncio
async def test_generic_start_route_enabled_with_explicit_env(monkeypatch):
    monkeypatch.setenv("SINTRAPRIME_ENABLE_GENERIC_WORKFLOW_START", "true")

    response = await start_workflow(
        StartWorkflowRequest(workflow_type="wf", input_data={"a": 1}, workflow_id="wf-explicit"),
        engine=_EngineStub(),
    )

    assert response.workflow_id == "wf-explicit"
    assert response.workflow_type == "wf"
    assert response.status == "running"

import asyncio

import pytest

from agent_commons.events import AgentCommonsEventBus
from agent_commons.provider_adapters import CallableAgentAdapter, ProviderPolicy


@pytest.mark.asyncio
async def test_event_bus_isolates_tenants():
    bus = AgentCommonsEventBus()
    tenant_a = bus.subscribe("tenant-a").__aiter__()
    tenant_b = bus.subscribe("tenant-b").__aiter__()

    await bus.publish("tenant-a", {"type": "run.updated", "data": {"run_id": "a"}})

    event = await asyncio.wait_for(tenant_a.__anext__(), timeout=0.2)
    assert event["tenant_id"] == "tenant-a"
    assert event["data"]["run_id"] == "a"

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(tenant_b.__anext__(), timeout=0.05)


@pytest.mark.asyncio
async def test_callable_adapter_invokes_provider_and_streams_observable_events():
    async def provider(task, context):
        return {"summary": task["objective"], "context_task": context["task_id"]}

    adapter = CallableAgentAdapter(
        "worker",
        ["build"],
        provider,
        ProviderPolicy(timeout_seconds=1.0, max_output_characters=1_000),
    )

    invocation = await adapter.invoke({"objective": "build"}, {"task_id": "T-1"})
    assert invocation.output == {"summary": "build", "context_task": "T-1"}

    events = [event async for event in adapter.stream_events(invocation.run_id)]
    assert [event["type"] for event in events] == ["started", "completed", "closed"]


@pytest.mark.asyncio
async def test_callable_adapter_enforces_timeout():
    async def slow_provider(task, context):
        await asyncio.sleep(0.1)
        return {"summary": "late"}

    adapter = CallableAgentAdapter(
        "slow",
        ["build"],
        slow_provider,
        ProviderPolicy(timeout_seconds=0.01),
    )

    with pytest.raises(asyncio.TimeoutError):
        await adapter.invoke({"objective": "wait"}, {"task_id": "T-2"})

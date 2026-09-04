from __future__ import annotations

from uuid import UUID

import pytest
from pydantic import ValidationError

from portal.services.jarvis_principal_mission import (
    EXTERNAL_SIDE_EFFECTS,
    JARVIS_AUTHORITY,
    JARVIS_WORKFLOW_TYPE,
    DecisionContext,
    InMemoryPrincipalMissionRequestStore,
    JarvisReadOnlyCapability,
    PrincipalMissionRequestInput,
    deterministic_request_hash,
    persist_principal_mission_request,
)


def _input() -> PrincipalMissionRequestInput:
    return PrincipalMissionRequestInput(
        objective="Review SintraPrime-Unified and identify what requires attention.",
        decision_context=DecisionContext(
            objective="Review repository",
            constraints=("read_only", "no_external_side_effects"),
            priorities=("security", "correctness"),
        ),
    )


@pytest.mark.asyncio
async def test_request_persists_separately_and_is_server_bound() -> None:
    store = InMemoryPrincipalMissionRequestStore()
    request = await persist_principal_mission_request(
        store, tenant_id="tenant-1", requested_by="principal-1", input_data=_input()
    )
    assert isinstance(request.request_id, UUID)
    assert await store.get(request.request_id) == request
    assert request.workflow_type == JARVIS_WORKFLOW_TYPE
    assert request.authority == JARVIS_AUTHORITY
    assert request.workflow_type != "client_selected_workflow"


def test_request_hash_is_deterministic() -> None:
    first = deterministic_request_hash(
        tenant_id="tenant-1", requested_by="principal-1", input_data=_input()
    )
    second = deterministic_request_hash(
        tenant_id="tenant-1", requested_by="principal-1", input_data=_input()
    )
    assert first == second
    assert len(first) == 64


def test_decision_context_is_typed_and_bounded() -> None:
    context = _input().decision_context
    assert isinstance(context, DecisionContext)
    assert "read_only" in context.constraints
    with pytest.raises(ValidationError):
        DecisionContext(objective="x", unexpected="client_authority")


def test_client_cannot_escalate_authority_or_workflow() -> None:
    with pytest.raises(ValidationError):
        PrincipalMissionRequestInput(
            objective="review",
            decision_context=DecisionContext(objective="review"),
            workflow_type="admin_workflow",
        )


@pytest.mark.asyncio
async def test_server_owned_capability_is_read_only() -> None:
    capability = JarvisReadOnlyCapability()
    assert capability.external_side_effects == EXTERNAL_SIDE_EFFECTS == 0
    store = InMemoryPrincipalMissionRequestStore()
    request = await persist_principal_mission_request(
        store, tenant_id="tenant-1", requested_by="principal-1", input_data=_input()
    )
    assert await capability.read(store, request.request_id) == request
    with pytest.raises(PermissionError, match="MUTATION_DENIED"):
        capability.mutate("send_email")
    with pytest.raises(PermissionError, match="EXECUTION_DENIED"):
        capability.execute("browser_write")

"""Principal-activation denial and legacy-route mounting regression guards.

Static route guard covers the canonical portal app; a separate deployment
entry-point inventory remains required before production certification.
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from portal.main import create_app
from portal.services.mission_control_approval_service import (
    NotPrincipalError,
    consume_approval_and_activate,
)


@pytest.mark.asyncio
async def test_nonprincipal_cannot_activate_even_with_existing_approval():
    db = SimpleNamespace()
    actor = SimpleNamespace(user_id="nonprincipal-user")
    with patch(
        "portal.services.mission_control_approval_service.is_tenant_principal",
        new_callable=AsyncMock,
        return_value=False,
    ) as principal_check:
        with pytest.raises(NotPrincipalError, match="NOT_TENANT_PRINCIPAL"):
            await consume_approval_and_activate(
                db, run_id="run-1", tenant_id="tenant-1",
                actor=actor, authority=SimpleNamespace(),
            )
        principal_check.assert_awaited_once_with(
            db, authenticated_user_id="nonprincipal-user", tenant_id="tenant-1",
        )


def test_legacy_unguarded_router_not_mounted_in_canonical_portal():
    app = create_app()
    registered = {getattr(route, "path", "") for route in app.routes}
    assert "/orchestration/workflows/start" not in registered
    assert "/orchestration/agents/message" not in registered
    assert "/orchestration/workflows/langgraph/run" not in registered
    assert "/api/orchestration/plan" in registered
    assert "/api/orchestration/execute" in registered

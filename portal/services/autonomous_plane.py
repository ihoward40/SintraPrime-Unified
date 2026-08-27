import asyncio
import logging
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from .cancellation_bus import CancellationScope, CancellationSignal, bus
from .parliament_scaling import scaling_service

logger = logging.getLogger(__name__)


class OrchestrationState(StrEnum):
    IDLE = "IDLE"
    ORCHESTRATING = "ORCHESTRATING"
    CROSS_TENANT_SYNC = "CROSS_TENANT_SYNC"
    BALANCING = "BALANCING"


class AutonomousExecutionPlane:
    """Manage cross-tenant orchestration and parliament-driven intelligence."""

    def __init__(self):
        self.plane_id = str(uuid.uuid4())
        self.state = OrchestrationState.IDLE
        self.active_orchestrations: dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def coordinate_cross_tenant_intent(
        self,
        intents: list[dict[str, Any]],
        shared_context_id: str,
    ) -> str:
        """Coordinate tenant-isolated intents under a shared context."""
        async with self._lock:
            self.state = OrchestrationState.CROSS_TENANT_SYNC
            orchestration_id = str(uuid.uuid4())

            logger.info(
                "[AUTONOMOUS_PLANE] Initializing cross-tenant orchestration: %s",
                orchestration_id,
            )

            self.active_orchestrations[orchestration_id] = {
                "shared_context_id": shared_context_id,
                "tenants": list({intent["tenant_id"] for intent in intents}),
                "intents": [intent["idempotency_key"] for intent in intents],
                "status": "INITIALIZING",
                "started_at": datetime.now(UTC),
            }

            total_load = len(intents)
            await scaling_service.scale_up(
                "ORCHESTRATOR",
                "SYSTEM",
                count=max(1, total_load // 10),
            )

            self.active_orchestrations[orchestration_id]["status"] = "RUNNING"
            self.state = OrchestrationState.ORCHESTRATING
            return orchestration_id

    async def global_emergency_stop(self, reason: str, principal_id: str):
        """Trigger a platform-wide emergency stop across all tenants."""
        logger.warning(
            "[AUTONOMOUS_PLANE] GLOBAL EMERGENCY STOP TRIGGERED BY %s: %s",
            principal_id,
            reason,
        )

        signal = CancellationSignal(
            scope=CancellationScope.PLATFORM,
            target_id="GLOBAL",
            reason=reason,
            principal_id=principal_id,
        )
        await bus.publish(signal)

        status = scaling_service.get_parliament_status()
        for agent_type, count in status["agent_types"].items():
            if agent_type != "SECURITY_GUARD":
                logger.info(
                    "[AUTONOMOUS_PLANE] Signaled scale-down for %s %s instances",
                    count,
                    agent_type,
                )

    def get_plane_status(self) -> dict[str, Any]:
        """Return the current status of the autonomous execution plane."""
        return {
            "plane_id": self.plane_id,
            "state": self.state,
            "active_orchestrations_count": len(self.active_orchestrations),
            "parliament_status": scaling_service.get_parliament_status(),
        }


autonomous_plane = AutonomousExecutionPlane()

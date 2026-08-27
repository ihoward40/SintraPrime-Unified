import asyncio
import logging
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from .cancellation_bus import CancellationScope, CancellationSignal, bus

logger = logging.getLogger(__name__)


class HealthStatus(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    RECOVERING = "RECOVERING"


class AutonomousRecoveryService:
    """Monitor system health and trigger recovery protocols for failed agents."""

    def __init__(self):
        self.system_health = HealthStatus.HEALTHY
        self.failure_registry: dict[str, Any] = {}
        self.recovery_count = 0

    async def report_agent_failure(
        self,
        agent_id: str,
        error_type: str,
        context: dict[str, Any],
    ):
        """Register an agent failure and initiate recovery."""
        logger.error("[AUTONOMOUS_RECOVERY] Agent %s failed: %s", agent_id, error_type)
        self.failure_registry[agent_id] = {
            "timestamp": datetime.now(UTC),
            "error": error_type,
            "context": context,
            "status": "FAILED",
        }
        await self.initiate_recovery(agent_id)

    async def initiate_recovery(self, agent_id: str):
        """Trigger the recovery protocol for a specific agent."""
        logger.info("[AUTONOMOUS_RECOVERY] Initiating recovery for %s...", agent_id)

        signal = CancellationSignal(
            scope=CancellationScope.EXECUTION,
            target_id=agent_id,
            reason="Autonomous Recovery Isolation",
            principal_id="SYSTEM-RECOVERY",
        )
        await bus.publish(signal)

        await asyncio.sleep(1)
        self.recovery_count += 1

        if agent_id in self.failure_registry:
            self.failure_registry[agent_id]["status"] = "RECOVERED"
            self.failure_registry[agent_id]["recovered_at"] = datetime.now(UTC)

        logger.info(
            "[AUTONOMOUS_RECOVERY] Recovery complete for %s. Total recoveries: %s",
            agent_id,
            self.recovery_count,
        )

    def get_recovery_metrics(self) -> dict[str, Any]:
        """Return metrics for the recovery service."""
        return {
            "system_health": self.system_health,
            "total_recoveries": self.recovery_count,
            "active_failures": len(
                [
                    failure
                    for failure in self.failure_registry.values()
                    if failure["status"] == "FAILED"
                ]
            ),
        }


autonomous_recovery = AutonomousRecoveryService()

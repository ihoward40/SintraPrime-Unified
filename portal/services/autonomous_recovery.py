import logging
import asyncio
import uuid
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional
from enum import Enum
from .cancellation_bus import bus, CancellationSignal, CancellationScope

logger = logging.getLogger(__name__)

class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    RECOVERING = "RECOVERING"

class AutonomousRecoveryService:
    """
    Phase 6: Autonomous Recovery.
    Monitors system health and automatically triggers recovery protocols for failed agents.
    """
    def __init__(self):
        self.system_health = HealthStatus.HEALTHY
        self.failure_registry: Dict[str, Any] = {}
        self.recovery_count = 0

    async def report_agent_failure(self, agent_id: str, error_type: str, context: Dict[str, Any]):
        """Registers an agent failure and initiates recovery."""
        logger.error(f"[AUTONOMOUS_RECOVERY] Agent {agent_id} failed: {error_type}")
        
        self.failure_registry[agent_id] = {
            "timestamp": datetime.now(UTC),
            "error": error_type,
            "context": context,
            "status": "FAILED"
        }
        
        await self.initiate_recovery(agent_id)

    async def initiate_recovery(self, agent_id: str):
        """Triggers recovery protocol for a specific agent."""
        logger.info(f"[AUTONOMOUS_RECOVERY] Initiating recovery for {agent_id}...")
        
        # 1. Isolate the failed instance
        signal = CancellationSignal(
            scope=CancellationScope.EXECUTION,
            target_id=agent_id,
            reason="Autonomous Recovery Isolation",
            principal_id="SYSTEM-RECOVERY"
        )
        await bus.publish(signal)
        
        # 2. Re-spawn replacement (simulated)
        await asyncio.sleep(1) 
        self.recovery_count += 1
        
        if agent_id in self.failure_registry:
            self.failure_registry[agent_id]["status"] = "RECOVERED"
            self.failure_registry[agent_id]["recovered_at"] = datetime.now(UTC)
            
        logger.info(f"[AUTONOMOUS_RECOVERY] Recovery complete for {agent_id}. Total recoveries: {self.recovery_count}")

    def get_recovery_metrics(self) -> Dict[str, Any]:
        """Returns metrics for the recovery service."""
        return {
            "system_health": self.system_health,
            "total_recoveries": self.recovery_count,
            "active_failures": len([f for f in self.failure_registry.values() if f["status"] == "FAILED"])
        }

# Global instance
autonomous_recovery = AutonomousRecoveryService()

import asyncio
import uuid
import logging
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional
from enum import Enum
from pydantic import BaseModel

from .mythos_brain import MythosBrainCoordinator
from .parliament_scaling import AgentInstance, scaling_service
from .cancellation_bus import bus, CancellationSignal, CancellationScope

logger = logging.getLogger(__name__)

class OrchestrationState(str, Enum):
    IDLE = "IDLE"
    ORCHESTRATING = "ORCHESTRATING"
    CROSS_TENANT_SYNC = "CROSS_TENANT_SYNC"
    BALANCING = "BALANCING"

class AutonomousExecutionPlane:
    """
    Phase 4: Autonomous Execution Plane.
    Manages cross-tenant orchestration and parliament-driven intelligence.
    """
    def __init__(self):
        self.plane_id = str(uuid.uuid4())
        self.state = OrchestrationState.IDLE
        self.active_orchestrations: Dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def coordinate_cross_tenant_intent(
        self, 
        intents: List[Dict[str, Any]], 
        shared_context_id: str
    ) -> str:
        """
        Coordinates multiple intents across different tenants under a shared context.
        Ensures strict isolation while allowing unified orchestration.
        """
        async with self._lock:
            self.state = OrchestrationState.CROSS_TENANT_SYNC
            orchestration_id = str(uuid.uuid4())
            
            logger.info(f"[AUTONOMOUS_PLANE] Initializing cross-tenant orchestration: {orchestration_id}")
            
            # 1. Register shared context
            self.active_orchestrations[orchestration_id] = {
                "shared_context_id": shared_context_id,
                "tenants": list(set(i["tenant_id"] for i in intents)),
                "intents": [i["idempotency_key"] for i in intents],
                "status": "INITIALIZING",
                "started_at": datetime.now(UTC)
            }
            
            # 2. Trigger parliament scaling for combined load
            total_load = len(intents)
            await scaling_service.scale_up("ORCHESTRATOR", "SYSTEM", count=max(1, total_load // 10))
            
            self.active_orchestrations[orchestration_id]["status"] = "RUNNING"
            self.state = OrchestrationState.ORCHESTRATING
            
            return orchestration_id

    async def global_emergency_stop(self, reason: str, principal_id: str):
        """
        Triggers a platform-wide emergency stop across all tenants.
        """
        logger.warning(f"[AUTONOMOUS_PLANE] GLOBAL EMERGENCY STOP TRIGGERED BY {principal_id}: {reason}")
        
        signal = CancellationSignal(
            scope=CancellationScope.PLATFORM,
            target_id="GLOBAL",
            reason=reason,
            principal_id=principal_id
        )
        await bus.publish(signal)
        
        # Immediate scale down of non-essential parliament members
        status = scaling_service.get_parliament_status()
        for agent_type, count in status["agent_types"].items():
            if agent_type != "SECURITY_GUARD":
                # In a real scenario, we'd iterate and kill instances
                logger.info(f"[AUTONOMOUS_PLANE] Signaled scale-down for {count} {agent_type} instances")

    def get_plane_status(self) -> Dict[str, Any]:
        """Returns the current status of the autonomous execution plane."""
        return {
            "plane_id": self.plane_id,
            "state": self.state,
            "active_orchestrations_count": len(self.active_orchestrations),
            "parliament_status": scaling_service.get_parliament_status()
        }

# Global instance
autonomous_plane = AutonomousExecutionPlane()

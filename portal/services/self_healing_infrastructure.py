import logging
from typing import Any, Dict, List

from .autonomous_recovery import autonomous_recovery
from .predictive_scaling import predictive_scaling

logger = logging.getLogger(__name__)

class SelfHealingInfrastructure:
    """
    Phase 6: Self-Healing Infrastructure.
    Integrates predictive scaling and autonomous recovery into a unified management layer.
    """
    def __init__(self):
        self.scaling = predictive_scaling
        self.recovery = autonomous_recovery

    async def get_infrastructure_health(self) -> Dict[str, Any]:
        """Aggregates health and performance metrics across the infrastructure."""
        recovery_metrics = self.recovery.get_recovery_metrics()

        return {
            "status": recovery_metrics["system_health"],
            "predictive_metrics": {
                "history_depth": len(self.scaling.load_history),
                "prediction_window": f"{self.scaling.prediction_window_minutes}m"
            },
            "recovery_metrics": recovery_metrics
        }

# Global instance
self_healing = SelfHealingInfrastructure()

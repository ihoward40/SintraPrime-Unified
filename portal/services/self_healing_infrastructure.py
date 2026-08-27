from typing import Any

from .autonomous_recovery import autonomous_recovery
from .predictive_scaling import predictive_scaling


class SelfHealingInfrastructure:
    """Combine predictive scaling and autonomous recovery health state."""

    def __init__(self):
        self.scaling = predictive_scaling
        self.recovery = autonomous_recovery

    async def get_infrastructure_health(self) -> dict[str, Any]:
        """Aggregate health and performance metrics across the infrastructure."""
        recovery_metrics = self.recovery.get_recovery_metrics()
        return {
            "status": recovery_metrics["system_health"],
            "predictive_metrics": {
                "history_depth": len(self.scaling.load_history),
                "prediction_window": f"{self.scaling.prediction_window_minutes}m",
            },
            "recovery_metrics": recovery_metrics,
        }


self_healing = SelfHealingInfrastructure()

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from .parliament_scaling import scaling_service

logger = logging.getLogger(__name__)

class PredictiveScalingService:
    """
    Phase 6: Predictive Scaling.
    Uses historical load patterns and intent velocity to anticipate scaling needs.
    """
    def __init__(self):
        self.load_history: List[Dict[str, Any]] = []
        self.prediction_window_minutes = 15
        self._lock = asyncio.Lock()

    async def record_load_metric(self, current_load: float, instance_count: int):
        """Records a load metric for trend analysis."""
        async with self._lock:
            self.load_history.append({
                "timestamp": datetime.now(UTC),
                "load": current_load,
                "instances": instance_count
            })
            # Keep only last 2 hours of history
            cutoff = datetime.now(UTC) - timedelta(hours=2)
            self.load_history = [m for m in self.load_history if m["timestamp"] > cutoff]

    async def predict_scaling_need(self) -> int:
        """
        Analyzes trends to predict the required instance count for the next window.
        Returns the suggested instance count.
        """
        if len(self.load_history) < 5:
            return 0 # Not enough data for prediction

        # Simple linear trend analysis
        recent = self.load_history[-5:]
        loads = [m["load"] for m in recent]

        # Calculate velocity (load change per metric)
        velocity = (loads[-1] - loads[0]) / len(loads)

        if velocity > 0.05: # Load is increasing rapidly (>5% per interval)
            current_instances = recent[-1]["instances"]
            predicted_increase = int(current_instances * 0.2) # Anticipate 20% growth
            logger.info(f"[PREDICTIVE_SCALING] High load velocity detected ({velocity:.2%}). Predicting +{predicted_increase} instances.")
            return predicted_increase

        return 0

    async def run_predictive_cycle(self):
        """Main loop for predictive scaling adjustments."""
        while True:
            status = scaling_service.get_parliament_status()
            await self.record_load_metric(status["system_load"], status["total_instances"])

            adjustment = await self.predict_scaling_need()
            if adjustment > 0:
                await scaling_service.scale_up("PREDICTIVE_WORKER", "SYSTEM", count=adjustment)

            await asyncio.sleep(60) # Run every minute

# Global instance
predictive_scaling = PredictiveScalingService()

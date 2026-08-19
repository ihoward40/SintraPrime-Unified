import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from .parliament_scaling import scaling_service

logger = logging.getLogger(__name__)


class PredictiveScalingService:
    """Use recent load patterns and intent velocity to anticipate scaling needs."""

    def __init__(self):
        self.load_history: list[dict[str, Any]] = []
        self.prediction_window_minutes = 15
        self._lock = asyncio.Lock()

    async def record_load_metric(self, current_load: float, instance_count: int):
        """Record a load metric for trend analysis."""
        async with self._lock:
            self.load_history.append(
                {
                    "timestamp": datetime.now(UTC),
                    "load": current_load,
                    "instances": instance_count,
                }
            )
            cutoff = datetime.now(UTC) - timedelta(hours=2)
            self.load_history = [
                metric for metric in self.load_history if metric["timestamp"] > cutoff
            ]

    async def predict_scaling_need(self) -> int:
        """Return the suggested instance increase for the next prediction window."""
        if len(self.load_history) < 5:
            return 0

        recent = self.load_history[-5:]
        loads = [metric["load"] for metric in recent]
        velocity = (loads[-1] - loads[0]) / len(loads)

        if velocity > 0.05:
            current_instances = recent[-1]["instances"]
            predicted_increase = int(current_instances * 0.2)
            logger.info(
                "[PREDICTIVE_SCALING] High load velocity detected (%0.2f%%). Predicting +%s instances.",
                velocity * 100,
                predicted_increase,
            )
            return predicted_increase

        return 0

    async def run_predictive_cycle(self):
        """Run the predictive scaling adjustment loop."""
        while True:
            status = scaling_service.get_parliament_status()
            await self.record_load_metric(
                status["system_load"],
                status["total_instances"],
            )

            adjustment = await self.predict_scaling_need()
            if adjustment > 0:
                await scaling_service.scale_up(
                    "PREDICTIVE_WORKER",
                    "SYSTEM",
                    count=adjustment,
                )

            await asyncio.sleep(60)


predictive_scaling = PredictiveScalingService()

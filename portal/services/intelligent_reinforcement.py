import logging
from typing import Any

from .marl_layer import marl_layer
from .vlm_adapter import VisualReasoningRequest, vlm_adapter

logger = logging.getLogger(__name__)


class IntelligentReinforcementService:
    """Integrate MARL and VLM capabilities into the SintraPrime core."""

    def __init__(self):
        self.marl = marl_layer
        self.vlm = vlm_adapter

    async def reinforce_execution(self, execution_id: str, feedback_score: float):
        """Reinforce the execution policy based on feedback."""
        logger.info(
            "[INTELLIGENT_REINFORCEMENT] Reinforcing execution %s with score %s",
            execution_id,
            feedback_score,
        )
        self.marl.distribute_reward(feedback_score)

    async def provide_visual_guidance(
        self,
        image_data: dict[str, Any],
        prompt: str,
        tenant_id: str,
    ):
        """Provide visual guidance to an agent using VLM."""
        request = VisualReasoningRequest(
            image_url=image_data.get("url"),
            local_path=image_data.get("path"),
            prompt=prompt,
            tenant_id=tenant_id,
        )
        return await self.vlm.analyze_visual_context(request)


intelligent_reinforcement = IntelligentReinforcementService()

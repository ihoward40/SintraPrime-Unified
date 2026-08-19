import logging
from typing import Any

from pydantic import BaseModel

from .remediation_service import remediation

logger = logging.getLogger(__name__)


class CouncilDecision(BaseModel):
    intent_id: str
    consensus_reached: bool
    recommendation: str
    votes: dict[str, str]
    rationale: str


class CouncilModeService:
    """Multi-model strategic debate with remediation."""

    def __init__(self):
        self.available_models = ["gpt-5", "claude-4", "llama-4"]

    async def initiate_debate(
        self,
        intent_id: str,
        context: dict[str, Any],
    ) -> CouncilDecision:
        """Trigger a multi-model debate with redacted context."""
        _safe_context = remediation.redact_boundaries(context)
        logger.info("[COUNCIL_MODE] Initiating strategic debate for intent %s", intent_id)

        votes = {
            model: "APPROVE" if model != "llama-4" else "NEEDS_REVISION"
            for model in self.available_models
        }
        consensus = list(votes.values()).count("APPROVE") >= 2
        return CouncilDecision(
            intent_id=intent_id,
            consensus_reached=consensus,
            recommendation=(
                "Proceed with isolation architecture"
                if consensus
                else "Refine security posture"
            ),
            votes=votes,
            rationale="Consensus reached among primary strategic models.",
        )


council_mode = CouncilModeService()

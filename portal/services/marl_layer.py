import logging
from enum import StrEnum

logger = logging.getLogger(__name__)


class AgentPolicy(StrEnum):
    COOPERATIVE = "COOPERATIVE"
    COMPETITIVE = "COMPETITIVE"
    EXPLORATORY = "EXPLORATORY"


class MARLLayer:
    """Coordinate learning and policy optimization across the Agent Parliament."""

    def __init__(self):
        self.active_policies: dict[str, AgentPolicy] = {}
        self.global_reward_signal: float = 0.0

    def register_agent(
        self,
        agent_id: str,
        initial_policy: AgentPolicy = AgentPolicy.COOPERATIVE,
    ):
        self.active_policies[agent_id] = initial_policy
        logger.info(
            "[MARL_LAYER] Registered agent %s with policy %s",
            agent_id,
            initial_policy,
        )

    def update_policy(self, agent_id: str, new_policy: AgentPolicy):
        if agent_id in self.active_policies:
            self.active_policies[agent_id] = new_policy
            logger.info(
                "[MARL_LAYER] Updated agent %s to policy %s",
                agent_id,
                new_policy,
            )

    def distribute_reward(self, reward: float):
        """Distribute a reward signal to active agents for policy reinforcement."""
        self.global_reward_signal += reward
        logger.info(
            "[MARL_LAYER] Distributed global reward: %s. Total: %s",
            reward,
            self.global_reward_signal,
        )


marl_layer = MARLLayer()

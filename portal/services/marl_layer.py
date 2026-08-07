import logging
from typing import Dict, List, Any, Optional
from enum import Enum
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class AgentPolicy(str, Enum):
    COOPERATIVE = "COOPERATIVE"
    COMPETITIVE = "COMPETITIVE"
    EXPLORATORY = "EXPLORATORY"

class MARLLayer:
    """
    Multi-Agent Reinforcement Learning (MARL) Layer.
    Coordinates learning and policy optimization across the Agent Parliament.
    """
    def __init__(self):
        self.active_policies: Dict[str, AgentPolicy] = {}
        self.global_reward_signal: float = 0.0

    def register_agent(self, agent_id: str, initial_policy: AgentPolicy = AgentPolicy.COOPERATIVE):
        self.active_policies[agent_id] = initial_policy
        logger.info(f"[MARL_LAYER] Registered agent {agent_id} with policy {initial_policy}")

    def update_policy(self, agent_id: str, new_policy: AgentPolicy):
        if agent_id in self.active_policies:
            self.active_policies[agent_id] = new_policy
            logger.info(f"[MARL_LAYER] Updated agent {agent_id} to policy {new_policy}")

    def distribute_reward(self, reward: float):
        """Distributes a reward signal to all active agents for policy reinforcement."""
        self.global_reward_signal += reward
        logger.info(f"[MARL_LAYER] Distributed global reward: {reward}. Total: {self.global_reward_signal}")

# Global instance
marl_layer = MARLLayer()

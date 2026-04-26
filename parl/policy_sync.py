"""
PARL Policy Synchronization — Shared policy state across the agent swarm.

Implements centralised training with decentralised execution (CTDE):
- A shared PolicyStore holds the latest policy parameters for each agent type
- Agents pull updated parameters at configurable sync intervals
- Policy versioning with rollback support
- Gradient accumulation across agents before parameter update
"""

from __future__ import annotations

import copy
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class PolicyVersion:
    """A snapshot of policy parameters at a given training step."""
    version_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_type: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    training_step: int = 0
    mean_reward: float = 0.0
    is_best: bool = False
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def clone(self) -> "PolicyVersion":
        return PolicyVersion(
            version_id=str(uuid.uuid4()),
            agent_type=self.agent_type,
            parameters=copy.deepcopy(self.parameters),
            training_step=self.training_step,
            mean_reward=self.mean_reward,
            is_best=False,
        )


@dataclass
class GradientAccumulator:
    """Accumulates gradients from multiple agents before a policy update."""
    agent_type: str = ""
    gradients: List[Dict[str, float]] = field(default_factory=list)
    weights: List[float] = field(default_factory=list)  # per-agent reward weights

    def add(self, gradient: Dict[str, float], weight: float = 1.0) -> None:
        self.gradients.append(gradient)
        self.weights.append(weight)

    def aggregate(self) -> Dict[str, float]:
        """Weighted average of accumulated gradients."""
        if not self.gradients:
            return {}
        total_weight = sum(self.weights) or 1.0
        aggregated: Dict[str, float] = {}
        for grad, w in zip(self.gradients, self.weights):
            for k, v in grad.items():
                aggregated[k] = aggregated.get(k, 0.0) + v * (w / total_weight)
        return aggregated

    def clear(self) -> None:
        self.gradients.clear()
        self.weights.clear()

    def __len__(self) -> int:
        return len(self.gradients)


# ---------------------------------------------------------------------------
# PolicyStore — central parameter server
# ---------------------------------------------------------------------------

class PolicyStore:
    """
    Centralised parameter store for the PARL agent swarm.

    All agents share a single PolicyStore instance. Agents push gradient
    updates; the store aggregates them and broadcasts the new parameters.

    Thread-safe for concurrent agent access.
    """

    def __init__(self, max_versions: int = 10):
        self.max_versions = max_versions
        self._policies: Dict[str, PolicyVersion] = {}          # agent_type → current
        self._history: Dict[str, List[PolicyVersion]] = {}     # agent_type → history
        self._accumulators: Dict[str, GradientAccumulator] = {}
        self._lock = threading.RLock()
        self._sync_count: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_agent_type(
        self,
        agent_type: str,
        initial_parameters: Optional[Dict[str, Any]] = None,
    ) -> PolicyVersion:
        """Register an agent type with initial policy parameters."""
        with self._lock:
            params = initial_parameters or {}
            version = PolicyVersion(
                agent_type=agent_type,
                parameters=copy.deepcopy(params),
                training_step=0,
                mean_reward=0.0,
                is_best=True,
            )
            self._policies[agent_type] = version
            self._history[agent_type] = [version.clone()]
            self._accumulators[agent_type] = GradientAccumulator(agent_type=agent_type)
            self._sync_count[agent_type] = 0
            return version

    # ------------------------------------------------------------------
    # Read (agents pull parameters)
    # ------------------------------------------------------------------

    def get_parameters(self, agent_type: str) -> Optional[Dict[str, Any]]:
        """Get the current policy parameters for an agent type."""
        with self._lock:
            policy = self._policies.get(agent_type)
            if policy is None:
                return None
            self._sync_count[agent_type] = self._sync_count.get(agent_type, 0) + 1
            return copy.deepcopy(policy.parameters)

    def get_version(self, agent_type: str) -> Optional[PolicyVersion]:
        """Get the current PolicyVersion for an agent type."""
        with self._lock:
            policy = self._policies.get(agent_type)
            return policy.clone() if policy else None

    # ------------------------------------------------------------------
    # Write (agents push gradient updates)
    # ------------------------------------------------------------------

    def push_gradient(
        self,
        agent_type: str,
        gradient: Dict[str, float],
        weight: float = 1.0,
    ) -> None:
        """Push a gradient update from one agent instance."""
        with self._lock:
            if agent_type not in self._accumulators:
                self.register_agent_type(agent_type)
            self._accumulators[agent_type].add(gradient, weight)

    def apply_gradients(
        self,
        agent_type: str,
        learning_rate: float = 0.01,
        training_step: int = 0,
        mean_reward: float = 0.0,
    ) -> Optional[PolicyVersion]:
        """
        Aggregate accumulated gradients and update policy parameters.

        Uses a simple gradient-descent style update:
            param[k] += lr * aggregated_gradient[k]

        Returns the new PolicyVersion, or None if no gradients were accumulated.
        """
        with self._lock:
            acc = self._accumulators.get(agent_type)
            if acc is None or len(acc) == 0:
                return None

            aggregated = acc.aggregate()
            acc.clear()

            current = self._policies.get(agent_type)
            if current is None:
                return None

            new_params = copy.deepcopy(current.parameters)
            for k, grad in aggregated.items():
                if k in new_params and isinstance(new_params[k], (int, float)):
                    new_params[k] = new_params[k] + learning_rate * grad
                else:
                    new_params[k] = learning_rate * grad

            new_version = PolicyVersion(
                agent_type=agent_type,
                parameters=new_params,
                training_step=training_step,
                mean_reward=mean_reward,
            )

            # Track best policy
            best_reward = max(
                (v.mean_reward for v in self._history.get(agent_type, [])),
                default=float("-inf"),
            )
            if mean_reward >= best_reward:
                new_version.is_best = True
                # Unmark previous best
                for v in self._history.get(agent_type, []):
                    v.is_best = False

            self._policies[agent_type] = new_version

            # Maintain history with cap
            history = self._history.setdefault(agent_type, [])
            history.append(new_version.clone())
            if len(history) > self.max_versions:
                history.pop(0)

            return new_version

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------

    def rollback(self, agent_type: str, steps: int = 1) -> Optional[PolicyVersion]:
        """Roll back to a previous policy version."""
        with self._lock:
            history = self._history.get(agent_type, [])
            if len(history) <= steps:
                return None
            target = history[-(steps + 1)]
            restored = target.clone()
            self._policies[agent_type] = restored
            return restored

    def rollback_to_best(self, agent_type: str) -> Optional[PolicyVersion]:
        """Roll back to the best-performing policy version."""
        with self._lock:
            history = self._history.get(agent_type, [])
            best = max(history, key=lambda v: v.mean_reward, default=None)
            if best is None:
                return None
            restored = best.clone()
            self._policies[agent_type] = restored
            return restored

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def registered_types(self) -> List[str]:
        with self._lock:
            return list(self._policies.keys())

    def sync_counts(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._sync_count)

    def pending_gradients(self, agent_type: str) -> int:
        with self._lock:
            acc = self._accumulators.get(agent_type)
            return len(acc) if acc else 0

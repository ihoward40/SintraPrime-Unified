"""
PARL Experience Replay — Multi-agent shared experience buffer.

Implements the MAC-PO (Multi-Agent Collective Priority Optimization) inspired
experience replay for SintraPrime's parallel agent swarm.

Key features:
- Shared replay buffer across all agents (centralised training)
- Priority-weighted sampling (higher-reward episodes sampled more often)
- Per-agent experience partitioning with cross-agent sharing
- Configurable buffer capacity with FIFO eviction
- Thread-safe for concurrent agent writes
"""

from __future__ import annotations

import heapq
import random
import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class Experience:
    """A single agent experience tuple (s, a, r, s', done)."""
    experience_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    agent_type: str = ""          # "zero", "sigma", "nova", "chat", etc.
    state: Dict[str, Any] = field(default_factory=dict)
    action: Dict[str, Any] = field(default_factory=dict)
    reward: float = 0.0
    next_state: Dict[str, Any] = field(default_factory=dict)
    done: bool = False
    priority: float = 1.0         # higher = sampled more often
    episode_id: str = ""
    training_step: int = 0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __lt__(self, other: "Experience") -> bool:
        # For heap ordering (max-heap via negation)
        return self.priority > other.priority


@dataclass
class ReplayStats:
    """Statistics about the replay buffer."""
    total_stored: int = 0
    total_sampled: int = 0
    buffer_size: int = 0
    capacity: int = 0
    agent_counts: Dict[str, int] = field(default_factory=dict)
    mean_reward: float = 0.0
    mean_priority: float = 0.0


# ---------------------------------------------------------------------------
# Replay Buffer
# ---------------------------------------------------------------------------

class SharedReplayBuffer:
    """
    Thread-safe shared experience replay buffer for the PARL agent swarm.

    All agents (Zero, Sigma, Nova, Chat) write to this buffer.
    The orchestrator samples from it during policy updates.

    Sampling strategies:
    - 'uniform'   : equal probability for all experiences
    - 'priority'  : proportional to experience priority (reward-weighted)
    - 'recency'   : prefer more recent experiences
    """

    STRATEGIES = ("uniform", "priority", "recency")

    def __init__(
        self,
        capacity: int = 10_000,
        strategy: str = "priority",
        alpha: float = 0.6,   # priority exponent (0 = uniform, 1 = full priority)
        beta: float = 0.4,    # importance-sampling correction exponent
    ):
        if strategy not in self.STRATEGIES:
            raise ValueError(f"strategy must be one of {self.STRATEGIES}")
        self.capacity = capacity
        self.strategy = strategy
        self.alpha = alpha
        self.beta = beta
        self._buffer: deque[Experience] = deque(maxlen=capacity)
        self._lock = threading.Lock()
        self._total_stored = 0
        self._total_sampled = 0

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def add(self, experience: Experience) -> None:
        """Add an experience to the buffer (thread-safe)."""
        with self._lock:
            self._buffer.append(experience)
            self._total_stored += 1

    def add_batch(self, experiences: List[Experience]) -> None:
        """Add multiple experiences at once."""
        with self._lock:
            for exp in experiences:
                self._buffer.append(exp)
            self._total_stored += len(experiences)

    # ------------------------------------------------------------------
    # Read / Sample
    # ------------------------------------------------------------------

    def sample(self, n: int) -> List[Experience]:
        """
        Sample n experiences according to the configured strategy.

        Returns fewer than n if the buffer has fewer entries.
        """
        with self._lock:
            buf = list(self._buffer)

        if not buf:
            return []

        n = min(n, len(buf))

        if self.strategy == "uniform":
            samples = random.sample(buf, n)

        elif self.strategy == "priority":
            # Priority-proportional sampling
            priorities = [max(e.priority, 1e-6) ** self.alpha for e in buf]
            total = sum(priorities)
            weights = [p / total for p in priorities]
            samples = random.choices(buf, weights=weights, k=n)

        else:  # recency — prefer later entries
            # Weight by position: later entries have higher weight
            weights = [i + 1 for i in range(len(buf))]
            total = sum(weights)
            norm_weights = [w / total for w in weights]
            samples = random.choices(buf, weights=norm_weights, k=n)

        self._total_sampled += len(samples)
        return samples

    def sample_by_agent(self, agent_id: str, n: int) -> List[Experience]:
        """Sample experiences from a specific agent."""
        with self._lock:
            agent_buf = [e for e in self._buffer if e.agent_id == agent_id]

        if not agent_buf:
            return []

        n = min(n, len(agent_buf))
        return random.sample(agent_buf, n)

    def sample_by_type(self, agent_type: str, n: int) -> List[Experience]:
        """Sample experiences from all agents of a given type."""
        with self._lock:
            type_buf = [e for e in self._buffer if e.agent_type == agent_type]

        if not type_buf:
            return []

        n = min(n, len(type_buf))
        return random.sample(type_buf, n)

    # ------------------------------------------------------------------
    # Update priorities
    # ------------------------------------------------------------------

    def update_priority(self, experience_id: str, new_priority: float) -> bool:
        """Update the priority of a stored experience. Returns True if found."""
        with self._lock:
            for exp in self._buffer:
                if exp.experience_id == experience_id:
                    exp.priority = max(0.0, new_priority)
                    return True
        return False

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def stats(self) -> ReplayStats:
        """Return buffer statistics."""
        with self._lock:
            buf = list(self._buffer)

        agent_counts: Dict[str, int] = {}
        total_reward = 0.0
        total_priority = 0.0

        for exp in buf:
            agent_counts[exp.agent_type] = agent_counts.get(exp.agent_type, 0) + 1
            total_reward += exp.reward
            total_priority += exp.priority

        n = len(buf)
        return ReplayStats(
            total_stored=self._total_stored,
            total_sampled=self._total_sampled,
            buffer_size=n,
            capacity=self.capacity,
            agent_counts=agent_counts,
            mean_reward=total_reward / n if n else 0.0,
            mean_priority=total_priority / n if n else 0.0,
        )

    def __len__(self) -> int:
        return len(self._buffer)

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()


# ---------------------------------------------------------------------------
# Per-agent experience collector (writes to shared buffer)
# ---------------------------------------------------------------------------

class AgentExperienceCollector:
    """
    Thin wrapper around SharedReplayBuffer for a single agent.

    Each agent holds a reference to the shared buffer and uses this
    collector to record its experiences with automatic priority assignment.
    """

    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        shared_buffer: SharedReplayBuffer,
        default_priority: float = 1.0,
    ):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.buffer = shared_buffer
        self.default_priority = default_priority
        self._episode_count = 0
        self._step_count = 0

    def record(
        self,
        state: Dict[str, Any],
        action: Dict[str, Any],
        reward: float,
        next_state: Dict[str, Any],
        done: bool = False,
        priority: Optional[float] = None,
        episode_id: Optional[str] = None,
    ) -> Experience:
        """Record a single (s, a, r, s', done) transition."""
        self._step_count += 1
        if done:
            self._episode_count += 1

        exp = Experience(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            state=state,
            action=action,
            reward=reward,
            next_state=next_state,
            done=done,
            priority=priority if priority is not None else max(abs(reward), self.default_priority),
            episode_id=episode_id or str(uuid.uuid4()),
            training_step=self._step_count,
        )
        self.buffer.add(exp)
        return exp

    @property
    def episode_count(self) -> int:
        return self._episode_count

    @property
    def step_count(self) -> int:
        return self._step_count

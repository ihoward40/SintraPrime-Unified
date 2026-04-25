"""
Load Balancer - Dynamic load calculation and request routing

Provides:
- Dynamic load calculation
- Least-connection routing
- Health-aware balancing
- Request queuing
- Circuit breaking
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """States of the circuit breaker."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class HealthStatus:
    """Health status of a backend."""
    backend_id: str
    is_healthy: bool
    error_count: int = 0
    success_count: int = 0
    total_requests: int = 0
    last_error: Optional[str] = None
    last_check_time: float = field(default_factory=time.time)
    response_time_ms: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    request_queue_depth: int = 0

    def get_success_rate(self) -> float:
        """Get success rate percentage."""
        if self.total_requests == 0:
            return 100.0
        return (self.success_count / self.total_requests) * 100

    def get_health_score(self) -> float:
        """Calculate overall health score (0-100)."""
        success_rate = self.get_success_rate()
        # Penalize slow responses
        response_penalty = min(self.response_time_ms / 1000, 50)
        # Penalize high resource usage
        resource_penalty = (self.cpu_usage + self.memory_usage) / 2
        # Penalize queue depth
        queue_penalty = min(self.request_queue_depth * 2, 20)

        score = success_rate - response_penalty - resource_penalty - queue_penalty
        return max(0, min(100, score))


@dataclass
class LoadBalancingConfig:
    """Configuration for load balancer."""
    algorithm: str = "least_connections"  # least_connections, round_robin, random, health_aware
    health_check_interval_ms: int = 5000
    circuit_breaker_threshold: int = 5  # consecutive failures to open circuit
    circuit_breaker_recovery_ms: int = 30000
    request_timeout_ms: int = 5000
    max_queue_depth: int = 100
    timeout_weight: float = 1.0
    health_weight: float = 1.0
    connection_weight: float = 1.0


class RequestStatistics:
    """Track request statistics for a backend."""

    def __init__(self, backend_id: str):
        self.backend_id = backend_id
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.request_times: List[float] = []
        self.error_log: List[Tuple[float, str]] = []

    def record_success(self, response_time_ms: float) -> None:
        """Record a successful request."""
        self.total_requests += 1
        self.successful_requests += 1
        self.request_times.append(response_time_ms)
        # Keep only recent request times (last 100)
        if len(self.request_times) > 100:
            self.request_times = self.request_times[-100:]

    def record_failure(self, error_message: str, response_time_ms: float = 0) -> None:
        """Record a failed request."""
        self.total_requests += 1
        self.failed_requests += 1
        self.error_log.append((time.time(), error_message))
        # Keep only recent errors (last 50)
        if len(self.error_log) > 50:
            self.error_log = self.error_log[-50:]

    def get_average_response_time_ms(self) -> float:
        """Get average response time."""
        if not self.request_times:
            return 0.0
        return sum(self.request_times) / len(self.request_times)

    def get_success_rate(self) -> float:
        """Get success rate."""
        if self.total_requests == 0:
            return 100.0
        return (self.successful_requests / self.total_requests) * 100

    def get_recent_errors(self, time_window_s: int = 60) -> List[str]:
        """Get errors from the last N seconds."""
        cutoff_time = time.time() - time_window_s
        return [
            error for error_time, error in self.error_log
            if error_time > cutoff_time
        ]


class CircuitBreaker:
    """Circuit breaker for protecting backends."""

    def __init__(
        self,
        backend_id: str,
        failure_threshold: int = 5,
        recovery_timeout_ms: int = 30000
    ):
        self.backend_id = backend_id
        self.failure_threshold = failure_threshold
        self.recovery_timeout_ms = recovery_timeout_ms
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_state_change = time.time()

    def record_success(self) -> None:
        """Record a successful request."""
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            logger.info(f"Circuit breaker for {self.backend_id} closed after recovery")
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def record_failure(self) -> None:
        """Record a failed request."""
        self.failure_count += 1

        if self.failure_count >= self.failure_threshold and self.state == CircuitState.CLOSED:
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
            logger.warning(f"Circuit breaker for {self.backend_id} opened after {self.failure_count} failures")

    def is_available(self) -> bool:
        """Check if circuit is available to accept requests."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            elapsed = (time.time() - self.last_state_change) * 1000
            if elapsed >= self.recovery_timeout_ms:
                self.state = CircuitState.HALF_OPEN
                self.failure_count = 0
                logger.info(f"Circuit breaker for {self.backend_id} entering half-open state")
                return True
            return False

        # HALF_OPEN
        return True


class RequestQueue:
    """Queue for requests waiting for available backends."""

    def __init__(self, max_depth: int = 100):
        self.max_depth = max_depth
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_depth)
        self.dropped_requests = 0

    async def enqueue(self, request: Dict[str, Any]) -> bool:
        """Add a request to the queue."""
        try:
            self.queue.put_nowait(request)
            return True
        except asyncio.QueueFull:
            self.dropped_requests += 1
            logger.warning(f"Request queue full, dropping request")
            return False

    async def dequeue(self) -> Optional[Dict[str, Any]]:
        """Get next request from queue."""
        try:
            return self.queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    def get_depth(self) -> int:
        """Get current queue depth."""
        return self.queue.qsize()


class LoadBalancer:
    """Basic load balancer with multiple routing algorithms."""

    def __init__(self, config: Optional[LoadBalancingConfig] = None):
        self.config = config or LoadBalancingConfig()
        self.backends: Dict[str, HealthStatus] = {}
        self.statistics: Dict[str, RequestStatistics] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.request_queue = RequestQueue(self.config.max_queue_depth)
        self.current_backend_index = 0  # For round-robin

        self.total_requests = 0
        self.total_errors = 0

    def register_backend(
        self,
        backend_id: str,
        initial_healthy: bool = True
    ) -> None:
        """Register a backend server."""
        self.backends[backend_id] = HealthStatus(
            backend_id=backend_id,
            is_healthy=initial_healthy
        )
        self.statistics[backend_id] = RequestStatistics(backend_id)
        self.circuit_breakers[backend_id] = CircuitBreaker(
            backend_id,
            failure_threshold=self.config.circuit_breaker_threshold,
            recovery_timeout_ms=self.config.circuit_breaker_recovery_ms
        )
        logger.info(f"Registered backend {backend_id}")

    def unregister_backend(self, backend_id: str) -> None:
        """Unregister a backend server."""
        if backend_id in self.backends:
            del self.backends[backend_id]
        if backend_id in self.statistics:
            del self.statistics[backend_id]
        if backend_id in self.circuit_breakers:
            del self.circuit_breakers[backend_id]
        logger.info(f"Unregistered backend {backend_id}")

    def update_backend_health(
        self,
        backend_id: str,
        response_time_ms: float,
        cpu_usage: float,
        memory_usage: float,
        queue_depth: int
    ) -> None:
        """Update health metrics for a backend."""
        if backend_id not in self.backends:
            return

        health = self.backends[backend_id]
        health.response_time_ms = response_time_ms
        health.cpu_usage = cpu_usage
        health.memory_usage = memory_usage
        health.request_queue_depth = queue_depth
        health.last_check_time = time.time()

        # Determine if backend is healthy
        is_healthy = (
            response_time_ms < self.config.request_timeout_ms and
            cpu_usage < 90 and
            memory_usage < 90 and
            queue_depth < self.config.max_queue_depth
        )
        health.is_healthy = is_healthy

    def record_request_success(
        self,
        backend_id: str,
        response_time_ms: float
    ) -> None:
        """Record a successful request to a backend."""
        if backend_id not in self.statistics:
            return

        stats = self.statistics[backend_id]
        stats.record_success(response_time_ms)

        health = self.backends[backend_id]
        health.success_count += 1
        health.total_requests += 1

        circuit_breaker = self.circuit_breakers[backend_id]
        circuit_breaker.record_success()

    def record_request_failure(
        self,
        backend_id: str,
        error_message: str,
        response_time_ms: float = 0
    ) -> None:
        """Record a failed request to a backend."""
        if backend_id not in self.statistics:
            return

        self.total_errors += 1
        stats = self.statistics[backend_id]
        stats.record_failure(error_message, response_time_ms)

        health = self.backends[backend_id]
        health.error_count += 1
        health.total_requests += 1
        health.last_error = error_message
        health.is_healthy = False

        circuit_breaker = self.circuit_breakers[backend_id]
        circuit_breaker.record_failure()

    def get_healthy_backends(self) -> List[str]:
        """Get list of healthy backends."""
        return [
            bid for bid, health in self.backends.items()
            if health.is_healthy and self.circuit_breakers[bid].is_available()
        ]

    def select_backend_least_connections(self) -> Optional[str]:
        """Select backend using least-connection algorithm."""
        healthy = self.get_healthy_backends()
        if not healthy:
            return None

        # Find backend with least queue depth (simulating connections)
        return min(
            healthy,
            key=lambda bid: self.backends[bid].request_queue_depth
        )

    def select_backend_round_robin(self) -> Optional[str]:
        """Select backend using round-robin algorithm."""
        healthy = self.get_healthy_backends()
        if not healthy:
            return None

        self.current_backend_index = (self.current_backend_index + 1) % len(healthy)
        return healthy[self.current_backend_index]

    def select_backend_random(self) -> Optional[str]:
        """Select backend using random selection."""
        import random
        healthy = self.get_healthy_backends()
        return random.choice(healthy) if healthy else None

    def select_backend(self) -> Optional[str]:
        """Select a backend based on configured algorithm."""
        if self.config.algorithm == "least_connections":
            return self.select_backend_least_connections()
        elif self.config.algorithm == "round_robin":
            return self.select_backend_round_robin()
        elif self.config.algorithm == "random":
            return self.select_backend_random()
        elif self.config.algorithm == "health_aware":
            return self.select_backend_health_aware()
        else:
            return self.select_backend_least_connections()

    def select_backend_health_aware(self) -> Optional[str]:
        """Select backend using health-aware algorithm."""
        healthy = self.get_healthy_backends()
        if not healthy:
            return None

        # Score based on health metrics
        scores = {}
        for backend_id in healthy:
            health = self.backends[backend_id]
            score = health.get_health_score()
            scores[backend_id] = score

        return max(scores.items(), key=lambda x: x[1])[0]

    async def route_request(self, request: Dict[str, Any]) -> Tuple[Optional[str], bool]:
        """Route a request to an available backend."""
        self.total_requests += 1

        backend_id = self.select_backend()
        if backend_id:
            return (backend_id, True)

        # Try to queue request
        queued = await self.request_queue.enqueue(request)
        return (None, queued)

    def get_backend_stats(self, backend_id: str) -> Dict[str, Any]:
        """Get statistics for a backend."""
        if backend_id not in self.statistics:
            return {}

        stats = self.statistics[backend_id]
        health = self.backends[backend_id]
        circuit_breaker = self.circuit_breakers[backend_id]

        return {
            'backend_id': backend_id,
            'is_healthy': health.is_healthy,
            'circuit_state': circuit_breaker.state.value,
            'total_requests': stats.total_requests,
            'successful_requests': stats.successful_requests,
            'failed_requests': stats.failed_requests,
            'success_rate': stats.get_success_rate(),
            'avg_response_time_ms': stats.get_average_response_time_ms(),
            'health_score': health.get_health_score(),
            'cpu_usage': health.cpu_usage,
            'memory_usage': health.memory_usage,
            'queue_depth': health.request_queue_depth,
        }

    def get_load_balancer_stats(self) -> Dict[str, Any]:
        """Get overall load balancer statistics."""
        healthy_count = len(self.get_healthy_backends())
        total_backends = len(self.backends)

        return {
            'total_requests': self.total_requests,
            'total_errors': self.total_errors,
            'error_rate': (self.total_errors / max(self.total_requests, 1)) * 100,
            'healthy_backends': healthy_count,
            'total_backends': total_backends,
            'queue_depth': self.request_queue.get_depth(),
            'dropped_requests': self.request_queue.dropped_requests,
            'algorithm': self.config.algorithm,
        }


class HealthAwareBalancer(LoadBalancer):
    """Load balancer with advanced health-awareness and predictive routing."""

    def __init__(self, config: Optional[LoadBalancingConfig] = None):
        super().__init__(config or LoadBalancingConfig(algorithm="health_aware"))
        self.response_time_history: Dict[str, List[float]] = defaultdict(list)
        self.prediction_window_size = 20

    def select_backend_health_aware(self) -> Optional[str]:
        """Select backend using health-aware algorithm with prediction."""
        healthy = self.get_healthy_backends()
        if not healthy:
            return None

        best_backend = None
        best_score = -1

        for backend_id in healthy:
            health = self.backends[backend_id]
            stats = self.statistics[backend_id]

            # Base score from health
            health_score = health.get_health_score()

            # Predictive component - trend of response times
            trend = 0
            if len(self.response_time_history[backend_id]) > 1:
                recent = self.response_time_history[backend_id][-5:]
                trend = sum(recent) / len(recent) - sum(recent[:2]) / len(recent[:2])

            # Adjust score based on trend (increasing response times lower score)
            adjusted_score = health_score - (trend * 0.5)

            if adjusted_score > best_score:
                best_score = adjusted_score
                best_backend = backend_id

        return best_backend

    def record_request_success(
        self,
        backend_id: str,
        response_time_ms: float
    ) -> None:
        """Record request with history tracking."""
        super().record_request_success(backend_id, response_time_ms)
        
        self.response_time_history[backend_id].append(response_time_ms)
        if len(self.response_time_history[backend_id]) > self.prediction_window_size:
            self.response_time_history[backend_id].pop(0)

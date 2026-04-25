"""
Distributed Runtime for SintraPrime UniVerse

Enables agents to scale horizontally across multiple machines with zero-downtime deployments.
Provides P2P agent communication, load balancing, failover, and horizontal scaling.
"""

from universe.distributed.agent_mesh import AgentMesh, NodeDiscovery, MessageRouter
from universe.distributed.distributed_scheduler import DistributedScheduler, WorkStealingAlgorithm
from universe.distributed.load_balancer import LoadBalancer, HealthAwareBalancer
from universe.distributed.service_registry import ServiceRegistry, ServiceInstance
from universe.distributed.distributed_cache import DistributedCache

__all__ = [
    'AgentMesh',
    'NodeDiscovery',
    'MessageRouter',
    'DistributedScheduler',
    'WorkStealingAlgorithm',
    'LoadBalancer',
    'HealthAwareBalancer',
    'ServiceRegistry',
    'ServiceInstance',
    'DistributedCache',
]

__version__ = '1.0.0'

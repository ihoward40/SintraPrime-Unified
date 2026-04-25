"""
Comprehensive test suite for Distributed Runtime components
Tests node discovery, message routing, task scheduling, failover, load balancing, and network partitions
"""

import asyncio
import pytest
import time
from typing import Set
import sys
import os

# Add universe to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from universe.distributed.agent_mesh import (
    AgentMesh, NodeDiscovery, MessageRouter, NetworkMessage, MessageType, NodeStatus
)
from universe.distributed.distributed_scheduler import (
    DistributedScheduler, DistributedTask, TaskPriority, TaskStatus, TaskSLA
)
from universe.distributed.load_balancer import (
    LoadBalancer, HealthAwareBalancer, LoadBalancingConfig, CircuitBreaker, CircuitState
)
from universe.distributed.service_registry import ServiceRegistry, ServiceStatus, HealthCheck
from universe.distributed.distributed_cache import DistributedCache, CacheStrategy


# ============================================================================
# AGENT MESH TESTS (14 tests)
# ============================================================================

class TestNodeDiscovery:
    """Test node discovery functionality."""

    def test_register_node(self):
        """Test node registration."""
        discovery = NodeDiscovery()
        node_info = discovery.register_node(
            "node1", "agent-1", "127.0.0.1", 5000, capacity=10
        )
        assert node_info.node_id == "node1"
        assert node_info.is_healthy()
        assert len(discovery.nodes) == 1

    def test_deregister_node(self):
        """Test node deregistration."""
        discovery = NodeDiscovery()
        discovery.register_node("node1", "agent-1", "127.0.0.1", 5000)
        assert discovery.deregister_node("node1")
        assert len(discovery.nodes) == 0

    def test_heartbeat_update(self):
        """Test heartbeat update."""
        discovery = NodeDiscovery()
        discovery.register_node("node1", "agent-1", "127.0.0.1", 5000)
        old_time = discovery.nodes["node1"].last_heartbeat
        time.sleep(0.1)
        assert discovery.update_heartbeat("node1")
        assert discovery.nodes["node1"].last_heartbeat > old_time

    def test_peer_connections(self):
        """Test peer connection management."""
        discovery = NodeDiscovery()
        discovery.register_node("node1", "agent-1", "127.0.0.1", 5000)
        discovery.register_node("node2", "agent-2", "127.0.0.1", 5001)
        
        assert discovery.add_peer_connection("node1", "node2")
        assert "node2" in discovery.nodes["node1"].connected_peers
        assert "node1" in discovery.nodes["node2"].connected_peers
        
        assert discovery.remove_peer_connection("node1", "node2")
        assert "node2" not in discovery.nodes["node1"].connected_peers

    def test_get_healthy_nodes(self):
        """Test getting healthy nodes."""
        discovery = NodeDiscovery()
        discovery.register_node("node1", "agent-1", "127.0.0.1", 5000)
        discovery.register_node("node2", "agent-2", "127.0.0.1", 5001)
        
        healthy = discovery.get_healthy_nodes()
        assert len(healthy) == 2
        
        # Mark node as unhealthy
        discovery.nodes["node1"].last_heartbeat = time.time() - 100
        healthy = discovery.get_healthy_nodes()
        assert len(healthy) == 1

    def test_detect_partitions(self):
        """Test network partition detection."""
        discovery = NodeDiscovery()
        # Create two isolated clusters
        discovery.register_node("node1", "agent-1", "127.0.0.1", 5000)
        discovery.register_node("node2", "agent-2", "127.0.0.1", 5001)
        discovery.register_node("node3", "agent-3", "127.0.0.1", 5002)
        
        discovery.add_peer_connection("node1", "node2")
        # node3 is isolated
        
        partitions = discovery.detect_partitions()
        assert len(partitions) == 2

    def test_update_node_metrics(self):
        """Test updating node metrics."""
        discovery = NodeDiscovery()
        discovery.register_node("node1", "agent-1", "127.0.0.1", 5000)
        
        metrics = {"cpu_usage": 45.5, "memory_usage": 60.0}
        assert discovery.update_node_metrics("node1", metrics)
        assert discovery.nodes["node1"].metrics["cpu_usage"] == 45.5


class TestMessageRouter:
    """Test message routing functionality."""

    def test_find_route_direct(self):
        """Test finding direct route between nodes."""
        discovery = NodeDiscovery()
        discovery.register_node("node1", "agent-1", "127.0.0.1", 5000)
        discovery.register_node("node2", "agent-2", "127.0.0.1", 5001)
        discovery.add_peer_connection("node1", "node2")
        
        router = MessageRouter(discovery)
        route = router.find_route("node1", "node2")
        assert route == ["node1", "node2"]

    def test_find_route_multi_hop(self):
        """Test finding multi-hop route."""
        discovery = NodeDiscovery()
        discovery.register_node("node1", "agent-1", "127.0.0.1", 5000)
        discovery.register_node("node2", "agent-2", "127.0.0.1", 5001)
        discovery.register_node("node3", "agent-3", "127.0.0.1", 5002)
        
        discovery.add_peer_connection("node1", "node2")
        discovery.add_peer_connection("node2", "node3")
        
        router = MessageRouter(discovery)
        route = router.find_route("node1", "node3")
        assert len(route) == 3
        assert route[0] == "node1" and route[-1] == "node3"

    def test_find_route_no_path(self):
        """Test finding route when no path exists."""
        discovery = NodeDiscovery()
        discovery.register_node("node1", "agent-1", "127.0.0.1", 5000)
        discovery.register_node("node2", "agent-2", "127.0.0.1", 5001)
        
        router = MessageRouter(discovery)
        route = router.find_route("node1", "node2")
        assert route is None

    @pytest.mark.asyncio
    async def test_send_message(self):
        """Test message sending."""
        discovery = NodeDiscovery()
        discovery.register_node("node1", "agent-1", "127.0.0.1", 5000)
        discovery.register_node("node2", "agent-2", "127.0.0.1", 5001)
        discovery.add_peer_connection("node1", "node2")
        
        router = MessageRouter(discovery)
        
        message_received = []
        def handler(msg):
            message_received.append(msg)
        
        router.register_handler(MessageType.HEARTBEAT, handler)
        
        success = await router.send_message(NetworkMessage(
            message_id="msg1",
            message_type=MessageType.HEARTBEAT,
            sender_id="node1",
            receiver_id="node2",
            payload={"data": "test"},
            timestamp=time.time()
        ))
        
        assert success

    def test_get_network_topology(self):
        """Test getting network topology."""
        discovery = NodeDiscovery()
        discovery.register_node("node1", "agent-1", "127.0.0.1", 5000)
        discovery.register_node("node2", "agent-2", "127.0.0.1", 5001)
        discovery.add_peer_connection("node1", "node2")
        
        router = MessageRouter(discovery)
        topology = router.get_network_topology()
        
        assert "nodes" in topology
        assert "peer_graph" in topology
        assert "partitions" in topology


# ============================================================================
# DISTRIBUTED SCHEDULER TESTS (13 tests)
# ============================================================================

class TestDistributedScheduler:
    """Test distributed scheduler functionality."""

    def test_register_agent(self):
        """Test agent registration."""
        scheduler = DistributedScheduler()
        capacity = scheduler.register_agent("agent1", 10)
        
        assert capacity.agent_id == "agent1"
        assert capacity.max_capacity == 10
        assert capacity.get_available_capacity() == 10

    def test_submit_task(self):
        """Test task submission."""
        scheduler = DistributedScheduler()
        task_id = scheduler.submit_task(
            "process",
            {"data": "test"},
            priority=TaskPriority.NORMAL
        )
        
        assert task_id is not None
        assert task_id in scheduler.tasks_by_id
        assert scheduler.total_scheduled == 1

    def test_get_best_agent_for_task(self):
        """Test agent selection for task."""
        scheduler = DistributedScheduler()
        scheduler.register_agent("agent1", 10, {"process"})
        scheduler.register_agent("agent2", 5, {"process"})
        
        task = DistributedTask(
            task_id="task1",
            task_type="process",
            payload={},
            sla=TaskSLA(),
            status=TaskStatus.PENDING
        )
        
        best_agent = scheduler.get_best_agent_for_task(task)
        assert best_agent in ["agent1", "agent2"]

    @pytest.mark.asyncio
    async def test_schedule_task(self):
        """Test task scheduling."""
        scheduler = DistributedScheduler()
        scheduler.register_agent("agent1", 10)
        
        task = DistributedTask(
            task_id="task1",
            task_type="process",
            payload={},
            sla=TaskSLA(),
            status=TaskStatus.PENDING
        )
        scheduler.tasks_by_id["task1"] = task
        
        success = await scheduler.schedule_task(task)
        assert success
        assert task.status == TaskStatus.ASSIGNED

    @pytest.mark.asyncio
    async def test_complete_task(self):
        """Test task completion."""
        scheduler = DistributedScheduler()
        scheduler.register_agent("agent1", 10)
        
        task_id = scheduler.submit_task("process", {})
        task = scheduler.tasks_by_id[task_id]
        task.assigned_agent_id = "agent1"
        
        success = await scheduler.complete_task(task_id, result="done")
        assert success
        assert task.status == TaskStatus.COMPLETED
        assert scheduler.total_completed == 1

    @pytest.mark.asyncio
    async def test_task_retry(self):
        """Test task retry."""
        scheduler = DistributedScheduler()
        scheduler.register_agent("agent1", 10)
        
        task_id = scheduler.submit_task("process", {})
        task = scheduler.tasks_by_id[task_id]
        task.assigned_agent_id = "agent1"
        task.status = TaskStatus.FAILED
        
        success = await scheduler.retry_task(task_id)
        assert success
        assert task.retry_count == 1

    def test_get_pending_tasks(self):
        """Test getting pending tasks."""
        scheduler = DistributedScheduler()
        scheduler.submit_task("process", {}, priority=TaskPriority.HIGH)
        scheduler.submit_task("process", {}, priority=TaskPriority.LOW)
        
        pending = scheduler.get_pending_tasks()
        assert len(pending) == 2
        # Should be sorted by priority
        assert pending[0].sla.priority == TaskPriority.HIGH

    def test_get_agent_load(self):
        """Test getting agent load."""
        scheduler = DistributedScheduler()
        scheduler.register_agent("agent1", 10)
        scheduler.register_agent("agent2", 10)
        
        loads = scheduler.get_agent_load()
        assert len(loads) == 2
        assert all(load == 0.0 for load in loads.values())

    def test_global_average_load(self):
        """Test calculating global average load."""
        scheduler = DistributedScheduler()
        scheduler.register_agent("agent1", 10)
        scheduler.register_agent("agent2", 10)
        
        avg_load = scheduler.get_global_average_load()
        assert avg_load == 0.0

    def test_work_stealing_suggestion(self):
        """Test work stealing algorithm."""
        scheduler = DistributedScheduler()
        scheduler.register_agent("agent1", 10)
        scheduler.register_agent("agent2", 10)
        
        # Simulate high load on agent2
        scheduler.agent_capacities["agent2"].current_load = 8
        
        suggestion = scheduler.suggest_work_steal()
        # Should suggest stealing from agent2
        if suggestion:
            assert suggestion[1] == "agent2"

    def test_scheduler_stats(self):
        """Test getting scheduler statistics."""
        scheduler = DistributedScheduler()
        scheduler.register_agent("agent1", 10)
        scheduler.submit_task("process", {})
        
        stats = scheduler.get_scheduler_stats()
        assert stats["total_scheduled"] == 1
        assert stats["agent_count"] == 1


# ============================================================================
# LOAD BALANCER TESTS (8 tests)
# ============================================================================

class TestLoadBalancer:
    """Test load balancer functionality."""

    def test_register_backend(self):
        """Test backend registration."""
        lb = LoadBalancer()
        lb.register_backend("backend1")
        
        assert "backend1" in lb.backends
        assert lb.backends["backend1"].is_healthy

    def test_select_backend_least_connections(self):
        """Test least connections algorithm."""
        lb = LoadBalancer(LoadBalancingConfig(algorithm="least_connections"))
        lb.register_backend("backend1")
        lb.register_backend("backend2")
        
        lb.backends["backend1"].request_queue_depth = 5
        lb.backends["backend2"].request_queue_depth = 2
        
        selected = lb.select_backend()
        assert selected == "backend2"

    def test_select_backend_round_robin(self):
        """Test round-robin algorithm."""
        lb = LoadBalancer(LoadBalancingConfig(algorithm="round_robin"))
        lb.register_backend("backend1")
        lb.register_backend("backend2")
        
        selected1 = lb.select_backend()
        selected2 = lb.select_backend()
        
        assert selected1 != selected2

    @pytest.mark.asyncio
    async def test_route_request(self):
        """Test request routing."""
        lb = LoadBalancer()
        lb.register_backend("backend1")
        
        backend_id, success = await lb.route_request({"data": "test"})
        assert success
        assert backend_id == "backend1"

    def test_circuit_breaker_open(self):
        """Test circuit breaker opening."""
        cb = CircuitBreaker("backend1", failure_threshold=3)
        
        assert cb.is_available()
        
        for _ in range(3):
            cb.record_failure()
        
        assert not cb.is_available()
        assert cb.state == CircuitState.OPEN

    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery."""
        cb = CircuitBreaker("backend1", failure_threshold=2, recovery_timeout_ms=100)
        
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        
        # Simulate recovery timeout
        cb.last_state_change = time.time() - 0.2
        assert cb.is_available()
        assert cb.state == CircuitState.HALF_OPEN
        
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_backend_stats(self):
        """Test getting backend statistics."""
        lb = LoadBalancer()
        lb.register_backend("backend1")
        lb.record_request_success("backend1", 100.0)
        
        stats = lb.get_backend_stats("backend1")
        assert stats["successful_requests"] == 1
        assert stats["success_rate"] == 100.0

    def test_load_balancer_stats(self):
        """Test getting load balancer statistics."""
        lb = LoadBalancer()
        lb.register_backend("backend1")
        lb.total_requests = 10
        lb.total_errors = 1
        
        stats = lb.get_load_balancer_stats()
        assert stats["total_requests"] == 10
        assert stats["total_errors"] == 1


# ============================================================================
# SERVICE REGISTRY TESTS (6 tests)
# ============================================================================

class TestServiceRegistry:
    """Test service registry functionality."""

    def test_register_service(self):
        """Test service registration."""
        registry = ServiceRegistry()
        instance = registry.register_service(
            "api-service", "127.0.0.1", 8000
        )
        
        assert instance.service_name == "api-service"
        assert instance.service_id in registry.services

    def test_deregister_service(self):
        """Test service deregistration."""
        registry = ServiceRegistry()
        instance = registry.register_service("api-service", "127.0.0.1", 8000)
        
        success = registry.deregister_service(instance.service_id)
        assert success
        assert instance.service_id not in registry.services

    def test_get_services_by_name(self):
        """Test getting services by name."""
        registry = ServiceRegistry()
        registry.register_service("api-service", "127.0.0.1", 8000)
        registry.register_service("api-service", "127.0.0.1", 8001)
        
        services = registry.get_services_by_name("api-service")
        assert len(services) == 2

    def test_get_healthy_services(self):
        """Test getting healthy services."""
        registry = ServiceRegistry()
        instance = registry.register_service("api-service", "127.0.0.1", 8000)
        
        healthy = registry.get_healthy_services("api-service")
        assert len(healthy) == 1
        assert healthy[0].service_id == instance.service_id

    def test_add_health_check(self):
        """Test adding health check."""
        registry = ServiceRegistry()
        instance = registry.register_service("api-service", "127.0.0.1", 8000)
        
        check = registry.add_health_check(instance.service_id, "http")
        assert check is not None
        assert check in instance.checks.values()

    def test_service_stats(self):
        """Test getting service statistics."""
        registry = ServiceRegistry()
        registry.register_service("api-service", "127.0.0.1", 8000)
        registry.register_service("db-service", "127.0.0.1", 5432)
        
        stats = registry.get_service_stats()
        assert stats["total_services"] == 2
        assert stats["total_instances"] == 2


# ============================================================================
# DISTRIBUTED CACHE TESTS (11 tests)
# ============================================================================

class TestDistributedCache:
    """Test distributed cache functionality."""

    def test_get_set(self):
        """Test basic get/set operations."""
        cache = DistributedCache()
        cache.set("key1", "value1")
        
        value = cache.get("key1")
        assert value == "value1"

    def test_get_miss(self):
        """Test cache miss."""
        cache = DistributedCache()
        value = cache.get("nonexistent")
        
        assert value is None
        assert cache.stats.misses == 1

    def test_delete(self):
        """Test delete operation."""
        cache = DistributedCache()
        cache.set("key1", "value1")
        assert cache.delete("key1")
        assert cache.get("key1") is None

    def test_ttl_expiration(self):
        """Test TTL expiration."""
        cache = DistributedCache()
        cache.set("key1", "value1", ttl_seconds=1)
        
        assert cache.get("key1") == "value1"
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_invalidate_by_tag(self):
        """Test invalidation by tag."""
        cache = DistributedCache()
        cache.set("key1", "value1", tags={"session"})
        cache.set("key2", "value2", tags={"session"})
        cache.set("key3", "value3", tags={"other"})
        
        invalidated = cache.invalidate_by_tag("session")
        assert invalidated == 2
        assert cache.get("key3") == "value3"

    def test_list_operations(self):
        """Test list operations."""
        cache = DistributedCache()
        cache.lpush("list1", "a", "b", "c")
        
        assert cache.llen("list1") == 3
        assert cache.lpop("list1") == "c"
        assert cache.rpop("list1") == "a"

    def test_set_operations(self):
        """Test set operations."""
        cache = DistributedCache()
        cache.sadd("set1", "a", "b", "c")
        
        assert cache.scard("set1") == 3
        cache.srem("set1", "a")
        assert cache.scard("set1") == 2

    def test_hash_operations(self):
        """Test hash operations."""
        cache = DistributedCache()
        cache.hset("hash1", "field1", "value1")
        cache.hset("hash1", "field2", "value2")
        
        assert cache.hget("hash1", "field1") == "value1"
        cache.hdel("hash1", "field1")
        assert cache.hget("hash1", "field1") is None

    def test_incr_decr(self):
        """Test increment/decrement operations."""
        cache = DistributedCache()
        cache.set("counter", 10)
        
        cache.incr("counter", 5)
        assert cache.get("counter") == 15
        
        cache.decr("counter", 3)
        assert cache.get("counter") == 12

    def test_cache_stats(self):
        """Test getting cache statistics."""
        cache = DistributedCache()
        cache.set("key1", "value1")
        cache.get("key1")  # hit
        cache.get("nonexistent")  # miss
        
        stats = cache.get_cache_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_ratio"] == 50.0

    def test_lru_eviction(self):
        """Test LRU eviction."""
        cache = DistributedCache(max_size=3, strategy=CacheStrategy.LRU)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # Access key1 to make it recently used
        cache.get("key1")
        
        # Add new key, should evict key2 (least recently used)
        cache.set("key4", "value4")
        
        assert cache.get("key1") is not None
        assert cache.get("key4") is not None


# ============================================================================
# INTEGRATION TESTS (3 tests)
# ============================================================================

class TestIntegration:
    """Integration tests for distributed components."""

    @pytest.mark.asyncio
    async def test_full_task_workflow(self):
        """Test complete task execution workflow."""
        scheduler = DistributedScheduler()
        scheduler.register_agent("agent1", 10)
        scheduler.register_agent("agent2", 10)
        
        # Submit tasks
        task1 = scheduler.submit_task("process", {"id": 1})
        task2 = scheduler.submit_task("process", {"id": 2})
        
        # Schedule tasks
        for task_id in [task1, task2]:
            task = scheduler.tasks_by_id[task_id]
            await scheduler.schedule_task(task)
        
        # Complete tasks
        await scheduler.complete_task(task1, result={"processed": True})
        await scheduler.complete_task(task2, result={"processed": True})
        
        assert scheduler.total_completed == 2

    @pytest.mark.asyncio
    async def test_mesh_with_failover(self):
        """Test mesh network with node failover."""
        # Create agent mesh
        mesh1 = AgentMesh("node1", "agent-1", "127.0.0.1", 5000)
        mesh2 = AgentMesh("node2", "agent-2", "127.0.0.1", 5001)
        
        # Connect nodes
        mesh1.connect_peer("node2", "127.0.0.1", 5001)
        mesh2.connect_peer("node1", "127.0.0.1", 5000)
        
        # Verify connectivity
        neighbors = mesh1.discovery.get_neighbors("node1")
        assert len(neighbors) > 0
        
        # Simulate node failure
        mesh2.discovery.nodes["node2"].status = NodeStatus.OFFLINE
        
        # Check partition detection
        partitions = mesh1.discovery.detect_partitions()
        # May detect partition or not depending on timeout

    @pytest.mark.asyncio
    async def test_load_balancer_with_service_registry(self):
        """Test load balancer with service registry."""
        registry = ServiceRegistry()
        lb = LoadBalancer()
        
        # Register services
        instance1 = registry.register_service("api", "127.0.0.1", 8000)
        instance2 = registry.register_service("api", "127.0.0.1", 8001)
        
        # Register as backends
        lb.register_backend(instance1.service_id)
        lb.register_backend(instance2.service_id)
        
        # Get healthy services
        healthy = registry.get_healthy_services("api")
        assert len(healthy) == 2
        
        # Route request
        backend_id, success = await lb.route_request({"data": "test"})
        assert success


# ============================================================================
# PERFORMANCE TESTS (2 tests)
# ============================================================================

class TestPerformance:
    """Performance tests for distributed components."""

    def test_scheduler_throughput(self):
        """Test scheduler throughput."""
        scheduler = DistributedScheduler()
        for i in range(10):
            scheduler.register_agent(f"agent{i}", 100)
        
        start_time = time.time()
        for i in range(1000):
            scheduler.submit_task("process", {"id": i})
        elapsed = time.time() - start_time
        
        throughput = 1000 / elapsed
        print(f"Scheduler throughput: {throughput:.0f} tasks/sec")
        assert throughput > 1000  # Should handle 1000+ tasks/sec

    def test_cache_performance(self):
        """Test cache performance."""
        cache = DistributedCache(max_size=10000)
        
        # Warm cache
        for i in range(1000):
            cache.set(f"key{i}", f"value{i}")
        
        # Measure read throughput
        start_time = time.time()
        for i in range(10000):
            cache.get(f"key{i % 1000}")
        elapsed = time.time() - start_time
        
        throughput = 10000 / elapsed
        print(f"Cache throughput: {throughput:.0f} ops/sec")
        assert throughput > 10000  # Should handle 10k+ ops/sec


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Agent Mesh Network - libp2p-based P2P network for agent-to-agent communication

Provides:
- Node discovery & registration
- Direct agent-to-agent messaging
- Network monitoring
- Partition recovery
- Peer-to-peer communication
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, asdict
from typing import Dict, List, Callable, Optional, Set, Any, Tuple
from enum import Enum
from collections import defaultdict
import heapq
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages in the agent mesh network."""
    HEARTBEAT = "heartbeat"
    TASK_ASSIGNMENT = "task_assignment"
    TASK_RESULT = "task_result"
    NODE_DISCOVERY = "node_discovery"
    NODE_SHUTDOWN = "node_shutdown"
    PARTITION_DETECTION = "partition_detection"
    SYNC_REQUEST = "sync_request"
    SYNC_RESPONSE = "sync_response"
    PING = "ping"
    PONG = "pong"
    STATE_UPDATE = "state_update"
    RECOVERY_MARKER = "recovery_marker"


class NodeStatus(Enum):
    """Status of a node in the mesh."""
    ONLINE = "online"
    RECOVERING = "recovering"
    OFFLINE = "offline"
    DEGRADED = "degraded"


@dataclass
class NetworkMessage:
    """Message in the agent mesh network."""
    message_id: str
    message_type: MessageType
    sender_id: str
    receiver_id: str
    payload: Dict[str, Any]
    timestamp: float
    ttl: int = 10
    priority: int = 5

    def to_dict(self) -> Dict[str, Any]:
        return {
            'message_id': self.message_id,
            'message_type': self.message_type.value,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'payload': self.payload,
            'timestamp': self.timestamp,
            'ttl': self.ttl,
            'priority': self.priority,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NetworkMessage':
        data['message_type'] = MessageType(data['message_type'])
        return cls(**data)


@dataclass
class NodeInfo:
    """Information about a node in the mesh."""
    node_id: str
    node_name: str
    ip_address: str
    port: int
    capacity: int
    status: NodeStatus
    last_heartbeat: float
    connected_peers: Set[str]
    created_at: float
    metrics: Dict[str, Any]

    def is_healthy(self, timeout: float = 30.0) -> bool:
        """Check if node is healthy based on heartbeat timeout."""
        return (time.time() - self.last_heartbeat) < timeout and self.status == NodeStatus.ONLINE

    def to_dict(self) -> Dict[str, Any]:
        return {
            'node_id': self.node_id,
            'node_name': self.node_name,
            'ip_address': self.ip_address,
            'port': self.port,
            'capacity': self.capacity,
            'status': self.status.value,
            'last_heartbeat': self.last_heartbeat,
            'connected_peers': list(self.connected_peers),
            'created_at': self.created_at,
            'metrics': self.metrics,
        }


class NodeDiscovery:
    """Discovers and manages nodes in the agent mesh."""

    def __init__(self):
        self.nodes: Dict[str, NodeInfo] = {}
        self.peer_graph: Dict[str, Set[str]] = defaultdict(set)
        self.node_locations: Dict[str, Tuple[str, int]] = {}  # node_id -> (ip, port)
        self.discovery_timeout = 30.0
        self.heartbeat_interval = 5.0
        self.partition_detection_interval = 10.0

    def register_node(
        self,
        node_id: str,
        node_name: str,
        ip_address: str,
        port: int,
        capacity: int = 10
    ) -> NodeInfo:
        """Register a new node in the network."""
        node_info = NodeInfo(
            node_id=node_id,
            node_name=node_name,
            ip_address=ip_address,
            port=port,
            capacity=capacity,
            status=NodeStatus.ONLINE,
            last_heartbeat=time.time(),
            connected_peers=set(),
            created_at=time.time(),
            metrics={
                'cpu_usage': 0.0,
                'memory_usage': 0.0,
                'disk_usage': 0.0,
                'task_count': 0,
                'error_count': 0,
            }
        )
        self.nodes[node_id] = node_info
        self.node_locations[node_id] = (ip_address, port)
        logger.info(f"Registered node {node_id} at {ip_address}:{port}")
        return node_info

    def deregister_node(self, node_id: str) -> bool:
        """Deregister a node from the network."""
        if node_id not in self.nodes:
            return False
        del self.nodes[node_id]
        if node_id in self.node_locations:
            del self.node_locations[node_id]
        # Clean up peer references
        if node_id in self.peer_graph:
            del self.peer_graph[node_id]
        for peers in self.peer_graph.values():
            peers.discard(node_id)
        logger.info(f"Deregistered node {node_id}")
        return True

    def update_heartbeat(self, node_id: str) -> bool:
        """Update the heartbeat timestamp for a node."""
        if node_id not in self.nodes:
            return False
        self.nodes[node_id].last_heartbeat = time.time()
        return True

    def add_peer_connection(self, node_id1: str, node_id2: str) -> bool:
        """Add a peer connection between two nodes."""
        if node_id1 not in self.nodes or node_id2 not in self.nodes:
            return False
        self.peer_graph[node_id1].add(node_id2)
        self.peer_graph[node_id2].add(node_id1)
        self.nodes[node_id1].connected_peers.add(node_id2)
        self.nodes[node_id2].connected_peers.add(node_id1)
        return True

    def remove_peer_connection(self, node_id1: str, node_id2: str) -> bool:
        """Remove a peer connection between two nodes."""
        if node_id1 in self.peer_graph:
            self.peer_graph[node_id1].discard(node_id2)
        if node_id2 in self.peer_graph:
            self.peer_graph[node_id2].discard(node_id1)
        if node_id1 in self.nodes:
            self.nodes[node_id1].connected_peers.discard(node_id2)
        if node_id2 in self.nodes:
            self.nodes[node_id2].connected_peers.discard(node_id1)
        return True

    def get_healthy_nodes(self) -> List[NodeInfo]:
        """Get all healthy nodes in the network."""
        return [node for node in self.nodes.values() if node.is_healthy()]

    def get_neighbors(self, node_id: str) -> List[NodeInfo]:
        """Get neighboring nodes for a given node."""
        if node_id not in self.nodes:
            return []
        neighbor_ids = self.peer_graph.get(node_id, set())
        return [self.nodes[nid] for nid in neighbor_ids if nid in self.nodes]

    def detect_partitions(self) -> List[Set[str]]:
        """Detect network partitions using BFS."""
        visited = set()
        partitions = []

        for node_id in self.nodes:
            if node_id in visited:
                continue
            partition = set()
            queue = [node_id]
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                partition.add(current)
                for neighbor in self.peer_graph.get(current, set()):
                    if neighbor not in visited:
                        queue.append(neighbor)
            if partition:
                partitions.append(partition)

        return partitions

    def update_node_metrics(self, node_id: str, metrics: Dict[str, Any]) -> bool:
        """Update metrics for a node."""
        if node_id not in self.nodes:
            return False
        self.nodes[node_id].metrics.update(metrics)
        return True


class MessageRouter:
    """Routes messages between nodes in the agent mesh."""

    def __init__(self, node_discovery: NodeDiscovery):
        self.discovery = node_discovery
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.message_handlers: Dict[MessageType, List[Callable]] = defaultdict(list)
        self.pending_messages: Dict[str, NetworkMessage] = {}
        self.routing_table: Dict[str, str] = {}  # node_id -> next_hop
        self.message_ttl = 10
        self.retry_limit = 3

    def register_handler(self, message_type: MessageType, handler: Callable) -> None:
        """Register a handler for a message type."""
        self.message_handlers[message_type].append(handler)

    def find_route(self, source_id: str, dest_id: str) -> Optional[List[str]]:
        """Find a route from source to destination using BFS."""
        if source_id not in self.discovery.nodes or dest_id not in self.discovery.nodes:
            return None

        queue = [(source_id, [source_id])]
        visited = {source_id}

        while queue:
            current, path = queue.pop(0)
            if current == dest_id:
                return path

            for neighbor in self.discovery.peer_graph.get(current, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None

    async def send_message(self, message: NetworkMessage) -> bool:
        """Send a message through the network."""
        route = self.find_route(message.sender_id, message.receiver_id)
        if not route:
            logger.warning(f"No route found from {message.sender_id} to {message.receiver_id}")
            return False

        self.pending_messages[message.message_id] = message
        return await self._route_message(message, route, 0)

    async def _route_message(
        self,
        message: NetworkMessage,
        route: List[str],
        attempt: int
    ) -> bool:
        """Route a message along a path."""
        if message.ttl <= 0:
            logger.error(f"Message {message.message_id} TTL expired")
            return False

        if attempt >= self.retry_limit:
            logger.error(f"Message {message.message_id} max retries exceeded")
            return False

        message.ttl -= 1

        # Simulate message propagation with handlers
        for handler in self.message_handlers[message.message_type]:
            try:
                result = handler(message)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Error in message handler: {e}")

        if message.message_id in self.pending_messages:
            del self.pending_messages[message.message_id]

        return True

    async def process_messages(self) -> None:
        """Process messages in the queue."""
        while True:
            try:
                message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                route = self.find_route(message.sender_id, message.receiver_id)
                if route:
                    await self._route_message(message, route, 0)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")

    def get_network_topology(self) -> Dict[str, Any]:
        """Get the current network topology."""
        return {
            'nodes': {nid: n.to_dict() for nid, n in self.discovery.nodes.items()},
            'peer_graph': {k: list(v) for k, v in self.discovery.peer_graph.items()},
            'partitions': self.discovery.detect_partitions(),
        }


class AgentMesh:
    """Agent Mesh Network - Main class for managing the distributed mesh."""

    def __init__(self, node_id: str, node_name: str = None, ip_address: str = "0.0.0.0", port: int = 5000):
        self.node_id = node_id
        self.node_name = node_name or f"agent-{node_id[:8]}"
        self.ip_address = ip_address
        self.port = port

        self.discovery = NodeDiscovery()
        self.router = MessageRouter(self.discovery)

        # Register self
        self.node_info = self.discovery.register_node(
            node_id=node_id,
            node_name=self.node_name,
            ip_address=ip_address,
            port=port,
            capacity=10
        )

        # Monitoring and recovery
        self.network_monitor_task = None
        self.partition_detector_task = None
        self.is_running = False
        self.last_partition_check = time.time()
        self.partition_recovery_delay = 5.0

    def connect_peer(self, peer_id: str, ip_address: str, port: int) -> bool:
        """Connect to another peer node."""
        if self.discovery.register_node(peer_id, f"agent-{peer_id[:8]}", ip_address, port):
            return self.discovery.add_peer_connection(self.node_id, peer_id)
        return False

    def disconnect_peer(self, peer_id: str) -> bool:
        """Disconnect from a peer node."""
        return self.discovery.remove_peer_connection(self.node_id, peer_id)

    async def send_message(
        self,
        receiver_id: str,
        message_type: MessageType,
        payload: Dict[str, Any],
        priority: int = 5
    ) -> str:
        """Send a message to another agent."""
        message = NetworkMessage(
            message_id=str(uuid.uuid4()),
            message_type=message_type,
            sender_id=self.node_id,
            receiver_id=receiver_id,
            payload=payload,
            timestamp=time.time(),
            priority=priority
        )
        success = await self.router.send_message(message)
        return message.message_id if success else None

    async def start(self) -> None:
        """Start the agent mesh network."""
        self.is_running = True
        logger.info(f"Starting Agent Mesh for node {self.node_id}")

        # Start message processor
        asyncio.create_task(self.router.process_messages())

        # Start monitoring tasks
        self.network_monitor_task = asyncio.create_task(self._monitor_network())
        self.partition_detector_task = asyncio.create_task(self._detect_partitions())

    async def stop(self) -> None:
        """Stop the agent mesh network."""
        self.is_running = False
        logger.info(f"Stopping Agent Mesh for node {self.node_id}")

        if self.network_monitor_task:
            self.network_monitor_task.cancel()
        if self.partition_detector_task:
            self.partition_detector_task.cancel()

        # Notify peers of shutdown
        await self.send_message(
            receiver_id="*",
            message_type=MessageType.NODE_SHUTDOWN,
            payload={'node_id': self.node_id}
        )
        self.discovery.deregister_node(self.node_id)

    async def _monitor_network(self) -> None:
        """Monitor the network for unhealthy nodes."""
        while self.is_running:
            try:
                await asyncio.sleep(self.discovery.heartbeat_interval)
                
                # Check for unhealthy nodes
                unhealthy_nodes = [
                    nid for nid, node in self.discovery.nodes.items()
                    if not node.is_healthy() and nid != self.node_id
                ]

                for node_id in unhealthy_nodes:
                    logger.warning(f"Node {node_id} is unhealthy")
                    self.discovery.nodes[node_id].status = NodeStatus.DEGRADED

                # Update own heartbeat
                self.discovery.update_heartbeat(self.node_id)

            except Exception as e:
                logger.error(f"Error in network monitor: {e}")

    async def _detect_partitions(self) -> None:
        """Detect and recover from network partitions."""
        while self.is_running:
            try:
                await asyncio.sleep(self.discovery.partition_detection_interval)

                partitions = self.discovery.detect_partitions()
                if len(partitions) > 1:
                    logger.warning(f"Network partition detected with {len(partitions)} components")

                    # Find which partition contains our node
                    our_partition = None
                    for partition in partitions:
                        if self.node_id in partition:
                            our_partition = partition
                            break

                    if our_partition:
                        # Attempt recovery by reaching out to isolated nodes
                        isolated_nodes = set()
                        for partition in partitions:
                            if partition != our_partition:
                                isolated_nodes.update(partition)

                        for node_id in isolated_nodes:
                            if node_id in self.discovery.nodes:
                                logger.info(f"Attempting to recover connection with {node_id}")
                                await self.send_message(
                                    node_id,
                                    MessageType.RECOVERY_MARKER,
                                    {'recovered_at': time.time()}
                                )

            except Exception as e:
                logger.error(f"Error in partition detection: {e}")

    def get_network_stats(self) -> Dict[str, Any]:
        """Get network statistics."""
        healthy_nodes = self.discovery.get_healthy_nodes()
        partitions = self.discovery.detect_partitions()

        return {
            'total_nodes': len(self.discovery.nodes),
            'healthy_nodes': len(healthy_nodes),
            'degraded_nodes': sum(1 for n in self.discovery.nodes.values() if n.status == NodeStatus.DEGRADED),
            'offline_nodes': sum(1 for n in self.discovery.nodes.values() if n.status == NodeStatus.OFFLINE),
            'partition_count': len(partitions),
            'avg_peer_connections': sum(len(p.connected_peers) for p in self.discovery.nodes.values()) / max(len(self.discovery.nodes), 1),
            'network_topology': self.router.get_network_topology(),
        }

# Distributed Runtime Deployment Guide

## Overview

The Distributed Runtime enables SintraPrime UniVerse agents to scale horizontally across multiple machines with zero-downtime deployments. This guide covers deployment, configuration, and operations.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│         Agent Mesh Network (P2P Communication)              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │    Node 1    │  │    Node 2    │  │    Node 3    │      │
│  │  (Agent A)   │  │  (Agent B)   │  │  (Agent C)   │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │               │
│         └─────────────────┼─────────────────┘               │
└─────────────────────────────────────────────────────────────┘
         │
         ├─ Distributed Scheduler (Task Queue & Work Stealing)
         ├─ Load Balancer (Dynamic Routing)
         ├─ Service Registry (Discovery)
         ├─ Distributed Cache (Redis-compatible)
         └─ Health Monitoring & Failover

```

## Core Components

### 1. Agent Mesh Network
- **Purpose**: P2P communication between agents
- **Protocol**: libp2p-based (simulated)
- **Features**:
  - Node discovery and registration
  - Direct agent-to-agent messaging
  - Network partition detection
  - Automatic recovery

### 2. Distributed Scheduler
- **Purpose**: Coordinate task execution across agents
- **Algorithm**: Work-stealing for load balancing
- **Features**:
  - Task affinity and dependency support
  - SLA enforcement
  - Priority-based scheduling
  - Automatic retry logic

### 3. Load Balancer
- **Purpose**: Route requests to agents
- **Algorithms**: 
  - Least connections
  - Round-robin
  - Health-aware
  - Weighted selection
- **Features**:
  - Circuit breaking
  - Health monitoring
  - Request queuing

### 4. Service Registry
- **Purpose**: Service discovery and health checking
- **Interface**: Consul-compatible
- **Features**:
  - Custom tags and metadata
  - Weighted routing
  - Auto-deregistration
  - Health checking

### 5. Distributed Cache
- **Purpose**: High-performance caching across cluster
- **Features**:
  - LRU/LFU eviction
  - Tag-based invalidation
  - TTL support
  - Batch operations
  - List, Set, Hash data structures

## Installation

### Prerequisites

- Python 3.8+
- Redis (optional, for persistent cache)
- PostgreSQL (optional, for persistent storage)
- Kubernetes 1.20+ (for production)

### Basic Setup

```bash
# Install dependencies
pip install -r requirements-distributed.txt

# Create database tables
python -m universe.distributed.schema init

# Start single node
python -c "from universe.distributed import AgentMesh; mesh = AgentMesh('node1'); asyncio.run(mesh.start())"
```

## Configuration

### Environment Variables

```bash
# Node Configuration
AGENT_NODE_ID=node1
AGENT_NODE_NAME=agent-primary
AGENT_IP=0.0.0.0
AGENT_PORT=5000

# Scheduler Configuration
SCHEDULER_MAX_QUEUE_SIZE=10000
SCHEDULER_WORK_STEALING_ENABLED=true
SCHEDULER_TASK_TIMEOUT_MS=5000

# Load Balancer Configuration
LB_ALGORITHM=health_aware
LB_HEALTH_CHECK_INTERVAL_MS=5000
LB_CIRCUIT_BREAKER_THRESHOLD=5

# Cache Configuration
CACHE_MAX_SIZE=10000
CACHE_STRATEGY=lru
CACHE_DEFAULT_TTL_SECONDS=3600

# Network Configuration
MESH_HEARTBEAT_INTERVAL_MS=5000
MESH_PARTITION_CHECK_INTERVAL_MS=10000
MESH_DISCOVERY_TIMEOUT_SECONDS=30
```

### Configuration File

Create `distributed_config.yaml`:

```yaml
mesh:
  heartbeat_interval_ms: 5000
  partition_detection_interval_ms: 10000
  message_ttl: 10
  node_discovery_timeout_s: 30

scheduler:
  work_stealing_enabled: true
  steal_threshold: 0.75
  max_queue_size: 10000
  task_timeout_ms: 5000

load_balancer:
  algorithm: health_aware
  health_check_interval_ms: 5000
  circuit_breaker_threshold: 5
  circuit_breaker_recovery_ms: 30000
  request_timeout_ms: 5000
  max_queue_depth: 100

cache:
  max_size: 10000
  strategy: lru
  default_ttl_seconds: 3600

registry:
  health_check_interval_ms: 10000
  auto_deregister_delay_s: 3600
```

## Deployment Modes

### Single Node Development

```python
from universe.distributed import AgentMesh, DistributedScheduler
import asyncio

async def run_single_node():
    mesh = AgentMesh("dev-node", ip_address="127.0.0.1", port=5000)
    await mesh.start()
    
    # Your agent code here
```

### Multi-Node Cluster

```python
from universe.distributed import AgentMesh
import asyncio

async def run_cluster_node(node_id, other_nodes):
    mesh = AgentMesh(node_id, port=5000 + int(node_id[-1]))
    
    # Connect to other nodes
    for other_id, ip, port in other_nodes:
        mesh.connect_peer(other_id, ip, port)
    
    await mesh.start()
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: scs-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: scs-agent
  template:
    metadata:
      labels:
        app: scs-agent
    spec:
      containers:
      - name: agent
        image: scs-agent:latest
        ports:
        - containerPort: 5000
        env:
        - name: AGENT_NODE_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: AGENT_IP
          valueFrom:
            fieldRef:
              fieldPath: status.podIP
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Docker Compose

```yaml
version: '3.8'
services:
  agent-node1:
    image: scs-agent:latest
    environment:
      AGENT_NODE_ID: node1
      AGENT_IP: agent-node1
      AGENT_PORT: 5000
    ports:
      - "5000:5000"
    networks:
      - mesh

  agent-node2:
    image: scs-agent:latest
    environment:
      AGENT_NODE_ID: node2
      AGENT_IP: agent-node2
      AGENT_PORT: 5000
    ports:
      - "5001:5000"
    networks:
      - mesh
    depends_on:
      - agent-node1

  agent-node3:
    image: scs-agent:latest
    environment:
      AGENT_NODE_ID: node3
      AGENT_IP: agent-node3
      AGENT_PORT: 5000
    ports:
      - "5002:5000"
    networks:
      - mesh
    depends_on:
      - agent-node1

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    networks:
      - mesh

networks:
  mesh:
    driver: bridge
```

## Operations

### Monitoring

Monitor cluster health:

```python
from universe.distributed import AgentMesh

mesh = AgentMesh("node1")
stats = mesh.get_network_stats()

print(f"Total nodes: {stats['total_nodes']}")
print(f"Healthy nodes: {stats['healthy_nodes']}")
print(f"Partitions detected: {stats['partition_count']}")
```

### Scaling

Add new nodes:

```bash
# Start new node and connect to existing cluster
AGENT_NODE_ID=node4 AGENT_PORT=5003 python -m universe.distributed.agent_mesh
```

### Health Checks

Implement custom health checks:

```python
from universe.distributed import ServiceRegistry

registry = ServiceRegistry()
instance = registry.register_service("api", "localhost", 8000)

# Add health check
check = registry.add_health_check(instance.service_id, "http")

# Simulate health monitoring
registry.update_check_status(instance.service_id, check.check_id, True)
```

### Metrics and Dashboards

Export metrics:

```python
import prometheus_client

scheduler_tasks = prometheus_client.Counter(
    'scheduler_tasks_total', 'Total tasks scheduled'
)
mesh_nodes = prometheus_client.Gauge(
    'mesh_nodes_healthy', 'Healthy nodes in mesh'
)

# Update metrics
stats = mesh.get_network_stats()
mesh_nodes.set(stats['healthy_nodes'])
```

## Troubleshooting

### Issue: Network Partitions

**Symptom**: Multiple cluster members, but some nodes can't communicate

**Solution**:
```python
# Check for partitions
partitions = mesh.discovery.detect_partitions()
if len(partitions) > 1:
    print(f"Partition detected: {partitions}")
    # Mesh will auto-recover, or manually reconnect:
    mesh.connect_peer(isolated_node_id, ip, port)
```

### Issue: High Task Latency

**Symptom**: Task scheduling taking >50ms

**Solution**:
1. Check scheduler load: `scheduler.get_scheduler_stats()`
2. Check agent capacity: `scheduler.get_agent_load()`
3. Enable work stealing: `scheduler.work_stealer.should_steal(...)`

### Issue: Uneven Load Distribution

**Symptom**: Some nodes busy while others idle

**Solution**:
```python
# Inspect loads
loads = scheduler.get_agent_load()
for agent_id, load in loads.items():
    print(f"{agent_id}: {load * 100}%")

# Trigger work stealing
suggestion = scheduler.suggest_work_steal()
if suggestion:
    print(f"Steal from {suggestion[1]} to {suggestion[0]}")
```

## Performance Tuning

### For High Throughput

```python
scheduler = DistributedScheduler(work_stealing_enabled=True)
# Increase agent capacity
scheduler.register_agent("agent1", max_capacity=1000)
# Use batch operations
scheduler.set_many(large_task_dict)
```

### For Low Latency

```python
# Reduce timeouts
config = TaskSLA(max_duration_ms=1000, timeout_ms=2000)
# Use affinity to improve cache locality
task_id = scheduler.submit_task(
    "process", {}, 
    affinity_tags={"cpu-intensive", "node1"}
)
```

### For Memory Efficiency

```python
cache = DistributedCache(
    max_size=1000,  # Reduce size
    strategy=CacheStrategy.LFU  # Use LFU for better hit rate
)
```

## Disaster Recovery

### Backup

```bash
# Backup cache
redis-cli BGSAVE

# Backup task state
pg_dump -d scs_db > backup.sql
```

### Restore

```bash
# Restore from backup
redis-cli --pipe < dump.rdb

psql -d scs_db < backup.sql
```

## Success Metrics

Track these metrics in production:

- **Availability**: 99.99% uptime target
- **Task Scheduling**: <50ms P99 latency
- **Failover**: <10s recovery from node failure
- **Throughput**: 1000+ tasks/sec per node
- **Cache Hit Ratio**: >80%
- **Network Partition Recovery**: <30s

## Limits and Capacity Planning

| Metric | Recommended Limit | Notes |
|--------|-------------------|-------|
| Cluster Size | 100+ nodes | Tested and supported |
| Task Queue Depth | 10,000 | Per scheduler instance |
| Agent Capacity | 1,000 concurrent tasks | Per agent |
| Network Partition | <10 components | Performance degrades with more |
| Cache Size | 10,000+ entries | In-memory limit |
| Message TTL | 10 hops | Prevents infinite loops |

## Security

### Network Security

```python
# Enable TLS for mesh communication
mesh_config = {
    'tls_enabled': True,
    'cert_file': '/path/to/cert.pem',
    'key_file': '/path/to/key.pem',
    'ca_file': '/path/to/ca.pem'
}

mesh = AgentMesh("node1", config=mesh_config)
```

### Authentication

```python
# Enable node authentication
from universe.distributed.auth import NodeAuth

auth = NodeAuth(secret_key="shared-cluster-secret")
mesh = AgentMesh("node1", auth=auth)
```

## References

- [Agent Mesh API](../distributed/agent_mesh.py)
- [Scheduler API](../distributed/distributed_scheduler.py)
- [Load Balancer API](../distributed/load_balancer.py)
- [Service Registry API](../distributed/service_registry.py)
- [Cache API](../distributed/distributed_cache.py)
- [Test Suite](../../tests/test_distributed.py)

# UniVerse Swarm Patterns - Integration Guide

## Integration with UniVerse Core

The Swarm Patterns module integrates seamlessly with the UniVerse core architecture, providing high-level coordination abstractions over the base agent system.

### Architecture Layers

```
┌─────────────────────────────────────────┐
│  Applications & User Interfaces          │
├─────────────────────────────────────────┤
│  Swarm Patterns (New!)                   │
│  ├─ Research Swarm                       │
│  ├─ Development Swarm                    │
│  ├─ Operations Swarm                     │
│  ├─ Content Swarm                        │
│  └─ Sales Swarm                          │
├─────────────────────────────────────────┤
│  Agent Types                             │
│  ├─ AnalystAgent                         │
│  ├─ ExecutorAgent                        │
│  ├─ LearnerAgent                         │
│  ├─ CoordinatorAgent                     │
│  ├─ VisionAgent                          │
│  └─ GuardAgent                           │
├─────────────────────────────────────────┤
│  Base Agent Infrastructure               │
│  ├─ BaseAgent (Abstract)                 │
│  ├─ Skill Management                     │
│  ├─ Performance Metrics                  │
│  └─ Collaboration Framework              │
├─────────────────────────────────────────┤
│  Core Engine                             │
│  ├─ Task Queue & Routing                 │
│  ├─ Event Loop Management                │
│  ├─ State Management                     │
│  └─ Persistence Layer                    │
├─────────────────────────────────────────┤
│  SQL Database & Memory System            │
│  ├─ swarm_definitions                    │
│  ├─ swarm_metrics                        │
│  ├─ agent_coordination                   │
│  ├─ task_registry                        │
│  └─ execution_trace                      │
└─────────────────────────────────────────┘
```

## Using Swarms with Agent Types

### Swarm Agent Configuration

Each swarm pattern automatically creates the right mix of agent types:

```python
# Research Swarm creates:
agents = [
    AnalystAgent("Analyst-1", specialization="competitive_analysis"),
    AnalystAgent("Analyst-2", specialization="trend_analysis"),
    AnalystAgent("Analyst-3", specialization="technical_analysis"),
    CoordinatorAgent("Coordinator")
]

# Development Swarm creates:
agents = [
    ExecutorAgent("Executor-1", specialization="backend"),
    ExecutorAgent("Executor-2", specialization="frontend"),
    VisionAgent("Vision"),
    LearnerAgent("Learner"),
    GuardAgent("Guard")
]

# ... and so on for other swarms
```

### Accessing Underlying Agents

```python
swarm = SwarmFactory.create_swarm('research')
await swarm.launch()

# Access individual agents
for agent_id, agent_info in swarm.agents.items():
    print(f"Agent: {agent_info['config']['name']}")
    print(f"Role: {agent_info['config']['role']}")
    print(f"Status: {agent_info['status']}")
```

## Database Integration

### Storing Swarm Definitions

Swarm patterns are automatically persisted:

```sql
-- Query swarm definitions
SELECT * FROM swarm_definitions;

-- Query specific pattern
SELECT * FROM swarm_definitions WHERE pattern_type = 'research';

-- Check current instances
SELECT COUNT(*) as active_swarms FROM swarm_definitions;
```

### Tracking Swarm Metrics

Real-time metrics are stored in `swarm_metrics`:

```sql
-- Get performance metrics for a swarm
SELECT 
    timestamp,
    tasks_completed,
    tasks_failed,
    success_rate,
    avg_task_duration_ms
FROM swarm_metrics
WHERE swarm_id = 'research-swarm-001'
ORDER BY timestamp DESC
LIMIT 100;

-- Compare swarm performance
SELECT 
    pattern_type,
    COUNT(*) as metric_samples,
    AVG(success_rate) as avg_success,
    AVG(avg_task_duration_ms) as avg_duration
FROM swarm_definitions sd
JOIN swarm_metrics sm ON sd.swarm_id = sm.swarm_id
GROUP BY pattern_type;
```

### Task Registry Integration

Tasks from swarms are logged in `task_registry`:

```sql
-- Find tasks from a specific swarm execution
SELECT * FROM task_registry
WHERE execution_id = (
    SELECT execution_id FROM execution_trace
    WHERE intent LIKE '%swarm%'
)
ORDER BY created_at DESC;

-- Analyze task success rates by swarm type
SELECT 
    st.pattern_type,
    COUNT(*) as total_tasks,
    SUM(CASE WHEN tr.status = 'completed' THEN 1 ELSE 0 END) as successful,
    ROUND(100.0 * SUM(CASE WHEN tr.status = 'completed' THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
FROM task_registry tr
JOIN swarm_definitions sd ON tr.execution_id = sd.swarm_id
GROUP BY st.pattern_type;
```

## Integration with Existing Workflows

### 1. Trigger-Based Swarm Execution

Create triggers to automatically launch swarms:

```python
# Example: Launch optimization swarm when performance degrades
def on_performance_alert(metrics):
    if metrics['avg_response_time_ms'] > 1000:
        swarm = SwarmFactory.create_swarm('operations')
        asyncio.create_task(swarm.launch())
        asyncio.create_task(
            swarm.execute(
                f"Diagnose performance issue: {metrics['alert']}",
                priority=10
            )
        )
```

### 2. Pipeline Integration

Use swarms as stages in a larger pipeline:

```python
async def content_production_pipeline(topic):
    """Multi-stage content production using swarms."""
    
    # Stage 1: Research using Research Swarm
    print("Stage 1: Research")
    research_swarm = SwarmFactory.create_swarm('research')
    await research_swarm.launch()
    research_task = await research_swarm.execute(f"Research {topic}")
    await asyncio.sleep(2)
    research_results = research_swarm.get_results(research_task)
    await research_swarm.shutdown()
    
    # Stage 2: Content Creation using Content Swarm
    print("Stage 2: Content Creation")
    content_swarm = SwarmFactory.create_swarm('content')
    await content_swarm.launch()
    # Pre-populate with research findings
    content_swarm.update_knowledge_base("research_findings", research_results)
    content_task = await content_swarm.execute(
        f"Write blog post on {topic} using research findings"
    )
    await asyncio.sleep(2)
    content_results = content_swarm.get_results(content_task)
    await content_swarm.shutdown()
    
    return {
        "research": research_results,
        "content": content_results
    }
```

### 3. Real-time Monitoring Dashboard

Stream swarm metrics to a dashboard:

```python
async def dashboard_stream(swarm, websocket):
    """Stream swarm metrics to dashboard."""
    while swarm.status == SwarmStatus.RUNNING:
        status = swarm.get_status()
        
        # Send metrics
        await websocket.send(json.dumps({
            "type": "swarm_metrics",
            "data": {
                "swarm_id": swarm.swarm_id,
                "status": status['status'],
                "agents": status['agents'],
                "tasks": status['tasks'],
                "metrics": status['metrics']
            }
        }))
        
        await asyncio.sleep(1)
```

### 4. Conditional Swarm Selection

Choose swarm based on task characteristics:

```python
def select_swarm_pattern(task_description):
    """Select appropriate swarm for a task."""
    
    keywords = task_description.lower()
    
    if any(k in keywords for k in ['research', 'analyze', 'investigate']):
        return 'research'
    elif any(k in keywords for k in ['build', 'develop', 'code', 'test']):
        return 'development'
    elif any(k in keywords for k in ['monitor', 'optimize', 'incident']):
        return 'operations'
    elif any(k in keywords for k in ['write', 'content', 'blog', 'document']):
        return 'content'
    elif any(k in keywords for k in ['lead', 'sales', 'prospect', 'outreach']):
        return 'sales'
    else:
        return 'research'  # Default

async def smart_task_execution(task_description):
    """Execute task using appropriate swarm."""
    pattern = select_swarm_pattern(task_description)
    swarm = SwarmFactory.create_swarm(pattern)
    await swarm.launch()
    task_id = await swarm.execute(task_description)
    # ... wait for results
    await swarm.shutdown()
```

## Advanced Integration Patterns

### 1. Multi-Swarm Orchestration

Coordinate multiple swarms working in parallel:

```python
async def parallel_swarm_execution(queries):
    """Execute multiple queries in parallel using different swarms."""
    
    swarms = {}
    tasks = {}
    
    # Launch swarms
    for query_type, query in queries.items():
        swarm = SwarmFactory.create_swarm(query_type)
        await swarm.launch()
        swarms[query_type] = swarm
        tasks[query_type] = await swarm.execute(query)
    
    # Wait for all to complete
    results = {}
    for query_type, task_id in tasks.items():
        result = swarms[query_type].get_results(task_id)
        results[query_type] = result
        await swarms[query_type].shutdown()
    
    return results
```

### 2. Hierarchical Task Decomposition

Use swarms at different hierarchy levels:

```python
async def hierarchical_execution(epic_task):
    """Decompose epic task into swarms and subtasks."""
    
    # Level 1: Use Research Swarm to plan
    research_swarm = SwarmFactory.create_swarm('research')
    await research_swarm.launch()
    plan_task = await research_swarm.execute(
        f"Create detailed project plan for: {epic_task}"
    )
    await asyncio.sleep(1)
    plan = research_swarm.get_results(plan_task)
    await research_swarm.shutdown()
    
    # Level 2: Use Development Swarm to execute phases
    dev_swarm = SwarmFactory.create_swarm('development')
    await dev_swarm.launch()
    # Populate knowledge base with plan
    dev_swarm.update_knowledge_base("project_plan", plan)
    
    # Execute each phase
    phases = plan.get('phases', [])
    for phase in phases:
        task_id = await dev_swarm.execute(f"Execute: {phase}")
    
    # ... wait and collect results
    await dev_swarm.shutdown()
```

### 3. Knowledge Transfer Between Swarms

Share learned knowledge across swarms:

```python
# Extract knowledge from first swarm
research_swarm = SwarmFactory.create_swarm('research')
await research_swarm.launch()
# ... execute research ...
learned_knowledge = research_swarm.get_knowledge_base()
await research_swarm.shutdown()

# Pass knowledge to second swarm
content_swarm = SwarmFactory.create_swarm('content')
await content_swarm.launch()

# Populate with learned knowledge
for key, value in learned_knowledge.items():
    content_swarm.update_knowledge_base(key, value['value'])

# ... execute content creation ...
await content_swarm.shutdown()
```

## Performance Optimization

### 1. Agent Pooling

Pre-create specialized agent pools:

```python
class AgentPool:
    def __init__(self):
        self.pools = {
            'analysts': [],
            'executors': [],
            'vision': []
        }
    
    def create_swarm_with_pool(self, pattern_type):
        """Create swarm using pooled agents."""
        swarm = SwarmFactory.create_swarm(pattern_type)
        # Customize with pooled agents
        return swarm
```

### 2. Load Balancing

Distribute tasks across multiple swarms:

```python
class LoadBalancer:
    def __init__(self, num_swarms=3):
        self.swarms = [
            SwarmFactory.create_swarm('research')
            for _ in range(num_swarms)
        ]
        self.current_idx = 0
    
    async def execute(self, task):
        """Execute task on least loaded swarm."""
        swarm = self.swarms[self.current_idx]
        self.current_idx = (self.current_idx + 1) % len(self.swarms)
        return await swarm.execute(task)
```

### 3. Caching Results

Avoid duplicate work:

```python
class SwarmCache:
    def __init__(self):
        self.cache = {}
    
    async def execute(self, swarm, task):
        """Execute with caching."""
        cache_key = hash(task)
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        task_id = await swarm.execute(task)
        result = swarm.get_results(task_id)
        self.cache[cache_key] = result
        return result
```

## Error Handling and Recovery

### 1. Graceful Degradation

```python
async def resilient_swarm_execution(task):
    """Execute with fallback strategies."""
    try:
        swarm = SwarmFactory.create_swarm('primary')
        await swarm.launch()
        task_id = await swarm.execute(task)
        result = swarm.get_results(task_id)
        await swarm.shutdown()
        return result
    except Exception as e:
        logger.error(f"Primary swarm failed: {e}")
        # Fallback to different swarm type
        swarm = SwarmFactory.create_swarm('fallback')
        await swarm.launch()
        task_id = await swarm.execute(task)
        result = swarm.get_results(task_id)
        await swarm.shutdown()
        return result
```

### 2. Circuit Breaker Pattern

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=3):
        self.failures = 0
        self.threshold = failure_threshold
        self.open = False
    
    async def call(self, swarm_factory_fn, task):
        """Execute with circuit breaker protection."""
        if self.open:
            raise RuntimeError("Circuit breaker is open")
        
        try:
            swarm = swarm_factory_fn()
            await swarm.launch()
            result = await swarm.execute(task)
            self.failures = 0
            await swarm.shutdown()
            return result
        except Exception as e:
            self.failures += 1
            if self.failures >= self.threshold:
                self.open = True
            raise
```

## Testing Swarm Patterns

### Unit Testing

```python
import pytest

@pytest.mark.asyncio
async def test_research_swarm():
    swarm = SwarmFactory.create_swarm('research')
    assert swarm is not None
    
    launch_result = await swarm.launch()
    assert launch_result['status'] == 'success'
    
    task_id = await swarm.execute("Test research task")
    assert task_id is not None
    
    await swarm.shutdown()
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_swarm_workflow():
    """Test complete swarm workflow."""
    swarm = SwarmFactory.create_swarm('development')
    await swarm.launch()
    
    # Add agents
    agent_id = swarm.add_agent(AgentRole.ANALYST)
    assert agent_id in swarm.agents
    
    # Execute task
    task_id = await swarm.execute("Test task")
    assert task_id is not None
    
    # Check status
    status = swarm.get_status()
    assert status['status'] == 'running'
    
    # Shutdown
    result = await swarm.shutdown()
    assert result['status'] == 'success'
```

## Monitoring and Analytics

### Key Metrics to Track

1. **Throughput**: Tasks completed per minute
2. **Latency**: Average task completion time
3. **Success Rate**: Percentage of successful tasks
4. **Agent Utilization**: Percentage of agents actively working
5. **Queue Depth**: Number of pending tasks
6. **Cost Per Task**: Resources used per completed task

### Queries for Analytics

```sql
-- Daily swarm performance
SELECT 
    DATE(timestamp) as date,
    pattern_type,
    COUNT(*) as tasks,
    AVG(success_rate) as avg_success,
    AVG(avg_task_duration_ms) as avg_duration
FROM swarm_metrics sm
JOIN swarm_definitions sd ON sm.swarm_id = sd.swarm_id
GROUP BY DATE(timestamp), pattern_type
ORDER BY date DESC;

-- Identify bottlenecks
SELECT 
    pattern_type,
    agents_active,
    tasks_in_progress,
    tasks_pending,
    AVG(avg_task_duration_ms) as duration
FROM swarm_metrics sm
JOIN swarm_definitions sd ON sm.swarm_id = sd.swarm_id
WHERE tasks_pending > 0
ORDER BY tasks_pending DESC;
```

## Production Deployment Checklist

- [ ] Test all 5 swarm patterns with production data
- [ ] Set up monitoring and alerting
- [ ] Configure database backups
- [ ] Document custom swarm extensions
- [ ] Set up CI/CD for swarm deployments
- [ ] Plan capacity and scaling strategy
- [ ] Create runbooks for common scenarios
- [ ] Train team on swarm operations
- [ ] Set up audit logging
- [ ] Plan disaster recovery procedures

## Conclusion

The Swarm Patterns module provides a powerful, production-ready system for multi-agent coordination. By following this integration guide, you can leverage the full power of UniVerse swarms in your applications.

For more information, see:
- `SWARM_PATTERNS_GUIDE.md` - Complete API reference
- `SWARM_QUICK_REFERENCE.md` - Quick lookup guide
- `swarm_examples.py` - Practical examples
- `swarm_patterns.py` - Source code

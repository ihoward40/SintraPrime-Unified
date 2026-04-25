# UniVerse Swarm Patterns - Quick Reference

## Create and Launch a Swarm

```python
from swarm_patterns import SwarmFactory

# Create a swarm
swarm = SwarmFactory.create_swarm('research')  # Options: research, development, operations, content, sales

# Launch it
await swarm.launch()
```

## Submit a Task

```python
task_id = await swarm.execute(
    task_description="Your task here",
    priority=5  # 1-10, higher is more urgent
)
```

## Check Status

```python
status = swarm.get_status()
print(f"Agents: {status['agents']}")
print(f"Tasks: {status['tasks']}")
print(f"Metrics: {status['metrics']}")
```

## Get Results

```python
# Get specific task result
result = swarm.get_results(task_id)

# Get all results
all_results = swarm.get_results()
```

## Shutdown

```python
await swarm.shutdown()
```

---

## Swarm Patterns Cheat Sheet

### Research Swarm
```
Purpose: Research across multiple sources
Agents: 3 Analysts + 1 Coordinator
Best for: Market research, competitive analysis, technical deep dives
Example: await swarm.execute("Research AI frameworks and compare")
```

### Development Swarm
```
Purpose: Code development with security
Agents: 2 Executors + 1 Vision + 1 Learner + 1 Guard
Best for: Building features, code review, security checks
Example: await swarm.execute("Build login form with validation")
```

### Operations Swarm
```
Purpose: Monitoring and incident response
Agents: 1 Analyst + 2 Executors + 1 Coordinator + 1 Guard
Best for: Infrastructure, monitoring, optimization
Example: await swarm.execute("Detect and fix performance issues")
```

### Content Swarm
```
Purpose: Writing and publishing
Agents: 2 Executors + 1 Vision + 1 Learner
Best for: Blog posts, documentation, marketing content
Example: await swarm.execute("Write SEO-optimized blog post")
```

### Sales Swarm
```
Purpose: Lead research and outreach
Agents: 2 Analysts + 1 Executor + 1 Vision + 1 Coordinator
Best for: Lead generation, sales research, outreach
Example: await swarm.execute("Find 20 qualified leads in Tech sector")
```

---

## Dynamic Agent Management

### Add an Agent
```python
new_agent_id = swarm.add_agent(
    role=AgentRole.ANALYST,
    specialization="market_analysis"
)
```

### Remove an Agent
```python
swarm.remove_agent(agent_id)
```

---

## Knowledge Base

### Store Knowledge
```python
swarm.update_knowledge_base("key", {
    "data": "value",
    "timestamp": "2026-04-21"
})
```

### Retrieve Knowledge
```python
knowledge = swarm.get_knowledge_base("key")
all_knowledge = swarm.get_knowledge_base()  # All keys
```

---

## Database Queries

### List All Swarm Definitions
```python
from run_agent_memory_sql import run_agent_memory_sql

swarms = run_agent_memory_sql("""
    SELECT swarm_id, pattern_type, name, agent_count, max_agents
    FROM swarm_definitions
""")
```

### Get Swarm Metrics
```python
metrics = run_agent_memory_sql("""
    SELECT * FROM swarm_metrics
    WHERE swarm_id = ?
    ORDER BY timestamp DESC
    LIMIT 10
""", [swarm_id])
```

---

## Status Codes

### Swarm Status
- `idle`: Not running
- `initializing`: Starting up
- `running`: Actively processing tasks
- `paused`: Temporarily paused
- `completed`: Finished all tasks
- `failed`: Encountered critical error
- `shutdown`: Cleanly shut down

### Task Status
- `pending`: Waiting to be assigned
- `assigned`: Assigned to an agent
- `completed`: Finished successfully
- `failed`: Failed after retries

### Agent Status
- `idle`: Ready for new tasks
- `working`: Currently executing a task

---

## Performance Metrics

```python
status = swarm.get_status()
metrics = status['metrics']

print(f"Success Rate: {metrics['success_rate']:.1%}")
print(f"Avg Duration: {metrics['avg_task_duration_ms']:.0f}ms")
print(f"Tasks Completed: {metrics['tasks_completed']}")
print(f"Tasks Failed: {metrics['tasks_failed']}")
print(f"Active Agents: {metrics['agents_active']}")
```

---

## Error Handling

```python
try:
    swarm = SwarmFactory.create_swarm('research')
    await swarm.launch()
    task_id = await swarm.execute("Task description")
    
    # Poll for completion
    while True:
        result = swarm.get_results(task_id)
        if result['status'] in ['completed', 'failed']:
            break
        await asyncio.sleep(1)
        
except Exception as e:
    print(f"Error: {e}")
finally:
    await swarm.shutdown()
```

---

## Common Tasks

### Research Competitive Landscape
```python
swarm = SwarmFactory.create_swarm('research')
await swarm.launch()
task_id = await swarm.execute(
    "Research 5 competing AI agent platforms and compare features",
    priority=8
)
# ... wait for results
```

### Build a New Feature
```python
swarm = SwarmFactory.create_swarm('development')
await swarm.launch()
task_id = await swarm.execute(
    "Build user authentication with 2FA support and full test coverage",
    priority=9
)
# ... wait for results
```

### Optimize Performance
```python
swarm = SwarmFactory.create_swarm('operations')
await swarm.launch()
task_id = await swarm.execute(
    "Identify database queries taking >100ms and optimize them",
    priority=10
)
# ... wait for results
```

### Create Marketing Content
```python
swarm = SwarmFactory.create_swarm('content')
await swarm.launch()
task_id = await swarm.execute(
    "Write a 2000-word blog post on AI agents with SEO optimization",
    priority=7
)
# ... wait for results
```

### Generate Sales Leads
```python
swarm = SwarmFactory.create_swarm('sales')
await swarm.launch()
task_id = await swarm.execute(
    "Find 20 qualified enterprise software companies and create outreach list",
    priority=8
)
# ... wait for results
```

---

## Complete Example

```python
import asyncio
from swarm_patterns import SwarmFactory, AgentRole

async def main():
    # Create swarm
    swarm = SwarmFactory.create_swarm('research')
    
    # Launch
    launch_result = await swarm.launch()
    print(f"✓ Swarm launched: {launch_result['swarm_name']}")
    
    # Add extra agents
    for i in range(2):
        agent_id = swarm.add_agent(
            role=AgentRole.ANALYST,
            specialization="research"
        )
        print(f"✓ Added agent: {agent_id}")
    
    # Execute task
    task_id = await swarm.execute(
        "Compare top 5 AI agent frameworks",
        priority=8
    )
    print(f"✓ Task submitted: {task_id}")
    
    # Monitor progress
    for _ in range(10):
        status = swarm.get_status()
        print(f"  Tasks: {status['tasks']['completed']} done, "
              f"{status['tasks']['in_progress']} in progress")
        await asyncio.sleep(1)
    
    # Get results
    result = swarm.get_results(task_id)
    print(f"✓ Result: {result}")
    
    # Shutdown
    shutdown = await swarm.shutdown()
    print(f"✓ Shutdown: {shutdown['tasks_completed']} tasks completed")

asyncio.run(main())
```

---

## Reference Links

- **Full Documentation**: See `SWARM_PATTERNS_GUIDE.md`
- **Implementation**: See `swarm_patterns.py`
- **Agent Types**: See `agent_types.py`
- **Base Architecture**: See `base_agent.py`

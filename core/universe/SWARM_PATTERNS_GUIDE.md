# UniVerse Swarm Patterns Guide

## Overview

Swarm Patterns are pre-configured, production-ready templates for coordinating multiple AI agents to work together on complex tasks. Each pattern is optimized for a specific use case and includes built-in support for:

- **Quick Launch**: Start a swarm with a single command
- **Custom Configuration**: Adjust agent count, model, tools, and parameters
- **Real-time Monitoring**: Stream progress and metrics to a dashboard
- **Graceful Fallback**: Automatically retry or reassign tasks if agents fail
- **Auto-Scaling**: Dynamically add more agents based on task queue depth
- **Knowledge Sharing**: All agents access a shared knowledge base

## 5 Pre-Configured Swarm Patterns

### 1. Research Swarm

**Purpose**: Parallel research across multiple sources

**Composition**: 3 Analyst Agents + 1 Coordinator

**Key Features**:
- Decompose research questions into 3 specialized subtopics
- Analysts research in parallel from different sources (web, databases, academic)
- Results synthesized into unified report
- Cross-references validated

**Specializations**:
- `competitive_analysis` - Analyze competitors and market landscape
- `trend_analysis` - Identify emerging trends and patterns
- `technical_analysis` - Deep technical research and benchmarking

**Example Use Cases**:
- "Research AI agent frameworks and compare feature sets"
- "Analyze competitor products in the market"
- "Study technical trends in machine learning"

**Quick Start**:
```python
research_swarm = SwarmFactory.create_swarm('research')
await research_swarm.launch()
task_id = await research_swarm.execute(
    "Research competitive AI agents and summarize key features",
    priority=8
)
status = research_swarm.get_status()
results = research_swarm.get_results(task_id)
await research_swarm.shutdown()
```

---

### 2. Development Swarm

**Purpose**: Code review, refactoring, testing

**Composition**: 2 Executor Agents + 1 Vision Agent + 1 Learner + 1 Guard

**Key Features**:
- Executor agents write code (backend and frontend)
- Vision Agent validates UI/design and accessibility
- Guard Agent checks security vulnerabilities and compliance
- Learner Agent extracts patterns and generates reusable components

**Specializations**:
- `backend` - Server-side code implementation
- `frontend` - Client-side code implementation
- `ui_validation` - Visual and UX validation
- `security_audit` - Security and compliance checks

**Example Use Cases**:
- "Build login form with password strength validation"
- "Refactor legacy authentication module"
- "Implement new REST API endpoint with tests"

**Quick Start**:
```python
dev_swarm = SwarmFactory.create_swarm('development')
await dev_swarm.launch()
task_id = await dev_swarm.execute(
    "Build secure login form with validation",
    priority=9
)
status = dev_swarm.get_status()
results = dev_swarm.get_results(task_id)
await dev_swarm.shutdown()
```

---

### 3. Operations Swarm

**Purpose**: Monitoring, incident response, optimization

**Composition**: 1 Analyst + 2 Executor + 1 Coordinator + 1 Guard

**Key Features**:
- Analyst continuously monitors metrics and detects anomalies
- Executors handle incidents in parallel (diagnosis + remediation)
- Coordinator manages priorities and escalations
- Guard logs all activities for compliance and audit

**Specializations**:
- `metrics_monitoring` - Real-time metrics collection and analysis
- `incident_response` - Emergency response and diagnostics
- `optimization` - Performance tuning and improvements

**Example Use Cases**:
- "Detect performance bottlenecks and optimize"
- "Monitor system health and respond to alerts"
- "Diagnose and fix recurring issues"

**Quick Start**:
```python
ops_swarm = SwarmFactory.create_swarm('operations')
await ops_swarm.launch()
task_id = await ops_swarm.execute(
    "Detect performance bottlenecks and optimize",
    priority=10
)
status = ops_swarm.get_status()
results = ops_swarm.get_results(task_id)
await ops_swarm.shutdown()
```

---

### 4. Content Swarm

**Purpose**: Writing, editing, publishing, analytics

**Composition**: 2 Executor Agents + 1 Vision Agent + 1 Learner

**Key Features**:
- Executor agents write different sections in parallel
- Vision Agent designs layout, generates images, ensures visual coherence
- Learner Agent analyzes writing style and extracts patterns
- Results merged for publication with SEO optimization

**Specializations**:
- `content_creation` - Original content writing
- `editing` - Proofreading and fact-checking
- `visual_design` - Layout and image generation

**Example Use Cases**:
- "Write comprehensive blog post with SEO optimization and visuals"
- "Create marketing collateral with consistent branding"
- "Produce technical documentation with diagrams"

**Quick Start**:
```python
content_swarm = SwarmFactory.create_swarm('content')
await content_swarm.launch()
task_id = await content_swarm.execute(
    "Write blog post about AI agents with visuals",
    priority=7
)
status = content_swarm.get_status()
results = content_swarm.get_results(task_id)
await content_swarm.shutdown()
```

---

### 5. Sales Swarm

**Purpose**: Lead research, outreach, deal tracking

**Composition**: 2 Analyst + 1 Executor + 1 Vision + 1 Coordinator

**Key Features**:
- Analysts research leads in parallel (firmographic + technology analysis)
- Vision Agent analyzes company websites and brand positioning
- Executor crafts personalized outreach messages
- Coordinator tracks interactions and manages deal pipeline

**Specializations**:
- `lead_research` - Target company identification
- `firmographic_analysis` - Company data analysis and qualification
- `personalization` - Custom outreach message generation
- `brand_analysis` - Website and brand analysis

**Example Use Cases**:
- "Find 20 qualified leads in our target market and create outreach list"
- "Analyze prospect companies and prepare personalized pitches"
- "Research decision-makers and create targeted campaigns"

**Quick Start**:
```python
sales_swarm = SwarmFactory.create_swarm('sales')
await sales_swarm.launch()
task_id = await sales_swarm.execute(
    "Find 20 qualified leads in AI/ML space",
    priority=8
)
status = sales_swarm.get_status()
results = sales_swarm.get_results(task_id)
await sales_swarm.shutdown()
```

---

## Core SwarmPattern Methods

### `launch(**config_overrides) -> Dict[str, Any]`

Initialize and start a swarm.

**Parameters**:
- `config_overrides` (optional): Configuration overrides like `model="gpt-4"`, `timeout_seconds=600`

**Returns**:
- `status`: "success" or "error"
- `swarm_id`: Unique identifier for this swarm instance
- `swarm_name`: Display name
- `agents_initialized`: Number of agents created
- `started_at`: Timestamp

**Example**:
```python
swarm = SwarmFactory.create_swarm('research')
result = await swarm.launch(model="claude-3.5-sonnet")
print(f"Swarm {result['swarm_id']} started with {result['agents_initialized']} agents")
```

---

### `execute(task_description, subtasks=None, priority=1) -> str`

Submit a task to the swarm for execution.

**Parameters**:
- `task_description` (str): What you want the swarm to do
- `subtasks` (list, optional): Pre-defined subtasks
- `priority` (int, 1-10): Priority level (1=low, 10=critical)

**Returns**:
- Task ID for tracking

**Example**:
```python
task_id = await swarm.execute(
    "Research competitive products",
    subtasks=["Find top 5 competitors", "Analyze their features", "Compare pricing"],
    priority=8
)
print(f"Task {task_id} queued")
```

---

### `get_status() -> Dict[str, Any]`

Get real-time status of the swarm.

**Returns**:
- `swarm_id`: Swarm identifier
- `status`: Current status (running, paused, completed, etc.)
- `metrics`: Real-time performance metrics
- `agents`: Agent status breakdown
- `tasks`: Task status breakdown
- `uptime_seconds`: How long swarm has been running

**Example**:
```python
status = swarm.get_status()
print(f"Status: {status['status']}")
print(f"Tasks: {status['tasks']}")
print(f"Agents: {status['agents']}")
```

---

### `get_results(task_id=None) -> Dict[str, Any]`

Retrieve results from completed tasks.

**Parameters**:
- `task_id` (optional): Specific task ID, or None for all results

**Returns**:
- Task results with status, output, and metadata

**Example**:
```python
# Get specific task result
result = swarm.get_results(task_id)

# Get all results
all_results = swarm.get_results()
print(f"Completed {all_results['total_results']} tasks")
```

---

### `add_agent(role, specialization=None, **config_overrides) -> str`

Dynamically add a new agent to the running swarm.

**Parameters**:
- `role` (AgentRole): Agent role (ANALYST, EXECUTOR, LEARNER, COORDINATOR, VISION, GUARD)
- `specialization` (optional): Specialization area
- `config_overrides` (optional): Configuration overrides

**Returns**:
- New agent ID

**Example**:
```python
new_agent = swarm.add_agent(
    role=AgentRole.ANALYST,
    specialization="market_analysis",
    model="claude-3.5-sonnet"
)
print(f"Added agent {new_agent}")
```

---

### `update_knowledge_base(key, value) -> None`

Update the shared knowledge base that all agents can access.

**Parameters**:
- `key` (str): Knowledge key
- `value` (any): Knowledge value (string, dict, list, etc.)

**Example**:
```python
swarm.update_knowledge_base("competitor_data", {
    "company": "Company A",
    "features": ["Feature 1", "Feature 2"],
    "pricing": "$99/month"
})
```

---

### `get_knowledge_base(key=None) -> Dict[str, Any]`

Access the shared knowledge base.

**Parameters**:
- `key` (optional): Specific key, or None for all knowledge

**Returns**:
- Knowledge dictionary with values and timestamps

**Example**:
```python
knowledge = swarm.get_knowledge_base()
competitor_data = swarm.get_knowledge_base("competitor_data")
```

---

### `shutdown() -> Dict[str, Any]`

Gracefully shut down the swarm.

**Returns**:
- Shutdown status and final metrics

**Example**:
```python
result = await swarm.shutdown()
print(f"Swarm completed {result['tasks_completed']} tasks")
print(f"Uptime: {result['uptime_seconds']} seconds")
```

---

## Advanced Usage

### Auto-Scaling

The swarm automatically scales agents based on task queue depth:

```python
swarm = SwarmFactory.create_swarm('research')
await swarm.launch()

# Add more agents if queue builds up
for i in range(3):
    swarm.add_agent(
        role=AgentRole.ANALYST,
        specialization="research"
    )
```

### Graceful Fallback

When an agent fails, the swarm automatically:
1. Retries the task (up to `max_retries` times, default 3)
2. If retries fail, reassigns to a different agent
3. Logs all failures for audit and debugging

### Real-time Monitoring

Stream metrics to a dashboard:

```python
async def monitor_swarm(swarm, interval=1):
    while swarm.status == SwarmStatus.RUNNING:
        status = swarm.get_status()
        dashboard.update(status)
        await asyncio.sleep(interval)
```

### Custom Configuration

Override agent configurations:

```python
swarm = SwarmFactory.create_swarm('development')
await swarm.launch(
    model="gpt-4",
    timeout_seconds=600,
    max_retries=5
)
```

---

## Database Storage

All swarm definitions and metrics are persisted in the database:

**`swarm_definitions` table**:
- `swarm_id`: Unique identifier
- `pattern_type`: research, development, operations, content, sales
- `name`: Display name
- `agent_count`: Initial agent count
- `max_agents`: Maximum allowed agents
- `configuration`: JSON configuration

**`swarm_metrics` table**:
- Tracks metrics per swarm: agents, tasks, success rate, duration, etc.
- Updated in real-time during execution

Query database:
```python
from run_agent_memory_sql import run_agent_memory_sql

# Get all swarm definitions
swarms = run_agent_memory_sql("SELECT * FROM swarm_definitions")

# Get metrics for a specific swarm
metrics = run_agent_memory_sql(
    "SELECT * FROM swarm_metrics WHERE swarm_id = ? LIMIT 100",
    [swarm_id]
)
```

---

## Error Handling

### Task Failures

When a task fails:
1. Swarm automatically retries (up to `max_retries` times)
2. If all retries fail, task status becomes "failed"
3. Check `get_results()` to see error details
4. Review logs for debugging

### Agent Failures

When an agent fails:
1. Agent marked as unhealthy
2. In-progress tasks reassigned to other agents
3. New agent can be added to replace it
4. Guard Agent logs all failures

### Graceful Shutdown

The swarm waits up to 30 seconds for in-progress tasks to complete before shutdown.

---

## Performance Tips

1. **Set appropriate priorities**: Critical tasks should have priority 8-10
2. **Use specializations**: Match agent specialization to task type
3. **Monitor metrics**: Use `get_status()` to track performance
4. **Scale proactively**: Add agents before queue builds up
5. **Share knowledge**: Use knowledge base to avoid duplicate work
6. **Set timeouts**: Adjust `timeout_seconds` based on task complexity

---

## Integration Examples

### With Existing Systems

```python
# Create and launch swarm
swarm = SwarmFactory.create_swarm('sales')
await swarm.launch()

# Send task to swarm
task_id = await swarm.execute("Find leads in Tech sector")

# Poll for results
while True:
    result = swarm.get_results(task_id)
    if result['status'] in ['completed', 'failed']:
        # Process result
        process_sales_leads(result['result'])
        break
    await asyncio.sleep(5)

await swarm.shutdown()
```

### With Dashboard

```python
# Monitor swarm metrics
async def dashboard_update_loop(swarm):
    while swarm.status == SwarmStatus.RUNNING:
        status = swarm.get_status()
        
        # Send to dashboard
        websocket.send(json.dumps({
            'agents_active': status['agents']['total'],
            'tasks_pending': status['tasks']['pending'],
            'tasks_completed': status['tasks']['completed'],
            'success_rate': status['metrics']['success_rate']
        }))
        
        await asyncio.sleep(1)
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Swarm won't launch | Check agent configs, verify models are available |
| Tasks not executing | Check task queue, verify agents are idle |
| High failure rate | Increase max_retries, check agent logs |
| Memory usage growing | Monitor knowledge base, implement cleanup |
| Slow performance | Add more agents, increase timeouts |

---

## Next Steps

1. **Try a demo**: Run `python swarm_patterns.py` to see all patterns in action
2. **Pick a pattern**: Choose the pattern that fits your use case
3. **Customize agents**: Adjust agent count, specializations, and tools
4. **Launch swarm**: Call `await swarm.launch()`
5. **Submit tasks**: Use `await swarm.execute()`
6. **Monitor progress**: Call `swarm.get_status()`
7. **Get results**: Call `swarm.get_results()`

---

## API Reference

See `/agent/home/universe/swarm_patterns.py` for complete implementation.

Key classes:
- `SwarmPattern`: Base class for all swarms
- `SwarmFactory`: Factory for creating swarm instances
- `ResearchSwarm`, `DevelopmentSwarm`, `OperationsSwarm`, `ContentSwarm`, `SalesSwarm`: Concrete implementations
- `AgentConfig`, `TaskDefinition`, `SwarmMetrics`: Data classes

Key enums:
- `AgentRole`: ANALYST, EXECUTOR, LEARNER, COORDINATOR, VISION, GUARD
- `SwarmStatus`: IDLE, INITIALIZING, RUNNING, PAUSED, COMPLETED, FAILED, SHUTDOWN

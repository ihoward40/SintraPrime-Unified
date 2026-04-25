# UniVerse Core Orchestration Engine - Quick Start Guide

## Installation

```bash
# The engine is self-contained and requires no external dependencies beyond Python 3.8+
# Python standard library is sufficient for core functionality
import asyncio
from core_engine import create_engine
```

## 5-Minute Quick Start

### 1. Create and Initialize Engine

```python
import asyncio
from core_engine import create_engine

async def main():
    # Create engine with max 50 agents
    engine = await create_engine(max_agents=50)
    
    # Define your agents
    agents = [
        {
            'agent_id': 'analyst_001',
            'capabilities': ['analysis', 'validation'],
            'max_concurrent_tasks': 5
        },
        {
            'agent_id': 'transformer_001',
            'capabilities': ['transformation', 'aggregation'],
            'max_concurrent_tasks': 3
        }
    ]
    
    # Create natural language intent
    intent = "Analyze the sales data and generate a summary report"
    
    # Execute orchestration
    result = await engine.orchestrate(
        intent=intent,
        agent_descriptors=agents
    )
    
    print(result)

# Run it
asyncio.run(main())
```

### 2. Parse Results

```python
# Check if orchestration succeeded
if result['status'] == 'success':
    print(f"✓ Execution completed in {result['duration_seconds']} seconds")
    print(f"✓ Success rate: {result['statistics']['success_rate']:.1f}%")
    print(f"✓ Agents used: {result['agents_used']}")
else:
    print(f"✗ Execution failed: {result.get('error', 'Unknown error')}")

# Access detailed results
task_results = result['task_results']
for task_id, task_result in task_results.items():
    print(f"Task {task_id}: {task_result['status']}")
```

## Common Scenarios

### Scenario 1: Simple Analysis Task

```python
async def analyze_data():
    engine = await create_engine(max_agents=10)
    
    result = await engine.orchestrate(
        intent="Analyze customer sentiment from reviews",
        agent_descriptors=[
            {
                'agent_id': 'sentiment_analyzer',
                'capabilities': ['analysis'],
                'max_concurrent_tasks': 5
            }
        ]
    )
    
    return result
```

### Scenario 2: Multi-Stage Data Pipeline

```python
async def data_pipeline():
    engine = await create_engine(max_agents=20)
    
    # Complex multi-stage intent
    intent = """
    Extract data from sources, transform to standard format, 
    aggregate metrics, validate quality, and generate reports
    """
    
    agents = [
        {
            'agent_id': 'extractor_01',
            'capabilities': ['transformation'],
            'max_concurrent_tasks': 5
        },
        {
            'agent_id': 'aggregator_01',
            'capabilities': ['aggregation'],
            'max_concurrent_tasks': 3
        },
        {
            'agent_id': 'validator_01',
            'capabilities': ['validation', 'reporting'],
            'max_concurrent_tasks': 4
        }
    ]
    
    result = await engine.orchestrate(intent, agents)
    return result
```

### Scenario 3: High-Priority Urgent Tasks

```python
async def urgent_task():
    engine = await create_engine(max_agents=30)
    
    # Marking as 'urgent' extracts high priority
    intent = "URGENT: Identify and alert on system anomalies"
    
    result = await engine.orchestrate(
        intent=intent,
        agent_descriptors=[
            {
                'agent_id': 'anomaly_detector',
                'capabilities': ['analysis', 'validation'],
                'max_concurrent_tasks': 10  # Higher capacity for urgent tasks
            }
        ]
    )
    
    return result
```

### Scenario 4: Distributed Parallel Processing

```python
async def parallel_processing():
    engine = await create_engine(max_agents=50)
    
    # Many agents for parallel processing
    agents = [
        {
            'agent_id': f'worker_{i:03d}',
            'capabilities': ['analysis', 'transformation'],
            'max_concurrent_tasks': 5
        }
        for i in range(20)  # 20 parallel workers
    ]
    
    intent = "Process all records in parallel"
    
    result = await engine.orchestrate(intent, agents[:5])  # Use subset
    return result
```

### Scenario 5: With Metadata and Tracking

```python
async def tracked_execution():
    engine = await create_engine(max_agents=10)
    
    result = await engine.orchestrate(
        intent="Validate data integrity",
        agent_descriptors=[
            {
                'agent_id': 'validator',
                'capabilities': ['validation'],
                'max_concurrent_tasks': 3
            }
        ],
        metadata={
            'user_id': 'user_123',
            'request_id': 'req_abc_456',
            'source': 'api',
            'environment': 'production',
            'retry_count': 0
        }
    )
    
    # Check metadata in result
    print(f"Execution ID: {result['execution_id']}")
    return result
```

## Monitoring Execution

### Check Status During Execution

```python
async def monitor_execution():
    engine = await create_engine(max_agents=10)
    
    # Start execution
    result = await engine.orchestrate(
        intent="Long-running analysis task",
        agent_descriptors=[{'agent_id': 'analyzer', 'capabilities': ['analysis']}]
    )
    
    # In a real scenario with longer-running tasks:
    execution_id = result['execution_id']
    
    # Check status
    status = engine.get_execution_status(execution_id)
    print(f"Status: {status['status']}")
    print(f"Progress: {status['completion_percentage']:.1f}%")
    print(f"Completed: {status['tasks_summary']['completed']} / {status['tasks_summary']['total']}")
```

### Handle Errors and Rollback

```python
async def error_handling():
    engine = await create_engine(max_agents=10)
    
    try:
        result = await engine.orchestrate(
            intent="Execute risky operation",
            agent_descriptors=[
                {'agent_id': 'executor', 'capabilities': ['analysis']}
            ]
        )
        
        # Check for failures
        if result['statistics']['failed_tasks'] > 0:
            print(f"Warning: {result['statistics']['failed_tasks']} tasks failed")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        # Can attempt rollback if execution started
        # await engine.rollback_execution(execution_id, reason=str(e))
```

## Understanding Results

The result object contains:

```python
{
    'execution_id': 'uuid-string',           # Unique execution identifier
    'original_intent': 'your intent text',   # Your original request
    'status': 'success',                     # success, failed, or rolled_back
    'duration_seconds': 12.345,              # Total execution time
    'completion_percentage': 100.0,          # % of tasks completed
    'statistics': {
        'total_tasks': 5,                    # Total decomposed tasks
        'completed_tasks': 5,                # Successfully completed
        'failed_tasks': 0,                   # Failed tasks
        'success_rate': 100.0,               # Success percentage
        'average_task_duration': 2.47,       # Average task time
        'total_agents': 2,                   # Agents used
        'agent_utilization': 0.75            # Avg utilization %
    },
    'task_results': {
        'task_001': {
            'task_type': 'analysis',
            'status': 'completed',
            'result': {...},
            'error': None,
            'execution_time': 2.1
        },
        # ... more tasks
    },
    'agents_used': 2,                        # Number of agents
    'timestamp': 'ISO-8601 timestamp'
}
```

### Interpret Statistics

```python
stats = result['statistics']

# Success rate interpretation
if stats['success_rate'] == 100.0:
    print("✓ All tasks completed successfully")
elif stats['success_rate'] >= 90.0:
    print("✓ Most tasks completed (some failures)")
else:
    print("✗ Significant failures detected")

# Performance interpretation
if stats['average_task_duration'] < 1.0:
    print("⚡ Fast execution")
elif stats['average_task_duration'] < 5.0:
    print("⏱ Normal execution")
else:
    print("🐢 Slow execution - consider optimization")

# Utilization interpretation
util = stats['agent_utilization']
if util > 0.8:
    print("📊 High utilization - consider more agents")
elif util < 0.3:
    print("📉 Low utilization - consider fewer agents")
else:
    print("✓ Good utilization")
```

## Advanced Usage

### Custom Agent Capabilities

```python
# Define specific capabilities for specialized agents
agents = [
    {
        'agent_id': 'nlp_expert',
        'capabilities': ['analysis', 'reporting'],  # Text-focused
        'max_concurrent_tasks': 3
    },
    {
        'agent_id': 'data_processor',
        'capabilities': ['transformation', 'aggregation'],  # Data-focused
        'max_concurrent_tasks': 8
    },
    {
        'agent_id': 'quality_assurance',
        'capabilities': ['validation'],  # QA-focused
        'max_concurrent_tasks': 2
    }
]
```

### Handling Large-Scale Operations

```python
async def large_scale():
    # For large-scale operations, use maximum agents
    engine = await create_engine(max_agents=50)
    
    # Create many workers
    agents = [
        {
            'agent_id': f'worker_{i:04d}',
            'capabilities': ['analysis', 'transformation'],
            'max_concurrent_tasks': 5
        }
        for i in range(40)  # 40 agents for massive parallel work
    ]
    
    result = await engine.orchestrate(
        intent="Process 1 million records in parallel",
        agent_descriptors=agents[:20]  # Use 20 of 40 registered
    )
    
    return result
```

### Real-time Monitoring Integration

```python
async def with_monitoring():
    engine = await create_engine(max_agents=20)
    
    # Start execution
    execution_result = asyncio.create_task(
        engine.orchestrate(
            intent="Long running task",
            agent_descriptors=[
                {
                    'agent_id': 'worker_1',
                    'capabilities': ['analysis']
                }
            ]
        )
    )
    
    # Monitor progress
    while not execution_result.done():
        await asyncio.sleep(1)
        # In production, would check status periodically
        print("Still executing...")
    
    result = await execution_result
    return result
```

## Troubleshooting

### Issue: Status is 'failed'

```python
# Check what went wrong
if result['status'] == 'failed':
    # 1. Check error message
    error = result.get('error_message', 'Unknown error')
    print(f"Error: {error}")
    
    # 2. Check failed tasks
    failed_tasks = [
        (task_id, task['error'])
        for task_id, task in result['task_results'].items()
        if task['status'] == 'failed'
    ]
    
    # 3. Check agent availability
    agents_used = result['agents_used']
    print(f"Agents used: {agents_used}")
    
    # 4. Try with more agents or resources
```

### Issue: Low Success Rate

```python
# Improve success rate
if result['statistics']['success_rate'] < 90.0:
    # Option 1: Use agents with better capabilities
    # Option 2: Simplify the intent (break into parts)
    # Option 3: Increase agent count
    # Option 4: Increase max_concurrent_tasks
    
    # Retry with improvements
    improved_agents = [
        {
            'agent_id': 'expert_analyzer',
            'capabilities': ['analysis', 'validation', 'transformation'],
            'max_concurrent_tasks': 10  # More capable
        }
    ]
```

### Issue: Slow Execution

```python
# Speed up execution
if result['duration_seconds'] > expected_time:
    # Option 1: Use more agents
    # Option 2: Increase max_concurrent_tasks
    # Option 3: Simplify intent to reduce decomposition
    # Option 4: Check agent health
    
    agents_for_speed = [
        {
            'agent_id': f'fast_worker_{i}',
            'capabilities': ['analysis', 'transformation'],
            'max_concurrent_tasks': 8  # Higher concurrency
        }
        for i in range(10)  # More workers
    ]
```

## Performance Tips

1. **Match Intent to Agent Capabilities**
   - Don't request 'transformation' if agents don't have it
   - Results in task reassignment or failure

2. **Right-Size max_concurrent_tasks**
   - Too high: Resource exhaustion
   - Too low: Underutilization
   - Sweet spot: 3-5 tasks per agent

3. **Use Metadata for Tracking**
   - Include user_id, request_id for tracing
   - Helps in debugging and optimization

4. **Monitor Statistics**
   - Watch success_rate
   - Monitor agent_utilization
   - Track average_task_duration trends

5. **Scale Gradually**
   - Start with 5-10 agents
   - Increase as needed
   - Monitor performance at each level

## Integration Examples

### With FastAPI

```python
from fastapi import FastAPI
from pydantic import BaseModel
import asyncio

app = FastAPI()
engine = None

@app.on_event("startup")
async def startup():
    global engine
    engine = await create_engine(max_agents=30)

@app.post("/orchestrate")
async def orchestrate(intent: str, agents: list):
    result = await engine.orchestrate(intent, agents)
    return result

@app.get("/status/{execution_id}")
async def status(execution_id: str):
    return engine.get_execution_status(execution_id)
```

### With Celery Tasks

```python
from celery import Celery

app = Celery('universe')
engine = None

def init_engine():
    global engine
    engine = asyncio.run(create_engine(max_agents=50))

@app.task
def orchestrate_task(intent, agents):
    result = asyncio.run(engine.orchestrate(intent, agents))
    return result
```

## Next Steps

1. **Read the full documentation**: See ARCHITECTURE.md
2. **Run the test suite**: `pytest test_core_engine.py -v`
3. **Explore the examples**: See example usage in core_engine.py
4. **Integrate with your system**: Use the API examples above
5. **Monitor in production**: Use execution traces and audit logs

## Support

For issues or questions:
1. Check audit logs: `audit_log` table
2. Review execution traces: `execution_trace` table
3. Check task details: `task_registry` table
4. Monitor agents: `agent_coordination` table

Logs include full error messages and operation details for debugging.

# UniVerse Memory System - Quick Start (5 Minutes)

## Installation

```python
from memory_system import MemorySystem

# Create instance
memory = MemorySystem()
```

Done! ✓

## 5-Minute Tutorial

### 1. Store Knowledge (30 seconds)

```python
# Agent learns something and shares it
knowledge_id = memory.store_knowledge(
    content="Always validate input before processing",
    knowledge_type="security_pattern",
    source_agent="security_expert"
)
```

### 2. Search Knowledge (30 seconds)

```python
# Find relevant knowledge by meaning
results = memory.search_knowledge_semantic(
    query="How to prevent security vulnerabilities?",
    limit=10
)

for result in results:
    print(f"- {result['content']}")
```

### 3. Register a Skill (30 seconds)

```python
# Agent shares a learned technique
skill_id = memory.register_skill(
    name="input_validation",
    description="Framework for validating user input",
    implementation="def validate(data): ...",
    source_agent="security_expert"
)
```

### 4. Inherit Skills (30 seconds)

```python
# Another agent learns the skill
memory.inherit_skill(skill_id, agent_id="learner_agent")

# Track performance when agent uses it
memory.update_skill_performance(
    skill_id=skill_id,
    agent_id="learner_agent",
    success=True  # or False for failure
)
```

### 5. Learning from Failure (60 seconds)

```python
# Task fails, trigger learning session
session = memory.start_learning_session(
    agent_id="learner_agent",
    trigger_type="task_failure",
    trigger_task_id="failed_task_123",
    mentor_agent_id="security_expert"
)

# Later, record what was learned
memory.record_learning_improvement(
    session_id=session,
    generated_skills=[skill_id],
    improvements={"error_reduction": 0.3}
)
```

### 6. Analyze Progress (30 seconds)

```python
# Get performance metrics
analytics = memory.get_agent_analytics("learner_agent")

for metric, stats in analytics.items():
    print(f"{metric}: avg={stats['average']:.2f}")

# Get overall stats
stats = memory.get_stats()
print(f"Total knowledge: {stats['total_knowledge']}")
print(f"Active skills: {stats['active_skills']}")
```

## Common Patterns

### Pattern 1: Capture a Success

```python
# Store successful technique
kid = memory.store_knowledge(
    f"Successfully handled {task_type} with approach X",
    "successful_approach",
    my_agent_id
)

# Mark it as successful for others to learn
memory.update_knowledge_usage(kid, success=True)
```

### Pattern 2: Share a Technique as Skill

```python
# Agent discovers a useful pattern
skill = memory.register_skill(
    name="pattern_name",
    description="What it does",
    implementation="Code or reference",
    source_agent=my_agent_id,
    tags=["domain", "category"]
)

# Let others discover and learn it
discovered = memory.discover_skills_for_agent("other_agent")
```

### Pattern 3: Link Related Concepts

```python
# Connect related pieces of knowledge
memory.link_knowledge(
    source_id=knowledge_1,
    target_id=knowledge_2,
    relationship_type="complements",
    strength=0.9
)

# Find all related knowledge
related = memory.get_related_knowledge(knowledge_1, depth=2)
```

### Pattern 4: Mentor-Led Learning

```python
# When a learner fails
session = memory.start_learning_session(
    agent_id="learner",
    trigger_type="task_failure",
    trigger_task_id=failed_task,
    mentor_agent_id="expert"  # Specify mentor!
)

# Later record improvements
memory.record_learning_improvement(
    session,
    generated_skills=new_skills,
    improvements=improvements
)
```

## Integration Example

### With Your Execution System

```python
from memory_integration import ExecutionAwareMemory

memory = ExecutionAwareMemory()

# Record task outcomes
memory.record_successful_task(
    task_id="task_123",
    execution_id="exec_001",
    agent_id="my_agent",
    description="Data validation",
    techniques_used=["regex", "validation"],
    metrics={"accuracy": 0.99}
)

# Handle failures
session = memory.record_failed_task_and_trigger_learning(
    task_id="task_124",
    execution_id="exec_002",
    agent_id="my_agent",
    description="API integration",
    error_message="Timeout error",
    mentor_agent_id="api_expert"
)

# Get recommendations
skills = memory.get_recommended_skills_for_task(
    "API integration task",
    agent_id="my_agent"
)

# Analyze progress
progress = memory.analyze_agent_learning_progress("my_agent")
print(f"Skills inherited: {progress['skills_inherited']}")
```

## Key Concepts (2 minutes)

### Knowledge
- Any experience, pattern, or insight shared by agents
- Auto-tagged and embedded for semantic search
- Tracked by success rate and usage count

### Skills
- Reusable techniques that agents can inherit
- Versioned and dependency-tracked
- Performance tracked per agent

### Learning Sessions
- Triggered when tasks fail or improvements needed
- Can include mentor guidance
- Record improvements and generated skills

### Relationships
- Connect related pieces of knowledge
- Types: related, complements, contradicts, expands, depends_on
- Enable graph traversal and pattern discovery

### Performance Metrics
- Track any metric for any agent
- Time-aggregated analytics
- Support custom metric types

## File Locations

```
/agent/home/universe/
├── memory_system.py          # Main implementation
├── memory_integration.py      # Execution integration
├── memory.db                  # SQLite database
├── MEMORY_SYSTEM.md          # Full guide
├── API_REFERENCE.md          # Complete API
└── test_memory_simple.py      # Test examples
```

## Common Functions Reference

| Function | Purpose |
|----------|---------|
| `store_knowledge()` | Save knowledge |
| `search_knowledge_semantic()` | Find by meaning |
| `register_skill()` | Create a skill |
| `inherit_skill()` | Agent learns skill |
| `start_learning_session()` | Begin learning from failure |
| `update_skill_performance()` | Track skill usage |
| `record_agent_performance()` | Track metrics |
| `get_agent_analytics()` | View progress |
| `get_stats()` | System overview |

## Tips & Tricks

1. **Always close connection**: `memory.close()` when done
2. **Use metadata**: Add context to knowledge for better discovery
3. **Track everything**: Record both successes and failures
4. **Link concepts**: Build knowledge graphs for deeper insights
5. **Monitor progress**: Regularly check analytics

## What's Next?

1. Read [MEMORY_SYSTEM.md](MEMORY_SYSTEM.md) for detailed guide
2. Check [API_REFERENCE.md](API_REFERENCE.md) for all functions
3. Look at [memory_integration.py](memory_integration.py) for integration patterns
4. Run [test_memory_simple.py](test_memory_simple.py) to see it work

## Troubleshooting

**Q: Getting "ModuleNotFoundError: No module named 'numpy'"?**
A: The system works without numpy. Install it with: `pip install numpy`

**Q: Search not returning results?**
A: Use `search_knowledge_keyword()` as fallback, or check if knowledge was stored.

**Q: Database locked?**
A: Call `memory.close()` to release connections.

**Q: Performance slow?**
A: Run `memory.cleanup_old_cache()` to clear old search cache.

## Real-World Example

```python
from memory_system import MemorySystem

memory = MemorySystem()

# Agent 1: Expert in error handling
error_skill = memory.register_skill(
    name="error_handling",
    description="Graceful error handling for production",
    implementation="class ErrorHandler: ...",
    source_agent="expert_agent",
    tags=["error_handling", "production"]
)

# Agent 2: Encounters failure
session = memory.start_learning_session(
    agent_id="junior_agent",
    trigger_type="task_failure",
    trigger_task_id="crash_handling",
    mentor_agent_id="expert_agent"
)

# Agent 2: Inherits the skill
memory.inherit_skill(error_skill, "junior_agent")

# Agent 2: Uses skill successfully
memory.update_skill_performance(error_skill, "junior_agent", success=True)

# Record improvement
memory.record_learning_improvement(
    session,
    generated_skills=[error_skill],
    improvements={"crashes_prevented": 10}
)

# Track progress
analytics = memory.get_agent_analytics("junior_agent")
print(analytics)

memory.close()
```

---

**Total Setup Time: ~5 minutes**

You're ready to use the memory system! 🚀

For detailed information, see the full documentation in `/agent/home/universe/`.

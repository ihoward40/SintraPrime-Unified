# UniVerse Hive Mind Memory System

A distributed knowledge and learning system that enables agents to share experiences, improve collectively, and inherit learned skills.

## Overview

The memory system consists of six core components:

1. **Knowledge Storage** - Store and retrieve experiences with semantic search
2. **Knowledge Relationships** - Link related concepts into knowledge graphs
3. **Skill Library** - Index and manage learned skills with versioning
4. **Skill Inheritance** - Allow agents to adopt and improve existing skills
5. **Learning Loops** - Trigger learning from failures with mentor guidance
6. **Performance Analytics** - Track agent improvement over time

## Installation

```python
from memory_system import MemorySystem

# Create an instance
memory = MemorySystem()
```

## Core Features

### 1. Knowledge Storage

Store any type of knowledge or experience learned by agents.

```python
# Store knowledge
knowledge_id = memory.store_knowledge(
    content="Always validate user input to prevent injection attacks",
    knowledge_type="security_insight",
    source_agent="security_agent",
    metadata={
        "risk_level": "high",
        "domain": "security",
        "impact_score": 0.95
    }
)

# Update usage statistics
memory.update_knowledge_usage(knowledge_id, success=True)
```

**Automatic Features:**
- Tag extraction from content (removes stop words, extracts meaningful terms)
- Vector embeddings for semantic search (using all-MiniLM-L6-v2 model)
- Success rate tracking across usage instances
- Relevance scoring based on usage patterns

### 2. Knowledge Relationships

Create semantic connections between pieces of knowledge.

```python
# Link two pieces of knowledge
memory.link_knowledge(
    source_id=k1,
    target_id=k2,
    relationship_type="complements",  # or: "contradicts", "expands", "depends_on"
    strength=0.8  # 0.0 to 1.0, higher = stronger relationship
)

# Retrieve related knowledge with traversal
related = memory.get_related_knowledge(
    knowledge_id=k1,
    relationship_type="complements",
    depth=2  # How many levels to traverse
)
```

**Relationship Types:**
- `related` - General semantic relationship
- `complements` - Adds to or enhances the knowledge
- `contradicts` - Opposes or conflicts with the knowledge
- `expands` - Provides more detail or examples
- `depends_on` - Requires understanding of another concept

### 3. Knowledge Search

Find relevant knowledge by meaning or keywords.

```python
# Semantic search (vector similarity)
results = memory.search_knowledge_semantic(
    query="How to prevent security vulnerabilities?",
    limit=10,
    knowledge_type="security_insight"  # optional filter
)

# Keyword search (fallback if embeddings unavailable)
results = memory.search_knowledge_keyword(
    query="security validation",
    limit=10
)
```

**Results Include:**
- Content and metadata
- Type and source agent
- Tags (auto-extracted)
- Relevance score (0-1)
- Usage count and success rate
- Creation timestamp

### 4. Skill Library

Register and discover learned skills.

```python
# Register a skill
skill_id = memory.register_skill(
    name="input_validation",
    description="Comprehensive input validation framework",
    implementation="def validate(data): ...",
    source_agent="security_agent",
    dependencies=["sanitizer", "validator"],
    tags=["security", "validation"]
)

# Search for skills
skills = memory.search_skills(
    query="How to validate user input securely?",
    limit=10
)

# Get skill details
for skill in skills:
    print(f"Name: {skill['name']}")
    print(f"Description: {skill['description']}")
    print(f"Success Rate: {skill['success_rate']:.2%}")
    print(f"Usage Count: {skill['usage_count']}")
```

**Skill Attributes:**
- Name, description, implementation code
- Source agent and version number
- Dependencies list for requirement tracking
- Usage count and success rate metrics
- Tags for categorization

### 5. Skill Inheritance

Allow agents to learn and adopt skills from others.

```python
# Agent learns a skill
success = memory.inherit_skill(skill_id, agent_id="learning_agent")

# Auto-discover relevant skills for an agent
skills = memory.discover_skills_for_agent(
    agent_id="learning_agent",
    recent_task_ids=["task_1", "task_2"]
)

# Record performance when agent uses the skill
memory.update_skill_performance(
    skill_id=skill_id,
    agent_id="learning_agent",
    success=True,  # or False for failure
    metrics={"execution_time": 0.5, "accuracy": 0.98}
)
```

### 6. Learning Loops

Trigger structured learning from task failures.

```python
# Start a learning session
session_id = memory.start_learning_session(
    agent_id="learning_agent",
    trigger_type="task_failure",
    trigger_task_id="failed_task_123",
    mentor_agent_id="expert_agent"
)

# Record improvements after learning
memory.record_learning_improvement(
    session_id=session_id,
    generated_skills=[skill1, skill2],
    improvements={
        "error_reduction": 0.3,
        "performance_improvement": 0.2,
        "new_patterns": 5
    },
    content="Learned proper error handling patterns from mentor"
)

# Retrieve learning history for analysis
sessions = memory.get_learning_sessions(agent_id="learning_agent", limit=20)
```

### 7. Performance Analytics

Track agent improvement and effectiveness.

```python
# Record performance metric
memory.record_agent_performance(
    agent_id="learning_agent",
    metric_type="success_rate",
    value=0.95,
    context={
        "domain": "security",
        "task_category": "validation"
    }
)

# Query performance analytics
analytics = memory.get_agent_analytics(
    agent_id="learning_agent",
    metric_type="success_rate",  # optional
    days=30  # last 30 days
)

# Results show: count, average, min, max
for metric, data in analytics.items():
    print(f"{metric}:")
    print(f"  Count: {data['count']}")
    print(f"  Average: {data['average']:.4f}")
    print(f"  Min: {data['min']:.4f}, Max: {data['max']:.4f}")
```

## Database Schema

### Tables

**knowledge_base**
- id: Unique identifier
- content: Full knowledge text
- type: Knowledge category
- source_agent: Which agent contributed this
- embedding: Vector embedding for semantic search
- tags: Auto-extracted meaningful terms
- relevance_score: Calculated metric
- usage_count: How many times used
- success_rate: Success percentage

**knowledge_relationships**
- source_knowledge_id: Origin knowledge
- target_knowledge_id: Related knowledge
- relationship_type: Type of relationship
- strength: Relationship strength (0-1)

**skills**
- id: Unique skill identifier
- name: Skill name
- description: What the skill does
- implementation: Code or reference
- source_agent: Original creator
- version: Version number
- usage_count: Total uses across agents
- success_rate: Success percentage
- dependencies: Required skills
- tags: Categorization tags

**skill_inheritance**
- skill_id: Which skill
- agent_id: Which agent
- inherited_at: When inherited
- usage_count: Uses by this agent
- success_count, failure_count: Outcomes
- performance_score: Agent-specific metric

**learning_sessions**
- id: Session identifier
- agent_id: Learning agent
- trigger_type: Why learning started
- trigger_task_id: Failed task reference
- mentor_agent_id: Teaching agent
- status: active/completed
- generated_skills: Skills created
- improvements: Measured improvements

**agent_performance**
- agent_id: Agent identifier
- metric_type: Type of metric
- value: Numeric value
- recorded_at: Timestamp
- context: Additional context

## Performance Characteristics

- **Search Speed**: <100ms for semantic search across 10k+ entries
- **Embeddings**: All-MiniLM-L6-v2 (384-dimensional vectors)
- **Caching**: Query results cached for 1 hour
- **Batch Operations**: Supported for bulk knowledge storage
- **Scalability**: SQLite for metadata, LanceDB-ready for vectors

## Vector Embeddings

The system uses Sentence Transformers for semantic understanding:

```python
# If embeddings are available
system.embedder is not None  # True if loaded
```

**Fallback Behavior:**
- If embeddings unavailable, keyword search is used
- JSON serialization of embeddings as fallback
- Graceful degradation without breaking functionality

## Example: Complete Workflow

```python
from memory_system import MemorySystem

# Initialize
memory = MemorySystem()

# Agent 1 learns something and shares it
k1 = memory.store_knowledge(
    "Pattern: Use async/await for I/O operations",
    "performance_pattern",
    "optimization_agent"
)

# Register a skill derived from this knowledge
skill = memory.register_skill(
    "async_optimization",
    "Optimize I/O with async/await",
    "async def fetch(): ...",
    "optimization_agent"
)

# Agent 2 learns about the skill failure
session = memory.start_learning_session(
    "learning_agent",
    "task_failure",
    "sync_io_task",
    "optimization_agent"
)

# Agent 2 inherits the skill
memory.inherit_skill(skill, "learning_agent")

# Agent 2 tries it successfully
memory.update_skill_performance(skill, "learning_agent", success=True)

# Record the learning
memory.record_learning_improvement(
    session,
    generated_skills=[skill],
    improvements={"performance": 0.3}
)

# Track metrics
memory.record_agent_performance("learning_agent", "speed_improvement", 2.5)

# Cleanup
memory.close()
```

## Statistics and Insights

```python
# Get overall stats
stats = memory.get_stats()
print(f"Total knowledge entries: {stats['total_knowledge']}")
print(f"Agents currently learning: {stats['agents_learning']}")

# Export knowledge graph
graph = memory.export_knowledge_graph(limit=1000)
# Use for visualization with Vis.js, D3.js, or similar

# Clean up old cache
memory.cleanup_old_cache(days=7)
```

## Best Practices

1. **Knowledge Organization**
   - Use consistent knowledge types
   - Add helpful metadata for context
   - Link related pieces together

2. **Skill Management**
   - Keep implementation code clean and well-commented
   - Use meaningful dependency declarations
   - Tag skills with domain and difficulty level

3. **Learning Sessions**
   - Always record completed learning with improvements
   - Connect failures to successful learnings
   - Track mentor-mentee relationships

4. **Performance Tracking**
   - Record multiple metric types for holistic view
   - Include context for metric interpretation
   - Regularly review analytics to identify trends

5. **Database Maintenance**
   - Periodically clean up old cache entries
   - Monitor database growth
   - Archive old learning sessions if needed

## Error Handling

All functions return `None` or empty results on error and log messages:

```python
try:
    knowledge_id = memory.store_knowledge(...)
    if knowledge_id is None:
        print("Failed to store knowledge")
except Exception as e:
    print(f"Error: {e}")
```

## Extending the System

To add new relationship types:

```python
# In knowledge_relationships table
memory.link_knowledge(k1, k2, "custom_relationship", 0.9)
```

To add new performance metrics:

```python
memory.record_agent_performance(
    agent_id,
    "custom_metric_name",
    value,
    context={"custom_field": "value"}
)
```

## File Location

```
/agent/home/universe/memory_system.py
```

## Dependencies

- sqlite3 (built-in)
- numpy (optional, for faster embeddings)
- sentence-transformers (optional, for semantic search)

The system gracefully degrades if optional dependencies are unavailable.

# Memory System API Reference

Complete reference for all MemorySystem functions and their usage.

## Initialization

### `MemorySystem(db_path: str = DB_PATH)`

Initialize a memory system instance.

**Parameters:**
- `db_path` (str): Path to SQLite database. Defaults to `/agent/home/universe/memory.db`

**Returns:** MemorySystem instance

**Example:**
```python
from memory_system import MemorySystem

memory = MemorySystem()
# or with custom path
memory = MemorySystem("/path/to/custom.db")
```

---

## Knowledge Storage

### `store_knowledge(content: str, knowledge_type: str, source_agent: str, metadata: Dict = None) -> str`

Store a new piece of knowledge or experience.

**Parameters:**
- `content` (str): The knowledge content
- `knowledge_type` (str): Category - e.g., "experience", "skill", "pattern", "insight"
- `source_agent` (str): Agent ID that contributed this knowledge
- `metadata` (dict, optional): Additional context

**Returns:** Knowledge ID (str) or None on error

**Auto-generated:**
- Tags (extracted from content)
- Vector embedding (if enabled)
- Created timestamp

**Example:**
```python
kid = memory.store_knowledge(
    "Always validate input before processing",
    "security_pattern",
    "security_agent",
    {"risk": "high", "domain": "input_validation"}
)
```

---

### `update_knowledge_usage(knowledge_id: str, success: bool = True) -> None`

Update usage statistics for a piece of knowledge.

**Parameters:**
- `knowledge_id` (str): ID of knowledge to update
- `success` (bool): Whether the usage was successful

**Effects:**
- Increments usage_count
- Updates success_rate (running average)

**Example:**
```python
memory.update_knowledge_usage(kid, success=True)
```

---

## Knowledge Search

### `search_knowledge_semantic(query: str, limit: int = 10, knowledge_type: str = None) -> List[Dict]`

Search knowledge by semantic meaning using vector similarity.

**Parameters:**
- `query` (str): Search query
- `limit` (int): Maximum results (default: 10)
- `knowledge_type` (str, optional): Filter by type

**Returns:** List of knowledge dictionaries with:
- `id`: Knowledge ID
- `content`: Full content
- `type`: Knowledge type
- `source_agent`: Creator
- `tags`: Auto-extracted tags
- `score`: Relevance score (0-1)
- `usage_count`: Number of uses
- `success_rate`: Success percentage

**Note:** Falls back to keyword search if embeddings unavailable

**Example:**
```python
results = memory.search_knowledge_semantic(
    "How to prevent SQL injection?",
    limit=5,
    knowledge_type="security_pattern"
)

for result in results:
    print(f"{result['score']:.2f} - {result['content'][:50]}")
```

---

### `search_knowledge_keyword(query: str, limit: int = 10, knowledge_type: str = None) -> List[Dict]`

Search knowledge by keywords (simple substring matching).

**Parameters:**
- `query` (str): Search query
- `limit` (int): Maximum results
- `knowledge_type` (str, optional): Filter by type

**Returns:** List of knowledge dictionaries (same as semantic search)

**Example:**
```python
results = memory.search_knowledge_keyword("validation patterns", limit=10)
```

---

## Knowledge Relationships

### `link_knowledge(source_id: str, target_id: str, relationship_type: str, strength: float = 1.0) -> None`

Create a relationship between two pieces of knowledge.

**Parameters:**
- `source_id` (str): Source knowledge ID
- `target_id` (str): Target knowledge ID
- `relationship_type` (str): Type of relationship
  - `"related"` - General relationship
  - `"complements"` - Adds/enhances
  - `"contradicts"` - Opposes
  - `"expands"` - Provides details
  - `"depends_on"` - Requires knowledge
- `strength` (float): Relationship strength 0.0-1.0

**Example:**
```python
memory.link_knowledge(
    k1, k2,
    relationship_type="complements",
    strength=0.9
)
```

---

### `get_related_knowledge(knowledge_id: str, relationship_type: str = None, depth: int = 1) -> List[Dict]`

Get knowledge related to a given piece.

**Parameters:**
- `knowledge_id` (str): Starting knowledge ID
- `relationship_type` (str, optional): Filter by type
- `depth` (int): Traversal depth in relationship graph

**Returns:** List of related knowledge with:
- All fields from `search_knowledge_semantic`
- `relationship_type`: Type of connection
- `strength`: Relationship strength
- `depth`: Distance from source

**Example:**
```python
related = memory.get_related_knowledge(kid, depth=2)
for rel in related:
    print(f"[{rel['relationship_type']}] {rel['content'][:40]}")
```

---

## Skill Management

### `register_skill(name: str, description: str, implementation: str, source_agent: str, dependencies: List[str] = None, tags: List[str] = None) -> str`

Register a new skill in the library.

**Parameters:**
- `name` (str): Unique skill name
- `description` (str): What the skill does
- `implementation` (str): Code or reference
- `source_agent` (str): Agent who created this
- `dependencies` (list, optional): Required skills
- `tags` (list, optional): Categorization tags

**Returns:** Skill ID (str) or None on error

**Auto-generated:**
- Version 1 (increment on updates)
- Vector embedding (if enabled)
- Created timestamp

**Example:**
```python
skill_id = memory.register_skill(
    name="async_io_optimization",
    description="Optimize I/O with async/await",
    implementation="async def process(): ...",
    source_agent="optimization_agent",
    dependencies=["event_loop"],
    tags=["performance", "async"]
)
```

---

### `search_skills(query: str, limit: int = 10) -> List[Dict]`

Search for skills by semantic meaning.

**Parameters:**
- `query` (str): Search query
- `limit` (int): Maximum results

**Returns:** List of skill dictionaries with:
- `id`: Skill ID
- `name`: Skill name
- `description`: Description
- `source_agent`: Creator
- `version`: Current version
- `usage_count`: Total uses across agents
- `success_rate`: Success percentage
- `tags`: Categorization tags

**Example:**
```python
skills = memory.search_skills("How to optimize database queries?", limit=5)
for skill in skills:
    print(f"{skill['name']} (v{skill['version']}) - {skill['success_rate']:.0%}")
```

---

## Skill Inheritance

### `inherit_skill(skill_id: str, agent_id: str) -> bool`

Allow an agent to inherit and use a skill.

**Parameters:**
- `skill_id` (str): Skill to learn
- `agent_id` (str): Learning agent

**Returns:** True if successful, False if already inherited or error

**Effects:**
- Creates inheritance record
- Tracks usage and performance for this agent

**Example:**
```python
if memory.inherit_skill(skill_id, "new_agent"):
    print("Agent learned the skill!")
```

---

### `discover_skills_for_agent(agent_id: str, recent_task_ids: List[str] = None) -> List[Dict]`

Auto-discover relevant skills for an agent.

**Parameters:**
- `agent_id` (str): Agent to discover for
- `recent_task_ids` (list, optional): Recent task context

**Returns:** List of skill recommendations with:
- All fields from `search_skills`
- `recommendation_score`: Relevance score

**Logic:** Finds high-success skills agent hasn't inherited yet

**Example:**
```python
recommendations = memory.discover_skills_for_agent(
    "learning_agent",
    recent_task_ids=["task_1", "task_2"]
)

for skill in recommendations:
    print(f"Recommended: {skill['name']} (score: {skill['recommendation_score']:.2f})")
```

---

### `update_skill_performance(skill_id: str, agent_id: str, success: bool, metrics: Dict = None) -> None`

Record skill usage and performance for an agent.

**Parameters:**
- `skill_id` (str): Skill being used
- `agent_id` (str): Agent using it
- `success` (bool): Whether usage was successful
- `metrics` (dict, optional): Additional performance data

**Effects:**
- Increments usage_count for this agent+skill
- Updates success/failure counts
- Updates performance_score (agent-specific)
- Updates global skill metrics

**Example:**
```python
memory.update_skill_performance(
    skill_id, 
    "learning_agent",
    success=True,
    metrics={"execution_time": 0.5, "accuracy": 0.99}
)
```

---

## Learning Sessions

### `start_learning_session(agent_id: str, trigger_type: str, trigger_task_id: str = None, mentor_agent_id: str = None) -> str`

Start a learning session triggered by failure.

**Parameters:**
- `agent_id` (str): Agent doing the learning
- `trigger_type` (str): Why learning started
  - `"task_failure"` - Failed task
  - `"performance_plateau"` - Needs improvement
  - `"skill_request"` - Requested learning
- `trigger_task_id` (str, optional): Related task ID
- `mentor_agent_id` (str, optional): Teaching agent

**Returns:** Session ID (str) or None on error

**Status:** Initially "active", becomes "completed" when recorded

**Example:**
```python
session = memory.start_learning_session(
    agent_id="learner",
    trigger_type="task_failure",
    trigger_task_id="failed_task_123",
    mentor_agent_id="expert"
)
```

---

### `record_learning_improvement(session_id: str, generated_skills: List[str] = None, improvements: Dict = None, content: str = None) -> None`

Record outcomes from a completed learning session.

**Parameters:**
- `session_id` (str): Session ID
- `generated_skills` (list, optional): Skills created/learned
- `improvements` (dict, optional): Measured improvements
  - Keys: metric names (e.g., "error_reduction")
  - Values: improvement amounts
- `content` (str, optional): Learning notes

**Effects:**
- Sets status to "completed"
- Records timestamp
- Stores generated skills and improvements

**Example:**
```python
memory.record_learning_improvement(
    session,
    generated_skills=[skill_id],
    improvements={
        "error_reduction": 0.25,
        "performance_boost": 0.15
    },
    content="Learned error handling patterns"
)
```

---

### `get_learning_sessions(agent_id: str = None, limit: int = 20) -> List[Dict]`

Retrieve completed learning sessions.

**Parameters:**
- `agent_id` (str, optional): Filter by agent
- `limit` (int): Maximum results

**Returns:** List of session dictionaries with:
- `id`: Session ID
- `agent_id`: Learning agent
- `trigger_type`: What triggered learning
- `mentor_agent_id`: Teaching agent (if any)
- `status`: "completed" (filtered)
- `created_at`: Session start time
- `completed_at`: Completion time
- `generated_skills`: Skills created
- `improvements`: Measured improvements

**Example:**
```python
sessions = memory.get_learning_sessions("learner", limit=10)
for session in sessions:
    print(f"Session {session['id'][:8]}")
    print(f"  Generated: {len(session['generated_skills'])} skills")
    print(f"  Improvements: {session['improvements']}")
```

---

## Performance Analytics

### `record_agent_performance(agent_id: str, metric_type: str, value: float, context: Dict = None) -> None`

Record a performance metric for an agent.

**Parameters:**
- `agent_id` (str): Agent identifier
- `metric_type` (str): Type of metric
  - Common: "success_rate", "avg_response_time", "error_count"
  - Custom: any string
- `value` (float): Metric value
- `context` (dict, optional): Additional context

**Example:**
```python
memory.record_agent_performance(
    "agent_id",
    "success_rate",
    0.95,
    context={"task_type": "validation", "domain": "security"}
)
```

---

### `get_agent_analytics(agent_id: str, metric_type: str = None, days: int = 30) -> Dict`

Get performance analytics for an agent.

**Parameters:**
- `agent_id` (str): Agent to analyze
- `metric_type` (str, optional): Filter by metric type
- `days` (int): Look back period (default: 30 days)

**Returns:** Dictionary with metrics:
```python
{
    "metric_name": {
        "count": int,          # number of recordings
        "average": float,      # average value
        "min": float,          # minimum value
        "max": float           # maximum value
    }
}
```

**Example:**
```python
analytics = memory.get_agent_analytics("agent_id", days=7)
for metric, stats in analytics.items():
    print(f"{metric}")
    print(f"  Avg: {stats['average']:.4f}")
    print(f"  Range: {stats['min']:.4f} - {stats['max']:.4f}")
```

---

## Statistics & Exports

### `get_stats() -> Dict`

Get overall memory system statistics.

**Returns:** Dictionary with:
- `total_knowledge`: Total knowledge entries
- `knowledge_sources`: Unique contributors
- `active_skills`: Active skill count
- `agents_learning`: Agents in learning process
- `completed_learning_sessions`: Completed sessions
- `agents_tracked`: Agents with performance data
- `knowledge_relationships`: Total relationships

**Example:**
```python
stats = memory.get_stats()
print(f"Knowledge base: {stats['total_knowledge']} entries")
print(f"Skills: {stats['active_skills']} available")
print(f"Learning agents: {stats['agents_learning']}")
```

---

### `export_knowledge_graph(limit: int = 1000) -> Dict`

Export knowledge graph for visualization.

**Parameters:**
- `limit` (int): Maximum nodes to export

**Returns:** Dictionary with:
- `nodes`: List of knowledge entries
  - `id`: Knowledge ID
  - `label`: Content preview (50 chars)
  - `type`: Knowledge type
  - `source`: Source agent
  - `success_rate`: Success percentage
  - `usage_count`: Usage count
- `edges`: List of relationships
  - `source`: Source knowledge ID
  - `target`: Target knowledge ID
  - `type`: Relationship type
  - `weight`: Strength 0-1
- `node_count`: Total nodes
- `edge_count`: Total edges

**Use Cases:** Visualization with Vis.js, D3.js, Cytoscape.js

**Example:**
```python
graph = memory.export_knowledge_graph(limit=500)
# Export to JSON for visualization
import json
with open("graph.json", "w") as f:
    json.dump(graph, f)
```

---

### `cleanup_old_cache(days: int = 7) -> None`

Clean up expired search cache entries.

**Parameters:**
- `days` (int): Delete entries older than this many days

**Effects:**
- Removes cached search results
- Reclaims database space

**Example:**
```python
memory.cleanup_old_cache(days=7)
```

---

## Connection Management

### `close() -> None`

Close database connections.

**Example:**
```python
memory.close()
```

---

## Utility Functions

### `create_memory_system(db_path: str = DB_PATH) -> MemorySystem`

Factory function to create a memory system instance.

**Example:**
```python
from memory_system import create_memory_system

memory = create_memory_system()
```

---

## Error Handling

All functions handle errors gracefully:

- **Return `None` or empty list on error**
- **Print error messages to console**
- **Database continues operating**

**Best Practice:**
```python
knowledge_id = memory.store_knowledge(...)
if knowledge_id is None:
    print("Failed to store knowledge")
else:
    print(f"Stored: {knowledge_id}")
```

---

## Constants

```python
DB_PATH = "/agent/home/universe/memory.db"
VECTOR_DIMENSION = 384  # all-MiniLM-L6-v2 model
```

---

## Performance Notes

- **Semantic Search**: <100ms for 10k+ entries
- **Keyword Search**: <50ms for 10k+ entries
- **Batch Operations**: Not directly supported, but individual operations are fast
- **Cache**: 1-hour TTL for search results
- **Embeddings**: Optional, system works without them

---

## Type Hints

All functions use type hints. When available:
- `Dict` from typing
- `List` from typing
- `Optional` from typing

Example with typing:
```python
from memory_system import MemorySystem
from typing import List, Dict, Optional

def my_function(memory: MemorySystem) -> Optional[str]:
    kid: str = memory.store_knowledge("test", "type", "agent")
    results: List[Dict] = memory.search_knowledge_semantic("query")
    return kid
```

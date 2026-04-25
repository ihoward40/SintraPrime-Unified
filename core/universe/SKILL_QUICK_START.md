# UniVerse Skill System - Quick Start Guide

Get started with the UniVerse Skill Generation System in 5 minutes.

## Installation

The skill system is pre-installed at `/agent/home/universe/skill_system.py`.

### Basic Import

```python
from skill_system import UniVersSkillSystem

# Initialize the system
system = UniVersSkillSystem()
```

## 5-Minute Quick Start

### 1. Create a Skill from a Task (2 minutes)

```python
# Define a completed task
task = {
    'inputs': {'data': 'input_data.csv'},
    'outputs': {'analysis': 'report.html'},
    'operations': ['load', 'process', 'analyze', 'report']
}

# Create skill from task
skill_id = system.learn_from_task(
    task_description="Analyze data and generate report",
    task_result=task,
    task_type="analysis",
    author="my_team"
)

print(f"Created skill: {skill_id}")
```

### 2. Share with Agents (1 minute)

```python
# Give the skill to agents
system.distribute_skill(skill_id, ["agent_1", "agent_2", "agent_3"])

# Verify agents have it
skills = system.get_agent_capabilities("agent_1")
print(f"Agent has {len(skills)} skills")
```

### 3. Track Usage (1 minute)

```python
# Log when an agent uses the skill
system.report_skill_usage(
    agent_id="agent_1",
    skill_id=skill_id,
    execution_time_ms=250.5,
    success=True
)

print("Usage tracked!")
```

### 4. Check Statistics (1 minute)

```python
# See overall statistics
stats = system.get_skill_stats()
print(f"Total skills: {stats['total_skills']}")
print(f"Published: {stats['published_skills']}")
print(f"Confidence: {stats['average_confidence']:.1%}")
```

## Common Tasks

### Get Agent's Skills

```python
skills = system.get_agent_capabilities("agent_1")
for skill in skills:
    print(f"- {skill['name']} (v{skill['version']})")
```

### Search for Skills

```python
from skill_system import SkillLibraryManager, DatabaseManager

db = DatabaseManager()
library = SkillLibraryManager(db)

results = library.search_skills("analyze", category="analysis")
for skill in results:
    print(f"Found: {skill['name']}")
```

### Revoke a Skill

```python
from skill_system import SkillInheritanceSystem, DatabaseManager

db = DatabaseManager()
inheritance = SkillInheritanceSystem(db)

inheritance.revoke_skill_from_agent("agent_1", skill_id)
print("Skill revoked")
```

### Export and Share Skills

```python
# Export a skill
exported = system.export_skill(skill_id)

# Import into another system
other_system = UniVersSkillSystem(db_path='/tmp/other.db')
new_skill_id = other_system.import_skill(exported)

print(f"Imported as: {new_skill_id}")
```

### Create Skill Versions

```python
from skill_system import SkillLibraryManager, DatabaseManager, SkillSchema

db = DatabaseManager()
library = SkillLibraryManager(db)

new_code = "def improved_function(): pass"
new_schema = SkillSchema(inputs={}, outputs={}, required_inputs=[], required_outputs=[])

library.create_skill_version(
    skill_id=skill_id,
    new_code=new_code,
    new_schema=new_schema,
    author="dev_team",
    changelog="Improved performance by 50%"
)
```

## Examples

### Example 1: Data Analysis Skill

```python
# Create a skill from a data analysis task
task_result = {
    'inputs': {'csv': 'sales.csv'},
    'outputs': {'summary': 'report.txt', 'plot': 'chart.png'},
    'operations': ['read', 'transform', 'aggregate', 'plot']
}

skill_id = system.learn_from_task(
    task_description="Analyze sales data by month",
    task_result=task_result,
    task_type="analysis",
    author="analytics_team"
)

# Distribute to reporting agents
system.distribute_skill(skill_id, ["report_agent_1", "report_agent_2"])
```

### Example 2: Web Scraping Skill

```python
# Create a skill for web research
task_result = {
    'inputs': {'url': 'https://example.com'},
    'outputs': {'data': 'json_data', 'status': 'success'},
    'operations': ['fetch', 'parse', 'validate']
}

skill_id = system.learn_from_task(
    task_description="Scrape and parse website data",
    task_result=task_result,
    task_type="web_scraping",
    author="research_team"
)

# Give to research agents
system.distribute_skill(skill_id, ["research_agent_1", "research_agent_2"])
```

### Example 3: Code Generation Skill

```python
# Create a skill for code generation
task_result = {
    'inputs': {'spec': 'requirement string'},
    'outputs': {'code': 'python_file', 'tests': 'test_file'},
    'operations': ['generate', 'test', 'format', 'validate']
}

skill_id = system.learn_from_task(
    task_description="Generate Python code from specifications",
    task_result=task_result,
    task_type="code_generation",
    author="engineering_team"
)

# Distribute to coding agents
system.distribute_skill(skill_id, ["coder_agent_1", "coder_agent_2"])
```

## Troubleshooting

### Issue: Skill has low confidence score

```python
# Check the confidence score
stats = system.get_skill_stats()
avg_conf = stats['average_confidence']

if avg_conf < 0.5:
    print("⚠️  Low confidence - add more test examples")
    # Add examples when creating skills:
    skill_id = system.learn_from_task(
        ...,
        examples=[
            {'inputs': {...}, 'outputs': {...}},
            {'inputs': {...}, 'outputs': {...}},
            # Add more examples
        ]
    )
```

### Issue: Agent doesn't have a skill

```python
# Verify distribution
from skill_system import SkillInheritanceSystem, DatabaseManager

db = DatabaseManager()
inheritance = SkillInheritanceSystem(db)

agent_skills = inheritance.get_agent_skills("agent_1")
if not any(s['skill_id'] == skill_id for s in agent_skills):
    # Skill not found, try distributing again
    inheritance.grant_skill_to_agent("agent_1", skill_id)
```

### Issue: Database locked

```python
# Use a different database path
system = UniVersSkillSystem(db_path='/tmp/new_skills.db')
```

## Performance Tips

1. **Batch Distribution**: Distribute multiple skills at once
   ```python
   for skill_id in skill_ids:
       system.distribute_skill(skill_id, agent_list)
   ```

2. **Log Usage Efficiently**: Report multiple at once
   ```python
   for agent in agents:
       system.report_skill_usage(..., execution_time_ms=time, success=True)
   ```

3. **Search by Category**: Filter before searching
   ```python
   from skill_system import SkillLibraryManager, DatabaseManager
   db = DatabaseManager()
   lib = SkillLibraryManager(db)
   
   # Much faster than searching all skills
   analysis_skills = lib.search_skills("analyze", category="analysis")
   ```

## API Quick Reference

| Task | Code |
|------|------|
| Create skill | `system.learn_from_task(...)` |
| Distribute | `system.distribute_skill(skill_id, agents)` |
| Check capabilities | `system.get_agent_capabilities(agent_id)` |
| Log usage | `system.report_skill_usage(...)` |
| Get stats | `system.get_skill_stats()` |
| Export | `system.export_skill(skill_id)` |
| Import | `system.import_skill(data)` |

## Next Steps

1. **Read Full Documentation**: See `SKILL_SYSTEM_README.md` for complete details
2. **Run Tests**: `python3 test_skill_system.py` to see it in action
3. **Integrate**: Use in your agent workflows
4. **Contribute**: Add new features and skill categories

## Database Location

Default: `/agent/home/universe/skills.db`

View database contents:
```bash
sqlite3 /agent/home/universe/skills.db
sqlite> .schema
sqlite> SELECT name, version, status FROM skills;
```

## Support

For issues and questions:
1. Check `SKILL_SYSTEM_README.md` for detailed documentation
2. Review test cases in `test_skill_system.py`
3. Check inline docstrings in `skill_system.py`

## Summary

The UniVerse Skill System enables:

✓ **Automatic learning** from completed tasks
✓ **Intelligent code generation** with AI assistance
✓ **Skill validation** with confidence scoring
✓ **Multi-agent distribution** of capabilities
✓ **Usage tracking** and analytics
✓ **Inter-universe sharing** via export/import

Start creating and sharing skills today!

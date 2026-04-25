# UniVerse Skill Generation System

## Overview

The UniVerse Skill Generation System is an autonomous engine that allows agents to learn, generate, validate, and share capabilities. It enables the automatic creation of reusable skills from completed tasks, with multi-agent distribution and inheritance.

**File Location:** `/agent/home/universe/skill_system.py`

## Architecture

The system is composed of five integrated components:

```
┌─────────────────────────────────────────────────────────────┐
│          UniVersSkillSystem (Main Coordinator)             │
└──────────┬──────────────┬──────────────┬──────────────┬────┘
           │              │              │              │
      ┌────▼────┐   ┌─────▼────┐  ┌────▼────┐  ┌─────▼─────┐
      │Extractor│   │Generator │  │Validator│  │  Library  │
      │          │   │          │  │         │  │ Manager   │
      └────┬────┘   └─────┬────┘  └────┬────┘  └─────┬─────┘
           │              │             │            │
      Extract       Generate      Validate      Publish
      Patterns      Code          Skills       Skills
           │              │             │            │
           └──────────────┴─────────────┴────────────┘
                          │
                    ┌─────▼──────────┐
                    │ Inheritance    │
                    │ System         │
                    │ (Distribution) │
                    └────────────────┘
```

## Core Components

### 1. **SkillExtractor**
Analyzes completed tasks and extracts reusable patterns.

```python
from skill_system import SkillExtractor

extractor = SkillExtractor()

pattern = extractor.extract_from_task(
    task_description="Analyze sales data and generate report",
    task_result={
        'inputs': {'data': 'sales.csv'},
        'outputs': {'report': 'analysis.pdf'},
        'operations': ['load', 'clean', 'analyze']
    },
    task_type="data_analysis"
)
```

**Features:**
- Automatic input/output key extraction
- Data transformation identification
- Complexity scoring (0-1 scale)
- Skill category classification

**Categories Supported:**
- `CODING` - Python, JavaScript, SQL, Bash
- `ANALYSIS` - Data processing, statistical analysis
- `COMMUNICATION` - Email, formatting, summarization
- `RESEARCH` - Web scraping, API calls
- `AUTOMATION` - File operations, deployment

### 2. **SkillGenerator**
Generates Python implementations from extracted patterns and examples.

```python
from skill_system import SkillGenerator

generator = SkillGenerator(db_manager)

code, schema, documentation = generator.generate_skill(
    pattern=pattern,
    examples=[
        {
            'inputs': {'data': [1, 2, 3]},
            'outputs': {'sum': 6}
        }
    ],
    category="analysis"
)
```

**Generates:**
- Type-hinted Python functions
- Input/output schema definitions
- Complete docstrings with examples
- Error handling and validation code

### 3. **SkillValidator**
Tests skill implementations and assigns confidence scores.

```python
from skill_system import SkillValidator

validator = SkillValidator(db_manager)

validation = validator.validate_skill(
    skill_code=code,
    schema=schema,
    test_data=[
        {'inputs': {'x': 5}, 'outputs': {'y': 10}},
        {'inputs': {'x': 3}, 'outputs': {'y': 6}}
    ]
)

print(f"Confidence: {validation.confidence_score}")  # 0.0 - 1.0
print(f"Tests passed: {validation.test_passed}/{validation.test_total}")
```

**Validation Metrics:**
- Test pass/fail rates
- Error detection
- Execution time tracking
- Memory usage profiling
- Confidence scoring (0-1)

### 4. **SkillLibraryManager**
Manages skill storage, versioning, and discovery.

```python
from skill_system import SkillLibraryManager, ValidationResult

library = SkillLibraryManager(db_manager)

# Publish a skill
skill_id = library.publish_skill(
    name="AnalyzeSalesData",
    code=code,
    schema=schema,
    category="analysis",
    author="universe_admin",
    validation_result=validation,
    dependencies=["DataLoader", "Reporter"]
)

# Search for skills
results = library.search_skills("analyze", category="analysis")

# Get specific skill
skill = library.get_skill_by_name("AnalyzeSalesData")

# Create new version
library.create_skill_version(
    skill_id=skill_id,
    new_code=updated_code,
    new_schema=updated_schema,
    author="dev_team",
    changelog="Fixed bug in data cleaning logic"
)
```

**Features:**
- Unique skill identification and naming
- Semantic versioning (major.minor.patch)
- Dependency tracking
- Skill search and discovery
- Version history management

### 5. **SkillInheritanceSystem**
Distributes skills across agents and tracks usage.

```python
from skill_system import SkillInheritanceSystem

inheritance = SkillInheritanceSystem(db_manager)

# Grant skill to single agent
inheritance.grant_skill_to_agent("agent_1", skill_id)

# Distribute to multiple agents
distribution_results = inheritance.distribute_skill_to_agents(
    skill_id,
    ["agent_1", "agent_2", "agent_3"]
)

# Get agent capabilities
agent_skills = inheritance.get_agent_skills("agent_1")

# Log usage
inheritance.log_skill_usage(
    agent_id="agent_1",
    skill_id=skill_id,
    execution_time_ms=250.5,
    success=True
)

# Upgrade skill version
inheritance.upgrade_agent_skill("agent_1", skill_id, "1.0.2")

# Get top-used skills
top_skills = inheritance.get_top_skills(limit=10)
```

## Main Unified Interface

### UniVersSkillSystem
The primary interface that coordinates all components.

```python
from skill_system import UniVersSkillSystem

system = UniVersSkillSystem(db_path='/agent/home/universe/skills.db')

# Complete workflow: Extract → Generate → Validate → Publish
skill_id = system.learn_from_task(
    task_description="Analyze customer data",
    task_result={
        'inputs': {'csv_file': 'customers.csv'},
        'outputs': {'report': 'analysis.html'},
        'operations': ['load', 'clean', 'segment', 'report']
    },
    task_type="analysis",
    author="automation_team",
    examples=[
        {
            'inputs': {'csv_file': 'sample.csv'},
            'outputs': {'report': 'output.html'}
        }
    ]
)

# Distribute the new skill
distribution = system.distribute_skill(skill_id, ["agent_1", "agent_2"])

# Check agent capabilities
capabilities = system.get_agent_capabilities("agent_1")

# Report skill usage
system.report_skill_usage(
    agent_id="agent_1",
    skill_id=skill_id,
    execution_time_ms=150,
    success=True
)

# Export skill for sharing
exported = system.export_skill(skill_id)

# Import skill from another universe
imported_id = system.import_skill(exported)

# Get system statistics
stats = system.get_skill_stats()
print(f"Total skills: {stats['total_skills']}")
print(f"Published: {stats['published_skills']}")
print(f"Avg confidence: {stats['average_confidence']:.2f}")
```

## Data Models

### SkillSchema
Defines input/output structure for a skill.

```python
from skill_system import SkillSchema

schema = SkillSchema(
    inputs={
        'data': {'type': 'list', 'description': 'Input data'},
        'threshold': {'type': 'float', 'description': 'Threshold value'}
    },
    outputs={
        'result': {'type': 'dict', 'description': 'Analysis result'},
        'metrics': {'type': 'dict', 'description': 'Performance metrics'}
    },
    required_inputs=['data'],
    required_outputs=['result']
)
```

### SkillMetadata
Stores skill metadata and lifecycle information.

```python
from skill_system import SkillMetadata

metadata = SkillMetadata(
    skill_id="a1b2c3d4e5f6g7h8",
    name="AnalyzeSalesData",
    category="analysis",
    version="1.0.0",
    created_at=datetime.datetime.now(),
    updated_at=datetime.datetime.now(),
    author="team_lead",
    status="published",
    confidence_score=0.92,
    dependencies=["DataLoader", "Reporter"],
    tags=["sales", "analytics", "reporting"]
)
```

### ValidationResult
Results from skill validation.

```python
from skill_system import ValidationResult

result = ValidationResult(
    is_valid=True,
    confidence_score=0.95,
    test_passed=19,
    test_failed=1,
    test_total=20,
    error_messages=[],
    execution_time_ms=125.5,
    memory_used_mb=2.3
)
```

## Database Schema

The system uses SQLite with the following tables:

### skills
Stores skill implementations and metadata.

```sql
CREATE TABLE skills (
    skill_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    version TEXT NOT NULL,
    status TEXT,  -- 'draft', 'validated', 'published', 'deprecated'
    code TEXT NOT NULL,
    schema_json TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    author TEXT,
    confidence_score REAL,
    usage_count INTEGER,
    last_used TIMESTAMP,
    error_count INTEGER,
    test_results_json TEXT
)
```

### skill_dependencies
Tracks dependencies between skills.

```sql
CREATE TABLE skill_dependencies (
    id INTEGER PRIMARY KEY,
    skill_id TEXT NOT NULL,
    dependency_skill_id TEXT NOT NULL,
    dependency_type TEXT,  -- 'required', 'optional'
    created_at TIMESTAMP
)
```

### skill_inheritance
Tracks which agents have which skills.

```sql
CREATE TABLE skill_inheritance (
    id INTEGER PRIMARY KEY,
    agent_id TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    inherited_at TIMESTAMP,
    status TEXT,  -- 'pending', 'active', 'disabled', 'removed'
    usage_count INTEGER,
    last_used TIMESTAMP,
    version_used TEXT
)
```

### skill_execution_log
Logs skill executions for metrics.

```sql
CREATE TABLE skill_execution_log (
    id INTEGER PRIMARY KEY,
    skill_id TEXT NOT NULL,
    agent_id TEXT,
    execution_timestamp TIMESTAMP,
    status TEXT,  -- 'success', 'failed', 'error'
    input_data TEXT,
    output_data TEXT,
    execution_time_ms REAL,
    error_message TEXT
)
```

### skill_versions
Historical versions of skills.

```sql
CREATE TABLE skill_versions (
    version_id INTEGER PRIMARY KEY,
    skill_id TEXT NOT NULL,
    version TEXT NOT NULL,
    code TEXT NOT NULL,
    schema_json TEXT NOT NULL,
    created_at TIMESTAMP,
    author TEXT,
    changelog TEXT
)
```

## Complete Example Workflow

```python
#!/usr/bin/env python3
"""
Complete example of UniVerse Skill Generation System
"""

from skill_system import UniVersSkillSystem
import json

# Initialize system
system = UniVersSkillSystem()

# ============================================================================
# STEP 1: Learn from a completed task
# ============================================================================

# Represent a data analysis task that was completed successfully
data_analysis_task = {
    'inputs': {
        'csv_file': 'sales_data_2024.csv',
        'metrics': ['revenue', 'units_sold', 'customer_count']
    },
    'outputs': {
        'summary_report': 'Monthly analysis report',
        'visualizations': 'Charts and graphs',
        'insights': 'Key business insights'
    },
    'operations': [
        'read_csv',
        'validate_data',
        'aggregate_by_month',
        'calculate_metrics',
        'generate_visualizations',
        'write_report'
    ],
    'data_volume': 50000,
    'success': True
}

# Extract pattern and create skill
skill_id = system.learn_from_task(
    task_description="Analyze monthly sales data and generate executive report",
    task_result=data_analysis_task,
    task_type="data_analysis",
    author="data_science_team",
    examples=[
        {
            'inputs': {'csv_file': 'sample.csv'},
            'outputs': {'summary_report': 'report.html', 'visualizations': 'charts.png'}
        }
    ]
)

print(f"✓ Created skill: {skill_id}")

# ============================================================================
# STEP 2: Distribute skill to agents that need it
# ============================================================================

agents_that_need_skill = [
    "analytics_agent_1",
    "analytics_agent_2",
    "reporting_agent_1"
]

distribution = system.distribute_skill(skill_id, agents_that_need_skill)
print(f"✓ Distributed to {sum(distribution.values())}/{len(agents_that_need_skill)} agents")

# ============================================================================
# STEP 3: Verify agents have the skill
# ============================================================================

for agent_id in agents_that_need_skill:
    agent_skills = system.get_agent_capabilities(agent_id)
    print(f"✓ Agent '{agent_id}' now has {len(agent_skills)} skills")

# ============================================================================
# STEP 4: Simulate agents using the skill
# ============================================================================

# Agent 1 executes the skill successfully
system.report_skill_usage(
    agent_id="analytics_agent_1",
    skill_id=skill_id,
    execution_time_ms=2500.5,
    success=True
)

# Agent 2 executes the skill successfully
system.report_skill_usage(
    agent_id="analytics_agent_2",
    skill_id=skill_id,
    execution_time_ms=2100.3,
    success=True
)

# Agent 3 had an error
system.report_skill_usage(
    agent_id="reporting_agent_1",
    skill_id=skill_id,
    execution_time_ms=1800.0,
    success=False,
    error_message="Insufficient data for report generation"
)

print("✓ Logged skill usage for all agents")

# ============================================================================
# STEP 5: Get system statistics
# ============================================================================

stats = system.get_skill_stats()

print("\n=== System Statistics ===")
print(f"Total skills created: {stats['total_skills']}")
print(f"Published skills: {stats['published_skills']}")
print(f"Average confidence: {stats['average_confidence']:.2%}")
print(f"Categories: {', '.join(stats['categories'])}")
print(f"Total skill usage: {stats['total_usage']}")

# ============================================================================
# STEP 6: Export skill for sharing with other universes
# ============================================================================

exported_skill = system.export_skill(skill_id)
exported_json = json.dumps(exported_skill, indent=2, default=str)
print(f"\n✓ Exported skill ({len(exported_json)} bytes)")

# ============================================================================
# STEP 7: Import skill into another universe
# ============================================================================

# Create a new system instance (could be in another universe)
other_system = UniVersSkillSystem(db_path='/tmp/other_universe_skills.db')

imported_skill_id = other_system.import_skill(exported_skill)
print(f"✓ Imported skill into other universe: {imported_skill_id}")

print("\n" + "="*60)
print("Workflow completed successfully!")
print("="*60)
```

## Testing

The system includes comprehensive unit tests:

```bash
cd /agent/home/universe
python3 test_skill_system.py
```

**Test Coverage:**
- 20 test cases
- All major components
- Integration workflows
- Error handling

**Run Results:**
```
Tests run: 20
Successes: 20
Failures: 0
Errors: 0
```

## Key Features

### 1. **Automatic Skill Extraction**
- Identifies reusable patterns from completed tasks
- Classifies into predefined categories
- Calculates task complexity

### 2. **Intelligent Code Generation**
- Creates type-hinted Python functions
- Includes docstrings and examples
- Adds error handling and validation

### 3. **Comprehensive Validation**
- Tests skills on sample data
- Calculates confidence scores
- Tracks execution metrics

### 4. **Skill Library Management**
- Stores skills in versioned database
- Tracks dependencies
- Enables skill discovery

### 5. **Multi-Agent Distribution**
- Grants skills to individual agents
- Distributes to groups of agents
- Tracks skill usage metrics

### 6. **Skill Export/Import**
- Serialize skills for sharing
- Distribute across universes
- Preserve version history

## Performance Characteristics

- **Skill Extraction**: <100ms per task
- **Code Generation**: <200ms per skill
- **Validation**: <500ms (depends on test data)
- **Database Operations**: <50ms per operation
- **Skill Distribution**: <10ms per agent

## Error Handling

The system implements comprehensive error handling:

```python
try:
    skill_id = system.learn_from_task(...)
except Exception as e:
    print(f"Error creating skill: {e}")

# Validation with low confidence
if validation.confidence_score < 0.5:
    print(f"Warning: Low confidence skill ({validation.confidence_score})")
    # Still published but in 'draft' status

# Check validation errors
if validation.error_messages:
    print(f"Validation errors: {validation.error_messages}")
```

## Integration with UniVerse

The skill system integrates seamlessly with the broader UniVerse architecture:

1. **Agent Coordination**: Skills are assigned to agents that execute them
2. **Execution Tracking**: Usage is logged for metrics and analysis
3. **Knowledge Sharing**: Skills are distributed across agent networks
4. **Continuous Learning**: New patterns are extracted from successful task executions

## Configuration

Default configuration in `/agent/home/universe/skills.db`:

```python
db_path = '/agent/home/universe/skills.db'
system = UniVersSkillSystem(db_path=db_path)
```

To use a different database:

```python
system = UniVersSkillSystem(db_path='/custom/path/skills.db')
```

## Logging

The system uses Python's standard logging module:

```python
import logging

logging.getLogger('skill_system').setLevel(logging.DEBUG)
```

Log levels include:
- **INFO**: Skill operations (created, published, distributed)
- **WARNING**: Low-confidence skills, validation issues
- **ERROR**: Failed operations, data integrity issues

## Future Enhancements

Planned features:

1. **Machine Learning-Based Optimization**: Use LLMs for more sophisticated code generation
2. **Skill Composition**: Combine multiple skills into complex workflows
3. **Performance Analytics**: Track and optimize skill performance
4. **Collaborative Skills**: Skills that require coordination between multiple agents
5. **Skill Marketplace**: Trade and share skills between universes

## API Reference

See inline docstrings in `/agent/home/universe/skill_system.py` for complete API documentation.

## License

Part of the UniVerse framework.

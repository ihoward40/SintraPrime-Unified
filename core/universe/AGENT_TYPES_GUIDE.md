# UniVerse Agent Types Guide

## Overview

The UniVerse ecosystem includes 6 specialized agent types, each designed for specific roles in the swarm. All agents inherit from `BaseAgent` and implement three core methods: `execute()`, `learn()`, and `collaborate()`.

## Quick Reference

| Agent Type | Role | Primary Function | Key Tools |
|------------|------|------------------|-----------|
| **Analyst** | Research & Analysis | Pattern identification, summarization | Web search, document analysis, visualization |
| **Executor** | Code & Deployment | Code execution, API calls | Python/Bash/JS/SQL exec, API integration |
| **Learner** | Skill Generation | Learning from examples | Code analysis, pattern extraction |
| **Coordinator** | Task Management | Delegation, negotiation | Agent discovery, priority queues |
| **Vision** | Image/Video Processing | Visual understanding, OCR | Computer vision, diagram parsing, UI understanding |
| **Guard** | Security & Compliance | Validation, compliance checks | Signature verification, audit logging |

---

## 1. AnalystAgent

**Purpose**: Research, analyze data, identify patterns, and generate reports.

### Capabilities
- Research and data gathering
- Pattern recognition and trend analysis
- Report generation
- Recommendation synthesis
- Source documentation

### Input Schema
```json
{
  "query": "string",           // Research query
  "sources": ["string"],       // Data sources to analyze
  "analysis_type": "string",   // summary | pattern | trend | comparison
  "depth": "string"            // shallow | medium | deep
}
```

### Output Schema
```json
{
  "analysis_type": "string",
  "findings": ["string"],      // Key findings
  "patterns": [{}],            // Identified patterns
  "recommendations": ["string"],
  "confidence": 0.0,           // 0-1 confidence score
  "sources_used": ["string"]
}
```

### Example Usage
```python
import json
import asyncio
from agent_types import AgentRegistry

async def run_analysis():
    analyst = AgentRegistry.create_agent("analyst", "ResearchBot")
    
    task = {
        "query": "Market trends in AI",
        "analysis_type": "trend",
        "depth": "deep",
        "sources": ["industry_reports", "research_papers"]
    }
    
    result = await analyst.execute("task_001", json.dumps(task))
    print(result["result"]["findings"])
    
    # Learn from successful analysis
    skill_id = await analyst.learn("task_001", result["result"])

asyncio.run(run_analysis())
```

### Skills Generated
- `analysis_pattern`: Reusable patterns from analyses
- Pattern extraction templates
- Analysis templates for specific domains

---

## 2. ExecutorAgent

**Purpose**: Execute code, run API calls, manage deployments.

### Capabilities
- Python, Bash, JavaScript, SQL execution
- API calls and integrations
- Deployment and provisioning
- System operations
- Database operations
- Security-aware sandboxing

### Input Schema
```json
{
  "code": "string",            // Code to execute
  "language": "string",        // python | bash | javascript | sql
  "environment": {},           // Environment variables
  "timeout": 30                // Execution timeout in seconds
}
```

### Output Schema
```json
{
  "status": "string",          // success | failure | timeout
  "output": "string",          // Execution output
  "error": "string",           // Error message if failed
  "execution_time_ms": 0,
  "artifacts": ["string"]      // Created files/outputs
}
```

### Example Usage
```python
import json
import asyncio
from agent_types import AgentRegistry

async def run_code():
    executor = AgentRegistry.create_agent("executor", "CodeRunner")
    
    task = {
        "code": "print('Hello Universe')",
        "language": "python",
        "timeout": 30
    }
    
    result = await executor.execute("task_002", json.dumps(task))
    print(f"Output: {result['result']['output']}")
    print(f"Execution time: {result['result']['execution_time_ms']}ms")

asyncio.run(run_code())
```

### Security Features
- Dangerous pattern detection (e.g., `__import__`, `eval`, `exec`)
- Timeout protection
- Isolated execution environment
- Error containment

### Skills Generated
- `executable_pattern`: Reusable code patterns
- Successful execution templates
- Language-specific patterns

---

## 3. LearnerAgent

**Purpose**: Generate new skills from task examples and generalize patterns.

### Capabilities
- Pattern extraction from examples
- Skill generalization to broader applicability
- Knowledge synthesis and documentation
- Best practice identification
- Skill reusability assessment

### Input Schema
```json
{
  "task_examples": [
    {
      "input": "string",
      "output": "string",
      "context": "string"
    }
  ],
  "skill_category": "string",           // Category of skill
  "generalization_level": "string"      // specific | general | abstract
}
```

### Output Schema
```json
{
  "skill_id": "string",
  "skill_name": "string",
  "skill_description": "string",
  "pattern": {},                        // Learned pattern
  "applicability": ["string"],          // Use cases
  "confidence": 0.0,                    // 0-1 confidence
  "documentation": "string"
}
```

### Example Usage
```python
import json
import asyncio
from agent_types import AgentRegistry

async def learn_skill():
    learner = AgentRegistry.create_agent("learner", "SkillBuilder")
    
    task = {
        "task_examples": [
            {"input": "hello", "output": "HELLO", "context": "uppercase"},
            {"input": "world", "output": "WORLD", "context": "uppercase"},
            {"input": "test", "output": "TEST", "context": "uppercase"},
        ],
        "skill_category": "text_transformation",
        "generalization_level": "general"
    }
    
    result = await learner.execute("task_003", json.dumps(task))
    skill = result["result"]
    print(f"Learned skill: {skill['skill_name']}")
    print(f"Applicable to: {skill['applicability']}")

asyncio.run(learn_skill())
```

### Generalization Levels
- **specific**: Single use case, high precision
- **general**: Multiple similar use cases
- **abstract**: Broad principle applicable across domains

### Skills Generated
- `meta_learning`: Patterns about learning itself
- Generalized skill templates
- Knowledge synthesis patterns

---

## 4. CoordinatorAgent

**Purpose**: Manage task delegation, resource allocation, and execution planning.

### Capabilities
- Task dependency analysis
- Agent capability matching
- Resource allocation optimization
- Execution planning and sequencing
- Load balancing
- Risk assessment and contingency planning

### Input Schema
```json
{
  "tasks": [
    {
      "task_id": "string",
      "type": "string",
      "priority": 1,
      "dependencies": ["string"]
    }
  ],
  "available_agents": [
    {
      "agent_id": "string",
      "capabilities": ["string"],
      "capacity": 0.0
    }
  ],
  "optimization_goal": "string"  // speed | quality | cost | balanced
}
```

### Output Schema
```json
{
  "task_plan": [
    {
      "task_id": "string",
      "assigned_agent": "string",
      "sequence": 1,
      "estimated_duration_ms": 0
    }
  ],
  "resource_allocation": {},
  "estimated_total_time_ms": 0,
  "risk_assessment": "string",
  "contingency_plans": ["string"]
}
```

### Example Usage
```python
import json
import asyncio
from agent_types import AgentRegistry

async def coordinate_tasks():
    coordinator = AgentRegistry.create_agent("coordinator", "TaskMaster")
    
    task = {
        "tasks": [
            {"task_id": "t1", "type": "analysis", "priority": 1},
            {"task_id": "t2", "type": "execution", "priority": 2},
            {"task_id": "t3", "type": "validation", "priority": 1},
        ],
        "available_agents": [
            {"agent_id": "analyst_1", "capabilities": ["analysis"]},
            {"agent_id": "executor_1", "capabilities": ["execution"]},
            {"agent_id": "guard_1", "capabilities": ["validation"]},
        ],
        "optimization_goal": "speed"
    }
    
    result = await coordinator.execute("task_004", json.dumps(task))
    plan = result["result"]
    print(f"Total estimated time: {plan['estimated_total_time_ms']}ms")
    for step in plan["task_plan"]:
        print(f"  {step['sequence']}: {step['task_id']} → {step['assigned_agent']}")

asyncio.run(coordinate_tasks())
```

### Optimization Goals
- **speed**: Minimize execution time
- **quality**: Maximize output quality
- **cost**: Minimize resource usage
- **balanced**: Balance all factors

### Skills Generated
- `coordination_pattern`: Reusable task plans
- Optimization patterns
- Resource allocation templates

---

## 5. VisionAgent

**Purpose**: Process images and videos, understand UI, extract text.

### Capabilities
- Object detection
- Optical character recognition (OCR)
- Scene understanding and description
- Diagram parsing and relationship analysis
- UI element identification
- Visual relationship analysis
- Result caching for performance

### Input Schema
```json
{
  "image_path": "string",      // Path to image/video
  "analysis_type": "string",   // object_detection | ocr | scene_understanding | diagram_parsing
  "focus_areas": ["string"]    // Specific areas to focus on
}
```

### Output Schema
```json
{
  "analysis_type": "string",
  "objects_detected": [
    {
      "object": "string",
      "confidence": 0.0,
      "location": {}
    }
  ],
  "text_extracted": "string",
  "scene_description": "string",
  "insights": ["string"],
  "ui_elements": [
    {
      "element_type": "string",
      "description": "string"
    }
  ]
}
```

### Example Usage
```python
import json
import asyncio
from agent_types import AgentRegistry

async def analyze_image():
    vision = AgentRegistry.create_agent("vision", "EyesBot")
    
    task = {
        "image_path": "/path/to/screenshot.png",
        "analysis_type": "object_detection",
        "focus_areas": ["buttons", "text", "images"]
    }
    
    result = await vision.execute("task_005", json.dumps(task))
    analysis = result["result"]
    print(f"Scene: {analysis['scene_description']}")
    print(f"Objects found: {len(analysis['objects_detected'])}")
    for obj in analysis['objects_detected']:
        print(f"  - {obj['object']} (confidence: {obj['confidence']:.2f})")

asyncio.run(analyze_image())
```

### Analysis Types
- **object_detection**: Identify and locate objects
- **ocr**: Extract text from images
- **scene_understanding**: Describe overall scene and context
- **diagram_parsing**: Analyze flowcharts, diagrams, relationships

### Caching
Vision Agent automatically caches results per image path, improving performance for repeated analyses.

### Skills Generated
- `vision_pattern`: Reusable visual patterns
- Object detection templates
- Scene understanding patterns

---

## 6. GuardAgent

**Purpose**: Ensure security, validate compliance, perform auditing.

### Capabilities
- Signature verification
- Compliance checking against policies
- Audit logging and reporting
- Permission validation
- Risk assessment
- Security policy enforcement
- Violation detection and recommendations

### Input Schema
```json
{
  "target": "string",          // Target to validate
  "check_type": "string",      // signature | compliance | audit | permission
  "policy": {},                // Security policy to apply
  "severity_level": "string"   // low | medium | high | critical
}
```

### Output Schema
```json
{
  "status": "string",          // approved | rejected | review_needed
  "check_type": "string",
  "violations": [
    {
      "violation": "string",
      "severity": "string",
      "recommendation": "string"
    }
  ],
  "risk_score": 0.0,           // 0-1 risk score
  "audit_trail": ["string"],
  "approval_required": false
}
```

### Example Usage
```python
import json
import asyncio
from agent_types import AgentRegistry

async def validate_security():
    guard = AgentRegistry.create_agent("guard", "SecurityGuard")
    
    task = {
        "target": "code_package_v1.2.3",
        "check_type": "signature",
        "severity_level": "critical"
    }
    
    result = await guard.execute("task_006", json.dumps(task))
    check = result["result"]
    print(f"Status: {check['status']}")
    print(f"Risk Score: {check['risk_score']:.2f}")
    for violation in check['violations']:
        print(f"  ⚠ {violation['violation']} ({violation['severity']})")
        print(f"    → {violation['recommendation']}")

asyncio.run(validate_security())
```

### Check Types
- **signature**: Verify authenticity and integrity signatures
- **compliance**: Check against security policies
- **audit**: Review access logs and activities
- **permission**: Validate user/entity permissions

### Risk Assessment
Risk scores are calculated based on:
- Number of violations detected
- Severity levels of violations
- Policy adherence metrics
- Historical patterns

### Skills Generated
- `security_pattern`: Reusable security checks
- Compliance validation patterns
- Audit templates

---

## Common Patterns

### Using the Agent Registry

```python
from agent_types import AgentRegistry

# Create agent
agent = AgentRegistry.create_agent("analyst", "MyAgent")

# Get available types
types = AgentRegistry.get_available_types()
# → ['analyst', 'executor', 'learner', 'coordinator', 'vision', 'guard']

# Get schemas for an agent type
schemas = AgentRegistry.get_agent_schema("analyst")
print(schemas["input_schema"])
print(schemas["output_schema"])
```

### Task Execution Pattern

```python
import json
import asyncio
from agent_types import AgentRegistry

async def execute_task():
    agent = AgentRegistry.create_agent("analyst", "Bot")
    
    # Prepare task as JSON
    task_input = {
        "query": "example",
        "analysis_type": "summary"
    }
    
    # Execute
    result = await agent.execute("task_id", json.dumps(task_input))
    
    # Check result
    if result["status"] == "success":
        print(result["result"])
    else:
        print(f"Error: {result['error']}")

asyncio.run(execute_task())
```

### Learning and Skill Acquisition

```python
# After successful execution
skill_id = await agent.learn(task_id, result["result"])

if skill_id:
    print(f"Agent acquired skill: {skill_id}")
    
    # Check skills
    status = agent.get_status()
    print(f"Agent now has {status['skills_count']} skills")
```

### Agent Collaboration

```python
# One agent requests information from another
message = {
    "request_type": "share_analysis",
    "query": "recent_findings"
}

response = await analyst.collaborate(executor, message)
print(response)
```

---

## Agent Methods

All agents implement these core methods:

### `execute(task_id: str, command: str) → Dict[str, Any]`
Execute a task asynchronously.

```python
result = await agent.execute("task_001", json.dumps(task_input))
# Returns: {"status": "success"|"failed", "task_id": "...", "result": {...}}
```

### `learn(task_id: str, result: Dict[str, Any]) → Optional[str]`
Learn from task results and potentially generate new skills.

```python
skill_id = await agent.learn(task_id, task_result)
# Returns: skill_id if skill generated, None otherwise
```

### `collaborate(other_agent: BaseAgent, message: Dict[str, Any]) → Dict[str, Any]`
Send messages to and receive responses from other agents.

```python
response = await agent1.collaborate(agent2, {"request_type": "share_data"})
# Returns: collaboration response
```

### `get_status() → Dict[str, Any]`
Get current agent status and metrics.

```python
status = agent.get_status()
# Returns: {
#   "agent_id": "...",
#   "name": "...",
#   "role": "analyst|executor|learner|coordinator|vision|guard",
#   "status": "idle|executing|...",
#   "current_task_id": "...",
#   "skills_count": 0,
#   "performance": {...}
# }
```

### `add_skill(skill_id: str, skill_def: Dict[str, Any]) → None`
Manually add a skill to the agent.

```python
skill_def = {
    "type": "custom_skill",
    "description": "My custom skill"
}
agent.add_skill("skill_custom_001", skill_def)
```

### `to_dict() → Dict[str, Any]`
Serialize agent to dictionary for storage.

```python
agent_data = agent.to_dict()
# Can be stored in database or JSON
```

---

## Performance Metrics

Each agent tracks performance:

```python
status = agent.get_status()
metrics = status["performance"]
# {
#   "tasks_completed": 5,
#   "tasks_failed": 1,
#   "success_rate": 0.833,
#   "avg_execution_time_ms": 1250
# }
```

---

## Database Integration

Agent state can be stored in the database:

```python
import json
from run_agent_memory_sql import run_agent_memory_sql

agent_data = agent.to_dict()

# Store agent
query = """
INSERT INTO agents (agent_id, name, role, data)
VALUES (?, ?, ?, ?)
"""
run_agent_memory_sql(query, (
    agent_data["agent_id"],
    agent_data["name"],
    agent_data["role"],
    json.dumps(agent_data)
))
```

---

## Error Handling

All agents handle errors gracefully:

```python
try:
    result = await agent.execute("task_id", json.dumps(task))
    if result["status"] == "failed":
        print(f"Task failed: {result['error']}")
except Exception as e:
    print(f"Exception: {str(e)}")
```

---

## Extending Agents

To create a custom agent:

```python
from base_agent import BaseAgent

class CustomAgent(BaseAgent):
    def __init__(self, name: str, specialization: Optional[str] = None):
        super().__init__(name, "custom", specialization)
    
    async def execute(self, task_id: str, command: str) -> Dict[str, Any]:
        # Implementation
        pass
    
    async def learn(self, task_id: str, result: Dict[str, Any]) -> Optional[str]:
        # Implementation
        pass
    
    async def collaborate(self, other_agent: BaseAgent, message: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation
        pass
```

---

## Schema Validation

Each agent type has defined input/output schemas:

```python
from agent_types import InputSchema, OutputSchema

# Validate input
analyst_input = InputSchema.ANALYST
# {
#   "type": "object",
#   "properties": {
#     "query": {"type": "string", ...},
#     "analysis_type": {...},
#     ...
#   },
#   "required": ["query", "analysis_type"]
# }

# Get expected output format
analyst_output = OutputSchema.ANALYST
```

---

## Prompt Templates

Each agent has Claude integration prompts:

```python
from agent_types import PromptTemplates

prompt = PromptTemplates.ANALYST.format(
    task="task_001",
    query="What are AI trends?",
    analysis_type="trend",
    depth="deep"
)
```

---

## Summary

The 6 UniVerse agent types provide a flexible, extensible foundation for building swarm-based AI systems:

1. **AnalystAgent** - Research and pattern recognition
2. **ExecutorAgent** - Code and deployment execution
3. **LearnerAgent** - Skill generation and learning
4. **CoordinatorAgent** - Task management and delegation
5. **VisionAgent** - Visual content analysis
6. **GuardAgent** - Security and compliance

All agents support skill acquisition, collaboration, and database persistence, enabling a truly adaptive swarm ecosystem.

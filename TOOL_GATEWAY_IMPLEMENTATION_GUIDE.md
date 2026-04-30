# ToolGateway Implementation Guide

Comprehensive step-by-step guide for implementing ToolGateway integration in SintraPrime Phase 16 agents.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Phase 1: Preparation](#phase-1-preparation)
3. [Phase 2: Core Implementation](#phase-2-core-implementation)
4. [Phase 3: Agent Integration](#phase-3-agent-integration)
5. [Phase 4: Testing](#phase-4-testing)
6. [Phase 5: Deployment](#phase-5-deployment)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

For experienced developers, here's the 5-minute setup:

```bash
# 1. Copy core implementation
cp core/tool_gateway.py /agent/home/SintraPrime-Unified/core/

# 2. Copy configuration
cp config/tool_gateway_config.yaml /agent/home/SintraPrime-Unified/config/

# 3. Run automated wiring script
cd /agent/home/SintraPrime-Unified
bash fix_scripts/wire_tool_gateway.sh ./phase16 ./config

# 4. Run tests
python3 -m pytest tests/test_tool_gateway_integration.py -v

# 5. Review documentation
cat TOOL_GATEWAY_WIRING_DIAGRAM.md
```

---

## Phase 1: Preparation

### 1.1 Verify Requirements

Before starting, verify you have:

```bash
# Check Python version (3.8+)
python3 --version

# Check pytest is available
python3 -m pytest --version

# Check repository structure
ls -la /agent/home/SintraPrime-Unified/phase16/
ls -la /agent/home/SintraPrime-Unified/core/
```

### 1.2 Review Documentation

Read in this order:

1. **TOOL_GATEWAY_WIRING_DIAGRAM.md** - Understand overall architecture
2. **TOOL_GATEWAY_INTEGRATION_BASE_TEMPLATE.md** - Learn base patterns
3. **FIX_TEMPLATES_AGENT_TOOL_GATEWAY_WIRING.md** - Review agent-specific details

### 1.3 Create Backup

```bash
# Backup all phase 16 agents before making changes
cd /agent/home/SintraPrime-Unified
tar czf phase16_backup_$(date +%s).tar.gz phase16/

# Backup core directory
tar czf core_backup_$(date +%s).tar.gz core/
```

---

## Phase 2: Core Implementation

### 2.1 Copy ToolGateway Core

The core ToolGateway implementation provides the central registry and invocation engine.

```bash
# Ensure core directory exists
mkdir -p /agent/home/SintraPrime-Unified/core

# Copy the core implementation
cp /agent/home/core/tool_gateway.py /agent/home/SintraPrime-Unified/core/

# Verify it's in place
ls -la /agent/home/SintraPrime-Unified/core/tool_gateway.py
```

### 2.2 Test Core Implementation

```bash
cd /agent/home/SintraPrime-Unified

python3 << 'EOF'
# Quick sanity check of core
from core.tool_gateway import ToolGateway, ToolNotFoundError

# Create gateway
gateway = ToolGateway(mode="single_agent")

# Register a test tool
def test_tool():
    return {"status": "ok"}

gateway.register_tool(
    agent_id="test_agent",
    tool_name="test_tool",
    handler=test_tool,
    description="Test tool"
)

# List tools
tools = gateway.list_tools("test_agent")
print(f"✓ Tools registered: {len(tools)}")

# Invoke tool
result = gateway.invoke_tool(
    requesting_agent_id="test_agent",
    tool_name="test_tool",
    args={}
)
print(f"✓ Tool invoked: {result}")

print("✓ Core ToolGateway working correctly!")
EOF
```

### 2.3 Set Up Configuration

```bash
# Ensure config directory exists
mkdir -p /agent/home/SintraPrime-Unified/config

# Copy configuration template
cp /agent/home/config/tool_gateway_config.yaml \
   /agent/home/SintraPrime-Unified/config/

# Verify configuration
cat /agent/home/SintraPrime-Unified/config/tool_gateway_config.yaml | head -20
```

---

## Phase 3: Agent Integration

This section shows how to integrate each agent. Start with MoE Router, then Jurisdiction Engine (least dependencies).

### 3.1 Integrate MoE Router

**File**: `phase16/moe_router/router.py`

#### Step 1: Add Import

```python
# At the top of phase16/moe_router/router.py
from core.tool_gateway import ToolGateway
```

#### Step 2: Update `__init__`

```python
class MoERouter:
    def __init__(self, gateway: ToolGateway = None):  # Add parameter
        self.agent_id = "moe_router"
        self.gateway = gateway or ToolGateway()       # Add initialization
        # ... rest of __init__
        self._register_tools()                         # Add this call
```

#### Step 3: Implement `_register_tools()`

```python
def _register_tools(self):
    """Register all MoE Router tools."""
    
    self.gateway.register_tool(
        agent_id=self.agent_id,
        tool_name='route_request',
        handler=self.route_request,
        schema={
            'type': 'object',
            'properties': {
                'request': {'type': 'string'},
                'context': {'type': 'object'}
            },
            'required': ['request']
        },
        description='Route request to appropriate specialist',
        tags=['routing', 'primary']
    )
    
    self.gateway.register_tool(
        agent_id=self.agent_id,
        tool_name='list_specialists',
        handler=self.list_specialists,
        description='List available specialists',
        tags=['routing', 'discovery']
    )
    
    self.gateway.register_tool(
        agent_id=self.agent_id,
        tool_name='get_routing_rules',
        handler=self.get_routing_rules,
        description='Get routing configuration',
        tags=['routing', 'config']
    )
```

#### Step 4: Verify Handlers Exist

Ensure these methods exist in the class:
- `route_request(request: str, context: dict = None) -> dict`
- `list_specialists() -> list`
- `get_routing_rules() -> dict`

If not, implement them:

```python
def route_request(self, request: str, context: dict = None) -> dict:
    """Route request to specialist."""
    # Implementation from existing code
    return {
        'target_specialist': 'jurisdiction_engine',
        'confidence': 0.95
    }

def list_specialists(self) -> list:
    """List available specialists."""
    return [
        {'name': 'jurisdiction_engine', 'type': 'rules'},
        {'name': 'precedent_ai', 'type': 'case_law'}
    ]

def get_routing_rules(self) -> dict:
    """Get routing rules."""
    return {'rules': []}
```

### 3.2 Integrate Jurisdiction Engine

**File**: `phase16/jurisdiction_engine/jurisdiction_engine.py`

Follow the same 4-step process:

1. Add import: `from core.tool_gateway import ToolGateway`
2. Update `__init__` with gateway parameter and initialization
3. Implement `_register_tools()` for jurisdiction tools
4. Ensure handlers exist:
   - `get_jurisdiction(case: dict) -> dict`
   - `get_rules(jurisdiction: str) -> dict`
   - `validate_jurisdiction(jurisdiction: str) -> dict`

### 3.3 Integrate Other Agents

Follow the same pattern for remaining agents:

**3.3.1 Precedent AI**
- Tools: `find_precedents`, `predict_outcome`, `calculate_confidence`
- Handlers: Implement async-aware wrappers for long-running searches

**3.3.2 Multimodal Court**
- Tools: `process_audio`, `process_handwriting`, `process_video`
- Handlers: Ensure file path handling is correct

**3.3.3 Hierarchical Orchestrator**
- Tools: `coordinate_agents`, `collect_results`, `resolve_conflicts`
- Handlers: Implement agent coordination logic

**3.3.4 PARL Core**
- Tools: `parallel_execute`, `collect_episodes`, `update_policy`
- Handlers: Implement learning pipeline

**3.3.5 Confidential Computing**
- Design phase; determine tools needed for secure computation

---

## Phase 4: Testing

### 4.1 Unit Tests

Test individual agent wiring:

```bash
cd /agent/home/SintraPrime-Unified

python3 << 'EOF'
from core.tool_gateway import ToolGateway
from phase16.moe_router.router import MoERouter
from phase16.jurisdiction_engine.jurisdiction_engine import JurisdictionEngine

# Test MoE Router
print("Testing MoE Router...")
gateway = ToolGateway(mode="single_agent")
router = MoERouter(gateway=gateway)

tools = gateway.list_tools("moe_router")
print(f"  ✓ MoE Router registered {len(tools)} tools")

# Test Jurisdiction Engine
print("Testing Jurisdiction Engine...")
jurisdiction = JurisdictionEngine(gateway=gateway)

tools = gateway.list_tools("jurisdiction_engine")
print(f"  ✓ Jurisdiction Engine registered {len(tools)} tools")

# Grant permissions
gateway.grant_permission("moe_router", "jurisdiction_engine")

# Test cross-agent invocation
print("Testing cross-agent invocation...")
result = gateway.invoke_tool(
    requesting_agent_id="moe_router",
    tool_name="get_rules",
    args={"jurisdiction": "federal"},
    provider_agent_id="jurisdiction_engine"
)
print(f"  ✓ Cross-agent invocation successful: {result['jurisdiction']}")

print("\n✓ All integration tests passed!")
EOF
```

### 4.2 Integration Tests

Run comprehensive test suite:

```bash
cd /agent/home/SintraPrime-Unified

# Run all tests
python3 -m pytest tests/test_tool_gateway_integration.py -v

# Run specific test class
python3 -m pytest tests/test_tool_gateway_integration.py::TestToolGatewayBasics -v

# Run with coverage
python3 -m pytest tests/test_tool_gateway_integration.py --cov=core --cov=phase16
```

### 4.3 Performance Tests

Test system performance:

```bash
cd /agent/home/SintraPrime-Unified

python3 << 'EOF'
import time
from core.tool_gateway import ToolGateway
from phase16.moe_router.router import MoERouter

gateway = ToolGateway(mode="multi_agent")
router = MoERouter(gateway=gateway)

# Test invocation throughput
start = time.time()
for i in range(100):
    gateway.invoke_tool(
        requesting_agent_id="moe_router",
        tool_name="list_specialists",
        args={}
    )
elapsed = time.time() - start

print(f"100 invocations in {elapsed:.2f}s")
print(f"Average: {elapsed/100*1000:.2f}ms per invocation")

# Expected: >500 invocations per second (2ms average)
invocations_per_sec = 100 / elapsed
print(f"Throughput: {invocations_per_sec:.0f} invocations/second")

if invocations_per_sec > 500:
    print("✓ Performance acceptable")
else:
    print("⚠ Performance below target")
EOF
```

---

## Phase 5: Deployment

### 5.1 Pre-Deployment Checklist

```bash
# Verify all files in place
[ -f /agent/home/SintraPrime-Unified/core/tool_gateway.py ] && echo "✓ Core" || echo "✗ Core"
[ -f /agent/home/SintraPrime-Unified/config/tool_gateway_config.yaml ] && echo "✓ Config" || echo "✗ Config"
[ -f /agent/home/SintraPrime-Unified/tests/test_tool_gateway_integration.py ] && echo "✓ Tests" || echo "✗ Tests"

# Verify all agents have been updated
grep -r "from core.tool_gateway import ToolGateway" /agent/home/SintraPrime-Unified/phase16/ | wc -l
# Expected: at least 6 (one per agent)

# Run full test suite
python3 -m pytest /agent/home/SintraPrime-Unified/tests/test_tool_gateway_integration.py -v --tb=short
```

### 5.2 Integration with Existing Code

#### Update Agent Initialization

If agents are instantiated elsewhere, update instantiation:

```python
# OLD:
router = MoERouter()

# NEW:
from core.tool_gateway import ToolGateway
gateway = ToolGateway()
router = MoERouter(gateway=gateway)
```

#### Update Agent Discovery

If there's agent discovery/registration, ensure ToolGateway is initialized first:

```python
# In agent factory or registry:

from core.tool_gateway import ToolGateway

class AgentFactory:
    def __init__(self):
        self.gateway = ToolGateway()
        self.agents = {}
    
    def create_agent(self, agent_type: str) -> Agent:
        if agent_type == "moe_router":
            agent = MoERouter(gateway=self.gateway)
        elif agent_type == "jurisdiction_engine":
            agent = JurisdictionEngine(gateway=self.gateway)
        # ... more agents
        
        self.agents[agent.agent_id] = agent
        return agent
```

### 5.3 Environment Setup

```bash
# Set Python path
export PYTHONPATH="/agent/home/SintraPrime-Unified:$PYTHONPATH"

# Verify imports work
python3 -c "from core.tool_gateway import ToolGateway; print('✓ Imports OK')"

# Run basic sanity check
python3 << 'EOF'
from core.tool_gateway import ToolGateway
gateway = ToolGateway()
print(f"✓ ToolGateway initialized in {gateway.mode} mode")
EOF
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'core.tool_gateway'"

**Solution**: Verify PYTHONPATH includes the repo root

```bash
# Check current PYTHONPATH
echo $PYTHONPATH

# Add if needed
export PYTHONPATH="/agent/home/SintraPrime-Unified:$PYTHONPATH"

# Verify
python3 -c "from core.tool_gateway import ToolGateway; print('OK')"
```

### Issue: "ToolNotFoundError: Tool 'X' not found"

**Possible causes**:
1. Tool not registered
2. Agent not initialized with gateway
3. Permission not granted (in single_agent mode)

**Solution**:
```python
# Check what tools are available
tools = gateway.discover_tools(requesting_agent_id)
print([t['name'] for t in tools])

# Verify registration
tools = gateway.list_tools(agent_id)  # Check specific agent
```

### Issue: "PermissionError: Agent X cannot access tools from Y"

**Solution**: Grant permission

```python
gateway.grant_permission("agent_x", "agent_y")
```

### Issue: Agent `__init__` signature mismatch

**Problem**: Existing code doesn't pass gateway parameter

**Solution 1**: Update all instantiation sites

```python
# Before
agent = MyAgent()

# After
gateway = ToolGateway()
agent = MyAgent(gateway=gateway)
```

**Solution 2**: Make gateway parameter truly optional

```python
class MyAgent:
    def __init__(self, *args, gateway: ToolGateway = None, **kwargs):
        # ... handle other params
        self.gateway = gateway or ToolGateway()
```

### Issue: Tool handler errors not clear

**Solution**: Add try/catch wrapper

```python
def tool_with_error_handling(self, **args):
    """Tool with explicit error handling."""
    try:
        # implementation
        return result
    except Exception as e:
        logger.error(f"Tool failed: {e}", exc_info=True)
        raise ValueError(f"Tool execution failed: {str(e)}")
```

### Issue: Schema validation errors

**Problem**: Arguments don't match schema

**Solution**: Verify schema matches handler signature

```python
# Handler signature:
def process_document(self, path: str, depth: str = 'medium'):
    pass

# Matching schema:
schema = {
    'type': 'object',
    'properties': {
        'path': {'type': 'string'},
        'depth': {'type': 'string', 'enum': ['shallow', 'medium', 'deep']}
    },
    'required': ['path']
}
```

### Issue: Tests fail with "Gateway not in multi_agent mode"

**Solution**: Explicitly set mode when needed

```python
# For testing:
gateway = ToolGateway(mode="single_agent")
gateway.grant_permission("agent1", "agent2")

# For production:
gateway = ToolGateway(mode="multi_agent")
```

---

## Validation Checklist

Complete this checklist after implementation:

### Core Setup
- [ ] `core/tool_gateway.py` exists and is importable
- [ ] `config/tool_gateway_config.yaml` exists with valid YAML
- [ ] Test suite runs without errors
- [ ] All tests pass (or are skipped appropriately)

### MoE Router
- [ ] Imports ToolGateway
- [ ] Has gateway parameter in `__init__`
- [ ] Registers 3 tools
- [ ] Can invoke own tools
- [ ] Can discover other agent tools

### Jurisdiction Engine
- [ ] Imports ToolGateway
- [ ] Has gateway parameter in `__init__`
- [ ] Registers 3 tools
- [ ] Handles jurisdiction lookups
- [ ] Provides rule validation

### Other Agents (repeat for each)
- [ ] Imports ToolGateway
- [ ] Has gateway parameter in `__init__`
- [ ] Registers expected tools
- [ ] Tool invocations work correctly
- [ ] Error handling is in place

### Integration
- [ ] Cross-agent tool invocation works
- [ ] Permissions are enforced (single_agent mode)
- [ ] Metrics are being tracked
- [ ] Invocation history is recorded
- [ ] Performance is acceptable (>500 inv/sec)

### Documentation
- [ ] All agents have docstrings for tools
- [ ] Tool schemas are documented
- [ ] Error cases are documented
- [ ] Dependencies are clearly marked

---

## Support & References

For questions or issues:

1. **Review documentation** (in order):
   - TOOL_GATEWAY_WIRING_DIAGRAM.md
   - TOOL_GATEWAY_INTEGRATION_BASE_TEMPLATE.md
   - FIX_TEMPLATES_AGENT_TOOL_GATEWAY_WIRING.md

2. **Check test examples**:
   - tests/test_tool_gateway_integration.py

3. **Reference implementations**:
   - Each agent's _register_tools() method
   - MockAgent class in test suite

4. **Common patterns**:
   - Basic integration (MockAgent)
   - Error handling (try/except blocks)
   - Async support (Precedent AI)
   - File handling (Multimodal Court)

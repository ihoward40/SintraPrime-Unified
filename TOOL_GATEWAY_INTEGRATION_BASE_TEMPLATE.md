# ToolGateway Integration Base Template

## Overview
This template provides the foundational pattern for integrating any SintraPrime agent with the ToolGateway. Use this as a reference when wiring agents to enable tool discovery, registration, and invocation.

## Core Integration Pattern

### Step 1: Import ToolGateway

```python
from core.tool_gateway import ToolGateway, ToolNotFoundError, ToolExecutionError
```

### Step 2: Add Gateway Initialization

```python
class MyAgent:
    def __init__(self, gateway: ToolGateway = None):
        """Initialize agent with optional gateway injection."""
        self.agent_id = "my_agent"
        self.gateway = gateway or ToolGateway()
        self._register_tools()
    
    def _register_tools(self):
        """Register all tools provided by this agent."""
        # Tools are registered here
        pass
```

### Step 3: Register Agent Tools

Each agent should register the tools it provides. Tools are defined with:
- **name**: Unique tool identifier
- **handler**: Python callable implementing the tool
- **schema**: JSON schema describing input parameters
- **description**: Human-readable explanation
- **tags**: Optional categorization tags

```python
def _register_tools(self):
    """Register all tools provided by this agent."""
    
    # Example Tool 1: Simple tool with no arguments
    self.gateway.register_tool(
        agent_id=self.agent_id,
        tool_name='list_specialists',
        handler=self.list_specialists,
        description='List available specialist models',
        tags=['routing', 'discovery']
    )
    
    # Example Tool 2: Tool with structured input
    self.gateway.register_tool(
        agent_id=self.agent_id,
        tool_name='route_request',
        handler=self.route_request,
        schema={
            'type': 'object',
            'properties': {
                'request': {
                    'type': 'string',
                    'description': 'The incoming request to route'
                },
                'context': {
                    'type': 'object',
                    'description': 'Additional context'
                }
            },
            'required': ['request']
        },
        description='Route request to appropriate specialist',
        tags=['routing']
    )
    
    # Example Tool 3: Tool with complex schema
    self.gateway.register_tool(
        agent_id=self.agent_id,
        tool_name='process_document',
        handler=self.process_document,
        schema={
            'type': 'object',
            'properties': {
                'document_path': {
                    'type': 'string',
                    'description': 'Path to document'
                },
                'analysis_depth': {
                    'type': 'string',
                    'enum': ['shallow', 'medium', 'deep'],
                    'description': 'Depth of analysis'
                }
            },
            'required': ['document_path']
        },
        description='Process and analyze documents',
        tags=['processing', 'analysis']
    )
```

### Step 4: Implement Tool Handlers

Tool handlers are standard Python methods:

```python
def list_specialists(self) -> List[Dict[str, str]]:
    """List all available specialists."""
    return [
        {'name': 'jurisdiction_engine', 'type': 'rules'},
        {'name': 'precedent_ai', 'type': 'case_law'},
        {'name': 'multimodal_court', 'type': 'analysis'}
    ]

def route_request(self, request: str, context: dict = None) -> Dict[str, Any]:
    """Route request to appropriate specialist."""
    # Route logic here
    return {
        'target_specialist': 'jurisdiction_engine',
        'confidence': 0.95,
        'reasoning': 'Request matches jurisdiction query pattern'
    }

def process_document(self, document_path: str, analysis_depth: str = 'medium') -> Dict[str, Any]:
    """Process a document."""
    # Processing logic here
    return {
        'status': 'success',
        'document': document_path,
        'depth': analysis_depth,
        'results': {}
    }
```

### Step 5: Invoke External Tools

To use tools from other agents:

```python
def invoke_specialist_tool(self, specialist: str, tool: str, args: dict) -> Any:
    """Invoke a tool from another agent."""
    try:
        result = self.gateway.invoke_tool(
            requesting_agent_id=self.agent_id,
            tool_name=tool,
            args=args,
            provider_agent_id=specialist
        )
        return result
    except ToolNotFoundError as e:
        logger.error(f"Tool not found: {e}")
        # Handle gracefully
        return None
    except ToolExecutionError as e:
        logger.error(f"Tool execution failed: {e}")
        # Handle gracefully
        return None

def discover_available_tools(self) -> List[Dict[str, Any]]:
    """Discover all available tools in the system."""
    return self.gateway.discover_tools(
        requesting_agent_id=self.agent_id
    )

def discover_tools_by_tag(self, tag: str) -> List[Dict[str, Any]]:
    """Discover tools by tag."""
    return self.gateway.discover_tools(
        requesting_agent_id=self.agent_id,
        tag_filter=tag
    )
```

### Step 6: Complete Example Class

```python
from core.tool_gateway import ToolGateway
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class MyAgent:
    """Example agent with ToolGateway integration."""
    
    def __init__(self, gateway: ToolGateway = None):
        self.agent_id = "my_agent"
        self.gateway = gateway or ToolGateway()
        self._register_tools()
    
    def _register_tools(self):
        """Register all tools provided by this agent."""
        self.gateway.register_tool(
            agent_id=self.agent_id,
            tool_name='tool_1',
            handler=self.tool_1,
            description='First tool'
        )
        
        self.gateway.register_tool(
            agent_id=self.agent_id,
            tool_name='tool_2',
            handler=self.tool_2,
            schema={
                'type': 'object',
                'properties': {
                    'input': {'type': 'string'}
                },
                'required': ['input']
            },
            description='Second tool with input'
        )
    
    def tool_1(self) -> Dict[str, str]:
        """First tool implementation."""
        return {'status': 'ok', 'result': 'Tool 1 executed'}
    
    def tool_2(self, input: str) -> Dict[str, str]:
        """Second tool implementation."""
        return {'status': 'ok', 'result': f'Processed: {input}'}
    
    def use_external_tool(self, tool_name: str, args: dict) -> Any:
        """Use a tool from another agent."""
        try:
            return self.gateway.invoke_tool(
                requesting_agent_id=self.agent_id,
                tool_name=tool_name,
                args=args
            )
        except Exception as e:
            logger.error(f"Failed to invoke {tool_name}: {e}")
            return None
    
    def list_all_tools(self) -> List[Dict[str, Any]]:
        """List all available tools."""
        return self.gateway.discover_tools(self.agent_id)
```

## Testing the Integration

```python
import unittest
from core.tool_gateway import ToolGateway

class TestToolGatewayIntegration(unittest.TestCase):
    
    def setUp(self):
        self.gateway = ToolGateway(mode="single_agent")
        self.agent = MyAgent(gateway=self.gateway)
    
    def test_tool_registration(self):
        """Test that tools are registered."""
        tools = self.gateway.list_tools(self.agent.agent_id)
        self.assertEqual(len(tools), 2)
        names = [t['name'] for t in tools]
        self.assertIn('tool_1', names)
        self.assertIn('tool_2', names)
    
    def test_tool_discovery(self):
        """Test tool discovery."""
        tools = self.agent.list_all_tools()
        self.assertGreater(len(tools), 0)
    
    def test_tool_invocation(self):
        """Test invoking a tool."""
        result = self.gateway.invoke_tool(
            requesting_agent_id=self.agent.agent_id,
            tool_name='tool_1',
            args={}
        )
        self.assertEqual(result['status'], 'ok')
    
    def test_tool_with_args(self):
        """Test tool invocation with arguments."""
        result = self.gateway.invoke_tool(
            requesting_agent_id=self.agent.agent_id,
            tool_name='tool_2',
            args={'input': 'test'}
        )
        self.assertIn('test', result['result'])
```

## Key Patterns

### 1. Dependency Injection
Always support optional gateway injection for testability:
```python
def __init__(self, gateway: ToolGateway = None):
    self.gateway = gateway or ToolGateway()
```

### 2. Tool Handler Conventions
- Use clear, descriptive names
- Include docstrings
- Return standardized response format
- Raise appropriate exceptions

### 3. Cross-Agent Communication
```python
# Always check for tool existence
tools = self.gateway.discover_tools(self.agent_id)
available = [t['name'] for t in tools]

if 'desired_tool' in available:
    result = self.gateway.invoke_tool(...)
```

### 4. Error Handling
```python
try:
    result = self.gateway.invoke_tool(...)
except ToolNotFoundError:
    # Handle tool not found
    pass
except ToolExecutionError as e:
    # Handle execution failure
    logger.error(f"Execution failed: {e}")
```

## Migration Checklist

For agents not yet using ToolGateway:

- [ ] Add `from core.tool_gateway import ToolGateway` import
- [ ] Modify `__init__` to accept optional `gateway` parameter
- [ ] Call `self.gateway = gateway or ToolGateway()` in `__init__`
- [ ] Create `_register_tools()` method
- [ ] Identify all public methods that should be tools
- [ ] Call `gateway.register_tool()` for each
- [ ] Test tool registration
- [ ] Add error handling for tool invocation
- [ ] Update unit tests to pass mock gateway
- [ ] Document tool schema in code

## Common Issues & Solutions

### Issue: Tool not found after registration
**Solution**: Ensure agent_id matches when registering and invoking

### Issue: PermissionError on tool invocation
**Solution**: Call `gateway.grant_permission()` before invoking in single_agent mode

### Issue: Handler function errors are not clear
**Solution**: Wrap handler in try/except and provide detailed error messages

### Issue: Tool schema validation fails
**Solution**: Verify schema matches actual handler parameters

## Configuration

Tools can be auto-registered from configuration files:

```yaml
tools:
  my_agent:
    - name: tool_1
      description: "Description"
      schema: {...}
    - name: tool_2
      description: "Description"
      schema: {...}
```

See `tool_gateway_config.yaml` for full configuration options.

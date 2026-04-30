# ToolGateway Agent Wiring Diagram & Architecture

## System Overview

The ToolGateway provides a centralized mechanism for SintraPrime Phase 16 agents to discover, register, and invoke tools across the system. This enables seamless inter-agent communication and tool sharing.

```
┌─────────────────────────────────────────────────────────────────┐
│                      ToolGateway Registry                        │
│  (Central tool discovery, registration, and invocation hub)      │
└─────────────────────────────────────────────────────────────────┘
                              ▲
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
    ┌─────────┐         ┌──────────────────┐  ┌──────────┐
    │  MoE    │         │ Hierarchical     │  │Jurisdiction
    │ Router  │         │ Orchestrator     │  │  Engine
    └─────────┘         └──────────────────┘  └──────────┘
        │                     │                     │
        ├─────────────────────┼─────────────────────┤
        │                     │                     │
        ▼                     ▼                     ▼
    ┌──────────┐         ┌──────────────┐      ┌────────────┐
    │Precedent │         │ Multimodal   │      │ PARL Core  │
    │   AI     │         │   Court      │      │ (Learning) │
    └──────────┘         └──────────────┘      └────────────┘
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              │
                     ┌────────▼────────┐
                     │ Confidential    │
                     │ Computing       │
                     └─────────────────┘
```

## Agent Dependency Graph

### MoE Router (Request Routing)
```
MoE Router
├─ PROVIDES:
│  ├─ route_request()        → Routes incoming requests to specialists
│  ├─ list_specialists()     → Returns available specialist models
│  └─ get_routing_rules()    → Returns current routing configuration
│
├─ DEPENDS ON:
│  ├─ Jurisdiction Engine    → For legal jurisdiction rules
│  ├─ Precedent AI           → For case law patterns
│  ├─ Multimodal Court       → For document analysis routing
│  └─ PARL Core              → For learned routing policies
│
└─ STATUS: 🟡 Partial (needs integration)
```

### Hierarchical Orchestrator (Multi-Agent Coordination)
```
Hierarchical Orchestrator
├─ PROVIDES:
│  ├─ coordinate_agents()    → Orchestrates multi-agent execution
│  ├─ collect_results()      → Aggregates specialist results
│  └─ resolve_conflicts()    → Resolves disagreements between agents
│
├─ DEPENDS ON:
│  ├─ MoE Router             → For routing decisions
│  ├─ Jurisdiction Engine    → For legal analysis
│  ├─ Precedent AI           → For outcome prediction
│  └─ Multimodal Court       → For document analysis
│
└─ STATUS: 🔴 Blocked (waiting for MoE Router)
```

### Jurisdiction Engine (Legal Rules)
```
Jurisdiction Engine
├─ PROVIDES:
│  ├─ get_jurisdiction()     → Determines jurisdiction for case
│  ├─ get_rules()            → Returns jurisdiction-specific rules
│  └─ validate_jurisdiction()→ Validates jurisdiction applicability
│
├─ DEPENDS ON:
│  ├─ Federal Agency Navigator
│  └─ Docket Feeds
│
└─ STATUS: 🟢 Ready (no blockers)
```

### Precedent AI (Case Law Analysis)
```
Precedent AI
├─ PROVIDES:
│  ├─ find_precedents()      → Searches case law (async, long-running)
│  ├─ predict_outcome()      → Predicts case outcomes
│  └─ calculate_confidence() → Calculates confidence intervals
│
├─ DEPENDS ON:
│  ├─ Jurisdiction Engine    → For jurisdiction-specific rules
│  ├─ Case Law Engine        → For precedent database
│  └─ ML Models              → For outcome prediction
│
└─ STATUS: 🟡 Partial (needs async support)
```

### Multimodal Court (Document Analysis)
```
Multimodal Court
├─ PROVIDES:
│  ├─ process_audio()        → Transcribes and analyzes audio
│  ├─ process_handwriting()  → OCRs handwritten documents
│  └─ process_video()        → Extracts key moments from video
│
├─ DEPENDS ON:
│  ├─ OCR Service            → For handwriting recognition
│  ├─ Audio Transcription    → For speech-to-text
│  └─ Video Analysis Models  → For video processing
│
└─ STATUS: 🔴 Blocked (needs file handling)
```

### PARL Core (Reinforcement Learning)
```
PARL Core
├─ PROVIDES:
│  ├─ parallel_execute()     → Runs parallel agent execution (async)
│  ├─ collect_episodes()     → Collects learning episodes
│  └─ update_policy()        → Updates agent policies via RL
│
├─ DEPENDS ON:
│  ├─ All Phase 16 Agents    → For execution and learning
│  ├─ Episode Store          → For data persistence
│  └─ RL Algorithms          → For policy updates
│
└─ STATUS: 🟡 Partial (needs episode management)
```

### Confidential Computing (Security & Encryption)
```
Confidential Computing
├─ PROVIDES:
│  ├─ TBD                    → Secure computation
│  └─ TBD
│
├─ DEPENDS ON:
│  └─ All other agents       → Provides security layer
│
└─ STATUS: 🟡 Partial (design phase)
```

## Tool Invocation Flow

```
Requesting Agent
      │
      ▼
  ┌─────────────────────────────────────────┐
  │ 1. DISCOVERY                             │
  │    agent.gateway.discover_tools()        │
  │    → Returns available tools             │
  └─────────────────────────────────────────┘
      │
      ▼
  ┌─────────────────────────────────────────┐
  │ 2. SELECTION                            │
  │    Choose tool from discovered list     │
  │    Get tool_name & provider_agent_id    │
  └─────────────────────────────────────────┘
      │
      ▼
  ┌──────────────────────────────────────────────┐
  │ 3. INVOCATION REQUEST                        │
  │    gateway.invoke_tool(                      │
  │      requesting_agent_id,                    │
  │      tool_name,                              │
  │      args,                                   │
  │      provider_agent_id                       │
  │    )                                         │
  └──────────────────────────────────────────────┘
      │
      ▼
  ┌──────────────────────────────────────────────┐
  │ 4. GATEWAY ROUTING                           │
  │    • Check permissions                       │
  │    • Emit invocation receipt                 │
  │    • Validate arguments against schema       │
  │    • Route to provider agent                 │
  └──────────────────────────────────────────────┘
      │
      ▼
  Provider Agent
      │
      ▼
  ┌──────────────────────────────────────────┐
  │ 5. EXECUTION                             │
  │    handler(**args)                       │
  │    • Execute tool logic                  │
  │    • Return result or error              │
  └──────────────────────────────────────────┘
      │
      ▼
  ┌──────────────────────────────────────────────────┐
  │ 6. RESPONSE                                      │
  │    Gateway returns result with metadata:         │
  │    • Invocation ID / receipt                     │
  │    • Execution time (ms)                         │
  │    • Tool metrics (invocation count, etc.)       │
  │    • Error information (if failed)               │
  └──────────────────────────────────────────────────┘
      │
      ▼
  Requesting Agent
      │
      ▼
  ┌──────────────────────────────────────────┐
  │ 7. PROCESSING & STATE UPDATE             │
  │    • Process result                      │
  │    • Update local state                  │
  │    • Execute next steps                  │
  └──────────────────────────────────────────┘
```

## Tool Registration Flow

```
Agent Initialization
      │
      ▼
  ┌──────────────────────────────────────────┐
  │ 1. CREATE GATEWAY INSTANCE               │
  │    self.gateway = ToolGateway()           │
  │    or                                    │
  │    self.gateway = injected_gateway       │
  └──────────────────────────────────────────┘
      │
      ▼
  ┌──────────────────────────────────────────┐
  │ 2. REGISTER TOOLS                        │
  │    self.gateway.register_tool(           │
  │      agent_id='my_agent',                │
  │      tool_name='my_tool',                │
  │      handler=self.my_handler,            │
  │      schema={...},                       │
  │      description='...',                  │
  │      tags=[...]                          │
  │    )                                     │
  └──────────────────────────────────────────┘
      │
      ▼
  ┌──────────────────────────────────────────┐
  │ 3. VALIDATION                            │
  │    • Verify tool name uniqueness         │
  │    • Validate schema format              │
  │    • Check handler is callable           │
  └──────────────────────────────────────────┘
      │
      ▼
  ┌──────────────────────────────────────────┐
  │ 4. STORAGE                               │
  │    Store in registry:                    │
  │    {                                     │
  │      agent_id: {                         │
  │        tool_name: ToolMetadata(...)      │
  │      }                                   │
  │    }                                     │
  └──────────────────────────────────────────┘
      │
      ▼
  ┌──────────────────────────────────────────┐
  │ 5. DISCOVERY AVAILABLE                   │
  │    Tool now discoverable via:            │
  │    gateway.discover_tools()              │
  │    gateway.list_tools(agent_id)          │
  └──────────────────────────────────────────┘
```

## Integration Status Matrix

| Agent | Status | Tools | Impl | Tests | Docs |
|-------|--------|-------|------|-------|------|
| **MoE Router** | 🟡 Partial | 3/3 | 50% | 0% | 100% |
| **Hierarchical Orch.** | 🔴 Blocked | 2/3 | 0% | 0% | 100% |
| **Jurisdiction Engine** | 🟢 Ready | 3/3 | 70% | 60% | 100% |
| **Precedent AI** | 🟡 Partial | 2/3 | 50% | 30% | 100% |
| **Multimodal Court** | 🔴 Blocked | 1/3 | 0% | 0% | 100% |
| **PARL Core** | 🟡 Partial | 2/3 | 40% | 20% | 100% |
| **Confidential Computing** | 🟡 Partial | 0/? | 0% | 0% | 50% |

## Tool Communication Patterns

### Pattern 1: Simple Request-Response
```
Agent A                    ToolGateway              Agent B
  │                            │                      │
  ├─ invoke_tool("tool_1") ──→ │                      │
  │                            ├─ route to Agent B ──→ │
  │                            │                       ├─ execute
  │                            │ ← return result ──── │
  │ ← receive result ──────── │
  │                            │                      │
```

### Pattern 2: Chained Calls
```
Agent A
  ├─ invoke "route_request"
  │  └─ MoE Router executes, calls
  │     ├─ invoke "get_jurisdiction"
  │     │  └─ Jurisdiction Engine
  │     └─ invoke "find_precedents"
  │        └─ Precedent AI
  └─ receive aggregate result
```

### Pattern 3: Parallel Execution (via PARL Core)
```
PARL Core
  ├─ invoke "route_request" to MoE Router ──→ MoE Router
  ├─ invoke "process_document" to Multimodal ──→ Multimodal Court
  └─ invoke "get_rules" to Jurisdiction ──→ Jurisdiction Engine
  
All execute in parallel, PARL Core aggregates results
```

## Permission Model

### Default (Multi-Agent Mode)
```
By default, all agents can invoke all tools.
No explicit permissions required.
Use for development and testing.
```

### Restrictive (Single-Agent Mode)
```
Explicit permission grant required:
gateway.grant_permission('requesting_agent', 'target_agent')

Useful for:
- Unit testing
- Security testing
- Multi-tenant scenarios
```

### Production Configuration
```
Enable in tool_gateway_config.yaml:
  enable_permissions: true

Define matrix in config:
  permissions:
    moe_router:
      - jurisdiction_engine
      - precedent_ai
```

## Caching Strategy

Tools can be cached based on:

```
Tool          │ Default TTL │ Rationale
──────────────┼─────────────┼──────────────────────────
list_specialists   │ 600s    │ Specialists list changes rarely
get_routing_rules  │ 600s    │ Rules stable during session
get_rules          │ 1800s   │ Jurisdiction rules very stable
find_precedents    │ 300s    │ Case law updates regularly
route_request      │ 0s      │ Each request unique
```

## Error Handling Scenarios

```
Scenario                    │ Exception              │ Handling
────────────────────────────┼───────────────────────┼──────────────
Tool not registered         │ ToolNotFoundError     │ Return available tools
Permission denied           │ PermissionError       │ Grant permission
Handler raises exception    │ ToolExecutionError    │ Log, return error
Schema validation fails     │ ValueError            │ Return schema
Timeout exceeded            │ TimeoutError          │ Retry or fail gracefully
```

## Metrics Tracked

```
Per-Tool Metrics:
├─ invocation_count         Total invocations
├─ last_invoked             Timestamp of last use
├─ avg_execution_time_ms    Average latency
├─ p99_execution_time_ms     99th percentile latency
├─ error_count              Number of failures
├─ success_rate             % of successful calls
└─ registered_at            Registration timestamp

Gateway-Level Metrics:
├─ total_tools_registered   Total tools in registry
├─ active_agents            Agents with registered tools
├─ discovery_requests       Discovery queries made
├─ tool_invocations         Total invocations
└─ gateway_uptime           ToolGateway availability
```

## Data Structures

### ToolMetadata
```python
{
  'name': 'route_request',
  'provider_agent_id': 'moe_router',
  'description': 'Route request to appropriate specialist',
  'schema': {
    'type': 'object',
    'properties': {
      'request': {'type': 'string'},
      'context': {'type': 'object'}
    },
    'required': ['request']
  },
  'status': 'active',
  'registered_at': '2024-01-15T10:30:00Z',
  'last_invoked': '2024-01-15T10:45:30Z',
  'invocation_count': 42,
  'tags': ['routing', 'primary']
}
```

### ToolInvocation Record
```python
{
  'tool_name': 'route_request',
  'requesting_agent_id': 'hierarchical_orchestrator',
  'provider_agent_id': 'moe_router',
  'args': {'request': '...', 'context': {...}},
  'result': {'target_specialist': '...', ...},
  'error': None,
  'timestamp': '2024-01-15T10:45:30Z',
  'duration_ms': 125.5
}
```

## Security Considerations

1. **Input Validation**: All arguments validated against tool schema
2. **Authorization**: Permission checks before tool invocation
3. **Audit Trail**: All invocations logged for compliance
4. **Rate Limiting**: Optional per-tool rate limits
5. **Encryption**: Optional TLS for remote gateways
6. **Isolation**: Confidential Computing layer for sensitive data

## Performance Considerations

```
Optimization          │ Implementation
──────────────────────┼──────────────────────────────
Tool Caching          │ In-memory with configurable TTL
Parallel Execution    │ Via PARL Core for concurrent ops
Lazy Registration     │ Tools registered on demand
Schema Validation     │ Optional, skip for performance
Connection Pooling    │ For remote gateway backend
Batch Operations      │ Multiple tools in single call
```

## Deployment Checklist

- [ ] ToolGateway core implementation completed
- [ ] MoE Router wired and tested
- [ ] Jurisdiction Engine wired and tested
- [ ] Hierarchical Orchestrator wired
- [ ] Precedent AI wired with async support
- [ ] Multimodal Court wired with file handling
- [ ] PARL Core wired with episode management
- [ ] Integration tests passing (90%+ coverage)
- [ ] Performance benchmarks met
- [ ] Security review completed
- [ ] Documentation finalized
- [ ] Production deployment

## Next Phases

**Phase 17**: Advanced ToolGateway features
- Remote gateway protocol (for distributed deployment)
- Advanced permission model (roles, groups)
- Tool versioning and compatibility
- Gateway federation (multiple gateways)

**Phase 18**: AI-assisted tool discovery
- Semantic search for tools
- Recommendation system
- Auto-routing based on performance metrics

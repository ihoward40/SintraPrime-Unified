# Fix Templates: Agent ToolGateway Wiring

Agent-specific wiring templates for Phase 16 agents. Each template includes the tools the agent should provide and its dependencies on other agents.

---

## FT-TG001: MoE Router ToolGateway Wiring

**Agent**: `phase16.moe_router.MoERouter`  
**Status**: 🟡 Partial (requires wiring)  
**Priority**: HIGH  

### Tools Provided

| Tool | Handler | Schema | Purpose |
|------|---------|--------|---------|
| `route_request` | `route_request()` | `{request: str, context: object}` | Route request to appropriate specialist |
| `list_specialists` | `list_specialists()` | None | List available specialist models |
| `get_routing_rules` | `get_routing_rules()` | None | Retrieve current routing configuration |

### Dependencies
- Jurisdiction Engine: for legal jurisdiction routing
- Precedent AI: for case law routing
- Multimodal Court: for document analysis routing
- Confidence Scorer: for confidence metrics

### Implementation Template

```python
# phase16/moe_router/router.py
from core.tool_gateway import ToolGateway
from phase16.moe_router.confidence_scorer import ConfidenceScorer

class MoERouter:
    def __init__(self, gateway: ToolGateway = None):
        self.agent_id = "moe_router"
        self.gateway = gateway or ToolGateway()
        self.confidence_scorer = ConfidenceScorer()
        self._register_tools()
    
    def _register_tools(self):
        """Register all MoE Router tools."""
        
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
                        'description': 'Additional context for routing'
                    }
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
            description='List available specialist models',
            tags=['routing', 'discovery']
        )
        
        self.gateway.register_tool(
            agent_id=self.agent_id,
            tool_name='get_routing_rules',
            handler=self.get_routing_rules,
            description='Retrieve current routing configuration',
            tags=['routing', 'config']
        )
    
    def route_request(self, request: str, context: dict = None) -> dict:
        """Route request to appropriate specialist."""
        specialists = self.list_specialists()
        
        # Score each specialist
        scores = {}
        for specialist in specialists:
            score = self.confidence_scorer.score(request, specialist)
            scores[specialist['name']] = score
        
        # Return best match
        best = max(scores.items(), key=lambda x: x[1])
        
        return {
            'target_specialist': best[0],
            'confidence': best[1],
            'alternatives': scores,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def list_specialists(self) -> list:
        """List available specialists."""
        return [
            {'name': 'jurisdiction_engine', 'type': 'rules', 'confidence': 0.95},
            {'name': 'precedent_ai', 'type': 'case_law', 'confidence': 0.92},
            {'name': 'multimodal_court', 'type': 'analysis', 'confidence': 0.88},
        ]
    
    def get_routing_rules(self) -> dict:
        """Get current routing rules."""
        return {
            'rules': [
                {'pattern': 'jurisdiction.*', 'target': 'jurisdiction_engine'},
                {'pattern': 'precedent.*', 'target': 'precedent_ai'},
                {'pattern': 'document.*', 'target': 'multimodal_court'},
            ]
        }
```

### Wiring Checklist
- [ ] Add `from core.tool_gateway import ToolGateway` import
- [ ] Modify `__init__` to accept gateway parameter
- [ ] Add `self.gateway = gateway or ToolGateway()`
- [ ] Implement `_register_tools()` method
- [ ] Call `_register_tools()` in `__init__`
- [ ] Test tool registration
- [ ] Add error handling

---

## FT-TG002: Hierarchical Orchestrator ToolGateway Wiring

**Agent**: `phase16.hierarchical_orchestration.Orchestrator`  
**Status**: 🔴 Blocked (requires MoE Router integration first)  
**Priority**: HIGH  

### Tools Provided

| Tool | Handler | Schema | Purpose |
|------|---------|--------|---------|
| `coordinate_agents` | `coordinate_agents()` | `{agents: array, task: object}` | Orchestrate multi-agent execution |
| `collect_results` | `collect_results()` | `{executions: array}` | Aggregate results from specialists |
| `resolve_conflicts` | `resolve_conflicts()` | `{results: array}` | Resolve agent disagreements |

### Dependencies
- MoE Router: for routing decisions
- Confidence Scorer: for confidence evaluation
- All Phase 16 agents: for execution

### Implementation Template

```python
# phase16/hierarchical_orchestration/orchestrator.py
from core.tool_gateway import ToolGateway

class Orchestrator:
    def __init__(self, gateway: ToolGateway = None):
        self.agent_id = "hierarchical_orchestrator"
        self.gateway = gateway or ToolGateway()
        self._register_tools()
    
    def _register_tools(self):
        """Register orchestrator tools."""
        
        self.gateway.register_tool(
            agent_id=self.agent_id,
            tool_name='coordinate_agents',
            handler=self.coordinate_agents,
            schema={
                'type': 'object',
                'properties': {
                    'agents': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': 'List of agent IDs to coordinate'
                    },
                    'task': {
                        'type': 'object',
                        'description': 'The task to coordinate'
                    }
                },
                'required': ['agents', 'task']
            },
            description='Orchestrate multi-agent execution',
            tags=['orchestration', 'coordination']
        )
        
        self.gateway.register_tool(
            agent_id=self.agent_id,
            tool_name='collect_results',
            handler=self.collect_results,
            schema={
                'type': 'object',
                'properties': {
                    'executions': {
                        'type': 'array',
                        'description': 'Execution results to collect'
                    }
                },
                'required': ['executions']
            },
            description='Aggregate results from specialists',
            tags=['aggregation', 'coordination']
        )
        
        self.gateway.register_tool(
            agent_id=self.agent_id,
            tool_name='resolve_conflicts',
            handler=self.resolve_conflicts,
            schema={
                'type': 'object',
                'properties': {
                    'results': {
                        'type': 'array',
                        'description': 'Conflicting results to resolve'
                    }
                },
                'required': ['results']
            },
            description='Resolve agent disagreements',
            tags=['coordination', 'conflict_resolution']
        )
    
    def coordinate_agents(self, agents: list, task: dict) -> dict:
        """Coordinate multiple agents."""
        results = {}
        for agent_id in agents:
            try:
                # Invoke appropriate tool on agent
                result = self.gateway.invoke_tool(
                    requesting_agent_id=self.agent_id,
                    tool_name='execute_task',
                    args={'task': task},
                    provider_agent_id=agent_id
                )
                results[agent_id] = result
            except Exception as e:
                results[agent_id] = {'error': str(e)}
        
        return {'status': 'complete', 'results': results}
    
    def collect_results(self, executions: list) -> dict:
        """Aggregate execution results."""
        # Aggregation logic
        return {'aggregated': executions, 'count': len(executions)}
    
    def resolve_conflicts(self, results: list) -> dict:
        """Resolve conflicting results."""
        # Conflict resolution logic
        return {'resolved': True, 'consensus': {}}
```

---

## FT-TG003: Jurisdiction Engine ToolGateway Wiring

**Agent**: `phase16.jurisdiction_engine.JurisdictionEngine`  
**Status**: 🟢 Complete (ready for wiring)  
**Priority**: HIGH  

### Tools Provided

| Tool | Handler | Schema | Purpose |
|------|---------|--------|---------|
| `get_jurisdiction` | `get_jurisdiction()` | `{case: object}` | Determine jurisdiction for case |
| `get_rules` | `get_rules()` | `{jurisdiction: string}` | Get jurisdiction-specific rules |
| `validate_jurisdiction` | `validate_jurisdiction()` | `{jurisdiction: string}` | Validate jurisdiction applicability |

### Dependencies
- Federal Agency Navigator: for federal agency rules
- Docket feeds: for case information

### Implementation Template

```python
# phase16/jurisdiction_engine/jurisdiction_engine.py
from core.tool_gateway import ToolGateway

class JurisdictionEngine:
    def __init__(self, gateway: ToolGateway = None):
        self.agent_id = "jurisdiction_engine"
        self.gateway = gateway or ToolGateway()
        self._register_tools()
    
    def _register_tools(self):
        """Register jurisdiction engine tools."""
        
        self.gateway.register_tool(
            agent_id=self.agent_id,
            tool_name='get_jurisdiction',
            handler=self.get_jurisdiction,
            schema={
                'type': 'object',
                'properties': {
                    'case': {
                        'type': 'object',
                        'description': 'Case object with location, type, etc.'
                    }
                },
                'required': ['case']
            },
            description='Determine jurisdiction for case',
            tags=['jurisdiction', 'rules']
        )
        
        self.gateway.register_tool(
            agent_id=self.agent_id,
            tool_name='get_rules',
            handler=self.get_rules,
            schema={
                'type': 'object',
                'properties': {
                    'jurisdiction': {
                        'type': 'string',
                        'description': 'Jurisdiction identifier'
                    }
                },
                'required': ['jurisdiction']
            },
            description='Get jurisdiction-specific rules',
            tags=['rules', 'jurisdiction']
        )
        
        self.gateway.register_tool(
            agent_id=self.agent_id,
            tool_name='validate_jurisdiction',
            handler=self.validate_jurisdiction,
            schema={
                'type': 'object',
                'properties': {
                    'jurisdiction': {
                        'type': 'string',
                        'description': 'Jurisdiction to validate'
                    }
                },
                'required': ['jurisdiction']
            },
            description='Validate jurisdiction applicability',
            tags=['validation', 'jurisdiction']
        )
    
    def get_jurisdiction(self, case: dict) -> dict:
        """Determine jurisdiction for a case."""
        location = case.get('location')
        case_type = case.get('type')
        
        # Jurisdiction determination logic
        jurisdiction = self._determine_jurisdiction(location, case_type)
        
        return {
            'jurisdiction': jurisdiction,
            'confidence': 0.95,
            'basis': 'Geographic location and case type'
        }
    
    def get_rules(self, jurisdiction: str) -> dict:
        """Get rules for jurisdiction."""
        return {
            'jurisdiction': jurisdiction,
            'rules': [
                {'rule': 'Rule 1', 'description': 'Description'},
                {'rule': 'Rule 2', 'description': 'Description'},
            ]
        }
    
    def validate_jurisdiction(self, jurisdiction: str) -> dict:
        """Validate jurisdiction."""
        return {
            'jurisdiction': jurisdiction,
            'valid': True,
            'type': 'Federal Court'
        }
    
    def _determine_jurisdiction(self, location: str, case_type: str) -> str:
        # Implementation
        return "Federal District Court"
```

---

## FT-TG004: Precedent AI ToolGateway Wiring

**Agent**: `phase16.precedent_ai.PrecedentAI`  
**Status**: 🟡 Partial (requires async support)  
**Priority**: HIGH  

### Tools Provided

| Tool | Handler | Schema | Purpose |
|------|---------|--------|---------|
| `find_precedents` | `find_precedents()` | `{query: string}` | Search case law |
| `predict_outcome` | `predict_outcome()` | `{case: object}` | Predict case outcome |
| `calculate_confidence` | `calculate_confidence()` | None | Calculate confidence intervals |

### Dependencies
- Case Law Engine: for precedent database
- ML prediction models: for outcome prediction

### Implementation Template

```python
# phase16/precedent_ai/precedent_ai.py
from core.tool_gateway import ToolGateway
import asyncio

class PrecedentAI:
    def __init__(self, gateway: ToolGateway = None):
        self.agent_id = "precedent_ai"
        self.gateway = gateway or ToolGateway()
        self._register_tools()
    
    def _register_tools(self):
        """Register precedent AI tools."""
        
        self.gateway.register_tool(
            agent_id=self.agent_id,
            tool_name='find_precedents',
            handler=self.find_precedents,
            schema={
                'type': 'object',
                'properties': {
                    'query': {
                        'type': 'string',
                        'description': 'Search query for precedents'
                    },
                    'limit': {
                        'type': 'integer',
                        'description': 'Max results to return',
                        'default': 10
                    }
                },
                'required': ['query']
            },
            description='Search case law database for precedents',
            tags=['precedent', 'search']
        )
        
        self.gateway.register_tool(
            agent_id=self.agent_id,
            tool_name='predict_outcome',
            handler=self.predict_outcome,
            schema={
                'type': 'object',
                'properties': {
                    'case': {
                        'type': 'object',
                        'description': 'Case details for prediction'
                    }
                },
                'required': ['case']
            },
            description='Predict likely case outcome based on precedents',
            tags=['prediction', 'analysis']
        )
        
        self.gateway.register_tool(
            agent_id=self.agent_id,
            tool_name='calculate_confidence',
            handler=self.calculate_confidence,
            description='Calculate confidence intervals',
            tags=['analysis', 'metrics']
        )
    
    def find_precedents(self, query: str, limit: int = 10) -> dict:
        """Find relevant precedents (sync wrapper for async)."""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self._find_precedents_async(query, limit))
    
    async def _find_precedents_async(self, query: str, limit: int) -> dict:
        """Async precedent search."""
        # Long-running search
        precedents = await self._search_case_law(query, limit)
        return {
            'query': query,
            'precedents': precedents,
            'count': len(precedents)
        }
    
    def predict_outcome(self, case: dict) -> dict:
        """Predict case outcome."""
        return {
            'case_id': case.get('id'),
            'prediction': 'Likely favorable',
            'confidence': 0.78,
            'reasoning': 'Based on 5 similar precedents'
        }
    
    def calculate_confidence(self) -> dict:
        """Calculate confidence intervals."""
        return {'confidence': 0.85, 'margin_of_error': 0.05}
    
    async def _search_case_law(self, query: str, limit: int) -> list:
        # Implementation
        return []
```

---

## FT-TG005: Multimodal Court ToolGateway Wiring

**Agent**: `phase16.multimodal_court.MultimodalCourt`  
**Status**: 🔴 Blocked (requires file handling)  
**Priority**: HIGH  

### Tools Provided

| Tool | Handler | Schema | Purpose |
|------|---------|--------|---------|
| `process_audio` | `process_audio()` | `{audio_path: string}` | Transcribe and analyze audio |
| `process_handwriting` | `process_handwriting()` | `{image_path: string}` | OCR handwritten documents |
| `process_video` | `process_video()` | `{video_path: string}` | Extract key moments from video |

### Dependencies
- OCR service: for handwriting recognition
- Audio transcription service: for speech-to-text
- Video analysis models: for video processing

### Implementation Template

```python
# phase16/multimodal_court/multimodal_intelligence.py
from core.tool_gateway import ToolGateway

class MultimodalCourt:
    def __init__(self, gateway: ToolGateway = None):
        self.agent_id = "multimodal_court"
        self.gateway = gateway or ToolGateway()
        self._register_tools()
    
    def _register_tools(self):
        """Register multimodal tools."""
        
        self.gateway.register_tool(
            agent_id=self.agent_id,
            tool_name='process_audio',
            handler=self.process_audio,
            schema={
                'type': 'object',
                'properties': {
                    'audio_path': {
                        'type': 'string',
                        'description': 'Path to audio file'
                    }
                },
                'required': ['audio_path']
            },
            description='Transcribe and analyze audio recordings',
            tags=['audio', 'transcription']
        )
        
        self.gateway.register_tool(
            agent_id=self.agent_id,
            tool_name='process_handwriting',
            handler=self.process_handwriting,
            schema={
                'type': 'object',
                'properties': {
                    'image_path': {
                        'type': 'string',
                        'description': 'Path to image with handwriting'
                    }
                },
                'required': ['image_path']
            },
            description='OCR handwritten documents',
            tags=['ocr', 'handwriting']
        )
        
        self.gateway.register_tool(
            agent_id=self.agent_id,
            tool_name='process_video',
            handler=self.process_video,
            schema={
                'type': 'object',
                'properties': {
                    'video_path': {
                        'type': 'string',
                        'description': 'Path to video file'
                    }
                },
                'required': ['video_path']
            },
            description='Extract key moments and analysis from video',
            tags=['video', 'analysis']
        )
    
    def process_audio(self, audio_path: str) -> dict:
        """Process audio file."""
        return {
            'audio_path': audio_path,
            'transcription': 'Transcribed text...',
            'confidence': 0.92
        }
    
    def process_handwriting(self, image_path: str) -> dict:
        """Process handwritten document."""
        return {
            'image_path': image_path,
            'text': 'OCR text...',
            'confidence': 0.85
        }
    
    def process_video(self, video_path: str) -> dict:
        """Process video."""
        return {
            'video_path': video_path,
            'key_moments': [],
            'summary': 'Video summary...'
        }
```

---

## FT-TG006: PARL Core ToolGateway Wiring

**Agent**: `phase16.parl_core.PARLCore`  
**Status**: 🟡 Partial (requires episode management)  
**Priority**: MEDIUM  

### Tools Provided

| Tool | Handler | Schema | Purpose |
|------|---------|--------|---------|
| `parallel_execute` | `parallel_execute()` | `{agents: array, task: object}` | Run parallel agent execution |
| `collect_episodes` | `collect_episodes()` | `{criteria: object}` | Collect learning episodes |
| `update_policy` | `update_policy()` | `{episodes: array}` | Update agent policies via RL |

### Dependencies
- Agent execution engines: for parallel execution
- Data collection services: for episode storage

### Implementation Template

```python
# phase16/parl_core/parl_engine.py
from core.tool_gateway import ToolGateway

class PARLCore:
    def __init__(self, gateway: ToolGateway = None):
        self.agent_id = "parl_core"
        self.gateway = gateway or ToolGateway()
        self._register_tools()
    
    def _register_tools(self):
        """Register PARL tools."""
        
        self.gateway.register_tool(
            agent_id=self.agent_id,
            tool_name='parallel_execute',
            handler=self.parallel_execute,
            schema={
                'type': 'object',
                'properties': {
                    'agents': {
                        'type': 'array',
                        'items': {'type': 'string'}
                    },
                    'task': {'type': 'object'}
                },
                'required': ['agents', 'task']
            },
            description='Run parallel agent execution',
            tags=['parallelization', 'learning']
        )
        
        self.gateway.register_tool(
            agent_id=self.agent_id,
            tool_name='collect_episodes',
            handler=self.collect_episodes,
            schema={
                'type': 'object',
                'properties': {
                    'criteria': {
                        'type': 'object',
                        'description': 'Selection criteria'
                    }
                },
                'required': ['criteria']
            },
            description='Collect learning episodes',
            tags=['learning', 'data_collection']
        )
        
        self.gateway.register_tool(
            agent_id=self.agent_id,
            tool_name='update_policy',
            handler=self.update_policy,
            schema={
                'type': 'object',
                'properties': {
                    'episodes': {
                        'type': 'array',
                        'description': 'Episodes for training'
                    }
                },
                'required': ['episodes']
            },
            description='Update agent policies via reinforcement learning',
            tags=['learning', 'policy_update']
        )
    
    def parallel_execute(self, agents: list, task: dict) -> dict:
        """Execute task in parallel on multiple agents."""
        return {
            'status': 'started',
            'agents': agents,
            'task_id': 'task_123'
        }
    
    def collect_episodes(self, criteria: dict) -> dict:
        """Collect learning episodes."""
        return {
            'episodes': [],
            'count': 0,
            'criteria': criteria
        }
    
    def update_policy(self, episodes: list) -> dict:
        """Update agent policies."""
        return {
            'status': 'updated',
            'episodes_processed': len(episodes),
            'policy_version': '2.0'
        }
```

---

## Summary: Wiring Status

| Agent | Status | Tools | Implementation | Testing |
|-------|--------|-------|-----------------|---------|
| MoE Router | 🟡 Partial | 3/3 | Required | Needed |
| Hierarchical Orch. | 🔴 Blocked | 2/3 | Required | Needed |
| Jurisdiction Engine | 🟢 Ready | 3/3 | Template | Needed |
| Precedent AI | 🟡 Partial | 2/3 | Required | Needed |
| Multimodal Court | 🔴 Blocked | 1/3 | Required | Needed |
| PARL Core | 🟡 Partial | 2/3 | Required | Needed |
| Confidential Computing | 🟡 Partial | TBD | TBD | TBD |

## Next Steps

1. **Week 1**: Wire MoE Router and Jurisdiction Engine
2. **Week 2**: Wire Precedent AI with async support
3. **Week 3**: Wire Hierarchical Orchestrator and resolve dependencies
4. **Week 4**: Wire Multimodal Court and PARL Core
5. **Week 5**: Wire Confidential Computing and integration testing

# SintraPrime-Unified Developer Experience

Comprehensive developer tooling for the **SintraPrime-Unified** API platform — your AI-powered legal, financial, and governance automation suite.

---

## 📦 Contents

| File | Description | Lines |
|------|-------------|-------|
| `openapi_spec.py` | Master OpenAPI 3.1 spec for all 10 API modules | ~550 |
| `cookbook.py` | 25+ real-world runnable scenarios | ~600 |
| `model_playground.py` | Multi-LLM benchmarking & A/B testing | ~450 |
| `sdk_generator.py` | Auto-generate Python, TypeScript, curl SDKs | ~320 |
| `dev_portal_api.py` | FastAPI router serving everything | ~260 |
| `tests/test_dev_experience.py` | 70+ tests (all passing) | ~440 |
| `DEVELOPER_EXPERIENCE.md` | This guide | — |

---

## 🚀 Quickstart

### 1. Install dependencies

```bash
pip install fastapi uvicorn pyyaml requests
```

### 2. Export OpenAPI Spec

```bash
cd developer_experience
python openapi_spec.py
# Creates: openapi.json and openapi.yaml
```

### 3. Run the Developer Portal

```bash
python dev_portal_api.py
# Opens at: http://localhost:8080
```

### 4. Run Tests

```bash
python -m pytest developer_experience/tests/ -v
# 70+ tests, all passing
```

### 5. Generate SDKs

```python
from developer_experience.sdk_generator import generate_all_sdks
from developer_experience.openapi_spec import build_openapi_spec

spec = build_openapi_spec()
generate_all_sdks(spec, output_dir="./generated_sdks/")
# Creates: sintraprime_sdk.py, sintraprime_sdk.ts, curl_examples.md
```

---

## 📚 Cookbook — All 25 Scenarios

### Beginner
| ID | Title | Tags |
|----|-------|------|
| `trust-001` | Help me create a living trust | trust, estate-planning, legal |
| `legal-001` | Research case law for landlord-tenant dispute | legal, case-law, research |
| `legal-002` | Set up automated court deadline monitoring | legal, deadlines, automation |
| `trust-002` | Create a business formation checklist | business, formation, LLC |
| `legal-004` | File federal agency complaint | legal, CFPB, federal |
| `mcp-002` | Execute MCP legal research tool | mcp, tools, legal |
| `obs-001` | Monitor system observability dashboard | observability, metrics |
| `banking-003` | Link bank account and categorize transactions | banking, plaid |
| `appbuilder-002` | Generate TypeScript SDK from OpenAPI spec | sdk, typescript |

### Intermediate
| ID | Title | Tags |
|----|-------|------|
| `banking-001` | Analyze my credit report | banking, credit, plaid |
| `banking-002` | Negotiate debt settlement | banking, debt, negotiation |
| `legal-003` | Review a contract for red flags | legal, contract, review |
| `compliance-001` | Run GDPR compliance audit | compliance, GDPR, privacy |
| `legal-006` | Eviction defense strategy | legal, eviction, defense |
| `governance-001` | Create agent governance policy | governance, agents, policy |
| `workflow-001` | Create automated legal intake workflow | workflow, automation |
| `ei-001` | Adapt stressful client communication | emotional-intelligence, empathy |
| `appbuilder-001` | Build a legal intake app | app-builder, deployment |
| `compliance-002` | HIPAA compliance check for health app | compliance, HIPAA |
| `legal-007` | Prepare interrogatories for discovery | legal, discovery, mcp |
| `banking-003` | Link bank account and categorize transactions | banking, plaid |

### Advanced
| ID | Title | Tags |
|----|-------|------|
| `legal-005` | Predict case outcome before filing | legal, prediction, AI |
| `mcp-001` | Set up multi-agent swarm for complex litigation | mcp, swarm, agents |
| `trust-003` | Irrevocable special needs trust | trust, special-needs |
| `ei-002` | Detect client deception risk in communications | emotional-intelligence, analysis |
| `workflow-002` | Automated compliance monitoring workflow | workflow, compliance, automation |

---

## 🤖 Model Playground

Test any of 8 supported LLM backends against SintraPrime prompts:

| Model | Provider | Context | Cost/1K in |
|-------|----------|---------|-----------|
| `gpt-4o` | OpenAI | 128K | $0.0050 |
| `gpt-4o-mini` | OpenAI | 128K | $0.00015 |
| `claude-3-5-sonnet` | Anthropic | 200K | $0.0030 |
| `claude-3-haiku` | Anthropic | 200K | $0.00025 |
| `ollama-llama3` | Ollama (local) | 8K | Free |
| `ollama-mistral` | Ollama (local) | 8K | Free |
| `deepseek-chat` | DeepSeek | 32K | $0.0002 |
| `hermes-3` | Hermes | 8K | Free |

### Run A/B Test

```python
from developer_experience.model_playground import PlaygroundBenchmark

bench = PlaygroundBenchmark(api_keys={
    "openai": "sk-...",
    "anthropic": "sk-ant-...",
})

result = bench.ab_test(
    model_a="gpt-4o",
    model_b="claude-3-5-sonnet",
    template_id="legal-002",
    variables={
        "contract_type": "lease",
        "party_role": "tenant",
        "contract_text": "Landlord may enter at any time...",
    },
)
print(result.comparison_summary)
```

### Benchmark Multiple Models

```python
results = bench.run_suite(
    model_ids=["gpt-4o", "claude-3-5-sonnet", "deepseek-chat"],
    template_ids=["legal-001", "legal-002", "fin-001"],
)
leaderboard = bench.leaderboard(results)
for entry in leaderboard:
    print(f"{entry['model']}: quality={entry['avg_quality']:.0%} latency={entry['avg_latency_ms']:.0f}ms")
```

### 50+ Prompt Templates by Category

| Category | Count | Example |
|----------|-------|---------|
| `legal` | 13 | Case law summarizer, contract red flag detector |
| `financial` | 7 | Debt negotiation strategist, budget optimizer |
| `estate` | 4 | Estate planning advisor, trust vs will analyzer |
| `compliance` | 5 | GDPR gap analyzer, HIPAA risk assessment |
| `governance` | 3 | AI agent policy drafter, audit trail analyzer |
| `business` | 5 | Business formation guide, NDA reviewer |
| `emotional` | 4 | Empathetic response generator, conflict de-escalator |
| `agent` | 4 | Agent task decomposer, prompt optimizer |
| `workflow` | 3 | Workflow designer, API integration designer |

---

## 🔌 Developer Portal API Endpoints

Start the portal:
```bash
python -m uvicorn developer_experience.dev_portal_api:create_dev_portal_app --factory --port 8080
```

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Portal health check |
| `GET` | `/docs/openapi.json` | OpenAPI spec (JSON) |
| `GET` | `/docs/openapi.yaml` | OpenAPI spec (YAML) |
| `GET` | `/docs/endpoints` | All endpoints summary |
| `GET` | `/docs/schemas` | All component schemas |
| `GET` | `/cookbook` | List all 25+ scenarios |
| `GET` | `/cookbook/search?tags=legal&difficulty=beginner` | Search scenarios |
| `GET` | `/cookbook/{id}` | Get scenario with code |
| `GET` | `/playground/models` | List LLM models |
| `GET` | `/playground/templates` | List prompt templates |
| `GET` | `/playground/templates/{id}` | Get template detail |
| `POST` | `/playground/run` | Run single model or A/B test |
| `POST` | `/playground/benchmark` | Run multi-model benchmark |
| `GET` | `/playground/cost-estimate` | Cost estimation |
| `GET` | `/sdk/python` | Download Python SDK |
| `GET` | `/sdk/typescript` | Download TypeScript SDK |
| `GET` | `/sdk/curl` | Download curl examples |
| `GET` | `/sdk/info` | SDK metadata |

---

## 🧪 Test Coverage

```
tests/test_dev_experience.py
├── TestOpenAPISpec      — 25 tests
├── TestCookbook         — 22 tests
├── TestModelPlayground  — 22 tests
├── TestSDKGenerator     — 22 tests
├── TestIntegration      — 5 tests
└── TestEdgeCases        — 5 tests

Total: 70+ tests | All passing
```

Run:
```bash
python -m pytest developer_experience/tests/test_dev_experience.py -v
```

---

## 🏗️ OpenAPI Spec Coverage

10 modules, 35+ endpoints, 55+ schemas:

| Module | Endpoints | Schemas |
|--------|-----------|---------|
| Legal Intelligence | 6 | 10 |
| Trust Law | 3 | 7 |
| Banking/Plaid | 4 | 5 |
| Governance | 3 | 6 |
| MCP Server | 3 | 6 |
| Emotional Intelligence | 2 | 4 |
| App Builder | 2 | 4 |
| Observability | 3 | 3 |
| Compliance | 2 | 3 |
| Workflow Builder | 2 | 4 |

---

## 📄 License

Proprietary — SintraPrime-Unified © 2026 ikesolutions.org

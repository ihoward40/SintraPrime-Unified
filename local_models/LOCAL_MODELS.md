# SintraPrime Local & Offline Models

Run SintraPrime-Unified completely offline — no internet required — using local
language models via [Ollama](https://ollama.com/) and optional cloud API
fallbacks (DeepSeek, OpenAI, Anthropic).

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start — Ollama Setup](#quick-start--ollama-setup)
3. [Recommended Models for Legal Work](#recommended-models-for-legal-work)
4. [Running SintraPrime Fully Offline](#running-sintraprime-fully-offline)
5. [Model Quantization Guide](#model-quantization-guide)
6. [DeepSeek API Integration](#deepseek-api-integration)
7. [Model Router](#model-router)
8. [Offline Mode Manager](#offline-mode-manager)
9. [API Endpoints](#api-endpoints)
10. [Running Tests](#running-tests)
11. [Troubleshooting](#troubleshooting)

---

## Overview

The `local_models/` package provides:

| Module | Purpose |
|---|---|
| `ollama_client.py` | Connect to a local Ollama daemon; generate, chat, embed |
| `deepseek_client.py` | DeepSeek-V3 / DeepSeek-R1 API with chain-of-thought extraction |
| `model_router.py` | Auto-pick the best available model for any task |
| `quantization_manager.py` | Memory calculator, GGUF info, download helper, benchmarking |
| `offline_manager.py` | Connectivity detection, air-gap mode, template cache |
| `local_models_api.py` | FastAPI router exposing all capabilities as REST endpoints |

---

## Quick Start — Ollama Setup

### 1. Install Ollama

```bash
# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows
# Download from https://ollama.com/download
```

### 2. Start the Ollama daemon

```bash
ollama serve
```

Ollama listens on `http://localhost:11434` by default.

### 3. Pull models

```bash
# Recommended for legal work (see next section)
ollama pull llama3
ollama pull mistral
ollama pull deepseek-r1
ollama pull hermes3
```

### 4. Verify

```bash
ollama list
```

---

## Recommended Models for Legal Work

| Model | Size | Best For | RAM Required (Q4) |
|---|---|---|---|
| **deepseek-r1** | 7 B | Legal research, case analysis, complex reasoning | ~5 GB |
| **mistral** | 7 B | Contract review, clause extraction, fast drafting | ~5 GB |
| **llama3** | 8 B | General chat, summarisation, document review | ~5.5 GB |
| **hermes3** | 8 B | Template filling, instruction-following, long context | ~5.5 GB |

### Larger models (if RAM allows)

| Model | Size | RAM (Q4) |
|---|---|---|
| deepseek-r1:14b | 14 B | ~9.5 GB |
| deepseek-r1:32b | 32 B | ~21 GB |
| llama3:70b | 70 B | ~44 GB |

Pull a larger model:
```bash
ollama pull deepseek-r1:14b
```

---

## Running SintraPrime Fully Offline

### Step 1 — Pre-pull models (while online)

```bash
ollama pull llama3
ollama pull mistral
ollama pull deepseek-r1
```

### Step 2 — Pre-cache legal templates

```python
from local_models.offline_manager import OfflineMode

mgr = OfflineMode()
count = mgr.pre_cache_templates()
print(f"Cached {count} templates")
```

### Step 3 — Enable air-gap mode (optional)

This completely blocks all external API calls, even if the internet is available:

```python
mgr.enable_air_gap()
```

Or via the API:
```bash
curl -X POST http://localhost:8000/models/offline/enable \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

### Step 4 — Use the router (automatically goes local)

```python
from local_models.model_router import ModelRouter

router = ModelRouter()
result = router.complete(
    "Explain the doctrine of promissory estoppel.",
    task="legal_research",
)
print(result.content)
print(f"Provider used: {result.provider}")
```

When Ollama is available and no cloud keys are set, all requests are served
locally at zero cost.

---

## Model Quantization Guide

Quantization reduces model file size at a small quality cost.

| Quantization | Quality | Size vs FP16 | Best For |
|---|---|---|---|
| Q4_K_M | ★★★★☆ | ~25% | Everyday use, best balance |
| Q5_K_M | ★★★★½ | ~31% | Quality-focused legal work |
| Q6_K | ★★★★★ | ~38% | Near-lossless, mid-range RAM |
| Q8_0 | ★★★★★ | ~50% | Best quality, high RAM |
| Q3_K_M | ★★★☆☆ | ~19% | Very low RAM only |

### Check what your machine can run

```python
from local_models.quantization_manager import QuantizationManager

qm = QuantizationManager()
print(f"Available RAM: {qm.available_ram_gb:.1f} GB")

report = qm.what_can_i_run()
for model, quants in report.items():
    print(f"  {model}: {quants}")
```

### Get recommendations

```python
recs = qm.recommend_quantization("llama3:8b", priority="balanced")
for r in recs:
    status = "✓" if r.suitable else "✗"
    print(f"{status} {r.quant} — {r.size_gb:.1f} GB — {r.quality} quality — {r.notes}")
```

---

## DeepSeek API Integration

[DeepSeek](https://platform.deepseek.com/) offers very cheap API access to:
- **DeepSeek-V3** (`deepseek-chat`) — fast, general purpose
- **DeepSeek-R1** (`deepseek-reasoner`) — deep chain-of-thought reasoning

### Setup

```bash
export DEEPSEEK_API_KEY="your-key-here"
```

### Legal reasoning with DeepSeek-R1

```python
from local_models.deepseek_client import DeepSeekClient

client = DeepSeekClient()
result = client.legal_reasoning(
    question="Analyse the implied covenant of good faith and fair dealing.",
    jurisdiction="California",
)

print("=== Chain of Thought ===")
print(result.thinking)
print("\n=== Final Answer ===")
print(result.answer)
print(f"\nCost: ${result.cost_usd:.4f}")
```

### Cost tracking

```python
summary = client.cost_summary()
print(f"Total spent: ${summary['total_cost_usd']:.4f}")
print(f"Total calls: {summary['calls']}")
```

---

## Model Router

The `ModelRouter` picks the best available provider automatically:

```
Ollama (free, private) → DeepSeek (cheap) → OpenAI → Anthropic
```

```python
from local_models.model_router import ModelRouter, TaskType

router = ModelRouter(
    deepseek_api_key="...",   # optional
    openai_api_key="...",     # optional
)

# Auto-routing
result = router.complete(
    "What is the statute of limitations for breach of contract in New York?",
    task=TaskType.LEGAL_RESEARCH,
)
print(result.content)
print(f"Used: {result.provider} / {result.model} — {result.latency_s:.1f}s")

# Check routing plan without executing
plan = router.routing_plan("legal_research")
print(plan)
```

### Task types

| Task String | Preferred Model |
|---|---|
| `legal_research` | deepseek-r1 (local) / deepseek-reasoner |
| `contract_review` | mistral / deepseek-chat |
| `document_review` | mistral / deepseek-chat |
| `chat` | llama3 / gpt-4o |
| `summarisation` | llama3 / gpt-4o |
| `template_filling` | hermes3 / deepseek-chat |
| `clause_extraction` | mistral / deepseek-chat |

---

## Offline Mode Manager

```python
from local_models.offline_manager import OfflineMode

mgr = OfflineMode()

# Check connectivity
print(mgr.is_online())       # True / False

# Air-gap mode
mgr.enable_air_gap()
mgr.disable_air_gap()

# Legal templates
template = mgr.get_template("nda_simple")
filled = mgr.fill_template("nda_simple", {
    "DATE": "2025-01-01",
    "PARTY_A": "Client Corp",
    "PARTY_B": "Vendor Ltd",
    "TERM": "3",
})

# Capability report
report = mgr.capability_report()
print(report)

# Graceful degradation
result = mgr.with_fallback(
    online_fn=lambda: deepseek_client.complete(prompt),
    offline_fn=lambda: ollama_client.generate(prompt),
    service_name="DeepSeek",
)
```

### Built-in templates

| Template | Description |
|---|---|
| `nda_simple` | Simple Non-Disclosure Agreement |
| `engagement_letter` | Attorney-client engagement letter |
| `motion_caption` | Court motion caption block |
| `cease_desist` | Cease and Desist letter |

---

## API Endpoints

Start the SintraPrime server, then use:

| Method | Endpoint | Description |
|---|---|---|
| GET | `/models/available` | List all models and providers |
| POST | `/models/complete` | Run a completion |
| GET | `/models/ollama/status` | Ollama health |
| POST | `/models/ollama/pull` | Pull a new Ollama model |
| GET | `/models/memory-check` | Hardware compatibility |
| POST | `/models/offline/enable` | Toggle air-gap mode |
| GET | `/models/offline/status` | Offline mode status |
| GET | `/models/routing-plan` | Show routing plan for a task |

### Example: run a completion

```bash
curl -X POST http://localhost:8000/models/complete \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Summarise the principle of promissory estoppel.",
    "task": "legal_research",
    "model": "auto"
  }'
```

---

## Running Tests

```bash
# From repo root
python -m pytest local_models/tests/test_local_models.py -v

# With coverage
pip install pytest-cov
python -m pytest local_models/tests/test_local_models.py -v --cov=local_models
```

All tests mock external HTTP calls — no Ollama daemon or API keys needed.

---

## Troubleshooting

### "OllamaConnectionError: Cannot connect to Ollama"

```bash
# Start Ollama
ollama serve

# Or check if it's running
curl http://localhost:11434/
```

### "DeepSeekAuthError: API key not set"

```bash
export DEEPSEEK_API_KEY="your-key"
```

### Model too slow / out of memory

Use a smaller quantization:
```python
from local_models.quantization_manager import QuantizationManager
qm = QuantizationManager()
print(qm.best_quant_for_ram("llama3:8b"))
```

Then pull that version explicitly via Ollama (e.g. from a GGUF source).

### GPU acceleration

Ollama automatically uses GPU if available (CUDA or Metal on macOS).
No configuration needed. Verify:
```bash
ollama run llama3 "hello"
# Should show gpu layers in verbose output
```

# SintraPrime Offline Mode — Local LLM Setup

> Run SintraPrime fully offline using Hermes, Llama, Mistral, or any Ollama-compatible model.
> No internet connection or cloud API key required once models are downloaded.

---

## Quick Start (2 minutes)

```bash
# 1. Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 2. Pull Hermes (recommended for legal reasoning)
ollama pull hermes3

# 3. Enable local mode
export SINTRA_LOCAL_LLM=true

# 4. Run SintraPrime
python -m sintra
```

---

## Supported Models

| Model | Best For | RAM Required | Size (disk) |
|---|---|---|---|
| `hermes3` | Legal reasoning, function calling | 6 GB | 4.7 GB |
| `nous-hermes2` | General + legal, 7B | 8 GB | 7.3 GB |
| `hermes-2-pro-mistral` | Complex reasoning, structured output | 6 GB | 4.7 GB |
| `llama3.2` | Fast responses, general use | 3 GB | 2.0 GB |
| `llama3.2:1b` | Ultra-fast, low RAM | 2 GB | 1.3 GB |
| `mistral` | Multi-purpose, fast | 5 GB | 4.1 GB |
| `mixtral` | Multi-domain, high quality | 32 GB | 26 GB |
| `codellama` | Code generation | 6 GB | 4.7 GB |
| `deepseek-coder` | Code, technical tasks | 5 GB | 4.2 GB |
| `nomic-embed-text` | Embeddings / vector search | 1 GB | 0.3 GB |

> **Minimum recommended:** 8 GB RAM + 10 GB disk for `hermes3`
> **Optimal for legal work:** 16 GB RAM with `nous-hermes2`

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SINTRA_LOCAL_LLM` | `false` | Set to `true` to enable local mode |
| `SINTRA_LOCAL_MODEL` | `hermes3` | Which model to use |
| `SINTRA_LOCAL_URL` | `http://localhost:11434` | Ollama server URL |
| `SINTRA_LOCAL_FALLBACK` | `true` | Fall back to OpenAI/Claude if local fails |
| `SINTRA_LLM_PROVIDER` | `hermes` | Adapter: `hermes` or `ollama` |
| `OPENAI_API_KEY` | _(unset)_ | OpenAI key (used as fallback) |
| `ANTHROPIC_API_KEY` | _(unset)_ | Anthropic key (used as fallback) |

---

## Backend Priority Chain

```
1. Local LLM (Ollama)    ← preferred when SINTRA_LOCAL_LLM=true
2. OpenAI                ← if OPENAI_API_KEY is set
3. Claude (Anthropic)    ← if ANTHROPIC_API_KEY is set
4. Static fallback msg   ← never raises, always returns a response
```

---

## Installing Multiple Models

```bash
# Legal reasoning suite
ollama pull hermes3
ollama pull nous-hermes2
ollama pull hermes-2-pro-mistral

# Code generation
ollama pull codellama
ollama pull deepseek-coder

# Embeddings
ollama pull nomic-embed-text

# List installed models
ollama list
```

---

## Running Ollama as a Service

### macOS / Linux (systemd)

```bash
# Ollama installer creates a systemd service automatically.
# Check status:
sudo systemctl status ollama

# Start / stop:
sudo systemctl start ollama
sudo systemctl stop ollama

# Enable on boot:
sudo systemctl enable ollama
```

### Docker

```bash
docker run -d \
  -v ollama:/root/.ollama \
  -p 11434:11434 \
  --name ollama \
  ollama/ollama

# With GPU support (NVIDIA):
docker run -d --gpus=all \
  -v ollama:/root/.ollama \
  -p 11434:11434 \
  --name ollama \
  ollama/ollama
```

### Remote Ollama

```bash
# Point SintraPrime at a remote Ollama instance:
export SINTRA_LOCAL_URL=http://192.168.1.100:11434
export SINTRA_LOCAL_LLM=true
```

---

## Python API Usage

```python
import asyncio
from local_llm import SintraLLMBridge, HermesAdapter, ModelManager, LLMConfig

async def main():
    # Simple chat
    bridge = SintraLLMBridge(force_local=True)
    reply = await bridge.chat([{"role": "user", "content": "What is a revocable trust?"}])
    print(reply)

    # Specialised legal analysis
    analysis = await bridge.legal_analysis(
        query="Explain the difference between a trustee and a beneficiary",
        context="California trust law applies."
    )
    print(analysis)

    # Trust law expert
    answer = await bridge.trust_law_expert(
        "Can a beneficiary also be a trustee of the same trust?"
    )
    print(answer)

    # Direct Hermes adapter
    config = LLMConfig(model="hermes3")
    hermes = HermesAdapter(config)
    result = await hermes.chain_of_thought(
        question="Is a spendthrift clause enforceable against creditors?"
    )
    print(result.content)

    # Model management
    mm = ModelManager()
    models = await mm.list_available()
    print("Available:", [m["name"] for m in models])
    recommended = await mm.recommend_for_task("trust law analysis")
    print("Recommended:", recommended)

asyncio.run(main())
```

---

## Streaming Responses

```python
import asyncio
from local_llm import SintraLLMBridge

async def main():
    bridge = SintraLLMBridge(force_local=True)
    async for token in bridge.stream_chat([
        {"role": "user", "content": "Explain irrevocable trusts in detail"}
    ]):
        print(token, end="", flush=True)
    print()

asyncio.run(main())
```

---

## Benchmarking Models

```python
import asyncio
from local_llm import ModelManager

async def main():
    mm = ModelManager()
    # Benchmark a single model
    result = await mm.benchmark("hermes3")
    print(f"Tokens/sec: {result['tokens_per_sec']}")
    print(f"First token: {result['first_token_ms']}ms")
    
    # Benchmark all installed models
    all_results = await mm.benchmark_all()
    for r in all_results:
        print(f"{r['model']:30s}  {r['tokens_per_sec']:6.1f} tok/s")

asyncio.run(main())
```

---

## Troubleshooting

### "Cannot connect to Ollama"

```bash
# Check if Ollama is running
curl http://localhost:11434/

# Start it manually
ollama serve
```

### "Model not found"

```bash
# Pull the model first
ollama pull hermes3

# Verify it's available
ollama list
```

### Slow responses

- Use a smaller model: `llama3.2:1b` or `mistral`
- Ensure model fits in RAM (no disk swapping)
- Use GPU if available — install Ollama with GPU support

### Out of memory

```bash
# Switch to a smaller model
export SINTRA_LOCAL_MODEL=llama3.2
ollama pull llama3.2
```

---

## Architecture

```
SintraPrime
    │
    └── SintraLLMBridge
            │
            ├── HermesAdapter (Hermes-specific ChatML + legal prompts)
            │       └── OllamaAdapter (HTTP → Ollama REST API)
            │               └── Ollama daemon (localhost:11434)
            │                       └── hermes3 / nous-hermes2 / ...
            │
            ├── OllamaAdapter (generic Ollama models)
            │
            ├── OpenAI API (fallback)
            └── Anthropic Claude (fallback)
```

---

## Legal Domain Specialisation

SintraPrime's Hermes integration includes pre-tuned system prompts for:

- **Trust law** — revocable/irrevocable trusts, trustee duties, beneficiary rights
- **Estate planning** — wills, probate, intestacy, estate tax
- **Fiduciary duties** — duty of care, loyalty, prudent investor rule
- **Legal document analysis** — clause comparison, risk identification
- **Structured reasoning** — chain-of-thought for complex legal questions

These are automatically applied when you use `bridge.legal_analysis()` or `bridge.trust_law_expert()`.

---

## Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run the full test suite (no Ollama required)
cd /path/to/SintraPrime-Unified
pytest local_llm/tests/test_local_llm.py -v

# Run with coverage
pip install pytest-cov
pytest local_llm/tests/ --cov=local_llm --cov-report=term-missing
```

---

*SintraPrime — Intelligent trust management, available anywhere.*

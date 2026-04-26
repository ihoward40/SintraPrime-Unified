# SintraPrime RAG Legal Intelligence Engine

> **Sierra-3** — Ask SintraPrime any legal question. Get answers grounded in its knowledge base.

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [Query Examples](#query-examples)
5. [Ingestion Guide](#ingestion-guide)
6. [Configuration](#configuration)
7. [API Reference](#api-reference)
8. [Running Tests](#running-tests)
9. [FAQ](#faq)

---

## Overview

The SintraPrime RAG engine provides **Retrieval-Augmented Generation** over all legal modules:

| Module | Content |
|--------|---------|
| `trust_law/` | Trust law, fiduciary duties, estate planning |
| `legal_intelligence/` | Legal analysis algorithms and reasoning |
| `federal_agencies/` | Regulatory compliance, agency rules |
| `case_law/` | Court decisions, precedents |
| `compliance/` | AML, KYC, regulatory requirements |
| `contract_intelligence/` | Contract analysis, clause extraction |

**No API keys needed** — TF-IDF fallback always works. Configure `OPENAI_API_KEY` for LLM-powered answers.

---

## Quick Start

```python
import asyncio
from rag import LegalRAG

async def main():
    rag = LegalRAG()
    
    # Auto-index all SintraPrime modules (cached after first run)
    stats = await rag.initialize()
    print(f"Indexed {stats['documents']} documents across {stats['categories']}")
    
    # Ask any legal question
    result = await rag.ask("What are a trustee's fiduciary duties under the UTC?")
    
    print(result["answer"])
    print(f"\nConfidence: {result['confidence']:.0%}")
    print(f"Sources: {[c['source'] for c in result['citations']]}")
    print(f"Follow-ups: {result['follow_up_questions']}")

asyncio.run(main())
```

**Output:**
```
Based on SintraPrime's trust law knowledge base, a trustee's fiduciary duties include...
[PASSAGE 1] — trust_law/analyzer.py ...

Confidence: 84%
Sources: ['trust_law/analyzer.py', 'trust_law/uslegal_definitions.md']
Follow-ups: ['What are the penalties for breach of fiduciary duty?', ...]
```

---

## Architecture

```
User Question
     │
     ▼
┌─────────────────────────────────────────────────────┐
│                    LegalRAG                         │
│   (High-level interface, auto-initialises)          │
└─────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────┐
│                   RAGPipeline                       │
│  1. Retrieve relevant passages                      │
│  2. Build context-augmented prompt                  │
│  3. Generate answer (OpenAI / Ollama / template)    │
│  4. Attach citations + follow-ups                   │
└─────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────┐
│                  LegalRetriever                     │
│  Hybrid: 70% semantic + 30% BM25 keyword            │
│  Re-ranking: authority boost + jurisdiction match   │
└─────────────────────────────────────────────────────┘
     │                    │
     ▼                    ▼
┌──────────────┐   ┌──────────────────────────────────┐
│ EmbeddingProvider│   │         VectorStore                 │
│ OpenAI / ST / TF-IDF│  │ numpy cosine search + JSON persist│
└──────────────┘   └──────────────────────────────────┘
```

### Components

| Component | File | Purpose |
|-----------|------|---------|
| `LegalRAG` | `legal_rag.py` | Main entry point, auto-indexing |
| `DocumentIngester` | `document_ingester.py` | Parse files → `LegalDocument` |
| `VectorStore` | `vector_store.py` | Store & search embeddings |
| `EmbeddingProvider` | `embedder.py` | Multi-provider text→vector |
| `LegalRetriever` | `retriever.py` | Hybrid semantic + BM25 retrieval |
| `RAGPipeline` | `rag_pipeline.py` | Full question→answer pipeline |

---

## Query Examples

### General Legal Questions

```python
result = await rag.ask("What is the prudent investor rule?")
result = await rag.ask("How does the cy-pres doctrine apply to charitable trusts?")
result = await rag.ask("What are the elements of securities fraud under Rule 10b-5?")
```

### Jurisdiction-Specific

```python
result = await rag.ask(
    "What are California's rules on no-contest clauses in trusts?",
    jurisdiction="california"
)

result = await rag.ask(
    "Federal reporting requirements for foreign trust distributions",
    jurisdiction="federal"
)
```

### Trust Law Specialist

```python
# Optimised retrieval for trust-law questions
result = await rag.ask_trust_law(
    "Can a trustee delegate investment decisions to a third-party advisor?"
)
```

### Document Analysis

```python
trust_deed = open("my_trust.txt").read()
analysis = await rag.analyze_document(trust_deed)

print(analysis["analysis"])
# Document Type: Revocable Living Trust
# Parties: Grantor: John Smith, Trustee: Jane Doe...
# Key Obligations: Trustee must distribute income annually...
# Risk Factors: Ambiguous successor trustee provisions...
```

### Case Law / Precedents

```python
result = await rag.find_precedents(
    "Corporate director approved related-party transaction without disclosure to board"
)
print(result["precedents_summary"])
print(result["case_citations"])
```

### Ingest New Documents

```python
# Ingest a single PDF
chunks = await rag.ingest("/path/to/trust_agreement.pdf", category="user_document")
print(f"Indexed {chunks} chunks")

# Ingest a directory
chunks = await rag.ingest("/path/to/new_regulations/", category="federal_agencies")

# Ingest a CourtListener JSON file
chunks = await rag.ingest("/path/to/case.json", category="case_law")
```

---

## Ingestion Guide

### Supported Formats

| Format | Method | Notes |
|--------|--------|-------|
| `.py` | Auto (directory scan) | Extracts docstrings and comments |
| `.md`, `.txt`, `.rst` | Auto (directory scan) | Full text extraction |
| `.pdf` | `ingest_pdf()` | Tries pdfplumber → PyPDF2 → poppler |
| CourtListener JSON | `ingest_case_json()` | Parses opinions, metadata |
| Any text file | `ingest()` | Reads as UTF-8 text |

### Adding Custom Legal Knowledge

```python
from rag import DocumentIngester, VectorStore, EmbeddingProvider, VectorEntry

ingester = DocumentIngester()
embedder = EmbeddingProvider()
store = VectorStore(persist_path="my_knowledge.json")

# Ingest a directory
docs = ingester.ingest_directory("/my/legal/docs/", category="custom")

for doc in docs:
    for i, chunk in enumerate(doc.chunks):
        vec = await embedder.embed(chunk)
        store.add(VectorEntry(
            id=f"{doc.id}_c{i}",
            embedding=vec,
            content=chunk,
            metadata=doc.metadata
        ))

store.save()
```

### Force Re-index

```python
# Rebuild index from scratch (ignores cache)
stats = await rag.initialize(force_reindex=True)
```

---

## Configuration

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `OPENAI_API_KEY` | Enables OpenAI embeddings + GPT-4o answers | None (TF-IDF fallback) |
| `OLLAMA_URL` | Local LLM endpoint (e.g. `http://localhost:11434`) | None |

### Constructor Options

```python
rag = LegalRAG(
    base_path="/path/to/SintraPrime-Unified/",   # repo root
    persist_path="/path/to/knowledge_base.json",  # custom store location
    use_chroma=True,                               # use ChromaDB (pip install chromadb)
    llm_model="gpt-4-turbo",                       # override LLM model
)
```

### Embedding Providers

```python
from rag.embedder import EmbeddingProvider

# Check which provider is active
embedder = EmbeddingProvider()
print(embedder.provider)  # "openai" | "sentence_transformers" | "tfidf"
print(embedder.dim)        # 1536 / 384 / 512
```

---

## API Reference

### `LegalRAG`

```python
# Initialize / re-index
await rag.initialize(force_reindex=False) → dict

# Ask any legal question
await rag.ask(question, jurisdiction=None, top_k=8) → {
    "answer": str,
    "confidence": float,        # 0–1
    "citations": list[dict],
    "follow_up_questions": list[str],
    "jurisdiction": str,
    "retrieval_count": int,
    "llm_backend": str,
    "elapsed_seconds": float
}

# Trust law specialist
await rag.ask_trust_law(question) → dict

# Analyze a document
await rag.analyze_document(document_text) → {"analysis": str, ...}

# Find case precedents
await rag.find_precedents(case_facts) → {"precedents_summary": str, ...}

# Ingest new knowledge
await rag.ingest(path, category="user_document") → int  # chunk count

# Stats
rag.status() → dict
```

### `VectorStore`

```python
store.add(entry)                              # Add entry
store.get(id) → VectorEntry | None           # Retrieve by id
store.delete(id) → bool                      # Remove entry
store.search(query_vec, top_k, filter_metadata) → list[(entry, score)]
store.save() / store.load()                  # Persistence
store.stats() → dict                         # Statistics
```

---

## Running Tests

```bash
# Run all 56 tests (no API keys needed)
cd SintraPrime-Unified/
python -m pytest rag/tests/test_rag.py -v

# Run a specific test class
python -m pytest rag/tests/test_rag.py::TestVectorStore -v

# With coverage
python -m pytest rag/tests/test_rag.py --cov=rag --cov-report=term-missing
```

Expected output:
```
PASSED rag/tests/test_rag.py::TestDocumentIngester::test_chunk_text_returns_list
PASSED rag/tests/test_rag.py::TestDocumentIngester::test_ingest_case_json
...
56 passed in 3.2s
```

---

## FAQ

**Q: Do I need an OpenAI API key?**  
A: No. The TF-IDF fallback and template-based answers work without any API keys. Add `OPENAI_API_KEY` for production-quality answers.

**Q: How large can the knowledge base be?**  
A: The numpy-based store handles 100k+ entries comfortably. For larger corpora, enable ChromaDB (`use_chroma=True`).

**Q: How do I add support for a new legal domain?**  
A: Create a directory under `SintraPrime-Unified/` and call `await rag.ingest("/path/to/dir", category="my_domain")`. It will be auto-indexed on next `initialize()`.

**Q: Can I use Ollama locally?**  
A: Yes. Set `OLLAMA_URL=http://localhost:11434` and the pipeline will use any model you have pulled (default: `mistral`).

**Q: How is confidence calculated?**  
A: Weighted average of the top-5 passage cosine similarity scores (top passage weighted highest). Scores above 0.7 indicate strong grounding in the knowledge base.

---

*SintraPrime RAG Engine — Sierra-3 — Built for legal intelligence at scale.*

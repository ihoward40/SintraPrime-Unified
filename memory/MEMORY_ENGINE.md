# SintraPrime-Unified Memory Engine

A Hermes-style multi-layer persistent memory system for SintraPrime-Unified.
Inspired by **Hermes Agent**, **Claude Memory**, **GPT-5.5**, and **Pi AI**.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        MemoryEngine                             │
│                   (Master Orchestrator)                         │
│                                                                 │
│  ┌─────────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │  SemanticMemory │  │  EpisodicMemory  │  │ WorkingMemory │  │
│  │                 │  │                  │  │               │  │
│  │  Long-term      │  │  Conversation    │  │  Active       │  │
│  │  knowledge      │  │  & event history │  │  session      │  │
│  │  SQLite         │  │  SQLite          │  │  In-memory    │  │
│  │  ~/.sintra/     │  │  ~/.sintra/      │  │  Thread-safe  │  │
│  │  memory/        │  │  memory/         │  │  TTL support  │  │
│  │  semantic.db    │  │  episodic.db     │  │               │  │
│  └─────────────────┘  └──────────────────┘  └───────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │               UserProfileManager                         │   │
│  │                                                          │   │
│  │  Personal AI profile: comm style, expertise, goals,      │   │
│  │  legal matters, trusted contacts, preferences            │   │
│  │  Stored at: ~/.sintra/profiles/{user_id}.json            │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Memory Layers Explained

| Layer | Storage | Persistence | Retrieval |
|-------|---------|-------------|-----------|
| **Semantic** | SQLite | Cross-session | TF-IDF cosine similarity |
| **Episodic** | SQLite | Cross-session, rolling 1000 | Keyword search + date range |
| **Working** | In-memory | Session-scoped | Direct key lookup + TTL |
| **User Profile** | JSON files | Cross-session | Direct user_id lookup |

---

## How It Compares

| Feature | SintraPrime Memory | Hermes Agent | Claude Memory | Pi AI |
|---------|-------------------|--------------|---------------|-------|
| Multi-layer | ✅ 4 layers | ✅ 3 layers | ✅ Cross-session | ✅ Personal |
| Semantic search | ✅ TF-IDF | ✅ Embeddings | ✅ Embeddings | ❓ |
| Episodic recall | ✅ Sessions | ✅ Episodes | ✅ | ✅ |
| User profiles | ✅ Rich | ✅ | ✅ Preferences | ✅ Deep |
| Legal domain | ✅ Auto-index | ❌ | ❌ | ❌ |
| GDPR controls | ✅ Full | Partial | ✅ | Partial |
| FastAPI router | ✅ | ❌ | ❌ | ❌ |
| Thread-safe | ✅ | ✅ | N/A | N/A |
| Open source | ✅ | ✅ | ❌ | ❌ |

---

## Quick Start

### Installation

```bash
pip install fastapi pydantic uvicorn
# No external ML dependencies required — uses built-in TF-IDF
```

### Basic Usage

```python
from memory import MemoryEngine

engine = MemoryEngine()

# Store a memory
entry = engine.remember(
    "The statute of limitations for negligence in California is 2 years",
    user_id="lawyer_alice",
    tags=["legal", "california", "negligence"],
)

# Recall relevant memories
results = engine.recall("negligence time limit", user_id="lawyer_alice")
for r in results:
    print(f"[{r.relevance_score:.2f}] {r.entry.content}")

# Build LLM context
context = engine.get_relevant_context(
    "What is the deadline for filing a negligence lawsuit?",
    user_id="lawyer_alice",
    max_tokens=4000,
)
print(context)
```

### Working Memory (Session Context)

```python
engine.working.set_context("active_case", "Smith v. Jones 2024-CV-001")
engine.working.set_attention_focus(["negligence", "statute of limitations"])

from memory.memory_types import Task
engine.working.set_current_task(Task(
    name="Draft complaint",
    description="Write the initial complaint for Smith v. Jones",
))

# Snapshot for later restore
snap = engine.working.snapshot()
# ... restore later:
engine.working.restore(snap)
```

### User Profiles

```python
from memory import UserProfileManager

mgr = UserProfileManager()
profile = mgr.create_profile("alice", "Alice Chen")

# Update preferences learned from interaction
mgr.update_preference("alice", "response_format", "bullet_points")
mgr.learn_from_conversation("alice", conversation_messages)

# Track legal matters
mgr.track_legal_matter("alice", "matter-001", {
    "type": "civil",
    "court": "US District Court CDCA",
    "status": "discovery",
    "filed": "2024-01-15",
})

print(mgr.summarize_profile("alice"))
```

### Episodic Memory

```python
from memory import EpisodicMemory
import uuid

epis = EpisodicMemory()

session_id = str(uuid.uuid4())
epis.log_session(
    session_id,
    messages=[
        {"role": "user", "content": "What are my legal options?"},
        {"role": "assistant", "content": "You have three main options..."},
    ],
    outcomes=["options reviewed"],
    user_id="alice",
)

# Retrieve and summarize
summary = epis.summarize_episode(session_id)
learnings = epis.extract_learnings(session_id)
history = epis.get_user_history("alice", limit=10)
```

### FastAPI Integration

```python
from fastapi import FastAPI
from memory.memory_api import router

app = FastAPI()
app.include_router(router)

# Endpoints available:
# GET  /memory/recall?query=...&user_id=...
# POST /memory/store
# DELETE /memory/{entry_id}
# GET  /memory/profile/{user_id}
# PUT  /memory/profile/{user_id}/preference
# GET  /memory/export/{user_id}
# DELETE /memory/user/{user_id}
# GET  /memory/stats
# GET  /memory/context?query=...
```

---

## Privacy & GDPR Controls

### Right to Erasure (Article 17)

```python
# Delete all data for a user across all layers
stats = engine.forget_all(user_id="alice")
# Returns: {"semantic_deleted": 42, "episodic_deleted": 15, "profile_deleted": 1}

# Via API:
# DELETE /memory/user/{user_id}
```

### Data Portability (Article 20)

```python
# Export all user data as structured dict
data = engine.export_user_data(user_id="alice")
# Contains: profile, semantic_memories, episodic_sessions

# Via API:
# GET /memory/export/{user_id}
```

### Data Minimization

- Working memory entries expire via TTL (default: 1 hour)
- Episodic memory enforces a rolling window of 1000 sessions
- Older sessions are summarized (compressed) rather than deleted
- Users can selectively delete individual memory entries

---

## Integration with SintraPrime Modules

### With SintraChat

```python
from memory import MemoryEngine

engine = MemoryEngine()

async def process_message(user_id: str, message: str) -> str:
    # Get relevant context before calling LLM
    context = engine.get_relevant_context(message, user_id=user_id, max_tokens=2000)

    # ... call LLM with context injected into system prompt ...

    # Store the response as a new memory
    engine.remember(response_content, user_id=user_id)
    return response
```

### With SintraLegal

The `SemanticMemory` layer automatically indexes:
- Legal concepts (plaintiff, defendant, negligence, etc.)
- Case numbers (format: `2024-CV-1234`)
- Statute references (`18 U.S.C. § 1234`)

```python
engine.remember(
    "In Case No. 2024-CV-1234, the plaintiff alleged negligence under 42 U.S.C. § 1983",
    user_id="attorney_alice",
    tags=["case-2024-CV-1234", "section-1983", "civil-rights"],
    importance=0.9,
)
```

### With SintraAgent

```python
from memory.memory_types import Task
from memory import WorkingMemory

wm = WorkingMemory()

# Track multi-step agent work
wm.set_current_task(Task(
    name="Research case law",
    description="Find relevant precedents for Smith v. Jones",
    priority=8,
))

# Use stack for nested operations
wm.push_to_stack({"step": "search_westlaw", "query": "negligence auto accident"})
result = await search_westlaw(wm.pop_from_stack()["query"])
```

---

## Running Tests

```bash
cd SintraPrime-Unified
python -m pytest memory/tests/test_memory.py -v
# 55+ tests covering all memory layers
```

---

## File Structure

```
memory/
├── __init__.py              # Public API exports
├── memory_types.py          # Data models (MemoryEntry, UserProfile, etc.)
├── semantic_memory.py       # Long-term knowledge store (SQLite + TF-IDF)
├── episodic_memory.py       # Conversation history (SQLite, rolling window)
├── working_memory.py        # Active session context (in-memory, thread-safe)
├── user_profile.py          # Personal AI profiles (JSON files)
├── memory_engine.py         # Master orchestrator
├── memory_api.py            # FastAPI REST endpoints
├── MEMORY_ENGINE.md         # This file
└── tests/
    ├── __init__.py
    └── test_memory.py       # 55+ unit tests
```

---

## Storage Locations

| Layer | Default Path |
|-------|-------------|
| Semantic DB | `~/.sintra/memory/semantic.db` |
| Episodic DB | `~/.sintra/memory/episodic.db` |
| User Profiles | `~/.sintra/profiles/{user_id}.json` |

All paths are configurable via constructor arguments.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-04 | Initial release — 4-layer memory system |

---

*Built for SintraPrime-Unified | Inspired by Hermes Agent, Claude Memory, Pi AI*

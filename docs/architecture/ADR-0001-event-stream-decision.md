# ADR-0001: Workflow Event Stream Architecture

**Status:** DRAFT - Decision Pending PR-0006A Review  
**Date:** 2026-06-14  
**Deciders:** (TBD)  
**Technical Story:** PR-0006A Event Stream Feasibility Review  

---

## Context

SintraPrime-Unified requires durable workflow state to support:
- Evidence Command Center long-running evidence processing
- Credit Command Center multi-step credit report analysis  
- Trust Administration multi-week case workflows
- Consumer dispute automation with restart recovery
- Multi-agent orchestration with checkpoint resumption

**Current State:**
- `StateGraph` defaults to `InMemoryCheckpointer` (RAM-backed)
- Workflow checkpoints lost on process restart
- `DurableStore` exists with SQLite-backed persistence but NOT wired by default
- `portal.messages` table exists for user messaging, not workflow events

**Problem:**
- Long-running workflows (Credit Command Center analyzing 500 tradelines) lose progress after restart
- Agent resumption not possible without durable checkpoints
- Production deployment blocked by recoverability gap

---

## Decision Drivers

### Must Have
- Workflow state survives process restart
- Checkpoints persist across server reboots
- Recovery from crash/kill without data loss
- Support workflows lasting hours to weeks
- Audit trail for compliance

### Should Have
- PostgreSQL-compatible for production scaling
- Low migration complexity from current state
- Minimal performance overhead
- Clear separation from user-facing data
- Indexing for efficient workflow resumption

### Could Have
- Multi-database support (SQLite dev, PostgreSQL prod)
- Connection pooling
- Retention policies separate from business data
- Query optimization for specific workflow patterns

### Won't Have (Out of Scope)
- Distributed consensus (Raft/Paxos)
- Kafka/RabbitMQ integration (no proof of need yet)
- Real-time streaming analytics
- Cross-region replication

---

## Options Considered

### Option A: Use `portal.messages` as Workflow Event Stream

**Description:**
Extend the existing `portal.messages` table to store both user messages and workflow checkpoint events.

**Pros:**
- Reuse existing PostgreSQL infrastructure
- No new tables or schemas
- Unified message store

**Cons:**
- ❌ Mixing user communication with system events (conceptual confusion)
- ❌ Encryption overhead inappropriate for workflow checkpoints
- ❌ Index structure optimized for thread queries, not workflow resumption
- ❌ Retention policies conflict (user privacy vs audit requirements)
- ❌ Schema evolution creates breaking changes for user messaging
- ❌ Query patterns incompatible (chat retrieval vs checkpoint loading)

**Evidence:** See PR-0006A Section "Portal Messages Analysis"

**Recommendation:** ❌ REJECT

---

### Option B: Create Dedicated `workflow_events` Table

**Description:**
New PostgreSQL table specifically designed for workflow state persistence.

**Schema:**
```sql
CREATE TABLE workflow_events (
    event_id UUID PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    graph_id TEXT NOT NULL,
    event_type TEXT NOT NULL,  -- checkpoint | state_update | node_transition
    node_name TEXT,
    state JSONB NOT NULL,
    visited_counts JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX idx_workflow_events_workflow_run ON workflow_events(workflow_id, run_id);
CREATE INDEX idx_workflow_events_timestamp ON workflow_events(timestamp);
CREATE INDEX idx_workflow_events_graph ON workflow_events(graph_id);
```

**Pros:**
- ✅ Purpose-built for workflow state
- ✅ Optimized indexes for checkpoint retrieval
- ✅ Clean separation from user data
- ✅ PostgreSQL-native (production ready)
- ✅ JSONB for flexible state storage

**Cons:**
- New table requires migration
- New code for event persistence layer
- Connection pool integration needed
- Estimated 3-5 days development

**Recommendation:** ✅ VIABLE - Medium effort, high confidence

---

### Option C: Wire `DurableStore` into StateGraph (SQLite → PostgreSQL Evolution)

**Description:**
1. **Phase 1:** Use existing `DurableStore` with file-based SQLite (immediate)
2. **Phase 2:** Extend `DurableStore` to support PostgreSQL backend (future)

**Phase 1 Implementation:**
```python
# orchestration/langgraph_engine.py
from .durable_execution import DurableStore

class StateGraph:
    def __init__(self, graph_id=None, checkpointer=None, max_cycles=50):
        self.graph_id = graph_id or f"graph_{uuid.uuid4().hex[:8]}"
        
        if checkpointer is None:
            db_path = os.environ.get("WORKFLOW_DB_PATH", "workflows.db")
            durable_store = DurableStore(db_path=db_path)
            checkpointer = DurableStoreCheckpointerAdapter(durable_store)
        
        self.checkpointer = checkpointer
```

**Phase 2 Implementation:**
```python
class DurableStore:
    def __init__(self, db_path=":memory:", pg_pool=None):
        if pg_pool:
            self._backend = PostgresBackend(pg_pool)
        else:
            self._backend = SQLiteBackend(db_path)
```

**Pros:**
- ✅ Leverages existing tested code (`DurableStore` already works)
- ✅ Proven by PR-0006A recovery tests
- ✅ Low-risk Phase 1 (single file change)
- ✅ Evolution path to PostgreSQL without rewrite
- ✅ Backward compatible (explicit checkpointer still works)
- ✅ Immediate restart recovery capability
- ✅ No migration required for Phase 1

**Cons:**
- SQLite file separate from main database (Phase 1)
- Requires adapter class for checkpoint interface
- PostgreSQL evolution deferred to Phase 2

**Recommendation:** ✅ PREFERRED - Lowest risk, fastest time-to-value

---

### Option D: Kafka/Event Sourcing

**Description:**
Full event sourcing with Kafka as event log.

**Pros:**
- Industry standard event stream
- Replay capability
- Horizontal scaling

**Cons:**
- ❌ No proof of need for Kafka-scale throughput
- ❌ Operational complexity (Kafka cluster, Zookeeper)
- ❌ Over-engineering for current scale
- ❌ 4-8 weeks implementation effort

**Recommendation:** ❌ REJECT - Premature optimization

---

## Decision

**[DECISION SECTION INTENTIONALLY LEFT BLANK]**

**This section will be completed after:**
1. PR-0006A findings are reviewed
2. Stakeholder discussion
3. Architecture review board approval

**Expected decision date:** TBD  
**Required approvals:** TBD  

---

## Consequences

### If Option A (portal.messages) is chosen:
- ⚠️ Technical debt from mixed concerns
- ⚠️ Query performance degradation likely
- ⚠️ Migration complexity for future separation

### If Option B (workflow_events table) is chosen:
- ✅ Clean architecture
- ⏱ 3-5 days development time
- ✅ Production-ready from start

### If Option C (DurableStore evolution) is chosen:
- ✅ Immediate value with Phase 1
- ✅ Low-risk incremental approach
- ⏱ PostgreSQL migration deferred but planned
- ✅ Backward compatibility maintained

### If Option D (Kafka) is chosen:
- ⚠️ High operational burden
- ⏱ 4-8 weeks before value delivery
- ⚠️ Infrastructure complexity increase

---

## Validation Criteria

The chosen solution must demonstrate:

1. **Restart Recovery** - Workflow resumes from last checkpoint after process kill
2. **Data Durability** - Checkpoints survive server reboot
3. **Performance** - Checkpoint save/load < 100ms for typical workflow state
4. **Scalability** - Support 100+ concurrent workflows
5. **Auditability** - Complete history of workflow transitions
6. **Test Coverage** - Restart recovery tests passing

---

## Implementation Plan

*To be completed after decision is made*

---

## References

- PR-0006A: Event Stream Feasibility Review
- `orchestration/langgraph_engine.py` - Current StateGraph implementation
- `orchestration/durable_execution.py` - DurableStore implementation
- `portal/models/message.py` - Portal messages schema
- `tests/test_pr0006a_restart_recovery.py` - Restart recovery tests

---

## Notes

**From PR-0006A findings:**
- InMemoryCheckpointer proven to lose state on restart (test evidence)
- DurableStore proven to survive restart (test evidence)
- portal.messages schema incompatible with workflow events
- 900K rows/year projection is UNVERIFIED (needs measurement)
- Persistence score 6.1/10 cannot be reproduced (recommend 5.7/10)

**Open Questions:**
1. What is acceptable checkpoint latency budget?
2. Should checkpoint saves be synchronous or async?
3. What retention policy for completed workflows?
4. Should failed workflows be auto-retried or require manual intervention?

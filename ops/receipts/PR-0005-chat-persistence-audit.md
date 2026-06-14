# PR-0005: Persistence & Recoverability Audit

**Status:** DRAFT  
**Priority:** P0 (Blocks Evidence Command Center)  
**Assignee:** Hermes (AI Architect)  
**Estimated Effort:** 6 hours (audit only, no implementation)  
**Created:** 2026-06-14  
**Updated:** 2026-06-14 (expanded to recoverability)  
**Phase:** Stability Layer (PR-1 through PR-5)

---

## Problem Statement

**Core Question:**  
*"Can the system recover from failure without losing work?"*

**NOT:**  
- ❌ "Does data persist?" (storage is not recovery)
- ❌ "How do we build persistence?" (that's a future PR)

### Critical Scenario

```
Client #0
Credit Command Center Workflow
Step 18 of 42

✓ Import credit report
✓ Parse tradelines  
✓ Generate violations
✓ Create scorecard
→ [SERVER CRASHES]

After restart:
Option A: Resume at Step 19 ✅ (Production-Ready)
Option B: Start over ❌ (Chatbot-Tier)
```

**This is the difference between:**
- An AI **assistant** (stateless, ephemeral)
- An AI **operator** (stateful, recoverable)

For SintraPrime workflows (Evidence Command Center, Credit Command Center, Trust Administration), this matters because:
- Legal workflows span hours/days (not seconds)
- Client work cannot be lost mid-process
- Audit trails must be defensible in court
- Hermes must resume where it stopped, not restart from scratch

---

## Scope: Recoverability Audit (4 Tiers)

### Tier 1: User Data Recovery
**Can the system recover 100% of user-generated data after server crash?**

- ❓ Conversations (chat history)
- ❓ Tickets (case records)
- ❓ Portal messages
- ❓ Uploaded evidence (PDFs, credit reports, documents)
- ❓ Generated documents (affidavits, scorecards, notices)

**Recovery Target:** 100% (zero data loss)

---

### Tier 2: Workflow State Recovery
**Can workflows resume from the exact step where they crashed?**

**Example:**
```
Workflow: Credit Command Center
Client: C-0001
Progress: Step 18 of 42 (violation analysis complete)
Next: Generate affidavit

[CRASH]

Recovery:
✅ Resume at Step 19 (affidavit generation)
❌ Restart at Step 1 (re-import credit report)
```

**Questions:**
- ❓ Is current step number stored?
- ❓ Is progress percentage stored?
- ❓ Can Hermes answer "What was I doing?"
- ❓ Can Hermes answer "What remains?"

**Recovery Target:** Resume from last completed step (no rework)

---

### Tier 3: Agent Memory Recovery
**Can agents reconstruct their context after restart?**

**Example Record:**
```json
{
  "task_id": "credit-audit-uacc-0001",
  "status": "running",
  "last_step": "violation-analysis",
  "progress_pct": 68,
  "next_step": "generate-affidavit",
  "context": {
    "client_id": "C-0001",
    "violations_found": 14,
    "tradelines_analyzed": 23
  }
}
```

**Questions:**
- ❓ Does Hermes know what it was doing?
- ❓ Does Hermes know why it was doing it?
- ❓ Can Hermes resume the task with full context?

**Recovery Target:** Full context restoration (no memory loss)

---

### Tier 4: Evidence Chain Recovery
**Can every action be reconstructed with a defensible audit trail?**

**Example Receipt:**
```json
{
  "timestamp": "2026-06-14T15:54:40.260Z",
  "actor": "hermes",
  "action": "generate_affidavit",
  "input": {
    "client_id": "C-0001",
    "violations": [...]
  },
  "output": {
    "file": "Affidavit_of_Facts.pdf",
    "hash": "A7F3C2B1..."
  },
  "result": "success"
}
```

**Questions:**
- ❓ Is every tool invocation logged?
- ❓ Are inputs/outputs/results stored?
- ❓ Are timestamps and hashes recorded?
- ❓ Can we prove "Hermes generated this affidavit at this time with this data"?

**Recovery Target:** Court-defensible audit trail (legal compliance)

---

### Out of Scope

- ❌ Implementation (provide options only)
- ❌ Code changes (diagnostic only)
- ❌ Performance testing
- ❌ Data migration
- ❌ Backup/restore procedures (separate PR)

---

## Investigation Checklist

### Phase 1: What Exists Today (30 min)

**Database Tables:**
```bash
# List all persistence-related tables
psql sintraprime_unified -c "
  SELECT table_name 
  FROM information_schema.tables 
  WHERE table_name LIKE '%message%' 
     OR table_name LIKE '%conversation%'
     OR table_name LIKE '%execution%'
     OR table_name LIKE '%audit%'
     OR table_name LIKE '%receipt%'
  ORDER BY table_name;
"

# Inspect messages schema
psql sintraprime_unified -c "\d messages"

# Inspect portal messages schema (if different)
psql sintraprime_unified -c "\d portal_messages"

# Inspect execution history
psql sintraprime_unified -c "\d execution_history"
```

**Evidence to Capture:**
- [ ] List of ALL tables related to persistence
- [ ] Schema for each table (columns, types, constraints)
- [ ] Duplicate tables (e.g., messages vs portal_messages)

---

### Phase 2: What Disappears (1 hour)

**Red Flag Patterns:**

```bash
# In-memory state (DISAPPEARS on restart)
grep -r "self\.messages\s*=\s*\[\]" --include="*.py" agents/ orchestration/ scheduler/
grep -r "self\.state\s*=\s*{}" --include="*.py" agents/ orchestration/ scheduler/
grep -r "tasks\s*=\s*\[\]" --include="*.py" scheduler/

# Queue implementations
grep -r "Queue\(\)" --include="*.py" scheduler/
grep -r "class.*Queue" --include="*.py" scheduler/

# Session-only storage
grep -r "session\[" --include="*.py" agents/
```

**Critical Files:**

| File | Check For | Risk |
|------|-----------|------|
| `agents/chat/chat_agent.py` | `self.messages = []` | Conversations lost |
| `agents/nova/nova_agent.py` | `self.action_history = []` | Tool history lost |
| `scheduler/task_queue.py` | In-memory queue | Tasks lost |
| `orchestration/langgraph_engine.py` | Checkpoint config | Workflows restart |
| `memory/episodic_memory.py` | RAM-only storage | Memory lost |

**Evidence to Capture:**
- [ ] Line-by-line list of in-memory state (`file:line: pattern`)
- [ ] Queue type (Redis/PostgreSQL/in-memory)
- [ ] Checkpoint configuration (enabled/disabled)

---

### Phase 3: Configuration Review (30 min)

**Redis Persistence:**
```bash
# Check Redis persistence config
cat docker-compose.yml | grep -A 10 "redis:"

# Check if Redis data volume is persistent
docker volume inspect sintraprime-unified_redis_data

# Verify Redis AOF/RDB settings
docker exec sintraprime-redis redis-cli CONFIG GET save
docker exec sintraprime-redis redis-cli CONFIG GET appendonly
```

**Expected Findings:**
- [ ] Redis data volume: `redis_data:/data` (persistent)
- [ ] AOF enabled: `appendonly yes` (or RDB snapshots configured)
- [ ] Redis used for: sessions, cache, or message queue?

**PostgreSQL Persistence:**
```bash
# Check database volume
cat docker-compose.yml | grep -A 10 "postgres:"

# Verify data persistence
docker volume inspect sintraprime-unified_postgres_data
```

**Expected Findings:**
- [ ] PostgreSQL volume: `postgres_data:/var/lib/postgresql/data` (persistent)
- [ ] Schema initialization: `unified_schema.sql` loaded on startup
- [ ] Backup strategy: NONE (flagged as gap)

---

### Phase 4: Restart Simulation (45 min)

**Test Scenario:**

```bash
# 1. Create state
docker-compose up -d
curl -X POST http://localhost:8080/api/chat \
  -d '{"user_id":"test","message":"Message 1"}'

# Verify state exists
psql sintraprime_unified -c "SELECT COUNT(*) FROM messages WHERE sender_id='test';"
# Expected: 1 row

# 2. Restart (graceful)
docker-compose restart api

# Check persistence
psql sintraprime_unified -c "SELECT COUNT(*) FROM messages WHERE sender_id='test';"
# Expected: 1 row (PASS) or 0 rows (FAIL)

# 3. Crash (ungraceful)
docker kill -s SIGKILL sintraprime-api
docker-compose up -d api

# Check persistence again
curl http://localhost:8080/api/chat/history?user_id=test
# Expected: Message 1 present (PASS) or missing (FAIL)
```

**Evidence to Capture:**
- [ ] Database row count: Before restart = 1, After restart = ? (PASS/FAIL)
- [ ] API response: Message history returned (PASS) or empty (FAIL)
- [ ] Logs: State recovery messages (if any)

---

### Phase 5: Integration Points (1 hour)

**Portal Messages Integration:**

```bash
# Check Portal Messages schema
cat portal/models/message.py

# Check if Chat Agent uses Portal Messages
grep -r "from portal.models import Message" agents/chat/
grep -r "Message.create\|Message.query" agents/chat/

# Check message routing
cat portal/routers/messages.py
cat portal/services/notification_service.py
```

**Questions to Answer:**
- [ ] Does Chat Agent write to `portal.models.Message`?
- [ ] Does Chat Agent write to `core.messages` (unified_schema.sql)?
- [ ] Are there TWO separate message systems? (conflict risk)
- [ ] Can Portal Messages be queried by session/conversation ID?
- [ ] Is there a bridge between Core Messages ↔ Portal Messages?

**Evidence to Capture:**
- Data flow diagram: Chat → Storage → Portal
- List of duplicate message tables (if any)
- Integration points (where data is copied/synced)

---

## Deliverable: Persistence & Recoverability Scorecard

**Format:** Single-page scorecard with maturity scores

```markdown
# Persistence & Recoverability Audit
**Date:** 2026-06-14  
**Auditor:** Hermes  
**Duration:** 6 hours

## Persistence Maturity Score

| System                | Persisted | Recoverable | Score | Evidence |
|-----------------------|-----------|-------------|-------|----------|
| Portal Messages       | [Yes/No]  | [Yes/No]    | [0-10] | [table/file/none] |
| Evidence Files        | [Yes/No]  | [Yes/No]    | [0-10] | [MinIO/S3/local] |
| Workflow State        | [Yes/Partial/No] | [Yes/Partial/No] | [0-10] | [table/checkpoint] |
| Agent Memory          | [Yes/Partial/No] | [Yes/Partial/No] | [0-10] | [table/Redis/none] |
| Queue Jobs            | [Yes/Partial/No] | [Yes/Partial/No] | [0-10] | [Redis/PG/memory] |
| Tool History          | [Yes/Partial/No] | [Yes/Partial/No] | [0-10] | [execution_history] |
| Checkpoints           | [Yes/No]  | [Yes/No]    | [0-10] | [LangGraph config] |
| Audit Receipts        | [Yes/Partial/No] | [Yes/Partial/No] | [0-10] | [audit_trail table] |

**Overall Maturity:** [0-10] / 10  
**Production Readiness:** [READY / AT RISK / BLOCKED]

---

## Scoring Rubric

**10/10:** ✅ Persisted + 100% recoverable + tested  
**7-9/10:** ⚠️ Persisted + partially recoverable  
**4-6/10:** ⚠️ Partial persistence (data loss possible)  
**1-3/10:** ❌ Memory-only (lost on restart)  
**0/10:** ❌ Missing (no implementation)

## Tier 1: User Data Recovery

### Portal Messages
**Score:** [0-10] / 10  
**Persisted:** [Yes ✅ / No ❌]  
**Recoverable:** [Yes ✅ / No ❌]

**Evidence:**
- Storage: [PostgreSQL `portal.messages` / In-Memory / None]
- Restart test: [PASS - All messages recovered / FAIL - Messages lost]
- Code reference: `portal/models/message.py:15`

**Conclusion:** [User conversations survive restart / User conversations lost]

---

### Evidence Files
**Score:** [0-10] / 10  
**Persisted:** [Yes ✅ / No ❌]  
**Recoverable:** [Yes ✅ / No ❌]

**Evidence:**
- Storage: [MinIO / Local disk / In-Memory / None]
- File retention: [Permanent / 30 days / None]
- Volume mount: `docker-compose.yml` line X

**Conclusion:** [Uploaded files survive restart / Uploaded files lost]

---

### Generated Documents
**Score:** [0-10] / 10  
**Persisted:** [Yes ✅ / No ❌]  
**Recoverable:** [Yes ✅ / No ❌]

**Evidence:**
- Storage: [MinIO / Database BLOB / Local disk / None]
- Example: Affidavits, scorecards, notices

**Conclusion:** [Generated documents survive restart / Must regenerate after crash]

---

## Tier 2: Workflow State Recovery

### Workflow Checkpoints
**Score:** [0-10] / 10  
**Persisted:** [Yes ✅ / Partial ⚠️ / No ❌]  
**Recoverable:** [Yes ✅ / Partial ⚠️ / No ❌]

**Evidence:**
```python
# orchestration/langgraph_engine.py:45
checkpointer = SqliteSaver(...)  # ✅ Configured
# OR
workflow = StateGraph(...)       # ❌ No checkpointer
```

**Restart Test:**
```
Workflow: Credit Command Center
Step before crash: 18 of 42
Step after restart: [18 ✅ / 1 ❌]
```

**Conclusion:**
- ✅ Workflows resume from last checkpoint
- ❌ Workflows restart from beginning (all work lost)

**Impact:** [Can run multi-day workflows / Cannot run workflows >1 hour]

---

### Task Queue Durability
**Score:** [0-10] / 10  
**Persisted:** [Yes ✅ / No ❌]  
**Recoverable:** [Yes ✅ / No ❌]

**Evidence:**
```python
# scheduler/task_queue.py:15
self.tasks = []  # ❌ In-memory (lost on restart)
# OR
redis.lpush("tasks", task)  # ✅ Persistent queue
```

**Restart Impact:**
- Queued tasks: [Survive restart ✅ / Lost ❌]
- Background jobs: [Resume ✅ / Lost ❌]

**Conclusion:** [Can queue long-running tasks / Queue is ephemeral]

---

## Tier 3: Agent Memory Recovery

### Agent State (Nova/Sigma/Zero)
**Score:** [0-10] / 10  
**Persisted:** [Yes ✅ / Partial ⚠️ / No ❌]  
**Recoverable:** [Yes ✅ / Partial ⚠️ / No ❌]

**Evidence:**
```python
# agents/nova/nova_agent.py:23
self.state = {
    "task_id": "credit-audit-0001",
    "progress_pct": 68,
    "last_step": "violation-analysis"
}
# Stored in: [PostgreSQL / Redis / In-Memory]
```

**Recovery Test:**
```
Task: Analyze 500 evidence files
Progress before crash: File 247 of 500
Progress after restart: [File 247 ✅ / File 1 ❌]
```

**Conclusion:**
- ✅ Agents resume from last known state
- ❌ Agents restart from zero (rework all completed steps)

**Impact:** [Can run multi-hour agent tasks / Agents are stateless]

---

### Working Memory
**Score:** [0-10] / 10  
**Persisted:** [Yes ✅ / No ❌]  
**Recoverable:** [Yes ✅ / No ❌]

**Evidence:**
- Storage: [PostgreSQL `knowledge_entries` / Redis / In-Memory]
- Example: Client context, intermediate results, decisions

**Questions Hermes Can Answer After Restart:**
- ❓ "What was I doing?" [Yes ✅ / No ❌]
- ❓ "Why was I doing it?" [Yes ✅ / No ❌]
- ❓ "What remains?" [Yes ✅ / No ❌]

**Conclusion:** [Full context restoration / Memory loss / Total amnesia]

---

## Tier 4: Evidence Chain Recovery

### Tool Execution History
**Score:** [0-10] / 10  
**Persisted:** [Yes ✅ / Partial ⚠️ / No ❌]  
**Recoverable:** [Yes ✅ / Partial ⚠️ / No ❌]

**Evidence:**
- Database table: `execution_history` (columns: id, command, status, result, agent_id, timestamp)
- Logged: [Tool name ✅ / Input ❓ / Output ❓ / Hash ❓]

**Example Record:**
```json
{
  "timestamp": "2026-06-14T15:54:40.260Z",
  "actor": "hermes",
  "tool": "generate_affidavit",
  "input": {...},      // ✅ Stored / ❌ Missing
  "output": {...},     // ✅ Stored / ❌ Missing
  "hash": "A7F3...",   // ✅ Stored / ❌ Missing
  "result": "success"
}
```

**Court-Defensible Audit Trail:**
- ✅ Can prove "Hermes generated this affidavit at this time with this data"
- ❌ Cannot reconstruct tool execution (missing inputs/outputs)

**Conclusion:** [Full audit trail / Partial trail / No trail]

---

### Audit Receipts
**Score:** [0-10] / 10  
**Persisted:** [Yes ✅ / Partial ⚠️ / No ❌]  
**Recoverable:** [Yes ✅ / Partial ⚠️ / No ❌]

**Evidence:**
- Storage: `governance/audit_trail.py` writes to `portal.audit` table
- Immutability: [Append-only ✅ / Mutable ❌]
- Retention: [Unlimited ✅ / 30 days / None]

**Actions with Receipts:**
- ✅ Affidavit generated
- ✅ Notice sent
- ❓ Dispute created
- ❓ UCC filed
- ❓ Evidence packet created

**Conclusion:** [Complete audit trail / Partial trail / No trail]

---

## Overall Assessment

**Readiness:** [BLOCKED / AT RISK / READY]

**Blocking Issues:**
1. Agent state (Nova/Sigma/Zero) is ephemeral → Multi-step workflows fail
2. Task queue is in-memory → Background jobs lost on restart
3. Workflow checkpoints missing → Long-running processes cannot resume

**Working Features:**
1. Chat history persists ✅
2. Audit trail persists ✅
3. Tool logs partially persist ✅

---

## Recommended Architecture

Based on audit findings, recommend **one** of the following:

---

### Phase A: Portal Messages as Canonical Event Stream (RECOMMENDED)

**Use existing `portal.messages` as the single source of truth for all state**

**Rationale:**
- If portal.messages already persists user conversations ✅
- Extend with workflow events (not just chat messages)
- Single table = single query interface = consistency

**Changes Required:**

1. **Extend portal.messages schema:**
```sql
ALTER TABLE portal.messages ADD COLUMN event_type VARCHAR(50);
-- event_type: 'chat' | 'workflow_step' | 'tool_execution' | 'receipt'

ALTER TABLE portal.messages ADD COLUMN workflow_id UUID;
ALTER TABLE portal.messages ADD COLUMN step_number INT;
ALTER TABLE portal.messages ADD COLUMN progress_pct FLOAT;
ALTER TABLE portal.messages ADD COLUMN metadata JSONB;
```

2. **Store workflow checkpoints as messages:**
```json
{
  "event_type": "workflow_step",
  "workflow_id": "credit-audit-0001",
  "step_number": 18,
  "progress_pct": 68,
  "metadata": {
    "client_id": "C-0001",
    "violations_found": 14,
    "next_step": "generate_affidavit"
  }
}
```

3. **Store tool executions as messages:**
```json
{
  "event_type": "tool_execution",
  "metadata": {
    "tool": "generate_affidavit",
    "input": {...},
    "output": {...},
    "hash": "A7F3C2B1..."
  }
}
```

**Pros:**
- ✅ Reuses existing infrastructure
- ✅ Single source of truth
- ✅ Fast implementation (2-3 weeks)
- ✅ Query all events: `SELECT * FROM portal.messages WHERE workflow_id = ?`

**Cons:**
- ⚠️ Table grows faster (add retention policy for old workflows)

---

### Phase B: Add Workflow Checkpoints

**Implement LangGraph checkpointer with PostgreSQL backend**

```python
# orchestration/langgraph_engine.py
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver(
    conn_string="postgresql://...",
    table_name="workflow_checkpoints"
)

workflow = StateGraph(...).compile(checkpointer=checkpointer)
```

**This enables:**
- ✅ Workflows resume from exact step after crash
- ✅ No rework on restart
- ✅ Multi-day workflows viable

**Effort:** 1 week (1 engineer)

---

### Phase C: Add Durable Receipts

**Ensure every action writes to audit trail**

```python
# After every tool execution:
audit_trail.record(
    timestamp=datetime.utcnow(),
    actor="hermes",
    action="generate_affidavit",
    input={...},
    output={...},
    hash=hash_output(output),
    result="success"
)
```

**This enables:**
- ✅ Court-defensible audit trail
- ✅ Full recoverability of "what happened"
- ✅ Compliance with legal record-keeping

**Effort:** 2 weeks (1 engineer)

---

### Phase D: Add Agent Resumption

**Agents read checkpoints on startup and resume tasks**

```python
# agents/nova/nova_agent.py
class NovaAgent:
    def on_restart(self):
        # Read last known state from portal.messages
        last_state = db.query(
            "SELECT * FROM portal.messages "
            "WHERE event_type='workflow_step' "
            "ORDER BY created_at DESC LIMIT 1"
        )
        
        if last_state:
            self.task_id = last_state.workflow_id
            self.progress = last_state.progress_pct
            self.next_step = last_state.metadata['next_step']
            
            # Resume where we left off
            self.execute(self.next_step)
```

**This enables:**
- ✅ Hermes becomes an operating system (not just an AI layer)
- ✅ Agents answer "What was I doing?" on restart
- ✅ True operator mode (multi-session tasks)

**Effort:** 3-4 weeks (1 engineer)

---

## Total Timeline

**Phase A:** 2-3 weeks  
**Phase B:** 1 week  
**Phase C:** 2 weeks  
**Phase D:** 3-4 weeks  

**Total:** 8-10 weeks (1 engineer, sequential)  
**Critical Path:** Phase A + B (unlock Evidence Command Center)  
**Full Maturity:** Phase A + B + C + D (production-grade operator)

---

## Appendix: Test Results

**Restart Test Output:**
```sql
-- Before restart
SELECT COUNT(*) FROM portal.messages WHERE user_id='test';
-- Result: 1

-- After `docker-compose restart api`
SELECT COUNT(*) FROM portal.messages WHERE user_id='test';
-- Result: 1 ✅ PASS
```

**In-Memory State (agents/nova/nova_agent.py:23):**
```python
self.action_history = []  # ❌ FAIL - Lost on restart
```

**Queue State (scheduler/task_queue.py:15):**
```python
self.tasks = []  # ❌ FAIL - Lost on restart
```
```

---

## Success Criteria

This audit is **COMPLETE** when:

- [x] All 5 investigation phases executed
- [x] Evidence captured for each section
- [x] Restart simulation performed with documented results
- [x] Recommendation provided (Option A/B/C with rationale)
- [x] Impact on Evidence Command Center documented
- [x] Next PR defined (implementation or proceed)

---

## Risk Mitigation

**If findings show NO persistence:**
- Immediate stakeholder notification (blocks production timeline)
- Escalate to P0 priority for implementation PR
- Estimate 6-8 week delay for Evidence Command Center

**If findings show PARTIAL persistence:**
- Document gaps with severity (CRITICAL/HIGH/MEDIUM)
- Define minimum viable persistence (MVP) for Evidence Command Center
- Phased implementation (MVP → Full)

**If findings show FULL persistence:**
- Validate with integration tests
- Document for onboarding
- Proceed to Evidence Command Center with confidence

---

## Dependencies

**Requires:**
- ✅ PR-0001: Repository Audit (this provides context)
- ✅ Docker environment running (for restart tests)
- ✅ Database access (for schema inspection)

**Blocks:**
- Evidence Command Center implementation
- Consumer Case Pipeline
- Trust Administration workflows
- Any multi-session AI workflows

---

## Timeline

**Total Effort:** 6 hours (single day task)

**Hour 1:** Database inspection (Tier 1: User Data)  
**Hour 2:** Code search for in-memory state (Tier 2: Workflow State)  
**Hour 3:** Agent memory audit (Tier 3: Agent Memory)  
**Hour 4:** Audit trail verification (Tier 4: Evidence Chain)  
**Hour 5:** Restart simulation across all tiers  
**Hour 6:** Compile scorecard + maturity assessment + recommendation

**Deliverable:** 2-page scorecard with maturity scores (0-10 per system)

---

## Notes

**Key Insights:**

> "The fastest route to production is usually **one source of truth**, not two."

**Portal Messages as Event Stream:**
- Chat messages are events
- Workflow steps are events  
- Tool executions are events
- Receipts are events

All written to `portal.messages` with `event_type` discriminator.

**Recovery = Replay Events:**
```python
# On restart, Hermes reads:
events = db.query("SELECT * FROM portal.messages WHERE workflow_id = ? ORDER BY created_at")

# Reconstructs state:
for event in events:
    if event.event_type == 'workflow_step':
        current_step = event.step_number
    elif event.event_type == 'tool_execution':
        tool_history.append(event)

# Resumes:
workflow.resume(from_step=current_step + 1)
```

This transforms Hermes from:
- ❌ AI assistant (stateless, ephemeral)  
- ✅ AI operator (stateful, recoverable, production-grade)

---

**END PR-0005 SPECIFICATION**

---

## Approval Required

- [ ] Repository Owner (confirms priority)
- [ ] Lead Architect (confirms scope)
- [ ] Evidence Command Center Stakeholder (confirms blocking relationship)

**Approved By:** _______________  
**Date:** _______________

---

**Auto-Generated Receipt:**

```json
{
  "pr_id": "PR-0005",
  "title": "Chat Agent Persistence Gap Audit",
  "created": "2026-06-14T15:45:58.345Z",
  "status": "draft",
  "assignee": "hermes",
  "priority": "P0",
  "phase": "stability_layer",
  "estimated_effort_hours": 6,
  "blocking": [
    "evidence_command_center",
    "consumer_case_pipeline",
    "trust_administration"
  ],
  "dependencies": [
    "PR-0001"
  ],
  "deliverable": "audit_report_with_recommendation.md",
  "success_metric": "persistence_strategy_defined"
}
```

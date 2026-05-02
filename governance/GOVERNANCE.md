# 🛡️ SintraPrime-Unified AI Governance Framework

## Why AI Governance Matters

> **"40% of agentic AI projects will be cancelled by 2027 due to lack of AI governance."**
> — Gartner, 2024

As AI agents take on increasingly autonomous roles — filing legal documents, sending client communications, executing financial transactions — the absence of human oversight creates existential risk for organizations. A single unreviewed action by an AI agent can result in:

- **Legal liability** (unauthorized practice of law, invalid contract signing)
- **Financial loss** (erroneous wire transfers, fraudulent payments)
- **Regulatory penalties** (GDPR violations, HIPAA breaches, SEC infractions)
- **Reputational damage** (unsanctioned client communications)

The SintraPrime-Unified Governance Framework addresses this by implementing **Human-in-the-Loop (HITL)** controls, **audit trails**, **compliance monitoring**, and **emergency intervention** capabilities at the infrastructure level.

---

## Architecture Overview

```
Agent Action Request
        │
        ▼
┌───────────────────┐
│  GovernanceEngine │  ← Master orchestrator
│   before_action() │
└───────────────────┘
        │
        ├─ 1. Emergency Stop Check
        ├─ 2. Guardrail Check  ──────────→ InterventionController
        ├─ 3. Risk Assessment  ──────────→ RiskAssessor
        ├─ 4. Compliance Check ──────────→ ComplianceMonitor
        └─ 5. Approval Gate    ──────────→ ApprovalGate
                │                                │
                ▼                                ▼
          AuditTrail                    Human Approver
          (log all)                  (approve / reject)
```

---

## How Approval Gates Work

Inspired by **OpenAI Operator** and **Claude Computer Use**, approval gates pause agent execution before high-risk actions and wait for explicit human authorization.

### Workflow

1. **Agent requests action** (e.g., `send_payment`, `sign_contract`)
2. **Risk Assessor** evaluates the action → `CRITICAL`
3. **Approval Gate** creates an `ApprovalRequest` with a unique ID
4. **Notification** sent to designated approvers (email, Slack, etc.)
5. **Agent blocks** — waits up to N minutes for a decision
6. **Human approves/rejects** via API or one-click email link
7. **Agent proceeds** (if approved) or **aborts** (if rejected/expired)
8. **AuditTrail** logs everything — approval ID, approver, timestamp

### One-Click Approval

Every approval request generates a URL:
```
https://app.sintraprime.com/governance/review/{request_id}
```

The approver sees the action details and clicks Approve or Reject — no login required if the link is treated as a token.

---

## Risk Level Classification

| Level | Examples | Approval Required | Reversible |
|-------|----------|-------------------|------------|
| **CRITICAL** | `send_payment`, `wire_transfer`, `sign_contract`, `delete_all_data`, `file_legal_document` | ✅ Always | ❌ Never |
| **HIGH** | `send_email_to_client`, `update_financial_record`, `publish_document`, `schedule_court_filing` | ✅ By default | ⚠️ Sometimes |
| **MEDIUM** | `draft_document`, `search_external_api`, `update_case_notes`, `generate_report` | ❌ No | ✅ Yes |
| **LOW** | `read_data`, `search_database`, `format_document`, `internal_calculation` | ❌ No | ✅ Yes |

### Customizing Thresholds

Organizations can adjust what requires approval:

```python
assessor = RiskAssessor(org_risk_threshold=RiskLevel.MEDIUM)
# Now ALL Medium, High, and Critical actions require approval
```

---

## Audit Trail for Legal Matters

The `AuditTrail` module provides a **tamper-evident, append-only** audit log:

### Key Features

- **SHA-256 checksums** on every entry (tamper detection)
- **SQLite backend** with indexed queries
- **7-year retention** (configurable, legal default)
- **CSV export** for regulatory submissions
- **Compliance reports** formatted for SOC2, HIPAA, GDPR

### Tamper Detection

```python
trail = AuditTrail()
checked, tampered_ids = trail.verify_integrity()
if tampered_ids:
    alert_security_team(tampered_ids)
```

### Example Audit Entry

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-04-26T14:30:00Z",
  "actor": "legal-agent-v2",
  "action": "send_email_to_client",
  "outcome": "approved",
  "risk_level": "HIGH",
  "approval_id": "approval-789",
  "checksum": "sha256:a3f5c2...",
  "metadata": {
    "approver": "john.smith@firm.com",
    "client_id": "client-001"
  }
}
```

---

## Compliance Standards Supported

| Standard | Coverage |
|----------|----------|
| **SOC2** | CC6.1, CC6.2, CC7.2, CC9.2, A1.1 |
| **HIPAA** | §164.308, §164.310, §164.312, §164.314, §164.316 |
| **GDPR** | Art. 5, 13, 17, 25, 30, 32, 37 |
| **ISO 27001** | A.9, A.10, A.12, A.16, A.18 |
| **SOX** | §302, §404, §409, §802 |

Generate a compliance report:

```python
monitor = ComplianceMonitor()
report = monitor.audit_for_standard("SOC2")
print(f"SOC2 Score: {report.score}%")
```

---

## Emergency Stop Procedures

### 🚨 Emergency Stop (Nuclear Option)

Immediately halts ALL agent activity system-wide:

```python
# Via Python
controller = InterventionController()
controller.emergency_stop()

# Via API
POST /governance/emergency-stop?authorized_by=admin-user
```

All agents enter `emergency_stopped` state. No new actions are started until a human explicitly clears the stop:

```python
controller.clear_emergency_stop(authorized_by="jane.doe@firm.com")
```

### Selective Pause

```python
controller.pause_agent("legal-agent-v2")    # pause one agent
controller.pause_all()                       # pause all agents
controller.resume_agent("legal-agent-v2")   # resume
```

### Dead Man's Switch

If no human activity is detected for N hours, all agents auto-pause:

```python
controller = InterventionController(dead_mans_switch_hours=8)
controller.start_dead_mans_switch()
# Human must call record_human_activity() periodically to keep agents running
controller.record_human_activity()
```

### Guardrails

Runtime constraints applied to all agents:

```python
controller.set_guardrail("read_only_mode")     # blocks all write operations
controller.set_guardrail("no_external_api_calls")
controller.remove_guardrail("read_only_mode")
```

### Action Rollback

For reversible actions, record undo payloads before execution:

```python
controller.record_action_for_rollback(
    task_id="task-123",
    action="update_record",
    undo_payload={"restore": {"field": "original_value"}}
)
# Later, if needed:
controller.rollback("task-123")
```

---

## Comparison to OpenAI Operator's Human-in-Loop Approach

| Feature | OpenAI Operator | SintraPrime Governance |
|---------|-----------------|------------------------|
| Approval gates | ✅ Yes | ✅ Yes |
| Risk-based routing | ✅ Yes | ✅ Yes (4 levels) |
| Audit logging | Limited | ✅ Full tamper-evident |
| Compliance reports | ❌ No | ✅ SOC2, HIPAA, GDPR, ISO 27001 |
| Emergency stop | ❌ No | ✅ Full system kill switch |
| Dead man's switch | ❌ No | ✅ Auto-pause on inactivity |
| Action rollback | ❌ No | ✅ For reversible actions |
| Legal domain rules | Limited | ✅ UPL, privilege, SEC |
| GDPR data residency | ❌ No | ✅ Yes |
| Decorator pattern | ❌ No | ✅ `@requires_approval` |

---

## Quick Start

```python
from governance import GovernanceEngine

engine = GovernanceEngine(
    db_path="/data/audit.db",
    base_url="https://app.sintraprime.com",
)

# Before any agent action
allowed = engine.before_action(
    action="send_payment",
    payload={"amount": 5000, "recipient": "vendor@example.com"},
    agent_id="finance-agent-1",
    domain="financial",
)

if allowed:
    result = execute_payment(amount=5000)
    engine.after_action("send_payment", result, "finance-agent-1")
else:
    print("Action blocked by governance policy")
```

### Using the Decorator

```python
from governance import GovernanceEngine
from governance.risk_types import RiskLevel

engine = GovernanceEngine()

@engine.requires_approval(min_risk=RiskLevel.HIGH, domain="legal")
def file_court_document(case_id: str, document_path: str):
    """This function will pause until a human approves."""
    ...
```

---

## REST API

Mount the governance router in your FastAPI app:

```python
from fastapi import FastAPI
from governance import GovernanceEngine
from governance.governance_api import create_governance_router

app = FastAPI()
engine = GovernanceEngine()
app.include_router(create_governance_router(engine))
```

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/governance/pending` | List pending approvals |
| `POST` | `/governance/approve/{id}` | Approve an action |
| `POST` | `/governance/reject/{id}` | Reject an action |
| `GET` | `/governance/audit` | Query audit trail |
| `GET` | `/governance/compliance/{std}` | Compliance report |
| `POST` | `/governance/pause` | Pause agents |
| `GET` | `/governance/dashboard` | Governance dashboard |
| `GET` | `/governance/violations` | Compliance violations |
| `POST` | `/governance/emergency-stop` | 🚨 Emergency stop |

---

## File Structure

```
governance/
├── __init__.py              # Package exports
├── risk_types.py            # Core data models
├── risk_assessor.py         # Automatic risk scoring
├── approval_gate.py         # HITL approval workflow
├── audit_trail.py           # Tamper-evident audit logging
├── intervention_controller.py  # Stop/pause/rollback controls
├── compliance_monitor.py    # Regulatory compliance
├── governance_engine.py     # Master orchestrator
├── governance_api.py        # FastAPI router
├── GOVERNANCE.md            # This document
└── tests/
    ├── __init__.py
    └── test_governance.py   # 55+ tests
```

---

*SintraPrime-Unified Governance Framework — Built for the agentic AI era.*
*"Trust, but verify. Then audit everything."*

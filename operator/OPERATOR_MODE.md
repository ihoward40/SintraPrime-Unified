# SintraPrime Operator Mode

> Autonomous multi-step task execution for legal professionals — powered by AI.

---

## What Is Operator Mode?

**Operator Mode** transforms SintraPrime from a conversational assistant into an **autonomous agent** that can plan, execute, and verify complex multi-step tasks without constant human input.

Unlike standard chat — where you ask a question and get an answer — Operator Mode:

| Chat Mode | Operator Mode |
|-----------|--------------|
| Answers questions | Executes tasks autonomously |
| Single response | Multi-step plan → execute → verify loop |
| You drive the workflow | Operator drives, you approve checkpoints |
| Static output | Live deliverables (files, reports, CSVs) |
| No browser access | Full web browsing & form automation |

Operator Mode is inspired by:
- **[OpenAI Operator](https://openai.com/operator)** — browser control agent
- **[Manus AI](https://manus.im)** — autonomous web task execution
- **[Claude Computer Use](https://www.anthropic.com/news/computer-use)** — desktop & browser automation
- **GPT-5.5 Spud** — plan → execute → verify → iterate architecture

---

## Quick Start

```python
from operator import OperatorAgent

agent = OperatorAgent()
result = agent.execute("Research the top 10 trust attorneys in California")

print(result.summary)
print(f"Completed {result.steps_completed}/{result.steps_total} steps")
print(f"Deliverables: {result.deliverables}")
```

### Legal-Specific Quick Start

```python
from operator.legal_operator import LegalOperator

# Create a legal-specialized operator
op = LegalOperator()

# Research case law
report = op.research_case_law("revocable trust formation", "California")
print(report.to_markdown())

# Draft a legal document
doc = op.draft_document(
    "trust_document",
    parties={
        "grantor": "John Smith",
        "trustee": "John Smith",
        "successor_trustee": "Jane Smith"
    },
    terms={
        "beneficiaries": ["Alice Smith", "Bob Smith"],
        "state": "California",
        "trust_name": "The Smith Family Trust"
    }
)
print(doc.content)

# Track deadlines
op.add_deadline("MATTER-001", "Filing", "2026-06-15", "File motion for summary judgment")
deadlines = op.deadline_tracker("MATTER-001")
for d in deadlines:
    print(f"⚠️  {d.deadline_type} due {d.due_date} ({d.days_remaining} days)")
```

---

## Step-by-Step Execution Walkthrough

When you call `agent.execute("Research the top 10 trust attorneys in California")`:

### 1. 🧠 Plan Phase
```
TaskPlanner.plan(goal) → TaskPlan
├── Step 1: [search] Search the web for: top 10 trust attorneys California
├── Step 2: [browse] Browse Avvo attorney directory
├── Step 3: [browse] Browse Martindale-Hubbell attorney directory
├── Step 4: [extract] Extract attorney names, ratings, contact info
├── Step 5: [verify] Cross-reference with California State Bar records
├── Step 6: [summarize] Compile ranked list with full profiles
└── Step 7: [verify] Final quality check and report validation
Complexity: 6/10 | Estimated: 4.2 minutes
```

### 2. ⚡ Execute Phase
Each step is dispatched to the appropriate tool:
- `search` → `BrowserController.search_web()`
- `browse` → `BrowserController.navigate()`
- `extract` → `BrowserController.extract_text()` / `extract_structured_data()`
- `code` → `OperatorAgent.execute_sandboxed()`
- `summarize` → `WebResearcher.research()`
- `verify` → Validation logic

### 3. ✅ Verify Phase
After each step executes, `TaskPlanner.verify_step()` checks:
- Did the step succeed?
- Was the expected outcome achieved?
- If not → retry up to 3x with exponential back-off

### 4. 🔄 Iterate Phase
If a step fails after max retries, the operator:
1. Logs the failure with chain-of-thought reasoning
2. Continues with remaining steps (graceful degradation)
3. Includes failure details in the final report

### 5. 📄 Deliverable Phase
Final output is written to disk:
```
/tmp/sintra_deliverables/deliverable_a3f8b2c1.md
```
Containing the full research report with citations.

---

## Human-in-Loop Approval Flow

Operator Mode automatically identifies **sensitive actions** that require human approval before proceeding:

**Actions requiring approval:**
- 💳 Payments and purchases
- 🗑️ Deletions and cancellations
- 📧 Sending emails or messages
- 📤 Publishing or submitting content
- 📝 Signing documents
- 🏦 Financial transactions

### Configuring Approvals

```python
from operator import OperatorAgent, HumanInLoopCheckpoint

# Interactive (prompts in terminal)
agent = OperatorAgent()

# Auto-approve everything (for testing)
checkpoint = HumanInLoopCheckpoint(auto_approve=True)
agent = OperatorAgent(checkpoint=checkpoint)

# Custom approval logic
def my_approval_handler(step):
    print(f"Approving: {step.description}")
    return True  # or False to reject

checkpoint = HumanInLoopCheckpoint(callback=my_approval_handler)
agent = OperatorAgent(checkpoint=checkpoint)
```

### Approval Flow Diagram

```
Step flagged as sensitive
        ↓
checkpoint.request_approval(step)
        ↓
    ┌───────┐
    │ Approve│ → Execute step → Continue
    └───────┘
    │ Reject │ → Pause task → Return PAUSED status
    └───────┘
```

When paused:
```python
result = agent.execute("Pay $500 subscription fee")
# result.status == TaskStatus.PAUSED
# result.summary == "Paused: step 3 rejected by user."
```

---

## Legal-Specific Operator Skills Guide

### Case Law Research

```python
from operator.legal_operator import LegalOperator

op = LegalOperator()

# Research across multiple legal databases
report = op.research_case_law(
    query="breach of fiduciary duty trust",
    jurisdiction="California",
    depth=3  # 1-5, higher = more thorough
)

# Output
print(report.to_markdown())
# Searches: Google Scholar, Justia, CourtListener, Leagle
# Returns: Structured case citations with year, court, summary
```

### Document Drafting

```python
# Available templates
doc_types = [
    "retainer_agreement",
    "nda",
    "demand_letter",
    "settlement_agreement",
    "power_of_attorney",
    "trust_document",
]

doc = op.draft_document(
    doc_type="nda",
    parties={"disclosing_party": "Acme Corp", "receiving_party": "Beta LLC"},
    terms={"purpose": "Technology partnership", "duration_years": "3"}
)

# Save to file
doc.save("/tmp/nda_draft.md")
print(doc.warnings)  # Always shows attorney review warning
```

### Court Docket Monitoring

```python
# Monitor a case for new filings
report = op.monitor_court_docket(
    case_number="2:23-cv-01234",
    court="CourtListener"  # or PACER, CA_Superior, NYCOURTS
)

print(f"Case: {report.case_name}")
print(f"New entries: {report.new_entries_since_last_check}")
for entry in report.entries:
    print(f"  {entry.date}: {entry.event} – {entry.description}")
```

### Government Form Finder

```python
# Find and get download URL for any government form
form = op.file_finder("IRS", "W-9")
print(f"Form: {form.form_name}")
print(f"Download: {form.download_url}")

# California Courts
form = op.file_finder("ca_courts", "FL-100")
print(f"Instructions: {form.instructions_url}")
```

### Deadline Tracking

```python
# Register deadlines
op.add_deadline(
    matter_id="MATTER-001",
    deadline_type="Statute of Limitations",
    due_date="2026-08-15",
    description="Personal injury claim must be filed by this date"
)

op.add_deadline(
    matter_id="MATTER-001",
    deadline_type="Response",
    due_date="2026-05-01",
    description="Respond to motion for summary judgment"
)

# Check all deadlines for a matter
deadlines = op.deadline_tracker("MATTER-001")
for d in deadlines:
    urgency = "🔴 CRITICAL" if d.is_critical else "🟡 Upcoming"
    print(f"{urgency} {d.deadline_type}: {d.due_date} ({d.days_remaining} days)")
```

### Deep Legal Research

```python
# Comprehensive multi-jurisdiction legal research
report = op.competitive_legal_research(
    topic="trust formation requirements California",
    depth=5  # Covers: Federal, CA, NY, TX, FL
)

print(report.report_markdown)
# Includes: Key cases, regulatory landscape,
# jurisdictional comparison, emerging trends
```

---

## Comparison: Operator Mode vs. AI Competitors

| Feature | SintraPrime Operator | OpenAI Operator | Manus AI | Claude Computer Use |
|---------|---------------------|-----------------|----------|---------------------|
| **Legal specialization** | ✅ Deep | ❌ General | ❌ General | ❌ General |
| **Browser control** | ✅ Playwright | ✅ Full | ✅ Full | ✅ Full |
| **Plan → Execute loop** | ✅ 100+ steps | ✅ | ✅ | ⚠️ Limited |
| **Human-in-loop gates** | ✅ Configurable | ✅ | ⚠️ Basic | ✅ |
| **Legal document drafting** | ✅ 6 templates | ❌ | ❌ | ❌ |
| **Case law research** | ✅ Multi-DB | ❌ | ⚠️ Web only | ❌ |
| **Court docket monitoring** | ✅ | ❌ | ❌ | ❌ |
| **Deadline tracking** | ✅ | ❌ | ❌ | ❌ |
| **Government form finder** | ✅ | ❌ | ⚠️ Web only | ❌ |
| **Sandboxed code exec** | ✅ | ⚠️ | ✅ | ✅ |
| **Retry with back-off** | ✅ 3x | ✅ | ✅ | ⚠️ |
| **Multi-engine search** | ✅ DDG + Bing | ✅ | ✅ | ❌ |
| **Deliverable output** | ✅ MD/JSON/CSV | ⚠️ | ✅ | ❌ |
| **Session replay** | ✅ | ❌ | ⚠️ | ❌ |

---

## Architecture Overview

```
OperatorAgent.execute(goal)
    │
    ├── TaskPlanner.plan(goal)
    │       └── Returns: TaskPlan (ordered steps with approval flags)
    │
    ├── For each TaskStep:
    │       ├── [if requires_approval] → HumanInLoopCheckpoint.request_approval()
    │       ├── OperatorAgent._execute_step(step)
    │       │       ├── browse → BrowserController.navigate()
    │       │       ├── search → BrowserController.search_web()
    │       │       ├── extract → BrowserController.extract_text()
    │       │       ├── summarize → WebResearcher.research()
    │       │       ├── code → OperatorAgent.execute_sandboxed()
    │       │       └── verify → Validation logic
    │       └── TaskPlanner.verify_step() → retry up to 3x
    │
    └── OperatorAgent.create_deliverable() → file on disk
            └── Returns: TaskResult
```

---

## Configuration Reference

```python
from operator import OperatorAgent, BrowserController, HumanInLoopCheckpoint
from operator.task_planner import TaskPlanner

agent = OperatorAgent(
    # Custom task planner with LLM integration
    planner=TaskPlanner(llm_client=my_llm, verbose=True),

    # Custom browser (headful for debugging)
    browser=BrowserController(headless=False, polite_delay=2.0),

    # Approval gate config
    checkpoint=HumanInLoopCheckpoint(
        auto_approve=False,
        callback=lambda step: step.action_type != "payment"
    ),

    # Output directory for deliverables
    deliverable_dir="/my/output/directory",

    # Verbose chain-of-thought logging
    verbose=True,
)
```

---

## Running Tests

```bash
# From the SintraPrime-Unified directory
cd operator
pytest tests/test_operator.py -v

# Run specific test class
pytest tests/test_operator.py::TestLegalOperator -v

# With coverage
pytest tests/test_operator.py --cov=operator --cov-report=html
```

---

## ⚠️ Important Disclaimer

All legal documents generated by Operator Mode are **templates and starting points only**.
They are NOT legal advice and MUST be reviewed by a licensed attorney before use.
Laws vary significantly by jurisdiction. SintraPrime is a technology platform, not a law firm.

---

*SintraPrime Operator Mode v1.0.0 — Built for legal professionals who move fast.*

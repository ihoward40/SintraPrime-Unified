# Agent Assembly Line

## The Problem: One Giant Confused Agent

A single agent that tries to do everything — research, draft, cite, review, publish — inevitably gets confused. It mixes roles, skips verification, and produces inconsistent output.

## The Solution: Specialized Agent Lanes

Each agent has a **single responsibility**. Agents hand off work like an assembly line:

```
[Intake] → [Research] → [Drafting] → [Citation] → [QA] → [Compliance] → [Delivery]
```

---

## Agent Lanes

### 1. Intake Agent
**Role:** First contact for incoming work.
**Hand-off:** Passes classified and triaged input to Research Agent or Drafting Agent depending on complexity.
**Gate:** If input is incomplete, triggers Grill-Me skill before passing downstream.

### 2. Research Agent
**Role:** Gathers facts, case law, statutes, and background.
**Hand-off:** Passes research package to Drafting Agent.
**Gate:** Research must include source citations. No citation = no hand-off.

### 3. Drafting Agent
**Role:** Produces first drafts of documents, filings, letters, and reports.
**Hand-off:** Passes draft to Citation Agent and/or QA Agent.
**Gate:** Draft must be complete before hand-off. No placeholder text, no "TODO" markers.

### 4. Citation Agent
**Role:** Verifies every legal assertion has a supporting citation.
**Hand-off:** Passes verified draft to QA Agent.
**Gate:** Uncited assertions are flagged and returned to Drafting Agent.

### 5. Evidence Agent
**Role:** Catalogs, hashes, and maintains chain of custody for all evidence.
**Hand-off:** Evidence manifests passed to Drafting Agent and QA Agent as needed.
**Gate:** Evidence without hash verification is not admitted.

### 6. QA Agent
**Role:** Reviews for errors, formatting, consistency, and completeness.
**Hand-off:** Passes approved output to Compliance/Safety Agent.
**Gate:** Rejects output that fails any verification check. Returns to appropriate upstream agent with notes.

### 7. Compliance/Safety Agent
**Role:** Final policy check before any external action.
**Hand-off:** Approved or blocked. If approved, passes to delivery channel.
**Gate:** Blocks output that violates permissions, exposes secrets, or lacks required receipts.

### 8. Repo Agent
**Role:** Maintains repository health — separate from the document assembly line.
**Hand-off:** Reports directly to Isiah. No downstream hand-off needed.

### 9. Social Media Agent
**Role:** Content repurposing and calendar management.
**Hand-off:** Drafts passed to QA Agent, then to Isiah for approval before scheduling.

### 10. Music Release Agent
**Role:** Release planning and metadata management.
**Hand-off:** Release plans passed to Isiah for approval.

---

## Hand-Off Protocol

When an agent completes its work and passes to the next agent:

1. **Save output** to the agreed location (see registry for each agent's path)
2. **Log hand-off** in the audit trail with: source agent, target agent, work product reference, timestamp
3. **Notify** the next agent (via drop file, message, or status flag)
4. **Do not modify** after hand-off unless returned for revision

---

## Review Chain

```
Simple task: Intake → Drafting → QA → Isiah
Research task: Intake → Research → Drafting → Citation → QA → Compliance → Isiah  
Urgent fix: Intake → Drafting → Isiah (with QA post-facto)
External action: Full chain + Compliance check + Isiah approval (T3)
```

---

## Agent Registry Reference

See `agents/agent_registry.json` for the full list of registered agents, their skills, boundaries, and approval tiers.
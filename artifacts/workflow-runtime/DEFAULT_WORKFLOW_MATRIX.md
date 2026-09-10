# Phase 5A — Default Workflow Matrix

## WF-000 — proof_workflow (Phase 5A certification proof)

```
START
  ↓
Deterministic Context Collection
  ↓
Agent Plan
  ↓
Agent Implementation
  ↓
Deterministic Test
  ↓
Fresh-Context Evaluator
  ↓
Immutable Receipt
  ↓
END
```

- Nodes: collect_context (deterministic) → plan (agent) → implement (agent) → validate (deterministic) → evaluate (agent, fresh) → certify (deterministic)
- No approval node (certification workflow — Phase 5A proof scope)
- No auto-merge, no auto-deploy

## WF-001 — repository_issue_fix (declared, Phase B+ execution)

```
Context → classify → research → plan → isolated implementation →
changed-scope tests → fresh-context review → draft PR preparation
```

- Deterministic: `github.issue.fetch` (stub), `test.changed_scope` (stub), `github.pr.prepare` (stub)
- Agent roles: issue_classifier, researcher, engineer, auditor (fresh)
- `github.pr.prepare` stub returns `auto_merge: False` — no auto-merge ever
- No auto-merge, no auto-deploy (policy contract)

## Not Yet Declared (Phase B+)

- WF-002 pull_request_certification
- WF-003 adversarial_feature_build
- WF-004 principal_research
- WF-005 interactive_prd

These require the adversarial runtime (Phase F), approval node
semantics, and Mission Control integration before declaration.

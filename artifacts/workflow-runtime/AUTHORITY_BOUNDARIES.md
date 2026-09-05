# Phase 5A — Authority Boundaries

## The Principal Remains the Final Authority

Consequential actions require Principal approval. In Phase 5A, approval
nodes pause the workflow to WAITING_APPROVAL. The runtime never grants
itself authority.

## Workflow Definitions Are Configuration

A YAML workflow file declares what nodes run and in what order. It is
NOT an authority grant. The runner enforces the intersection of:

```
workflow requested permissions
∩ agent permissions
∩ tenant permissions
∩ Principal policy
```

Never the union.

## Node Authority Levels (Phase 5A)

| Node Type | Authority | Notes |
|---|---|---|
| deterministic | read/compute only | registered operations, no external side effects in Phase 5A |
| agent | scoped computation | provider session with ContextPackage, no tool escalation |
| approval | pause only | waits for Principal decision (stub in Phase 5A) |
| condition | none | deterministic branch evaluation |
| loop | none | bounded by max_iterations |

## Explicit Prohibitions (Phase 5A)

- No auto-merge.
- No auto-deploy.
- No auto-file.
- No auto-send of consequential communications.
- No agent self-grant of capabilities.
- No unlimited loops.
- No uncontrolled model spending.
- No evaluator inheriting implementation bias.
- No bypass of tenant boundaries.
- No bypass of Mission Control command guards.

## Capability Manifest (Phase 5A)

Default workflows declare only:

- `github.read`
- `repository.write_worktree`
- `tests.execute`

Anything beyond these requires a documented workflow extension and
Principal policy approval.

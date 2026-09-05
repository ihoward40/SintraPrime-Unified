# Collaborative Agent Authority

## Agents May

- observe channels and events
- analyze, classify, recommend
- draft content and artifacts
- coordinate other agents (within contracts)
- request workflows (through Mission Control authorization)
- request handoffs (if contract allows `agent.handoff.request`)

## Agents May NOT (Independently)

- approve themselves
- change authority policy
- grant capabilities
- spend money
- file legal documents
- file tax documents
- send consequential communications
- merge protected code
- deploy production
- delete protected data
- modify official records
- recruit privileged agents
- mutate canonical OmniBrain memory silently

## Enforcement

1. Structural: behavior contracts (hashed, versioned) bound every
   persistent agent; capabilities come from contracts, not prompts.
2. Runtime: event policy gates every activation; actor policy gates
   every trigger; loop guard, dedup, rate limits, budgets, kill
   switch bound execution.
3. Forensic: every activation/handoff/event emits a hash-chained
   receipt recording what ran, under which contract, on which host.

## Final Authority

The Principal remains final authority over consequential actions.
Mission Control supervises; agents compute.

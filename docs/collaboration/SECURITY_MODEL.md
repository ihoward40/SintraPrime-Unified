# Collaboration Security Model

## Trust Zones (directive §XLI)

`T0_PUBLIC` → `T1_EXTERNAL_AUTHENTICATED` → `T2_INTERNAL` →
`T3_SENSITIVE` → `T4_RESTRICTED`.

Agent capabilities must decrease as exposure grows. A T0 channel has
near-zero internal access. CF-1 defaults channels to `T2_INTERNAL`.

## Context Firewall (directive §XXXVII)

Channel messages are untrusted input (prompt injection, secret
extraction, privilege escalation, tool abuse). Agent-facing prompts
must distinguish:

```text
SYSTEM POLICY | WORKFLOW POLICY | AGENT CONTRACT |
TRUSTED MEMORY | CHANNEL CONTENT | EXTERNAL CONTENT | SECRETS
```

## Secret Management (directive §XXXVIII)

No provider/API secrets in messages, briefs, memory, artifacts,
prompts, or logs. Agents receive capability handles resolved by
runtime (`capability: gemini.image.generate`), not raw secret text.

## Capability Leases (directive §XXXIX)

Per-activation temporary leases with expiry + scope. Persistent
agents do not carry permanent broad credentials.

## Authority Surface (directive §LIX)

`A0` read-only → `A1` internal reversible → `A2` external reversible
→ `A3` consequential → `A4` irreversible.

Persistent channel agents default to A0/A1. A3/A4 require explicit
Principal approval per operation. Behavior contracts pin
authority_class; activation receipts record it.

## Security Tests (CF-1)

Cross-tenant event injection, unauthorized trigger, agent spoofing,
author spoofing, agent loop, duplicate event, budget bypass, stop
control bypass, capability escalation, secret leakage, prompt
injection in channel message, malicious handoff request, forged
approval — all fail closed.

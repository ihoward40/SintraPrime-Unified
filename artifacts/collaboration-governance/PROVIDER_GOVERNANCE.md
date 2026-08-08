# Provider Governance

## CF-1 Status

Provider routing, reputation, arena, circuit breakers, drift
detection, golden task suite, and model escalation (§50–54, §131)
are **Phase CF-5** per the directive's phase plan — the fabric
foundation already defines `provider_profile` / `model_profile` on
bindings and `approved_provider_profiles` on behavior contracts, and
the existing portal has provider routing (REUSE).

## Budget Governor (§34) — implemented here

Every agent/workflow can be hard-limited:

```text
max_tokens        max_tokens_per_hour
max_provider_cost max_calls
max_retries       max_parallelism
```

`BudgetGovernor` enforces:

```text
can_spend(tokens, calls, cost) → False at limit
record() → BLOCKED_BUDGET on refusal
snapshot() for Mission Control
```

States: `OK | PAUSED_BUDGET | BLOCKED_BUDGET`.
Proof: `test_hard_token_limit`, `test_hard_call_limit`,
`test_hard_cost_limit`.

## Outbound DLP (§111) — implemented here

`DLPScanner` inspects payloads before external transmission:

```text
secret patterns (api keys, bearer tokens, private keys, long base64)
wrong tenant
wrong matter
```

Proof: `test_secret_in_payload_detected`, `test_wrong_tenant_detected`,
`test_wrong_matter_detected`.

## Model Data Boundary (§112)

Provider eligibility by data classification is configuration for
CF-5; the classification vocabulary (TrustZone, security
compartments, LineageClass) is in place.

## Deferred to CF-5

Provider Arena, circuit breaker, drift detection, Golden Task Suite,
behavior regression suite (§54–55), model escalation ladder (§131).

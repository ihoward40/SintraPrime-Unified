# CEREBRAS-UTILIZATION-001 — Governed Utilization Track

**Status:** BASELINE / NOT ADMITTED FOR LIVE ROUTING  
**Sequence:** 2 of 3 — Gemini → Cerebras → NVIDIA Build  
**Authority boundary:** This specification does not authorize secret changes, external calls, paid usage, merge, deployment, or routing of restricted data.

## Purpose

Admit Cerebras Inference as a governed SintraPrime provider only after entitlement, pricing, privacy, quota, adapter, canary, and receipt gates are independently verified. Reuse the existing `governed_inference` contracts, router, classification, policy, ledger, reliability scoring, retry/fallback, and receipt mechanisms. Do not create a parallel routing system.

## Current verified public facts — 2026-10-04

1. Cerebras currently documents a **Free** tier with lower rate limits and community support.
2. Current official rate-limit documentation lists Free-tier limits including `gpt-oss-120b`, `llama3.1-8b`, and `qwen-3-235b-a22b-instruct-2507` at up to **1,000,000 tokens/day** and `zai-glm-4.7` with lower request ceilings. These are rate/usage ceilings; the organization dashboard remains authoritative for the user's actual limits.
3. Cerebras separately advertises a **one-time $5 signup credit** for its Free Trial / developer onboarding. Treat that promotional credit as separate from the recurring Free-tier entitlement.
4. Cerebras exposes an OpenAI-compatible API surface, making an adapter feasible without leaking provider-specific payload semantics into domain contracts.
5. No account-side Cerebras entitlement, API key, billing state, exact organization limits, data-retention setting, or privacy configuration has been verified for this SintraPrime installation.

Official-source anchors:
- https://inference-docs.cerebras.ai/support/pricing
- https://inference-docs.cerebras.ai/support/rate-limits
- https://www.cerebras.ai/inference
- https://inference-docs.cerebras.ai/quickstart

## Admission gates

### G1 — Entitlement
Required evidence before live activation:
- Cerebras organization/account identifier (non-secret)
- active tier (`Free`, `Pay as You Go`, or other)
- API key existence confirmed without storing the secret in a receipt
- model availability from the account/dashboard
- account Limits snapshot with timestamp

**Fail-closed rule:** public documentation never substitutes for account entitlement evidence.

### G2 — Pricing
Record separately:
- recurring Free-tier entitlement
- one-time promotional credit balance/expiration, if present
- pay-as-you-go pricing for any model allowed after Free-tier exhaustion
- whether automatic paid fallback is disabled

**Default:** `paid_models_allowed = false`; exhaustion of a free allowance must not silently convert into paid usage.

### G3 — Privacy / data policy
Before cloud routing is enabled, record the applicable Cerebras terms/privacy source, retention/training behavior, organization controls, verification timestamp, and reviewer.

Until verified:
- PUBLIC / synthetic data: potentially admissible after remaining gates pass
- INTERNAL: requires explicit policy admission
- CONFIDENTIAL / RESTRICTED_* / UNKNOWN: denied from Cerebras cloud

### G4 — Quota
Initial public-model baseline (not account entitlement):

| Model | Public Free-tier ceiling observed | Intended lane |
|---|---:|---|
| `gpt-oss-120b` | 1M tokens/day | reasoning, code review, agent planning |
| `llama3.1-8b` | 1M tokens/day | classification, extraction, cheap transforms |
| `qwen-3-235b-a22b-instruct-2507` | 1M tokens/day | coding/reasoning alternate |
| `zai-glm-4.7` | account/public limits materially tighter | specialist/benchmark only |

The adapter must prefer account-reported remaining quota where available and never encode a public maximum as guaranteed capacity.

### G5 — Adapter
Implement behind `InferenceProvider` using OpenAI-compatible semantics where possible.

Minimum requirements:
- credentials only from approved secret source/environment
- explicit endpoint and model allowlist
- token usage captured from provider response
- provider request ID captured when available
- 401/403 → terminal auth failure, no failover around governance
- 402/payment-required → terminal paid boundary
- 429 → rate-limited/transient and eligible for bounded fallback
- timeout and malformed-schema normalization
- no provider payload fields outside the adapter boundary

### G6 — Canary
Canary must use PUBLIC synthetic content only.

Required canaries:
1. deterministic short classification
2. structured JSON extraction
3. bounded code-analysis prompt
4. rate-limit handling fixture
5. malformed-response fixture
6. paid-boundary fixture proving free exhaustion cannot silently spend

Canary success is evidence of technical behavior only; it does not authorize production routing.

### G7 — Receipt
Every Cerebras call admitted into governed routing must produce/extend the canonical inference receipt with:
- request ID/hash
- data classification
- selected provider/model
- entitlement snapshot hash
- pricing metadata version/hash
- quota snapshot/remaining amount when available
- input/output/total tokens
- estimated and actual cost if knowable
- promotional-credit consumption kept distinct from recurring Free-tier usage
- latency
- provider request ID when available
- fallback/retry history
- final output hash
- policy receipt ID

## Routing policy

### Preferred Cerebras workloads
- high-throughput reasoning on PUBLIC/synthetic data
- code analysis and refactoring after repository/task authorization
- second-model verification
- benchmark/evaluation workloads
- agent planning where latency materially matters

### Do not use Cerebras automatically for
- restricted legal/financial/identity evidence
- unknown-classification content
- tasks whose provider privacy metadata is stale
- any request that would consume paid balance without explicit paid authorization

## Cost containment

1. Free tier before paid tier.
2. Promotional credit is a separate bucket and must carry an expiration date.
3. No implicit paid fallback after quota exhaustion.
4. Per-request output caps remain enforced by `InferencePolicy`.
5. Provider metadata TTL and pricing TTL must expire stale assumptions.
6. Repeated 429s lower reliability and trigger governed fallback rather than retries without bound.

## Implementation sequence

1. Verify Cerebras account entitlement and Limits page.
2. Verify privacy/retention terms applicable to the account.
3. Add a network-capable Cerebras adapter behind the existing provider interface.
4. Add deterministic unit fixtures before live canary.
5. Run PUBLIC synthetic canary.
6. Create certification receipt tied to exact commit SHA and CI runs.
7. Human authorization required before merge or production admission.

## Explicit non-claims

This baseline does **not** prove:
- the user's Cerebras account is active,
- the user's account receives every public Free-tier ceiling,
- any $5 credit remains available,
- Cerebras may receive confidential SintraPrime data,
- the adapter is production-ready,
- merge or deployment is authorized.

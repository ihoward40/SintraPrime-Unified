# NVIDIA-BUILD-UTILIZATION-001 — Governed Utilization Track

**Status:** BASELINE / NOT ADMITTED FOR LIVE ROUTING  
**Sequence:** 3 of 3 — Gemini → Cerebras → NVIDIA Build  
**Authority boundary:** This specification does not authorize secret changes, external calls, paid usage, merge, deployment, or routing of restricted data.

## Purpose

Admit NVIDIA Build / hosted NIM API endpoints as a governed SintraPrime provider family only after entitlement, pricing, privacy, quota, adapter, canary, and receipt gates are independently verified. Reuse the existing `governed_inference` contracts, router, policy, classification, ledger, reliability scoring, fallback, and receipt machinery.

## Current verified public facts — 2026-10-04

1. NVIDIA Build currently exposes a catalog containing multiple models marked **Free Endpoint**. The exact count varies by filter and catalog state; current official catalog pages show dozens across all modalities and roughly ten text-oriented free endpoints under text filters.
2. Current examples include `glm-5-3`, `glm-5-3-flash`, `nemotron-3.5-lightning-30b-a3b`, `deepseek-v4.1-flash`, and `muse-glimmer-30b`, with model capabilities varying across text, reasoning, multimodal, and tool use.
3. NVIDIA's hosted NIM API uses an OpenAI-style chat-completions surface at `https://integrate.api.nvidia.com`, while downloadable NIM containers are a separate deployment model.
4. Public catalog labeling of `Free Endpoint` is not sufficient evidence of the user's exact per-account quota, commercial entitlement, retention behavior, or whether a model remains free at call time.
5. NVIDIA also documents self-hosted NIM options. Self-hosting is architecturally distinct from NVIDIA-hosted Build endpoints and can offer stronger data-control options, but it requires suitable infrastructure and entitlements.

Official-source anchors:
- https://build.nvidia.com/models
- https://docs.api.nvidia.com/nim/reference/llm-apis
- https://docs.api.nvidia.com/nim/docs/api-quickstart
- https://developer.nvidia.com/nim

## Admission gates

### G1 — Entitlement
Before hosted inference activation, capture:
- NVIDIA account/org identity (non-secret)
- API key existence without persisting the secret
- accessible endpoint/model inventory
- account-specific quota/rate-limit evidence if exposed
- applicable terms/entitlement for each selected model

**Fail-closed rule:** `Free Endpoint` catalog status is discovery evidence, not an account entitlement receipt.

### G2 — Pricing
Maintain model-level pricing/entitlement metadata. Each route must distinguish:
- hosted Free Endpoint
- partner endpoint
- downloadable/self-hosted NIM
- paid/enterprise endpoint

Unknown pricing must remain unknown, never coerced to zero.

### G3 — Privacy / data policy
Hosted Build endpoints remain cloud routes. Before admission, record applicable NVIDIA terms, retention/training/logging behavior, model-provider terms where relevant, verification timestamp, and reviewer.

Default classification policy:
- PUBLIC / synthetic: eligible only after remaining gates pass
- INTERNAL: requires explicit admission
- CONFIDENTIAL / RESTRICTED_* / UNKNOWN: denied from NVIDIA-hosted endpoints until privacy and contractual controls are affirmatively certified

Self-hosted NIM is a separate future route tier decision and must not inherit hosted-endpoint approval automatically.

### G4 — Quota
Do not hard-code a global free-token allowance from catalog labels. Quota handling must be model/account specific.

Required runtime metadata when available:
- requests remaining
- tokens remaining
- reset timestamp/window
- endpoint/model availability
- catalog status (`Free Endpoint`, partner, downloadable)
- metadata verification timestamp

If quota is not machine-readable, SintraPrime should treat it as unknown and rely on bounded 429 handling plus a conservative request budget.

### G5 — Adapter
Implement hosted NVIDIA Build behind `InferenceProvider`, preferably through a reusable OpenAI-compatible HTTP adapter abstraction if one exists or is introduced without weakening provider boundaries.

Minimum behavior:
- endpoint fixed/allowlisted to NVIDIA hosted API for hosted lane
- API key only from approved secret source/environment
- model allowlist; never trust task-supplied arbitrary model identifiers
- usage capture
- provider request ID capture where available
- structured-output compatibility verified per selected model
- tool-call capability verified per selected model
- multimodal payloads admitted only for models/capabilities explicitly certified
- 401/403 terminal authentication/authorization failure
- 402/payment boundary terminal
- 429 bounded transient fallback
- 5xx/timeout normalized to provider error kinds

### G6 — Canary
Canaries use PUBLIC synthetic content only.

Minimum canary suite:
1. text chat completion
2. structured JSON extraction
3. tool-use test for one model advertised with tool support
4. multimodal test for one certified VLM, with synthetic/public image only
5. invalid-model denial
6. quota/429 handling fixture
7. paid/partner endpoint denial fixture
8. capability mismatch denial (e.g. image sent to text-only model)

### G7 — Receipt
Every NVIDIA hosted call must record:
- request ID/hash
- data classification
- selected provider/model/endpoint class
- catalog/entitlement snapshot hash
- pricing/quota metadata hashes
- capability set used for eligibility
- token usage
- estimated/actual cost when knowable
- latency
- provider request ID when available
- retry/fallback history
- final output hash
- policy receipt ID

For multimodal calls, receipt records should identify media type and content hash, not duplicate sensitive payloads.

## Initial workload map

| Workload | Candidate lane | Notes |
|---|---|---|
| fast agent/reasoning tasks | Nemotron / GLM free endpoint candidate | benchmark before preference |
| tool-use agents | GLM-family free endpoint candidate | capability must be canary-proven |
| multimodal document/image analysis | GLM Flash / DeepSeek V4.1 Flash / Muse Glimmer candidates | PUBLIC synthetic canary first |
| model diversity / second opinion | NVIDIA-hosted model unlike primary model | useful for correlated-error reduction |
| local/private inference | downloadable NIM future track | separate hardware + entitlement admission |

No listed model is permanently pinned as preferred solely because it is currently marked free.

## Cost containment

1. Hosted `Free Endpoint` routes may score above paid routes only while entitlement/pricing metadata is current.
2. If a free endpoint changes classification or returns payment-required, fail closed; do not auto-upgrade to a paid/partner endpoint.
3. Maintain model-specific TTLs because NVIDIA catalog state changes rapidly.
4. Rate-limit failures reduce reliability and trigger bounded fallback.
5. Multimodal payload sizes and max-output tokens require explicit caps.
6. Never interpret downloadable availability as zero-cost execution; infrastructure cost is separate.

## Implementation sequence

1. Verify account/API entitlement and inspect current Build catalog from the authenticated account.
2. Select a minimal allowlist of text and multimodal candidates.
3. Verify privacy/terms for hosted endpoints and selected model publishers.
4. Implement/adapt OpenAI-compatible network adapter behind `InferenceProvider`.
5. Add deterministic fixtures and negative tests.
6. Run PUBLIC synthetic canaries.
7. Generate certification receipt tied to exact SHA and CI runs.
8. Human authorization required before merge or production admission.

## Explicit non-claims

This baseline does **not** prove:
- a specific NVIDIA Free Endpoint will remain free,
- the user's account has access to every catalog model,
- any specific recurring token quota,
- NVIDIA-hosted endpoints are approved for confidential evidence,
- downloadable NIMs can run on the current SintraPrime hardware,
- merge or deployment is authorized.

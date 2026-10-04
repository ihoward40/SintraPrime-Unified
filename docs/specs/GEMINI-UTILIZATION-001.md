# GEMINI-UTILIZATION-001 — Governed Gemini Utilization Track

Status: **DESIGN BASELINE — ACCOUNT INVENTORY PENDING**

Authorization boundary: this track authorizes repository planning/configuration artifacts only. It does **not** authorize production deployment, credential creation/rotation, billing changes, paid inference, merge, or relaxation of existing data-classification gates.

## 1. Purpose

Use the Google Gemini Developer API aggressively where it creates measurable value for SintraPrime while preserving fail-closed cost, privacy, data-classification, and evidence controls.

This track extends the existing `governed_inference` control plane. It does not create a second router.

## 2. Verified repository baseline

At baseline SHA `051e2594c67a805ceacc66ea2a6fc6db9c0bc793`:

- `GeminiProvider` already exists in `governed_inference/providers.py`.
- Gemini is currently a shell adapter and is not configured for network invocation.
- The governed router already supports classification, route eligibility, cost estimates, provider priority, retry/failover, cache behavior, reliability scoring, and inference receipts.
- Default policy is local-first, denies paid models, sets paid daily/monthly budget to zero, fails closed on unknown cost/data policy, and disallows cloud-sensitive data.
- Existing contracts already record token usage, estimated/actual cost, selected provider/model, retry/fallback history, and output hash.

Therefore, Gemini admission should reuse the existing provider/router/ledger contracts rather than bypass them.

## 3. External provider baseline — verification date 2026-10-04

Official sources:

- Models: https://ai.google.dev/gemini-api/docs/models
- Pricing: https://ai.google.dev/gemini-api/docs/pricing
- Billing: https://ai.google.dev/gemini-api/docs/billing
- Data logging/sharing: https://ai.google.dev/gemini-api/docs/logs-policy
- Zero data retention: https://ai.google.dev/gemini-api/docs/zdr

Current preferred specialist model for this track: `gemini-3.8-flash`.

Google currently describes Gemini 3.8 Flash as a model for long-horizon software engineering, autonomous agents, and complex enterprise workflows. Introductory paid pricing is documented as $0.75 per 1M input tokens and $3.75 per 1M output tokens through 2026-12-31, with higher standard pricing scheduled for 2027-01-01.

Provider facts are metadata, not permanent truths. Pricing/model/privacy facts must be reverified before activation and after the configured TTL expires.

## 4. Account-side inventory gate

The repository cannot prove the user's Google account state. Before Gemini is made eligible for real network invocation, capture an account inventory receipt with:

1. Google AI Studio project identifier (non-secret identifier only).
2. Billing tier and plan (`Prepay` or `Postpay`).
3. Current positive credit/billing status where applicable.
4. Project spend cap.
5. Billing-account tier/cap.
6. Models actually available to the project.
7. API key presence and project association — **never record the secret key**.
8. Current usage/rate-limit evidence.
9. Logging/data-sharing configuration.
10. Whether any Zero Data Retention requirements are satisfied for intended sensitive workloads.
11. Verification timestamp and evidence hashes/screenshots or exported administrative records.

Until this receipt exists, set:

- `configured = false`
- `account_entitlement_known = false`
- `pricing_known = false` unless tied to fresh model metadata
- network invocation = **BLOCKED**

## 5. Workload map

### Tier G0 — do not spend Gemini

Prefer local/free low-cost routes for:

- simple classification
- deterministic tagging
- short extraction
- trivial summarization
- format conversion
- tasks already satisfied by exact cache/replay

### Tier G1 — Gemini preferred when public/non-sensitive

Prefer Gemini 3.8 Flash for:

- multi-file code review/refactoring
- repository architecture analysis
- long-context synthesis
- agent planning/tool orchestration
- structured extraction from large public documents
- public statute/regulation comparison
- synthetic benchmark generation/evaluation
- multimodal analysis of non-sensitive material

### Tier G2 — Gemini as verifier/escalation model

Use Gemini as an independent second model when:

- a claim-integrity benchmark needs adversarial review
- a primary model reaches a quality floor
- a complex coding plan needs a second-pass critique
- a long-context reconciliation is too large for cheaper routes

A second-model answer is evidence for review, not authority to act.

### Tier G3 — sensitive/confidential

Default: **BLOCKED FROM CLOUD** under existing policy.

No confidential, restricted legal, restricted financial, restricted identity, trust, client, litigation, or account evidence may be sent merely because the project is on Google's paid tier. Admission requires a separately verified data-policy decision, explicit SintraPrime policy authorization, and preservation of the existing classification gate.

## 6. Proposed routing thresholds

These thresholds are **provisional design defaults**, not activated budgets:

| Condition | Route decision |
|---|---|
| exact cache/replay available | use cache/replay |
| simple bounded task suitable for local model | local first |
| public/internal coding or agentic task with material complexity | Gemini candidate |
| input context > 12k tokens and task benefits from whole-context reasoning | Gemini candidate after a task-specific context cap is authorized |
| estimated Gemini request cost <= $0.10 | may be automatically eligible only after paid-use policy is explicitly enabled |
| estimated request cost > $0.10 | explicit paid authorization required |
| daily Gemini spend reaches $2.00 | stop automatic Gemini routing; require review |
| monthly Gemini spend reaches $25.00 | hard stop pending budget review |
| pricing unknown/stale | fail closed |
| model entitlement unknown | fail closed |
| provider metadata stale | fail closed |
| restricted/unknown data classification | keep local / deny cloud |

The $0.10 / $2 / $25 figures are conservative initial circuit-breakers for certification. They are not assertions about the user's desired budget and must be reviewed against actual AI Studio billing history before activation.

## 7. Cost model

For a verified pricing record:

`estimated_cost = input_tokens * input_price_per_token + output_tokens * output_price_per_token + tool/grounding/cache charges`

Do not assume `0` for unknown charges. Search grounding, Maps grounding, caching/storage, agent sessions, image/audio/video generation, and other billable features must be represented separately when used.

Long-running tasks may overrun a provider-side spend cap due to billing-processing delay; SintraPrime therefore needs its own local pre-dispatch and post-response counters rather than relying solely on Google's cap.

## 8. Required receipt fields

Each Gemini call must preserve the existing inference receipt and add/provider-source the following evidence when available:

- provider = `gemini`
- exact model endpoint
- task/workload tier (`G0`-`G3`)
- request ID
- policy version
- data classification
- input/output/cached/thinking token counts where exposed
- estimated cost before dispatch
- actual/reconciled cost when available
- cumulative daily/monthly Gemini spend observed locally
- provider request ID
- latency
- retry/fallback history
- output hash
- model/pricing metadata version or evidence hash
- authorization receipt when paid threshold or sensitive-data policy requires it

Secrets, raw API keys, and credentials are prohibited from receipts.

## 9. Admission gates

### GATE A — repository inventory
Status: **VERIFIED** at baseline SHA above.

### GATE B — Google account/billing inventory
Status: **PENDING**.

### GATE C — provider metadata/pricing snapshot
Status: **SAMPLED** from official documentation on 2026-10-04; must be captured into runtime-verifiable metadata before activation.

### GATE D — real Gemini adapter
Status: **BLOCKED** until B/C are satisfied and credentials are supplied through an approved secret mechanism.

### GATE E — deterministic adapter tests
Status: **PENDING**.

### GATE F — live canary against non-sensitive synthetic input
Status: **BLOCKED** pending D/E and explicit paid-use authorization.

### GATE G — production routing
Status: **BLOCKED**. Requires separate authorization, CI receipt, cost/privacy review, and merge/deploy approval.

## 10. Implementation sequence

1. Capture account-side inventory evidence from Google AI Studio.
2. Add a fresh model/pricing metadata record with TTL/review date.
3. Implement Gemini network adapter behind `InferenceProvider`; keep it disabled by default.
4. Normalize Google usage metadata into existing `InferenceResult` fields.
5. Add local daily/monthly Gemini spend accounting and hard-stop enforcement.
6. Add workload-aware admission policy without allowing task input to self-authorize provider choice.
7. Add deterministic unit tests for unknown price, stale metadata, budget exhaustion, restricted data, rate limiting, auth failure, and fallback behavior.
8. Run package-required adapter/router tests.
9. Run a synthetic, non-sensitive live canary only after explicit authorization.
10. Produce a certification receipt bound to exact SHA and CI workflow/job outcomes.

## 11. Multi-provider rollout order

The utilization framework must remain provider-independent so the next tracks can reuse it without weakening gates:

1. `GEMINI-UTILIZATION-001`
2. `CEREBRAS-UTILIZATION-001`
3. `NVIDIA-BUILD-UTILIZATION-001`

Each provider gets independent entitlement, pricing, privacy, quota, adapter, canary, and certification evidence. Success of one provider does not authorize another.

## 12. Non-authorizations

This document does not authorize:

- merge to `main`
- production deployment
- modifying Google billing or purchasing credits
- creating/rotating secrets
- external network invocation
- sending sensitive evidence to Gemini
- increasing paid budgets
- disabling local-first, classification, receipt, or approval controls

A passing CI run proves only the tested repository state. It does not itself authorize merge or production deployment.

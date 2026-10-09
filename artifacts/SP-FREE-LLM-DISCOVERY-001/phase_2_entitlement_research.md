# Phase 2 — Entitlement and Commercial-Use Research (Read-Only)

**Artifact ID:** SP-FREE-LLM-DISCOVERY-001-P2-2026-10-09-01
**Track:** SP-FREE-LLM-DISCOVERY-001
**Phase:** 2 — Entitlement and cost verification
**Date:** 2026-10-09
**Status:** COMPLETE — read-only provider-documentation research; states advanced at most to `DOCUMENTED`; zero entitlements verified; zero providers approved
**Authorization basis:** Phase 2 authorization proposal (read-only research for NVIDIA NIM, Cerebras, Cloudflare Workers AI)
**Companion:** `phase_1_certification_corrections.md` (required corrections), `phase_1_provenance.json` (updated records)

---

## 1. Scope and Boundaries

Authorized: reading provider-controlled primary documentation to establish active model availability and retirement status, free allowance/expiry/quota/reset rules, card/verification/payment prerequisites, commercial-use permissions, data retention/training/privacy terms, regional limitations, API compatibility and rate-limit documentation, and free-vs-trial-vs-production entitlement differences.

Performed boundaries (recorded separately, per correction C3):

| Boundary | Conduct |
|---|---|
| Provider documentation (public web) | Read-only fetches on 2026-10-09 (09:35–10:02 UTC) |
| Provider accounts, keys, endpoints | **No access.** No signup, no key acquisition, no authenticated request |
| SintraPrime repository | Modified via preservation commits to WIP branch `cline/33b1n070` only; no PR, merge, deployment, or CI change |
| `governed_inference/` runtime | Untouched |

Retrieval window: 2026-10-09T09:35Z–10:02Z. Every claim below is anchored to one source.

### 2.1 NVIDIA NIM (canonical: `nvidia-nim`)

| Question | Finding | Evidence | Classification |
|---|---|---|---|
| Governing terms | "NVIDIA Technology Access Terms of Use", last updated **August 20, 2026**, governs use of developer-site services unless a separate Product Agreement applies; contains binding arbitration and class-action waiver | `developer.nvidia.com/legal/terms` | `PROVIDER_TERMS` |
| Free-access nature | §7: NVIDIA "may offer free or discounted pricing programs … for trial, evaluation or academic use. NVIDIA may stop accepting new participants or discontinue a promotional offering at any time. **Standard charges will apply after a promotional offering ends** or if you exceed the promotional offering use term" | same, §7 | `PROVIDER_TERMS` |
| Rate limits | Hosted API: "**Up to 40 rpm**", "**10,000 requests per day**"; "Rate limits may vary by model and traffic from other users may cause throttling"; dedicated availability requires deploying NVIDIA NIM | `build.nvidia.com/explore/discover` (embedded `rateLimits` copy) | `PROVIDER_EMBEDDED_COPY` |
| Termination/volatility | §2: NVIDIA "may change, discontinue, or deprecate any part, or all, of the Technology … at any time **without prior notice**" | `developer.nvidia.com/legal/terms`, §2 | `PROVIDER_TERMS` |
| Anti-fee-avoidance | Prohibited use: "(n) not access or use the Technology **to avoid incurring fees or exceeding use limits or quotas**" | same, §6(n) | `PROVIDER_TERMS` |
| Data constraints | User Content warranties: submissions must **not** include confidential information, controlled or sensitive data, personal data, PHI, or PCI information; NVIDIA disclaims that the Technology is appropriate for processing personal data / PCI / PHI absent a Product Agreement | same, §6, §14 | `PROVIDER_TERMS` |
| Production readiness | Pre-release offerings "not intended, and should not be used, in production or business-critical systems" | same, §8 | `PROVIDER_TERMS` |
| Regional limits | U.S. export/embargo restrictions; registrant must not reside in an embargoed country/region | same, §10 | `PROVIDER_TERMS` |
| Commercial-use right | **No explicit commercial-use license statement found** in the TOU for the hosted API; §7 frames free access as promotional. A Product Agreement may grant it; none exists | same | `UNRESOLVED` (blocker) |
| Retention/training of API inputs/outputs | No statement found in fetched pages establishing retention or non-training guarantees for hosted-endpoint inputs/outputs | `build.nvidia.com/explore/discover`, `developer.nvidia.com/legal/terms` | `UNRESOLVED` |
| Card/phone prerequisite | Catalog claims phone verification (`README.md:134,180`); provider-controlled confirmation **not found** in fetched pages | catalog + fetched pages | `THIRD_PARTY` / `UNRESOLVED` |
| Model retirement status | Not systematically retrievable from fetched public pages; the catalog itself carries retirement-named IDs (Phase 1 F4) | — | `UNRESOLVED` |
### 2.2 Cerebras (canonical: `cerebras`)

| Question | Finding | Evidence | Classification |
|---|---|---|---|
| Permanent free tier | **None.** FAQ: "Is there a permanently free tier? **No.** The Free Trial is time- and credit-bounded: $5 in credits that expire 30 days after they're granted … Cerebras doesn't currently offer a no-cost tier that renews automatically or a per-model always-free allowance" | `inference-docs.cerebras.ai/support/rate-limits` (FAQ) | `PROVIDER_DOCS` |
| Free allowance | $5 in credits, expire **30 days** after grant, usable across all public models | same | `PROVIDER_DOCS` |
| Payment prerequisite | Credits granted **after adding a verified payment method**; without one, "Playground and API access remain inactive until you do" | same | `PROVIDER_DOCS` |
| Trial rate limits | `gpt-oss-120b`: 5 RPM / 30K uncached TPM / 90K total TPM / 1M TPH / 1M TPD; dual-bucket token model (uncached + total), continuous replenishment, organization-level limits | same ("Limits by Tier") | `PROVIDER_DOCS` |
| Post-trial state | "API and Playground access stop on the Free Trial tier until you purchase credits"; Pay-As-You-Go purchase moves the account to the Developer tier | same | `PROVIDER_DOCS` |
| Model retirement | Deprecation log: `zai-glm-4.7` deprecated **2026-08-17**; `llama3.1-8b` and `qwen-3-235b-a22b-instruct-2507` deprecated **2026-05-27**; `qwen-3-32b` and `llama-3.3-70b` deprecated **2026-02-16**; `gemma-4-31b` removed from Shared Inference **2026-09-03** | `inference-docs.cerebras.ai/support/deprecation` | `PROVIDER_DOCS` |
| Privacy/training | Site FAQ: "Your chatbot conversations are not used for AI model training purposes"; "We delete your data once it is no longer needed to provide the training/inference service" | `www.cerebras.ai/policies` | `PROVIDER_FAQ` (site-level; API-specific retention lives in the Privacy Policy / Terms of Use PDFs, not reviewed) |
| Commercial-use right | Not established; Terms of Use PDF not reviewed in this phase | `www.cerebras.ai/policies` (PDF links) | `UNRESOLVED` |
| API compatibility | OpenAI-compatible endpoints documented; not operationally tested (no endpoint calls authorized) | `inference-docs.cerebras.ai` | `PROVIDER_DOCS` |
### 2.3 Cloudflare Workers AI (canonical: `cloudflare-workers-ai`)

| Question | Finding | Evidence | Classification |
|---|---|---|---|
| Free allowance | "**10,000 Neurons per day** at no charge" on the Workers **Free** plan; limits reset **daily at 00:00 UTC**; exceeding a limit fails with an error | `developers.cloudflare.com/workers-ai/platform/pricing/` (page "Last updated Oct 1, 2026") | `PROVIDER_DOCS` |
| Overage pricing | $0.011 per 1,000 Neurons on Workers Paid, above the free allocation | same | `PROVIDER_DOCS` |
| Card prerequisite (default models) | None stated; Workers AI is included in the Free plan | same | `PROVIDER_DOCS` |
| Paid-only models | Several models **require a paid billing method** (Workers Paid or prepaid AI Gateway credits): `@cf/moonshotai/kimi-k2.6`, `@cf/moonshotai/kimi-k2.7-code`, `@cf/zai-org/glm-5.2`, `@cf/zai-org/glm-5.3`, `@cf/zai-org/glm-5.3-flash`, `@cf/deepseek-ai/deepseek-v4-flash-0731`, `@cf/deepseek-ai/deepseek-v4-pro-0813` | same | `PROVIDER_DOCS` |
| Rate limits | Text Generation **300 requests/min** default (per account, per model); paid-requirement models: **20 rpm** on standard billing / **50 rpm** with prepaid AI Gateway credits; other task types 720–3000 rpm; beta models may be lower | `developers.cloudflare.com/workers-ai/platform/limits/` ("Last updated Sep 17, 2026") | `PROVIDER_DOCS` |
| Training / data use | "Cloudflare does not use your Customer Content to (1) train any AI models made available on Workers AI or (2) improve any Cloudflare or third-party services" absent explicit consent; Customer Content is not made available to other customers; Cloudflare "neither creates nor trains" the models; models are Third-Party Services subject to their own license terms | `developers.cloudflare.com/workers-ai/platform/privacy/` ("Data usage", "Last updated Apr 21, 2026") | `PROVIDER_DOCS` |
| Governing contract | Self-Serve Subscription Agreement, "Last Updated September 12, 2025" (arbitration clause present); Workers AI data processing subject to Privacy Policy and the subscription agreement | `www.cloudflare.com/terms/` | `PROVIDER_TERMS` |
| Commercial-use right | No commercial-use prohibition found in the reviewed agreement text; the service is a commercial subscription product. **Not yet an explicit sign-off** | same | `PROVIDER_TERMS` (conditional) |
| Free-allocation capacity | `DERIVED_CALCULATION`: at published per-model neuron prices, 10,000 Neurons/day ≈ 0.31M input or ≈0.15M output tokens for `@cf/openai/gpt-oss-120b` (31,818 / 68,182 neurons per M tokens); ≈4M input / ≈0.55M output for `@cf/meta/llama-3.2-1b` | arithmetic on `pricing/` figures | `DERIVED_CALCULATION` |
| Per-model license terms | Each model may carry its own open-source or other license terms between user and model provider; per-model review not yet performed | `platform/privacy/` | `UNRESOLVED` |
| Regional availability | Per-model/region hosting not established in fetched pages | — | `UNRESOLVED` |
| Account-specific limits | Documented limits are defaults; account plans and custom arrangements can differ (custom-requirements form exists) | `platform/limits/` | `UNRESOLVED` |
| Catalog conflict | Catalog claims card requirement "**No**" and permanent-free classification; provider requires a verified payment method for any access — recorded as **F12** | catalog `README.md:149` vs rate-limits FAQ | `THIRD_PARTY` contradiction |
---

## 3. Eligibility Blockers

| Provider | Blocker | Why it blocks |
|---|---|---|
| NVIDIA NIM | No explicit commercial-use license for the hosted API; free access is framed as a promotional/trial program that can be discontinued at any time with standard charges applying afterwards | Cannot establish `ENTITLEMENT_VERIFIED` without a commercial-use right and a durable allowance; TOU §7 + §2 make the allowance inherently revocable |
| NVIDIA NIM | TOU §6 prohibits using the Technology "to avoid incurring fees or exceeding use limits or quotas" | Any routing justified primarily by fee avoidance would breach the terms; use must be defensible as within published limits |
| NVIDIA NIM | User Content warranties prohibit confidential/sensitive/personal data | Free hosted API is categorically ineligible for confidential IKE Solutions materials, consumer documents, and trust workflows |
| Cerebras | **No permanent free tier**; $5 credits expire after 30 days; a verified payment method is required for any access | Fails the "genuinely free allowance" premise; the catalog's permanent-free classification is contradicted by the provider (F12) |
| Cerebras | Commercial-use right and API-specific retention unverified (PDFs not reviewed) | Cannot reach `ENTITLEMENT_VERIFIED` |
| Cloudflare Workers AI | Per-model third-party license terms not yet reviewed | Models are third-party services; each candidate model's license must be cleared |
| Cloudflare Workers AI | Commercial-use permission is inferred, not signed off | Requires explicit legal confirmation before `ENTITLEMENT_VERIFIED` |
---

## 4. Cost and Privacy Findings

Cost:

- **Cerebras**: not a zero-cost option. It is a paid service with a 30-day, $5 trial requiring a payment method at signup. For SintraPrime's cost objective it is a billing relationship, not a free allowance. Recommend de-prioritization below Gemini/Groq shell activation and out of the free-tier track entirely.
- **NVIDIA NIM**: free-shaped (40 RPM / 10,000 RPD hosted API) but legally promotional and revocable at any time with standard charges after. Cost exposure is structural: a suspension event would move traffic to paid tiers or fail closed.
- **Cloudflare Workers AI**: the only genuinely free daily allocation of the three (10,000 Neurons/day, no card for default models). Capacity is modest — the derived calculation puts the daily free budget at roughly 0.1–0.3M output tokens for mid-size models. Useful for bounded sub-tasks (classification, extraction, summarization of small non-sensitive items), not for bulk workloads.
- None of the three changes SintraPrime's cost authority: `governed_inference` budgets, policy gates, and receipts remain controlling, and "unknown cloud cost is not zero" still holds for any unconfigured route.

Privacy:

---

## 5. Unresolved Questions

1. NVIDIA: explicit commercial-use grant for the hosted API (or a Product Agreement path); input/output retention and training guarantees; phone-verification prerequisite (only a catalog claim); per-model retirement dates; per-model rate-limit variance.
2. Cerebras: Terms of Use PDF (commercial use, liability, termination) and API-specific retention; whether any non-trial free program exists that would be relevant to SintraPrime.
3. Cloudflare: per-model license review for the specific `@cf/*` models of interest; regional/data-location guarantees; whether the free allocation can be dedicated to SintraPrime without paid-plan entanglement; custom-requirements path.
4. All: account-level verification (actual limits dashboards), which by definition requires credential acquisition and is outside this phase's authorization.

---

## 6. State Transitions Applied

| Canonical provider | Previous state | New state | Basis |
|---|---|---|---|
| `nvidia-nim` | `DISCOVERED` | `DOCUMENTED` | Primary-source terms, rate limits, and data constraints captured; commercial-use and retention unresolved |
| `cerebras` | `DISCOVERED` | `DOCUMENTED` | Primary-source allowance, prerequisites, and deprecation log captured; classification corrected to credit-bounded trial |
| `cloudflare-workers-ai` | `DISCOVERED` | `DOCUMENTED` | Primary-source pricing, limits, and data-use posture captured; per-model licenses unresolved |

All three remain `entitlement_verified: false` and unapproved. No other provider record changed. Catalog defect F12 appended to the provenance record.

---

## 7. Next Proposed Authorization

**Phase 2B — per-model license review + account-verification checklist design (still zero credentials acquired without separate authorization):**

1. Cloudflare Workers AI: review the specific `@cf/*` model licenses and the Self-Serve Subscription Agreement AI/data sections in full; draft the account-verification checklist that would be executed only if credential acquisition is later authorized.
2. NVIDIA: locate the hosted-API commercial-use position in provider-controlled docs (docs.api.nvidia.com / NGC terms); if absent, record commercial use as unavailable for the free path and route NVIDIA interest toward NIM self-hosting evaluation instead.
3. Cerebras: review the Terms of Use PDF for completeness, then park the provider as "paid service with trial" — candidate for removal from the free-tier track.
4. Only after a provider clears licensing review: propose Phase 3 canary design (non-sensitive prompts, bounded requests, itemized receipts) with an explicit, separate authorization for credential acquisition, key custody rules, and spend ceilings. No keys, no spend, no adapter work until that authorization exists.

Per the standing principle: discover widely, verify narrowly, authorize deliberately. No provider's eligibility advanced automatically by this artifact.
- **NVIDIA**: strongest reason for caution. The TOU requires submitter warranties that User Content contains no confidential or sensitive data, and NVIDIA disclaims suitability for personal data/PCI/PHI absent a Product Agreement. Confirms the global rule: free-tier models never receive confidential evidence regardless of price.
- **Cerebras**: site-level FAQ says chatbot conversations are not used for model training; API-specific retention is in unreviewed PDFs. Treat as unproven for API traffic.
- **Cloudflare**: clearest written posture — no training on Customer Content, no sharing, no service-improvement use without consent — but models are third-party services with their own licenses, so per-model review is still required.
- Operational note: caching and storage integrations change the retention picture for Cloudflare (content stored via R2/KV/DO/Vectorize is retained as those products' data). Any future canary design must avoid storage-backed paths.
| All three | Account-specific evidence (actual quotas, limits, availability) does not exist — no account was created | State cannot pass `DOCUMENTED` → `ENTITLEMENT_VERIFIED` without account-specific evidence and authorized verification |
Evidence classification used below: `PROVIDER_TERMS` (binding-looking terms), `PROVIDER_DOCS` (product documentation), `PROVIDER_FAQ` (site FAQ, not API-specific), `PROVIDER_EMBEDDED_COPY` (text served inside provider product pages), `THIRD_PARTY` (upstream catalog), `DERIVED_CALCULATION` (arithmetic on provider-published numbers), `UNRESOLVED`.
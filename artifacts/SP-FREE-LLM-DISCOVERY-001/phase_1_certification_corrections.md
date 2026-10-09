# Phase 1 Certification Corrections Receipt

**Artifact ID:** SP-FREE-LLM-DISCOVERY-001-P1-CORR-2026-10-09-01
**Track:** SP-FREE-LLM-DISCOVERY-001
**Date:** 2026-10-09
**Responds to:** Phase 1 certification review — "Accepted with corrections" (remote HEAD `41d4527f7f9a35d86a1eb3dbc6d5cf6a82ad0502`)
**Status:** All four required corrections applied; Phase 2 (read-only entitlement research) executed under its authorization in a separate artifact

---

## C1 — Provenance coverage reclassified as partial

The Phase 1 audit overstated hash coverage. Corrected to **partial**:

- 9 of 15 tracked files carry SHA-256 digests: `README.md`, `LICENSE`, `CONTRIBUTING.md`, all three `code-examples/` files, `PULL_REQUEST_TEMPLATE.md`, `FUNDING.yml`, `ISSUE_TEMPLATE/submit_api.yml`.
- 6 tracked files are declared `unhashed_paths`: four localized READMEs, `provider-logos-marquee.svg`, `ISSUE_TEMPLATE/config.yml`. These were inventoried but never content-verified, and future syncs of these files are not detectable from this record.
- `phase_1_catalog_audit.md` §3 wording corrected accordingly. `phase_1_provenance.json` now carries an explicit `hash_coverage` object with `status: partial`, hashed/unhashed counts, and a sync-detection limitation note.

## C2 — Canonical provider identity mapping prepared

Raw catalog rows stay preserved as evidence, but identity normalization is now defined so duplicate rows cannot become separate entitlement accounts. `phase_1_provenance.json` gains `canonical_provider_identity_map`; the rule is: **entitlement accounts are keyed by `canonical_provider_id`, never by catalog row.**

Normalization decisions applied at this stage:

| Canonical provider ID | Catalog rows merged | Rationale |
|---|---|---|
| `xai` | `xAI`, `Grok (xAI)` | Same vendor, same base URL `https://api.x.ai/v1` (Phase 1 finding F2) |
| `nvidia-nim` | `NVIDIA NIM` | Vendor = NVIDIA Corporation |
| `cerebras` | `Cerebras` | Vendor = Cerebras Systems |
| `cloudflare-workers-ai` | `Cloudflare Workers AI` | Vendor = Cloudflare, Inc. |
| `google-gemini` | `Google Gemini` | Vendor = Google |
| `deepseek` | `DeepSeek` | Vendor = DeepSeek |
| `ollama-cloud` | `Ollama Cloud` | Hosted service; distinct from local/self-hosted Ollama, which is not a catalog provider row |
| `zhipu-z-ai` | `Z AI (Zhipu AI)` | One vendor, two trade names |

All remaining catalog rows map 1:1 and are listed in the JSON. Local/self-hosted tools (Ollama local, LM Studio, llama.cpp, GPT4All, Jan.ai, KoboldCpp) are **not** catalog providers and are excluded from the map.

## C3 — Read-only boundary stated per target, not globally

Phase 1 and Phase 2 receipts now record three separate boundaries instead of one blanket "read-only" claim:

1. **Upstream catalog access** — read-only public fetches; no writes, no forks, no issues.
2. **SintraPrime repository** — modified, committed, and pushed to the designated work-in-progress branch `cline/33b1n070` as preservation only. No PRs, no merges to `main`, no deployments, no CI-affecting changes. This is a repository mutation and is now labeled as such in every receipt.
3. **Provider accounts and endpoints** — no access of any kind in Phase 1; none in Phase 2 either (no signups, no keys, no authenticated requests).

Recorded in this track's `AGENTS.md` (Local Contracts), in `phase_1_provenance.json` (`authorization.boundaries`), and in the Phase 2 artifact.

## C4 — Shell versus integration distinction recorded

`governed_inference/` authority boundary is preserved and untouched — no adapter, router, policy, or contract code was modified. The Phase 2 artifact and provenance records now distinguish:

- **Shell declared** — a provider class exists in SintraPrime code with `configured=False` (e.g. `GeminiProvider`). This establishes a code surface only.
- **Verified integration** — requires account entitlement, known pricing/account policy, and declared data policy. **Zero providers meet this bar.**

An existing shell establishes nothing about entitlement or production readiness, and no shell was upgraded by this work.

---

## New catalog defect found during Phase 2 (F12)

| # | Finding | Evidence | Impact |
|---|---|---|---|
| F12 | The catalog lists Cerebras under Permanent Free Tiers with credit-card requirement "**No**", while Cerebras' own rate-limit documentation states the Free Trial requires a **verified payment method** at signup (access stays inactive without it) and that credits expire after 30 days | `inference-docs.cerebras.ai/support/rate-limits` (retrieved 2026-10-09); catalog `README.md:149` | Confirms the Phase 1 classification-risk thesis with a provider-controlled contradiction; Cerebras is credit-bounded, not permanently free |

Appended to `catalog_defects` in `phase_1_provenance.json`.

---

## Document status

- Corrections: complete.
- Phase 1 conclusions: unchanged in substance; two wording corrections applied (§2 boundary, §3 coverage).
- Phase 2 evidence matrix: see `phase_2_entitlement_research.md`.
- No provider state advanced beyond `DOCUMENTED`; no provider approved; no entitlement verified.
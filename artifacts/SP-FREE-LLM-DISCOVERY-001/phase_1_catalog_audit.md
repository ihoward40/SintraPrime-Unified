# Phase 1 — Free LLM Catalog Audit (Read-Only)

**Artifact ID:** SP-FREE-LLM-DISCOVERY-001-P1-2026-10-09-01
**Track:** SP-FREE-LLM-DISCOVERY-001
**Phase:** 1 — Catalog audit
**Date:** 2026-10-09
**Status:** COMPLETE — read-only; no provider registered, no credential used, no spend initiated
**Subject:** `open-free-llm-api/awesome-freellm-apis` at commit `63a2633ae22201c551e350c46af041ddee5ab5ed`
**Companion evidence:** `phase_1_provenance.json` (commit pin, retrieval timestamp, file hashes, derived counts)

---

## 1. Executive Summary

The catalog is a small, single-purpose Markdown index — 15 tracked files, no dataset, no schema, no code — rendered from the operator's website `freellm.net` by an automated GitHub Actions sync. It is useful as a **lead source** and unusable as a **cost or security authority**.

Four conclusions drive the Phase 2+ plan:

1. **The headline numbers are self-published and internally inconsistent.** The `505+` figure is exactly the sum of the "Free Models" column in the catalog's own two directory tables (474 + 31). The same README, 345 lines later, cites a *different* figure — 453 models — for the same dataset, and the shipped config examples claim `35+` OpenRouter models and `128+` total free models. Nothing in the repository reconciles these.
2. **No entitlement is verifiable from this repository.** There is no machine-readable dataset, no provider record, no rate-limit source of truth, and no per-model metadata beyond rendered prose. The full dataset lives off-repo at `freellm.net`, which cannot be pinned by commit.
3. **Defects exist in the published rows themselves**, at the exact places where classification matters: a credit-based provider sits in the "Permanent Free Tiers" table, a model whose ID declares retirement is published as a *recommended* best model, and one provider row has a zero context window and no base URL or key link.
4. **The catalog is an intake surface with an untrusted-input shape.** Its shipped examples instruct the reader to export API keys into shell profiles. That material must never be copied into this repository, and no catalog row may ever flip a router gate.

Recommendation carried forward unchanged: keep this as a **monitored intelligence source**, not software to install, and require per-provider Phase 2 verification before any provider leaves `DISCOVERED`.

---

## 2. Scope and Authorization Boundary

In scope for Phase 1: read-only inventory of the catalog's contents, licensing, source data, update mechanism, data-quality defects, and overlap with existing SintraPrime inference surfaces.

Out of scope and not performed: provider signup, API key acquisition or use, provider endpoint calls, model registration, router or policy modification, spend of any kind. No credential was read, written, or transmitted.

Boundaries, stated separately (per certification correction C3):

- **Upstream catalog access** was read-only: public fetches only, no writes, forks, or issues.
- **SintraPrime repository** was modified: the Phase 1 artifacts were committed and pushed to the designated work-in-progress branch `cline/33b1n070` for preservation. No PR, merge to `main`, deployment, or CI change was made. Repository mutation and upstream read-only access are distinct facts and are recorded separately in every receipt from this track forward.
- **Provider accounts and endpoints**: no access of any kind.


---

## 3. Evidence Base and Method

All evidence came from public GitHub reads through the authenticated `gh` CLI and `raw.githubusercontent.com` at the pinned commit.

| Item | Value |
|---|---|
| Canonical repository | `open-free-llm-api/awesome-freellm-apis` |
| Pinned commit | `63a2633ae22201c551e350c46af041ddee5ab5ed` |
| Commit date (UTC) | 2026-10-09T03:03:56Z |
| Commit author | `github-actions[bot]` |
| Commit message | `chore: sync README from freellm.net data [skip ci]` |
| Commit signature verified | `false` |
| Retrieved (UTC) | 2026-10-09T09:17Z |
| License (GitHub API) | MIT |
| Stars / default branch | 3,941 / `main` |
| Tracked files (blobs) | 15 |

Tracked file inventory at the pin:

| Path | Bytes |
|---|---|
| `README.md` | 36,979 |
| `README.zh-CN.md`, `README.zh-TW.md` | 35,163 each |
| `README.ja.md` | 36,455 |
| `README.ko.md` | 35,898 |
| `LICENSE` | 1,074 |
| `CONTRIBUTING.md` | 1,718 |
| `code-examples/claude-code.md` | 2,627 |
| `code-examples/codex.md` | 2,367 |
| `code-examples/cursor.md` | 2,399 |
| `assets/provider-logos-marquee.svg` | 52,512 |
| `.github/FUNDING.yml` | 39 |
| `.github/PULL_REQUEST_TEMPLATE.md` | 641 |
| `.github/ISSUE_TEMPLATE/submit_api.yml` | 2,165 |
| `.github/ISSUE_TEMPLATE/config.yml` | 245 |

SHA-256 digests were captured for **9 of 15 tracked files (partial coverage)** — the primary README, license, contributing guide, all three code-examples, PR template, funding file, and submission template — and are recorded in `phase_1_provenance.json`. The remaining 6 tracked files (four localized READMEs, the logo SVG, and the issue-config) are listed under `unhashed_paths`: they were inventoried by size only, never content-verified, and a future upstream sync touching only those files would **not** be detectable from this record.

**Not present:** JSON/CSV/YAML dataset, JSON schema, per-model machine-readable records, rate-limit source data, provider terms-of-service snapshots, tests, or CI validation of the rendered tables.

---

## 4. Provenance and Trust Chain

The trust anchor is not this repository. It is `freellm.net`, a commercial site whose operator is the funding recipient declared in `.github/FUNDING.yml` (`mailto:support@freellm.net`).

| Layer | Observation | Consequence |
|---|---|---|
| Generation | README sections are wrapped in `<!-- AUTO_STATS -->`, `<!-- AUTO_UPDATE_BADGE -->`, `<!-- BEGIN_PERMANENT_FREE -->`, `<!-- BEGIN_RENEWABLE -->`, `<!-- BEGIN_QUICK_REF -->`, `<!-- BEGIN_BEST_MODELS -->`, `<!-- BEGIN_TOP_MODELS -->` markers | Table content is machine-generated, not editorially reviewed per row |
| Sync | Latest commit is bot-authored with `[skip ci]`, signature unverified | No CI check, no human gate, no review trail between site data and published row |
| Dataset | Repo states it is a "structured, machine-readable directory"; the actual dataset is only at `freellm.net` | The machine-readable claim is unsupported inside the repository; the data cannot be commit-pinned or diffed |
| Currency claim | "Data refreshed daily" | Freshness of the sync is not evidence of provider-side accuracy |
| Intake | `CONTRIBUTING.md` and `submit_api.yml` accept community submissions with a "genuine free tier" self-attestation | Rows can be added from self-reported claims |
| License | MIT, `Copyright (c) 2026 open-free-llm-api` | Reuse of text requires attribution; MIT covers the compilation, not the accuracy of third-party provider claims |
| Naming | Repository slug is `awesome-freellm-apis`; README title, structure block, and the Contributing issue link use `awesome-free-llm-apis` | Stale reference; GitHub currently redirects the old slug, so the link resolves today but is not a stable citation |

Authorization for Phase 2 (entitlement and cost verification) is **not** granted by this artifact. This artifact recommends it.

---

## 5. Catalog Structure (as published)

| Section | Lines | Content | Rows |
|---|---|---|---|
| Why This Exists / How to Use | 30–53 | Positioning and three-step onboarding | — |
| Quick Start | 55–123 | Python, Codex, Cursor, Claude Code snippets; tool list | — |
| Provider Directory — Permanent Free Tiers | 127–163 | Provider, free model count, credit-card requirement, max context, modalities, key link | 29 |
| Provider Directory — Renewable Credits | 165–173 | Same columns plus credit model | 1 (OpenRouter) |
| Quick Reference — Base URLs & API Keys | 175–210 | Provider, base URL, key link, card requirement | 30 |
| Best Free Models by Provider | 212–299 | Provider, model, model ID, context, rate limit | 83 model rows / 30 provider groups |
| Local / Self-Hosted | 303–312 | Ollama, LM Studio, llama.cpp, GPT4All, Jan.ai, KoboldCpp | 6 |
| Top Free Models (by weekly usage) | 316–333 | Usage-ranked models, sourced from freellm.net monitoring | 10 |

Cross-table reconciliation result: every provider group in "Best Free Models by Provider" appears in the Provider Directory and vice versa — the three tables agree on the provider *set*, but not on the *counts* (§6).

---

## 6. Published Counts vs Derived Counts

| Claim | Source (line) | Derived value | Verdict |
|---|---|---|---|
| "505+ free LLM APIs" | `README.md:4` | Sum of the "Free Models" column: 474 (permanent) + 31 (OpenRouter) = **505** | Exactly the sum of catalog listings, i.e. listings ≠ distinct APIs; "505+" is a rounded sum of a self-reported column |
| "30 providers" | `README.md:4` | 29 permanent rows + 1 renewable row = 30 rows, but `xAI` (3 models) and `Grok (xAI)` (2 models) are the same vendor with the same base URL `https://api.x.ai/v1` → **29 distinct providers** | Row count includes a duplicate vendor entity |
| "full structured dataset with 453 models" | `README.md:349` | Not derivable from the repo (dataset is off-repo) | Contradicts the 505 headline for the same dataset |
| "35+ free models" (OpenRouter) | `code-examples/claude-code.md:29`, `codex.md:29`, `cursor.md:37` | Directory row states **31** | Inconsistent within one commit |
| "all 128+ free models" | `code-examples/claude-code.md:72` | Headline states 505+ | Inconsistent within one commit |

Reading: the catalog's own arithmetic is reproducible, but its *definitions* are not stable. A count of "free models" here means "rows the operator chose to publish", not "models with verified zero-cost access".

---

## 7. Data-Quality Findings

Each finding is reproducible from the pinned commit. These are recorded, not normalized, per this track's contracts.

| # | Finding | Evidence (line) | Impact on SintraPrime |
|---|---|---|---|
| F1 | A credit-based offering is published inside **Permanent Free Tiers**: the `Grok (xAI)` row's rate-limit column reads "$25/month free credits" | `README.md:158`, `290-291` | Misclassification; a credits model is not a permanent free tier and can lapse |
| F2 | Duplicate vendor entity: `xAI` (3 models) and `Grok (xAI)` (2 models) are separate rows with the same base URL | `README.md:155`, `158`, `202`, `205` | Inflates the provider count; entitlement must be tracked per account, not per row |
| F3 | `DeepSeek` is listed as a permanent free tier with 2 models while its rate limit is "Dynamic" and its Quick Reference requirement is "Registration" | `README.md:160`, `207`, `294-295` | Access depends on account/promotional state, not a published permanent allowance |
| F4 | Retirement/decommission state is carried in the **model ID** and the row is still published as a recommended best model: `glm-4-5-flash-retirement-announced`, `zai-glm-4-7-deprecated-aug-2026` | `README.md:263`, `266` | A naive import would register retiring models as usable |
| F5 | Malformed provider row: `Cline` has free-model count 4, **max context `0`**, an empty API-key link, and an empty base URL in Quick Reference | `README.md:153`, `200` | Unusable row; any parser must tolerate and quarantine empty/zero fields |
| F6 | `OpenAI-compatible` is asserted for all providers, but Cloudflare Workers AI is published with a non-`/v1` base URL in the directory and a `/v1` variant in the examples | `README.md:59`, `182`, `code-examples/cursor.md` | Base-URL compatibility is not operational compatibility |
| F7 | Claude Code guidance contradicts itself and the "free" premise: README uses `https://openrouter.ai/api` with a "$10 top-up" note, examples use `https://openrouter.ai/api/v1` | `README.md:96-103`, `code-examples/claude-code.md:29-35` | Free-tier claims in this repo can carry a paid prerequisite |
| F8 | Deprecated-model entries retain plausible-looking rate limits (`5 RPM, 30K TPM, 1M TPD`) | `README.md:266` | Rate limits on a retired model are stale by construction; entitlements must carry retirement status |
| F9 | Shipped examples instruct persistent shell-profile exports of API keys (`~/.zshrc` / `~/.bashrc`) | `code-examples/claude-code.md:47-55`, `codex.md:41-47` | Conflicts with this track's no-credential-import rule; credential-leak risk if copied |
| F10 | No schema or machine-readable records; table parsing is the only ingestion path | §3 inventory | Ingestion requires a parser with an explicit quarantine path for F5-class rows |
| F11 | Stale repository slug in README title, structure block, and Contributing link | `README.md:2`, `341`, `357` | Citations must use the canonical slug plus commit pin |


---

## 8. Overlap With Existing SintraPrime Inference Surfaces

The catalog is **not** a new integration target. SintraPrime already declares provider surfaces for several catalog entries; the gap is verified entitlement and configuration, not code.

| Catalog provider | Catalog free models | Existing SintraPrime surface | State today |
|---|---|---|---|
| Google Gemini | 19 | `governed_inference/providers.py::GeminiProvider` (shell, `configured=False`) | Unconfigured shell |
| Groq | 12 | `governed_inference/providers.py::GroqProvider` (shell) | Unconfigured shell |
| Mistral AI | 15 | `governed_inference/providers.py::MistralProvider` (shell) | Unconfigured shell |
| OpenRouter | 31 | `governed_inference/providers.py::OpenRouterProvider` (free-gateway shell) | Ineligible until pricing/account policy is known |
| Ollama (local and Ollama Cloud) | 17 (cloud) | `governed_inference/adapters.py::OllamaProvider`, `local_models/ollama_client.py`, `local_llm/ollama_adapter.py` | Real local adapter |
| DeepSeek | 2 | `governed_inference/adapters.py::DeepSeekProvider`, `local_models/deepseek_client.py` | Real adapter (paid-tier semantics) |
| LM Studio (local) | — | `governed_inference/providers.py::LMStudioProvider` | Local, free-allowance-known |
| OmniRoute (free gateway) | — | `governed_inference/providers.py::OmniRouteProvider` | Free-gateway shell, gated |
| OpenAI / Anthropic | — | `governed_inference/adapters.py` real adapters | Paid, policy-gated |
| **NVIDIA NIM** | **132 (largest catalog entry)** | none | Gap |
| **Cerebras** | 6 | none | Gap |
| **Cloudflare Workers AI** | 40 | none | Gap |
| Cohere, Hugging Face, SambaNova, AI21 Labs, Nebius, Nscale, Chutes.ai, Glhf.chat, xAI/Grok, SiliconFlow, ModelScope, OpenCode Zen, LLM7.io, Kilo Code, OVHcloud, Aion Labs, Z AI, Agnes AI, Alibaba Cloud Model Studio, Cline | — | none | Not evaluated |

Three governance constraints already exist in code and constrain this track:

- `governed_inference/AGENTS.md`: free-gateway providers "must stay ineligible until configured with known pricing/account policy"; "Unknown cloud cost is not zero".
- `governed_inference/contracts.py`: `ProviderMetadata` already carries `account_entitlement_known` and `free_allowance_known` — the exact fields a verified registry must populate, and the exact fields a catalog row must never populate by itself.
- `docs/orchestration/PROVIDER_CONTRACT.md`: external providers remain blocked in the current milestone; provider declarations must include data policy and allowed sensitivity.

Therefore the three "gap" providers (NVIDIA NIM, Cerebras, Cloudflare Workers AI) are the only candidates that could *add* capability, and each must arrive with verified entitlement plus a declared data policy before any adapter work.

---

## 9. Security, Privacy, and Governance Implications

- **Confidential-evidence rule (controlling).** For IKE Solutions legal-education materials, consumer documents, and trust-related workflows, no free-tier model may receive confidential evidence because it is cheaper. Provider retention terms, jurisdictional applicability, source verification, and SintraPrime approval boundaries control. Free-tier output may assist drafting and research and cannot certify legal conclusions.
- **Untrusted intake.** The catalog is third-party, machine-generated, self-attested content. Parse defensively, quarantine malformed rows (F5), and never let a row mutate routing state.
- **No credential material.** Upstream `.env` examples, key formats, and shell-profile export instructions (F9) must not be copied into this repository or into any operational environment from this source.
- **No silent paid substitution.** A suspended free tier must fail closed. It may not be replaced by a paid route without separate approval, even where an equivalent model is already configured.
- **Attribution and license.** The catalog is MIT-licensed; quoted text requires the source URL and commit pin. Bulk import of the tables would also import the accuracy defects in §6–§7.
- **Cost authority.** SintraPrime's cost authority remains `governed_inference` policy, budgets, and receipts — not this catalog.


---

## 10. Conclusions

Established by Phase 1:

- The catalog is a 15-file, MIT-licensed, bot-synced Markdown index sourced from `freellm.net`, with no in-repo dataset and no validation.
- Its published counts are internally inconsistent and reproducible only as sums of self-reported listings.
- At least eleven concrete data-quality defects exist at the pin, including classification errors, a retirement-announced model published as recommended, and a malformed provider row.
- SintraPrime already owns provider surfaces for most catalog entries; the genuine gaps are NVIDIA NIM, Cerebras, and Cloudflare Workers AI.
- No provider entitlement, commercial-use right, retention term, or quota has been verified by this phase.

Not established (explicitly deferred to Phase 2): actual free quota per account, commercial-use rights, data retention and training terms, jurisdictional constraints, real rate limits, model retirement dates, and operational compatibility (tools, streaming, structured output, retry semantics).

**No provider is approved. All candidates remain `DISCOVERED`.** The per-provider state record is in `phase_1_provenance.json`.

---

## 11. Recommended Next Steps

Phase 2 (entitlement and cost verification), one provider at a time, in this order: NVIDIA NIM, Cerebras, Cloudflare Workers AI (capability gaps), then Google Gemini, Groq, Mistral AI (already-present shells needing entitlement), then OpenRouter last (free-gateway, card/top-up prerequisite, historically most volatile).

Per provider, Phase 2 must produce, from provider-controlled primary sources: current free allowance and its terms; commercial-use permission; training/retention and data-use terms; regional availability and jurisdictional constraints; real rate limits; model retirement dates; and a named approver. Records move to `DOCUMENTED` on evidence capture and to `ENTITLEMENT_VERIFIED` only on primary-source confirmation. `CANARY_PASSED` requires Phase 4 canaries with non-sensitive prompts and itemized cost receipts.

Phase 3 (routing design) remains disabled-by-default and must not duplicate `governed_inference` routing.

Monitoring: because the upstream README changes daily by automation, watch the pinned hashes rather than the counts, and alert only on a *verified* change that would improve cost or capability — never on a catalog edit alone.

---

## 12. Reproduction

```bash
# Pin and commit metadata
gh api repos/open-free-llm-api/awesome-freellm-apis/commits/63a2633 \
  --jq '{sha:.sha,date:.commit.committer.date,author:.commit.author.name,msg:.commit.message}'

# Tracked file inventory
gh api 'repos/open-free-llm-api/awesome-freellm-apis/git/trees/main?recursive=1' \
  --jq '.tree[] | "\(.type)\t\(.size)\t\(.path)"'

# Retrieve and hash the audited files
curl -sSL https://raw.githubusercontent.com/open-free-llm-api/awesome-freellm-apis/63a2633/README.md | sha256sum

# Re-derive the 505 count (sum of the "Free Models" column in both directory tables)
python3 - <<'EOF'
lines = open('README.md').read().splitlines()
rows = [l for l in lines[133:162] if l.startswith('|')]      # Permanent Free Tiers
total = sum(int([c.strip() for c in r.split('|')][2]) for r in rows)
print('permanent', len(rows), 'rows', total, 'models')
print('with OpenRouter 31 ->', total + 31)                   # 505
EOF
```

Expected: 29 rows / 474 models / 505 with OpenRouter, matching §6.

---

## 13. Change Log

| Date | Change |
|---|---|
| 2026-10-09 | Phase 1 catalog audit created; provider records seeded at `DISCOVERED`; no provider approved |
| 2026-10-09 | Certification corrections applied: §2 boundary now states upstream read-only access, WIP-branch repository mutations, and zero provider access separately; §3 hash coverage reclassified as partial (9 of 15). Provider states have since advanced to `DOCUMENTED` for `nvidia-nim`, `cerebras`, and `cloudflare-workers-ai` via Phase 2 — see `phase_1_certification_corrections.md` and `phase_2_entitlement_research.md` |


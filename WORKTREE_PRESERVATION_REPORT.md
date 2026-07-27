# Worktree Preservation Report

**Repository:** `C:\Users\admin\Desktop\Projects\SintraPrime-Unified`
**Report generated:** 2026-07-27
**Preservation branch:** `p0/preserve-untracked-2026-07-26-221432`
**Preservation HEAD commit:** `6415e47bbb2537eccf9b95a00a7bf47c01d3f62f`

---

## Purpose

Capture a safety checkpoint of all untracked working-tree items before implementation begins. No untracked item has been deleted. All five items have been classified and preserved in the branch above.

---

## Preservation Evidence

```text
$ git checkout -b p0/preserve-untracked-2026-07-26-221432
Switched to a new branch 'p0/preserve-untracked-2026-07-26-221432'

$ git commit -m "p0(preserve): checkpoint untracked worktree items before implementation"
[p0/preserve-untracked-2026-07-26-221432 6415e47b] ...
 109 files changed, 11104 insertions(+)
```

Current working branch returned to `main` after checkpoint.

---

## Untracked Item Classification

### 1. `governed_inference/`

| Attribute | Value |
|---|---|
| Classification | **ACTIVE WORK** |
| Files | `AGENTS.md`, `__init__.py`, `cache.py`, `classification.py`, `contracts.py`, `decomposition.py`, `escalation.py`, `ledger.py`, `policy.py`, `providers.py`, `router.py` |
| Purpose | Governed LLM inference layer: provider abstraction, retry/backoff, caching, policy enforcement, classification, decomposition, escalation, ledger, routing |
| Dependencies in code | `pydantic`, `httpx`, `tenacity` (likely), `portal` patterns |
| Contains tests | Yes — `tests/test_governed_inference.py` |
| Unique unrecoverable work | **Yes** — this is a new module not present in any tracked branch |
| Recommended disposition | **Preserve / Integrate** |
| Notes | Must be evaluated against the Version 1 LLM reliability layer and Version 2 LLM Gateway architecture. Do not delete. |

### 2. `revenue-team/`

| Attribute | Value |
|---|---|
| Classification | **ACTIVE WORK** |
| Files | ~90 markdown documents across `agents/`, `inputs/`, `launch/`, `outputs/`, `templates/` |
| Purpose | Revenue-team operating system: market signals, offer architecture, content campaigns, conversion systems, launch runbooks, governance docs |
| Dependencies | None on runtime code (documentation / planning artifacts) |
| Unique unrecoverable work | **Yes** — large body of strategy and launch artifacts not tracked elsewhere |
| Recommended disposition | **Preserve / Archive** |
| Notes | This is planning/product content, not engineering code. Preserve on branch; decide later whether to move to `docs/` or a separate knowledge base. Do not delete. |

### 3. `tests/test_governed_inference.py`

| Attribute | Value |
|---|---|
| Classification | **ACTIVE WORK** |
| Purpose | Tests for the `governed_inference/` module |
| Dependencies | `governed_inference/`, pytest, portal test fixtures |
| Unique unrecoverable work | **Yes** — tests for untracked module |
| Recommended disposition | **Preserve / Integrate** |
| Notes | Must be kept with `governed_inference/`. Evaluate whether it belongs in `tests/` root or `governed_inference/tests/`. |

### 4. `portal/routers/wrapper.py`

| Attribute | Value |
|---|---|
| Classification | **PARTIAL IMPLEMENTATION / STUB** |
| Size | 36 bytes, 1 line |
| Content | `from .webhooks.stripe import router` |
| Purpose | Appears intended to re-export the Stripe webhook router as a convenience wrapper |
| Dependencies | `portal.routers.webhooks.stripe` |
| Unique unrecoverable work | **No** — content is trivial and reconstructible |
| Recommended disposition | **Preserve on branch / Likely Delete** |
| Notes | Does not follow portal router contract (no FastAPI routes declared). `portal/main.py` already imports `portal.routers.webhooks.stripe` directly. No tracked code references `portal.routers.wrapper`. This file is likely an accidental leftover or incomplete stub. Deletion can be recommended after confirming zero references. |

### 5. `portal/main.py.bak`

| Attribute | Value |
|---|---|
| Classification | **BACKUP (older revision)** |
| Size | 162 lines vs. tracked `portal/main.py` 164 lines |
| Byte-identical to tracked `portal/main.py` | **No** |
| Relationship | Older backup created before Stripe webhook router was wired into `main.py` |
| Diff summary | Missing `from portal.routers.webhooks import stripe as stripe_webhook` and the `app.include_router(stripe_webhook.router, ...)` line |
| Unique unrecoverable work | **No** — equivalent state can be recovered from git history |
| Recommended disposition | **Preserve on branch / Recommend Delete** |
| Notes | Confirmed backup artifact. It contains no unique code. However, per preservation-first rules, deletion is recommended but **not executed** until explicit approval is granted. |

---

## Summary of Recommended Dispositions

| Item | Preserve | Commit | Integrate | Archive | Delete (recommend) |
|---|---|---|---|---|---|
| `governed_inference/` | ✓ | ✓ | ✓ |  |  |
| `revenue-team/` | ✓ |  |  | ✓ |  |
| `tests/test_governed_inference.py` | ✓ | ✓ | ✓ |  |  |
| `portal/routers/wrapper.py` | ✓ (branch) |  |  |  | ✓ |
| `portal/main.py.bak` | ✓ (branch) |  |  |  | ✓ |

---

## Next-Step Authorization Required

Before P0.1 worktree stabilization continues, the following decisions need explicit approval:

1. **Integrate `governed_inference/` and its test into the main implementation?**
   - Recommendation: Yes, after aligning with portal architecture and AGENTS.md rules.

2. **Archive `revenue-team/` as planning artifacts, or leave it on the preservation branch only?**
   - Recommendation: Leave on preservation branch; do not merge to `main` unless the user wants product docs in repo.

3. **Delete `portal/routers/wrapper.py`?**
   - Recommendation: Yes — it is a stub with no references and does not satisfy the portal router contract.

4. **Delete `portal/main.py.bak`?**
   - Recommendation: Yes — it is an older backup with no unique content; full history is recoverable from git.

No deletions will occur without explicit approval.

---

## Mechanical Evidence Captured

- `git checkout -b p0/preserve-untracked-2026-07-26-221432`
- `git commit ... 109 files changed, 11104 insertions(+)`
- `git rev-parse HEAD` → `6415e47bbb2537eccf9b95a00a7bf47c01d3f62f`
- `diff -u portal/main.py portal/main.py.bak` showed older backup (missing webhook router)
- `cmp -s portal/main.py portal/main.py.bak` → `BYTE_IDENTICAL=false`

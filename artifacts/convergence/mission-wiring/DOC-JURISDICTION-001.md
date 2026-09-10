# DOC-JURISDICTION-001 — Jurisdiction Coverage Documentation Audit

**Verdict: CLAIM_DRIFT_FOUND** · **DOCUMENTATION_CREDIBILITY_DEFECT = TRUE** · Read-only; docs not edited.
Machine-readable twin: `DOC-JURISDICTION-001.json`.

## Advertised claims (quoted)

| File:line | Claim |
|---|---|
| `README.md:83` | "analyze law across **19 US jurisdictions** currently supported (federal court system also covered; expansion to all 50 states is planned, not complete)" |
| `README.md:134` | "Trust law analysis (19 jurisdictions) \| FUNCTIONAL" |
| `README.md:184` | "Trust law limited to **19 US jurisdictions** (not all 50 yet)" |
| `docs/CLAIMS.md:72/77` | "Trust law analysis across 19 U.S. jurisdictions" — limitation honestly notes the 19-state list (CA, NY, TX, FL, IL, PA, OH, MI, NC, VA, AZ, CO, WA, OR, MA, MD, NJ, CT, DE) |
| `docs/CLAIMS.md:175` | "Trust law (19 jurisdictions) \| 247 \| ⚠️ PARTIAL" |
| `docs/CAPABILITY_INDEX.md:15` | "Trust-law support … FUNCTIONAL \| 19 jurisdictions only" |

## What the code actually contains

- `trust_law/jurisdiction_analyzer.py` (694 lines): named jurisdictions are **Delaware, Nevada, Alaska, South Dakota, Wyoming** + international **Cook Islands, Nevis, Belize, Liechtenstein**. No 19-state table.
- `trust_knowledge_base.py`: 30+ doctrines, **8 named jurisdictions**, UCC Art. 1–9 doctrine text (national scope).
- `trust_reasoning_engine.py`: a **UTC-adoption boolean list (~42 states)** at lines 521–531 — a data point for compliance checks, **not per-state rules**; `JURISDICTION_SCORES` scoring matrix.
- `trust_case_law.py`: case citations naming ~14 states in `states_followed` lists — citations, not per-state rule implementations.
- `trust_document_generator.py` / `ucc_filing_assistant.py`: **zero per-state tokens** — generic templates.

Of the CLAIMS-19 list: 0 appear as 2-letter code keys anywhere in `trust_law/`; 16/19 appear as incidental full names (mostly case-law `states_followed`), not as jurisdiction rule content.

## Mechanical test evidence (run on this worktree)

```text
trust_law/tests/test_trust_law.py = 73 tests → 73/73 PASS (JUnit: tests=73 failures=0 errors=0 skipped=0)
States exercised by tests: California, Nevada, New York, Texas, Delaware, South Dakota, Wyoming, Cook Islands
CI coverage: pytest.ini testpaths = tests, portal/tests, voice_concierge/governed/tests → trust_law NOT in default lane
Certification artifacts naming trust_law jurisdictions: NONE found under artifacts/
```

## Counts (never merged)

```text
ADVERTISED_COVERAGE     = 19
ACTUAL_IMPLEMENTED      = 8   (CA, NY, TX, DE, NV, SD, WY, AK; Cook Islands offshore)
ACTUAL_TESTED           = 8   (73/73 green, same 8 jurisdictions)
ACTUAL_CERTIFIED        = 0
```

## Recommended corrections (not applied)

1. README.md:83/134/184, docs/CLAIMS.md:72/77/175, docs/CAPABILITY_INDEX.md:15 — replace "19 US jurisdictions" with evidence-backed wording: **"8 jurisdictions with implemented and tested trust-law content (CA, NY, TX, DE, NV, SD, WY, AK; Cook Islands offshore)"**.
2. docs/CLAIMS.md:175 — the "247" test count is stale; current measured count is **73/73 PASS**.
3. docs/CLAIMS.md "CI coverage: UNKNOWN" → **NO** (not in the default pytest lane).
4. Keep the "not all 50 states" limitation — accurate and honest.

Note: the ~42-state UTC-adoption list in the reasoning engine is a genuine data point but is not per-state rule coverage and was not counted toward implementation.

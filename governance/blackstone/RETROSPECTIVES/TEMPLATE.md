# GB-1 Retrospective Template

## Purpose

This template captures operational evidence about whether GB-1 is improving engineering outcomes. It is not part of the frozen GB-1 baseline. It is the primary input for deciding when and how to open GBC-2.

## Review Window

Recommended: 90 days after GB-1 merge.

## Questions

### Usage

- Which BKGC articles were referenced most frequently in PRs and reviews?
- Which BGS standards were applied to real features?
- Which BKC concepts were reused without confusion?
- Which BRA engine or API definitions matched implementation decisions?
- Which BCCM tests were cited during certification or review?
- Which BKR terms were queried or clarified?
- Which BGC cases were referenced for guidance?

### Gaps

- Which BKGC articles were never referenced?
- Which BGS standards were ignored or unknown?
- Which concepts caused terminology confusion?
- Which architectural decisions lacked a clear BRA mapping?
- Which features had no corresponding BCCM test?

### Value

- Which CDRs prevented repeated debate?
- Which governance rules helped catch defects early?
- Which rules improved review clarity or speed?
- Which rules proved unnecessary or slowed engineering without benefit?

### Amendment Need

- What evidence supports creating GBC-2?
- Is the need tooling (linter, traceability, dashboard) or constitutional (new articles, changed hierarchy)?
- If a constitutional change is proposed, which downstream volumes would require updates?

## Evidence Format

Each answer should reference:

- PR or issue number
- Date range
- Specific requirement identifiers affected
- CDR created, if any

## Decision Output

At the end of the retrospective, produce one of:

1. **No action** — GB-1 is working; continue using it.
2. **Tooling workstream** — Open GBC-2 with a focus on linter, traceability, dashboard, or CI checks.
3. **Minor amendment** — Update BGS, BKC, BRA, BCCM, BKR, or BGC without changing BKGC.
4. **Constitutional amendment** — Follow the BKGC amendment procedure; this is intentionally rare.

## Location

Store completed retrospectives under `governance/blackstone/RETROSPECTIVES/`.

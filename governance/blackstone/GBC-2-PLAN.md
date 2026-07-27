# GBC-2 Planning — Governance Tooling

## Objective

Transform the Blackstone Governance Library from documentation into an active governance system by introducing validation tooling, traceability visualization, and automated compliance checks.

## Status

Draft planning stub. Not yet a baseline candidate.

## Candidate Priorities

1. **Governance Linter**
   - Detect undefined terms.
   - Detect missing requirement identifiers.
   - Detect broken references.
   - Detect terminology drift.

2. **Governance Traceability Graph**
   - Visualize links from BKGC → BGS → BKC → BRA → BCCM → BKR → BGC.
   - Report orphaned concepts and orphaned requirements.

3. **Governance Dashboard**
   - Compliance coverage.
   - Certified agents.
   - Open CDRs.
   - Pending amendments.
   - Registry health.

4. **Automated Compliance Tests**
   - Every requirement has at least one corresponding certification test.
   - Every BGC case references governing requirements.
   - Flag orphaned concepts or missing traceability.

## Deferred

- New constitutional articles.
- New BGC cases (add only as real development produces them).
- Agent certification (requires live system evidence).
- Portal integration code (own feature PRs).

## Entry Criteria for GBC-2

- GB-1 merged to `main`.
- At least three real PRs or features have attempted to reference BKGC requirements.
- Initial tooling design recorded in a CDR.

# Phase One Implementation Notes

## Governance

- Root `AGENTS.md` governs the repository and requires a DOX pass after meaningful edits.
- `portal/AGENTS.md` governs portal models, services, migrations, routers, and portal tests.
- `portal/routers/AGENTS.md` requires router logic to delegate to `portal/services/`.
- `tests/AGENTS.md` governs root-level tests outside the portal subtree.

## Phase 0 Artifacts Inspected

- `artifacts/fifty_state_expansion/PHASE_ZERO_CLOSURE.md`
- `artifacts/fifty_state_expansion/CURRENT_STATE_AUDIT.md`
- `artifacts/fifty_state_expansion/DEFICIENCY_REGISTER.json`
- `artifacts/fifty_state_expansion/ARCHITECTURE_PROPOSAL.md`
- `artifacts/fifty_state_expansion/DATA_MIGRATION_PLAN.md`
- `artifacts/fifty_state_expansion/SECURITY_AND_PRIVACY_REVIEW.md`
- `artifacts/fifty_state_expansion/UNSUPPORTED_CLAIM_CONTAINMENT.md`
- `data/jurisdictions/coverage.json`

## Architecture Findings

- Backend directories under `backend/` are standalone lead-router and Stripe services, not the active portal API.
- The active API surface is `portal/main.py` with FastAPI routers under `portal/routers/`.
- Portal business logic belongs in `portal/services/`.
- Portal persistence uses SQLAlchemy models under `portal/models/` and SQL migrations in `portal/migrations/`.
- Existing migrations are plain SQL files with inline schema definitions and runtime integrity migrations.
- Audit facilities exist in `portal/services/audit_service.py`, `portal/models/audit.py`, and `portal/models/audit_record.py`.
- Existing trust and UCC logic in `trust_law/` is prototype dataclass logic with static jurisdiction assertions and no primary-authority provenance.
- Existing legal intelligence modules under `legal_intelligence/` are practice-area engines, not a normalized legal authority store.
- Test conventions are pytest-based; portal tests live in `portal/tests/`, while root tests live in `tests/`.
- Pydantic v2 is available and used by portal route schemas.
- Citation/provenance concepts exist in Blackstone evidence ledger models, but no repository-wide legal authority schema existed before Phase 1.
- Feature flags exist in other governed surfaces, but no legal-authority feature flag was present.
- `data/` is ignored; intended jurisdiction JSON files require narrow `git add -f`.

## Phase 1 Design Decision

Phase 1 adds a new `legal_authority/` bounded package for normalized schemas, authority hierarchy, JSON-backed repository loading, effective-date evaluation, supersession, conflict detection, and provenance response shaping. Portal endpoints are read-only and delegate to `portal/services/jurisdiction_rule_service.py`.

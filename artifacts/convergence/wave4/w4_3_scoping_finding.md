# W4-3 SCOPING FINDING (recorded before implementation)

## Browser-gate target (#4) is NOT on the production line

`mission_wiring/browser_executor.py` (the §27 governed gate) exists only on the
ZD-001 derivative branch (`feat/sp-converge-zero-dollar-wiring`), which was never
published. The Wave-3 publication PR #304 deliberately excluded `mission_wiring/`
per the Principal's "publish canonical Wave-3 production implementation only"
protection. Main @ 79deec88 therefore has no browser gate to migrate.

## Adjusted W4-3 scope

Migratable consumers on the production line:
1. agent_runtime/manifest.py validator
2. agent_runtime/delegation.py set_delegatable
3. agent_runtime/registry.py validate

`BROWSER_GATE_RESOLUTION` = NOT_APPLICABLE_ON_PRODUCTION_LINE (gate lives in
unpublished mission_wiring; its migration happens when mission_wiring itself is
adjudicated for publication — separate decision, not silently bundled).

`PORTAL_CLASSIFICATION_SET` = EXCLUDED_BY_NAMESPACE (ruled).

This is recorded as a scoping correction, not a gate weakening: the browser gate
is still alias-blind today but it is not production surface on main.

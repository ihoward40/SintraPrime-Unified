# Deployment Foundation Runbook (design only; target unresolved)

PRODUCTION_TARGET = UNKNOWN
PROVIDER_SELECTION_REQUIRED = TRUE

## Required preflight

- exact approved SHA match;
- approved SHA reachable from explicitly certified lineage `79deec881544a80105e0b45663740ad0f0fccf17`;
- target/service/region/runtime/database/health URL identified;
- required configuration names present (values never recorded);
- migration prerequisite and rollback reference verified.

## Post-deploy verification (deterministic once target exists)

1. GET the named health endpoint; require expected status/body schema.
2. Read deployed revision from the provider's revision endpoint/metadata.
3. Verify revision equals approved SHA.
4. Run the documented read-only smoke suite.
5. Record evidence and stop; no automatic retry of uncertain consequential effects.

## Rollback

Application: redeploy the verified prior revision.
Configuration: restore the prior named configuration revision.
Database: do not blindly run DOWN in production. If disposable certification finds
any destructive step, policy is `APP ROLLBACK + FORWARD DATABASE REPAIR`.

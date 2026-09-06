-- JARVIS B2 capability registry migration ownership (INT/REGISTRY_MIGRATION_OWNERSHIP repair).
-- Adds production SQL ownership for the two authority-registry tables that previously
-- existed only via ORM create_all(). Definition matches portal/models/jarvis_capability_registry.py
-- exactly (column names, types, nullability, PK, FKs, uniques, indexes, server defaults).
-- No authority semantics changes: no lifecycle CHECKs are added because the ORM represents
-- enum membership at the Python service layer, not as database CHECK constraints.
-- DOWN: DROP TABLE IF EXISTS capability_transitions, capability_registrations CASCADE;

CREATE TABLE IF NOT EXISTS capability_registrations (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    capability_id VARCHAR(255) NOT NULL,
    capability_version VARCHAR(64) NOT NULL,
    contract_hash VARCHAR(64) NOT NULL,
    owner_principal UUID NOT NULL,
    lifecycle_state VARCHAR(64) NOT NULL,
    lifecycle_state_effective_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ,
    effective_state VARCHAR(64) NOT NULL,
    effective_state_computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    effective_executable BOOLEAN NOT NULL,
    supersedes VARCHAR(64),
    dependency_ids JSON NOT NULL,
    executor_id VARCHAR(255) NOT NULL,
    adapter_id VARCHAR(255) NOT NULL,
    approval_policy_ref VARCHAR(255),
    credential_policy_ref VARCHAR(255),
    verification_policy_ref VARCHAR(255),
    registry_revision INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_capability_registration_tenant_id_version UNIQUE (tenant_id, capability_id, capability_version),
    CONSTRAINT uq_capability_registration_tenant_contract_hash UNIQUE (tenant_id, contract_hash)
);
CREATE INDEX IF NOT EXISTS ix_capability_registrations_tenant_id ON capability_registrations (tenant_id);
CREATE INDEX IF NOT EXISTS ix_capability_registration_tenant_lifecycle ON capability_registrations (tenant_id, lifecycle_state);
CREATE INDEX IF NOT EXISTS ix_capability_registration_tenant_effective ON capability_registrations (tenant_id, effective_state);
CREATE INDEX IF NOT EXISTS ix_capability_registration_tenant_capability ON capability_registrations (tenant_id, capability_id);

CREATE TABLE IF NOT EXISTS capability_transitions (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    capability_id VARCHAR(255) NOT NULL,
    capability_version VARCHAR(64) NOT NULL,
    contract_hash VARCHAR(64) NOT NULL,
    from_status VARCHAR(64) NOT NULL,
    to_status VARCHAR(64) NOT NULL,
    actor_id UUID NOT NULL,
    authority VARCHAR(64) NOT NULL,
    reason VARCHAR(64),
    transitioned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    previous_transition_hash VARCHAR(64),
    transition_hash VARCHAR(64) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_capability_transitions_tenant_id ON capability_transitions (tenant_id);
CREATE INDEX IF NOT EXISTS ix_capability_transition_tenant_capability ON capability_transitions (tenant_id, capability_id, capability_version);
CREATE INDEX IF NOT EXISTS ix_capability_transition_hash_chain ON capability_transitions (previous_transition_hash);

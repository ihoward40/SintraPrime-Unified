-- Mission Control authoritative Mission/Run identity contract.
CREATE TABLE IF NOT EXISTS missions (
    mission_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    created_by UUID NOT NULL REFERENCES users(id),
    workflow_type VARCHAR(128),
    status VARCHAR(40) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_missions_tenant_status ON missions(tenant_id, status);

CREATE TABLE IF NOT EXISTS runs (
    run_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mission_id UUID NOT NULL REFERENCES missions(mission_id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    status VARCHAR(40) NOT NULL DEFAULT 'PENDING',
    execution_ref VARCHAR(128) UNIQUE,
    workflow_type VARCHAR(128) NOT NULL,
    input_data JSONB,
    input_data_hash VARCHAR(64),
    created_by UUID NOT NULL REFERENCES users(id),
    failure_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_runs_tenant_status ON runs(tenant_id, status);
CREATE INDEX IF NOT EXISTS ix_runs_tenant_mission ON runs(tenant_id, mission_id);

-- DOWN migration (dependency-safe):
-- DROP TABLE IF EXISTS runs;
-- DROP TABLE IF EXISTS missions;

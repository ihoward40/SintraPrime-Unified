-- =============================================================================
-- SP-EG-001 Phase 2: Economic governance persistence and integrity controls
-- Records decisions, approvals, reservations, provenance and planning data only.
-- No payment, banking, brokerage, borrowing, or trust-asset execution path exists.
-- =============================================================================

CREATE TABLE IF NOT EXISTS economic_asset_provenance_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    asset_id VARCHAR(128) NOT NULL,
    asset_type VARCHAR(80) NOT NULL,
    claim_maturity VARCHAR(40) NOT NULL,
    legal_effect VARCHAR(40) NOT NULL,
    public_filing_reference VARCHAR(256),
    provenance_payload JSONB NOT NULL DEFAULT '{}',
    evidence JSONB NOT NULL DEFAULT '[]',
    missing_elements JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_economic_asset_provenance_asset UNIQUE (tenant_id, asset_id)
);
CREATE INDEX IF NOT EXISTS ix_economic_asset_provenance_tenant
    ON economic_asset_provenance_records(tenant_id, asset_type);

CREATE TABLE IF NOT EXISTS economic_value_accrual_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    asset_id VARCHAR(128) NOT NULL,
    source VARCHAR(128) NOT NULL,
    amount NUMERIC(18,2),
    currency VARCHAR(3),
    description TEXT NOT NULL,
    evidence_refs JSONB NOT NULL DEFAULT '[]',
    accrued_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_economic_value_accrual_asset
    ON economic_value_accrual_records(tenant_id, asset_id, accrued_at);

CREATE TABLE IF NOT EXISTS economic_scenario_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    scenario_id VARCHAR(128) NOT NULL,
    title VARCHAR(256) NOT NULL,
    assumptions JSONB NOT NULL,
    confidence VARCHAR(32) NOT NULL,
    failure_conditions JSONB NOT NULL,
    time_horizon VARCHAR(128) NOT NULL,
    decision_use TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_economic_scenario_record UNIQUE (tenant_id, scenario_id)
);
CREATE INDEX IF NOT EXISTS ix_economic_scenario_tenant
    ON economic_scenario_records(tenant_id, created_at);

CREATE TABLE IF NOT EXISTS economic_capital_reserve_targets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    reserve_policy_id VARCHAR(128) NOT NULL,
    layer INTEGER NOT NULL CHECK (layer > 0),
    name VARCHAR(128) NOT NULL,
    purpose TEXT NOT NULL,
    target_amount NUMERIC(18,2) CHECK (target_amount IS NULL OR target_amount >= 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_economic_capital_reserve_layer UNIQUE (tenant_id, reserve_policy_id, layer)
);
CREATE INDEX IF NOT EXISTS ix_economic_capital_reserve_tenant
    ON economic_capital_reserve_targets(tenant_id, reserve_policy_id);

CREATE TABLE IF NOT EXISTS economic_mission_budgets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    mission_id VARCHAR(128) NOT NULL,
    authorized_amount NUMERIC(18,2) NOT NULL CHECK (authorized_amount >= 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    policy_version VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_economic_mission_budget UNIQUE (tenant_id, mission_id)
);
CREATE INDEX IF NOT EXISTS ix_economic_mission_budget_tenant
    ON economic_mission_budgets(tenant_id, mission_id);

CREATE TABLE IF NOT EXISTS economic_spend_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    mission_id VARCHAR(128) NOT NULL,
    actor_id UUID NOT NULL REFERENCES users(id),
    category VARCHAR(64) NOT NULL,
    amount NUMERIC(18,2) NOT NULL CHECK (amount > 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    request_digest VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_economic_spend_request_digest UNIQUE (tenant_id, request_digest)
);
CREATE INDEX IF NOT EXISTS ix_economic_spend_requests_tenant_mission
    ON economic_spend_requests(tenant_id, mission_id, created_at);

CREATE TABLE IF NOT EXISTS economic_spend_evaluations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    spend_request_id UUID NOT NULL REFERENCES economic_spend_requests(id) ON DELETE CASCADE,
    policy_version VARCHAR(64) NOT NULL,
    decision VARCHAR(32) NOT NULL CHECK (decision IN ('allowed','denied','approval_required')),
    reason TEXT NOT NULL,
    requires_principal_approval BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_economic_spend_evaluations_request
    ON economic_spend_evaluations(tenant_id, spend_request_id);

CREATE TABLE IF NOT EXISTS economic_principal_approval_receipts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    approval_request_id VARCHAR(128) NOT NULL,
    principal_id UUID NOT NULL REFERENCES users(id),
    mission_id VARCHAR(128) NOT NULL,
    request_digest VARCHAR(64) NOT NULL,
    policy_version VARCHAR(64) NOT NULL,
    result VARCHAR(16) NOT NULL CHECK (result IN ('approved','denied')),
    receipt_hash VARCHAR(64) NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_economic_approval_expiry CHECK (expires_at > issued_at),
    CONSTRAINT uq_economic_approval_request UNIQUE (tenant_id, approval_request_id)
);
CREATE INDEX IF NOT EXISTS ix_economic_approval_digest
    ON economic_principal_approval_receipts(tenant_id, mission_id, request_digest);

CREATE TABLE IF NOT EXISTS economic_budget_reservations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    mission_id VARCHAR(128) NOT NULL,
    spend_request_id UUID NOT NULL REFERENCES economic_spend_requests(id) ON DELETE CASCADE,
    idempotency_key VARCHAR(128) NOT NULL,
    request_digest VARCHAR(64) NOT NULL,
    amount NUMERIC(18,2) NOT NULL CHECK (amount > 0),
    state VARCHAR(24) NOT NULL DEFAULT 'reserved'
        CHECK (state IN ('reserved','committed','released','expired')),
    expires_at TIMESTAMPTZ NOT NULL,
    committed_at TIMESTAMPTZ,
    released_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_economic_budget_reservation_idempotency
        UNIQUE (tenant_id, mission_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS ix_economic_budget_reservations_state
    ON economic_budget_reservations(tenant_id, mission_id, state);

CREATE TABLE IF NOT EXISTS economic_ledger_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    mission_id VARCHAR(128) NOT NULL,
    actor_id UUID NOT NULL REFERENCES users(id),
    sequence INTEGER NOT NULL CHECK (sequence > 0),
    decision_type VARCHAR(64) NOT NULL,
    policy_version VARCHAR(64) NOT NULL,
    evidence_refs JSONB NOT NULL DEFAULT '[]',
    payload JSONB NOT NULL DEFAULT '{}',
    previous_hash VARCHAR(64),
    event_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_economic_ledger_sequence UNIQUE (tenant_id, mission_id, sequence),
    CONSTRAINT uq_economic_ledger_event_hash UNIQUE (tenant_id, event_hash)
);
CREATE INDEX IF NOT EXISTS ix_economic_ledger_chain
    ON economic_ledger_events(tenant_id, mission_id, sequence);

-- Immutable evidence: corrections are new superseding events/receipts, never mutation.
CREATE OR REPLACE FUNCTION prevent_economic_ledger_event_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'economic_ledger_events rows are immutable';
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_economic_ledger_event_immutable ON economic_ledger_events;
CREATE TRIGGER trg_economic_ledger_event_immutable
    BEFORE UPDATE OR DELETE ON economic_ledger_events
    FOR EACH ROW EXECUTE FUNCTION prevent_economic_ledger_event_mutation();

CREATE OR REPLACE FUNCTION prevent_economic_approval_receipt_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'economic_principal_approval_receipts rows are immutable';
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_economic_approval_receipt_immutable ON economic_principal_approval_receipts;
CREATE TRIGGER trg_economic_approval_receipt_immutable
    BEFORE UPDATE OR DELETE ON economic_principal_approval_receipts
    FOR EACH ROW EXECUTE FUNCTION prevent_economic_approval_receipt_mutation();

-- PostgreSQL tenant isolation. The application sets app.tenant_id per request/transaction.
DO $$
DECLARE
    table_name TEXT;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'economic_asset_provenance_records',
        'economic_value_accrual_records',
        'economic_scenario_records',
        'economic_capital_reserve_targets',
        'economic_mission_budgets',
        'economic_spend_requests',
        'economic_spend_evaluations',
        'economic_principal_approval_receipts',
        'economic_budget_reservations',
        'economic_ledger_events'
    ]
    LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', table_name);
        EXECUTE format('DROP POLICY IF EXISTS tenant_isolation ON %I', table_name);
        EXECUTE format(
            'CREATE POLICY tenant_isolation ON %I USING (tenant_id = NULLIF(current_setting(''app.tenant_id'', true), '''')::uuid) WITH CHECK (tenant_id = NULLIF(current_setting(''app.tenant_id'', true), '''')::uuid)',
            table_name
        );
    END LOOP;
END;
$$;

COMMENT ON TABLE economic_ledger_events IS
    'SP-EG-001 immutable economic decision ledger. Records governance only; no money movement.';
COMMENT ON TABLE economic_budget_reservations IS
    'SP-EG-001 reserve/commit/release accounting control; a reservation is not a payment.';
COMMENT ON TABLE economic_principal_approval_receipts IS
    'Immutable approval evidence bound to one exact request digest, mission, tenant and expiry.';

-- DOWN migration notes intentionally require explicit operator action because this migration
-- creates immutable governance evidence. Remove RLS/policies and triggers before dropping tables.

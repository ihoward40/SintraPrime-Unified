-- SintraPrime Adaptive Orchestration Layer domain tables.
-- Milestone One stores deterministic mock-provider orchestration only.

CREATE TABLE IF NOT EXISTS orchestration_runs (
    id                      UUID PRIMARY KEY,
    tenant_id               UUID NOT NULL REFERENCES tenants(id),
    created_by              UUID REFERENCES users(id),
    objective               TEXT NOT NULL,
    constraints             JSONB NOT NULL DEFAULT '{}'::jsonb,
    task_type               VARCHAR(40) NOT NULL,
    sensitivity             VARCHAR(40) NOT NULL,
    execution_mode          VARCHAR(40) NOT NULL,
    status                  VARCHAR(40) NOT NULL DEFAULT 'PLANNED',
    classification          JSONB NOT NULL DEFAULT '{}'::jsonb,
    policy                  JSONB NOT NULL DEFAULT '{}'::jsonb,
    final_result            JSONB,
    approval_required       BOOLEAN NOT NULL DEFAULT FALSE,
    cancellation_reason     TEXT,
    started_at              TIMESTAMPTZ,
    completed_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_orchestration_runs_tenant_status
    ON orchestration_runs(tenant_id, status);
CREATE INDEX IF NOT EXISTS ix_orchestration_runs_tenant_created
    ON orchestration_runs(tenant_id, created_at);
CREATE INDEX IF NOT EXISTS ix_orchestration_runs_task_type
    ON orchestration_runs(tenant_id, task_type);

CREATE TABLE IF NOT EXISTS orchestration_nodes (
    id                      UUID PRIMARY KEY,
    run_id                  UUID NOT NULL REFERENCES orchestration_runs(id) ON DELETE CASCADE,
    node_id                 VARCHAR(80) NOT NULL,
    sequence                INTEGER NOT NULL,
    role                    VARCHAR(40) NOT NULL,
    objective               TEXT NOT NULL,
    instructions            JSONB NOT NULL DEFAULT '{}'::jsonb,
    dependencies            JSONB NOT NULL DEFAULT '[]'::jsonb,
    assigned_provider_id    VARCHAR(80),
    assigned_model_id       VARCHAR(120),
    status                  VARCHAR(40) NOT NULL DEFAULT 'PLANNED',
    retry_count             INTEGER NOT NULL DEFAULT 0,
    input_artifacts         JSONB NOT NULL DEFAULT '[]'::jsonb,
    output_artifacts        JSONB NOT NULL DEFAULT '[]'::jsonb,
    confidence              DOUBLE PRECISION,
    evidence                JSONB NOT NULL DEFAULT '[]'::jsonb,
    started_at              TIMESTAMPTZ,
    completed_at            TIMESTAMPTZ,
    error                   TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_orchestration_nodes_run_node UNIQUE (run_id, node_id)
);

CREATE INDEX IF NOT EXISTS ix_orchestration_nodes_run_status
    ON orchestration_nodes(run_id, status);
CREATE INDEX IF NOT EXISTS ix_orchestration_nodes_provider
    ON orchestration_nodes(assigned_provider_id, assigned_model_id);

CREATE TABLE IF NOT EXISTS orchestration_events (
    id                      UUID PRIMARY KEY,
    run_id                  UUID NOT NULL REFERENCES orchestration_runs(id) ON DELETE CASCADE,
    node_id                 VARCHAR(80),
    sequence                INTEGER NOT NULL,
    event_type              VARCHAR(80) NOT NULL,
    actor_role              VARCHAR(40),
    payload                 JSONB NOT NULL DEFAULT '{}'::jsonb,
    previous_event_hash     VARCHAR(64),
    event_hash              VARCHAR(64) NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_orchestration_events_run_seq UNIQUE (run_id, sequence)
);

CREATE INDEX IF NOT EXISTS ix_orchestration_events_run
    ON orchestration_events(run_id);
CREATE INDEX IF NOT EXISTS ix_orchestration_events_type
    ON orchestration_events(run_id, event_type);

CREATE TABLE IF NOT EXISTS orchestration_provider_definitions (
    id                      UUID PRIMARY KEY,
    provider_id             VARCHAR(80) NOT NULL,
    model_id                VARCHAR(120) NOT NULL,
    display_name            VARCHAR(160) NOT NULL,
    supported_task_types    JSONB NOT NULL DEFAULT '[]'::jsonb,
    context_window          INTEGER NOT NULL,
    structured_output       BOOLEAN NOT NULL DEFAULT FALSE,
    tool_support            JSONB NOT NULL DEFAULT '[]'::jsonb,
    coding_strength         DOUBLE PRECISION NOT NULL DEFAULT 0,
    reasoning_strength      DOUBLE PRECISION NOT NULL DEFAULT 0,
    research_strength       DOUBLE PRECISION NOT NULL DEFAULT 0,
    verification_strength   DOUBLE PRECISION NOT NULL DEFAULT 0,
    latency_class           VARCHAR(40) NOT NULL,
    input_cost              DOUBLE PRECISION NOT NULL DEFAULT 0,
    output_cost             DOUBLE PRECISION NOT NULL DEFAULT 0,
    availability            VARCHAR(40) NOT NULL,
    data_policy             JSONB NOT NULL DEFAULT '{}'::jsonb,
    allowed_sensitivity     JSONB NOT NULL DEFAULT '[]'::jsonb,
    enabled                 BOOLEAN NOT NULL DEFAULT TRUE,
    confidence_history      JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_orchestration_provider_model UNIQUE (provider_id, model_id)
);

CREATE INDEX IF NOT EXISTS ix_orchestration_provider_enabled
    ON orchestration_provider_definitions(enabled, availability);

CREATE TABLE IF NOT EXISTS orchestration_routing_decisions (
    id                      UUID PRIMARY KEY,
    run_id                  UUID NOT NULL REFERENCES orchestration_runs(id) ON DELETE CASCADE,
    node_pk                 UUID REFERENCES orchestration_nodes(id) ON DELETE CASCADE,
    node_id                 VARCHAR(80),
    selected_provider_id    VARCHAR(80),
    selected_model_id       VARCHAR(120),
    candidate_providers     JSONB NOT NULL DEFAULT '[]'::jsonb,
    rejected_providers      JSONB NOT NULL DEFAULT '[]'::jsonb,
    selection_reason        TEXT NOT NULL,
    policy_applied          JSONB NOT NULL DEFAULT '{}'::jsonb,
    estimated_cost          DOUBLE PRECISION NOT NULL DEFAULT 0,
    actual_cost             DOUBLE PRECISION,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_orchestration_routing_run_node
    ON orchestration_routing_decisions(run_id, node_id);
CREATE INDEX IF NOT EXISTS ix_orchestration_routing_selected
    ON orchestration_routing_decisions(selected_provider_id, selected_model_id);

CREATE TABLE IF NOT EXISTS orchestration_verification_results (
    id                      UUID PRIMARY KEY,
    run_id                  UUID NOT NULL REFERENCES orchestration_runs(id) ON DELETE CASCADE,
    node_id                 VARCHAR(80) NOT NULL,
    checker_node_id         VARCHAR(80),
    verification_status     VARCHAR(40) NOT NULL,
    confidence_score        DOUBLE PRECISION NOT NULL,
    evidence_quality        VARCHAR(40) NOT NULL,
    unresolved_uncertainty  JSONB NOT NULL DEFAULT '[]'::jsonb,
    assumptions             JSONB NOT NULL DEFAULT '[]'::jsonb,
    contradictions          JSONB NOT NULL DEFAULT '[]'::jsonb,
    findings                JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_orchestration_verification_run_node
    ON orchestration_verification_results(run_id, node_id);

CREATE TABLE IF NOT EXISTS orchestration_reconciliation_results (
    id                          UUID PRIMARY KEY,
    run_id                      UUID NOT NULL REFERENCES orchestration_runs(id) ON DELETE CASCADE,
    reconciler_node_id          VARCHAR(80),
    verified_result             JSONB NOT NULL DEFAULT '{}'::jsonb,
    supported_inference         JSONB NOT NULL DEFAULT '[]'::jsonb,
    unresolved_issues           JSONB NOT NULL DEFAULT '[]'::jsonb,
    disputed_claims             JSONB NOT NULL DEFAULT '[]'::jsonb,
    principal_decision_required JSONB NOT NULL DEFAULT '[]'::jsonb,
    final_confidence            DOUBLE PRECISION NOT NULL DEFAULT 0,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_orchestration_reconciliation_run
    ON orchestration_reconciliation_results(run_id);

CREATE TABLE IF NOT EXISTS orchestration_approval_requests (
    id                  UUID PRIMARY KEY,
    run_id              UUID NOT NULL REFERENCES orchestration_runs(id) ON DELETE CASCADE,
    node_id             VARCHAR(80),
    requested_action    VARCHAR(160) NOT NULL,
    reason              TEXT NOT NULL,
    risk_level          VARCHAR(40) NOT NULL,
    status              VARCHAR(40) NOT NULL DEFAULT 'REQUESTED',
    requested_by_role   VARCHAR(40) NOT NULL,
    principal_id        UUID REFERENCES users(id),
    decided_at          TIMESTAMPTZ,
    decision_reason     TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_orchestration_approval_run_status
    ON orchestration_approval_requests(run_id, status);
CREATE INDEX IF NOT EXISTS ix_orchestration_approval_principal
    ON orchestration_approval_requests(principal_id, status);

CREATE TABLE IF NOT EXISTS orchestration_budget_usage (
    id                      UUID PRIMARY KEY,
    run_id                  UUID NOT NULL UNIQUE REFERENCES orchestration_runs(id) ON DELETE CASCADE,
    max_input_tokens        INTEGER NOT NULL,
    max_output_tokens       INTEGER NOT NULL,
    max_provider_cost       DOUBLE PRECISION NOT NULL,
    max_nodes               INTEGER NOT NULL,
    max_retries             INTEGER NOT NULL,
    max_execution_seconds   INTEGER NOT NULL,
    input_tokens_used       INTEGER NOT NULL DEFAULT 0,
    output_tokens_used      INTEGER NOT NULL DEFAULT 0,
    provider_cost_used      DOUBLE PRECISION NOT NULL DEFAULT 0,
    nodes_used              INTEGER NOT NULL DEFAULT 0,
    retries_used            INTEGER NOT NULL DEFAULT 0,
    hard_limit_reached      BOOLEAN NOT NULL DEFAULT FALSE,
    limit_reason            TEXT,
    approved_providers      JSONB NOT NULL DEFAULT '[]'::jsonb,
    approved_task_types     JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS orchestration_evidence_references (
    id                  UUID PRIMARY KEY,
    run_id              UUID NOT NULL REFERENCES orchestration_runs(id) ON DELETE CASCADE,
    node_id             VARCHAR(80),
    source_type         VARCHAR(60) NOT NULL,
    source_uri          TEXT,
    title               TEXT,
    excerpt_redacted    TEXT,
    citation            TEXT,
    evidence_quality    VARCHAR(40) NOT NULL,
    verified            BOOLEAN NOT NULL DEFAULT FALSE,
    protected           BOOLEAN NOT NULL DEFAULT FALSE,
    metadata_json       JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_orchestration_evidence_run_node
    ON orchestration_evidence_references(run_id, node_id);
CREATE INDEX IF NOT EXISTS ix_orchestration_evidence_quality
    ON orchestration_evidence_references(run_id, evidence_quality);

COMMENT ON TABLE orchestration_runs IS
    'Governed adaptive orchestration run; Milestone One permits deterministic mock providers only.';
COMMENT ON TABLE orchestration_events IS
    'Append-only orchestration audit event stream with hash-chain fields.';
COMMENT ON TABLE orchestration_provider_definitions IS
    'Declared provider capabilities; no external or paid provider is enabled by this migration.';

-- DOWN migration notes:
-- Run in reverse dependency order if rollback is required.
--   DROP TABLE IF EXISTS orchestration_evidence_references;
--   DROP TABLE IF EXISTS orchestration_budget_usage;
--   DROP TABLE IF EXISTS orchestration_approval_requests;
--   DROP TABLE IF EXISTS orchestration_reconciliation_results;
--   DROP TABLE IF EXISTS orchestration_verification_results;
--   DROP TABLE IF EXISTS orchestration_routing_decisions;
--   DROP TABLE IF EXISTS orchestration_provider_definitions;
--   DROP TABLE IF EXISTS orchestration_events;
--   DROP TABLE IF EXISTS orchestration_nodes;
--   DROP TABLE IF EXISTS orchestration_runs;

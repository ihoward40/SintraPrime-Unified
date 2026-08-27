-- =============================================================================
-- Gate 4D-B: public GitHub repository-metadata read authority extension
-- Extends the existing Gate 4B/4C external-action envelope. This gate permits
-- E0 read-only provider metadata only and does not authorize credentials,
-- repository content reads, account connection, or any external write.
-- =============================================================================

ALTER TABLE external_action_intents
    DROP CONSTRAINT IF EXISTS ck_external_action_intent_environment;

ALTER TABLE external_action_intents
    ADD CONSTRAINT ck_external_action_intent_environment
        CHECK (environment IN ('sandbox', 'provider_test', 'provider_readonly'));

ALTER TABLE external_action_intents
    DROP CONSTRAINT IF EXISTS ck_external_action_intent_risk;

ALTER TABLE external_action_intents
    ADD CONSTRAINT ck_external_action_intent_risk
        CHECK (risk_class IN ('E0', 'E1'));

COMMENT ON TABLE external_action_intents IS
    'Canonical Gate 4B+ external-action authority envelope. Gate 4D-B adds E0 public provider metadata reads only.';

# Payment Webhook Validation — Increment One Certification Report

**Baseline commit:** `cb343b92ef776e2a827ee459d9512179bc9aad6a`
**Baseline tree:** `740a752b200672a5840bf9c1647b628eed6d403c`
**Increment:** Payment Webhook Validation and Durable Replay Controls
**Date:** 2026-07-21

## Scope

This increment establishes:
- Stripe webhook signature verification at the ingestion boundary
- Server-side tenant resolution from provider_tenant_mappings
- Durable replay-idempotency via PostgreSQL with UNIQUE (provider, provider_account_id, provider_event_id)
- Lease-safe processing with short transactions
- Audit-envelope integration for all event phases
- No-side-effect acknowledgment sink

## Authority boundaries

- The `payment_events` row is the authoritative webhook acknowledgment and idempotency record. `result_reference` stores a deterministic acknowledgment identifier. No separate receipt table exists.
- Audit envelopes remain the audit-event authority. The `payment_events` table does not replace the audit envelope and introduces no competing evidence hash authority.
- Audit metadata is not deeply immutable (known limitation from PR #215 certification).

## CI certification

The `payment-webhook-certification` CI lane:
- Provisions PostgreSQL 15 with health checks
- Applies base schema and all additive migrations in order
- Runs signature verification, tenant resolution, idempotency, concurrency, mapping, and parity tests
- Proves UNIQUE constraint enforcement under concurrent access
- Proves lease acquisition and stale-lease reclaim exclusivity

## Known limitations

1. Production migration runner: no programmatic mechanism exists to apply SQL migrations in production
2. Stripe Connect vs non-Connect: deployment decision not yet made
3. Webhook endpoint secret provisioning: STRIPE_WEBHOOK_SECRET must be provisioned per deployment
4. Provider_tenant_mapping bootstrapping: mapping table starts empty; admin flow not part of this increment
5. Audit metadata is not deeply immutable

## Explicit nonclaims

- NOT production certified
- NOT PCI-DSS certified
- NOT complete payment processing
- NOT case-generation enablement
- NOT subscription authority
- NOT distributed execution authority
- NOT a replacement for backend/stripe-payments/
- NOT a claim that SQLite is sufficient for production idempotency durability
- NOT a claim that production migration execution is resolved
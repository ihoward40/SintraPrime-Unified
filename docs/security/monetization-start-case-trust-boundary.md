# Monetization Start-Case Trust Boundary

The start-case endpoint uses a trusted internal gateway model.

```text
Stripe Checkout
  -> Stripe webhook signature verification in the payment gateway
  -> gateway validates checkout.session.completed, paid, complete, amount, currency, tier, metadata.case_id
  -> gateway emits normalized internal_payment_event.v1
  -> gateway signs the exact raw JSON body with HMAC-SHA256
  -> POST /api/monetization/start-case verifies key id, timestamp, event id, body digest, signature, and payment bindings
  -> case generation, schema validation, ledger recording, and idempotent response
```

`POST /api/monetization/start-case` is not a public payment-verification endpoint. It must be reachable only by the verified payment gateway or equivalent trusted automation that has already verified Stripe webhook signatures. The route rejects requests unless the signed raw body includes the normalized event fields and the following binding checks pass:

- `event_type == checkout.session.completed`
- `payment_status == paid`
- `session_status == complete`
- `currency` is configured and supported; default is `usd`
- `amount_total` equals the configured amount for `tier`
- request `case_id`, `tier`, and `payment_session_id` are the same values covered by the signed event
- `event_id` is unique in the SQLite idempotency store

Signature input is exactly:

```text
v1
<key_id>
<timestamp>
<event_id>
<raw_body_sha256>
```

Required headers:

- `X-Start-Case-Key-Id`
- `X-Start-Case-Timestamp`
- `X-Start-Case-Event-Id`
- `X-Start-Case-Signature`

The service supports current and previous keys through `MONETIZATION_START_CASE_CURRENT_*`, `MONETIZATION_START_CASE_PREVIOUS_*`, or `MONETIZATION_START_CASE_HMAC_KEYS` JSON. Full secret material must never be logged.

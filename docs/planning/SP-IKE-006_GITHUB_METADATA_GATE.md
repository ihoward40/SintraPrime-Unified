# SP-IKE-006 — Gate 4D-B GitHub Repository Metadata Read

Status: **OPEN — IMPLEMENTATION / CERTIFICATION IN PROGRESS**

## Authorization

Gate 4D-B is explicitly authorized only for the first selected Gate 4D candidate: public GitHub repository metadata for `ihoward40/SintraPrime-Unified`.

This authorization does **not** authorize:

- GitHub credentials or account connection;
- private repository access;
- repository contents download;
- arbitrary owner/repository selection;
- issues, pull requests, discussions, Actions, administration, or branch mutation;
- POST, PUT, PATCH, DELETE, or GraphQL mutations;
- Gmail, Google Drive, Shopify, Meta, legal filing, payments, publishing, or any other connector;
- production write authority of any kind.

Google Drive metadata-only remains reserved for a later separately authorized authenticated-account gate.

## Exact adapter contract

- adapter: `provider.github-metadata-read-v1`
- operation: `repository_metadata_read`
- environment: `provider_readonly`
- risk: `E0`
- credentials: none permitted
- method: exact `GET`
- host: exact `api.github.com`
- path: exact `/repos/ihoward40/SintraPrime-Unified`
- query: forbidden
- fragment: forbidden
- redirects: forbidden
- destination mutation: forbidden
- payload: exact `{ "method": "GET", "resource": "repository_metadata" }`

## Authority model

The adapter does not own authority. It is dispatched only through `portal/services/restricted_external_action.py`, the same durable authority envelope certified by Gates 4B and 4C.

Before network I/O, execution must revalidate:

1. exact adapter/operation/environment/risk;
2. active durable service identity;
3. exact capability and destination scope;
4. exact Principal approval bound to destination and payload hash;
5. global, tenant, and adapter kill switches;
6. durable tenant+adapter rate bucket;
7. exact approved destination and payload at execution time.

The GitHub adapter cannot receive a credential lease and never emits an `Authorization` header.

## Network containment

- HTTPS only;
- DNS resolution only for `api.github.com`;
- private, loopback, link-local, reserved/non-global IPs fail closed;
- resolved IPs are pinned into the actual aiohttp transport resolver;
- DNS cache/re-resolution is disabled for the request;
- TLS hostname remains `api.github.com`;
- all 30x redirects fail closed and are never followed;
- no second hostname may be resolved by the pinned resolver.

## Durable evidence

The existing evidence chain records the durable intent, preflight, Principal approval, execution claim, provider request hash, provider response hash, provider URL, resolved IP set, outcome, and replay/reconciliation evidence. Raw provider response bodies are not persisted by the external-action authority.

## Failure and replay semantics

- no automatic network retry;
- timeout becomes `UNKNOWN_REQUIRES_RECONCILIATION`;
- reconciliation performs no blind retry and confirms no persistent provider-side state;
- succeeded intents replay from the durable provider receipt without another provider request;
- concurrent duplicate execution must collapse to one provider attempt;
- E0 read-only success has no compensating external action because there is no external effect to undo.

## Closure requirements

Gate 4D-B remains OPEN until one exact head proves:

- adapter destination/method/payload containment;
- redirect escape prevention;
- DNS/host pinning and private-address rejection;
- zero credential use;
- E0/provider-readonly durable schema support;
- Principal approval and service-identity enforcement;
- cross-tenant denial;
- payload/destination mutation rejection;
- scheduler non-bypass;
- global/tenant/adapter kill switches;
- durable local rate limit and provider-rate-limit handling;
- timeout/restart reconciliation with no blind retry;
- concurrent duplicate suppression and durable replay;
- provider request/response evidence and evidence-chain verification;
- one real public GitHub metadata GET through the durable authority envelope;
- all prior gate workflows and broad repository CI terminal-green on that same head.

A green Gate 4D-B does not authorize repository contents-read expansion, authenticated GitHub access, Google Drive, or any write operation.

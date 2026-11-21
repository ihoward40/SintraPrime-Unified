# SintraPrime adapters

## Purpose

Own the live Notion HTTP boundary and its local write replay ledger.

## Ownership

- `notionLiveRead.ts`: fixed-origin GET, integration identity lookup, configuration and secret redaction.
- `notionLiveWrite.ts`: approved page-property PATCH, opaque in-process authority and durable request reservations.
- The CLI owns operator, saved approval, skill, prestate and policy validation; `executor/executePlan.ts` consumes its authority.

## Local Contracts

- Use `NOTION_TOKEN`, `NOTION_API_BASE` (only `https://api.notion.com`) and `NOTION_API_VERSION` (default `2022-06-28`). No alternative live-mode environment switch is required.
- Reads return `{ http_status, redacted }`; identity lookup returns `{ ok, me }`. Successful reads require a JSON object; malformed or non-object success bodies fail closed. Only page/database GET and `/v1/users/me` are supported.
- Writes accept only page PATCH with a JSON `properties` object. Require matching canonical URL/path, `NotionAdapter`, `read_only:false`, `approval_scoped:true`, consistent prestate fingerprint and passing guards.
- Only the three validated CLI approval-resume branches mint write authority. Serialized flags/timestamps or copied capability objects cannot authorize a write. The issuer is an internal trusted-code API, not an untrusted-input endpoint.
- Bind authority and replay to execution, step, canonical destination, serialized body, key, API version and hashed credential scope. Never store the credential in the ledger or evidence.
- Reserve a SHA-256 key filename atomically with exclusive create before dispatch. Only matching 2xx success records replay. Unbound legacy records and pending, failed, malformed or uncertain outcomes require explicit reconciliation; never automatically retry them or claim remote Notion idempotency.
- PATCH transport stays private. Redirects are forbidden; reads/writes have a 30-second timeout. Redact configured credentials in all response strings and keys, request evidence and transport errors.
- CLI replay shortcuts must use the bound Notion ledger. Generic adapters keep their existing ledger behavior.

## Work Guidance

- Exercise transport with fake fetch only; regression tests must never contact live Notion.

## Verification

- From `apps/sintraprime`: `node --require tsx/cjs --test tests/integration/notion-adapters.test.mjs`.
- `npm run typecheck` validates integration with the CLI and executor.

## Child DOX Index

None.

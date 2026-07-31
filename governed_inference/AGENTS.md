# governed_inference

## Purpose

Owns the local-first inference control plane: normalized request/result contracts, data classification, policy enforcement, provider adapters, routing, cost accounting, cache receipts, reliability scoring, task decomposition, and escalation evidence.

## Ownership

- Provider-independent inference contracts and enums
- Inference policy inheritance and paid-use governance
- Data classification and redaction boundary receipts
- Provider adapter interfaces and deterministic test adapters
- Local, free-gateway, cloud, and premium provider adapter shells
- Governed routing, fallback, retry, circuit-breaker, and reliability decisions
- In-memory ledger, cache, task decomposition, and escalation primitives used by tests and future persistence adapters

## Local Contracts

- CI-facing defaults must not make external provider calls.
- Unknown cloud cost is not zero; policy gates must fail closed when configured.
- Restricted or unknown data must remain local under default policy.
- Paid routes must be denied when the global paid switch is disabled, even if a request carries approval metadata.
- Free-gateway providers such as OmniRoute/OpenRouter are cloud candidates and must stay ineligible until configured with known pricing/account policy.
- Provider-specific payloads must stay inside adapters and not leak into domain contracts.

## Work Guidance

- Add provider integrations behind the `InferenceProvider` interface.
- Keep network-capable adapters disabled unless credentials, endpoint, account limits, and cost metadata are explicit.
- Prefer deterministic mock or replay providers for tests.
- Use decomposition before escalation when a smaller local model can handle bounded subtasks.

## Verification

- Run `python -m pytest tests/test_governed_inference.py -q` after changing core router/policy/cache/ledger behavior.
- Run `python -m pytest tests/test_governed_inference_adapters.py -q` after changing or adding provider adapters.

## Child DOX Index

*(None - package modules are leaf modules.)*

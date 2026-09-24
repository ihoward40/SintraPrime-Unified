# Provider Reliability Matrix

**Generated:** 2026-08-08
**Commit:** e2ada66e

---

## Runtime Providers

| Provider | Config | Auth | Invocation | Streaming | Structured Output | Error Handling | Rate Limits | Retry | Timeout | Usage Accounting | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| OpenAI | NOT CONFIGURED | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | BLOCKED_BY_DEPENDENCY |
| Anthropic | NOT CONFIGURED | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | BLOCKED_BY_DEPENDENCY |
| Google | NOT CONFIGURED | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | BLOCKED_BY_DEPENDENCY |
| Mock Provider 1 | mock_only | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | STUB_ONLY |
| Mock Provider 2 | mock_only | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | STUB_ONLY |

## Provider Adapters Found

| File | Purpose | Status |
|---|---|---|
| `portal/services/orchestration/provider_registry.py` | Mock provider registry | STUB_ONLY |
| `portal/services/orchestration/model_router.py` | Policy-driven routing | STUB_ONLY (routes to mocks) |
| `governed_inference/providers.py` | Provider adapters | DISCONNECTED |
| `local_llm/provider.py` | Local LLM adapter | NOT TESTED |
| `voice_concierge/governed/providers.py` | Voice providers | NOT TESTED |
| `voice_concierge/governed/mock_providers.py` | Voice mocks | STUB_ONLY |
| `portal/sso/okta_provider.py` | SSO provider | VERIFIED (SSO flow) |
| `portal/sso/providers/azure.py` | Azure AD SSO | NOT TESTED |
| `portal/sso/providers/google.py` | Google SSO | NOT TESTED |

## Summary

- **No real LLM provider is connected.** The system routes exclusively to mock providers.
- Provider registry header states: "no external providers are connected."
- SSO providers (Okta, Azure, Google) exist for authentication — separate from LLM providers.

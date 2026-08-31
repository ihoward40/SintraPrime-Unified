# Security Boundaries

Milestone One uses deterministic mock providers only. Before provider-facing records or audit payloads, orchestration helpers redact API keys, passwords, tokens, session cookies, payment-card-like numbers, and tax-identifier-like values.

Prompt-injection markers and denied external actions are detected and logged. The orchestrator may not merge code, deploy, spend money, publish public content, send external communications, change legal positions, modify payment settings, or approve its own high-risk result.

Protected evidence must remain referenced through redacted metadata. Secrets belong in environment variables or the existing secret-management system, never source files.

# LLM Reliability Layer Audit — PR-0004

**Date:** 2026-06-12  
**Status:** Complete — Audit Phase  
**Auditor:** Hermes Agent

---

## Executive Summary

This audit identifies **four distinct agents** that directly invoke LLM providers (OpenAI) with **zero shared infrastructure**. Each agent independently creates `openai.OpenAI` clients, handles errors differently, and lacks timeout, retry, fallback, and redaction safeguards.

| Agent | File | LLM Calls | Streaming | Fallback |
|-------|------|-----------|-----------|----------|
| **Chat Agent** | `agents/chat/chat_agent.py` | 4 locations | ✅ Yes | ✅ Basic |
| **Zero Agent** | `agents/zero/zero_agent.py` | 1 location | ❌ No | ❌ None |
| **Sigma Agent** | `agents/sigma/sigma_agent.py` | 1 location | ❌ No | ❌ None |
| **Nova Agent** | `agents/nova/nova_agent.py` | 1 location | ❌ No | ❌ None |

**Critical Gaps:**
- **No central LLM wrapper** — 4+ duplicate OpenAI client instantiations
- **No timeout handling** — All calls can hang indefinitely
- **No retry/backoff** — Transient failures cause immediate errors
- **No error normalization** — Each agent handles exceptions differently
- **No PII/secret redaction** — Prompts, responses, API keys can leak to logs
- **No receipt tracking** — Model outputs not audited
- **Tool calls not gated** — Nova has exec gate; others don't

---

## 1. LLM Invocation Inventory

### 1.1 Chat Agent (`agents/chat/chat_agent.py`)

| Method | Line | Type | Model | Params | Streaming |
|--------|------|------|-------|--------|-----------|
| `chat_stream()` | 323 | Streaming | `self.model` (default: gpt-4o-mini) | temp=0.7, max_tokens=2000 | ✅ |
| `_get_llm_response()` | 454 | Non-streaming | `self.model` | temp=0.7, max_tokens=2000 | ❌ |
| `_tool_draft_document()` | 591 | Non-streaming | `self.model` | temp=0.3, max_tokens=3000 | ❌ |
| `_tool_summarize_file()` | 632 | Non-streaming | `self.model` | temp=0.3, max_tokens=500 | ❌ |

**Fallback:** `_fallback_response()` returns rule-based responses when no API key or on error.

**Error Handling:** Bare `except Exception` — logs error, returns fallback string.

### 1.2 Zero Agent (`agents/zero/zero_agent.py`)

| Method | Line | Type | Model | Params | Purpose |
|--------|------|------|-------|--------|---------|
| `generate_fix_patch()` | 305 | Non-streaming | gpt-4o-mini | temp=0.1, max_tokens=4000 | Generate code fixes for failing tests |

**Fallback:** Rule-based fixture generation if LLM fails.

**Error Handling:** Logs error, falls back to rule-based.

### 1.3 Sigma Agent (`agents/sigma/sigma_agent.py`)

| Method | Line | Type | Model | Params | Purpose |
|--------|------|------|-------|--------|---------|
| `generate_report()` | 262 | Non-streaming | gpt-4o-mini | temp=0.2, max_tokens=1000 | AI code review of PR diff |

**Fallback:** None — review section omitted on error.

**Error Handling:** Logs error, continues without review.

### 1.4 Nova Agent (`agents/nova/nova_agent.py`)

| Method | Line | Type | Model | Params | Purpose |
|--------|------|------|-------|--------|---------|
| `execute_action()` | 291 | Non-streaming | gpt-4o-mini | temp=0.1, max_tokens=1000 | Generate dynamic action handlers |

**Fallback:** Raises `ValueError` if dynamic generation fails.

**Error Handling:** Logs error, raises exception. Has exec gate (`NOVA_ALLOW_DYNAMIC_EXEC`).

---

## 2. Reliability Gap Analysis

| Requirement | Chat Agent | Zero Agent | Sigma Agent | Nova Agent | Status |
|-------------|------------|------------|-------------|------------|--------|
| **Central wrapper** | ❌ Direct | ❌ Direct | ❌ Direct | ❌ Direct | ❌ Missing |
| **Timeout handling** | ❌ None | ❌ None | ❌ None | ❌ None | ❌ Missing |
| **Retry/backoff** | ❌ None | ❌ None | ❌ None | ❌ None | ❌ Missing |
| **Stream fallback** | ✅ Basic | N/A | N/A | N/A | ⚠️ Partial |
| **Error normalization** | ❌ None | ❌ None | ❌ None | ❌ None | ❌ Missing |
| **Redacted logging** | ❌ Logs raw | ❌ Logs raw | ❌ Logs raw | ❌ Logs raw | ❌ Missing |
| **Receipt tracking** | ❌ None | ❌ None | ❌ None | ❌ None | ❌ Missing |
| **Tool gating** | ❌ None | ❌ None | ❌ None | ✅ Exec gate | ⚠️ Partial |

---

## 3. PII/Secret Leakage Risk

| Location | Risk | Example |
|----------|------|---------|
| Chat Agent `_get_llm_response` | Logs full exception with prompt context | `logger.error("LLM call failed: %s", e)` |
| Chat Agent `chat_stream` | Logs exception with user message | `logger.error("Streaming failed: %s", e)` |
| Zero Agent `generate_fix_patch` | Logs prompt with file content | `logger.info("Successfully generated LLM patch...")` |
| Sigma Agent `generate_report` | Logs PR diff (may contain secrets) | `logger.error("LLM PR review failed: %s", e)` |
| Nova Agent `execute_action` | Logs generated code | `logger.info("Dynamically generated handler...")` |
| All agents | API key read from env directly | `os.environ.get("OPENAI_API_KEY")` |

**No redaction utilities exist anywhere in the codebase.**

---

## 4. Source of Truth Declaration

**No single source of truth exists for LLM invocation.**

Each agent independently:
- Imports `openai` inline
- Creates `OpenAI(api_key=...)` client
- Calls `chat.completions.create()`
- Handles errors differently

**Recommendation:** Create `services/llm_service.py` as the central invocation layer with:
- Unified client management
- Timeout, retry, fallback
- Error normalization
- Redacted logging
- Receipt emission

---

## 5. Required Audit Document Outputs

### 5.1 `docs/llm-reliability-audit.md` — This document

### 5.2 Implementation Targets

| Fix | File | Priority |
|-----|------|----------|
| Create `portal/services/llm_service.py` | New | CRITICAL |
| Add `LLMClient` with timeout/retry | New | CRITICAL |
| Add `redact()` utility | New | CRITICAL |
| Add `LLMReceipt` dataclass | New | CRITICAL |
| Refactor Chat Agent | `agents/chat/chat_agent.py` | HIGH |
| Refactor Zero Agent | `agents/zero/zero_agent.py` | HIGH |
| Refactor Sigma Agent | `agents/sigma/sigma_agent.py` | MEDIUM |
| Refactor Nova Agent | `agents/nova/nova_agent.py` | MEDIUM |
| Add tests | `portal/tests/test_llm_service.py` | HIGH |

---

## 6. Test Requirements

| Test Case | Status |
|-----------|--------|
| Successful non-streaming call | ❌ Missing |
| Successful streaming call | ❌ Missing |
| Provider timeout handling | ❌ Missing |
| Provider error (rate limit, auth) | ❌ Missing |
| Streaming failure → non-stream fallback | ❌ Missing |
| Retry capped at max attempts | ❌ Missing |
| Exponential backoff timing | ❌ Missing |
| PII redaction in logs | ❌ Missing |
| API key not logged | ❌ Missing |
| Receipt emitted per call | ❌ Missing |

---

## 7. Acceptance Criteria for PR-4

- [ ] `docs/llm-reliability-audit.md` exists (this document)
- [ ] All LLM entry points listed above
- [ ] Central `LLMService` created in `portal/services/llm_service.py`
- [ ] All 4 agents refactored to use `LLMService`
- [ ] Timeout, retry, fallback implemented
- [ ] Error normalization via `LLMError` hierarchy
- [ ] Redacted logging utility created and used
- [ ] No prompts/PII/API keys in logs
- [ ] Receipt JSON emitted per invocation
- [ ] Tests pass: `pytest portal/tests/test_llm_service.py -v`
- [ ] `docs/repo-verification-report.md` updated
- [ ] `artifacts/receipts/pr-0004-llm-reliability-audit.json` emitted

---

*End of Audit Phase — Implementation Phase begins next*
# Governed Inference Migration Coverage Report

**Report ID:** P3.4-COVERAGE-2026-07-27-01
**Phase:** 3.4 — Governance & Reliability Consolidation
**Date:** 2026-07-27
**Certified by:** Hermes Agent on behalf of Isiah Howard
**Baseline commit:** 86c1ac3eaed9fcecdde877975eddc337d4e29de2

---

## 1. Executive Summary

This report audits all remaining direct LLM SDK call sites in SintraPrime-Unified, quantifies migration coverage, and maps the path to full convergence on the governed inference control plane.

| Metric | Count |
|---|---|
| Migrated production consumers | 4 |
| Remaining productive direct-SDK call sites | 15 |
| Legacy fallback paths (preserved intentionally) | 4 |
| Deferred call sites (Nova dynamic execution) | 1 |
| Effective migration coverage | **21.1%** |
| Full coverage including legacy fallbacks | 16.7% |

Effective coverage is calculated as migrated consumers divided by the sum of migrated consumers and remaining productive (non-fallback, non-deferred) call sites.

---

## 2. Migrated Production Consumers

| Consumer | Primary Path | Phase Closed |
|---|---|---|
| `ModelRouter.complete()` | `local_models/model_router.py` | 3.2 |
| `ChatAgent._get_llm_response()` | `agents/chat/chat_agent.py` | 3.3.1 |
| `ZeroAgent.generate_fix_patch()` | `agents/zero/zero_agent.py` | 3.3.2 |
| `SigmaAgent.generate_gate_report()` AI review | `agents/sigma/sigma_agent.py` | 3.3.3 |

---

## 3. Remaining Productive Direct-SDK Call Sites

| File | Function | Category | Migration Notes |
|---|---|---|---|
| `agents/chat/chat_agent.py` | `_tool_draft_document` | Secondary tool | Same agent, secondary path; low risk |
| `agents/chat/chat_agent.py` | `_tool_summarize_file` | Secondary tool | Same agent, secondary path; low risk |
| `agents/chat/chat_agent.py` | `chat_stream` | Streaming | Streaming not yet supported end-to-end by adapters |
| `integrations/airtable_crm/crm_manager.py` | `enrich_contact_with_llm` | CRM integration | Structured JSON output; requires JSON schema support |
| `integrations/airtable_crm/crm_manager.py` | `generate_case_summary` | CRM integration | Text summary; low risk |
| `multimodal/document_vision.py` | `_call_vision_api` | Multimodal | GPT-4o Vision with image_url messages; needs vision adapter |
| `rag/rag_pipeline.py` | `_openai_generate` | RAG | Async OpenAI client; needs async router or sync adapter |
| `claude_code/engine.py` | `_send` | Claude Code | Anthropic `messages.create`; separate product area |
| `claude_code/code_generator.py` | `_send` | Claude Code | Anthropic `messages.create`; separate product area |
| `claude_code/legal_code_assistant.py` | `_send` | Claude Code | Anthropic `messages.create`; separate product area |
| `developer_experience/model_playground.py` | `OpenAIClient.complete` | Dev tool | Interactive playground; not production routing |
| `developer_experience/model_playground.py` | `AnthropicClient.complete` | Dev tool | Interactive playground; not production routing |
| `developer_experience/model_playground.py` | `DeepSeekClient.complete` | Dev tool | Interactive playground; not production routing |
| `phase17/llm_wiring/llm_executor.py` | `_call_openai` | Legacy gateway | Separate `LLMRequest/LLMResponse` contract |
| `local_llm/sintra_llm_bridge.py` | `_cloud_chat` | Legacy bridge | Async cloud chat with raw HTTP fallbacks |

---

## 4. Legacy Fallbacks Inside Migrated Consumers

These paths are preserved intentionally and should be removed only during an explicit retirement phase.

| File | Function | Protected By |
|---|---|---|
| `local_models/model_router.py` | `_call_openai`, `_call_anthropic` | `complete()` tries governed router first |
| `agents/chat/chat_agent.py` | `_get_llm_response` legacy branch | Tries governed router first |
| `agents/zero/zero_agent.py` | `_legacy_llm_fix_code` | `_llm_fix_code` tries governed router first |
| `agents/sigma/sigma_agent.py` | `_legacy_ai_review` | `_generate_ai_review` tries governed router first |

---

## 5. Deferred Call Site

| File | Function | Deferral Reason |
|---|---|---|
| `agents/nova/nova_agent.py` | `execute_action` dynamic handler generation | Dynamic code execution via `exec()` requires sandboxing, audit controls, and dedicated risk review. Deferral plan captured in `artifacts/nova_agent_migration_deferred_plan.md`.

---

## 6. Consistency Verification

All migrated consumers use an identical governed policy shape and request mapping convention:

| Attribute | Value | Consistent |
|---|---|---|
| `max_input_tokens` | 12000 | ✅ |
| `max_output_tokens` | capped by policy at 4096 | ✅ |
| `timeout_seconds` | 60 | ✅ |
| `max_attempts` | 3 | ✅ |
| `paid_models_allowed` | True when key present | ✅ |
| `paid_escalation_requires_explicit_approval` | False | ✅ |
| `estimated_cost_usd` | 0.0 (conservative) | ✅ |
| `pricing_known` | True | ✅ |
| `data_classification` | PUBLIC | ✅ |
| `quality_floor` | STANDARD | ✅ |

The `GovernedInferenceRouter` provides uniform:

- structured logging (`inference.requested`, `inference.classified`, `inference.route_selected`, `inference.completed`, etc.)
- data classification and redaction receipts
- fallback and retry logic
- timeout enforcement
- ledger receipts
- cache integration (currently in-memory)
- trace span hooks (active when a tracer is supplied)

No migrated consumer implements its own fallback chain, retry, or timeout logic; all defer to the router.

---

## 7. Gap Analysis

| Gap | Impact | Remediation |
|---|---|---|
| Streaming not fully supported | `chat_stream` remains on legacy path | Add `invoke_stream` to remaining adapters or document limitation |
| Vision messages not supported | `document_vision.py` remains on legacy path | Add vision-capable provider adapter |
| Async router missing | `rag/rag_pipeline.py`, `sintra_llm_bridge.py` remain on legacy paths | Add async `invoke` variant or wrap sync router |
| Structured output via JSON schema partially used | CRM enrichment could migrate if response_format is verified | Validate OpenAIProvider `response_format` handling |
| Claude Code product area | 3 direct Anthropic call sites | Treat as a separate migration workstream |
| Dev tools | 3 direct call sites in `model_playground.py` | Low priority unless productized |
| Legacy gateways | `llm_executor.py`, `sintra_llm_bridge.py` | Retire or bridge after consumer migration |

---

## 8. Conclusion

The governed inference control plane is serving four production consumers with consistent policy, logging, and fallback behavior. Coverage is intentionally low because the program prioritized low-risk, high-value consumers first. The remaining call sites are either secondary paths, dev tools, legacy gateways, or areas requiring additional adapter capabilities (streaming, vision, async).

No new migration is recommended until the gaps above are addressed or explicitly scoped by a subsequent phase.

---

## 9. References

- `artifacts/phase_3_3_3_sigma_agent_certification.md` — last migration certification
- `artifacts/nova_agent_migration_deferred_plan.md` — Nova deferral
- `governed_inference/AGENTS.md` — package DOX contract
- `local_models/AGENTS.md` — ModelRouter DOX contract

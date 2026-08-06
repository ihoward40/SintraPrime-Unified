# agents/chat — SintraPrime Autonomous Chat Agent

## Purpose

Owns the interactive Chat Agent: a general-purpose conversational interface that handles multi-turn sessions, delegates to specialist agents, manages session memory, and executes autonomous tasks in permitted modes.

## Ownership

- `agents/chat/chat_agent.py` — core agent implementation
- `agents/chat/__init__.py` — public exports
- `agents/chat/tests/test_chat_agent.py` — existing public API tests
- `agents/chat/tests/test_chat_agent_governed.py` — governed inference routing regression tests

## Local Contracts

- Public API stability: `ChatAgent.chat()`, `ChatAgent.create_session()`, session management, task execution, tool registration, statistics, and persistence must remain backward compatible.
- The primary LLM response path (`_get_llm_response`) routes through `GovernedInferenceRouter` when an OpenAI API key is present.
- The streaming response path (`chat_stream`) routes through `GovernedInferenceRouter.invoke_stream()` when an OpenAI API key is present and falls back to the legacy direct OpenAI SDK streaming call on failure.
- Legacy direct OpenAI SDK invocation remains as a fallback until an explicit retirement phase.
- No real external API calls are made in tests; use deterministic mock providers or legacy OpenAI mocks.
- Built-in tool handlers remain on legacy paths in this phase.

## Work Guidance

- When modifying the LLM response path, update both the governed route and the legacy fallback.
- Keep `InferenceRequest` mapping consistent with `local_models/model_router.py` conventions:
  - `task_type="chat"`
  - `capability="drafting"`
  - `data_classification=DataClassification.PUBLIC`
  - `quality_floor=QualityFloor.STANDARD`
- Preserve session token counting by reading `InferenceResult.usage["total_tokens"]`.
- Add regression tests for any new routing behavior; keep existing tests green.

## Verification

- Run `python -m pytest agents/chat/tests/test_chat_agent.py -q` after any change to the public interface.
- Run `python -m pytest agents/chat/tests/test_chat_agent_governed.py -q` after changing governed inference routing (includes streaming regression tests).
- Run `python -m pytest tests/test_chat_agent_governed.py -q` to verify the CI-visible wrapper includes streaming tests.
- Run the full suite (`python -m pytest --tb=short -q -o addopts=`) before certification.
- Run the smoke lane (`python scripts/smoke/e2e_skills_smoke.py`) before certification.

## Child DOX Index

*(None — modules are leaf modules.)*

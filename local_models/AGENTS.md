# local_models

## Purpose

Owns local and optional-cloud model integration for SintraPrime-Unified: Ollama client, DeepSeek client, model routing, quantization management, offline mode, and the local-models REST API.

## Ownership

- `ollama_client.py` — Ollama daemon integration
- `deepseek_client.py` — DeepSeek API integration
- `model_router.py` — Public routing surface for model completion
- `quantization_manager.py` — Memory calculations and quantization recommendations
- `offline_manager.py` — Air-gap mode and offline template cache
- `local_models_api.py` — FastAPI router exposing local-models capabilities

## Local Contracts

- The public API of `ModelRouter` is stable. Changes to signatures or return shapes require explicit authorization.
- `ModelRouter.complete()` delegates inference routing to `GovernedInferenceRouter` while preserving legacy provider call paths as a safety net.
- Local-first routing is the default; configured cloud providers are only used when keys are present and local routes fail.
- Air-gap mode disables all cloud/paid providers regardless of key presence.

## Work Guidance

- Add new provider integrations in `governed_inference/adapters.py`, not in this package.
- Keep legacy `_call_*` methods in `model_router.py` until an explicit retirement phase.
- Mock `OllamaClient` and `DeepSeekClient` for tests; do not require a running Ollama daemon or real API keys.

## Verification

- Run `python -m pytest local_models/tests/test_local_models.py -q` after changing this package.
- Run `python -m pytest tests/test_model_router_migration.py -q` after changing the delegation logic.

## Child DOX Index

*(None — modules are leaf modules.)*

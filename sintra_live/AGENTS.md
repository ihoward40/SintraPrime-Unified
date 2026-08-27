# SP-LIVE-001 I1 offline integration runtime

## Purpose

Implements the frozen D1 contracts for one complete governed synthetic mission. No live voice, real credentials, account connections, external APIs, side effects, or production mutations.

## Authority

- Offline implementation and local testing only.
- All components use mocks, fakes, and synthetic providers.
- No microphone, speaker, OAuth, real tokens, Google API calls, GitHub authority expansion, Drive retrieval, or production side effects.
- This package does not authorize I1 live execution, C1 certification, or any later gate.

## Architecture

```
sintra_live/
├── voice/
│   ├── synthetic_voice_input.py
│   └── synthetic_voice_output.py
├── identity/
│   └── principal_fixture.py
├── mission/
│   ├── mission_manager.py
│   ├── state_machine.py
│   └── transitions.py
├── memory/
│   └── governed_memory.py
├── swarm/
│   ├── orchestrator.py
│   ├── specialist.py
│   └── isolation.py
├── models/
│   └── model_router.py
├── approval/
│   ├── action_envelope.py
│   ├── approval_binding.py
│   └── validation.py
├── side_effect/
│   ├── synthetic_executor.py
│   └── fake_provider.py
├── verification/
│   └── independent_verifier.py
├── evidence/
│   ├── evidence_chain.py
│   └── seal.py
└── brief/
    └── principal_brief.py
```

## Integration contract

All components must:
- Accept synthetic/fake inputs only
- Produce deterministic, reproducible outputs
- Generate evidence with explicit SHA-256 hashes
- Enforce D1 state machine transitions
- Block on missing authority, approval, or evidence
- Never call real external services

## Test entry point

```python
from sintra_live.integration import run_synthetic_mission

result = run_synthetic_mission(principal_fixture, voice_fixture, mission_request)
# Returns sealed evidence bundle, principal brief, and test results
```
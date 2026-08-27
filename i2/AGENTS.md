# SP-LIVE-001 I2 Live Voice Convergence

## Purpose

Implement real live voice I/O (microphone capture, speech recognition, text-to-speech) while preserving all C1 authority, approval, evidence, swarm, memory, model-routing, and fail-closed controls. Real external side effects remain mechanically disabled.

## Authority

- Bounded milestone work package authorized by SP_LIVE_001_I2_LIVE_VOICE_CONVERGENCE_001
- Baseline: e4d260da867a2e04375b2329cd680be3b8833e79 (C1 PASS / COMPLETE)
- All C1 controls must remain active and unweakened
- Real external side effects: HARD DISABLED

## Architecture

### Voice Pipeline

```
AUDIO_DEVICE
→ CAPTURE
→ VAD (Voice Activity Detection)
→ SPEECH SEGMENT
→ STT (Speech-to-Text)
→ TRANSCRIPT + CONFIDENCE
→ PRINCIPAL SESSION BINDING
→ MISSION INPUT
→ GOVERNED OPERATING LOOP (memory, swarm, model routing, approval, evidence)
→ RESPONSE GENERATION
→ TTS (Text-to-Speech)
→ AUDIO PLAYBACK
```

### Key Principles

- VOICE != AUTHORITY
- TRANSCRIPTION != APPROVAL
- SPEAKER SOUNDING LIKE PRINCIPAL != AUTOMATIC AUTHORITY
- Voice layer supplies input to authority system; does not replace it

## Implementation Requirements

### Audio Capture
- Local microphone device discovery
- Push-to-talk and/or wake-word activation
- Voice activity detection
- Audio format normalization
- Streaming and buffered capture modes

### Speech Recognition (STT)
- Local or configured transcription models
- Streaming partial transcriptions
- Final transcription with confidence
- Interruption/barge-in handling
- Low confidence → clarification request

### Text-to-Speech (TTS)
- Local synthesis
- Spoken responses
- Interruption handling (stop on user speech)
- Latency optimization

### Principal Session
- Local interactive session model
- Explicit session activation
- Optional challenge/confirmation for consequential actions
- Ambiguity → blocked execution

### Conversational Experience
- Turn-taking
- Interruption handling
- Context persistence within session
- Natural response flow

### Hard Side-Effect Disablement
- External executor: DISABLED
- Real provider write path: DISABLED
- All external actions: DENY at mechanical boundary

### Evidence & Governance
- Transcript as authoritative textual evidence
- Timestamp evidence
- Transcription confidence evidence
- Voice transcript evidence
- Hash chains include voice records

## Demos Required (per authorization)

1. Simple conversation
2. Mission status
3. Swarm (≥2 specialists)
4. Memory retrieval
5. Approval (mock action, external disabled)
6. Ambiguous approval
7. Interruption
8. Principal Brief (written + spoken)

## Stop Conditions

- Real external side effect occurs
- Real external write required
- OAuth/account connection needed
- Connector authority expansion needed
- Deployment/release/PR merge needed
- Frozen C1 authority weakened
- D1 design materially redefined
- Architecture-level security blocker
- C1 certification integrity unreconciled
- I2 milestone complete
# SP-LIVE-001 D1 design package

## Purpose

Owns the immutable architecture and certification contract for the proposed SintraPrime Governed Live Operating Loop.

## Authority

- Design and test-plan authoring only.
- Source implementation, voice/microphone activation, biometric enrollment, persistent agents, production swarm, external tools, credentials, account connections, APIs, side effects, merge, release, and deployment are not authorized.
- Gate 4D-B and the ratified Gate 4D-C design remain untouched.
- This package does not authorize SP-LIVE-001-I1 or any later stage.

## Local contracts

- Consequential execution requires current authority, required approval, a certified capability, and evidence-capable execution.
- Ambiguous identity or approval blocks execution.
- Approval binds an immutable action envelope; material changes invalidate approval.
- Exactly one authorized external side effect is required for eventual SP-LIVE-001 certification; zero or more than one cannot pass.
- Independent verification and a valid evidence chain are required before completion.

## Verification

- Validate all JSON and JSON Schema artifacts.
- Verify cross-document state names, invariants, acceptance fields, hashes, and file counts.
- Verify no changes outside this package and no authority-file drift.
- Verify no secret patterns or implementation artifacts.

## Package index

- `SP-LIVE-001-MISSION-CONTRACT.md`
- `SP-LIVE-001-AUTHORITY-STATE-MACHINE.md`
- `SP-LIVE-001-VOICE-APPROVAL-PROTOCOL.md`
- `SP-LIVE-001-SWARM-CONTRACT.md`
- `SP-LIVE-001-MEMORY-CONTRACT.md`
- `SP-LIVE-001-ACTION-ENVELOPE-SCHEMA.json`
- `SP-LIVE-001-FIRST-MISSION-SELECTION.md`
- `SP-LIVE-001-THREAT-MODEL.md`
- `SP-LIVE-001-END-TO-END-ACCEPTANCE-PLAN.md`
- `SP-LIVE-001-DESIGN-MANIFEST.json`

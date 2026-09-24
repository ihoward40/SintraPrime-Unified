# WS8-CMRD-001 scenario calculator

## Purpose

Owns the standalone Phase 1 certified scenario-arithmetic engine and deterministic JSON replay.

## Ownership

`calculator.py`, `replay.py`, frozen `test-manifest.json`, example receipt, tests, and README.

## Local Contracts

- Only `SCENARIO_ARITHMETIC` is executable. Jurisdiction is context, not a legal-rule selector.
- Mailing and delivery are distinct evidence events. The user selects a trigger and counting convention.
- No automatic weekend or holiday adjustment and no legal deadline claim.
- Exports retain inputs, assumptions, version, counted dates and chronology; replay compares deterministic fields.
- Replay establishes consistency, not authorship. Legal authority admission is a separate R3 gate.
- Do not persist user inputs by default or wire public routes without separate review.

## Work Guidance

Keep arithmetic pure and reject missing or unsupported scenario inputs. Update the manifest and version when an interpretation-changing algorithm changes.

## Verification

From repository root: `python3 -m unittest ws8_cmrd.test_calculator -v`; `python3 -m ws8_cmrd.replay ws8_cmrd/example-timeline.json`.

## Child DOX Index

None.

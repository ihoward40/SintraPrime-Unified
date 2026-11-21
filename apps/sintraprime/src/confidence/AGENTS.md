# Confidence state and decay

## Purpose

Provide the per-fingerprint confidence state and conservative decay decision consumed by CLI, policy and speech code.

## Ownership

- `updateConfidence.ts`: validated operator policy/base state, immutable penalties and fail-closed reads.
- `evaluateConfidenceDecay.ts`: a read-only decision over attributable probation evidence; it does not promote or mutate requalification state.

## Local Contracts

- Load explicit policy from `config/confidence-policy.json`: `initial_score` and `penalties.THROTTLE`, `.ROLLBACK`, `.POLICY_DENIAL` must be finite numbers in [0,1]. No positive default is inferred.
- Base state is `runs/confidence/fingerprint/<sha256-of-UTF8-fingerprint>.json`, with exact `fingerprint` and a finite `confidence` in [0,1]. Policy score caps that provisioned base; missing/malformed policy, state or event data yields zero confidence.
- Adverse signals atomically publish uniquely named immutable penalty events beneath `runs/confidence/penalties/<hash>/`. Persist the chosen penalty amount so future policy changes cannot erase spent penalties. Sum committed events using exact decimal values of stored numbers and convert the result conservatively; do not read/modify/write the derived score or round it upward.
- A signal received without valid policy/state publishes a quarantine fact. Merely supplying configuration later does not remove that fact or restore authority. Explicit operator changes to policy, base or event history are authority-bearing; never automatically clear history or recover confidence.
- Stage events outside the committed ledger. Hash fingerprints for filesystem keys, verify embedded identities and preserve every concurrent penalty.
- Decay defaults to the existing `CONFIDENCE_DECAY_HOURS=72` and `CONFIDENCE_MIN_SUCCESS=1`. Invalid configuration/time/evidence decays conservatively. The existing probation summary proves at most one fresh success, even if its lifetime count is larger; a higher configured minimum needs stronger evidence and currently fails closed. Future or mismatched evidence is not success.

## Work Guidance

- Do not synthesize a permissive baseline or penalties to silence type errors.
- Do not count arbitrary, administrative, dry-run or unproven receipts as qualifying success.

## Verification

- From `apps/sintraprime`: `node --require tsx/cjs --test tests/unit/confidence-engine.test.mjs`.
- Cover absent/corrupt inputs, fingerprint isolation, configured penalties, quarantine, concurrent updates, precision and decay boundaries.

## Child DOX Index

None.

# SP-LIVE-001 voice and approval protocol

## Voice capture

- Record session ID, capture timestamps, audio-segment hashes, device/channel identity, speech-recognition provider/model, transcript, token/segment confidence, and consent/retention policy.
- Raw audio handling is separately governed; D1 does not authorize microphone activation or biometric enrollment.
- Low confidence, overlapping speakers, clipped commands, or uncertain wake/session binding require clarification.

## Principal session binding

Voice alone is not sufficient for consequential authority. A certified Principal Gateway binds the active voice session to a current Principal identity using separately approved factors. Re-authentication is required after timeout, channel/device change, speaker ambiguity, sensitive consequence class, or interrupted trust state.

## Turn-taking and barge-in

- The Principal may interrupt synthesis at any time.
- Barge-in stops speech output and records an interruption event; it does not imply approval.
- “Stop,” “cancel,” or kill-switch phrases immediately suspend pending execution and enter `CANCELLED` unless already in an ambiguous provider attempt, which enters reconciliation.
- Background speech and assistant echo are excluded from approvals.

## Proposal presentation

Before consequential execution, SintraPrime speaks and displays the same canonical summary:

- exact action and capability;
- destination and material parameters;
- expected consequence and reversibility;
- evidence/verification plan;
- expiry and action-hash short code.

The spoken/displayed renderings are hashed and linked to the canonical action envelope.

## Approval grammar

Approval requires an explicit affirmative response tied to the pending proposal, for example: “I approve action `<short-code>`.” Configurable equivalent phrases must include an unambiguous approval verb and pending action identifier. “Okay,” “sure,” silence, conversational acknowledgements, future intent, or approval of a different action are ambiguous and block.

Rejection includes “reject,” “do not execute,” “cancel,” and equivalent explicit negatives. Conflicting affirmative/negative language is rejection/ambiguity, never approval.

## Approval record

Bind Principal identity/session, mission ID, action hash, proposal-render hashes, transcript/audio-segment hashes, approval phrase, confidence, timestamp, expiry, nonce, consequence class, and previous evidence hash. Approval must be one-time and cannot authorize another mission or action.

## Expiry and material change

Approval expires at its explicit deadline, mission expiry, Principal session loss, cancellation, capability certification change, or kill switch. Changes to action, destination, capability, parameters, consequence class, evidence requirements, credential/account binding, or idempotency key invalidate approval. Cosmetic presentation changes require deterministic proof of semantic identity.

## Result and Principal Brief

After independent verification, SintraPrime speaks a concise result: what was approved, what occurred, verification outcome, exceptions, and evidence reference. The spoken brief and written brief derive from one sealed canonical brief object and have recorded render hashes. If voice delivery fails, the mission is `INCOMPLETE`, even if written evidence exists.

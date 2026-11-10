# SP-COLLECTIVE-INTELLIGENCE-001

## Purpose

Implement a governed organizational-learning loop for SintraPrime/IKE:

1. One agent learns from evidence.
2. Independent agents challenge the lesson.
3. An independent verifier verifies or rejects it.
4. Verified knowledge becomes distributable organizational memory.
5. Only relevant agents inherit the lesson.
6. Agents demonstrate competency against evidence-bound lessons.
7. Useful lessons may produce value/revenue proposals.
8. Consequential execution remains approval-gated.
9. Outcomes are measured with evidence.
10. Results feed the next learning cycle.

## Implemented in this increment

- Typed lesson, evidence, challenge, competency, value-proposal, and outcome contracts.
- Fail-closed state transitions for challenge/verification/distribution.
- Independence rules: source != challenger; verifier != source/challenger.
- Targeted inheritance: only explicitly applicable agents receive distributable lessons.
- Evidence-bound competency receipts.
- Supersession invalidates dependent competency by marking it STALE.
- Value proposals always carry `requires_principal_approval=True`.
- Outcome records require evidence references.
- Root DOX contract makes TRAINING != CERTIFICATION != AUTHORIZATION durable.

## Reused architecture

This increment does **not** create a second evidence ledger, memory vault, agent registry,
receipt system, or approval engine. The pure coordinator is designed to connect to the
existing Constitutional Evidence Ledger / Blackstone knowledge objects, governed memory
writeback, canonical agent registry/certification, and existing approval paths.

## Not claimed

- No production persistence adapter is wired in this increment.
- No autonomous web scout is activated.
- No agent receives new execution authority.
- No consequential external action is authorized.
- No revenue is claimed.
- No merge or deployment is authorized by this implementation.

## Next integration increments

1. Persistence adapter: map `EvidenceRef` and verified `Lesson` to existing CEL/KO and
   governed memory writeback without introducing a parallel store.
2. Registry adapter: bind competency receipts to canonical agent identity and certification
   dependency closure.
3. Academy adapter: generate evidence-bound curricula/exams and require independent
   red-team review before competency certification.
4. Mission adapter: allow verified lessons to be retrieved by applicable agents within
   tenant/memory scope.
5. Outcome adapter: ingest receipts/telemetry from approved executions and create new
   OBSERVED lessons for challenge, never auto-verify outcomes.
6. Competitive-intelligence scout: public/authorized-source collection only, with source
   provenance and freshness/reverification rules.
7. Revenue experiment lane: product/marketing proposals may be generated automatically,
   but publishing, spending, customer contact, pricing mutation, financial movement, and
   other consequential actions remain approval-gated.

## Acceptance rules

- Unchallenged knowledge cannot verify.
- Self-challenge cannot satisfy the gate.
- Challenger cannot also serve as verifier for that lesson.
- Failed challenge blocks verification/distribution.
- Unverified knowledge cannot drive value proposals.
- Inheritance is relevance-scoped.
- Competency is evidence-bound and becomes stale on supersession.
- Outcomes require evidence.
- Competency never grants execution authority.

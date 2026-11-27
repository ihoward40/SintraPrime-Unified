# SintraPrime Product Truth (PRODUCT.md)

> **Durable product truth for the SintraPrime web app.** Companion to
> `web/DESIGN.md`. This file defines what the product *is*, who it serves, and
> what it must never do. AI agents generating UI copy, flows, or features must
> follow this file first.
>
> Structural pattern inspired by
> [pbakaus/impeccable](https://github.com/pbakaus/impeccable) (Apache-2.0).
> See the Attribution footer at the end.

**Status:** v1.0 · 2026-10-06 · applies to `web/`

---

## 1. What the web app is

SintraPrime-Unified's web app is the operator console for an AI legal and
financial automation platform — "the world's first AI law firm & financial
empire portal." It is a **working tool for a professional operator**, not a
marketing site and not a consumer chatbot.

It exists to let the operator:

- Monitor the health and state of connected legal/financial workflows
  (mission-control dashboards, system status, metrics).
- Review AI-generated legal and financial work product **before it is used**
  (drafts, analyses, filings preparation).
- Approve, reject, or hold actions that change external state (payments,
  filings, submissions).
- Maintain an evidence and audit trail of what the system did and decided.

## 2. Who it serves

- **Primary user:** the platform owner/operator (a sophisticated principal who
  runs on written directives, evidence, and governance).
- **Secondary audience:** licensed professionals (attorneys, accountants,
  compliance reviewers) who consume or validate the work product.
- **Not for:** the general public, casual consumers, or anyone seeking legal or
  financial advice from the interface itself.

## 3. Key user journeys

1. **Morning state check** — open the console, read the status bar and metrics,
   confirm every connected system is healthy. (Layout: `mc-masthead`,
   `mc-statusbar`, `mc-metrics`.)
2. **Review AI work product** — open a draft/analysis, read it, check its
   provenance (which model, which source documents, when generated), then
   approve, request changes, or hold.
3. **Approve an external action** — a payment, filing, or submission is
   proposed; the operator sees what, why, the evidence, the risk, and the
   reversibility before explicitly approving. Nothing external executes without
   approval.
4. **Investigate an incident** — drill from a degraded/offline system row into
   detail, see the timeline, and find the decision or evidence it blocks.
5. **Produce an audit receipt** — export or view the record of an approved
   action: what happened, when, where, resulting state.

## 4. Tone and voice for UI copy

- **Direct, precise, evidence-first.** Short sentences. No marketing fluff, no
  exclamation points in operational copy.
- **State what is known; label what is not.** Prefer "Status unknown — last
  check 14:02" over "Everything looks fine." Never manufacture certainty.
- **Actions name their consequence.** Buttons say what happens: "Approve $75
  payment", "Hold filing", "Export audit receipt" — not "Submit" or "OK".
- **Professional-review framing.** Copy positions the operator (and their
  licensed professionals) as the decision-maker. The system proposes; the human
  disposes.
- **Errors explain and offer a next step.** "Sync failed — retry" beats "An
  error occurred."

## 5. What the app must NEVER do

These are hard constraints. A UI change that violates any of them is wrong no
matter how good it looks.

1. **Never present AI output as licensed professional advice.** Legal and
   financial work product is labeled "for professional review" / "draft — not
   legal/financial advice." No screen, summary, or export may imply the output
   carries attorney, CPA, or other professional authority on its own.
2. **Never execute an external action without explicit operator approval.**
   Payments, filings, submissions, account changes, and outbound communications
   require an explicit approve step (READ → VERIFY → ANALYZE → PROPOSE →
   REQUEST APPROVAL → ACT → REPORT RECEIPT).
3. **Never hide provenance.** AI-generated content must show its source: model,
   inputs/documents, generation time. No unattributed "answers."
4. **Never manufacture certainty.** Unknown state stays labeled unknown.
   Estimates are labeled estimates. Absence of an alert is not proof of health.
5. **Never expose secrets or credentials.** No API keys, tokens, or credential
   values in UI, logs, or exports — masked references only.
6. **Never silently drop evidence.** Destructive or archival actions are
   confirmed, reversible where possible, and recorded in the audit trail.
7. **Never use dark patterns.** No pre-checked consent, no disguised upsells,
   no urgency copy designed to push an approval through.

## 6. Non-goals

- Not a marketing/landing site.
- Not a consumer self-serve legal/financial advice product.
- Not a replacement for licensed professional judgment — it is the workspace
  where that judgment is applied.

---

## Attribution

Product-truth-doc pattern (durable `PRODUCT.md` alongside `DESIGN.md` as
governing context for AI-generated frontends) adapted from
[pbakaus/impeccable](https://github.com/pbakaus/impeccable), © the impeccable
authors, licensed under the Apache License 2.0. This file's content is original
to SintraPrime; only the pattern is adapted.

---
id: "7e9b52a1"
agent: "agent"
platform: "cli"
timestamp: "2026-09-22T12:59:28Z"
type: "decision"
tier: "hot"
summary: "SP-SYSTEM-ONE-DECISION-FABRIC-001 R1 directive frozen; awaiting admin-side implementation in an approved worktree"
project_id: "unknown"
session_id: "sess-20260922-125928-29208"
tags: [sintraprime,decision-fabric,jev,governance,r1,spec]
status: "open"
outcome: "Directive text frozen and agreed by both lanes; implementation not started. Next owner must create R1 artifacts before any PASS claim."
assigned_to: "admin"
training_value: "normal"
evidence: "Design only; no implementation artifacts exist yet. Repository state verified by direct inspection (git worktree list, ls)."
---

## Program: SP-SYSTEM-ONE-DECISION-FABRIC-001 — R1 frozen directive status

Directive (v3, closing the design loop): vendor-neutral Decision Fabric in SintraPrime-Unified; Jev (typesafe-ai/jev) is first provider, not a dependency. Constitution: "Probability may select a workflow. Probability may not create authority."

R1 scope: DecisionProvider protocol; MockDecisionProvider (mandatory) + JevDecisionProvider; canonical primitives CHOICE|SCORE|BOOLEAN (Noul strictly provider-local, normalized in adapter); canonical state serialization (sp-decision-state-v1, sorted keys, deterministic hashes, conformance fixture); semantic contract hashing (parse→validate→strip→normalize→canonical JSON→SHA-256, whitespace/comment-insensitive); full distribution persisted (top1/top2/margin/provider confidence); abstention first-class (DECISION|ABSTAIN|ERROR|UNAVAILABLE); fail-closed degradation (provider failure → Hermes path, never deterministic execution); untrusted-content boundary (SYSTEM CONTEXT | TRUSTED METADATA | UNTRUSTED CONTENT | DERIVED FEATURES; injection fixtures); ledger receipt schema with SHADOW_ONLY default; R1 contracts limited to decision.health.v1, case_route.v1, execution_risk.v1, verification_disposition.v1.

Config defaults: SINTRAPRIME_DECISION_PROVIDER=mock, SINTRAPRIME_DECISION_SHADOW_ONLY=1; live Jev requires explicit config (JEV_API_KEY etc., no secrets in source).

Status: DESIGN APPROVED WITH MANDATORY R1 PRECONDITIONS. R1 = UNKNOWN / UNVERIFIED until artifacts exist. Next proper move: R1 only — interfaces, canonicalization, semantic hashing, normalization, failure behavior, mock provider, tests, evidence artifacts. No live steering.

Independent verification rule (§14): different input ≠ independence. For Jev-routed work: LOW-RISK may use independent verification contract; ELEVATED/CONSEQUENTIAL require Hermes or independent verifier; HIGH-RISK human/governed. No Jev decision may both authorize its route and serve as sole evidence of validity.

Standing reality rule: IMPLEMENTED ≠ VERIFIED ≠ CALIBRATED ≠ AUTHORIZED ≠ SUCCESSFUL.

## 2026-09-22 environmental note (HERMES@admin lane):
Worktrees exist locally: C:/Users/howar/SintraPrime-Unified (main repo, currently on rc/g0r3-collection, 4+ modified files uncommitted) plus detached-HEAD worktrees SintraPrime-Unified-sp-exec001-repair (dirty: scheduler/task_scheduler.py, workflow_builder/web_tui.py), SintraPrime-EXEC001-{CERT-R2,DIAG,W1,WAVE2-QUARANTINE}. No decision/ or jev/fabric directory exists yet in the repair worktree — R1 is greenfield. Admin must pick implementation worktree per one-writer rule and record the choice in the R1 manifest. CLINE: RECORD/OBSERVE ONLY.
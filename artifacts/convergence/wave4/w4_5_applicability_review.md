# SP-W4-5-APPLICABILITY-R1

```text
W4-5 = BLOCKED_BY_MISSION_WIRING_PUBLICATION
BLOCKER = GOVERNED_BROWSER_EXECUTOR_NOT_PRESENT_ON_PRODUCTION_LINE
CLASSIFICATION = B
```

## Mechanism availability vs governed execution

Browser mechanisms are present, but a governed browser execution boundary is not present on production main. No browser mechanism was promoted or modified.

| Path | Reachable | Authority-aware | Capability-gated | Side-effect classified | Approval-aware | Registry-bindable now | Canonical governed executor |
|---|---|---|---|---|---|---|---|
| `operator/browser_controller.py` | NO production importer found | NO | NO | NO | NO | NO | NO |
| `apps/sintraprime/src/automation/browserRunner.ts` | YES via VLM app wiring | PARTIAL app-level `PolicyGate`; runner itself NO | NO registry binding | NO | NO direct approval binding | NO | NO |
| `apps/SintraPrime/src/browserOperator/l0.ts` + `runBrowserOperator.ts` | YES via `executePlan.ts` | NO registry/authority binding | YES URL/SSRF policy only | NO governed capability class | NO direct approval binding | NO | NO |
| `mission_wiring/browser_executor.py` | NO; unpublished ZD-001 derivative | YES | YES | YES | YES | YES | YES, but unpublished |

## Decision

Do not retrofit authority into `operator/browser_controller.py`. Do not promote `mission_wiring/` implicitly. A separate reconciliation/publication decision is required before W4-5 implementation can begin.

# SintraPrime Agentic Runtime

This package adds provider-neutral primitives inspired by the strongest ideas
in current agentic engineering systems without weakening SintraPrime's
constitutional control plane.

## What is implemented

- **Build loop:** ordered actions with injected authorization and evidence hooks.
- **Auto-heal loop:** bounded repair attempts followed by re-verification.
- **Janitor mode:** refactor/cleanup execution with verification but no silent
  behavior-changing repair cycle.
- **Capability registry:** routes by context length/capability/evidence status,
  not vendor marketing.
- **Media workflow policy:** a fail-closed admission contract for ComfyUI-style
  image, video, audio and 3D pipelines, including local-only and cost controls.

## Integration rule

This layer MUST sit behind existing SintraPrime governance. It intentionally
contains no raw shell runner, no unrestricted filesystem writer, no Git push,
no payment action, and no direct cloud-media invocation. Callers inject those
capabilities only after existing approval/risk policy admits them.

## Recommended adapters

1. Bind `authorize` to `governance.approval_gate` / Nova approval gateway.
2. Bind `record` to the existing execution ledger/audit trail.
3. Bind model profiles to `local_models.model_router` and governed inference.
4. Add a ComfyUI adapter that accepts only admitted `MediaJob` objects.
5. Require explicit principal approval for external providers, paid execution,
   publication, destructive filesystem actions, Git push/merge, and deployment.

## Evidence labels

Model/license/context claims should enter the registry as `UNVERIFIED` until
checked against primary documentation. This prevents a transcript or video
claim from silently becoming an execution assumption.

# Agent Receipts

This directory stores audit receipts for every agent action taken on the SintraPrime Unified repository.

## Naming Convention

```text
<task-id>-<agent>.md
```

Examples:
- `P0-001-manus.md`
- `P0-002-manus.md`
- `SPU-012-tasklet.md`

## Required Fields

Every receipt must include:

| Field | Description |
|---|---|
| Agent | Name of the agent that performed the work |
| Task ID | Task identifier from `/ops/tasks/` |
| Branch | Git branch used |
| Files changed | List of all files created or modified |
| Commands run | All shell commands executed |
| Tests passed | Number and names of passing tests |
| Tests failed | Number and names of failing tests |
| Security results | Output of bandit/safety scans |
| Known risks | Any identified risks or concerns |
| Manual review required | Yes/No and reason |
| Next recommended task | Suggested follow-up task ID |
| Timestamp | ISO 8601 datetime |

## Policy

- No agent work is considered complete without a receipt.
- Receipts are reviewed by the Commander before merge approval.
- Missing receipts block the pull request.

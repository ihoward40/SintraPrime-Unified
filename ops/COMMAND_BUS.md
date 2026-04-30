# SintraPrime Command Bus

## Workflow

1. Commander creates GitHub Issue or task JSON.
2. Tasklet watches GitHub issues labeled `agent-ready`.
3. Tasklet summarizes the mission and assigns it to either:
   - Manus for implementation/research
   - Tasklet for recurring execution/monitoring
4. Manus works only on a feature branch.
5. Manus opens or prepares a pull request.
6. Tasklet runs recurring checks and summarizes status.
7. Commander reviews.
8. Merge only occurs after all gates pass.

## Labels

- `agent-ready`
- `tasklet`
- `manus`
- `p0-security`
- `refactor`
- `tests`
- `docs`
- `blocked`
- `human-review-required`

## Branch Naming

```text
agent/tasklet/<task-id>-short-name
agent/manus/<task-id>-short-name
remediation/<task-id>-short-name
```

## Phase Ownership Registry

Before starting any implementation, check this registry. If a phase is already assigned, **stand down immediately** and notify the Commander.

| Phase | Scope | Owner | Status |
|---|---|---|---|
| P0-001 | `.gitignore` + `.env.example` | Manus | ✅ Merged #28 |
| P0-002 | CI fail-closed gates | Manus | ✅ Merged #30 |
| P0-003 | `exec()` gate | Manus | ✅ Merged #31 |
| P0-004 | Dependabot CVEs | Manus | ✅ Merged #33 |
| Phase 21A | SAML/SSO (Sessions, Okta, Azure, Google) | **Tasklet** | 🔄 In progress |
| Phase 22 | Ruff lint debt + test collection fixes | TBD | Queued |

## Collision Prevention Rule

> **No two agents may work on the same phase, module, or file path simultaneously.**
>
> Before creating a branch or writing any code, an agent MUST:
> 1. Check the Phase Ownership Registry above.
> 2. Check `git branch -r | grep <phase-keyword>` for any existing branches.
> 3. If a branch or ownership entry already exists for that scope — **STOP**. Post a comment on the relevant issue/PR and wait for Commander direction.
>
> Violation of this rule causes merge conflicts, duplicate work, and wasted CI minutes.

## Required Gates


```bash
python -m pytest --tb=short -q
ruff check .
bandit -r . -x tests/ -ll
safety check -r requirements.lock
grep -R "|| true" .github/workflows && exit 1 || echo "CI fail-closed"
grep -R "allow_origins=.*\*" -n . && exit 1 || echo "CORS restricted"
grep -R "assert True" -n tests && exit 1 || echo "Tests meaningful"
grep -R "sys.path.insert\|sys.path.append" -n tests && exit 1 || echo "Imports clean"
```

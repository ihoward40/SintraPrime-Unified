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

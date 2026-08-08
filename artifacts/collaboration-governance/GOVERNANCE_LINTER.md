# Governance Linter

Static inspection of workflow definitions, agent contracts, and
channel bindings (directive §86, §144). Fail CI where appropriate.

## Rules — `GovernanceLinter`

### lint_workflow(definition)

| Rule | Severity | Condition |
|---|---|---|
| UNBOUNDED_LOOP | ERROR | no max_iterations / max_hops |
| MISSING_BUDGET | ERROR | no budget |
| MISSING_HASH | WARNING | no hash |
| MISSING_VERSION | WARNING | no version |
| MISSING_TENANT | WARNING | no tenant scope |
| HIGH_AUTHORITY_NO_APPROVAL | ERROR | A3/A4 without approval |
| SELF_CERTIFICATION | ERROR | certifier_id == implementer_id |

### lint_agent_contract(contract)

| Rule | Severity | Condition |
|---|---|---|
| PRIVILEGED_PUBLIC_AGENT | ERROR | public + A2/A3/A4 |
| NO_FORBIDDEN_CAPS | WARNING | no forbidden_capabilities |
| UNVERSIONED_CONTRACT | WARNING | no version |
| UNHASHED_CONTRACT | WARNING | no hash |

### lint_binding(binding)

| Rule | Severity | Condition |
|---|---|---|
| UNAUTHORIZED_ALL_MESSAGES | ERROR | all_messages without authorization |
| NO_EVENT_TYPES | WARNING | no subscriptions |
| PUBLIC_TRUST_HIGH_AUTH | ERROR | T0 + A2/A3/A4 |

## Architecture Linter (§87, §145)

`ArchitectureLinter.scan_file()` — targeted anti-pattern detection:

```text
DIRECT_PROVIDER_CALL: import openai / requests.post / httpx.post /
                      provider.call / direct_api_call
```

Only where technically reliable (text-level, with `# noqa:arch-lint`
escape). Deeper AST-based checks are CF-2.

## Proof Tests (§144)

```text
test_unbounded_loop_detected
test_missing_budget_detected
test_self_certification_detected
test_high_authority_no_approval
test_public_agent_high_authority
test_binding_unauthorized_all_messages
test_compliant_workflow
test_architecture_linter / test_architecture_linter_clean
```

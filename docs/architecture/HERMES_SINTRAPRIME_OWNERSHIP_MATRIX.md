# Hermes / SintraPrime Ownership Matrix

## Proposed Boundary (confirmed by source evidence)

| Responsibility | Hermes | SintraPrime | Adapter | Prohibited duplication |
| -------------- | :----: | :---------: | :-----: | ---------------------- |
| Specialist identity | — | **final authority** | validates | Do not create Hermes specialist concept |
| Profile identity | **final authority** | — | reads only | Do not duplicate profile engine |
| Profile discovery | owns mechanics | — | reads via filesystem/CLI | Do not reimplement profile enumeration |
| Routing decision | inbound message routing | high-level intent/case routing | maps specialist → profile | Do not duplicate Hermes gateway routing |
| Tenant authorization | — | **final authority** | enforces before delegation | Do not move tenant checks into Hermes |
| Hard deny | pattern detection for dangerous CLI commands | enterprise policy deny | SintraPrime deny overrides all | Do not rely on Hermes to enforce SintraPrime policy |
| Human approval | CLI/gateway interactive approval | `ApprovalGateway` owns enterprise approval record | Hermes approval cannot override SintraPrime denial | Do not create second approval engine inside SintraPrime beyond existing `ApprovalGateway` |
| Tool execution | owns runtime mechanics | authorizes and audits | read-only delegation envelope | Do not duplicate tool implementations |
| Session persistence | **final authority** | — | not touched in Increment One | No new SintraPrime session store |
| Checkpoint recovery | **final authority** | — | not touched in Increment One | No new checkpoint store |
| Provider selection | **final authority** | — | receives cost warning only if needed | Do not duplicate provider catalog |
| Cost warning | emits warning | decides policy response | surfaces warning | Do not duplicate pricing data |
| Secret loading | **final authority** | — | never reads Hermes secrets | Do not duplicate secret store |
| Redaction | redacts raw command/prompt text | redacts enterprise audit payload | applies both layers | Do not trust Hermes redaction as sole layer for SintraPrime evidence |
| Audit event generation | emits observer hooks | `ExecutionLedger` / `ConstitutionalEvidenceLedger` receive final event | constructs SintraPrime event | Do not duplicate ledger inside Hermes |
| Evidence hashing | — | **final authority** (`ExecutionLedger`, CEL) | includes hash of redacted envelope | Do not duplicate hashing inside adapter |
| Kill switch | per-profile disable | enterprise kill switch | SintraPrime kill switch evaluated first | Do not require Hermes to enforce enterprise kill |
| External action | executes after Hermes approval | authorizes and records | no external action in Increment One | Do not send/file/email from adapter |
| Error normalization | returns raw errors | normalizes to governance event | maps to SintraPrime error class | Do not expose Hermes internals to users |

## Source evidence

- SintraPrime `agent_id` and `AgentCapabilities` are defined in `agent_protocol/message_types.py`; discovery is in `agent_protocol/agent_discovery.py`; the network facade is in `agent_protocol/__init__.py` (`AgentNetwork`).
- SintraPrime `ApprovalGateway`, `ApprovalRequest`, `ApprovalStatus`, `ApprovalTier` are in `agents/nova/approval_gateway.py`.
- SintraPrime `ExecutionLedger` and `LedgerEntry` are in `agents/nova/execution_ledger.py`.
- SintraPrime `ConstitutionalEvidenceLedger` and `EvidenceItemRecord` are in `blackstone/bra/cel.py`.
- SintraPrime tenant/user/role models are in `portal/models/user.py`.
- Hermes profile identity and directory layout are in `hermes_cli/profiles.py`.
- Hermes profile routing is in `gateway/profile_routing.py`.
- Hermes profile description is in `hermes_cli/profile_describer.py`.

## Key boundary rule

**No Hermes approval may override a SintraPrime denial.** SintraPrime hard-deny and approval decisions are evaluated before any Hermes delegation. Hermes runtime approval remains an internal execution safety layer.
